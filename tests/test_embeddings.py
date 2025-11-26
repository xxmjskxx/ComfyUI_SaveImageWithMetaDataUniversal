import importlib

from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField
from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.utils.hash import calc_hash

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture"


def _build_inputs(*, positive: str | None = None, negative: str | None = None):
    inputs = {}
    if positive is not None:
        inputs[MetaField.POSITIVE_PROMPT] = [("pos-node", positive, "text")]
    if negative is not None:
        inputs[MetaField.NEGATIVE_PROMPT] = [("neg-node", negative, "text")]
    return inputs


def test_prompt_scan_populates_embeddings(monkeypatch, tmp_path):
    cap = importlib.import_module(MODULE_PATH)
    embed_dir = tmp_path / "embeddings"
    embed_dir.mkdir()
    file_path = embed_dir / "FastNegativeV2.safetensors"
    file_path.write_text("dummy hash content", encoding="utf-8")

    def fake_get_folder_paths(kind):  # pragma: no cover - deterministic helper
        if kind == "embeddings":
            return [str(embed_dir)]
        return []

    monkeypatch.setattr(cap.folder_paths, "get_folder_paths", fake_get_folder_paths)

    prompt_text = f"masterpiece embedding:{file_path.stem} lighting"
    inputs = _build_inputs(positive=prompt_text)
    cap.Capture._augment_embeddings_from_prompts(inputs)

    names = [cap.Capture._extract_value(entry) for entry in inputs[MetaField.EMBEDDING_NAME]]
    hashes = [cap.Capture._extract_value(entry) for entry in inputs[MetaField.EMBEDDING_HASH]]

    assert any(file_path.stem in name for name in names)
    expected_hash = calc_hash(str(file_path))[:10]
    assert expected_hash in hashes


def test_prompt_scan_writes_embedding_sidecar(monkeypatch, tmp_path):
    """Prompt augmentation should create .sha256 files for discovered embeddings."""

    cap = importlib.import_module(MODULE_PATH)
    embed_dir = tmp_path / "embeddings"
    embed_dir.mkdir()
    file_path = embed_dir / "PromptSidecar.safetensors"
    file_path.write_text("from prompt", encoding="utf-8")

    def fake_get_folder_paths(kind):
        if kind == "embeddings":
            return [str(embed_dir)]
        return []

    monkeypatch.setattr(cap.folder_paths, "get_folder_paths", fake_get_folder_paths)

    inputs = _build_inputs(positive=f"embedding:{file_path.stem}")
    cap.Capture._augment_embeddings_from_prompts(inputs)

    sidecar = file_path.with_suffix(".sha256")
    assert sidecar.exists(), "Prompt-driven embedding capture must create sidecars"
    assert len(sidecar.read_text().strip()) == 64


def test_prompt_scan_deduplicates_and_handles_negative(monkeypatch):
    cap = importlib.import_module(MODULE_PATH)

    inputs = _build_inputs(
        positive="portrait embedding:dupStyle",
        negative="stormy sky embedding:negToken",
    )
    # Pretend a loader already captured the duplicate embedding
    inputs[MetaField.EMBEDDING_NAME] = [("loader", "dupStyle.safetensors", "node_field")]

    cap.Capture._augment_embeddings_from_prompts(inputs)

    names = [
        cap.Capture._clean_name(cap.Capture._extract_value(entry), drop_extension=True).lower()
        for entry in inputs[MetaField.EMBEDDING_NAME]
    ]
    assert names.count("dupstyle") == 1  # no duplicate for existing entry
    assert "negtoken" in names  # negative prompt embedding captured

    hashes = [cap.Capture._extract_value(entry) for entry in inputs.get(MetaField.EMBEDDING_HASH, [])]
    assert any(hash_val == "N/A" for hash_val in hashes)
