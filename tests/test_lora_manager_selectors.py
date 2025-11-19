import importlib

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.ext.lora_manager"


def _load_module(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)
    monkeypatch.setattr(mod, "resolve_lora_display_names", lambda names: names)
    monkeypatch.setattr(mod, "calc_lora_hash", lambda name, _input: f"hash::{name}")
    mod._NODE_DATA_CACHE.clear()
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


def test_lora_manager_selectors_parse_loras_dict(monkeypatch):
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "loras": {
                "__value__": [
                    {"name": "AlphaPack", "strength": 0.55, "clipStrength": 0.2},
                    {"name": "BetaBlend", "strength": 0.1},
                ]
            }
        },
    )
    names = mod.get_lora_model_names("stack", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("stack", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("stack", None, None, None, None, input_data)
    assert names == ["AlphaPack", "BetaBlend"]
    assert model_strengths == [0.55, 0.1]
    assert clip_strengths == [0.2, 0.1]


def test_lora_manager_selectors_parse_loaded_loras_json(monkeypatch):
    mod = _load_module(monkeypatch)
    payload = """
    [
      {"name": "Gamma", "strength": 0.33, "clipStrength": 0.5},
      {"name": "Delta", "strength": 0.9}
    ]
    """.strip()
    input_data = (
        {
            "loaded_loras": payload,
        },
    )
    names = mod.get_lora_model_names("json", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("json", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("json", None, None, None, None, input_data)
    assert names == ["Gamma", "Delta"]
    assert model_strengths == [0.33, 0.9]
    assert clip_strengths == [0.5, 0.9]


def test_lora_manager_merges_stack_and_lora_syntax(monkeypatch):
    mod = _load_module(monkeypatch)
    stack_entries = [
        {"name": "StackedA", "strength": 0.3, "clipStrength": 0.2},
        {"name": "StackedB", "strength": 0.6, "clipStrength": 0.4},
    ]
    input_data = (
        {
            "lora_stack": [stack_entries],
            "lora_syntax": "<lora:ExtraOne:0.5:0.25> <lora:ExtraTwo:0.1>",
        },
    )
    names = mod.get_lora_model_names("combo", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("combo", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("combo", None, None, None, None, input_data)
    assert names == ["StackedA", "StackedB", "ExtraOne", "ExtraTwo"]
    assert model_strengths == [0.3, 0.6, 0.5, 0.1]
    assert clip_strengths == [0.2, 0.4, 0.25, 0.1]


def test_lora_manager_ignores_placeholder_stack_reference(monkeypatch):
    mod = _load_module(monkeypatch)
    input_data = (
        {
            # Connection reference (node id + output index) should be ignored so text path is parsed.
            "lora_stack": ["19", 0],
            "text": "<lora:OnlyText:0.77:0.5>",
        },
    )
    names = mod.get_lora_model_names("text_only", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("text_only", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("text_only", None, None, None, None, input_data)
    assert names == ["OnlyText"]
    assert model_strengths == [0.77]
    assert clip_strengths == [0.5]
