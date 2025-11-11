import logging

from saveimage_unimeta.defs import formatters


def test_model_basename_retry(tmp_path, monkeypatch):
    # Create file only accessible via basename retry (token includes path separators)
    model_file = tmp_path / "nested" / "retryModel.safetensors"
    model_file.parent.mkdir(parents=True, exist_ok=True)
    model_file.write_text("content-retry", encoding="utf-8")

    import folder_paths  # type: ignore

    # First lookup with token 'some/sub/dirs/retryModel' should fail direct resolution; basename retry should succeed
    def _gf(kind, name):
        # Only succeed when name exactly matches basename
        if name == model_file.name:
            return str(model_file)
        return None

    monkeypatch.setattr(folder_paths, "get_full_path", _gf)
    captured: list[str] = []
    monkeypatch.setattr(formatters, "_log", lambda k, m, level=logging.INFO: captured.append(m))
    formatters.set_hash_log_mode("debug")
    # Include extension in the provided token path to reduce dependence on extension probing nuances
    h = formatters.calc_model_hash("some/sub/dirs/retryModel.safetensors", None)
    assert len(h) == 10, h
    joined = "\n".join(captured)
    assert "retry basename=retryModel" in joined
    assert "basename resolved retryModel" in joined


def test_hash_skipped_reason_debug(monkeypatch):
    captured: list[str] = []
    monkeypatch.setattr(formatters, "_log", lambda k, m, level=logging.INFO: captured.append(m))
    formatters.set_hash_log_mode("debug")
    # Unresolvable model
    h1 = formatters.calc_model_hash("does_not_exist_model_123", None)
    assert h1 == "N/A"
    # Unresolvable lora
    h2 = formatters.calc_lora_hash("ghost_lora_999", None)
    assert h2 == "N/A"
    # Unresolvable unet
    h3 = formatters.calc_unet_hash("phantom_unet_777", None)
    assert h3 == "N/A"
    log_all = "\n".join(captured)
    # Ensure skip reasons present for each artifact type
    assert "hash skipped reason=unresolved token=does_not_exist_model_123" in log_all
    assert "hash skipped reason=unresolved token=ghost_lora_999" in log_all
    assert "hash skipped reason=unresolved token=phantom_unet_777" in log_all
