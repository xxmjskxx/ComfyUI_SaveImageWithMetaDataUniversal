import json
import pytest

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes import MetadataRuleScanner


class DummyNode:
    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        return {"required": {"foo_strength": ("FLOAT", {}), "foo_name": ("STRING", {})}}


def _register_temp(mapping, name, cls):
    mapping[name] = cls
    return lambda: mapping.pop(name, None)


def test_forced_inclusion_overrides_exclusion():
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta import nodes as nodes_pkg

    undo = _register_temp(nodes_pkg.NODE_CLASS_MAPPINGS, "MaskAnalysisNode", DummyNode)
    try:
        scanner = MetadataRuleScanner()
        result_json, diff = scanner.scan_for_rules(
            exclude_keywords="mask",
            include_existing=False,
            mode="new_only",
            force_include_metafields="",
            force_include_node_class="MaskAnalysisNode",
        )
        payload = json.loads(result_json)
        assert "MaskAnalysisNode" in payload["nodes"]
        assert "forced_node_classes" in payload["summary"]
        assert "MaskAnalysisNode" in payload["summary"]["forced_node_classes"], diff
    finally:
        undo()


def test_forced_inclusion_existing_only_mode():
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta import nodes as nodes_pkg

    undo = _register_temp(nodes_pkg.NODE_CLASS_MAPPINGS, "TransientDummyNode", DummyNode)
    try:
        scanner = MetadataRuleScanner()
        result_json, _ = scanner.scan_for_rules(
            exclude_keywords="",
            include_existing=False,
            mode="existing_only",
            force_include_metafields="",
            force_include_node_class="TransientDummyNode",
        )
        payload = json.loads(result_json)
        assert "TransientDummyNode" in payload["nodes"]
    finally:
        undo()


@pytest.mark.parametrize(
    "value", ["ClassOne,ClassTwo", "ClassOne\nClassTwo", "ClassOne, ClassTwo\n"],
)
def test_multiple_forced_variants(value):
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta import nodes as nodes_pkg

    u1 = _register_temp(nodes_pkg.NODE_CLASS_MAPPINGS, "ClassOne", DummyNode)
    u2 = _register_temp(nodes_pkg.NODE_CLASS_MAPPINGS, "ClassTwo", DummyNode)
    try:
        scanner = MetadataRuleScanner()
        result_json, _ = scanner.scan_for_rules(
            exclude_keywords="irrelevant",
            include_existing=False,
            mode="existing_only",
            force_include_metafields="",
            force_include_node_class=value,
        )
        payload = json.loads(result_json)
        forced = set(payload["summary"].get("forced_node_classes", []))
        assert {"ClassOne", "ClassTwo"}.issubset(forced)
        # Both nodes should appear even though mode would normally exclude them
        assert "ClassOne" in payload["nodes"] and "ClassTwo" in payload["nodes"]
    finally:
        u1()
        u2()


def test_forced_node_empty_object_emitted():
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta import nodes as nodes_pkg

    undo = _register_temp(nodes_pkg.NODE_CLASS_MAPPINGS, "UnmatchedNode", DummyNode)
    try:
        scanner = MetadataRuleScanner()
        result_json, _ = scanner.scan_for_rules(
            exclude_keywords="unmatched",
            include_existing=False,
            mode="new_only",
            force_include_metafields="",
            force_include_node_class="UnmatchedNode",
        )
        payload = json.loads(result_json)
        assert "UnmatchedNode" in payload["nodes"]
        assert payload["nodes"]["UnmatchedNode"] == {}, "Expected empty object for unmatched forced node"
    finally:
        undo()
