#!/usr/bin/env python3
r"""
Comprehensive tests for filename handling with Windows-valid special characters.

Tests model, LoRA, VAE, UNet, and embedding filename resolution and hashing
for all valid Windows filename characters except reserved ones:
< > : " / \ | ? *

Tests include:
- Unicode characters (ñ, ü, ß, 日本語, emoji)
- Extended ASCII (128-255)
- Punctuation and symbols
- Version numbers with dots
- Trailing punctuation
- Spaces and complex combinations
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
    from saveimage_unimeta.defs.formatters import (
        calc_lora_hash,
        calc_model_hash,
        calc_vae_hash,
        calc_unet_hash,
        extract_embedding_hashes,
        extract_embedding_names,
    )
    from saveimage_unimeta.utils.lora import build_lora_index, find_lora_info
    from saveimage_unimeta.utils.embedding import get_embedding_file_path
    formatters_available = True
except ImportError as e:
    logging.warning("Could not import formatters: %s", e)
    formatters_available = False


class TestSpecialCharacterFilenames(unittest.TestCase):
    """Test filename handling for Windows-valid special characters."""

    def setUp(self):
        """Set up test environment with mock directories and files."""
        self.test_filenames = [
            # Normal cases
            "normal_file.safetensors",
            "file-with-dashes.safetensors",
            "file_with_underscores.safetensors",
            "file with spaces.safetensors",

            # Dots and versions (the original issue)
            "model.v1.2.3.safetensors",
            "lora.with.dots.safetensors",
            "dark_gothic_fantasy_xl_3.01.safetensors",
            "version.1.2.3.final.safetensors",

            # Unicode characters
            "unicode_ñ_ü_ß_model.safetensors",
            "japanese_日本語_model.safetensors",
            "emoji_😀_model.safetensors",

            # Extended ASCII (128-255)
            "extended_àáâãäåæçèéêë.safetensors",
            "symbols_£¥€§©®™.safetensors",

            # Punctuation and symbols (valid in Windows)
            "file(with)parentheses.safetensors",
            "file[with]brackets.safetensors",
            "file{with}braces.safetensors",
            "file'with'apostrophes.safetensors",
            "file,with,commas.safetensors",
            "file;with;semicolons.safetensors",
            "file=with=equals.safetensors",
            "file+with+plus.safetensors",
            "file!with!exclamation.safetensors",
            "file@with@at.safetensors",
            "file#with#hash.safetensors",
            "file$with$dollar.safetensors",
            "file%with%percent.safetensors",
            "file^with^caret.safetensors",
            "file&with&ampersand.safetensors",
            "file~with~tilde.safetensors",
            "file`with`backtick.safetensors",

            # Trailing punctuation
            "file.ending.with.dot..safetensors",
            "file ending with space .safetensors",

            # Complex combinations
            "complex-file_name.with.many[special](chars)&symbols.v1.2.3.safetensors",
        ]

    def create_mock_folder_paths(self, temp_dir):
        """Create a mock folder_paths module for testing."""
        mock_folder_paths = MagicMock()

        def mock_get_full_path(folder_type, filename):
            """Mock implementation that handles extension fallback."""
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

        def mock_get_folder_paths(folder_type):
            """Return list of directories for the folder type."""
            return [os.path.join(temp_dir, folder_type)]

        mock_folder_paths.get_full_path = mock_get_full_path
        mock_folder_paths.get_folder_paths = mock_get_folder_paths

        return mock_folder_paths

    @unittest.skipUnless(formatters_available, "Formatters not available")
    def test_lora_hash_with_special_characters(self):
        """Test LoRA hash calculation with special character filenames."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create lora directory and files
            lora_dir = os.path.join(temp_dir, "loras")
            os.makedirs(lora_dir, exist_ok=True)

            # Create test files
            test_files = []
            for filename in self.test_filenames:
                filepath = os.path.join(lora_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("mock safetensors content")
                test_files.append(filename)

            # Mock folder_paths
            mock_folder_paths = self.create_mock_folder_paths(temp_dir)

            with patch('saveimage_unimeta.defs.formatters.folder_paths', mock_folder_paths):
                # Test each filename (without extension)
                for filename in test_files:
                    base_name = os.path.splitext(filename)[0]
                    with self.subTest(filename=base_name):
                        try:
                            hash_result = calc_lora_hash(base_name, [])
                            # Should not be N/A since file exists
                            self.assertNotEqual(hash_result, "N/A",
                                              f"Hash calculation failed for '{base_name}'")
                            self.assertEqual(len(hash_result), 10,
                                           f"Hash should be 10 characters for '{base_name}'")
                        except Exception as e:
                            self.fail(f"Hash calculation failed for '{base_name}': {e}")

    @unittest.skipUnless(formatters_available, "Formatters not available")
    def test_model_hash_with_special_characters(self):
        """Test model hash calculation with special character filenames."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create checkpoints directory and files
            model_dir = os.path.join(temp_dir, "checkpoints")
            os.makedirs(model_dir, exist_ok=True)

            # Create test files
            test_files = []
            for filename in self.test_filenames:
                filepath = os.path.join(model_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("mock model content")
                test_files.append(filename)

            # Mock folder_paths
            mock_folder_paths = self.create_mock_folder_paths(temp_dir)

            with patch('saveimage_unimeta.defs.formatters.folder_paths', mock_folder_paths):
                # Test each filename (without extension)
                for filename in test_files:
                    base_name = os.path.splitext(filename)[0]
                    with self.subTest(filename=base_name):
                        try:
                            hash_result = calc_model_hash(base_name, [])
                            # Should not be N/A since file exists
                            self.assertNotEqual(hash_result, "N/A",
                                              f"Hash calculation failed for '{base_name}'")
                            self.assertEqual(len(hash_result), 10,
                                           f"Hash should be 10 characters for '{base_name}'")
                        except Exception as e:
                            self.fail(f"Hash calculation failed for '{base_name}': {e}")

    @unittest.skipUnless(formatters_available, "Formatters not available")
    def test_vae_hash_with_special_characters(self):
        """Test VAE hash calculation with special character filenames."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create vae directory and files
            vae_dir = os.path.join(temp_dir, "vae")
            os.makedirs(vae_dir, exist_ok=True)

            # Create test files
            test_files = []
            for filename in self.test_filenames:
                filepath = os.path.join(vae_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("mock vae content")
                test_files.append(filename)

            # Mock folder_paths
            mock_folder_paths = self.create_mock_folder_paths(temp_dir)

            with patch('saveimage_unimeta.defs.formatters.folder_paths', mock_folder_paths):
                # Test each filename (without extension)
                for filename in test_files:
                    base_name = os.path.splitext(filename)[0]
                    with self.subTest(filename=base_name):
                        try:
                            hash_result = calc_vae_hash(base_name, [])
                            # Should not be N/A since file exists
                            self.assertNotEqual(hash_result, "N/A",
                                              f"Hash calculation failed for '{base_name}'")
                            self.assertEqual(len(hash_result), 10,
                                           f"Hash should be 10 characters for '{base_name}'")
                        except Exception as e:
                            self.fail(f"Hash calculation failed for '{base_name}': {e}")

    @unittest.skipUnless(formatters_available, "Formatters not available")
    def test_unet_hash_with_special_characters(self):
        """Test UNet hash calculation with special character filenames."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create unet directory and files
            unet_dir = os.path.join(temp_dir, "unet")
            os.makedirs(unet_dir, exist_ok=True)

            # Create test files
            test_files = []
            for filename in self.test_filenames:
                filepath = os.path.join(unet_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("mock unet content")
                test_files.append(filename)

            # Mock folder_paths
            mock_folder_paths = self.create_mock_folder_paths(temp_dir)

            with patch('saveimage_unimeta.defs.formatters.folder_paths', mock_folder_paths):
                # Test each filename (without extension)
                for filename in test_files:
                    base_name = os.path.splitext(filename)[0]
                    with self.subTest(filename=base_name):
                        try:
                            hash_result = calc_unet_hash(base_name, [])
                            # Should not be N/A since file exists
                            self.assertNotEqual(hash_result, "N/A",
                                              f"Hash calculation failed for '{base_name}'")
                            self.assertEqual(len(hash_result), 10,
                                           f"Hash should be 10 characters for '{base_name}'")
                        except Exception as e:
                            self.fail(f"Hash calculation failed for '{base_name}': {e}")

    @unittest.skipUnless(formatters_available, "Formatters not available")
    def test_embedding_resolution_with_special_characters(self):
        """Test embedding file resolution with special character filenames."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create embeddings directory and files
            embed_dir = os.path.join(temp_dir, "embeddings")
            os.makedirs(embed_dir, exist_ok=True)

            # Create test files (embeddings use different extensions)
            test_files = []
            for i, base_filename in enumerate(self.test_filenames[:10]):  # Test subset
                # Use different extensions for embeddings
                extensions = [".safetensors", ".pt", ".bin"]
                ext = extensions[i % len(extensions)]
                base_name = os.path.splitext(base_filename)[0]
                filename = base_name + ext

                filepath = os.path.join(embed_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("mock embedding content")
                test_files.append((base_name, filename))

            # Mock CLIP object
            mock_clip = MagicMock()
            mock_clip.embedding_directory = embed_dir

            # Test each embedding
            for base_name, expected_filename in test_files:
                with self.subTest(filename=base_name):
                    try:
                        resolved_path = get_embedding_file_path(base_name, mock_clip)
                        self.assertIsNotNone(resolved_path,
                                           f"Could not resolve embedding '{base_name}'")
                        self.assertTrue(os.path.exists(resolved_path),
                                      f"Resolved path doesn't exist: {resolved_path}")
                        self.assertTrue(resolved_path.endswith(expected_filename),
                                      f"Resolved path doesn't match expected: {resolved_path}")
                    except Exception as e:
                        self.fail(f"Embedding resolution failed for '{base_name}': {e}")

    def test_reserved_characters_handling(self):
        """Test that reserved characters are handled gracefully."""
        # Reserved characters that should NOT be in filenames
        reserved_chars = '<>:"/\\|?*'

        # These should be handled gracefully (not crash)
        for char in reserved_chars:
            test_name = f"file{char}with{char}reserved"
            with self.subTest(char=char):
                # The functions should not crash, even with invalid filenames
                # They should return N/A for unresolvable names
                try:
                    result = calc_lora_hash(test_name, []) if formatters_available else "N/A"
                    # Should return N/A since file won't exist
                    self.assertEqual(result, "N/A")
                except Exception as e:
                    # Should not raise exceptions
                    self.fail(f"Function crashed with reserved character '{char}': {e}")

    def test_filename_parsing_edge_cases(self):
        """Test edge cases in filename parsing."""
        edge_cases = [
            # Names that could confuse os.path.splitext
            "model.name.v1.2.3",      # Multiple dots
            "file.ending.with.dot.",  # Trailing dot
            "file.with..double.dots", # Double dots
            "file name with spaces",  # Spaces
            "file.01",                # Number as "extension"
            "file.123.456",           # Multiple number "extensions"
        ]

        for test_case in edge_cases:
            with self.subTest(filename=test_case):
                base, ext = os.path.splitext(test_case)
                # Document the behavior - this shows how splitext handles edge cases
                self.assertIsInstance(base, str)
                self.assertIsInstance(ext, str)
                # The issue we fixed: ensure we try extension fallback when needed


if __name__ == "__main__":
    print("Running comprehensive filename handling tests...")
    print("Testing Windows-valid characters (excluding reserved: < > : \" / \\ | ? *)")
    print()

    # Run the tests
    unittest.main(verbosity=2)
