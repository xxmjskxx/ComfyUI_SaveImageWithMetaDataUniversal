import json
import logging
import sys
from pathlib import Path

import pytest

try:  # Allow execution inside editable installs or custom_nodes checkouts
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.utils import deserialize as deserialize_mod
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField
except ModuleNotFoundError:  # pragma: no cover - repo-local fallback for pytest
    pkg_root = Path(__file__).resolve().parents[2]
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.utils import deserialize as deserialize_mod
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField


@pytest.fixture()
def restore_warning_toggle(monkeypatch):
    """Ensure WARNINGS_ENABLED flips back after tests toggle it."""

    original = deserialize_mod.WARNINGS_ENABLED
    monkeypatch.setattr(deserialize_mod, "WARNINGS_ENABLED", original, raising=False)
    return lambda value: monkeypatch.setattr(deserialize_mod, "WARNINGS_ENABLED", value, raising=False)


# Ensure enums + callables survive a round-trip through JSON files processed by deserialize_input.
def test_deserialize_input_restores_enums_and_functions(tmp_path):
    capture_payload = {
        "TestSampler": {
            "STEPS": "calc_model_hash",
            "CFG": "CFG",
            "EXTRA": ["is_positive_prompt", "SEED"],
            "CALL": "calc_model_hash()",
        }
    }
    json_path = tmp_path / "user_captures.json"
    json_path.write_text(json.dumps(capture_payload), encoding="utf-8")

    restored = deserialize_mod.deserialize_input(str(json_path))
    node_cfg = restored["TestSampler"]

    assert node_cfg[MetaField.STEPS] is deserialize_mod.FUNCTIONS["calc_model_hash"]
    assert node_cfg[MetaField.CFG] is MetaField.CFG
    assert node_cfg["EXTRA"][0] is deserialize_mod.FUNCTIONS["is_positive_prompt"]
    assert node_cfg["EXTRA"][1] is MetaField.SEED
    assert node_cfg["CALL"] is deserialize_mod.FUNCTIONS["calc_model_hash"]


# Confirm non-dict payloads raise with helpful pretty-printed content.
def test_deserialize_input_rejects_non_dict(tmp_path):
    json_path = tmp_path / "bad.json"
    json_path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        deserialize_mod.deserialize_input(str(json_path))

    assert "Captures file must deserialize" in str(exc.value)
    assert "list" in str(exc.value)


# Exercise warning paths for unknown enums, ints, and callable names.
def test_restore_values_logs_unknown_tokens(monkeypatch, caplog):
    caplog.set_level(logging.WARNING)
    monkeypatch.setattr(deserialize_mod, "WARNINGS_ENABLED", True, raising=False)

    payload = {"UnknownEnum": "mystery", 999: "another"}
    deserialize_mod.restore_values(payload)

    assert "Unknown enum key 'UnknownEnum'" in caplog.text
    assert "Unknown enum int '999'" in caplog.text
    assert "Unknown function or enum value 'mystery'" in caplog.text


# Cover format_config pretty-print branches for dict/list/callable/meta/string scalars.
def test_format_config_renders_human_readable_strings():
    sample = {
        MetaField.STEPS: deserialize_mod.FUNCTIONS["calc_model_hash"],
        "nested": ["plain", MetaField.CFG],
    }

    formatted = deserialize_mod.format_config(sample)

    assert "MetaField.STEPS" in formatted
    assert "calc_model_hash" in formatted
    assert "MetaField.CFG" in formatted


# Validate integer MetaField keys are restored even outside of JSON contexts.
def test_restore_values_accepts_int_enum_keys():
    payload = {MetaField.STEPS.value: "calc_model_hash"}

    restored = deserialize_mod.restore_values(payload)

    assert MetaField.STEPS in restored
    assert restored[MetaField.STEPS] is deserialize_mod.FUNCTIONS["calc_model_hash"]
