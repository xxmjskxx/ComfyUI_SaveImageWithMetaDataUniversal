import importlib
import json
import os
import sys

import pytest


def _paths_for_generated_files():
    mod = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.rules_writer"
    )
    base_py = os.path.dirname(os.path.dirname(os.path.abspath(mod.__file__)))
    user_captures = os.path.join(base_py, "user_rules", "user_captures.json")
    user_samplers = os.path.join(base_py, "user_rules", "user_samplers.json")
    ext_dir = os.path.join(base_py, "defs", "ext")
    gen_py = os.path.join(ext_dir, "generated_user_rules.py")
    return base_py, user_captures, user_samplers, gen_py, ext_dir


def _cleanup_generated_files():
    _, user_captures, user_samplers, gen_py, ext_dir = _paths_for_generated_files()
    for p in [user_captures, user_samplers, gen_py]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass
    # Best-effort: remove compiled cache for generated module to avoid bleed between tests
    try:
        cache_dir = os.path.join(ext_dir, "__pycache__")
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
def _ensure_cleanup():
    # Clean up before and after each test to ensure isolation
    _cleanup_generated_files()
    try:
        yield
    finally:
        _cleanup_generated_files()


def test_save_custom_rules_generates_valid_ext_and_jsons():
    nodes_mod = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes"
    )
    writer = nodes_mod.SaveCustomMetadataRules()

    rules = {
        "nodes": {
            "UnitTestNode": {
                # include a 'status' to ensure it is stripped by the writer
                "MODEL_NAME": {"field_name": "ckpt", "status": "auto"},
                "MODEL_HASH": {"field_name": "ckpt", "format": "calc_model_hash"},
                "POSITIVE_PROMPT": {"field_name": "positive"},
                "NEGATIVE_PROMPT": {"field_name": "negative"},
            }
        },
        "samplers": {"UnitTestSampler": {"positive": "positive", "negative": "negative"}},
    }

    status, = writer.save_rules(json.dumps(rules))
    # Verify status mentions saved files
    assert "user_captures.json" in status
    assert "user_samplers.json" in status
    assert "generated_user_rules.py" in status

    base_py, user_captures, user_samplers, gen_py, _ = _paths_for_generated_files()
    assert os.path.exists(user_captures)
    assert os.path.exists(user_samplers)
    assert os.path.exists(gen_py)

    # Generated file should import and expose CAPTURE_FIELD_LIST/SAMPLERS
    pkg = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.ext.generated_user_rules"
    gen_mod = importlib.import_module(pkg)
    assert hasattr(gen_mod, "CAPTURE_FIELD_LIST") and isinstance(gen_mod.CAPTURE_FIELD_LIST, dict)
    assert hasattr(gen_mod, "SAMPLERS") and isinstance(gen_mod.SAMPLERS, dict)
    # KNOWN mapping should exist with core callables
    assert hasattr(gen_mod, "KNOWN") and isinstance(gen_mod.KNOWN, dict)
    for k in [
        "calc_model_hash",
        "convert_skip_clip",
        "get_lora_model_name_stack",
        "get_lora_strength_clip_stack",
    ]:
        assert k in gen_mod.KNOWN

    # Confirm our node appears with MetaField keys
    meta_mod = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta"
    )
    assert "UnitTestNode" in gen_mod.CAPTURE_FIELD_LIST
    node_rules = gen_mod.CAPTURE_FIELD_LIST["UnitTestNode"]
    assert meta_mod.MetaField.MODEL_HASH in node_rules
    # Ensure status key was stripped from JSON
    with open(user_captures, encoding="utf-8") as f:
        uc = json.load(f)
    assert "status" not in uc["UnitTestNode"]["MODEL_NAME"]

    # Loader should merge this module when loading extensions only
    defs_mod = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs"
    )
    defs_mod.load_extensions_only()
    # In regular mode, loader should merge our generated module.
    # Under METADATA_TEST_MODE, defaults/ext loading may differ; only assert merge in regular mode.
    import os as _os
    if not _os.environ.get("METADATA_TEST_MODE"):
        assert "UnitTestNode" in defs_mod.CAPTURE_FIELD_LIST
        assert "UnitTestSampler" in defs_mod.SAMPLERS


def test_scanner_roundtrip_generates_importable_module(monkeypatch):
    # Register a simple dummy node so the scanner always finds at least one
    nodes_pkg = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes"
    )

    class DummyNode:
        @classmethod
        def INPUT_TYPES(cls):  # noqa: N802
            return {
                "required": {
                    "positive": ("STRING", {}),
                    "negative": ("STRING", {}),
                    "seed": ("INT", {}),
                }
            }

    # Temporarily register our dummy
    nodes_pkg.NODE_CLASS_MAPPINGS["UnitTestScanNode"] = DummyNode
    try:
        scanner = nodes_pkg.MetadataRuleScanner()
        result_json, _ = scanner.scan_for_rules(
            exclude_keywords="",
            include_existing=False,
            mode="existing_only",
            force_include_metafields="",
            force_include_node_class="UnitTestScanNode",
        )
        # Save via writer
        writer = nodes_pkg.SaveCustomMetadataRules()
        status, = writer.save_rules(result_json)
        assert "generated_user_rules.py" in status

        # Import generated module to ensure it compiles
        pkg = (
            "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.ext.generated_user_rules"
        )
        gen_mod = importlib.import_module(pkg)
        assert hasattr(gen_mod, "CAPTURE_FIELD_LIST") and isinstance(gen_mod.CAPTURE_FIELD_LIST, dict)
        assert isinstance(gen_mod.SAMPLERS, dict)
    finally:
        nodes_pkg.NODE_CLASS_MAPPINGS.pop("UnitTestScanNode", None)
