from saveimage_unimeta.nodes.rules_save import SaveGeneratedUserRules


def test_save_generated_rules_is_deprecated_noop(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (status,) = SaveGeneratedUserRules().save_rules("CAPTURE_FIELD_LIST = {}\n", append=False)
    assert "Deprecated" in status
    assert list(tmp_path.iterdir()) == []
    # Inputs stay unchanged so saved workflows containing the node still load.
    assert set(SaveGeneratedUserRules.INPUT_TYPES()["required"]) == {"rules_text", "append"}
