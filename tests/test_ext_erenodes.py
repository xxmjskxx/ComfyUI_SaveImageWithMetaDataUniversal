import importlib

import pytest

from .test_helpers import install_prompt_environment

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.ext.erenodes"
_CAPTURE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture"


def _load_module(monkeypatch, available=None):
    mod = importlib.import_module(MODULE_PATH)
    if available is None:
        available = [f"{name}.safetensors" for name in (
            "Foo", "Bar", "Upstream", "Own", "Shared", "Other",
            "Off", "On", "ClipOnly", "First", "Second",
        )]
    monkeypatch.setattr(mod.folder_paths, "get_filename_list", lambda _kind: available, raising=False)
    monkeypatch.setattr(mod, "calc_lora_hash", lambda name, _input: f"hash::{name}")
    mod._NODE_DATA_CACHE.clear()
    return mod


def _input_data(text="", prefix="", model=True, clip=True):
    batch = {"text": [text], "prefix": [prefix]}
    if model:
        batch["model"] = [object()]
    if clip:
        batch["clip"] = [object()]
    return (batch,)


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
    data = _input_data("1girl, <lora:Foo:0.8:0.3>, smile, <lora:Bar:0.25>")
    assert _capture(mod, "1", data) == (
        ["Foo.safetensors", "Bar.safetensors"],
        ["hash::Foo.safetensors", "hash::Bar.safetensors"],
        [0.8, 0.25],
        [0.3, 0.25],
    )


def test_erenodes_prefix_applied_first(monkeypatch):
    mod = _load_module(monkeypatch)
    data = _input_data("<lora:Own:0.9>", prefix="<lora:Upstream:0.6>, a cat")
    names, _hashes, strengths, _clip = _capture(mod, "2", data)
    assert names == ["Upstream.safetensors", "Own.safetensors"]
    assert strengths == [0.6, 0.9]


@pytest.mark.parametrize("alias", ["shared", "Shared.safetensors", "SHARED.SAFETENSORS"])
def test_erenodes_lora_in_both_counted_once(monkeypatch, alias):
    mod = _load_module(monkeypatch)
    data = _input_data(f"<lora:{alias}:1.0>, <lora:Other:0.5>", prefix="<lora:Shared:0.4>")
    names, _hashes, strengths, _clip = _capture(mod, "3", data)
    assert names == ["Shared.safetensors", "Other.safetensors"]
    assert strengths == [0.4, 0.5]


@pytest.mark.parametrize("alias", ["Foo.safetensors", "foo", "folder\\Foo.safetensors"])
def test_erenodes_disabled_first_alias_stays_disabled(monkeypatch, alias):
    mod = _load_module(monkeypatch, ["folder/Foo.safetensors"])
    data = _input_data(f"<lora:{alias}:1.0>", prefix="<lora:folder/Foo:0:0>")
    assert _capture(mod, "alias", data) == ([], [], [], [])


def test_erenodes_zero_strength_skipped(monkeypatch):
    mod = _load_module(monkeypatch)
    data = _input_data("<lora:Off:0:0>, <lora:On:0.7>, <lora:ClipOnly:0:0.5>")
    names, _hashes, model_strengths, clip_strengths = _capture(mod, "4", data)
    assert names == ["On.safetensors", "ClipOnly.safetensors"]
    assert model_strengths == [0.7, 0.0]
    assert clip_strengths == [0.7, 0.5]


@pytest.mark.parametrize(("tag", "model_strength", "clip_strength"), [
    ("<lora:Foo>", 1.0, 1.0),
    ("<lora:Foo:-0.5>", -0.5, -0.5),
    ("<lora:Foo:0.8:-0.2>", 0.8, -0.2),
    ("<lora:Foo:-0.5:0.2>", -0.5, 0.2),
    ("<lora:Foo:.7>", 0.7, 0.7),
    ("<lora:Foo:..:0.2>", 1.0, 0.2),
    ("<lora:Foo:0.7:..>", 0.7, 0.7),
])
def test_erenodes_strength_syntax(monkeypatch, tag, model_strength, clip_strength):
    mod = _load_module(monkeypatch)
    names, _hashes, ms, cs = _capture(mod, "syntax", _input_data(tag))
    assert names == ["Foo.safetensors"]
    assert ms == [model_strength]
    assert cs == [clip_strength]


