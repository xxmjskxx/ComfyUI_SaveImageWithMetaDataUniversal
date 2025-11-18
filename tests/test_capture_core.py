import os
import types
import importlib

# We will import capture module and test a few isolated helper behaviors.
# Runtime ComfyUI dependencies are guarded by try/except inside capture.

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture"


def _setup_inline_prompt_environment(monkeypatch, inline_flag: bool):
    cap = importlib.import_module(MODULE_PATH)
    meta_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta")
    MetaField = meta_mod.MetaField

    class DummyPromptExecuter:
        class Caches:
            outputs = {}

        caches = Caches()

    class DummyHook:
        current_prompt = {
            "1": {
                "class_type": "InlinePromptNode",
                "inputs": {"text": ["base prompt <lora:StackedDemo:0.75:0.5>"]},
            }
        }
        current_extra_data = {}
        prompt_executer = DummyPromptExecuter()

    monkeypatch.setattr(cap, "hook", DummyHook)
    monkeypatch.setattr(cap, "NODE_CLASS_MAPPINGS", {"InlinePromptNode": object})

    def fake_get_input_data(node_inputs, obj_class, node_id, outputs, dyn_prompt, extra):
        return (node_inputs,)

    monkeypatch.setattr(cap, "get_input_data", fake_get_input_data)

    rule = {"field_name": "text"}
    if inline_flag:
        rule["inline_lora_candidate"] = True
    monkeypatch.setattr(cap, "CAPTURE_FIELD_LIST", {"InlinePromptNode": {MetaField.POSITIVE_PROMPT: rule}})
    return cap, MetaField


def test_module_imports_without_comfy_runtime(monkeypatch):
    # Ensure env flags don't break import.
    monkeypatch.delenv("METADATA_DEBUG_PROMPTS", raising=False)
    mod = importlib.import_module(MODULE_PATH)
    assert hasattr(mod, "Capture")


def test_clean_name_basic():
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture
    assert Capture._clean_name("C:/models/foo/bar.safetensors", drop_extension=True) == "bar"
    assert Capture._clean_name(["C:/x/y/z.pt"]) == "z.pt"
    assert Capture._clean_name("\\\\network\\share\\model.ckpt", drop_extension=True) == "model"
    # When capture tuples include node id + field context, ensure we clean the value portion.
    assert Capture._clean_name((42, "EasyNegative.safetensors", "text"), drop_extension=True) == "EasyNegative"


def test_iter_values_and_extract_value():
    capture_mod = importlib.import_module(MODULE_PATH)
    Capture = capture_mod.Capture
    data = [(1, "val1"), (2, "val2", "extra"), "bare", (3, ["nested"])]
    vals = list(Capture._iter_values(data))
    # "bare" stays as string, nested list returns list object
    assert vals[0] == "val1"
    assert vals[1] == "val2"
    assert vals[2] == "bare"


def test_get_inputs_fallback_flux(monkeypatch):
    """Simulate a minimal prompt graph where Flux fallback should capture T5/CLIP prompts."""
    cap = importlib.import_module(MODULE_PATH)
    meta_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta")
    MetaField = meta_mod.MetaField

    # Minimal fake hook state
    class DummyPromptExecuter:
        class Caches:
            outputs = {}

        caches = Caches()

    class DummyHook:
        current_prompt = {
            "1": {"class_type": "CLIPTextEncodeFlux", "inputs": {"t5xxl": ["A cat"], "clip_l": ["A dog"]}},
        }
        current_extra_data = {}
        prompt_executer = DummyPromptExecuter()

    monkeypatch.setattr(cap, "hook", DummyHook)
    # Provide node mapping & get_input_data to mimic environment
    monkeypatch.setattr(cap, "NODE_CLASS_MAPPINGS", {"CLIPTextEncodeFlux": object})

    def fake_get_input_data(node_inputs, obj_class, node_id, outputs, dyn_prompt, extra):
        return (node_inputs,)  # shape expected: first element mapping

    monkeypatch.setattr(cap, "get_input_data", fake_get_input_data)

    inputs = cap.Capture.get_inputs()
    assert MetaField.T5_PROMPT in inputs
    assert MetaField.CLIP_PROMPT in inputs
    t5_vals = [v[1] for v in inputs[MetaField.T5_PROMPT]]
    clip_vals = [v[1] for v in inputs[MetaField.CLIP_PROMPT]]
    assert "A cat" in t5_vals
    assert "A dog" in clip_vals


