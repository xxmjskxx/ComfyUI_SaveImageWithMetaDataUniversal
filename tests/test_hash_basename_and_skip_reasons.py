import logging
import types

from saveimage_unimeta.defs import formatters


def test_model_basename_retry(tmp_path, monkeypatch):
    # Create file only accessible via basename retry (token includes path separators)
    model_file = tmp_path / "nested" / "retryModel.safetensors"
    model_file.parent.mkdir(parents=True, exist_ok=True)
    model_file.write_text("content-retry", encoding="utf-8")

    import folder_paths

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


def test_ckpt_index_resolver_uses_basename_for_subdir_tokens(tmp_path, monkeypatch):
    model_file = tmp_path / "checkpoints" / "retryModel.safetensors"
    model_file.parent.mkdir(parents=True, exist_ok=True)
    model_file.write_text("content-retry", encoding="utf-8")
    queried_keys: list[str] = []

    def _fake_try_resolve_artifact(_kind, _name_like, post_resolvers=None):
        resolved = post_resolvers[0]("nested/retryModel.safetensors") if post_resolvers else None
        return types.SimpleNamespace(display_name="retryModel", full_path=resolved)

    def _fake_find_checkpoint_info(key):
        queried_keys.append(key)
        if key == "retryModel":
            return {"abspath": str(model_file)}
        return None

    monkeypatch.setattr(formatters, "try_resolve_artifact", _fake_try_resolve_artifact)
    monkeypatch.setattr(formatters, "find_checkpoint_info", _fake_find_checkpoint_info)
    # Force the index resolver to engage even though LoraManager isn't installed in CI.
    monkeypatch.setattr(formatters, "_get_lm_checkpoint_dirs", lambda: ["<test-lm-dir>"])

    display, path = formatters._ckpt_name_to_path("nested/retryModel.safetensors")

    assert display == "retryModel"
    assert path == str(model_file)
    assert queried_keys == ["retryModel"]


def test_unet_index_resolver_uses_basename_for_subdir_tokens(tmp_path, monkeypatch):
    model_file = tmp_path / "unet" / "flux1-dev.safetensors"
    model_file.parent.mkdir(parents=True, exist_ok=True)
    model_file.write_text("content-unet", encoding="utf-8")
    queried_keys: list[str] = []

    def _fake_try_resolve_artifact(_kind, _name_like, post_resolvers=None):
        resolved = post_resolvers[0]("nested/flux1-dev.safetensors") if post_resolvers else None
        return types.SimpleNamespace(display_name="flux1-dev", full_path=resolved)

    def _fake_find_unet_info(key):
        queried_keys.append(key)
        if key == "flux1-dev":
            return {"abspath": str(model_file)}
        return None

    monkeypatch.setattr(formatters, "try_resolve_artifact", _fake_try_resolve_artifact)
    monkeypatch.setattr(formatters, "find_unet_info", _fake_find_unet_info)
    monkeypatch.setattr(formatters, "_hash_file", lambda *_args, **_kwargs: "1234567890")
    # Force the index resolver to engage even though LoraManager isn't installed in CI.
    monkeypatch.setattr(formatters, "_get_lm_unet_dirs", lambda: ["<test-lm-dir>"])

    result = formatters.calc_unet_hash("nested/flux1-dev.safetensors", None)

    assert result == "1234567890"
    assert queried_keys == ["flux1-dev"]
