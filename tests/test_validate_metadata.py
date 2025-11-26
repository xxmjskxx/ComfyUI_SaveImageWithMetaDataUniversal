"""Test validate_metadata.py script functionality."""

import sys
from pathlib import Path
from typing import Any

try:
    from tests.tools.validate_metadata import MetadataValidator, WorkflowAnalyzer
except ModuleNotFoundError:  # pragma: no cover - fallback for direct invocation
    # Add tests/tools directory to path to import validate_metadata when running the test directly
    sys.path.insert(0, str(Path(__file__).parent / "tools"))
    from validate_metadata import MetadataValidator, WorkflowAnalyzer  # type: ignore


class TestMetadataParser:
    """Test the metadata parameter string parser."""

    def test_parse_comma_separated_format(self):
        """Test parsing comma-separated metadata format."""
        validator = MetadataValidator(Path("."), Path("."))

        # Single-line format with commas
        params_str = (
            "masterpiece, best quality\n"
            "Negative prompt: low quality, worst\n"
            "Steps: 2, Sampler: DPM++ 2M Karras, CFG scale: 3.5, Denoise: 1.0, "
            "Seed: 517196117394134, Size: 832x1216"
        )

        fields = validator.parse_parameters_string(params_str)

        assert "Steps" in fields
        assert fields["Steps"] == "2"
        assert "Sampler" in fields
        assert fields["Sampler"] == "DPM++ 2M Karras"
        assert "CFG scale" in fields
        assert fields["CFG scale"] == "3.5"
        assert "Seed" in fields
        assert fields["Seed"] == "517196117394134"

    def test_parse_newline_separated_format(self):
        """Test parsing newline-separated metadata format."""
        validator = MetadataValidator(Path("."), Path("."))

        # Multi-line format with newlines
        params_str = """masterpiece, best quality
Negative prompt: low quality, worst
Steps: 2
Sampler: DPM++ 2M Karras
CFG scale: 3.5
Denoise: 1.0
Seed: 517196117394134
Size: 832x1216"""

        fields = validator.parse_parameters_string(params_str)

        assert "Steps" in fields
        assert fields["Steps"] == "2"
        assert "Sampler" in fields
        assert fields["Sampler"] == "DPM++ 2M Karras"
        assert "CFG scale" in fields
        assert fields["CFG scale"] == "3.5"
        assert "Seed" in fields
        assert fields["Seed"] == "517196117394134"

    def test_parse_with_lora_fields(self):
        """Test parsing metadata with LoRA fields."""
        validator = MetadataValidator(Path("."), Path("."))

        params_str = (
            "test prompt\n"
            "Negative prompt: bad\n"
            "Steps: 20, Sampler: euler, CFG scale: 7, Seed: 123, "
            "Lora_0 Model name: test.safetensors, Lora_0 Model hash: abc123, "
            "Lora_0 Strength model: 1.0, Lora_0 Strength clip: 1.0"
        )

        fields = validator.parse_parameters_string(params_str)

        assert "Steps" in fields
        assert "Sampler" in fields
        assert "CFG scale" in fields
        assert "Seed" in fields
        assert "Lora_0 Model name" in fields
        assert fields["Lora_0 Model name"] == "test.safetensors"

    def test_parse_with_hashes_json(self):
        """Test parsing metadata with Hashes JSON field."""
        validator = MetadataValidator(Path("."), Path("."))

        params_str = (
            "test prompt\n"
            "Negative prompt: bad\n"
            "Steps: 20, Sampler: euler, CFG scale: 7, Seed: 123, "
            'Hashes: {"model": "abc123", "vae": "def456"}'
        )

        fields = validator.parse_parameters_string(params_str)

        assert "Steps" in fields
        assert "Hashes" in fields
        assert '{"model": "abc123", "vae": "def456"}' in fields["Hashes"]

    def test_parse_dual_clip_prompts_comma_format(self):
        """Test parsing with dual-encoder prompts (T5 + CLIP) in comma-separated format."""
        validator = MetadataValidator(Path("."), Path("."))

        # In normal (non-test) mode, the format is comma-separated after the prompts
        params_str = """T5 Prompt: detailed prompt for T5
CLIP Prompt: shorter prompt for CLIP
Negative prompt: bad quality
Steps: 4, Sampler: euler, CFG scale: 1.0, Seed: 42, Size: 1024x1024"""

        fields = validator.parse_parameters_string(params_str)

        assert "Steps" in fields
        assert "Sampler" in fields
        assert "CFG scale" in fields
        assert "Seed" in fields

    def test_parse_dual_clip_prompts_multiline_format(self):
        """Test parsing with dual-encoder prompts (T5 + CLIP) in multiline format."""
        validator = MetadataValidator(Path("."), Path("."))

        # In test mode (METADATA_TEST_MODE=1), the format is newline-separated
        params_str = """T5 Prompt: detailed prompt for T5
CLIP Prompt: shorter prompt for CLIP
Negative prompt: bad quality
Steps: 4
Sampler: euler
CFG scale: 1.0
Seed: 42
Size: 1024x1024"""

        fields = validator.parse_parameters_string(params_str)

        assert "Steps" in fields
        assert "Sampler" in fields
        assert "CFG scale" in fields
        assert "Seed" in fields


