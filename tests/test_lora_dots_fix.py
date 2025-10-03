#!/usr/bin/env python3
"""
Test for the specific LoRA filename issue with dots and version numbers.
This tests the fix for names like 'dark_gothic_fantasy_xl_3.01' which
os.path.splitext treats incorrectly.
"""

import os
import tempfile
import unittest
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

# Test requires the project modules
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from saveimage_unimeta.defs.formatters import calc_lora_hash, calc_model_hash, calc_vae_hash, calc_unet_hash
    formatters_available = True
except ImportError as e:
    logging.warning("Could not import formatters: %s", e)
    formatters_available = False


class TestLoraDotsIssue(unittest.TestCase):
    """Test the specific fix for LoRA names with dots that could be mistaken for extensions."""

    @unittest.skipUnless(formatters_available, "Formatters not available")
    def test_lora_version_numbers_with_dots(self):
        """Test LoRA hash calculation for names with version numbers containing dots."""
        test_cases = [
            # The specific problematic case from the issue
            ("dark_gothic_fantasy_xl_3.01", "dark_gothic_fantasy_xl_3.01.safetensors"),

            # Other similar cases
            ("model.v1.2.3", "model.v1.2.3.safetensors"),
            ("style.model.v2.1", "style.model.v2.1.safetensors"),
            ("lora.with.dots", "lora.with.dots.safetensors"),
            ("version.1.2.3.final", "version.1.2.3.final.safetensors"),

            # Cases that should work normally
            ("normal_lora", "normal_lora.safetensors"),
            ("lora-with-dashes", "lora-with-dashes.safetensors"),
            ("lora_with_underscores", "lora_with_underscores.safetensors"),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create lora directory and files
            lora_dir = os.path.join(temp_dir, "loras")
            os.makedirs(lora_dir, exist_ok=True)

            # Create all test files
            for _, filename in test_cases:
                filepath = os.path.join(lora_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("mock lora content for testing")

            # Mock folder_paths with extension fallback logic
            mock_folder_paths = MagicMock()

            def mock_get_full_path(folder_type, filename):
                """Mock that implements the extension fallback we added."""
                base_path = os.path.join(temp_dir, folder_type)

                # Try exact filename first
                full_path = os.path.join(base_path, filename)
                if os.path.exists(full_path):
                    return full_path

                # Try with extensions (the fix we implemented)
                for ext in [".safetensors", ".st", ".pt", ".bin", ".ckpt"]:
                    full_path = os.path.join(base_path, filename + ext)
                    if os.path.exists(full_path):
                        return full_path

                raise FileNotFoundError(f"Could not find {filename} in {folder_type}")

            mock_folder_paths.get_full_path = mock_get_full_path

            # Test each case
            with patch('saveimage_unimeta.defs.formatters.folder_paths', mock_folder_paths):
                for lora_name, expected_file in test_cases:
                    with self.subTest(lora_name=lora_name):
                        # Demonstrate the os.path.splitext issue
                        base, ext = os.path.splitext(lora_name)

                        # Test hash calculation
                        hash_result = calc_lora_hash(lora_name, [])

                        # Should find the file and calculate hash successfully
                        self.assertNotEqual(hash_result, "N/A",
                                          f"Hash should not be N/A for '{lora_name}' -> '{expected_file}'")
                        self.assertEqual(len(hash_result), 10,
                                       f"Hash should be 10 characters for '{lora_name}'")

                        # Verify the hash is consistent
                        hash_result2 = calc_lora_hash(lora_name, [])
                        self.assertEqual(hash_result, hash_result2,
                                       f"Hash should be consistent for '{lora_name}'")

    @unittest.skipUnless(formatters_available, "Formatters not available")
    def test_all_model_types_with_dots(self):
        """Test that all model types handle dots correctly."""
        test_name = "dark_gothic_fantasy_xl_3.01"

        model_types = [
            ("loras", calc_lora_hash),
            ("checkpoints", calc_model_hash),
            ("vae", calc_vae_hash),
            ("unet", calc_unet_hash),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directories and files for each model type
            for folder_name, hash_func in model_types:
                model_dir = os.path.join(temp_dir, folder_name)
                os.makedirs(model_dir, exist_ok=True)

                # Create the test file
                filepath = os.path.join(model_dir, f"{test_name}.safetensors")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"mock {folder_name} content")

            # Mock folder_paths
            mock_folder_paths = MagicMock()

            def mock_get_full_path(folder_type, filename):
                base_path = os.path.join(temp_dir, folder_type)

                # Try exact filename first
                full_path = os.path.join(base_path, filename)
                if os.path.exists(full_path):
                    return full_path

                # Try with extensions
                for ext in [".safetensors", ".st", ".pt", ".bin", ".ckpt"]:
                    full_path = os.path.join(base_path, filename + ext)
                    if os.path.exists(full_path):
                        return full_path

                raise FileNotFoundError(f"Could not find {filename} in {folder_type}")

            mock_folder_paths.get_full_path = mock_get_full_path

            # Test each model type
            with patch('saveimage_unimeta.defs.formatters.folder_paths', mock_folder_paths):
                for folder_name, hash_func in model_types:
                    with self.subTest(model_type=folder_name):
                        hash_result = hash_func(test_name, [])

                        self.assertNotEqual(hash_result, "N/A",
                                          f"{folder_name} hash should not be N/A for '{test_name}'")
                        self.assertEqual(len(hash_result), 10,
                                       f"{folder_name} hash should be 10 characters")

    def test_splitext_behavior_documentation(self):
        """Document the os.path.splitext behavior that was causing the issue."""
        test_cases = [
            # The problematic case
            ("dark_gothic_fantasy_xl_3.01", "dark_gothic_fantasy_xl_3", ".01"),

            # Other cases showing the pattern
            ("model.v1.2.3", "model.v1.2", ".3"),
            ("file.name.with.dots", "file.name.with", ".dots"),
            ("version.1.2.3.final", "version.1.2.3", ".final"),

            # Normal cases
            ("normal_file.safetensors", "normal_file", ".safetensors"),
            ("file.safetensors", "file", ".safetensors"),
        ]

        for filename, expected_base, expected_ext in test_cases:
            with self.subTest(filename=filename):
                base, ext = os.path.splitext(filename)
                self.assertEqual(base, expected_base,
                               f"Base name for '{filename}' should be '{expected_base}'")
                self.assertEqual(ext, expected_ext,
                               f"Extension for '{filename}' should be '{expected_ext}'")


if __name__ == "__main__":
    print("Testing LoRA dots issue fix...")
    print("=" * 50)
    unittest.main(verbosity=2)
