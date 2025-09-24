import importlib
from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture"


def test_embedding_hash_detail_construction(monkeypatch):
    cap = importlib.import_module(MODULE_PATH)

    # Simulate inputs containing embedding names and hashes
    inputs = {
        MetaField.EMBEDDING_NAME: [("n1", "myEmbedding.safetensors")],
        MetaField.EMBEDDING_HASH: [("n1", "deadbeef")],
    }

    # gen_embeddings should produce grouped fields
    emb_pnginfo = cap.Capture.gen_embeddings(inputs)
    # Expect prefix Embedding_0 name/hash
    assert any(k.startswith("Embedding_0 name") for k in emb_pnginfo.keys())
    assert any(k.startswith("Embedding_0 hash") for k in emb_pnginfo.keys())
