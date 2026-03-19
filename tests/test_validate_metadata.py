"""Test validate_metadata.py script functionality."""

import sys
from pathlib import Path
from typing import Any

try:
    from tests.tools import validate_metadata as validate_metadata_module
    from tests.tools.validate_metadata import MetadataValidator, WorkflowAnalyzer
except ModuleNotFoundError:  # pragma: no cover - fallback for direct invocation
    # Add tests/tools directory to path to import validate_metadata when running the test directly
    sys.path.insert(0, str(Path(__file__).parent / "tools"))
    import validate_metadata as validate_metadata_module  # type: ignore

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

    def test_no_match_from_subdir_only(self, tmp_path):
        """Images should not match solely because they live in a nested output folder."""
        validator = MetadataValidator(tmp_path, tmp_path)

        image_path = tmp_path / "2026-03-19" / "1234567890123.png"
        expected = {
            "filename_prefix": "Test\\%date:yyyy-MM-dd%//%seed%",
            "filename_patterns": [],
            "filename_leaf_markers": [],
        }

        assert not validator.match_image_to_workflow(image_path, [], expected)


class TestWorkflowAssignment:
    """Test strict one-image-to-one-workflow assignment."""

    def test_assign_images_prefers_strongest_unique_match(self, tmp_path):
        validator = MetadataValidator(tmp_path, tmp_path)
        image_path = tmp_path / "eff_xl_hash_00002_.png"

        workflow_entries = [
            {
                "file": Path("efficiency-nodes.json"),
                "expected": {
                    "has_save_node": True,
                    "filename_patterns": ["eff_xl"],
                    "filename_leaf_markers": ["eff_xl"],
                },
            },
            {
                "file": Path("efficiency-nodes-debug-hash.json"),
                "expected": {
                    "has_save_node": True,
                    "filename_patterns": ["eff_xl_hash"],
                    "filename_leaf_markers": ["eff_xl_hash"],
                },
            },
        ]

        workflow_to_images, ambiguous_matches = validator._assign_images_to_workflows(workflow_entries, [image_path])

        assert workflow_to_images[Path("efficiency-nodes.json")] == []
        assert workflow_to_images[Path("efficiency-nodes-debug-hash.json")] == [image_path]
        assert ambiguous_matches == {}

    def test_assign_images_marks_equal_strength_matches_ambiguous(self, tmp_path):
        validator = MetadataValidator(tmp_path, tmp_path)
        image_path = tmp_path / "zoo-cat_dog-bar_00001_.png"

        workflow_entries = [
            {
                "file": Path("cat.json"),
                "expected": {
                    "has_save_node": True,
                    "filename_patterns": ["cat"],
                    "filename_leaf_markers": ["cat"],
                },
            },
            {
                "file": Path("dog.json"),
                "expected": {
                    "has_save_node": True,
                    "filename_patterns": ["dog"],
                    "filename_leaf_markers": ["dog"],
                },
            },
        ]

        workflow_to_images, ambiguous_matches = validator._assign_images_to_workflows(workflow_entries, [image_path])

        assert workflow_to_images[Path("cat.json")] == []
        assert workflow_to_images[Path("dog.json")] == []
        assert ambiguous_matches[image_path] == ["cat.json", "dog.json"]


class TestSamplerValidation:
    """Test sampler and scheduler validation rules."""

    def _run_validation(self, fields: dict[str, str], expected: dict[str, Any]) -> dict:
        validator = MetadataValidator(Path("."), Path("."))
        result = {"errors": [], "warnings": [], "check_details": []}
        fields = {**fields}
        fields.setdefault("Metadata generator version", "test")
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


class TestPromptResolution:
    """Ensure prompt traversal stays aligned with the requested edge."""

    def test_guider_positive_and_negative_prompts_resolve_separately(self):
        workflow = {
            "save": {
                "class_type": "SaveImageWithMetaDataUniversal",
                "inputs": {
                    "images": ["decode", 0],
                    "filename_prefix": "Test\\guider-prompts",
                },
            },
            "decode": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["sampler", 0],
                    "vae": ["vae", 0],
                },
            },
            "sampler": {
                "class_type": "SamplerCustomAdvanced",
                "inputs": {
                    "steps": 20,
                    "cfg": 5,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "model": ["ckpt", 0],
                    "latent_image": ["latent", 0],
                    "guider": ["guider", 0],
                },
            },
            "guider": {
                "class_type": "BasicGuider",
                "inputs": {
                    "model": ["ckpt", 0],
                    "positive": ["positive_text", 0],
                    "negative": ["negative_text", 0],
                },
            },
            "positive_text": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "bright sunrise",
                },
            },
            "negative_text": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "low quality",
                },
            },
            "latent": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1,
                },
            },
            "ckpt": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "model.safetensors",
                },
            },
            "vae": {
                "class_type": "VAELoader",
                "inputs": {
                    "vae_name": "vae.safetensors",
                },
            },
        }

        expected = WorkflowAnalyzer.extract_expected_metadata(workflow, "guider-prompts")
        save_node_expected = expected["save_nodes"][0]

        assert save_node_expected["positive_prompt"] == "bright sunrise"
        assert save_node_expected["negative_prompt"] == "low quality"


class TestCliBehavior:
    """Test main() side effects and argument handling."""

    def test_main_rejects_missing_output_dir_before_setting_up_log(self, monkeypatch, tmp_path):
        missing_output = tmp_path / "missing-output"
        tee_calls: list[Path] = []

        monkeypatch.setattr(validate_metadata_module, "setup_print_tee", lambda path: tee_calls.append(path))
        monkeypatch.setattr(
            validate_metadata_module.sys,
            "argv",
            ["validate_metadata.py", "--output-folder", str(missing_output)],
        )

        exit_code = validate_metadata_module.main()

        assert exit_code == 1
        assert tee_calls == []
        assert not missing_output.exists()


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