def test_inline_lora_fallback_requires_opt_in(monkeypatch):
    cap, MetaField = _setup_inline_prompt_environment(monkeypatch, inline_flag=False)
    inputs = cap.Capture.get_inputs()
    assert MetaField.POSITIVE_PROMPT in inputs
    assert MetaField.LORA_MODEL_NAME not in inputs


def test_inline_lora_fallback_runs_when_opted_in(monkeypatch):
    cap, MetaField = _setup_inline_prompt_environment(monkeypatch, inline_flag=True)
    inputs = cap.Capture.get_inputs()
    assert MetaField.LORA_MODEL_NAME in inputs
    names = [entry[1] for entry in inputs[MetaField.LORA_MODEL_NAME]]
    assert "StackedDemo" in names


def test_inline_prompt_text_not_recorded_without_opt_in(monkeypatch):
    cap, MetaField = _setup_inline_prompt_environment(monkeypatch, inline_flag=False)
    inputs = cap.Capture.get_inputs()
    records, _ = cap.Capture._collect_lora_records(inputs)
    assert all("StackedDemo" not in rec.name for rec in records)


def test_generate_pnginfo_version_stamp():
    cap = importlib.import_module(MODULE_PATH)
    # meta_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta")
    # MetaField = meta_mod.MetaField

    # Provide minimal empty inputs
    pnginfo = cap.Capture.gen_pnginfo_dict({}, {}, False)
    assert "Metadata generator version" in pnginfo


def test_collect_lora_records_aligns_strengths():
    cap = importlib.import_module(MODULE_PATH)
    meta_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta")
    MetaField = meta_mod.MetaField
    inputs = {
        MetaField.LORA_MODEL_NAME: [
            (1, "berserk_guts-10.safetensors", "lora_name_1"),
            (1, "Guts_05.safetensors", "lora_name_2"),
        ],
        MetaField.LORA_MODEL_HASH: [
            (1, "448a59f25e", "lora_hash_1"),
            (1, "c2b1d95dde", "lora_hash_2"),
        ],
        MetaField.LORA_STRENGTH_MODEL: [
            (1, 0.65, "model_strength_1"),
            (1, 0.55, "model_strength_2"),
        ],
        MetaField.LORA_STRENGTH_CLIP: [
            (1, 0.44, "clip_strength_1"),
            (1, 0.46, "clip_strength_2"),
            (1, 0.99, "model_strength_1"),
        ],
    }
    records, aggregate_error = cap.Capture._collect_lora_records(inputs)
    assert not aggregate_error
    assert [rec.name for rec in records] == ["berserk_guts-10.safetensors", "Guts_05.safetensors"]
    assert records[0].strength_clip == 0.44
    assert records[1].strength_clip == 0.46
    assert len(records) == 2


def test_collect_lora_records_uses_tuple_fallbacks():
    cap = importlib.import_module(MODULE_PATH)
    meta_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta")
    MetaField = meta_mod.MetaField
    inputs = {
        MetaField.LORA_MODEL_NAME: [
            (1, ("StackOne", "0.25", "0.15"), "lora_stack"),
            (1, ("StackTwo", 0.5, 0.4), "lora_stack"),
        ],
        MetaField.LORA_MODEL_HASH: [
            (1, "1111111111", "lora_stack"),
            (1, "2222222222", "lora_stack"),
        ],
        MetaField.LORA_STRENGTH_MODEL: [],
        MetaField.LORA_STRENGTH_CLIP: [],
    }
    records, aggregate_error = cap.Capture._collect_lora_records(inputs)
    assert not aggregate_error
    assert [rec.name for rec in records] == ["StackOne", "StackTwo"]
    assert records[0].strength_model == 0.25
    assert records[0].strength_clip == 0.15
    assert records[1].strength_model == 0.5
    assert records[1].strength_clip == 0.4


