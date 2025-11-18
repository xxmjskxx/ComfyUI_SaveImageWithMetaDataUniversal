import importlib
import pytest


def _load_helper():
    try:
        return importlib.import_module("ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.nodes.rules_writer")
    except ImportError as e:  # pragma: no cover - environment specific
        pytest.skip(f"rules_writer module not importable in this environment: {e}")


@pytest.mark.parametrize(
    "value,expected",
    [
        ("20250101-123045", True),  # exact base
        ("20250101-123045-1", True),  # numeric suffix
        ("20250101-123045-12", True),  # multi-digit suffix
        ("20250101-12304", False),  # too short
        ("20250101-123045-", False),  # dash but no digits
        ("20250101-123045X", False),  # stray char instead of '-'
        ("20250101-123045-a", False),  # non-digit suffix
        ("notatimestamp", False),  # random text
    ],
)
def test_looks_like_timestamp(value, expected):
    mod = _load_helper()
    helper = getattr(mod, "_looks_like_timestamp", None)
    assert helper is not None, "_looks_like_timestamp not found"
    assert helper(value) is expected
