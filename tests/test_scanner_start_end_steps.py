import json
import importlib


def test_scanner_detects_start_end_step(monkeypatch):
    """Ensure newly added START_STEP / END_STEP heuristic rules propose fields for a sampler-like node.

    We inject a dummy node whose class name contains 'Sampler' and exposes integer inputs
    'start_step' and 'end_step'. The scanner should emit suggestions mapping these to the
    START_STEP and END_STEP MetaFields (string keys in JSON output).
    """
    # Import scanner module
    scanner_mod = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.scanner"
    )

    # Build dummy sampler-like node class
    class SegmentedSamplerTest:
        @classmethod
        def INPUT_TYPES(cls):  # mimic ComfyUI node API shape
            return {
                "required": {
                    "start_step": ("INT", {"default": 0, "min": 0, "max": 100}),
                    "end_step": ("INT", {"default": 10, "min": 1, "max": 100}),
                },
                "optional": {},
            }

    # Inject into NODE_CLASS_MAPPINGS
    node_map = scanner_mod.nodes.NODE_CLASS_MAPPINGS
    prev = node_map.get("SegmentedSamplerTest")
    node_map["SegmentedSamplerTest"] = SegmentedSamplerTest

    try:
        scanner = scanner_mod.MetadataRuleScanner()
        # Use mode 'all' to simplify inclusion logic; include_existing=False (default) okay for new node
        result_json, _diff = scanner.scan_for_rules(mode="all")
        data = json.loads(result_json)
        assert "SegmentedSamplerTest" in data["nodes"], "Dummy sampler node missing from scan output"
        node_rules = data["nodes"]["SegmentedSamplerTest"]
        assert "START_STEP" in node_rules, "START_STEP metafield not suggested"
        assert "END_STEP" in node_rules, "END_STEP metafield not suggested"
        # Basic structure sanity: each entry should have at least a field_name
        assert node_rules["START_STEP"].get("field_name") in {"start_step", "start"}
        assert node_rules["END_STEP"].get("field_name") in {"end_step", "end"}
    finally:
        # Restore mapping to avoid side effects
        if prev is not None:
            node_map["SegmentedSamplerTest"] = prev
        else:
            node_map.pop("SegmentedSamplerTest", None)


def test_scanner_does_not_detect_start_end_for_non_sampler(monkeypatch):
    """Ensure START_STEP / END_STEP heuristics do NOT fire for a node whose class name lacks required keywords.

    The heuristic requires at least one of: 'sampler', 'wan', 'range' in the class name. We simulate a config
    node that happens to expose 'start_step' and 'end_step' parameters but is not a sampler.
    """
    scanner_mod = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.scanner"
    )

    class SegmentConfigHelper:
        @classmethod
        def INPUT_TYPES(cls):
            return {
                "required": {
                    "start_step": ("INT", {"default": 1}),
                    "end_step": ("INT", {"default": 5}),
                },
                "optional": {},
            }

    node_map = scanner_mod.nodes.NODE_CLASS_MAPPINGS
    prev = node_map.get("SegmentConfigHelper")
    node_map["SegmentConfigHelper"] = SegmentConfigHelper
    try:
        scanner = scanner_mod.MetadataRuleScanner()
        result_json, _ = scanner.scan_for_rules(mode="all")
        data = json.loads(result_json)
        # Either the node is absent (no suggestions at all) OR present without START/END suggestions.
        if "SegmentConfigHelper" in data["nodes"]:
            node_rules = data["nodes"]["SegmentConfigHelper"]
            assert "START_STEP" not in node_rules, "START_STEP incorrectly suggested for non-sampler node"
            assert "END_STEP" not in node_rules, "END_STEP incorrectly suggested for non-sampler node"
    finally:
        if prev is not None:
            node_map["SegmentConfigHelper"] = prev
        else:
            node_map.pop("SegmentConfigHelper", None)
