import importlib
import json

import pytest

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes import MetadataRuleScanner


@pytest.fixture(name="_scanner_env")
def fixture_scanner_env():
    """Register a temporary loader node used to test priority keyword ordering."""

    nodes_pkg = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes"
    )
    global_nodes = None
    try:  # pragma: no cover - optional global nodes module
        global_nodes = importlib.import_module("nodes")
    except ImportError:  # noqa: TRY301 - compatibility shim when ComfyUI modules absent
        global_nodes = None

    class PriorityLoRALoader:
        """Minimal loader exposing clip/model fields for priority sorting tests."""

        @classmethod
        def INPUT_TYPES(cls):  # noqa: N802
            return {
                "required": {
                    "lora_name": ("STRING", {}),
                    "alpha_strength": ("FLOAT", {}),
                    "clip_strength": ("FLOAT", {}),
                    "clipped_value": ("FLOAT", {}),
                    "weight_plain": ("FLOAT", {}),
                }
            }

    nodes_pkg.NODE_CLASS_MAPPINGS["PriorityLoRALoader"] = PriorityLoRALoader
    undo_global = None
    if global_nodes is not None and hasattr(global_nodes, "NODE_CLASS_MAPPINGS"):
        global_nodes.NODE_CLASS_MAPPINGS["PriorityLoRALoader"] = PriorityLoRALoader  # type: ignore[attr-defined]

        def _undo_global():
            global_nodes.NODE_CLASS_MAPPINGS.pop("PriorityLoRALoader", None)  # type: ignore[attr-defined]

        undo_global = _undo_global

    yield "PriorityLoRALoader"

    nodes_pkg.NODE_CLASS_MAPPINGS.pop("PriorityLoRALoader", None)
    if undo_global:
        undo_global()


def test_priority_keywords_rank_clip_fields(_scanner_env):
    scanner = MetadataRuleScanner()
    result_json, _ = scanner.scan_for_rules(
        exclude_keywords="",
        include_existing=False,
        mode="all",
        force_include_metafields="",
        force_include_node_class=_scanner_env,
    )
    payload = json.loads(result_json)
    node_entries = payload.get("nodes", {}).get(_scanner_env)
    assert node_entries, payload
    clip_entry = node_entries.get("LORA_STRENGTH_CLIP")
    assert clip_entry and "fields" in clip_entry, node_entries
    fields = clip_entry["fields"]
    assert fields == ["clip_strength", "clipped_value"], fields


def test_priority_keywords_keep_fallback_when_no_clip_fields():
    nodes_pkg = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes"
    )
    global_nodes = None
    try:
        global_nodes = importlib.import_module("nodes")
    except ImportError:  # pragma: no cover - optional runtime module
        global_nodes = None

    class ModelOnlyLoader:
        @classmethod
        def INPUT_TYPES(cls):  # noqa: N802
            return {
                "required": {
                    "lora_name": ("STRING", {}),
                    "alpha_strength": ("FLOAT", {}),
                    "weight_plain": ("FLOAT", {}),
                }
            }

    class_name = "ModelOnlyLoader"
    nodes_pkg.NODE_CLASS_MAPPINGS[class_name] = ModelOnlyLoader
    undo_global = None
    if global_nodes is not None and hasattr(global_nodes, "NODE_CLASS_MAPPINGS"):
        global_nodes.NODE_CLASS_MAPPINGS[class_name] = ModelOnlyLoader  # type: ignore[attr-defined]

        def _undo_global():
            global_nodes.NODE_CLASS_MAPPINGS.pop(class_name, None)  # type: ignore[attr-defined]

        undo_global = _undo_global

    try:
        scanner = MetadataRuleScanner()
        result_json, _ = scanner.scan_for_rules(
            exclude_keywords="",
            include_existing=False,
            mode="all",
            force_include_metafields="",
            force_include_node_class=class_name,
        )
        payload = json.loads(result_json)
        node_entries = payload.get("nodes", {}).get(class_name)
        assert node_entries, payload
        clip_entry = node_entries.get("LORA_STRENGTH_CLIP")
        assert clip_entry and "fields" in clip_entry, node_entries
        assert clip_entry["fields"] == ["alpha_strength", "weight_plain"]
    finally:
        nodes_pkg.NODE_CLASS_MAPPINGS.pop(class_name, None)
        if undo_global:
            undo_global()
