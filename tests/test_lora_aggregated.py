import importlib
from typing import Any
from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture"


def _prime(monkeypatch, prompt_text: str):
    cap = importlib.import_module(MODULE_PATH)

    class DummyPromptExecuter:
        class Caches:
            outputs: dict[str, Any] = {}

        caches = Caches()

    class DummyHook:
        current_prompt: dict[str, dict[str, Any]] = {
            "1": {"class_type": "KSampler", "inputs": {"positive": [prompt_text]}},
        }
        current_extra_data: dict[str, Any] = {}
        prompt_executer: DummyPromptExecuter = DummyPromptExecuter()

    monkeypatch.setattr(cap, "NODE_CLASS_MAPPINGS", {"KSampler": object})

    def fake_get_input_data(
        node_inputs: dict[str, Any],
        obj_class: object,
        node_id: str,
        outputs: dict[str, Any],
        dyn_prompt: Any,
        extra: Any,
    ) -> tuple[dict[str, Any]]:
        return (node_inputs,)

    monkeypatch.setattr(cap, "get_input_data", fake_get_input_data)
    monkeypatch.setattr(cap, "hook", DummyHook)
    return cap


def test_aggregated_multiple_loras(monkeypatch):
    # Simulate aggregated inline syntax separated by commas (handled by parser fallback)
    prompt = "masterpiece, <lora:fooStyle:0.7>, <lora:barStyle:0.5:0.3>, <lora:fooStyle:0.7>"  # duplicate fooStyle
    cap = _prime(monkeypatch, prompt)
    inputs = cap.Capture.get_inputs()
    names = [t[1] for t in inputs.get(MetaField.LORA_MODEL_NAME, [])]
    # Expect at least fooStyle & barStyle present
    assert any("fooStyle" in n for n in names)
    assert any("barStyle" in n for n in names)
    # Dedup may keep only one fooStyle entry (depending on final implementation) => ensure not >2 copies
    assert sum(1 for n in names if "fooStyle" in n) <= 2
