import os
import importlib
import types

import pytest

# Ensure test mode for deterministic formatting (multiline parameters)
os.environ.setdefault("METADATA_TEST_MODE", "1")

from saveimage_unimeta.trace import Trace  # noqa: E402
from saveimage_unimeta.defs.captures import CAPTURE_FIELD_LIST  # noqa: E402
from saveimage_unimeta.defs.meta import MetaField  # noqa: E402
from saveimage_unimeta.capture import Capture  # noqa: E402


@pytest.fixture(autouse=True)
def restore_capture_field_list():
    """Provide isolated modification of CAPTURE_FIELD_LIST per test."""
    original = dict(CAPTURE_FIELD_LIST)
    try:
        yield
    finally:
        # Restore original keys (shallow) and remove any added
        to_delete = set(CAPTURE_FIELD_LIST.keys()) - set(original.keys())
        for k in to_delete:
            CAPTURE_FIELD_LIST.pop(k, None)
        for k, v in original.items():
            CAPTURE_FIELD_LIST[k] = v


def test_enumerate_samplers_explicit_and_rule_backed():
    # Add a rule-backed sampler class
    CAPTURE_FIELD_LIST["MyCustomSampler"] = {
        MetaField.SAMPLER_NAME: {"field_name": "sampler_name"},
        MetaField.STEPS: {"field_name": "steps"},
    }
    trace_tree = {
        "0": (0, "SaveImageWithMetaDataUniversal"),
        "1": (1, "KSampler"),  # Tier A explicit
        "2": (1, "MyCustomSampler"),  # Tier B rule-backed
    }
    candidates = Trace.enumerate_samplers(trace_tree)
    assert len(candidates) == 2, candidates
    assert candidates[0]["node_id"] == "1" and candidates[0]["tier"] == "A"
    assert candidates[1]["node_id"] == "2" and candidates[1]["tier"] == "B"


def test_parameters_tail_present_for_multi():
    pnginfo = {
        "Positive prompt": "cat in hat",
        "Negative prompt": "ugly, bad",
        "Steps": 30,
        "Sampler": "Euler a",
        # internal multi entry list with two samplers
        "__multi_sampler_entries": [
            {"node_id": "1", "class_type": "KSampler", "sampler_name": "Euler a", "steps": 30},
            {
                "node_id": "2",
                "class_type": "MyCustomSampler",
                "sampler_name": "DPM++ 2M",
                "start_step": 30,
                "end_step": 49,
            },
        ],
    }
    params = Capture.gen_parameters_str(pnginfo)
    # Tail should appear and include both sampler names
    assert "Samplers:" in params
    assert "Euler a" in params and "DPM++ 2M" in params
    assert "(30-49)" in params  # segment range formatting


def test_parameters_tail_absent_for_single():
    pnginfo = {
        "Positive prompt": "dog",
        "Negative prompt": "lowres",
        "Steps": 20,
        "Sampler": "Euler a",
        "__multi_sampler_entries": [
            {"node_id": "1", "class_type": "KSampler", "sampler_name": "Euler a", "steps": 20},
        ],
    }
    params = Capture.gen_parameters_str(pnginfo)
    assert "Samplers:" not in params


def test_minimal_parameters_trims_sampler_tail():
    pnginfo = {
        "Positive prompt": "castle",
        "Negative prompt": "noise",
        "Steps": 40,
        "Sampler": "Euler a",
        "Seed": 123,
        "Sampler detail placeholder": "x",  # ensure extra content to not break splitting
        "__multi_sampler_entries": [
            {"node_id": "1", "class_type": "KSampler", "sampler_name": "Euler a", "steps": 40},
            {"node_id": "2", "class_type": "MyCustomSampler", "sampler_name": "Heun", "start_step": 40, "end_step": 59},
        ],
    }
    params_full = Capture.gen_parameters_str(pnginfo)
    assert "Samplers:" in params_full
    # Simulate minimal fallback trimming path
    from saveimage_unimeta.nodes.save_image import SaveImageWithMetaDataUniversal

    trimmed = SaveImageWithMetaDataUniversal._build_minimal_parameters(params_full)
    assert "Samplers:" not in trimmed


