"""Test validate_metadata.py with wan21 workflow containing Chinese characters."""

import sys
from pathlib import Path

import pytest

try:
    from tests.tools.validate_metadata import MetadataValidator
except ModuleNotFoundError:  # pragma: no cover - fallback for direct invocation
    # Add tests/tools directory to path to import validate_metadata when running the test directly
    sys.path.insert(0, str(Path(__file__).parent / "tools"))
    from validate_metadata import MetadataValidator  # type: ignore


class TestWan21ChineseMetadata:
    """Test the parser with actual wan21 workflow metadata containing Chinese characters."""

    def test_parse_wan21_metadata_with_chinese_characters(self):
        """Test parsing wan21 metadata with Chinese characters in embeddings and negative prompt."""
        validator = MetadataValidator(Path("."), Path("."))

        # This is actual metadata from Wan21_00001_.png
        # Contains Chinese characters in negative prompt and embedding fields
        # Using string concatenation to avoid line length issues
        prompt = "a fox moving quickly in a beautiful winter scenery nature trees mountains daytime tracking camera"
        neg_prompt = (
            "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，"
            "最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，"
            "画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，"
            "杂乱的背景，三条腿，背景人很多，倒着走"
        )
        metadata = (
            "Steps: 4, Sampler: dpmpp_2m Karras, CFG scale: 1.0, Denoise: 1.0, "
            "Seed: 82628696717253, Size: 1344x1504, "
            "Model: Wan2_1-T2V-14B_fp8_e4m3fn_scaled_KJ.safetensors, "
            "Model hash: 5519e566e6, Weight dtype: default, "
            "VAE: wan_2.1_vae.safetensors, VAE hash: 2fc39d3135, Shift: 8.0, "
            "Lora_0 Model name: lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16_.safetensors, "
            "Lora_0 Model hash: 37d4921854, Lora_0 Strength model: 1.0, Lora_0 Strength clip: 1.0, "
            f"Embedding_0 name: {neg_prompt}, Embedding_0 hash: abc123, "
            'CLIP_1 Model name: umt5_xxl_fp8_e4m3fn_scaled, Hashes: {"model": "5519e566e6"}, '
            "Metadata generator version: 1.3.0"
        )
        params_str = f"{prompt}\nNegative prompt: {neg_prompt}\n{metadata}"

        fields = validator.parse_parameters_string(params_str)

        # Verify all required fields are extracted
        assert "Steps" in fields
        assert fields["Steps"] == "4"

        assert "Sampler" in fields
        assert fields["Sampler"] == "dpmpp_2m Karras"

        assert "CFG scale" in fields
        assert fields["CFG scale"] == "1.0"

        assert "Seed" in fields
        assert fields["Seed"] == "82628696717253"

        assert "Size" in fields
        assert fields["Size"] == "1344x1504"

        assert "Model" in fields
        assert "Wan2_1-T2V-14B" in fields["Model"]

        # Verify Chinese character fields are extracted
        assert "Embedding_0 name" in fields
        assert "色调艳丽" in fields["Embedding_0 name"]  # Chinese characters present
        assert "静态" in fields["Embedding_0 name"]
        assert "细节模糊不清" in fields["Embedding_0 name"]

        # Verify other fields
        assert "VAE" in fields
        assert "Lora_0 Model name" in fields
        assert "CLIP_1 Model name" in fields

        # Verify we got a good number of fields
        assert len(fields) >= 20, f"Expected at least 20 fields, got {len(fields)}"

    def test_wan21_image_exists(self):
        """Test that the wan21 reference image exists."""
        image_path = Path("tests/_test_outputs/Wan21_00006_.png")
        assert image_path.exists(), f"Wan21 reference image not found at {image_path}"

    def test_wan21_image_has_metadata(self):
        """Test that the wan21 image contains the expected metadata."""
        from PIL import Image

        image_path = Path("tests/_test_outputs/Wan21_00006_.png")
        if not image_path.exists():
            pytest.skip("Wan21 reference image not available")

        img = Image.open(image_path)

        # Verify PNG info is present
        assert hasattr(img, "info"), "Image has no info attribute"
        assert "parameters" in img.info, "Image has no 'parameters' field"

        params = img.info["parameters"]

        # Verify it contains Chinese characters
        assert "色调艳丽" in params, "Expected Chinese characters not found in parameters"

        # Verify it contains expected English fields
        assert "Steps:" in params
        assert "Sampler:" in params
        assert "Seed:" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
