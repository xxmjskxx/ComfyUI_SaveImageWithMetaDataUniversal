"""Central, privacy-safe JSON cache for Civitai AutoV1/AutoV3 hashes.

The full SHA-256 hash and its AutoV2 prefix already live in per-model
``.sha256`` sidecars (kept for Stability Matrix compatibility and left
untouched). This module stores only the two hashes that cannot be derived from
the sidecar — AutoV1 (8 chars, a fixed 64 KiB window at 1 MiB) and AutoV3
(12 chars, the safetensors payload digest) — in a single shared JSON file under
ComfyUI's user directory.

The cache is:
- **Privacy-safe**: records contain no absolute paths; the ``cacheKey`` is a
  SHA-256 of ``{category, selectedValue, size, modifiedNs}``.
- **Atomic**: written via ``tempfile`` + ``fsync`` + ``os.replace``.
- **Locked**: a byte-range lock (``msvcrt``/``fcntl``) plus a per-process
  ``RLock``, so concurrent ComfyUI processes can't corrupt the file.
- **Tolerant**: malformed or over-limit records are silently dropped on read,
  and a corrupt cache file never raises to the caller.
"""

from __future__ import annotations

import errno
import hashlib
import json
import logging
import os
import re
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

try:  # ComfyUI runtime provides this; tests may stub it
    import folder_paths
except ModuleNotFoundError:  # pragma: no cover - isolated test fallback
    folder_paths = None  # type: ignore

if os.name == "nt":  # pragma: no cover - selected only on Windows
    import msvcrt as _locking_module
elif os.name == "posix":  # pragma: no cover - selected only on POSIX
    import fcntl as _locking_module
else:  # pragma: no cover - no supported release platform reaches this branch
    _locking_module = None

logger = logging.getLogger(__name__)

HASH_CACHE_SCHEMA = "saveimage-unimeta.hash-cache"
CACHE_FORMAT_VERSION = 1
DEFAULT_MAX_CACHE_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_CACHE_RECORDS = 50_000
DEFAULT_LOCK_TIMEOUT_SECONDS = 5.0
_LOCK_RETRY_SECONDS = 0.01
_CONTENTION_ERRNOS = {errno.EACCES, errno.EAGAIN}

_HEX8_RE = re.compile(r"^[0-9a-fA-F]{8}$")
_HEX12_RE = re.compile(r"^[0-9a-fA-F]{12}$")

_ENV_CACHE_PATH = "METADATA_HASH_CACHE_PATH"
_FALLBACK_DIR = ".saveimage_unimeta"
_FALLBACK_FILE = "hash-cache.json"


@dataclass(frozen=True, slots=True)
class HashCacheKey:
    """Stable cache identity containing no absolute path."""

    category: str
    selected_value: str
    size: int
    modified_ns: int

    @property
    def token(self) -> str:
        """Return a deterministic opaque cache-record key."""
        source = json.dumps(
            {
                "category": self.category,
                "modifiedNs": self.modified_ns,
                "selectedValue": self.selected_value,
                "size": self.size,
            },
            separators=(",", ":"),
        )
        return hashlib.sha256(source.encode("utf-8")).hexdigest()


class _LockTimeoutError(OSError):
    """Raised internally when a cross-process lock cannot be acquired."""


def _user_directory() -> str:
    """Return ComfyUI's user directory or a safe home-directory fallback."""
    try:
        if folder_paths is not None:
            getter = getattr(folder_paths, "get_user_directory", None)
            if callable(getter):
                user_dir = getter()
                if user_dir:
                    return str(user_dir)
    except OSError:  # pragma: no cover - defensive
        pass
    return os.path.expanduser("~")


def get_hash_cache_path() -> str:
    """Return the path of the central hash-cache JSON file.

    The location can be overridden with ``METADATA_HASH_CACHE_PATH`` (used by
    tests for isolation). The default is ComfyUI's user directory.
    """
    override = os.environ.get(_ENV_CACHE_PATH, "").strip()
    if override:
        return override
    return os.path.join(_user_directory(), _FALLBACK_DIR, _FALLBACK_FILE)