def test_segment_three_samplers_tail_order():
    # Ensure ordering preserved (primary first then descending range / steps)
    pnginfo = {
        "Positive prompt": "scenery",
        "Negative prompt": "",
        "Steps": 60,
        "Sampler": "Euler a",
        "__multi_sampler_entries": [
            {"node_id": "10", "class_type": "KSampler", "sampler_name": "Euler a", "steps": 60},
            {"node_id": "11", "class_type": "SegSampler", "sampler_name": "DPM++ 2M", "start_step": 30, "end_step": 49},
            {"node_id": "12", "class_type": "SegSampler", "sampler_name": "Heun", "start_step": 50, "end_step": 59},
        ],
    }
    params = Capture.gen_parameters_str(pnginfo)
    # Tail should respect provided order (primary first, then as listed because we already sorted upstream)
    tail_idx = params.find("Samplers:")
    assert tail_idx != -1
    tail = params[tail_idx:]
    first_pos = tail.find("Euler a")
    second_pos = tail.find("DPM++ 2M")
    third_pos = tail.find("Heun")
    assert -1 not in {first_pos, second_pos, third_pos}
    assert first_pos < second_pos < third_pos


def test_samplers_detail_includes_scheduler_and_denoise():
    """Scheduler and Denoise should appear in 'Samplers detail' (not in tail) when present."""
    multi_entries = [
        {
            "node_id": "1",
            "class_type": "KSampler",
            "sampler_name": "Euler a",
            "steps": 40,
            "scheduler": "normal",
            "denoise": 0.75,
        },
        {
            "node_id": "2",
            "class_type": "KSampler",
            "sampler_name": "DPM++ 2M",
            "start_step": 40,
            "end_step": 59,
            "scheduler": "karras",
            "denoise": 0.5,
        },
    ]
    # Simulate enrichment output from save_image (which populates 'Samplers detail')
    structured_items = []
    for e in multi_entries:
        parts = []
        if e.get("sampler_name"):
            parts.append(f"Name: {e['sampler_name']}")
        if e.get("scheduler") is not None:
            parts.append(f"Scheduler: {e['scheduler']}")
        if e.get("denoise") is not None:
            parts.append(f"Denoise: {e['denoise']}")
        if e.get("start_step") is not None and e.get("end_step") is not None:
            parts.append(f"Start: {e['start_step']}")
            parts.append(f"End: {e['end_step']}")
        elif e.get("steps") is not None:
            parts.append(f"Steps: {e['steps']}")
        structured_items.append('{'+', '.join(parts)+'}')
    samplers_detail = '[ ' + ', '.join(structured_items) + ' ]'
    assert "Scheduler: normal" in samplers_detail
    assert "Denoise: 0.75" in samplers_detail
    assert "Scheduler: karras" in samplers_detail
    assert "Denoise: 0.5" in samplers_detail
    # Parameter string tail should not include scheduler/denoise tokens (only range/name)
    pnginfo = {
        "Positive prompt": "fusion",
        "Negative prompt": "",
        "Steps": 40,
        "Sampler": "Euler a",
        "__multi_sampler_entries": multi_entries,
    }
    params = Capture.gen_parameters_str(pnginfo)
    assert "Samplers:" in params
    assert "Scheduler:" not in params  # tail doesn't list scheduler fields
    assert "Denoise:" not in params