def test_collect_lora_records_skips_orphan_strength_slots():
    cap = importlib.import_module(MODULE_PATH)
    meta_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta")
    MetaField = meta_mod.MetaField
    inputs = {
        MetaField.LORA_MODEL_NAME: [
            (1, "Majora_Zelda.safetensors", "lora_name_1"),
            (1, "ootlink-nvwls-v1.safetensors", "lora_name_2"),
        ],
        MetaField.LORA_MODEL_HASH: [],
        MetaField.LORA_STRENGTH_MODEL: [
            (1, 0.97, "model_str_1"),
            (1, 0.6, "model_str_2"),
            (1, 1.0, "model_str_50"),
        ],
        MetaField.LORA_STRENGTH_CLIP: [
            (1, 0.88, "clip_str_1"),
            (1, 0.51, "clip_str_2"),
            (1, 1.0, "clip_str_50"),
        ],
    }
    records, aggregate_error = cap.Capture._collect_lora_records(inputs)
    assert not aggregate_error
    assert [rec.name for rec in records] == [
        "Majora_Zelda.safetensors",
        "ootlink-nvwls-v1.safetensors",
    ]
    assert [rec.strength_model for rec in records] == [0.97, 0.6]
    assert [rec.strength_clip for rec in records] == [0.88, 0.51]


def test_collect_lora_records_preserves_strengths_per_node():
    cap = importlib.import_module(MODULE_PATH)
    meta_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta")
    MetaField = meta_mod.MetaField
    inputs = {
        MetaField.LORA_MODEL_NAME: [
            ("node_a", "FirstStyle", "lora_name"),
            ("node_b", "SecondStyle", "lora_name"),
            ("node_c", "ThirdStyle", "lora_name"),
        ],
        MetaField.LORA_STRENGTH_MODEL: [
            ("node_b", 0.42, "strength_model"),
            ("node_c", 0.73, "strength_model"),
        ],
        MetaField.LORA_STRENGTH_CLIP: [
            ("node_c", 0.55, "strength_clip"),
        ],
    }
    records, _ = cap.Capture._collect_lora_records(inputs)
    assert [rec.name for rec in records] == ["FirstStyle", "SecondStyle", "ThirdStyle"]
    assert records[0].strength_model is None
    assert records[1].strength_model == 0.42
    assert records[2].strength_model == 0.73
    # Clip strength should only land on the originating node
    assert records[0].strength_clip is None
    assert records[1].strength_clip is None
    assert records[2].strength_clip == 0.55


def test_collect_lora_records_keeps_per_selector_hashes():
    cap = importlib.import_module(MODULE_PATH)
    meta_mod = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta")
    MetaField = meta_mod.MetaField
    inputs = {
        MetaField.LORA_MODEL_NAME: [
            ("node_10", "StackedEntry", "stack_selector"),
            ("node_10", "ManagerEntry", "manager_selector"),
        ],
        # Only provide a hash for the manager selector to ensure provenance keeps it aligned.
        MetaField.LORA_MODEL_HASH: [
            ("node_10", "managed-hash", "manager_selector"),
        ],
    }
    records, _ = cap.Capture._collect_lora_records(inputs)
    assert len(records) == 2
    # First entry has no explicit hash, so it should fall back to a computed value (non empty string)
    assert records[0].name == "StackedEntry"
    assert records[0].hash
    # Second entry must re-use the provided hash even though its selector emitted after the first.
    assert records[1].name == "ManagerEntry"
    assert records[1].hash == "managed-hash"


def test_get_hashes_for_civitai_skips_plaintext_vae_entries():
    cap = importlib.import_module(MODULE_PATH)
    hashes = cap.Capture.get_hashes_for_civitai(
        inputs_before_sampler_node={},
        inputs_before_this_node={},
        pnginfo_dict={"Model hash": "abc123def0", "VAE hash": "Baked VAE"},
        lora_records=[],
    )
    assert hashes["model"] == "abc123def0"
    assert "vae" not in hashes
