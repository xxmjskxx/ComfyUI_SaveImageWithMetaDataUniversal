import importlib
import json
import os
import sys

import pytest

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.version import resolve_runtime_version

PKG = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta"


def _paths_for_generated_files():
    mod = importlib.import_module(f"{PKG}.nodes.rules_writer")
    base_py = os.path.dirname(os.path.dirname(os.path.abspath(mod.__file__)))
    repo_root = os.path.dirname(base_py)
    # Writer delegates to defs.resolve_user_rules_dir(): in test mode it uses
    # <repo>/tests/_test_outputs/user_rules when present. Ensure that directory
    # exists so the resolver selects it (mirrors tests/conftest.py layout).
    test_isolated = os.path.join(repo_root, "tests/_test_outputs", "user_rules")
    if os.environ.get("METADATA_TEST_MODE"):
        os.makedirs(test_isolated, exist_ok=True)
        user_dir = test_isolated
    else:
        user_dir = os.path.join(base_py, "user_rules")
    user_captures = os.path.join(user_dir, "user_captures.json")
    user_samplers = os.path.join(user_dir, "user_samplers.json")
    version_file = os.path.join(user_dir, "rules_version.json")
    gen_py = os.path.join(base_py, "defs", "ext", "generated_user_rules.py")
    return user_captures, user_samplers, version_file, gen_py


def _cleanup_generated_files():
    for p in _paths_for_generated_files():
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass


@pytest.fixture(autouse=True)
def _ensure_cleanup():
    _cleanup_generated_files()
    try:
        yield
    finally:
        _cleanup_generated_files()


def test_save_custom_rules_writes_json_and_version_only():
    nodes_mod = importlib.import_module(f"{PKG}.nodes")
    writer = nodes_mod.SaveCustomMetadataRules()

    rules = {
        "nodes": {
            "UnitTestNode": {
                # include a 'status' to ensure it is stripped by the writer
                "MODEL_NAME": {"field_name": "ckpt", "status": "auto"},
                "MODEL_HASH": {"field_name": "ckpt", "format": "calc_model_hash"},
                "LORA_MODEL_NAME": {"selector": "get_lora_model_name_stack"},
            }
        },
        "samplers": {"UnitTestSampler": {"positive": "positive", "negative": "negative"}},
    }

    (status,) = writer.save_rules(json.dumps(rules))
    assert status.startswith("mode=overwrite"), status

    user_captures, user_samplers, version_file, gen_py = _paths_for_generated_files()
    assert os.path.exists(user_captures)
    assert os.path.exists(user_samplers)
    assert not os.path.exists(gen_py), "writer must not produce an importable Python file"
    with open(version_file, encoding="utf-8") as f:
        assert json.load(f) == {"rules_version": resolve_runtime_version()}
    with open(user_captures, encoding="utf-8") as f:
        assert "status" not in json.load(f)["UnitTestNode"]["MODEL_NAME"]

    defs_mod = importlib.import_module(f"{PKG}.defs")
    meta_mod = importlib.import_module(f"{PKG}.defs.meta")
    defs_mod.load_user_definitions()
    assert defs_mod.LOADED_RULES_VERSION == resolve_runtime_version()
    node_rules = defs_mod.CAPTURE_FIELD_LIST["UnitTestNode"]
    assert callable(node_rules[meta_mod.MetaField.MODEL_HASH]["format"])
    assert callable(node_rules[meta_mod.MetaField.LORA_MODEL_NAME]["selector"])
    assert "UnitTestSampler" in defs_mod.SAMPLERS


def test_loader_never_imports_generated_user_rules_py():
    _, _, _, gen_py = _paths_for_generated_files()
    with open(gen_py, "w", encoding="utf-8") as f:
        f.write("raise RuntimeError('generated_user_rules.py must not be imported')\n")

    defs_mod = importlib.import_module(f"{PKG}.defs")
    defs_mod.load_user_definitions()
    defs_mod.load_extensions_only()
    assert not any(name.endswith("ext.generated_user_rules") for name in sys.modules)


def test_scanner_roundtrip_loads_as_json():
    # Register a simple dummy node so the scanner always finds at least one
    nodes_pkg = importlib.import_module(f"{PKG}.nodes")
    comfy_nodes = importlib.import_module("nodes")

    class DummyNode:
        @classmethod
        def INPUT_TYPES(cls):  # noqa: N802
            return {
                "required": {
                    "positive": ("STRING", {}),
                    "negative": ("STRING", {}),
                    "clip": ("CLIP", {}),
                    "seed": ("INT", {}),
                }
            }

    nodes_pkg.NODE_CLASS_MAPPINGS["UnitTestClipEncode"] = DummyNode
    comfy_nodes.NODE_CLASS_MAPPINGS["UnitTestClipEncode"] = DummyNode
    try:
        scanner = nodes_pkg.MetadataRuleScanner()
        result_json, _ = scanner.scan_for_rules(
            exclude_keywords="",
            include_existing=False,
            mode="all",  # 'existing_only' skips forced nodes not in baseline definitions
            force_include_metafields="",
            force_include_node_class="UnitTestClipEncode",
        )
        parsed = json.loads(result_json)
        node_rules = parsed["nodes"].get("UnitTestClipEncode")
        assert node_rules["POSITIVE_PROMPT"].get("inline_lora_candidate") is True
        assert node_rules["NEGATIVE_PROMPT"].get("inline_lora_candidate") is True
        writer = nodes_pkg.SaveCustomMetadataRules()
        (status,) = writer.save_rules(result_json)
        assert status.startswith("mode=overwrite"), status

        defs_mod = importlib.import_module(f"{PKG}.defs")
        defs_mod.load_user_definitions()
        assert "UnitTestClipEncode" in defs_mod.CAPTURE_FIELD_LIST
    finally:
        nodes_pkg.NODE_CLASS_MAPPINGS.pop("UnitTestClipEncode", None)
        comfy_nodes.NODE_CLASS_MAPPINGS.pop("UnitTestClipEncode", None)
