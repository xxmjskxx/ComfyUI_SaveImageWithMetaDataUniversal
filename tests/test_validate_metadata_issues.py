"""Test validate_metadata.py validation of metadata quality issues."""

import json
import sys
from pathlib import Path

import pytest

# Add comfyui_cli_tests directory to path to import validate_metadata
sys.path.insert(0, str(Path(__file__).parent / 'comfyui_cli_tests'))

from validate_metadata import MetadataValidator


class TestMetadataQualityValidation:
    """Test validation of metadata quality issues."""

    def test_detect_na_values(self):
        """Test that N/A values in metadata are detected as errors."""
        validator = MetadataValidator(Path('.'), Path('.'))

        params_str = (
            "test prompt\nNegative prompt: bad\n"
            "Steps: 20, Sampler: euler, CFG scale: 7, Seed: 123, "
            "Embedding_0 name: TestEmbed, Embedding_0 hash: N/A, Model hash: N/A"
        )

        fields = validator.parse_parameters_string(params_str)
        result = {'errors': [], 'warnings': []}

        # Check for N/A values
        for field_name, field_value in fields.items():
            if field_value == 'N/A' or 'N/A' in field_value:
                result['errors'].append(f"Field '{field_name}' contains 'N/A' value")

        # Should detect N/A in both Embedding_0 hash and Model hash
        assert len(result['errors']) == 2
        assert any('Embedding_0 hash' in err for err in result['errors'])
        assert any('Model hash' in err for err in result['errors'])

    def test_detect_prompts_as_embedding_names(self):
        """Test that prompts incorrectly recorded as embedding names are detected."""
        validator = MetadataValidator(Path('.'), Path('.'))

        # Very long "embedding name" suggests it's actually a prompt
        long_prompt = (
            "This is a very long prompt text that should not be an embedding name "
            "because embeddings have short names like EasyNegative or BadHands "
            "but this is clearly a full prompt"
        )
        params_str = (
            f"test prompt\nNegative prompt: bad\n"
            f"Steps: 20, Sampler: euler, Seed: 123, "
            f"Embedding_0 name: {long_prompt}, Embedding_0 hash: abc123"
        )

        fields = validator.parse_parameters_string(params_str)
        result = {'errors': [], 'warnings': []}

        # Validate embeddings
        validator._validate_embedding_fields(fields, result)

        # Check if Hashes validation detects the issue
        if 'Hashes' in fields:
            hashes_dict = json.loads(fields['Hashes'])
            validator._validate_hashes_summary(fields, hashes_dict, result)

        # Should detect that the embedding name is too long to be a real embedding
        assert any('appears to be a prompt' in err for err in result['errors'])

    def test_detect_prompts_as_embedding_hashes(self):
        """Test that prompts incorrectly recorded as embedding hashes are detected."""
        validator = MetadataValidator(Path('.'), Path('.'))

        # Hash that's actually a prompt
        fake_hash = (
            "This is clearly a prompt not a hash value because hashes are "
            "short alphanumeric strings"
        )
        params_str = (
            f"test prompt\nNegative prompt: bad\n"
            f"Steps: 20, Sampler: euler, Seed: 123, "
            f"Embedding_0 name: TestEmbed, Embedding_0 hash: {fake_hash}"
        )

        fields = validator.parse_parameters_string(params_str)
        result = {'errors': [], 'warnings': []}

        validator._validate_embedding_fields(fields, result)

        # Should detect that the embedding hash is too long to be a real hash
        assert any('Embedding hash' in err and 'appears to be a prompt' in err for err in result['errors'])

    def test_detect_trailing_punctuation_in_embedding_names(self):
        """Test that trailing punctuation in embedding names is detected."""
        validator = MetadataValidator(Path('.'), Path('.'))

        params_str = """test prompt
Negative prompt: bad
Steps: 20, Sampler: euler, Seed: 123, Embedding_0 name: EasyNegative,,, Embedding_0 hash: abc123"""

        fields = validator.parse_parameters_string(params_str)
        result = {'errors': [], 'warnings': []}

        validator._validate_embedding_fields(fields, result)

        # Should detect trailing commas
        assert any('trailing punctuation' in err for err in result['errors'])

    def test_detect_wrong_embedding_index_in_hashes(self):
        """Test that wrong embedding indexing in Hashes summary is detected."""
        validator = MetadataValidator(Path('.'), Path('.'))

        params_str = (
            "test prompt\nNegative prompt: bad\n"
            "Steps: 20, Sampler: euler, Seed: 123, "
            "Embedding_0 name: EasyNegative, Embedding_0 hash: c74b4e810b, "
            "Embedding_1 name: FastNegativeV2, Embedding_1 hash: a7465e7cc2, "
            'Hashes: {"model": "7a4dbba12f", "embed:10": "a7465e7cc2"}'
        )

        fields = validator.parse_parameters_string(params_str)
        result = {'errors': [], 'warnings': []}

        if 'Hashes' in fields:
            hashes_dict = json.loads(fields['Hashes'])
            validator._validate_hashes_summary(fields, hashes_dict, result)

        # Should detect that embed:10 is wrong (should be embed:FastNegativeV2)
        # and that EasyNegative is missing from Hashes
        assert any('wrong key' in err or 'missing from Hashes' in err for err in result['errors'])

    def test_detect_missing_embeddings_from_hashes(self):
        """Test that embeddings missing from Hashes summary are detected."""
        validator = MetadataValidator(Path('.'), Path('.'))

        params_str = (
            "test prompt\nNegative prompt: bad\n"
            "Steps: 20, Sampler: euler, Seed: 123, "
            "Embedding_0 name: EasyNegative, Embedding_0 hash: c74b4e810b, "
            "Embedding_1 name: FastNegativeV2, Embedding_1 hash: a7465e7cc2, "
            'Hashes: {"model": "7a4dbba12f", "vae": "c6a580b13a"}'
        )

        fields = validator.parse_parameters_string(params_str)
        result = {'errors': [], 'warnings': []}

        if 'Hashes' in fields:
            hashes_dict = json.loads(fields['Hashes'])
            validator._validate_hashes_summary(fields, hashes_dict, result)

        # Should detect that both embeddings are missing from Hashes
        assert len([err for err in result['errors'] if 'missing from Hashes' in err]) == 2

    def test_detect_missing_lora_from_hashes(self):
        """Test that LoRAs missing from Hashes summary are detected."""
        validator = MetadataValidator(Path('.'), Path('.'))

        params_str = (
            "test prompt\nNegative prompt: bad\n"
            "Steps: 20, Sampler: euler, Seed: 123, "
            "Lora_0 Model name: test_lora.safetensors, Lora_0 Model hash: abc123, "
            'Hashes: {"model": "def456"}'
        )

        fields = validator.parse_parameters_string(params_str)
        result = {'errors': [], 'warnings': []}

        if 'Hashes' in fields:
            hashes_dict = json.loads(fields['Hashes'])
            validator._validate_hashes_summary(fields, hashes_dict, result)

        # Should detect that LoRA is missing from Hashes
        assert any('missing from Hashes' in err and 'test_lora' in err for err in result['errors'])

    def test_detect_hash_mismatch_embedding(self):
        """Test that hash mismatches between metadata and Hashes are detected for embeddings."""
        validator = MetadataValidator(Path('.'), Path('.'))

        params_str = (
            "test prompt\nNegative prompt: bad\n"
            "Steps: 20, Sampler: euler, Seed: 123, "
            "Embedding_0 name: TestEmbed, Embedding_0 hash: abc123, "
            'Hashes: {"model": "def456", "embed:TestEmbed": "xyz789"}'
        )

        fields = validator.parse_parameters_string(params_str)
        result = {'errors': [], 'warnings': []}

        if 'Hashes' in fields:
            hashes_dict = json.loads(fields['Hashes'])
            validator._validate_hashes_summary(fields, hashes_dict, result)

        # Should detect hash mismatch
        assert any('hash mismatch' in err.lower() for err in result['errors'])

    def test_detect_hash_mismatch_lora(self):
        """Test that hash mismatches between metadata and Hashes are detected for LoRAs."""
        validator = MetadataValidator(Path('.'), Path('.'))

        params_str = (
            "test prompt\nNegative prompt: bad\n"
            "Steps: 20, Sampler: euler, Seed: 123, "
            "Lora_0 Model name: test_lora.safetensors, Lora_0 Model hash: abc123, "
            'Hashes: {"model": "def456", "lora:test_lora": "xyz789"}'
        )

        fields = validator.parse_parameters_string(params_str)
        result = {'errors': [], 'warnings': []}

        if 'Hashes' in fields:
            hashes_dict = json.loads(fields['Hashes'])
            validator._validate_hashes_summary(fields, hashes_dict, result)

        # Should detect hash mismatch
        assert any('hash mismatch' in err.lower() for err in result['errors'])

    def test_detect_hash_mismatch_model(self):
        """Test that hash mismatches between metadata and Hashes are detected for models."""
        validator = MetadataValidator(Path('.'), Path('.'))

        params_str = (
            "test prompt\nNegative prompt: bad\n"
            "Steps: 20, Sampler: euler, Seed: 123, Model hash: abc123, "
            'Hashes: {"model": "xyz789"}'
        )

        fields = validator.parse_parameters_string(params_str)
        result = {'errors': [], 'warnings': []}

        if 'Hashes' in fields:
            hashes_dict = json.loads(fields['Hashes'])
            validator._validate_hashes_summary(fields, hashes_dict, result)

        # Should detect hash mismatch
        assert any('hash mismatch' in err.lower() for err in result['errors'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
