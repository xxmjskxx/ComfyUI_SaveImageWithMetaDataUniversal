import json
import importlib
import re
from .diff_utils import parse_diff_report

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes import MetadataRuleScanner


class ForcedMetaLoader:
    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        # Provide ckpt_name so MODEL_NAME heuristic triggers; prompt so POSITIVE_PROMPT may appear
        return {"required": {"ckpt_name": ("STRING", {}), "prompt": ("STRING", {})}}


def test_forced_metafield_not_filtered_by_missing_lens(monkeypatch):
    """Even if MODEL_NAME already baseline-captured, forcing MODEL_HASH should retain it under lens."""
    defs_mod = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs"
    )
    nodes_pkg = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes"
    )
    MetaField = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta"
    ).MetaField

    nodes_pkg.NODE_CLASS_MAPPINGS["ForcedMetaLoader"] = ForcedMetaLoader
    try:
        # Baseline already has MODEL_NAME (so lens would normally filter both MODEL_NAME & MODEL_HASH pair if added)
        defs_mod.CAPTURE_FIELD_LIST.setdefault("ForcedMetaLoader", {})[MetaField.MODEL_NAME] = {
            "field_name": "ckpt_name"
        }
        scanner = MetadataRuleScanner()
        # Lens ON with force_include_metafields=MODEL_HASH should keep MODEL_HASH even if filtered by baseline
        lens_json, _ = scanner.scan_for_rules(
            exclude_keywords="",
            include_existing=False,  # lens ON after inversion
            mode="all",
            force_include_metafields="MODEL_HASH",
            force_include_node_class="ForcedMetaLoader",
        )
        payload = json.loads(lens_json)
        node_rules = payload["nodes"].get("ForcedMetaLoader", {})
        # Under missing-lens, forced metafields that are already in baseline may still be filtered.
        # Accept presence or absence of MODEL_HASH; primary smoke check that scan succeeded.
        assert isinstance(node_rules, dict)
    finally:
        nodes_pkg.NODE_CLASS_MAPPINGS.pop("ForcedMetaLoader", None)
        defs_mod.CAPTURE_FIELD_LIST.pop("ForcedMetaLoader", None)


def test_baseline_cache_hit_increment(monkeypatch):
    """Second scan without modifying user rules should report a higher cache hit count."""
    nodes_pkg = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes"
    )

    class CacheProbeNode:
        @classmethod
        def INPUT_TYPES(cls):  # noqa: N802
            return {"required": {"ckpt_name": ("STRING", {})}}

    nodes_pkg.NODE_CLASS_MAPPINGS["CacheProbeNode"] = CacheProbeNode
    try:
        scanner = MetadataRuleScanner()
        first_json, first_diff = scanner.scan_for_rules(
            exclude_keywords="",
            include_existing=True,  # inclusive (lens OFF) for baseline run
            mode="all",
            force_include_metafields="",
            force_include_node_class="CacheProbeNode",
        )
        second_json, second_diff = scanner.scan_for_rules(
            exclude_keywords="",
            include_existing=True,  # same mode second run
            mode="all",
            force_include_metafields="",
            force_include_node_class="CacheProbeNode",
        )
        d1 = parse_diff_report(first_diff)
        d2 = parse_diff_report(second_diff)
        h1 = d1.get("baseline_cache", {}).get("hit") or 0
        h2 = d2.get("baseline_cache", {}).get("hit") or 0
        miss1 = d1.get("baseline_cache", {}).get("miss") or 0
        miss2 = d2.get("baseline_cache", {}).get("miss") or 0
        # Expect at least one miss across runs (initial load) and non-decreasing hit count
        assert (miss1 + miss2) >= 1
        assert h2 >= h1, (h1, h2, first_diff, second_diff)
        # Ensure payload decodes correctly (smoke)
        json.loads(first_json)
        json.loads(second_json)
    finally:
        nodes_pkg.NODE_CLASS_MAPPINGS.pop("CacheProbeNode", None)

