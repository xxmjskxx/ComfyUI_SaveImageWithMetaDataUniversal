import importlib
import types


def _make_clip(tmp_path, identifier="embedding:"):
    clip_core = types.SimpleNamespace(
        embedding_directory=[str(tmp_path)],
        embedding_identifier=identifier,
    )
    tokenizer = types.SimpleNamespace(clip_l=clip_core)
    return types.SimpleNamespace(tokenizer=tokenizer)


def test_extract_embedding_names_without_clip_records_token(monkeypatch):
    fmt = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.formatters")
    monkeypatch.setattr(fmt, "token_weights", lambda text: [(text, 1.0)])
    names = fmt.extract_embedding_names("embedding:EasyNegative", ({"text": ["embedding:EasyNegative"]},))
    assert names == ["EasyNegative"]


def test_extract_embedding_names_respects_valid_embeddings(monkeypatch, tmp_path):
    fmt = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.formatters")
    monkeypatch.setattr(fmt, "token_weights", lambda text: [(text, 1.0)])
    clip = _make_clip(tmp_path)
    (tmp_path / "EasyNegative.safetensors").write_text("stub")
    assert fmt.get_embedding_file_path("EasyNegative", clip.tokenizer.clip_l) is not None
    names = fmt.extract_embedding_names(
        "embedding:EasyNegative",
        ({"clip": [clip], "text": ["embedding:EasyNegative"]},),
    )
    assert names == ["EasyNegative"]


def test_extract_embedding_names_skips_whitespace_candidates(monkeypatch, tmp_path):
    fmt = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.formatters")
    monkeypatch.setattr(fmt, "token_weights", lambda text: [(text, 1.0)])
    clip = _make_clip(tmp_path)
    (tmp_path / "foo.safetensors").write_text("stub")
    names = fmt.extract_embedding_names(
        "embedding:foo\u3000bar",
        ({"clip": [clip], "text": ["embedding:foo\u3000bar"]},),
    )
    assert names == []


def test_extract_embedding_hashes_without_clip_returns_na(monkeypatch):
    fmt = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.formatters")
    monkeypatch.setattr(fmt, "token_weights", lambda text: [(text, 1.0)])
    hashes = fmt.extract_embedding_hashes("embedding:EasyNegative", ({"text": ["embedding:EasyNegative"]},))
    assert hashes == ["N/A"]


def test_extract_embedding_hashes_create_sidecar(monkeypatch, tmp_path):
    """Embedding hashing should reuse the shared helper so .sha256 sidecars exist."""

    fmt = importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.formatters")
    monkeypatch.setattr(fmt, "token_weights", lambda text: [(text, 1.0)])
    clip = _make_clip(tmp_path)
    embed_path = tmp_path / "FastNegativeV2.safetensors"
    embed_path.write_text("hash me", encoding="utf-8")

    stub_input = ({"clip": [clip], "text": [f"embedding:{embed_path.stem}"]},)
    hashes = fmt.extract_embedding_hashes(f"embedding:{embed_path.stem}", stub_input)

    assert hashes and len(hashes[0]) == 10
    sidecar = embed_path.with_suffix(".sha256")
    assert sidecar.exists(), "Embedding hashing must create a .sha256 sidecar"
    assert len(sidecar.read_text().strip()) == 64
