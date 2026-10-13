import importlib

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.ext.erenodes"


def _load_module(monkeypatch):
    mod = importlib.import_module(MODULE_PATH)
    monkeypatch.setattr(mod, "resolve_lora_display_names", lambda names: names)
    monkeypatch.setattr(mod, "calc_lora_hash", lambda name, _input: f"hash::{name}")
    mod._NODE_DATA_CACHE.clear()
    return mod


def _capture(mod, node_id, input_data):
    return (
        mod.get_lora_model_names(node_id, None, input_data),
        mod.get_lora_model_hashes(node_id, None, input_data),
        mod.get_lora_model_strengths(node_id, None, input_data),
        mod.get_lora_clip_strengths(node_id, None, input_data),
    )


def test_erenodes_rule_registered():
    mod = importlib.import_module(MODULE_PATH)
    rules = mod.CAPTURE_FIELD_LIST["ErePromptLoraLoader"]
    assert rules[mod.MetaField.LORA_MODEL_NAME]["selector"] is mod.get_lora_model_names
    assert rules[mod.MetaField.LORA_STRENGTH_CLIP]["selector"] is mod.get_lora_clip_strengths


def test_erenodes_text_only(monkeypatch):
    mod = _load_module(monkeypatch)
    input_data = [{"text": ["1girl, <lora:Foo:0.8:0.3>, smile, <lora:Bar:0.25>"]}]
    names, hashes, model_strengths, clip_strengths = _capture(mod, "1", input_data)
    assert names == ["Foo", "Bar"]
    assert hashes == ["hash::Foo", "hash::Bar"]
    assert model_strengths == [0.8, 0.25]
    assert clip_strengths == [0.3, 0.25]


def test_erenodes_prefix_applied_first(monkeypatch):
    mod = _load_module(monkeypatch)
    # `prefix` is the resolved output of an upstream prompt node.
    input_data = [{"prefix": ["<lora:Upstream:0.6>, a cat"], "text": ["<lora:Own:0.9>"]}]
    names, _hashes, model_strengths, _clip = _capture(mod, "2", input_data)
    assert names == ["Upstream", "Own"]
    assert model_strengths == [0.6, 0.9]


def test_erenodes_lora_in_both_counted_once(monkeypatch):
    mod = _load_module(monkeypatch)
    # The node applies a LoRA once, with the strength it was first named with.
    input_data = [{"prefix": ["<lora:Shared:0.4>"], "text": ["<lora:shared:1.0>, <lora:Other:0.5>"]}]
    names, _hashes, model_strengths, _clip = _capture(mod, "3", input_data)
    assert names == ["Shared", "Other"]
    assert model_strengths == [0.4, 0.5]


def test_erenodes_zero_strength_skipped(monkeypatch):
    mod = _load_module(monkeypatch)
    input_data = [{"text": ["<lora:Off:0:0>, <lora:On:0.7>, <lora:ClipOnly:0:0.5>"]}]
    names, _hashes, model_strengths, clip_strengths = _capture(mod, "4", input_data)
    assert names == ["On", "ClipOnly"]
    assert model_strengths == [0.7, 0.0]
    assert clip_strengths == [0.7, 0.5]


def test_erenodes_no_loras(monkeypatch):
    mod = _load_module(monkeypatch)
    assert _capture(mod, "5", [{"text": ["just a prompt"]}]) == ([], [], [], [])
    assert _capture(mod, "6", [{}]) == ([], [], [], [])


def test_erenodes_cache_follows_input(monkeypatch):
    mod = _load_module(monkeypatch)
    assert mod.get_lora_model_names("7", None, [{"text": ["<lora:First:1>"]}]) == ["First"]
    assert mod.get_lora_model_names("7", None, [{"text": ["<lora:Second:1>"]}]) == ["Second"]
