from __future__ import annotations

import importlib.util
import logging
import sys
import types
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
INIT_FILE = ROOT / "__init__.py"
MODULE_ALIASES = [
    "custom_nodes.ComfyUI_SaveImageWithMetaDataUniversal",
    "ComfyUI_SaveImageWithMetaDataUniversal",
]
SENTINEL = "ComfyUI_SaveImageWithMetaDataUniversal_startup_logged"


def _load_module(module_name: str):
    spec = importlib.util.spec_from_file_location(
        module_name,
        INIT_FILE,
        submodule_search_locations=[str(ROOT)],
    )
    if spec is None:
        raise RuntimeError(f"Unable to create spec for {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    loader = spec.loader
    assert loader is not None
    loader.exec_module(module)
    return module


def test_startup_message_emitted_once(monkeypatch: pytest.MonkeyPatch, caplog):
    registry_logger = logging.getLogger("_startup_registry")
    if hasattr(registry_logger, SENTINEL):
        delattr(registry_logger, SENTINEL)

    saved_modules: dict[str, ModuleType | None] = {}
    for alias in MODULE_ALIASES:
        saved_modules[alias] = sys.modules.pop(alias, None)

    saved_custom_nodes = sys.modules.get("custom_nodes")
    if saved_custom_nodes is None:
        custom_nodes_pkg = types.ModuleType("custom_nodes")
        custom_nodes_pkg.__path__ = []
        sys.modules["custom_nodes"] = custom_nodes_pkg
        created_custom_nodes = True
    else:
        created_custom_nodes = False

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("METADATA_TEST_MODE", raising=False)

    try:
        with caplog.at_level("INFO"):
            for alias in MODULE_ALIASES:
                _load_module(alias)
    finally:
        for alias, module in saved_modules.items():
            if module is not None:
                sys.modules[alias] = module
            else:
                sys.modules.pop(alias, None)
        if created_custom_nodes:
            sys.modules.pop("custom_nodes", None)
        elif isinstance(saved_custom_nodes, ModuleType):
            sys.modules["custom_nodes"] = saved_custom_nodes
        if hasattr(registry_logger, SENTINEL):
            delattr(registry_logger, SENTINEL)

    banner_logs = [
        record.getMessage()
        for record in caplog.records
        if "nodes successfully" in record.getMessage()
    ]
    assert len(banner_logs) == 1