def test_erenodes_mixed_default_positive_and_negative_strengths(monkeypatch):
    mod = _load_module(monkeypatch)
    data = _input_data("<lora:Foo:0.8>, <lora:Bar:-0.5:0.2>, <lora:Other>")
    names, _hashes, ms, cs = _capture(mod, "mixed", data)
    assert names == ["Foo.safetensors", "Bar.safetensors", "Other.safetensors"]
    assert ms == [0.8, -0.5, 1.0]
    assert cs == [0.8, 0.2, 1.0]


@pytest.mark.parametrize("tag", ["<lora:Foo:1e-1>", "<lora:Foo:+1>", "<lora:Foo:1:1:1>", "<lora:Foo:>"])
def test_erenodes_unsupported_tags_are_not_captured(monkeypatch, tag):
    mod = _load_module(monkeypatch)
    assert _capture(mod, "invalid", _input_data(tag)) == ([], [], [], [])


@pytest.mark.parametrize("value", [None, [], [None]])
def test_erenodes_missing_model_skipped(monkeypatch, value):
    mod = _load_module(monkeypatch)
    data = _input_data("<lora:Foo:0.7>", model=False)
    data[0]["model"] = value
    assert _capture(mod, "no-model", data) == ([], [], [], [])


@pytest.mark.parametrize("value", [None, [], [None]])
def test_erenodes_missing_clip_zeros_strength_and_skips_clip_only(monkeypatch, value):
    mod = _load_module(monkeypatch)
    data = _input_data("<lora:Foo:0:0.5>, <lora:Bar:0.7:0.2>", clip=False)
    data[0]["clip"] = value
    assert _capture(mod, "no-clip", data) == (
        ["Bar.safetensors"], ["hash::Bar.safetensors"], [0.7], [0.0],
    )


def test_erenodes_omitted_inputs_and_scalar_objects(monkeypatch):
    mod = _load_module(monkeypatch)
    assert _capture(mod, "omitted-model", _input_data("<lora:Foo>", model=False)) == ([], [], [], [])
    data = _input_data("<lora:Foo>", clip=False)
    data[0]["model"] = object()
    assert _capture(mod, "scalar-model", data)[3] == [0.0]
    data[0]["clip"] = object()
    assert _capture(mod, "scalar-model", data)[3] == [1.0]


def test_erenodes_missing_files_skipped(monkeypatch):
    mod = _load_module(monkeypatch, ["Foo.safetensors"])
    assert _capture(mod, "missing-file", _input_data("<lora:Missing>, <lora:Foo>")) == (
        ["Foo.safetensors"], ["hash::Foo.safetensors"], [1.0], [1.0],
    )


def test_erenodes_relative_paths_preserve_file_identity_for_hashes(monkeypatch):
    mod = _load_module(monkeypatch, ["a/Foo.safetensors", "b/Foo.safetensors"])
    data = _input_data("<lora:a\\Foo:0.4>, <lora:b/Foo.safetensors:0.9>")
    assert _capture(mod, "paths", data) == (
        ["a/Foo.safetensors", "b/Foo.safetensors"],
        ["hash::a/Foo.safetensors", "hash::b/Foo.safetensors"],
        [0.4, 0.9], [0.4, 0.9],
    )


def test_erenodes_full_path_precedes_basename_match(monkeypatch):
    mod = _load_module(monkeypatch, ["a/Foo.safetensors", "Foo.safetensors"])
    assert _capture(mod, "precedence", _input_data("<lora:Foo>"))[0] == ["Foo.safetensors"]


