import importlib

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.ext.lora_manager"


def _load_module(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)
    monkeypatch.setattr(mod, "resolve_lora_display_names", lambda names: names)
    monkeypatch.setattr(mod, "calc_lora_hash", lambda name, _input: f"hash::{name}")
    return mod


def test_lora_manager_selectors_parse_stack_dicts(monkeypatch):
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "lora_stack": [
                [
                    {"name": "FluxMyth", "strength": 0.47, "clipStrength": 0.35},
                    {"name": "FantasyWizard", "strength": 0.22, "clipStrength": 0.2},
                ]
            ]
        },
    )
    names = mod.get_lora_model_names("42", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("42", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("42", None, None, None, None, input_data)
    assert names == ["FluxMyth", "FantasyWizard"]
    assert model_strengths == [0.47, 0.22]
    assert clip_strengths == [0.35, 0.2]


def test_lora_manager_selectors_parse_stack_tuples(monkeypatch):
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "lora_stack": [
                [
                    ("StackedA", 0.31, 0.18),
                    ("StackedB", 0.6, None),
                ]
            ]
        },
    )
    names = mod.get_lora_model_names("7", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("7", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("7", None, None, None, None, input_data)
    assert names == ["StackedA", "StackedB"]
    assert model_strengths == [0.31, 0.6]
    assert clip_strengths == [0.18, 0.6]
