"""Shared version helpers for UniMeta runtime and rule stamping."""
from __future__ import annotations

import importlib.metadata
import os


def _read_pyproject_version() -> str | None:  # pragma: no cover - simple IO
    toml_loader = None  # type: ignore
    try:
        import tomllib as toml_loader  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        try:
            import tomli as toml_loader  # type: ignore
        except ModuleNotFoundError:
            return None
    try:
        import pathlib

        here = pathlib.Path(__file__).resolve()
        for parent in here.parents:
            pyproject = parent / "pyproject.toml"
            if pyproject.is_file():
                with pyproject.open("rb") as fh:
                    data = toml_loader.load(fh)  # type: ignore[arg-type]
                return (
                    data.get("project", {}).get("version")
                    or data.get("tool", {}).get("poetry", {}).get("version")
                    or None
                )
    except (OSError, KeyError, ValueError):
        return None
    return None


try:
    _dist_version = importlib.metadata.version("SaveImageWithMetaDataUniversal")
except importlib.metadata.PackageNotFoundError:
    _dist_version = None
_pyproj_version = _read_pyproject_version()
_RESOLVED_VERSION = (
    _pyproj_version
    if (_pyproj_version and (_dist_version is None or _pyproj_version != _dist_version))
    else (_dist_version or _pyproj_version or "unknown")
)


def resolve_runtime_version() -> str:
    """Return the effective version string, honoring env overrides."""

    override = os.environ.get("METADATA_VERSION_OVERRIDE", "").strip()
    if override:
        return override
    return _RESOLVED_VERSION or "unknown"
