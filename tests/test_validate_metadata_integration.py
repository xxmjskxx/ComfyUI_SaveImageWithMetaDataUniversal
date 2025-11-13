"""Integration tests for validate_metadata.py with sample image metadata."""

import json
import sys
from pathlib import Path

import pytest

# Add comfyui_cli_tests directory to path to import validate_metadata
sys.path.insert(0, str(Path(__file__).parent / "comfyui_cli_tests"))

from validate_metadata import MetadataValidator, WorkflowAnalyzer


class TestValidateMetadataIntegration:
    """Integration tests using real workflow configurations."""

    def test_special_workflow_skip(self):
        """Test that 1-scan-and-save-custom-metadata-rules.json is skipped."""
        validator = MetadataValidator(Path("."), Path("."))
        workflow_file = Path("tests/comfyui_cli_tests/dev_test_workflows/1-scan-and-save-custom-metadata-rules.json")

        # This should return empty list and print info message
        results = validator.validate_workflow_outputs(workflow_file, [])
        assert results == []

    def test_filename_format_denoise_workflow_pattern(self):
        """Test that filename_format_denoise.json workflow pattern extraction works."""
        workflow_file = Path("tests/comfyui_cli_tests/dev_test_workflows/filename_format_denoise.json")

        if not workflow_file.exists():
            pytest.skip(f"Workflow file not found: {workflow_file}")

        with open(workflow_file, encoding="utf-8") as f:
            workflow = json.load(f)

        patterns = WorkflowAnalyzer.extract_filename_patterns(workflow)

        # Should extract "siwm" from "Test\\siwm-%model:10%/%pprompt:20%-%nprompt:20%/%seed%"
        assert "siwm" in patterns, f"Expected 'siwm' in patterns, got: {patterns}"

    def test_large_workflow_jpeg_1kb_variant(self):
        """Test that 2kb and 1kb variants exist for testing other fallback stages."""
        workflow_file = Path("tests/comfyui_cli_tests/dev_test_workflows/large-workflow-jpeg-1kb.json")
        assert workflow_file.exists(), "large-workflow-jpeg-1kb.json should exist"

        with open(workflow_file, encoding="utf-8") as f:
            workflow = json.load(f)

        # Verify the max_jpeg_exif_kb setting
        for node_id, node_data in workflow.items():
            if node_data.get("class_type") == "SaveImageWithMetaDataUniversal":
                inputs = node_data.get("inputs", {})
                assert inputs.get("max_jpeg_exif_kb") == 1
                break

    def test_extra_metadata_clip_skip_workflow(self):
        """Test extra_metadata_clip_skip.json workflow analysis."""
        workflow_file = Path("tests/comfyui_cli_tests/dev_test_workflows/extra_metadata_clip_skip.json")

        if not workflow_file.exists():
            pytest.skip(f"Workflow file not found: {workflow_file}")

        with open(workflow_file, encoding="utf-8") as f:
            workflow = json.load(f)

        expected = WorkflowAnalyzer.extract_expected_metadata(workflow, workflow_file.stem)

        # Should have save node
        assert expected["has_save_node"]

        # Should have save nodes with metadata
        assert len(expected["save_nodes"]) > 0

        # First save node should have steps, cfg, seed
        save_node = expected["save_nodes"][0]
        assert save_node.get("steps") is not None
        assert save_node.get("cfg") is not None

    def test_flux_workflows(self):
        """Test various flux workflows."""
        flux_workflows = [
            "flux-CR-LoRA-stack-ClownsharK.json",
            "flux-PC-LoRA-inline-Inspire-KSampler.json",
        ]

        for workflow_name in flux_workflows:
            workflow_file = Path(f"tests/comfyui_cli_tests/dev_test_workflows/{workflow_name}")

            if not workflow_file.exists():
                pytest.skip(f"Workflow file not found: {workflow_file}")

            with open(workflow_file, encoding="utf-8") as f:
                workflow = json.load(f)

            expected = WorkflowAnalyzer.extract_expected_metadata(workflow, workflow_file.stem)

            # Should have save node
            assert expected["has_save_node"]

            # Should have save nodes with metadata
            assert len(expected["save_nodes"]) > 0


class TestMetadataParserWithRealFormats:
    """Test the parser with real-world metadata formats."""

    def test_parse_flux_metadata_without_cfg(self):
        """Test parsing Flux metadata that uses Guidance instead of CFG scale."""
        validator = MetadataValidator(Path("."), Path("."))

        # Flux models often have Guidance instead of CFG scale
        params_str = (
            "masterpiece, best quality\n"
            "Negative prompt: low quality\n"
            "Steps: 4, Sampler: euler, Guidance: 3.5, Seed: 42, Size: 1024x1024"
        )

        fields = validator.parse_parameters_string(params_str)

        assert "Steps" in fields
        assert "Sampler" in fields
        assert "Guidance" in fields  # Flux uses Guidance
        assert "Seed" in fields

    def test_parse_with_metadata_fallback_marker(self):
        """Test parsing metadata with fallback marker."""
        validator = MetadataValidator(Path("."), Path("."))

        params_str = (
            "test prompt\n"
            "Negative prompt: bad\n"
            "Steps: 2, Sampler: DPM++ 2M Karras, CFG scale: 3.5, Seed: 123, "
            "Metadata Fallback: reduced-exif"
        )

        fields = validator.parse_parameters_string(params_str)

        assert "Steps" in fields
        assert "Metadata Fallback" in fields
        assert fields["Metadata Fallback"] == "reduced-exif"

    def test_parse_chinese_characters(self):
        """Test parsing metadata with Chinese characters (wan21 workflow issue)."""
        validator = MetadataValidator(Path("."), Path("."))

        # wan21 workflow may contain Chinese characters
        params_str = "测试提示词\n" "Negative prompt: 低质量\n" "Steps: 20, Sampler: euler, CFG scale: 7, Seed: 123"

        fields = validator.parse_parameters_string(params_str)

        # Should still parse the metadata fields correctly
        assert "Steps" in fields
        assert fields["Steps"] == "20"
        assert "Sampler" in fields
        assert "CFG scale" in fields
        assert "Seed" in fields


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
