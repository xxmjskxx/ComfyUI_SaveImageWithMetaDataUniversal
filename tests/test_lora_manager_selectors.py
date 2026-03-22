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


def test_lora_manager_filters_inactive_loras(monkeypatch):
    """Test that only loras with active=True (or no active field) are captured."""
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "lora_stack": [
                [
                    {"name": "lenovo_z", "strength": 0.2, "clipStrength": 0.2, "active": False},
                    {"name": "grainscape_zimage", "strength": 0.2, "clipStrength": 0.2, "active": True},
                    {"name": "z-image_turbo", "strength": 1.0, "clipStrength": 1.0, "active": True},
                    {"name": "Rainbow_Brite", "strength": 1.0, "clipStrength": 1.0, "active": False},
                    {"name": "Marvel_Spectrum", "strength": 1.0, "clipStrength": 1.0, "active": True},
                    {"name": "DC_Comics_Mera", "strength": 1.0, "clipStrength": 1.0, "active": False},
                ]
            ]
        },
    )
    names = mod.get_lora_model_names("active_test", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("active_test", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("active_test", None, None, None, None, input_data)
    # Only the 3 active loras should be captured
    assert names == ["grainscape_zimage", "z-image_turbo", "Marvel_Spectrum"]
    assert model_strengths == [0.2, 1.0, 1.0]
    assert clip_strengths == [0.2, 1.0, 1.0]


def test_lora_manager_includes_loras_without_active_field(monkeypatch):
    """Test that loras without an 'active' field are included (backward compat)."""
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "lora_stack": [
                [
                    {"name": "NoActiveField", "strength": 0.5, "clipStrength": 0.3},
                    {"name": "WithActiveTrue", "strength": 0.6, "clipStrength": 0.4, "active": True},
                    {"name": "WithActiveFalse", "strength": 0.7, "clipStrength": 0.5, "active": False},
                ]
            ]
        },
    )
    names = mod.get_lora_model_names("compat_test", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("compat_test", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("compat_test", None, None, None, None, input_data)
    # NoActiveField and WithActiveTrue should be captured, WithActiveFalse should not
    assert names == ["NoActiveField", "WithActiveTrue"]
    assert model_strengths == [0.5, 0.6]
    assert clip_strengths == [0.3, 0.4]


def test_lora_manager_active_fields_prevent_text_merge(monkeypatch):
    """Test that when structured data has 'active' fields, text is NOT merged.

    This tests the exact LoraManager scenario where:
    - lora_stack has entries with active: true/false
    - lora_syntax/text has ALL loras (including inactive ones)
    Only the active loras from structured data should be captured.
    """
    mod = _load_module(monkeypatch)
    # Simulates LoraManager data format where text contains all loras
    # but structured data has active flags
    input_data = (
        {
            "lora_stack": [
                [
                    {"name": "lenovo_z", "strength": 0.2, "clipStrength": 0.2, "active": False},
                    {"name": "grainscape_zimage", "strength": 0.2, "clipStrength": 0.2, "active": True},
                    {"name": "Marvel_Spectrum", "strength": 1.0, "clipStrength": 1.0, "active": True},
                    {"name": "Rainbow_Brite", "strength": 1.0, "clipStrength": 1.0, "active": False},
                ]
            ],
            # This text contains ALL loras including inactive ones - should be ignored
            # when structured data has 'active' fields
            "lora_syntax": "<lora:lenovo_z:0.2> <lora:grainscape_zimage:0.2> <lora:Marvel_Spectrum:1.0> <lora:Rainbow_Brite:1.0>",
        },
    )
    names = mod.get_lora_model_names("civitai_test", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("civitai_test", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("civitai_test", None, None, None, None, input_data)
    # Only the 2 active loras should be captured - text should NOT re-add inactive ones
    assert names == ["grainscape_zimage", "Marvel_Spectrum"]
    assert model_strengths == [0.2, 1.0]
    assert clip_strengths == [0.2, 1.0]


def test_lora_manager_all_inactive_prevents_text_merge(monkeypatch):
    """Regression: all-inactive structured data must still prevent text merge.

    Even when every entry is filtered out (entries == []), the presence of
    'active' fields must keep skip_text_parsing=True so inactive LoRAs are
    not re-added via the text fallback path.
    """
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "lora_stack": [
                [
                    {"name": "lenovo_z", "strength": 0.2, "clipStrength": 0.2, "active": False},
                    {"name": "Rainbow_Brite", "strength": 1.0, "clipStrength": 1.0, "active": False},
                ]
            ],
            # Text contains the inactive LoRAs - must NOT be merged when 'active' fields present
            "lora_syntax": "<lora:lenovo_z:0.2> <lora:Rainbow_Brite:1.0>",
        },
    )
    names = mod.get_lora_model_names("all_inactive", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("all_inactive", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("all_inactive", None, None, None, None, input_data)
    # All entries inactive -> nothing should be returned; text must not re-add them
    assert names == []
    assert model_strengths == []
    assert clip_strengths == []


def test_lora_manager_lora_loader_syntax_in_lora_name(monkeypatch):
    """Regression: 'Lora Loader (LoraManager)' stores LoRA data in lora_name.

    The node uses ``<lora:name:strength>`` syntax in its ``lora_name`` field.
    Previously ``lora_name`` was not in ``_TEXT_FIELD_CANDIDATES``, causing names
    and hashes to be silently lost.
    """
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "lora_name": "<lora:Hyper-SD15-8steps-CFG-lora:1.00>",
        },
    )
    names = mod.get_lora_model_names("loader_1", None, None, None, None, input_data)
    hashes = mod.get_lora_model_hashes("loader_1", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("loader_1", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("loader_1", None, None, None, None, input_data)
    assert names == ["Hyper-SD15-8steps-CFG-lora"]
    assert hashes == ["hash::Hyper-SD15-8steps-CFG-lora"]
    assert model_strengths == [1.0]
    assert clip_strengths == [1.0]


def test_lora_manager_lora_loader_multiple_loras_in_lora_name(monkeypatch):
    """Regression: multiple LoRAs in lora_name text are all captured."""
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "lora_name": "<lora:LoraA:0.8:0.6> <lora:LoraB:0.5>",
        },
    )
    names = mod.get_lora_model_names("loader_multi", None, None, None, None, input_data)
    hashes = mod.get_lora_model_hashes("loader_multi", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("loader_multi", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("loader_multi", None, None, None, None, input_data)
    assert names == ["LoraA", "LoraB"]
    assert hashes == ["hash::LoraA", "hash::LoraB"]
    assert model_strengths == [0.8, 0.5]
    assert clip_strengths == [0.6, 0.5]


def test_lora_manager_lora_loader_plain_filename_fallback(monkeypatch):
    """Scalar fallback: plain filename in lora_name with strength fields."""
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "lora_name": "my_lora.safetensors",
            "strength_model": 0.75,
            "strength_clip": 0.5,
        },
    )
    names = mod.get_lora_model_names("loader_plain", None, None, None, None, input_data)
    hashes = mod.get_lora_model_hashes("loader_plain", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("loader_plain", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("loader_plain", None, None, None, None, input_data)
    assert names == ["my_lora.safetensors"]
    assert hashes == ["hash::my_lora.safetensors"]
    assert model_strengths == [0.75]
    assert clip_strengths == [0.5]


def test_lora_manager_lora_loader_plain_filename_default_strengths(monkeypatch):
    """Scalar fallback: plain filename without strength fields uses defaults."""
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "lora_name": "my_lora.safetensors",
        },
    )
    names = mod.get_lora_model_names("loader_defaults", None, None, None, None, input_data)
    hashes = mod.get_lora_model_hashes("loader_defaults", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("loader_defaults", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("loader_defaults", None, None, None, None, input_data)
    assert names == ["my_lora.safetensors"]
    assert hashes == ["hash::my_lora.safetensors"]
    assert model_strengths == [1.0]
    assert clip_strengths == [1.0]


def test_lora_manager_lora_name_not_used_when_stack_has_active_data(monkeypatch):
    """lora_name scalar fallback must NOT fire when structured data has results."""
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "lora_stack": [
                [
                    {"name": "StackLoRA", "strength": 0.9, "clipStrength": 0.7, "active": True},
                ]
            ],
            "lora_name": "<lora:ShouldBeIgnored:0.5>",
        },
    )
    names = mod.get_lora_model_names("stack_priority", None, None, None, None, input_data)
    hashes = mod.get_lora_model_hashes("stack_priority", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("stack_priority", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("stack_priority", None, None, None, None, input_data)
    # Only the stack data should appear; lora_name text must not be merged
    # because 'active' fields are present.
    assert names == ["StackLoRA"]
    assert hashes == ["hash::StackLoRA"]
    assert model_strengths == [0.9]
    assert clip_strengths == [0.7]


def test_lora_manager_lora_name_list_input(monkeypatch):
    """lora_name delivered as a list (ComfyUI wraps widget values) is handled."""
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "lora_name": ["<lora:ListLora:0.9:0.4>"],
        },
    )
    names = mod.get_lora_model_names("list_input", None, None, None, None, input_data)
    hashes = mod.get_lora_model_hashes("list_input", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("list_input", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("list_input", None, None, None, None, input_data)
    assert names == ["ListLora"]
    assert hashes == ["hash::ListLora"]
    assert model_strengths == [0.9]
    assert clip_strengths == [0.4]


def test_lora_manager_scalar_fallback_skipped_when_active_fields_present(monkeypatch):
    """Scalar fallback must respect active-field skip behavior."""
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "lora_stack": [
                [
                    {"name": "InactiveA", "strength": 0.2, "clipStrength": 0.2, "active": False},
                ]
            ],
            # If scalar fallback ran while active fields are present, this would be reintroduced.
            "lora_name": "ShouldNotBeReintroduced.safetensors",
            "strength_model": 0.9,
            "strength_clip": 0.8,
        },
    )
    names = mod.get_lora_model_names("active_skip_scalar", None, None, None, None, input_data)
    hashes = mod.get_lora_model_hashes("active_skip_scalar", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("active_skip_scalar", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("active_skip_scalar", None, None, None, None, input_data)
    assert names == []
    assert hashes == []
    assert model_strengths == []
    assert clip_strengths == []


def test_lora_manager_scalar_fallback_unwraps_strength_lists(monkeypatch):
    """Scalar fallback should unwrap ComfyUI-style one-item list strengths."""
    mod = _load_module(monkeypatch)
    input_data = (
        {
            "lora_name": "wrapped_strengths.safetensors",
            "strength_model": [0.35],
            "strength_clip": [0.15],
        },
    )
    names = mod.get_lora_model_names("wrapped_strengths", None, None, None, None, input_data)
    hashes = mod.get_lora_model_hashes("wrapped_strengths", None, None, None, None, input_data)
    model_strengths = mod.get_lora_model_strengths("wrapped_strengths", None, None, None, None, input_data)
    clip_strengths = mod.get_lora_clip_strengths("wrapped_strengths", None, None, None, None, input_data)
    assert names == ["wrapped_strengths.safetensors"]
    assert hashes == ["hash::wrapped_strengths.safetensors"]
    assert model_strengths == [0.35]
    assert clip_strengths == [0.15]
