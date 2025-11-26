"""Tests for MetadataValidator._validate_reverse_coverage method.

This test module verifies the reverse validation feature that checks whether
each metadata field found in an image has a corresponding validation check
in the validation script.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# Add tools directory to path for import
TOOLS_DIR = Path(__file__).parent.parent / "tests" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


@pytest.fixture
def validator():
    """Create a MetadataValidator instance for testing."""
    from validate_metadata import MetadataValidator

    # Create validator with mock paths
    v = MetadataValidator(
        workflow_dir=Path("."),
        output_dir=Path("."),
        comfyui_models_path=None,
    )
    return v


class TestReverseValidationBasics:
    """Basic tests for reverse validation functionality."""

    def test_empty_fields_returns_empty_stats(self, validator):
        """Empty fields dict should return zero counts."""
        result = {"check_details": []}
        stats = validator._validate_reverse_coverage({}, result)

        assert stats["total_fields"] == 0
        assert stats["validated_fields"] == 0
        assert stats["unvalidated_fields"] == []
        assert stats["coverage_percentage"] == 0.0

    def test_field_with_direct_check(self, validator):
        """Field that has a direct check in check_details should be marked validated."""
        result = {
            "check_details": [
                {"field": "Seed", "status": "pass", "expected": "12345", "actual": "12345"},
            ]
        }
        fields = {"Seed": "12345"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["total_fields"] == 1
        assert stats["validated_fields"] == 1
        assert stats["unvalidated_fields"] == []
        assert stats["coverage_percentage"] == 100.0

    def test_field_without_check_is_unvalidated(self, validator):
        """Field without any check should be marked unvalidated."""
        result = {"check_details": []}
        fields = {"Custom Field": "some value"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["total_fields"] == 1
        assert stats["validated_fields"] == 0
        assert "Custom Field" in stats["unvalidated_fields"]
        assert stats["coverage_percentage"] == 0.0

    def test_multiple_fields_mixed_coverage(self, validator):
        """Multiple fields with some validated and some not."""
        result = {
            "check_details": [
                {"field": "Seed", "status": "pass"},
                {"field": "Steps", "status": "pass"},
            ]
        }
        fields = {
            "Seed": "12345",
            "Steps": "20",
            "Unknown Field": "value",
        }

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["total_fields"] == 3
        assert stats["validated_fields"] == 2
        assert "Unknown Field" in stats["unvalidated_fields"]
        assert 66.0 < stats["coverage_percentage"] < 67.0


class TestDirectFieldValidation:
    """Tests for direct field validation via check_details."""

    def test_field_with_check_is_validated(self, validator):
        """Field with actual check in check_details should be validated."""
        result = {
            "check_details": [
                {"field": "CFG scale", "status": "pass"},
            ]
        }
        fields = {"CFG scale": "7.5"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["validated_fields"] == 1
        assert stats["unvalidated_fields"] == []

    def test_field_without_check_is_not_validated(self, validator):
        """Field without check in check_details should NOT be validated."""
        result = {"check_details": []}
        fields = {"CFG scale": "7.5"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["validated_fields"] == 0
        assert "CFG scale" in stats["unvalidated_fields"]

    def test_metadata_generator_version_always_validated(self, validator):
        """Metadata generator version is always considered validated."""
        result = {"check_details": []}
        fields = {"Metadata generator version": "1.0.0"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["validated_fields"] == 1
        assert stats["unvalidated_fields"] == []

    def test_hashes_field_validated_via_hashes_checks(self, validator):
        """Hashes field validated when Hashes-related checks exist."""
        result = {
            "check_details": [
                {"field": "Hashes model entry", "status": "pass"},
            ]
        }
        fields = {"Hashes": '{"model": "abc123"}'}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["validated_fields"] == 1
        assert "Hashes" not in stats["unvalidated_fields"]


class TestDynamicPatterns:
    """Tests for dynamic pattern matching (LoRA, Embedding, CLIP)."""

    def test_lora_fields_need_individual_checks(self, validator):
        """Each LoRA field needs its own check in check_details."""
        result = {
            "check_details": [
                {"field": "Lora_0 Model name", "status": "pass"},
            ]
        }
        fields = {
            "Lora_0 Model name": "my_lora.safetensors",
            "Lora_0 Model hash": "abc123",
        }

        stats = validator._validate_reverse_coverage(fields, result)

        # Only the field with a direct check is validated
        assert stats["validated_fields"] == 1
        assert "Lora_0 Model hash" in stats["unvalidated_fields"]

    def test_lora_fields_all_checked(self, validator):
        """All LoRA fields validated when each has a check."""
        result = {
            "check_details": [
                {"field": "Lora_0 Model name", "status": "pass"},
                {"field": "Lora_0 Model hash", "status": "pass"},
            ]
        }
        fields = {
            "Lora_0 Model name": "my_lora.safetensors",
            "Lora_0 Model hash": "abc123",
        }

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["validated_fields"] == 2
        assert stats["unvalidated_fields"] == []

    def test_embedding_fields_need_individual_checks(self, validator):
        """Each Embedding field needs its own check in check_details."""
        result = {
            "check_details": [
                {"field": "Embedding_0 name", "status": "pass"},
            ]
        }
        fields = {
            "Embedding_0 name": "my_embedding",
            "Embedding_0 hash": "def456",
        }

        stats = validator._validate_reverse_coverage(fields, result)

        # Only the field with a direct check is validated
        assert stats["validated_fields"] == 1
        assert "Embedding_0 hash" in stats["unvalidated_fields"]

    def test_clip_field_with_check(self, validator):
        """CLIP fields should be validated when check exists."""
        result = {
            "check_details": [
                {"field": "CLIP_1 Model name", "status": "pass"},
            ]
        }
        fields = {"CLIP_1 Model name": "clip_model.safetensors"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["validated_fields"] == 1


class TestInformationalFields:
    """Tests for informational fields that don't need validation."""

    def test_metadata_fallback_is_informational(self, validator):
        """Metadata Fallback field should be considered informational."""
        result = {"check_details": []}
        fields = {"Metadata Fallback": "stage1"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["validated_fields"] == 1
        assert "Metadata Fallback" not in stats["unvalidated_fields"]

    def test_loras_summary_is_informational(self, validator):
        """LoRAs summary field should be considered informational."""
        result = {"check_details": []}
        fields = {"LoRAs": "lora1, lora2"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["validated_fields"] == 1
        assert "LoRAs" not in stats["unvalidated_fields"]


class TestExtraMetadataFields:
    """Tests for extra metadata fields recorded as 'Extra: {field}'."""

    def test_extra_metadata_field_recognized(self, validator):
        """Extra metadata fields recorded as 'Extra: {field}' should be recognized."""
        result = {
            "check_details": [
                {"field": "Extra: custom_key", "status": "pass"},
                {"field": "Extra: hello", "status": "pass"},
                {"field": "Extra: custom_w", "status": "fail"},
                {"field": "Extra: custom_h", "status": "fail"},
            ]
        }
        fields = {
            "custom_key": "custom_value",
            "hello": "world",
            "custom_w": "832",
            "custom_h": "1216",
        }

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["total_fields"] == 4
        assert stats["validated_fields"] == 4
        assert stats["unvalidated_fields"] == []

    def test_extra_metadata_mixed_with_regular_fields(self, validator):
        """Mix of extra metadata and regular fields should both be validated."""
        result = {
            "check_details": [
                {"field": "Seed", "status": "pass"},
                {"field": "Extra: custom_key", "status": "pass"},
            ]
        }
        fields = {
            "Seed": "12345",
            "custom_key": "custom_value",
        }

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["total_fields"] == 2
        assert stats["validated_fields"] == 2


class TestHashFieldValidation:
    """Tests for hash field validation."""

    def test_hash_field_needs_direct_check(self, validator):
        """Hash fields need direct checks in check_details."""
        result = {
            "check_details": [
                {"field": "Hashes model match", "status": "pass"},
            ]
        }
        fields = {"Model hash": "abc123def"}

        stats = validator._validate_reverse_coverage(fields, result)

        # "Model hash" is not the same as "Hashes model match", so not validated
        assert stats["validated_fields"] == 0
        assert "Model hash" in stats["unvalidated_fields"]

    def test_hash_field_validated_with_direct_check(self, validator):
        """Hash fields validated when they have direct checks."""
        result = {
            "check_details": [
                {"field": "Model hash", "status": "pass"},
            ]
        }
        fields = {"Model hash": "abc123def"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["validated_fields"] == 1
        assert "Model hash" not in stats["unvalidated_fields"]


class TestRequiredFieldChecks:
    """Tests for required field self-validation."""

    def test_missing_required_field_check_seed(self, validator):
        """Missing check for required 'Seed' field should be reported."""
        result = {"check_details": []}
        fields = {"Seed": "12345"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert "Seed" in stats["missing_required_checks"]

    def test_missing_required_field_check_steps(self, validator):
        """Missing check for required 'Steps' field should be reported."""
        result = {"check_details": []}
        fields = {"Steps": "20"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert "Steps" in stats["missing_required_checks"]

    def test_missing_cfg_or_guidance_check(self, validator):
        """Missing check for CFG/Guidance should be reported when field is present."""
        result = {"check_details": []}
        fields = {"CFG scale": "7.5"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert "CFG scale/Guidance" in stats["missing_required_checks"]

    def test_required_field_with_check_not_missing(self, validator):
        """Required field with a check should not be in missing_required_checks."""
        result = {
            "check_details": [
                {"field": "Seed", "status": "pass"},
            ]
        }
        fields = {"Seed": "12345"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert "Seed" not in stats["missing_required_checks"]


class TestFieldDetails:
    """Tests for field_details output."""

    def test_field_details_contains_all_fields(self, validator):
        """field_details should contain an entry for each field."""
        result = {"check_details": [{"field": "Seed", "status": "pass"}]}
        fields = {"Seed": "12345", "Steps": "20"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert len(stats["field_details"]) == 2
        field_names = {d["field"] for d in stats["field_details"]}
        assert "Seed" in field_names
        assert "Steps" in field_names

    def test_field_details_has_check_info(self, validator):
        """field_details should indicate whether field has a check."""
        result = {"check_details": [{"field": "Seed", "status": "pass"}]}
        fields = {"Seed": "12345"}

        stats = validator._validate_reverse_coverage(fields, result)

        detail = stats["field_details"][0]
        assert detail["field"] == "Seed"
        assert detail["has_check"] is True
        assert detail["check_source"] == "direct"

    def test_field_details_value_preview_truncated(self, validator):
        """Long field values should be truncated in preview."""
        result = {"check_details": []}
        long_value = "a" * 100
        fields = {"Long Field": long_value}

        stats = validator._validate_reverse_coverage(fields, result)

        detail = stats["field_details"][0]
        assert len(detail["value_preview"]) == 53  # 50 chars + "..."
        assert detail["value_preview"].endswith("...")


class TestVerboseOutput:
    """Tests for verbose output functionality."""

    def test_verbose_false_no_print(self, validator, capsys):
        """With verbose=False, no output should be printed."""
        result = {"check_details": []}
        fields = {"Seed": "12345"}

        validator._validate_reverse_coverage(fields, result, verbose=False)

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_verbose_true_prints_fields(self, validator, capsys):
        """With verbose=True, field info should be printed."""
        result = {"check_details": [{"field": "Seed", "status": "pass"}]}
        fields = {"Seed": "12345"}

        validator._validate_reverse_coverage(fields, result, verbose=True)

        captured = capsys.readouterr()
        assert "Seed" in captured.out
        assert "✓" in captured.out

    def test_verbose_shows_unvalidated_with_x(self, validator, capsys):
        """Verbose output should show ✗ for unvalidated fields."""
        result = {"check_details": []}
        fields = {"Unknown": "value"}

        validator._validate_reverse_coverage(fields, result, verbose=True)

        captured = capsys.readouterr()
        assert "Unknown" in captured.out
        assert "✗" in captured.out


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_string_field_value_skipped(self, validator):
        """Empty string field values should be skipped."""
        result = {"check_details": []}
        fields = {"Empty": "", "NonEmpty": "value"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["total_fields"] == 1

    def test_none_field_value_skipped(self, validator):
        """None field values should be skipped."""
        result = {"check_details": []}
        fields = {"None Field": None, "Real Field": "value"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["total_fields"] == 1

    def test_whitespace_only_field_value_skipped(self, validator):
        """Whitespace-only field values should be skipped."""
        result = {"check_details": []}
        fields = {"Whitespace": "   ", "Real": "value"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["total_fields"] == 1

    def test_check_detail_without_field_key(self, validator):
        """Check details without 'field' key should be handled gracefully."""
        result = {
            "check_details": [
                {"status": "pass"},  # Missing 'field' key
                {"field": "Seed", "status": "pass"},
            ]
        }
        fields = {"Seed": "12345"}

        stats = validator._validate_reverse_coverage(fields, result)

        assert stats["validated_fields"] == 1

    def test_check_detail_with_info_status_ignored_for_required(self, validator):
        """Check details with 'info' status shouldn't count for required field checks."""
        result = {
            "check_details": [
                {"field": "Seed", "status": "info"},  # Info, not pass/fail/warn
            ]
        }
        fields = {"Seed": "12345"}

        stats = validator._validate_reverse_coverage(fields, result)

        # Direct match still counts for validation
        assert stats["validated_fields"] == 1
        # But info status doesn't satisfy required check
        assert "Seed" in stats["missing_required_checks"]
