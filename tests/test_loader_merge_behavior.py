import json
import os

import pytest

from saveimage_unimeta.defs import (
    CAPTURE_FIELD_LIST,
    SAMPLERS,
    load_extensions_only,
    load_user_definitions,
)
from saveimage_unimeta.defs.meta import MetaField


def _node_pack_py_dir() -> str:
    # Place test user rule artifacts under tests/_test_outputs/user_rules to avoid polluting real tree.
    here = os.path.dirname(__file__)
    pack_root = os.path.abspath(os.path.join(here, os.pardir))
    return os.path.join(pack_root, "tests/_test_outputs", "user_rules")


def _write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _cleanup(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


@pytest.mark.usefixtures("reset_env_flags")
class TestLoaderMergeBehavior:
    def setup_method(self):
        # Ensure we start from defaults for each test
        load_extensions_only()
        # Clean any stray user files that earlier tests may have created
        base = _node_pack_py_dir()
        _cleanup(os.path.join(base, "user_captures.json"))
        _cleanup(os.path.join(base, "user_samplers.json"))

    def teardown_method(self):
        base = _node_pack_py_dir()
        _cleanup(os.path.join(base, "user_captures.json"))
        _cleanup(os.path.join(base, "user_samplers.json"))
        load_extensions_only()

    def test_efficiency_lora_stacker_prefers_selectors(self):
        load_extensions_only()
        entry = CAPTURE_FIELD_LIST.get("LoRA Stacker")
        if not entry:
            pytest.skip("LoRA Stacker rules missing; efficiency extension not loaded")

        meta_fields = (
            MetaField.LORA_MODEL_NAME,
            MetaField.LORA_MODEL_HASH,
            MetaField.LORA_STRENGTH_MODEL,
            MetaField.LORA_STRENGTH_CLIP,
        )
        for meta in meta_fields:
            config = entry.get(meta)
            assert isinstance(config, dict), f"Expected dict config for {meta}"
            assert "selector" in config, f"Selector missing for {meta}"
            assert "fields" not in config, f"Generated fields should not override selector for {meta}"

    def test_skip_user_json_when_coverage_satisfied(self, metadata_test_mode):
        base = _node_pack_py_dir()
        user_caps = os.path.join(base, "user_captures.json")
        # Create user JSON with a class that does NOT exist in defaults/ext
        user_only_class = "UserOnly.Node"
        _write_json(user_caps, {user_only_class: {"field": {"key": "Value"}}})

        # Build a required set fully covered by current defaults/ext
        load_extensions_only()
        cover = set(CAPTURE_FIELD_LIST.keys()) | set(SAMPLERS.keys())
        if not cover:
            # In CI with METADATA_TEST_MODE enabled defaults may intentionally be empty; skip.
            if metadata_test_mode:
                import pytest as _pytest

                _pytest.skip("Baseline empty under test mode; skip coverage satisfied scenario.")
            raise AssertionError("Expected defaults/ext to provide some coverage")
        covered_subset = set(list(cover)[: min(3, len(cover))])

        # Because all required classes are covered, user JSON should be skipped
        load_user_definitions(required_classes=covered_subset, suppress_missing_log=True)
        assert user_only_class not in CAPTURE_FIELD_LIST
        assert user_only_class not in SAMPLERS

    def test_user_override_applies_even_if_coverage_complete(self, metadata_test_mode):
        base = _node_pack_py_dir()
        user_caps = os.path.join(base, "user_captures.json")

        load_extensions_only()
        if not CAPTURE_FIELD_LIST:
            if metadata_test_mode:
                pytest.skip("No baseline captures under test mode; skipping override test.")
            raise AssertionError("Expected baseline captures for override scenario")

        existing_class = next(iter(CAPTURE_FIELD_LIST.keys()))
        override_key = "user_override_field"
        _write_json(user_caps, {existing_class: {override_key: {"field_name": "custom"}}})

        # Provide a coverage set that is fully satisfied by defaults to trigger the previous skip path
        load_user_definitions(required_classes={existing_class}, suppress_missing_log=True)

        assert existing_class in CAPTURE_FIELD_LIST
        assert override_key in CAPTURE_FIELD_LIST[existing_class]

    def test_merge_user_json_when_missing_classes(self, metadata_test_mode):
        base = _node_pack_py_dir()
        user_caps = os.path.join(base, "user_captures.json")
        user_samplers = os.path.join(base, "user_samplers.json")

        # Pick an existing class from defaults/ext to test deep-merge behavior
        load_extensions_only()
        if not CAPTURE_FIELD_LIST:
            if metadata_test_mode:
                import pytest as _pytest

                _pytest.skip("Baseline empty under test mode; skip merge test.")
            raise AssertionError("Expected baseline captures to be non-empty")
        existing_class = next(iter(CAPTURE_FIELD_LIST.keys()))

        # Seed: verify a known field map type (or fallback to empty mapping)
        before_fields = dict(CAPTURE_FIELD_LIST.get(existing_class, {}))

        # Prepare user JSON: 1) add a brand new class, 2) extend an existing class
        user_only_class = "UserOnly.Node"
        _write_json(
            user_caps,
            {
                user_only_class: {"extra": {"key": "X"}},
                existing_class: {"added": {"key": "Y"}},
            },
        )
        _write_json(user_samplers, {user_only_class: {"sampler": "Euler"}})

        # Force merge by requiring the user-only class
        load_user_definitions(required_classes={user_only_class}, suppress_missing_log=True)

        # 1) New class appears in both dicts as applicable
        assert user_only_class in CAPTURE_FIELD_LIST
        assert user_only_class in SAMPLERS

        # 2) Existing class is deep-merged, original keys preserved
        after_fields = CAPTURE_FIELD_LIST.get(existing_class, {})
        assert isinstance(after_fields, dict)
        for k, v in before_fields.items():
            assert after_fields.get(k) == v
        assert "added" in after_fields and isinstance(after_fields["added"], dict)

    def test_user_json_malformed_is_ignored(self, caplog):
        base = _node_pack_py_dir()
        bad_json = os.path.join(base, "user_samplers.json")
        os.makedirs(os.path.dirname(bad_json), exist_ok=True)
        with open(bad_json, "w", encoding="utf-8") as f:
            f.write("{ this is not valid json ")

        load_extensions_only()
        before = dict(SAMPLERS)

        # Trigger loader; it should not raise and SAMPLERS should remain unchanged
        with caplog.at_level("WARNING"):
            load_user_definitions(required_classes={"Definitely.Missing.Node"}, suppress_missing_log=True)
        assert dict(SAMPLERS) == before
        _cleanup(bad_json)

    def test_malformed_capture_rules_skipped_for_existing_class(self):
        base = _node_pack_py_dir()
        user_caps = os.path.join(base, "user_captures.json")

        load_extensions_only()
        if not CAPTURE_FIELD_LIST:
            pytest.skip("No baseline captures available to test against")
        existing_class = next(iter(CAPTURE_FIELD_LIST.keys()))
        before_fields = dict(CAPTURE_FIELD_LIST.get(existing_class, {}))

        # Provide a non-mapping for rules (invalid shape): should be skipped without crashing
        _write_json(user_caps, {existing_class: ["bad", "shape"]})

        load_user_definitions(required_classes={existing_class}, suppress_missing_log=True)

        after_fields = CAPTURE_FIELD_LIST.get(existing_class, {})
        assert isinstance(after_fields, dict)
        assert after_fields == before_fields, "Existing class fields must remain unchanged on invalid user shape"
        _cleanup(user_caps)

    def test_malformed_capture_rules_for_new_class_create_empty_entry(self):
        base = _node_pack_py_dir()
        user_caps = os.path.join(base, "user_captures.json")

        load_extensions_only()
        user_only_class = "BadShape.Node"
        # Non-mapping rules should not populate fields; loader creates empty dict for the class
        _write_json(user_caps, {user_only_class: "not-a-mapping"})

        load_user_definitions(required_classes={user_only_class}, suppress_missing_log=True)

        assert user_only_class in CAPTURE_FIELD_LIST
        assert CAPTURE_FIELD_LIST[user_only_class] == {}, "New class with invalid rules should remain empty"
        _cleanup(user_caps)

    def test_malformed_samplers_shape_is_skipped(self, caplog):
        base = _node_pack_py_dir()
        user_samplers = os.path.join(base, "user_samplers.json")

        load_extensions_only()
        before = dict(SAMPLERS)

        # Non-mapping value for a sampler entry should be ignored
        _write_json(user_samplers, {"Weird.Sampler.Node": "not-a-mapping"})

        with caplog.at_level("WARNING"):
            load_user_definitions(required_classes={"Weird.Sampler.Node"}, suppress_missing_log=True)

        after = dict(SAMPLERS)
        assert after == before, "Invalid sampler value should not modify SAMPLERS"
        _cleanup(user_samplers)

    def test_malformed_samplers_partial_merge_preserves_existing(self):
        base = _node_pack_py_dir()
        user_samplers = os.path.join(base, "user_samplers.json")

        load_extensions_only()
        # Pick an existing key to simulate a partial merge
        if not SAMPLERS:
            pytest.skip("No baseline samplers to test against")
        existing_key = next(iter(SAMPLERS.keys()))
        before_map = dict(SAMPLERS.get(existing_key, {}))

        # Mixed shapes: existing key gets mapping merged; invalid key is skipped
        _write_json(
            user_samplers,
            {
                existing_key: {"new": "val"},
                "Invalid.Key": [1, 2, 3],
            },
        )

        load_user_definitions(required_classes={existing_key, "Invalid.Key"}, suppress_missing_log=True)

        # Existing key merged
        after_map = SAMPLERS.get(existing_key, {})
        assert isinstance(after_map, dict)
        for k, v in before_map.items():
            assert after_map.get(k) == v
        assert after_map.get("new") == "val"

        # Invalid key was not added
        assert "Invalid.Key" not in SAMPLERS
        _cleanup(user_samplers)