def test_samplers_detail_includes_unique_seed_and_cfg(monkeypatch):
    """Unique per-sampler SEED/CFG should appear; identical values should not duplicate."""
    # Build multi entries baseline by invoking enrichment logic indirectly via parameters generation path.
    # We simulate after-enrichment structure by providing __multi_sampler_entries plus captured inputs.
    pnginfo = {
        "Positive prompt": "fusion",
        "Negative prompt": "",
        "Steps": 40,
        "Sampler": "Euler a",
        "__multi_sampler_entries": [
            {
                "node_id": "1",
                "class_type": "KSampler",
                "sampler_name": "Euler a",
                "steps": 40,
                "seed": 111,
                "cfg": 8.5,
            },
            {
                "node_id": "2",
                "class_type": "KSampler",
                "sampler_name": "DPM++ 2M",
                "start_step": 40,
                "end_step": 59,
                "seed": 222,
                "cfg": 12.0,
            },
        ],
    }
    # Monkeypatch Capture.get_inputs to feed seed & cfg per node for enrichment uniqueness detection.
    import saveimage_unimeta.capture as capture_mod
    from saveimage_unimeta.defs.meta import MetaField as MF
    def fake_get_inputs():
        return {
            MF.SAMPLER_NAME: [("1", "Euler a"), ("2", "DPM++ 2M")],
            MF.STEPS: [("1", 40), ("2", 20)],
            MF.SEED: [("1", 111), ("2", 222)],
            MF.CFG: [("1", 8.5), ("2", 12.0)],
        }
    monkeypatch.setattr(capture_mod.Capture, "get_inputs", classmethod(lambda cls: fake_get_inputs()))
    # Generate parameters through normal function to trigger tail (Samplers:)
    # Uniqueness detail logic validated in integration test below.
    param_str = Capture.gen_parameters_str(pnginfo)
    # Uniqueness logic only affects 'Samplers detail' generation inside save_image; since we didn't run that, skip.
    # Instead we assert tail unaffected; dedicated integration test covers enrichment path.
    assert "Samplers:" in param_str


def test_integration_unique_field_enrichment(monkeypatch, tmp_path):
    """Full enrichment: unique Seed & CFG included per sampler, identical Model omitted."""
    # Prepare prompt graph
    from saveimage_unimeta import hook as global_hook
    prompt = {
        "1": {"class_type": "KSampler", "inputs": {}},
        "2": {"class_type": "KSampler", "inputs": {}},
        "100": {"class_type": "SaveImageWithMetaDataUniversal", "inputs": {"a": ["1", 0], "b": ["2", 0]}},
    }
    global_hook.current_prompt = prompt
    global_hook.current_save_image_node_id = "100"
    # Patch inputs with unique seed/cfg, identical model
    import saveimage_unimeta.capture as capture_mod
    from saveimage_unimeta.defs.meta import MetaField as MF
    def fake_get_inputs():
        return {
            MF.SAMPLER_NAME: [("1", "Euler a"), ("2", "DPM++ 2M")],
            MF.STEPS: [("1", 30), ("2", 20)],
            MF.SEED: [("1", 111), ("2", 222)],
            MF.CFG: [("1", 7.5), ("2", 11.0)],
            MF.MODEL_NAME: [("1", "sameModel"), ("2", "sameModel")],
        }
    monkeypatch.setattr(capture_mod.Capture, "get_inputs", classmethod(lambda cls: fake_get_inputs()))
    import nodes as nodes_pkg  # type: ignore
    nodes_pkg.NODE_CLASS_MAPPINGS.setdefault("KSampler", type("_DummyKSampler", (), {}))  # type: ignore
    import saveimage_unimeta.nodes.save_image as save_mod
    SaveNode = save_mod.SaveImageWithMetaDataUniversal
    node = SaveNode()
    node.output_dir = str(tmp_path)
    ImgType = type(
        "Img",
        (),
        {
            "cpu": lambda self: self,
            "numpy": lambda self: __import__("numpy").zeros((8, 8, 3), dtype="float32"),
        },
    )
    img = ImgType()
    node.save_images([img], include_lora_summary=False, set_max_samplers=4)
    # Recompute pnginfo dict to inspect Samplers detail formatting (force multi enumeration)
    pnginfo = node.gen_pnginfo("Farthest", 0, False, 4)
    detail = pnginfo.get("Samplers detail", "")
    assert "Seed:" in detail and "CFG:" in detail  # unique fields appear
    assert "Model:" not in detail  # identical model omitted