class HashCache:
    """Versioned JSON cache for AutoV1/AutoV3, invalidated by size and mtime."""

    def __init__(
        self,
        path: str,
        *,
        max_bytes: int = DEFAULT_MAX_CACHE_BYTES,
        max_records: int = DEFAULT_MAX_CACHE_RECORDS,
        lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    ) -> None:
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.max_records = max_records
        self.lock_timeout_seconds = lock_timeout_seconds
        self._process_lock = threading.RLock()

    # -- reading -----------------------------------------------------------------

    def _read_unlocked(self) -> list[dict]:
        try:
            raw = self.path.read_bytes()
        except FileNotFoundError:
            return []
        except OSError as exc:  # pragma: no cover - defensive
            logger.debug("[HashCache] Read failed for %s: %s", self.path, exc)
            return []
        if len(raw) > self.max_bytes:  # pragma: no cover - oversized cache
            logger.debug("[HashCache] Cache file too large: %s", self.path)
            return []
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.debug("[HashCache] Cache JSON invalid: %s", self.path)
            return []
        if (
            not isinstance(payload, dict)
            or payload.get("schemaName") != HASH_CACHE_SCHEMA
            or payload.get("formatVersion") != CACHE_FORMAT_VERSION
            or not isinstance(payload.get("records"), list)
        ):
            return []
        records: list[dict] = []
        for value in payload["records"][: self.max_records]:
            validated = _validate_record(value)
            if validated is not None:
                records.append(validated)
        return records

    def get(self, key: HashCacheKey) -> dict[str, str] | None:
        """Return ``{"AutoV1": …, "AutoV3": …}`` for an exact cache match."""
        for record in self._read_unlocked():
            if record.get("cacheKey") != key.token:
                continue
            if (
                record.get("category") != key.category
                or record.get("selectedValue") != key.selected_value
                or record.get("size") != key.size
                or record.get("modifiedNs") != key.modified_ns
            ):
                continue
            hashes = record.get("hashes")
            if isinstance(hashes, dict):
                return dict(hashes)
        return None

    # -- writing -----------------------------------------------------------------

    def _write_unlocked(self, records: list[dict]) -> None:
        payload = {
            "schemaName": HASH_CACHE_SCHEMA,
            "formatVersion": CACHE_FORMAT_VERSION,
            "records": records,
        }
        encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        if len(encoded) > self.max_bytes:  # pragma: no cover - oversized output
            raise ValueError("cache_output_too_large")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(self.path)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:  # pragma: no cover - defensive
                pass

    @staticmethod
    def _merge_into(existing: list[dict], validated: dict) -> list[dict]:
        by_key: dict[str, dict] = {str(item["cacheKey"]): item for item in existing}
        by_key[str(validated["cacheKey"])] = validated
        return [by_key[key] for key in sorted(by_key)]

    def put(
        self,
        key: HashCacheKey,
        auto_v1: str,
        auto_v3: str | None,
        *,
        timestamp: str,
    ) -> bool:
        """Persist one record's AutoV1/AutoV3 under a native lock transaction.

        Returns ``True`` on success and ``False`` on any non-fatal failure
        (lock timeout, invalid record, write error). Never raises to callers.
        """
        hashes: dict[str, str] = {}
        if isinstance(auto_v1, str) and _HEX8_RE.fullmatch(auto_v1):
            hashes["AutoV1"] = auto_v1
        if isinstance(auto_v3, str) and _HEX12_RE.fullmatch(auto_v3):
            hashes["AutoV3"] = auto_v3
        if not hashes:
            return False
        validated = {
            "cacheKey": key.token,
            "category": key.category,
            "selectedValue": key.selected_value,
            "size": key.size,
            "modifiedNs": key.modified_ns,
            "computedAt": timestamp,
            "hashes": hashes,
        }
        lock_path = self.path.with_name(f".{self.path.name}.lock")
        try:
            with self._process_lock:
                self._acquire_file_lock(lock_path)
                try:
                    records = self._read_unlocked()
                    records = self._merge_into(records, validated)
                    # Eviction is lexicographic by cacheKey (not recency/LRU);
                    # acceptable at the default 50k-record / 16 MB bounds.
                    if len(records) > self.max_records:
                        records = records[-self.max_records :]
                    self._write_unlocked(records)
                    return True
                finally:
                    self._release_file_lock(lock_path)
        except _LockTimeoutError:
            logger.debug("[HashCache] Lock timeout writing %s", self.path)
        except (OSError, ValueError):  # pragma: no cover - defensive
            logger.debug("[HashCache] Write failed for %s", self.path)
        return False

    # -- locking -----------------------------------------------------------------

    def _acquire_file_lock(self, lock_path: Path) -> None:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(lock_path, "a+b")
        try:
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"\0")
                handle.flush()
            deadline = time.monotonic() + self.lock_timeout_seconds
            while True:
                try:
                    # Seek before locking so the locked byte range matches the
                    # byte unlocked by _release_file_lock.
                    handle.seek(0)
                    if os.name == "nt":
                        _locking_module.locking(handle.fileno(), _locking_module.LK_NBLCK, 1)
                    elif os.name == "posix":
                        _locking_module.flock(handle.fileno(), _locking_module.LOCK_EX | _locking_module.LOCK_NB)
                    else:  # pragma: no cover - unsupported platform
                        return
                    self._lock_handle = handle
                    return
                except OSError as exc:
                    if getattr(exc, "errno", None) not in _CONTENTION_ERRNOS:
                        raise
                    if time.monotonic() >= deadline:
                        raise _LockTimeoutError(errno.ETIMEDOUT, "cache lock timed out") from None
                    time.sleep(_LOCK_RETRY_SECONDS)
        except Exception:
            handle.close()
            raise

    def _release_file_lock(self, lock_path: Path) -> None:
        handle = getattr(self, "_lock_handle", None)
        if handle is None:
            return
        self._lock_handle = None
        try:
            handle.seek(0)
            if os.name == "nt":
                _locking_module.locking(handle.fileno(), _locking_module.LK_UNLCK, 1)
            elif os.name == "posix":
                _locking_module.flock(handle.fileno(), _locking_module.LOCK_UN)
        except OSError:  # pragma: no cover - defensive
            pass
        finally:
            handle.close()


