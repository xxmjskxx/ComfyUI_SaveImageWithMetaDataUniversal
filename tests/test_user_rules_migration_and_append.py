import importlib
import json
import os
import shutil
import time

import pytest

# Helper paths adapted to new user_rules directory, with legacy fallback for migration test

def _base_dirs():
    mod = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.rules_writer"
    )
    base = os.path.dirname(os.path.dirname(os.path.abspath(mod.__file__)))  # saveimage_unimeta
    user_rules = os.path.join(base, "user_rules")
    legacy_py = os.path.join(base, "py")
    ext_dir = os.path.join(base, "defs", "ext")
    return base, user_rules, legacy_py, ext_dir


def _rules_paths():
    _, user_rules, legacy_py, ext_dir = _base_dirs()
    return (
        os.path.join(user_rules, "user_captures.json"),
        os.path.join(user_rules, "user_samplers.json"),
        os.path.join(ext_dir, "generated_user_rules.py"),
        legacy_py,
    )


def _cleanup():
    captures, samplers, gen_py, legacy_py = _rules_paths()
    for p in [captures, samplers, gen_py]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass
    # Clear legacy dir remnants
    if os.path.isdir(legacy_py):
        for name in ("user_captures.json", "user_samplers.json"):
            lp = os.path.join(legacy_py, name)
            try:
                if os.path.exists(lp):
                    os.remove(lp)
            except OSError:
                pass
    # Purge generated module cache
    try:
        cache_dir = os.path.join(os.path.dirname(gen_py), "__pycache__")
        if os.path.isdir(cache_dir):
            for f in os.listdir(cache_dir):
                if f.startswith("generated_user_rules."):
                    try:
                        os.remove(os.path.join(cache_dir, f))
                    except OSError:
                        pass
    except OSError:
        pass


@pytest.fixture(autouse=True)
def isolate():
    _cleanup()
    yield
    _cleanup()


def test_migration_from_legacy_py(monkeypatch):
    captures, samplers, gen_py, legacy_py = _rules_paths()
    os.makedirs(legacy_py, exist_ok=True)
    # Create legacy files simulating prior layout
    with open(os.path.join(legacy_py, "user_captures.json"), "w", encoding="utf-8") as f:
        json.dump({"LegacyNode": {"MODEL_NAME": {"field_name": "ckpt"}}}, f)
    with open(os.path.join(legacy_py, "user_samplers.json"), "w", encoding="utf-8") as f:
        json.dump({"LegacySampler": {"positive": "pos"}}, f)

    defs_mod = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs"
    )
    # Trigger load which should migrate legacy json
    defs_mod.load_user_definitions()

    assert os.path.exists(captures), "Legacy user_captures.json not migrated"
    assert os.path.exists(samplers), "Legacy user_samplers.json not migrated"
    # Ensure legacy originals removed
    assert not os.path.exists(os.path.join(legacy_py, "user_captures.json"))
    assert not os.path.exists(os.path.join(legacy_py, "user_samplers.json"))


def test_append_future_placeholder_logic(monkeypatch):
    """Placeholder test to stake out counts for future append implementation.

    Currently writer overwrites; this ensures we have a baseline to compare once append_new mode lands.
    """
    nodes_mod = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes"
    )
    writer = nodes_mod.SaveCustomMetadataRules()

    base_rules = {
        "nodes": {
            "AppendNode": {
                "MODEL_NAME": {"field_name": "ckpt"},
                "POSITIVE_PROMPT": {"field_name": "positive"},
            }
        },
        "samplers": {"AppendSampler": {"positive": "positive"}},
    }
    status, = writer.save_rules(json.dumps(base_rules))
    assert "user_captures.json" in status
    assert "user_samplers.json" in status

    # Overwrite with extra metafield (simulating what append_new would later treat differently)
    updated_rules = {
        "nodes": {
            "AppendNode": {
                "MODEL_NAME": {"field_name": "ckpt"},
                "POSITIVE_PROMPT": {"field_name": "positive"},
                "NEGATIVE_PROMPT": {"field_name": "negative"},
            }
        },
        "samplers": {"AppendSampler": {"positive": "positive", "negative": "negative"}},
    }
    status2, = writer.save_rules(json.dumps(updated_rules))
    # Since current logic overwrites, final file should include NEGATIVE_PROMPT and sampler negative role
    captures, samplers, *_ = _rules_paths()
    with open(captures, encoding="utf-8") as f:
        cap_json = json.load(f)
    assert "NEGATIVE_PROMPT" in cap_json["AppendNode"]
    with open(samplers, encoding="utf-8") as f:
        sam_json = json.load(f)
    assert "negative" in sam_json["AppendSampler"]

    # Provide assertion hook for later (when append_new added we will branch test behavior)
    assert "Successfully" in status2 or "saved" in status2
