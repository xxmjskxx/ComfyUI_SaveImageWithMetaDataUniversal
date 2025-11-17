"""Provides version resolution for the `saveimage_unimeta` package.

This module is responsible for determining the version of the package at
runtime. It attempts to read the version from the package metadata and falls
back to parsing the `pyproject.toml` file. It also allows for overriding the
version through an environment variable, which is useful for testing and
development.
"""
from __future__ import annotations

import importlib.metadata
from importlib import import_module
import os
from types import ModuleType


def _read_pyproject_version() -> str | None:
    """Read the version from the `pyproject.toml` file.

    This function searches for a `pyproject.toml` file in the parent
    directories of the current file, parses it, and extracts the version
    string from either the `[project]` or `[tool.poetry]` section.

    Returns:
        str | None: The version string, or None if the file cannot be found
            or the version is not specified.
    """
    toml_loader: ModuleType | None = None
    for module_name in ("tomllib", "tomli"):
        try:
            toml_loader = import_module(module_name)
            break
        except ModuleNotFoundError:
            continue
    if toml_loader is None:
        return None
    try:
        import pathlib

        here = pathlib.Path(__file__).resolve()
        for parent in here.parents:
            pyproject = parent / "pyproject.toml"
            if pyproject.is_file():
                with pyproject.open("rb") as fh:
                    data = toml_loader.load(fh)
                return (
                    data.get("project", {}).get("version")
                    or data.get("tool", {}).get("poetry", {}).get("version")
                    or None
                )
    except (OSError, KeyError, ValueError):
        return None
    return None


try:
    _dist_version: str | None = importlib.metadata.version("SaveImageWithMetaDataUniversal")
except importlib.metadata.PackageNotFoundError:
    _dist_version = None
_pyproj_version = _read_pyproject_version()
if _pyproj_version and (_dist_version is None or _pyproj_version != _dist_version):
    _RESOLVED_VERSION: str = _pyproj_version
else:
    _RESOLVED_VERSION = _dist_version or _pyproj_version or "unknown"


def resolve_runtime_version() -> str:
    """Resolve the runtime version of the package.

    This function determines the effective version string for the package. It
    first checks for a version override from the `METADATA_VERSION_OVERRIDE`
    environment variable. If no override is present, it returns the version
    resolved from the package metadata or `pyproject.toml`.

    Returns:
        str: The resolved version string, or "unknown" if the version cannot
            be determined.
    """

    override = os.environ.get("METADATA_VERSION_OVERRIDE", "").strip()
    if override:
        return override
    return _RESOLVED_VERSION or "unknown"