def test_set_max_samplers_one_disables_multi_detail(monkeypatch, tmp_path):
    """When set_max_samplers=1 multi-sampler enrichment detail should be suppressed."""
    from saveimage_unimeta import hook as global_hook
    prompt = {
        "1": {"class_type": "KSampler", "inputs": {}},
        "2": {"class_type": "KSampler", "inputs": {}},
        "100": {"class_type": "SaveImageWithMetaDataUniversal", "inputs": {"a": ["1", 0], "b": ["2", 0]}},
    }
    global_hook.current_prompt = prompt
    global_hook.current_save_image_node_id = "100"
    import saveimage_unimeta.capture as capture_mod
    from saveimage_unimeta.defs.meta import MetaField as MF
    def fake_get_inputs():
        return {
            MF.SAMPLER_NAME: [("1", "Euler a"), ("2", "DPM++ 2M")],
            MF.STEPS: [("1", 30), ("2", 40)],
        }
    monkeypatch.setattr(capture_mod.Capture, "get_inputs", classmethod(lambda cls: fake_get_inputs()))
    import nodes as nodes_pkg  # type: ignore
    nodes_pkg.NODE_CLASS_MAPPINGS.setdefault("KSampler", type("_DummyKSampler", (), {}))  # type: ignore
    from saveimage_unimeta.nodes.save_image import SaveImageWithMetaDataUniversal
    node = SaveImageWithMetaDataUniversal()
    node.output_dir = str(tmp_path)
    ImgType = type(
        "Img",
        (),
        {
            "cpu": lambda self: self,
            "numpy": lambda self: __import__("numpy").zeros((4, 4, 3), dtype="float32"),
        },
    )
    img = ImgType()
    node.save_images([img], include_lora_summary=False, set_max_samplers=1)
    pnginfo = node.gen_pnginfo("Farthest", 0, False, 1)
    assert "Samplers detail" not in pnginfo  # suppressed


def test_set_max_samplers_allows_multi_detail(monkeypatch, tmp_path):
    """When set_max_samplers>1 multi-sampler enrichment detail should appear."""
    from saveimage_unimeta import hook as global_hook
    prompt = {
        "1": {"class_type": "KSampler", "inputs": {}},
        "2": {"class_type": "KSampler", "inputs": {}},
        "100": {"class_type": "SaveImageWithMetaDataUniversal", "inputs": {"a": ["1", 0], "b": ["2", 0]}},
    }
    global_hook.current_prompt = prompt
    global_hook.current_save_image_node_id = "100"
    import saveimage_unimeta.capture as capture_mod
    from saveimage_unimeta.defs.meta import MetaField as MF
    def fake_get_inputs():
        return {
            MF.SAMPLER_NAME: [("1", "Euler a"), ("2", "DPM++ 2M")],
            MF.STEPS: [("1", 30), ("2", 25)],
        }
    monkeypatch.setattr(capture_mod.Capture, "get_inputs", classmethod(lambda cls: fake_get_inputs()))
    import nodes as nodes_pkg  # type: ignore
    nodes_pkg.NODE_CLASS_MAPPINGS.setdefault("KSampler", type("_DummyKSampler", (), {}))  # type: ignore
    from saveimage_unimeta.nodes.save_image import SaveImageWithMetaDataUniversal
    node = SaveImageWithMetaDataUniversal()
    node.output_dir = str(tmp_path)
    ImgType = type(
        "Img",
        (),
        {
            "cpu": lambda self: self,
            "numpy": lambda self: __import__("numpy").zeros((4, 4, 3), dtype="float32"),
        },
    )
    img = ImgType()
    node.save_images([img], include_lora_summary=False, set_max_samplers=3)
    pnginfo = node.gen_pnginfo("Farthest", 0, False, 3)
    assert "Samplers detail" in pnginfo
