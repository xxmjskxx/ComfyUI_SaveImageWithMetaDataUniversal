from saveimage_unimeta.defs.ext.wan_video_wrapper import CAPTURE_FIELD_LIST
from saveimage_unimeta.defs.meta import MetaField


def test_wan_video_wrapper_mapping_exists_and_has_core_nodes():
    nodes = CAPTURE_FIELD_LIST
    # Core nodes present
    for key in [
        "WanVideoModelLoader",
        "WanVideoVAELoader",
        "WanVideoTinyVAELoader",
        "WanVideoLoraSelect",
        "WanVideoLoraSelectByName",
        "WanVideoLoraSelectMulti",
        "WanVideoVACEModelSelect",
        "WanVideoExtraModelSelect",
        "LoadWanVideoT5TextEncoder",
        "LoadWanVideoClipTextEncoder",
        "WanVideoTextEncode",
        "WanVideoTextEncodeCached",
        "WanVideoTextEncodeSingle",
        "WanVideo Sampler",
    ]:
        assert key in nodes, f"Missing mapping for {key}"


def test_model_loader_has_multi_fields_and_hash_formatter():
    entry = CAPTURE_FIELD_LIST["WanVideoModelLoader"]
    name_cfg = entry[MetaField.MODEL_NAME]
    hash_cfg = entry[MetaField.MODEL_HASH]
    assert "fields" in name_cfg and isinstance(name_cfg["fields"], list)
    assert "fields" in hash_cfg and callable(hash_cfg["format"]) and isinstance(hash_cfg["fields"], list)


def test_lora_select_multi_has_expected_slots():
    entry = CAPTURE_FIELD_LIST["WanVideoLoraSelectMulti"]
    names = entry[MetaField.LORA_MODEL_NAME]["fields"]
    strengths = entry[MetaField.LORA_STRENGTH_MODEL]["fields"]
    assert names == ["lora_0", "lora_1", "lora_2", "lora_3", "lora_4"]
    assert strengths == ["strength_0", "strength_1", "strength_2", "strength_3", "strength_4"]


def test_wan_sampler_has_expected_fields_and_selectors():
    entry = CAPTURE_FIELD_LIST["WanVideo Sampler"]
    # direct fields
    assert entry[MetaField.SEED]["field_name"] == "seed"
    assert entry[MetaField.STEPS]["field_name"] == "steps"
    assert entry[MetaField.CFG]["field_name"] == "cfg"
    assert entry[MetaField.SHIFT]["field_name"] == "shift"
    assert entry[MetaField.DENOISE]["field_name"] == "denoise"
    # Wan2.2 MoE segment support
    assert entry[MetaField.START_STEP]["field_name"] == "start_step"
    assert entry[MetaField.END_STEP]["field_name"] == "end_step"
    # selectors callable
    assert callable(entry[MetaField.SAMPLER_NAME]["selector"])  # type: ignore[index]
    assert callable(entry[MetaField.SCHEDULER]["selector"])  # type: ignore[index]


def test_wan_sampler_selector_parsing_variants():
    entry = CAPTURE_FIELD_LIST["WanVideo Sampler"]
    get_sampler = entry[MetaField.SAMPLER_NAME]["selector"]  # type: ignore[index]
    get_sched = entry[MetaField.SCHEDULER]["selector"]  # type: ignore[index]

    def mk_input(val):
        return [{"scheduler": [val]}]

    # dict-like
    input_data = mk_input({"sampler": "Euler a", "scheduler": "Karras"})
    assert get_sampler(None, None, None, None, None, input_data) == "Euler a"
    assert get_sched(None, None, None, None, None, input_data) == "Karras"

    # tuple/list-like
    input_data = mk_input(["DPM++ 2M", "Exponential"])
    assert get_sampler(None, None, None, None, None, input_data) == "DPM++ 2M"
    assert get_sched(None, None, None, None, None, input_data) == "Exponential"

    # string with parentheses
    input_data = mk_input("Euler (Karras)")
    assert get_sampler(None, None, None, None, None, input_data) == "Euler"
    assert get_sched(None, None, None, None, None, input_data) == "Karras"

    # string with separator
    input_data = mk_input("Heun / Normal")
    assert get_sampler(None, None, None, None, None, input_data) == "Heun"
    assert get_sched(None, None, None, None, None, input_data) == "Normal"

    # unknown string: treat as scheduler-only
    input_data = mk_input("Karras")
    assert get_sampler(None, None, None, None, None, input_data) == ""
    assert get_sched(None, None, None, None, None, input_data) == "Karras"