class TestFilenamePatternExtraction:
    """Test filename pattern extraction from workflows."""

    def test_extract_simple_pattern(self):
        """Test extracting a simple filename pattern."""
        workflow = {
            "1": {"class_type": "SaveImageWithMetaDataUniversal", "inputs": {"filename_prefix": "Test\\flux-turbo"}}
        }

        patterns = WorkflowAnalyzer.extract_filename_patterns(workflow)
        assert "flux-turbo" in patterns
        assert "Test" not in patterns  # Test should be filtered out

    def test_extract_pattern_with_tokens(self):
        """Test extracting patterns with date/seed tokens."""
        workflow = {
            "1": {
                "class_type": "SaveImageWithMetaDataUniversal",
                "inputs": {"filename_prefix": "Test\\siwm-%model:10%/%pprompt:20%-%nprompt:20%/%seed%"},
            }
        }

        patterns = WorkflowAnalyzer.extract_filename_patterns(workflow)
        assert "siwm" in patterns

    def test_extract_multiple_patterns(self):
        """Test extracting patterns from multiple save nodes."""
        workflow = {
            "1": {"class_type": "SaveImageWithMetaDataUniversal", "inputs": {"filename_prefix": "Test\\workflow-one"}},
            "2": {"class_type": "SaveImage", "inputs": {"filename_prefix": "Test\\workflow-two-control"}},
        }

        patterns = WorkflowAnalyzer.extract_filename_patterns(workflow)
        assert "workflow-one" in patterns
        assert "workflow-two-control" in patterns


class TestImageMatching:
    """Test image to workflow matching logic."""

    def test_match_simple_name(self):
        """Test matching simple image names."""
        validator = MetadataValidator(Path("."), Path("."))

        image_path = Path("flux-turbo_00001_.png")
        patterns = ["flux-turbo"]

        assert validator.match_image_to_workflow(image_path, patterns)

    def test_match_with_delimiters(self):
        """Test matching with delimiters."""
        validator = MetadataValidator(Path("."), Path("."))

        image_path = Path("test_flux-turbo_00001_.png")
        patterns = ["flux-turbo"]

        assert validator.match_image_to_workflow(image_path, patterns)

    def test_no_match_substring(self):
        """Test that substrings don't match incorrectly."""
        validator = MetadataValidator(Path("."), Path("."))

        # "eff" should not match "jeff_image.png"
        image_path = Path("jeff_image.png")
        patterns = ["eff"]

        assert not validator.match_image_to_workflow(image_path, patterns)