def test_erenodes_no_loras(monkeypatch):
    mod = _load_module(monkeypatch)
    assert _capture(mod, "5", _input_data("just a prompt")) == ([], [], [], [])
    assert _capture(mod, "6", [{}]) == ([], [], [], [])


def test_erenodes_cache_follows_input(monkeypatch):
    mod = _load_module(monkeypatch)
    assert _capture(mod, "7", _input_data("<lora:First:1>"))[0] == ["First.safetensors"]
    assert _capture(mod, "7", _input_data("<lora:Second:1>"))[0] == ["Second.safetensors"]
    assert _capture(mod, "7", _input_data("<lora:Second:1>", prefix="<lora:First:0.4>"))[0] == [
        "First.safetensors", "Second.safetensors",
    ]


def test_erenodes_cache_follows_model_and_clip_availability(monkeypatch):
    mod = _load_module(monkeypatch)
    tag = "<lora:Foo:0:0.5>"
    assert _capture(mod, "cache", _input_data(tag))[3] == [0.5]
    assert _capture(mod, "cache", _input_data(tag, clip=False)) == ([], [], [], [])
    assert _capture(mod, "cache", _input_data(tag, model=False)) == ([], [], [], [])
    assert _capture(mod, "cache", _input_data(tag))[3] == [0.5]


def test_erenodes_cache_follows_registered_files(monkeypatch):
    available = ["Foo.safetensors"]
    mod = _load_module(monkeypatch, available)
    data = _input_data("<lora:Foo>")
    assert _capture(mod, "cache-files", data)[0] == ["Foo.safetensors"]
    available.clear()
    assert _capture(mod, "cache-files", data) == ([], [], [], [])
    available.append("folder/Foo.safetensors")
    assert _capture(mod, "cache-files", data)[0] == ["folder/Foo.safetensors"]


def test_erenodes_selectors_share_cached_hashes(monkeypatch):
    mod = _load_module(monkeypatch)
    calls = []
    monkeypatch.setattr(mod, "calc_lora_hash", lambda name, _data: calls.append(name) or f"hash::{name}")
    _capture(mod, "cache-hashes", _input_data("<lora:Foo>, <lora:Bar>"))
    assert calls == ["Foo.safetensors", "Bar.safetensors"]


def test_erenodes_capture_reaches_pnginfo_with_aligned_loras(monkeypatch):
    mod = _load_module(monkeypatch)
    cap = importlib.import_module(_CAPTURE_PATH)
    prompt = {"loader": {"class_type": "ErePromptLoraLoader", "inputs": {
        "prefix": "<lora:Foo>, a cat",
        "text": "<lora:Bar:-0.5:0.2>, <lora:Foo.safetensors:0.9>",
        "model": object(),
        "clip": object(),
    }}}
    install_prompt_environment(monkeypatch, cap, prompt)
    monkeypatch.setattr(cap, "CAPTURE_FIELD_LIST", mod.CAPTURE_FIELD_LIST)
    # Preserve the supplied hashes during downstream record normalization.
    monkeypatch.setattr(cap, "calc_lora_hash", mod.calc_lora_hash)
    inputs = cap.Capture.get_inputs()
    pnginfo = cap.Capture.gen_loras(inputs)
    assert pnginfo == {
        "Lora_0 Model name": "Foo.safetensors",
        "Lora_0 Model hash": "hash::Foo.safetensors",
        "Lora_0 Strength model": 1.0,
        "Lora_0 Strength clip": 1.0,
        "Lora_1 Model name": "Bar.safetensors",
        "Lora_1 Model hash": "hash::Bar.safetensors",
        "Lora_1 Strength model": -0.5,
        "Lora_1 Strength clip": 0.2,
    }

@pytest.mark.parametrize("name", ["./Foo", "folder/../Foo"])
def test_erenodes_unresolved_names_normalized_before_apply(monkeypatch, name):
    mod = _load_module(monkeypatch)
    assert _capture(mod, "normalized", _input_data(f"<lora:{name}>")) == (
        ["Foo.safetensors"], ["hash::Foo.safetensors"], [1.0], [1.0],
    )
