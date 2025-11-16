import importlib
import os

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture"


def _prime_module(monkeypatch, prompt_text: str):
    cap = importlib.import_module(MODULE_PATH)

    class DummyPromptExecuter:
        class Caches:
            outputs = {}

        caches = Caches()

    # Simulate a node that will produce prompt text for positive prompt capture
    class DummyHook:
        current_prompt = {
            "1": {"class_type": "KSampler", "inputs": {"positive": [prompt_text]}},
        }
        current_extra_data = {}
        prompt_executer = DummyPromptExecuter()

    # Minimal mapping — only need the class referenced; value not used in our fake get_input_data
    monkeypatch.setattr(cap, "NODE_CLASS_MAPPINGS", {"KSampler": object})

    def fake_get_input_data(node_inputs, obj_class, node_id, outputs, dyn_prompt, extra):
        return (node_inputs,)

    monkeypatch.setattr(cap, "get_input_data", fake_get_input_data)
    monkeypatch.setattr(cap, "hook", DummyHook)
    return cap


def test_inline_lora_parsing_basic(monkeypatch):
    # Provide inline LoRA in angled bracket format with single strength
    prompt = "A painting of a fox <lora:fantasyStyle:0.75> in the woods"
    cap = _prime_module(monkeypatch, prompt)
    inputs = cap.Capture.get_inputs()
    # LoRA model names are mapped to MetaField.LORA_MODEL_NAME
    lora_names = [t[1] for t in inputs.get(MetaField.LORA_MODEL_NAME, [])]
    assert any("fantasyStyle" in ln for ln in lora_names), f"Expected fantasyStyle in {lora_names}"


def test_inline_lora_dual_strength(monkeypatch):
    # Dual strength syntax (model and CLIP strength) expected
    prompt = "portrait <lora:cinematic:0.6:0.4> dusk lighting"  # 0.6 model / 0.4 clip
    cap = _prime_module(monkeypatch, prompt)
    inputs = cap.Capture.get_inputs()
    strengths_model = [t[1] for t in inputs.get(MetaField.LORA_STRENGTH_MODEL, [])]
    strengths_clip = [t[1] for t in inputs.get(MetaField.LORA_STRENGTH_CLIP, [])]
    assert any(abs(float(s) - 0.6) < 1e-6 for s in strengths_model), strengths_model
    assert any(abs(float(s) - 0.4) < 1e-6 for s in strengths_clip), strengths_clip
