import os
import types
import importlib

# We will import capture module and test a few isolated helper behaviors.
# Runtime ComfyUI dependencies are guarded by try/except inside capture.

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture"

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
    assert (
        Capture._clean_name((42, "EasyNegative.safetensors", "text"), drop_extension=True) == "EasyNegative"
    )


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
    meta_mod = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta"
    )
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


def test_generate_pnginfo_version_stamp():
    cap = importlib.import_module(MODULE_PATH)
    meta_mod = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta"
    )
    MetaField = meta_mod.MetaField

    # Provide minimal empty inputs
    pnginfo = cap.Capture.gen_pnginfo_dict({}, {}, False)
    assert "Metadata generator version" in pnginfo

