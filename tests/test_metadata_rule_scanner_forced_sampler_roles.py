import json

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes import MetadataRuleScanner
import nodes


class _DummyKSampler:
    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        # Provide positive/negative to satisfy sampler detection heuristic
        return {"required": {"positive": ("STRING", {}), "negative": ("STRING", {}), "steps": ("INT", {})}}


if "KSampler" not in nodes.NODE_CLASS_MAPPINGS:
    nodes.NODE_CLASS_MAPPINGS["KSampler"] = _DummyKSampler


def test_forced_sampler_role_preserved_under_lens():
    scanner = MetadataRuleScanner()
    # Build baseline (include existing) so sampler roles are considered 'existing'
    scanner.scan_for_rules(
        exclude_keywords="",
        include_existing=True,
        mode="all",
        force_include_metafields="",
        force_include_node_class="",
    )
    # Second scan: activate missing-lens and force include role 'positive'
    json_payload, _ = scanner.scan_for_rules(
        exclude_keywords="",
        include_existing=False,
        mode="all",
        force_include_metafields="positive",
        force_include_node_class="",
    )
    data = json.loads(json_payload)
    # We expect KSampler (a known sampler) to be present and its 'positive' role retained
    assert "KSampler" in data.get("samplers", {}), data
    roles = data["samplers"]["KSampler"]
    assert "positive" in roles, roles
    # Also verify sampler_status marks the role as forced
    status_map = data.get("samplers_status", {}).get("KSampler", {})
    assert status_map.get("positive", {}).get("forced") is True, status_map
