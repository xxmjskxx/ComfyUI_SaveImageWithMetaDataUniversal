
import os
import pytest
from unittest.mock import MagicMock, patch
from saveimage_unimeta.capture import Capture, _LoRARecord, _include_lora_summary, _include_hash_detail, _debug_prompts_enabled, _OutputCacheCompat
from saveimage_unimeta.defs.meta import MetaField

def test_clean_name_tuple_variants():
    # Test _clean_name with tuple variants
    assert Capture._clean_name((42, "model.safetensors"), drop_extension=True) == "model"
    assert Capture._clean_name(("model.safetensors",), drop_extension=True) == "model"
    assert Capture._clean_name([], drop_extension=True) == "unknown"
    assert Capture._clean_name("model.safetensors", drop_extension=True) == "model"
    # Test path cleanup
    assert Capture._clean_name("path/to/model.safetensors", drop_extension=True) == "model"
    assert Capture._clean_name("path\\to\\model.safetensors", drop_extension=True) == "model"

def test_extract_value_variants():
    assert Capture._extract_value((42, "val")) == "val"
    assert Capture._extract_value(("val",)) == "val"
    assert Capture._extract_value("val") == "val"
    assert Capture._extract_value([]) is None

def test_looks_like_hex_hash():
    assert Capture._looks_like_hex_hash("1234567890abcdef") is True
    assert Capture._looks_like_hex_hash("123") is False
    assert Capture._looks_like_hex_hash(123) is False
    assert Capture._looks_like_hex_hash("not a hash") is False
    assert Capture._looks_like_hex_hash("A" * 65) is False

def test_build_prompt_embedding_stub_input():
    # It mocks folder_paths.get_folder_paths if available, or empty list
    stub = Capture._build_prompt_embedding_stub_input()
    assert isinstance(stub, tuple)
    assert "clip" in stub[0]

def test_debug_prompts_enabled(monkeypatch):
    monkeypatch.setenv("METADATA_DEBUG_PROMPTS", "1")
    assert _debug_prompts_enabled() is True
    monkeypatch.delenv("METADATA_DEBUG_PROMPTS")
    assert _debug_prompts_enabled() is False

def test_include_hash_detail(monkeypatch):
    monkeypatch.setenv("METADATA_NO_HASH_DETAIL", "1")
    assert _include_hash_detail() is False
    monkeypatch.delenv("METADATA_NO_HASH_DETAIL")
    assert _include_hash_detail() is True

def test_include_lora_summary(monkeypatch):
    monkeypatch.setenv("METADATA_NO_LORA_SUMMARY", "1")
    assert _include_lora_summary() is False
    monkeypatch.delenv("METADATA_NO_LORA_SUMMARY")
    assert _include_lora_summary() is True

def test_output_cache_compat():
    compat = _OutputCacheCompat({"1": "output"})
    assert compat.get_output_cache("1", "2") == "output"
    assert compat.get_cache("1", "2") == "output"
    assert compat.get_output_cache("3", "2") is None

def test_augment_embeddings_from_prompts():
    inputs = {
        MetaField.POSITIVE_PROMPT: [("src", "embedding:test_embed")],
        MetaField.EMBEDDING_NAME: []
    }
    # We need to mock extract_embedding_names/hashes in Capture
    with patch("saveimage_unimeta.capture.extract_embedding_names", return_value=["test_embed.pt"]):
        with patch("saveimage_unimeta.capture.extract_embedding_hashes", return_value=["hash123"]):
             Capture._augment_embeddings_from_prompts(inputs)

    assert len(inputs[MetaField.EMBEDDING_NAME]) == 1
    assert inputs[MetaField.EMBEDDING_NAME][0][1] == "test_embed.pt"
    assert inputs[MetaField.EMBEDDING_HASH][0][1] == "hash123"

