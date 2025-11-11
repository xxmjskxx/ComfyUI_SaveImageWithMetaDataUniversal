import importlib
import types


def _make_clip(tmp_path, identifier="embedding:"):
    clip_core = types.SimpleNamespace(
        embedding_directory=[str(tmp_path)],
        embedding_identifier=identifier,
    )
    tokenizer = types.SimpleNamespace(clip_l=clip_core)
    return types.SimpleNamespace(tokenizer=tokenizer)


def test_extract_embedding_names_without_clip_returns_empty(monkeypatch):
    fmt = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.formatters"
    )
    monkeypatch.setattr(fmt, "token_weights", lambda text, _: [(text, 1.0)])
    names = fmt.extract_embedding_names(
        "embedding:EasyNegative", ({"text": ["embedding:EasyNegative"]},)
    )
    assert names == []


def test_extract_embedding_names_respects_valid_embeddings(monkeypatch, tmp_path):
    fmt = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.formatters"
    )
    monkeypatch.setattr(fmt, "token_weights", lambda text, _: [(text, 1.0)])
    clip = _make_clip(tmp_path)
    (tmp_path / "EasyNegative.safetensors").write_text("stub")
    assert fmt.get_embedding_file_path("EasyNegative", clip.tokenizer.clip_l) is not None
    names = fmt.extract_embedding_names(
        "embedding:EasyNegative",
        ({"clip": [clip], "text": ["embedding:EasyNegative"]},),
    )
    assert names == ["EasyNegative"]


def test_extract_embedding_names_skips_whitespace_candidates(monkeypatch, tmp_path):
    fmt = importlib.import_module(
        "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.formatters"
    )
    monkeypatch.setattr(fmt, "token_weights", lambda text, _: [(text, 1.0)])
    clip = _make_clip(tmp_path)
    (tmp_path / "foo.safetensors").write_text("stub")
    names = fmt.extract_embedding_names(
        "embedding:foo\u3000bar",
        ({"clip": [clip], "text": ["embedding:foo\u3000bar"]},),
    )
    assert names == []
