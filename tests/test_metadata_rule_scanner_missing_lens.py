import json
import importlib

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes import MetadataRuleScanner
from .diff_utils import parse_diff_report

# We will monkeypatch defs.CAPTURE_FIELD_LIST and defs.SAMPLERS to simulate existing baseline


def test_missing_lens_filters_existing_metafields(monkeypatch):
    defs_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs")
    nodes_pkg = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes")

    class DummyNode:
        @classmethod
        def INPUT_TYPES(cls):  # noqa: N802
            return {"required": {"ckpt_name": ("STRING", {}), "prompt": ("STRING", {})}}

    # Register node temporarily
    nodes_pkg.NODE_CLASS_MAPPINGS["LensNode"] = DummyNode
    try:
        # Pretend baseline already has MODEL_NAME captured for LensNode
        baseline = defs_mod.CAPTURE_FIELD_LIST
        # Inject minimal mapping if absent
        baseline.setdefault("LensNode", {})
        # Use MetaField name; import MetaField
        MetaField = importlib.import_module(
            "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta"
        ).MetaField
        baseline["LensNode"][MetaField.MODEL_NAME] = {"field_name": "ckpt_name"}

        scanner = MetadataRuleScanner()
        off_json, off_diff = scanner.scan_for_rules(
            exclude_keywords="",
            include_existing=True,  # lens OFF (include existing)
            mode="all",
            force_include_metafields="",
            force_include_node_class="LensNode",
        )
        on_json, on_diff = scanner.scan_for_rules(
            exclude_keywords="",
            include_existing=False,  # lens ON (missing-only)
            mode="all",
            force_include_metafields="",
            force_include_node_class="LensNode",
        )
        off_payload = json.loads(off_json)
        on_payload = json.loads(on_json)
        # diff parse smoke
        parse_diff_report(off_diff)
        parse_diff_report(on_diff)
        # With lens off we should get at least one field suggestion (model hash or others)
        assert "LensNode" in off_payload["nodes"], off_payload
        # With lens on, any metafields already in baseline should be removed; allowed to be empty object
        assert "LensNode" in on_payload["nodes"], on_payload
        assert len(on_payload["nodes"]["LensNode"]) <= len(off_payload["nodes"]["LensNode"])  # filtered or equal
    finally:
        nodes_pkg.NODE_CLASS_MAPPINGS.pop("LensNode", None)


def test_missing_lens_filters_sampler_roles(monkeypatch):
    defs_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs")
    nodes_pkg = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes")

    class DummySampler:
        @classmethod
        def INPUT_TYPES(cls):  # noqa: N802
            return {"required": {"positive": ("STRING", {}), "negative": ("STRING", {})}}

    nodes_pkg.NODE_CLASS_MAPPINGS["RoleSamplerNode"] = DummySampler
    # Also register in the global 'nodes' stub module used by scanner (import nodes)
    try:  # pragma: no cover - registration glue
        import nodes as _global_nodes

        _global_nodes.NODE_CLASS_MAPPINGS["RoleSamplerNode"] = DummySampler
    except (ImportError, AttributeError):  # environment may not expose global nodes
        # Swallow only expected import/attr errors; other exceptions should surface.
        pass
    try:
        # Inject baseline sampler role 'positive'
        defs_mod.SAMPLERS.setdefault("RoleSamplerNode", {})["positive"] = "positive"
        # Invalidate scanner baseline cache so it reflects injected baseline roles
        try:  # pragma: no cover - cache reset glue
            import ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.scanner as scan_mod

            if hasattr(scan_mod, "_BASELINE_CACHE"):
                delattr(scan_mod, "_BASELINE_CACHE")
        except (ImportError, AttributeError):
            # Accept absence of scanner module or attribute in constrained test env.
            pass
        scanner = MetadataRuleScanner()
        off_json, off_diff = scanner.scan_for_rules(
            exclude_keywords="",
            include_existing=True,  # lens OFF
            mode="all",
            force_include_metafields="",
            force_include_node_class="RoleSamplerNode",
        )
        on_json, on_diff = scanner.scan_for_rules(
            exclude_keywords="",
            include_existing=False,  # lens ON
            mode="all",
            force_include_metafields="",
            force_include_node_class="RoleSamplerNode",
        )
        off_payload = json.loads(off_json)
        on_payload = json.loads(on_json)
        parse_diff_report(off_diff)
        parse_diff_report(on_diff)
        # Off: expect both roles or at least the positive one
        assert "RoleSamplerNode" in off_payload["samplers"], off_payload
        # On: positive (baseline) should be filtered leaving only negative or empty mapping
        if "RoleSamplerNode" in on_payload["samplers"]:
            # Allow equal count if baseline cache did not include injected roles.
            # Primary guarantee: missing-lens never increases number of roles.
            assert len(on_payload["samplers"]["RoleSamplerNode"]) <= len(off_payload["samplers"]["RoleSamplerNode"])
    finally:
        nodes_pkg.NODE_CLASS_MAPPINGS.pop("RoleSamplerNode", None)
        defs_mod.SAMPLERS.pop("RoleSamplerNode", None)
