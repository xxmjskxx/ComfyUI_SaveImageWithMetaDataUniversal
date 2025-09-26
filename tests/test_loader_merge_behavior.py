import json
import os

import pytest

from saveimage_unimeta.defs import (
    CAPTURE_FIELD_LIST,
    SAMPLERS,
    load_extensions_only,
    load_user_definitions,
)


def _node_pack_py_dir() -> str:
    # saveimage_unimeta/defs/__init__.py is two levels deeper than package root
    here = os.path.dirname(__file__)
    # tests/ -> package root is parent of 'tests'
    pack_root = os.path.abspath(os.path.join(here, os.pardir))
    return os.path.join(pack_root, "py")


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

    def test_skip_user_json_when_coverage_satisfied(self):
        base = _node_pack_py_dir()
        user_caps = os.path.join(base, "user_captures.json")
        # Create user JSON with a class that does NOT exist in defaults/ext
        user_only_class = "UserOnly.Node"
        _write_json(user_caps, {user_only_class: {"field": {"key": "Value"}}})

        # Build a required set fully covered by current defaults/ext
        load_extensions_only()
        cover = set(CAPTURE_FIELD_LIST.keys()) | set(SAMPLERS.keys())
        assert cover, "Expected defaults/ext to provide some coverage"
        covered_subset = set(list(cover)[: min(3, len(cover))])

        # Because all required classes are covered, user JSON should be skipped
        load_user_definitions(required_classes=covered_subset, suppress_missing_log=True)
        assert user_only_class not in CAPTURE_FIELD_LIST
        assert user_only_class not in SAMPLERS

    def test_merge_user_json_when_missing_classes(self):
        base = _node_pack_py_dir()
        user_caps = os.path.join(base, "user_captures.json")
        user_samplers = os.path.join(base, "user_samplers.json")

        # Pick an existing class from defaults/ext to test deep-merge behavior
        load_extensions_only()
        assert CAPTURE_FIELD_LIST, "Expected baseline captures to be non-empty"
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
