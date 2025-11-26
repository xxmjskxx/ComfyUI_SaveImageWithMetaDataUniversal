"""Integration tests for validate_metadata.py with sample image metadata."""

import json
import sys
from pathlib import Path

import pytest

try:
    from tests.tools.validate_metadata import MetadataValidator, WorkflowAnalyzer
except ModuleNotFoundError:  # pragma: no cover - fallback for direct invocation
    sys.path.insert(0, str(Path(__file__).parent / "tools"))
    from validate_metadata import MetadataValidator, WorkflowAnalyzer  # type: ignore


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

    def test_resolve_latent_attributes_walks_nested_nodes(self):
        """Ensure latent tracing finds closest dimensions and upstream batch size."""

        workflow = {
            "sampler": {
                "class_type": "KSampler",
                "inputs": {
                    "latent_image": ["router", 0],
                },
            },
            "router": {
                "class_type": "LatentUpscale",
                "inputs": {
                    "latent_image": ["source", 0],
                    "width": 1024,
                    "height": 768,
                },
            },
            "source": {
                "class_type": "EfficiencyLatentLoader",
                "inputs": {
                    "width": 960,
                    "height": 640,
                    "batch_size": 3,
                    "samples": ["base", 0],
                },
            },
            "base": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1,
                },
            },
        }

        sampler_inputs = workflow["sampler"]["inputs"]
        attrs = WorkflowAnalyzer.resolve_latent_attributes(workflow, sampler_inputs)

        assert attrs["image_width"] == 1024
        assert attrs["image_height"] == 768
        assert attrs["batch_size"] == 3

    def test_expected_metadata_merges_inline_and_stack_loras(self):
        """Inline loader LoRAs should merge with stack nodes for validation."""

        workflow = {
            "save": {
                "class_type": "SaveImageWithMetaDataUniversal",
                "inputs": {
                    "images": ["vae_decode", 0],
                    "filename_prefix": "demo",
                },
            },
            "vae_decode": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["sampler", 0],
                },
            },
            "sampler": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["model_loader", 0],
                    "latent_image": ["latent_router", 0],
                    "steps": 20,
                    "cfg": 6.5,
                    "sampler_name": "euler",
                },
            },
            "latent_router": {
                "class_type": "LatentUpscale",
                "inputs": {
                    "latent_image": ["latent_source", 0],
                    "width": 1024,
                    "height": 768,
                },
            },
            "latent_source": {
                "class_type": "EfficiencyLatentLoader",
                "inputs": {
                    "width": 960,
                    "height": 640,
                    "batch_size": 2,
                },
            },
            "model_loader": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "base_model.safetensors",
                    "lora_stack": ["lora_stack_node", 0],
                    "lora_name": "inline_lora.safetensors",
                },
            },
            "lora_stack_node": {
                "class_type": "LoraStacker",
                "inputs": {
                    "input_mode": "advanced",
                    "lora_count": 2,
                    "lora_name_1": "stack_a.safetensors",
                    "model_str_1": 0.8,
                    "clip_str_1": 0.5,
                    "lora_name_2": "stack_b.safetensors",
                    "model_str_2": 0.6,
                    "clip_str_2": 0.4,
                },
            },
        }

        expected = WorkflowAnalyzer.extract_expected_metadata(workflow, "demo-workflow")
        assert expected["has_save_node"]
        save_node = expected["save_nodes"][0]

        merged_names = sorted(entry["name"] for entry in save_node.get("lora_stack", []))
        assert merged_names == [
            "inline_lora.safetensors",
            "stack_a.safetensors",
            "stack_b.safetensors",
        ]
        assert save_node["image_width"] == 1024
        assert save_node["image_height"] == 768
        assert save_node["batch_size"] == 2
        assert save_node.get("include_lora_summary") is True



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


def test_workflow_analyzer_marks_modelonly_clip_strength_none():
    """Synthetic workflow proves ModelOnly loaders skip clip-strength expectations."""

    workflow = {
        "sampler": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "model": ["lora_loader", 0],
            },
        },
        "lora_loader": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "lora_name": "demo_lora.safetensors",
                "strength_model": 0.42,
                "model": ["ckpt_loader", 0],
            },
        },
        "ckpt_loader": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "base_model.safetensors",
            },
        },
    }

    info = WorkflowAnalyzer.resolve_model_hierarchy(workflow, "sampler")
    lora_stack = info.get("lora_stack")
    assert lora_stack, "Expected synthetic workflow to expose a LoRA stack"
    assert lora_stack[0]["clip_strength"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
