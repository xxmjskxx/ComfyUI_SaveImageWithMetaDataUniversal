"""Tests for Civitai AutoV1/V2/V3 + SHA-256 hashing and the central cache."""

from __future__ import annotations

import hashlib
import json
import struct

import pytest

from saveimage_unimeta.defs.hash_values import (
    HASH_PRIORITY,
    HashRecord,
    hash_record_from_mapping,
    hash_record_to_mapping,
    normalize_hash,
)
from saveimage_unimeta.utils.hash import calc_all_hashes, calc_auto_v1
from saveimage_unimeta.utils.hash_cache import HashCache, cache_key_for


def _write_safetensors(tmp_path, payload: bytes, name: str = "model.safetensors") -> str:
    header = json.dumps({"test": "tensor"}).encode("utf-8")
    data = struct.pack("<Q", len(header)) + header + payload
    path = tmp_path / name
    path.write_bytes(data)
    return str(path)


# --------------------------------------------------------------------------- #
# calc_all_hashes
# --------------------------------------------------------------------------- #


def test_calc_all_hashes_safetensors_payload(tmp_path) -> None:
    payload = b"tensor-data-bytes" * 100
    header = json.dumps({"test": "tensor"}).encode("utf-8")
    data = struct.pack("<Q", len(header)) + header + payload
    path = _write_safetensors(tmp_path, payload)

    result = calc_all_hashes(path)
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert result["auto_v2"] == result["sha256"][:10]
    assert result["auto_v3"] == hashlib.sha256(payload).hexdigest()[:12]


def test_calc_all_hashes_ckpt_has_no_auto_v3(tmp_path) -> None:
    data = b"pickle-like-bytes" * 100
    path = tmp_path / "model.ckpt"
    path.write_bytes(data)

    result = calc_all_hashes(str(path))
    assert result["auto_v3"] is None
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert result["auto_v2"] == result["sha256"][:10]


def test_calc_all_hashes_malformed_safetensors_has_no_auto_v3(tmp_path) -> None:
    path = tmp_path / "bad.safetensors"
    path.write_bytes(struct.pack("<Q", 4) + b"not!")  # invalid JSON header

    result = calc_all_hashes(str(path))
    assert result["auto_v3"] is None


def test_auto_v1_offset_window(tmp_path) -> None:
    filler = b"\x00" * 0x100000  # 1 MiB
    window = b"\xab" * 0x10000  # 64 KiB at the AutoV1 offset
    tail = b"\x01\x02\x03"
    data = filler + window + tail
    path = tmp_path / "big.bin"
    path.write_bytes(data)

    result = calc_all_hashes(str(path))
    assert result["auto_v1"] == hashlib.sha256(window).hexdigest()[:8]
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert result["auto_v3"] is None


def test_small_file_auto_v1_is_sha256_of_empty(tmp_path) -> None:
    path = tmp_path / "tiny.safetensors"
    path.write_bytes(b"tiny")

    result = calc_all_hashes(str(path))
    assert result["auto_v1"] == hashlib.sha256(b"").hexdigest()[:8]


def test_calc_auto_v1_matches_streaming(tmp_path) -> None:
    filler = b"\x00" * 0x100000
    window = b"\xcd" * 0x10000
    tail = b"\xff"
    data = filler + window + tail
    path = tmp_path / "big.bin"
    path.write_bytes(data)

    assert calc_auto_v1(str(path)) == hashlib.sha256(window).hexdigest()[:8]
    assert calc_auto_v1(str(path)) == calc_all_hashes(str(path))["auto_v1"]


# --------------------------------------------------------------------------- #
# hash_values normalization
# --------------------------------------------------------------------------- #


def test_normalize_hash() -> None:
    assert normalize_hash("abc123", length=6) == "abc123"
    assert normalize_hash("ABC123", length=6) == "abc123"
    assert normalize_hash("xyz", length=6) is None
    assert normalize_hash("abc12g", length=6) is None  # 'g' is not hex
    assert normalize_hash(123456, length=6) is None


def test_hash_record_round_trip() -> None:
    record = HashRecord(sha256="a" * 64, auto_v3="b" * 12, auto_v2="c" * 10, auto_v1="d" * 8)
    mapping = hash_record_to_mapping(record)
    assert mapping == {"SHA256": "a" * 64, "AutoV3": "b" * 12, "AutoV2": "c" * 10, "AutoV1": "d" * 8}
    assert hash_record_from_mapping(mapping) == record


def test_hash_record_from_mapping_rejects_malformed() -> None:
    assert hash_record_from_mapping({"AutoV2": "zzzz"}) is None
    assert hash_record_from_mapping("nope") is None
    assert hash_record_from_mapping({}) is None
    assert hash_record_from_mapping(None) is None