class TestSamplerValidation:
    """Test sampler and scheduler validation rules."""

    def _run_validation(self, fields: dict[str, str], expected: dict[str, Any]) -> dict:
        validator = MetadataValidator(Path("."), Path("."))
        result = {"errors": [], "warnings": [], "check_details": []}
        validator._validate_expected_fields(fields, expected, result)
        return result

    def test_non_civitai_sampler_requires_scheduler_suffix(self):
        expected = {"sampler_name": "euler", "scheduler": "karras", "civitai_sampler": False}
        fields = {"Sampler": "euler_karras"}
        result = self._run_validation(fields, expected)
        assert not result["errors"]
        assert any(detail["field"] == "Sampler" and detail["status"] == "pass" for detail in result["check_details"])

    def test_non_civitai_sampler_missing_scheduler_fails(self):
        expected = {"sampler_name": "euler", "scheduler": "karras", "civitai_sampler": False}
        fields = {"Sampler": "euler"}
        result = self._run_validation(fields, expected)
        assert result["errors"]
        assert any("Sampler mismatch" in err for err in result["errors"])

    def test_civitai_sampler_mapping_passes(self):
        expected = {"sampler_name": "dpmpp_2m_sde", "scheduler": "karras", "civitai_sampler": True}
        fields = {"Sampler": "DPM++ 2M SDE Karras"}
        result = self._run_validation(fields, expected)
        assert not result["errors"]
        assert any(detail["field"] == "Sampler" and detail["status"] == "pass" for detail in result["check_details"])

    def test_civitai_sampler_mismatch_fails(self):
        expected = {"sampler_name": "dpmpp_2m_sde", "scheduler": "karras", "civitai_sampler": True}
        fields = {"Sampler": "Euler"}
        result = self._run_validation(fields, expected)
        assert result["errors"]
        assert any("Civitai" in err for err in result["errors"])


class TestSamplerSelectionWorkflow:
    """Ensure sampler selection mirrors runtime sampler_selection_method semantics."""

    def _build_multi_sampler_workflow(self, selection_method: str = "Farthest", selection_node_id: int = 0) -> dict[str, Any]:
        workflow: dict[str, Any] = {
            "10": {
                "class_type": "SaveImageWithMetaDataUniversal",
                "inputs": {
                    "images": ["9", 0],
                    "filename_prefix": "Test\\multi-sampler",
                    "sampler_selection_method": selection_method,
                    "sampler_selection_node_id": selection_node_id,
                },
            },
            "9": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["8", 0],
                    "vae": ["4", 0],
                },
            },
            "8": {
                "class_type": "KSampler",
                "inputs": {
                    "steps": 10,
                    "cfg": 7,
                    "sampler_name": "sampler_near",
                    "scheduler": "normal",
                    "model": ["5", 0],
                    "latent_image": ["7", 0],
                    "positive": "good prompt",
                    "negative": "bad prompt",
                },
            },
            "7": {
                "class_type": "KSampler",
                "inputs": {
                    "steps": 30,
                    "cfg": 7,
                    "sampler_name": "sampler_far",
                    "scheduler": "karras",
                    "model": ["5", 0],
                    "latent_image": ["6", 0],
                    "positive": "good prompt",
                    "negative": "bad prompt",
                },
            },
            "6": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1,
                },
            },
            "5": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "model.safetensors",
                },
            },
            "4": {
                "class_type": "VAELoader",
                "inputs": {
                    "vae_name": "vae.safetensors",
                },
            },
        }
        return workflow

    def _extract_save_node(self, workflow: dict[str, Any]) -> dict[str, Any]:
        expected = WorkflowAnalyzer.extract_expected_metadata(workflow, "multi-sampler")
        assert expected["save_nodes"], "Expected at least one save node"
        return expected["save_nodes"][0]

    def test_farthest_sampler_selected(self):
        workflow = self._build_multi_sampler_workflow(selection_method="Farthest")
        save_node_expected = self._extract_save_node(workflow)
        assert save_node_expected["sampler_node_id"] == "7"

    def test_nearest_sampler_selected(self):
        workflow = self._build_multi_sampler_workflow(selection_method="Nearest")
        save_node_expected = self._extract_save_node(workflow)
        assert save_node_expected["sampler_node_id"] == "8"

    def test_by_node_id_sampler_selected(self):
        workflow = self._build_multi_sampler_workflow(selection_method="By node ID", selection_node_id=8)
        save_node_expected = self._extract_save_node(workflow)
        assert save_node_expected["sampler_node_id"] == "8"

    def test_match_case_insensitive(self):
        """Test case-insensitive matching."""
        validator = MetadataValidator(Path("."), Path("."))

        image_path = Path("FLUX-TURBO_00001_.png")
        patterns = ["flux-turbo"]

        assert validator.match_image_to_workflow(image_path, patterns)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
