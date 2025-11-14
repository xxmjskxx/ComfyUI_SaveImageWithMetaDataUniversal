import importlib
import os


def _rules_save_node():
    return importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.rules_save")


def _rules_path(mod):
    node = mod.SaveGeneratedUserRules()
    return node._rules_path()


def _cleanup(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def test_rules_save_rejects_invalid_syntax():
    mod = _rules_save_node()
    node = mod.SaveGeneratedUserRules()
    (status,) = node.save_rules("CAPTURE_FIELD_LIST = {")  # unterminated dict
    assert status.startswith("Refused to write: provided text has errors.")


def test_rules_save_create_and_overwrite(tmp_path):
    mod = _rules_save_node()
    node = mod.SaveGeneratedUserRules()
    path = _rules_path(mod)
    _cleanup(path)

    content_v1 = "KNOWN = {}\n\nSAMPLERS = {}\n\nCAPTURE_FIELD_LIST = {\n}\n"
    (status,) = node.save_rules(content_v1, append=False)
    assert status.startswith("Overwritten") or status.startswith("Created")
    assert os.path.exists(path)

    with open(path, encoding="utf-8") as f:
        result = f.read()
        # Version header should be injected
        assert 'GENERATED_RULES_VERSION = ' in result
        assert 'KNOWN = {}' in result
        assert 'SAMPLERS = {}' in result
        assert 'CAPTURE_FIELD_LIST = {' in result

    content_v2 = 'KNOWN = {}\n\nSAMPLERS = {"X": {}}\n\nCAPTURE_FIELD_LIST = {\n}\n'
    (status2,) = node.save_rules(content_v2, append=False)
    assert status2.startswith("Overwritten")
    with open(path, encoding="utf-8") as f:
        result2 = f.read()
        # Version header should be present
        assert 'GENERATED_RULES_VERSION = ' in result2
        assert '"X"' in result2


def test_rules_save_merge_updates_and_appends():
    mod = _rules_save_node()
    node = mod.SaveGeneratedUserRules()
    path = _rules_path(mod)
    _cleanup(path)

    base = (
        "KNOWN = {}\n\n"
        'SAMPLERS = {"A": {}}\n\n'
        "CAPTURE_FIELD_LIST = {\n"
        '    "Node1": {\n'
        '        "MODEL_NAME": {"field_name": "m"},\n'
        "    },\n"
        "}\n"
    )
    node.save_rules(base, append=False)
    assert os.path.exists(path)

    # Merge in an update to SAMPLERS and a new CAPTURE_FIELD_LIST entry
    update = (
        "KNOWN = {}\n\n"
        'SAMPLERS = {"A": {"positive": "p"}, "B": {}}\n\n'
        "CAPTURE_FIELD_LIST = {\n"
        '    "Node2": {\n'
        '        "NEGATIVE_PROMPT": {"field_name": "n"},\n'
        "    },\n"
        "}\n"
    )
    (st2,) = node.save_rules(update, append=True)
    assert st2.startswith("Merged updates into")

    with open(path, encoding="utf-8") as f:
        merged = f.read()
    assert '"B"' in merged  # appended sampler
    assert '"positive"' in merged  # updated sampler A
    assert '"Node2"' in merged  # new node appended
    # Version header should be present after merge
    assert 'GENERATED_RULES_VERSION = ' in merged


def test_rules_save_version_injection():
    """Test that version header is properly injected into generated rules."""
    mod = _rules_save_node()
    node = mod.SaveGeneratedUserRules()
    path = _rules_path(mod)
    _cleanup(path)

    # Simple rules without version
    content = "KNOWN = {}\n\nCAPTURE_FIELD_LIST = {}\n"
    (status,) = node.save_rules(content, append=False)
    assert status.startswith("Overwritten") or status.startswith("Created")

    with open(path, encoding="utf-8") as f:
        result = f.read()

    # Check version header components are present
    assert '"""Auto-generated metadata capture rules."""' in result
    assert '# Generated with metadata generator version:' in result
    assert 'GENERATED_RULES_VERSION = "' in result
    # Original content should still be present
    assert 'KNOWN = {}' in result
    assert 'CAPTURE_FIELD_LIST = {}' in result

    _cleanup(path)