def test_deduplicate_lora_records():
    r1 = _LoRARecord("lora1", "hash1", 1.0, 1.0)
    r2 = _LoRARecord("lora1", "hash2", 1.0, 1.0) # duplicate name
    r3 = _LoRARecord("lora2", "hash3", 1.0, 1.0)

    dedup = Capture._deduplicate_lora_records([r1, r2, r3])
    assert len(dedup) == 2
    # Should prefer hash if available (both have hashes, first one kept? Or hashed preferred over unhashed)
    # The logic is: keys by name. Then entries. with_hash = [e for e in entries if e.hash ...]
    # dedup.append(with_hash[0] if with_hash else entries[0])
    # Both have hashes, so r1 is kept as it is first in filtered list (which preserves order)
    assert dedup[0].name == "lora1"
    assert dedup[1].name == "lora2"

def test_is_invalid_lora_name():
    assert Capture._is_invalid_lora_name("N/A")
    assert Capture._is_invalid_lora_name("none")
    assert Capture._is_invalid_lora_name("")
    assert Capture._is_invalid_lora_name("1.0") # numeric
    assert not Capture._is_invalid_lora_name("my_lora")
    assert not Capture._is_invalid_lora_name("path/to/lora") # slashes allowed?
    # Logic: if any(ch in stripped for ch in ("/", "\\")): return False (valid)

def test_resolve_lora_hash():
    # Mock calc_lora_hash
    with patch("saveimage_unimeta.capture.calc_lora_hash", return_value="calculated_hash"):
        h = Capture._resolve_lora_hash("lora", "captured", "token")
        assert h == "calculated_hash"

    with patch("saveimage_unimeta.capture.calc_lora_hash", side_effect=Exception("Fail")):
        h = Capture._resolve_lora_hash("lora", "captured", "token")
        assert h == "captured"

def test_get_sampler_for_civitai_fallbacks():
    # Case: Sampler object with no name
    obj = MagicMock()
    del obj.sampler_name
    del obj.name
    # But has sampler_name in __dict__? or attribute
    # The code probes attributes.

    # Test logic where sampler is found via heuristic scan
    # KNOWN_TOKENS = {"euler", ...}

    # Test fallback to scheduler if sampler missing
    res = Capture.get_sampler_for_civitai([], [("id", "normal")])
    assert res == "normal"

    # Test unknown sampler + scheduler
    res = Capture.get_sampler_for_civitai([("id", "unknown_sampler")], [("id", "normal")])
    assert res == "unknown_sampler"

    res = Capture.get_sampler_for_civitai([("id", "unknown_sampler")], [("id", "karras")])
    assert res == "unknown_sampler_karras"

def test_add_hash_detail_section(monkeypatch):
    monkeypatch.delenv("METADATA_NO_HASH_DETAIL", raising=False)
    pnginfo = {"Model": "m", "Model hash": "h"}
    Capture.add_hash_detail_section(pnginfo)
    assert "Hash detail" in pnginfo
    assert '"model": {"hash": "h", "name": "m"}' in pnginfo["Hash detail"]

def test_gen_pnginfo_dict_multi_sampler():
    # Test multi sampler entries formatting
    meta = {
        "__multi_sampler_entries": [{"sampler_name": "s1", "start_step": 0, "end_step": 10}, {"sampler_name": "s2", "start_step": 10, "end_step": 20}]
    }
    # This logic is in gen_parameters_str
    res = Capture.gen_parameters_str(meta)
    assert "Samplers: s1 (0-10) | s2 (10-20)" in res

def test_gen_parameters_str_guidance_as_cfg():
    pnginfo = {"Guidance": 3.5}
    res = Capture.gen_parameters_str(pnginfo, guidance_as_cfg=True)
    assert "CFG scale: 3.5" in res
    assert "Guidance:" not in res

def test_gen_parameters_str_dual_prompt_suppression():
    pnginfo = {"Positive prompt": "pos", "T5 Prompt": "t5", "CLIP Prompt": "clip", "Negative prompt": "neg"}
    res = Capture.gen_parameters_str(pnginfo)
    assert "T5 Prompt: t5" in res
    assert "CLIP Prompt: clip" in res
    assert "Positive prompt:" not in res # Suppressed because dual prompt present