def test_hash_priority_order() -> None:
    assert [name for name, _field, _length in HASH_PRIORITY] == [
        "SHA256",
        "AutoV3",
        "AutoV2",
        "AutoV1",
    ]


# --------------------------------------------------------------------------- #
# HashCache
# --------------------------------------------------------------------------- #


def test_hash_cache_round_trip(tmp_path) -> None:
    cache = HashCache(str(tmp_path / "cache.json"))
    key = cache_key_for("loras", "my-lora.safetensors", 12345, 67890)
    assert cache.put(key, "abcdef12", "abcdef123456", timestamp="2026-09-03T00:00:00Z") is True
    assert cache.get(key) == {"AutoV1": "abcdef12", "AutoV3": "abcdef123456"}


def test_hash_cache_miss(tmp_path) -> None:
    cache = HashCache(str(tmp_path / "cache.json"))
    key = cache_key_for("loras", "my-lora.safetensors", 12345, 67890)
    assert cache.get(key) is None


def test_hash_cache_invalidated_by_size_and_mtime(tmp_path) -> None:
    cache = HashCache(str(tmp_path / "cache.json"))
    k1 = cache_key_for("loras", "x.safetensors", 100, 200)
    cache.put(k1, "abcdef12", "abcdef123456", timestamp="t")
    assert cache.get(cache_key_for("loras", "x.safetensors", 101, 200)) is None
    assert cache.get(cache_key_for("loras", "x.safetensors", 100, 201)) is None


def test_hash_cache_tolerates_corrupt_file(tmp_path) -> None:
    path = tmp_path / "cache.json"
    path.write_bytes(b"{ not valid json")
    cache = HashCache(str(path))
    key = cache_key_for("loras", "x.safetensors", 100, 200)
    assert cache.get(key) is None  # no crash
    assert cache.put(key, "abcdef12", "abcdef123456", timestamp="t") is True
    assert cache.get(key) == {"AutoV1": "abcdef12", "AutoV3": "abcdef123456"}


def test_hash_cache_key_is_deterministic() -> None:
    k1 = cache_key_for("loras", "a.safetensors", 1, 2)
    k2 = cache_key_for("loras", "a.safetensors", 1, 2)
    k3 = cache_key_for("loras", "b.safetensors", 1, 2)
    assert k1.token == k2.token
    assert k1.token != k3.token
    assert "a.safetensors" not in k1.token  # privacy-safe: no plaintext identity


def test_hash_cache_rejects_invalid_hashes(tmp_path) -> None:
    cache = HashCache(str(tmp_path / "cache.json"))
    key = cache_key_for("loras", "x.safetensors", 100, 200)
    assert cache.put(key, "too-short", "also-bad", timestamp="t") is False


# --------------------------------------------------------------------------- #
# Hash detail enrichment
# --------------------------------------------------------------------------- #


def test_hash_detail_enriched_with_auto_hashes(monkeypatch) -> None:
    from saveimage_unimeta import capture as capture_mod

    record = HashRecord(sha256="a" * 64, auto_v3="b" * 12, auto_v2="c" * 10, auto_v1="d" * 8)
    monkeypatch.setitem(capture_mod._hashfmt._FULL_HASH_RECORDS, "c" * 10, record)

    pnginfo_dict = {"Model": "model.safetensors", "Model hash": "c" * 10}
    capture_mod.Capture.add_hash_detail_section(pnginfo_dict)

    detail = json.loads(pnginfo_dict["Hash detail"])
    assert detail["model"]["hash"] == "c" * 10
    assert detail["model"]["autoV1"] == "d" * 8
    assert detail["model"]["autoV2"] == "c" * 10
    assert detail["model"]["autoV3"] == "b" * 12
    assert detail["model"]["sha256"] == "a" * 64


def test_hash_file_skips_full_hashes_when_detail_disabled(tmp_path, monkeypatch) -> None:
    from saveimage_unimeta.defs import formatters

    model_file = tmp_path / "model.ckpt"
    model_file.write_bytes(b"model-bytes" * 100)

    calls: list[str] = []
    monkeypatch.setattr(
        formatters,
        "_full_hashes_for_path",
        lambda kind, path: calls.append(path) or None,
    )

    monkeypatch.setenv("METADATA_NO_HASH_DETAIL", "1")
    formatters._hash_file("model", str(model_file), truncate=10)
    assert calls == []

    monkeypatch.delenv("METADATA_NO_HASH_DETAIL")
    formatters._hash_file("model", str(model_file), truncate=10)
    assert calls == [str(model_file)]