def _validate_record(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    key = value.get("cacheKey")
    if not isinstance(key, str) or not key:
        return None
    if not isinstance(value.get("category"), str):
        return None
    if not isinstance(value.get("selectedValue"), str):
        return None
    if not isinstance(value.get("size"), int) or not isinstance(value.get("modifiedNs"), int):
        return None
    hashes = value.get("hashes")
    if not isinstance(hashes, dict):
        return None
    auto_v1 = hashes.get("AutoV1")
    auto_v3 = hashes.get("AutoV3")
    if not isinstance(auto_v1, str) or _HEX8_RE.fullmatch(auto_v1) is None:
        return None
    if auto_v3 is not None and (not isinstance(auto_v3, str) or _HEX12_RE.fullmatch(auto_v3) is None):
        return None
    return value


_default_cache: HashCache | None = None
_default_cache_lock = threading.Lock()


def get_hash_cache() -> HashCache:
    """Return the process-wide default :class:`HashCache` singleton."""
    global _default_cache
    with _default_cache_lock:
        if _default_cache is None:
            _default_cache = HashCache(get_hash_cache_path())
        return _default_cache


def reset_hash_cache() -> None:
    """Drop the cached singleton (used by tests to change the cache path)."""
    global _default_cache
    with _default_cache_lock:
        _default_cache = None


def cache_key_for(category: str, selected_value: str, size: int, modified_ns: int) -> HashCacheKey:
    """Build a :class:`HashCacheKey` from file identity fields."""
    return HashCacheKey(category, selected_value, size, modified_ns)


def utc_timestamp() -> str:
    """Return the current time as an ISO-8601 UTC string with a ``Z`` suffix."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


__all__ = [
    "HashCache",
    "HashCacheKey",
    "cache_key_for",
    "get_hash_cache",
    "get_hash_cache_path",
    "reset_hash_cache",
    "utc_timestamp",
]
