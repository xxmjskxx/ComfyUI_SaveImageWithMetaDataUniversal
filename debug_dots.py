#!/usr/bin/env python3
"""
Test script to demonstrate the issue with dots in LoRA names.
This will help us understand where the problem occurs.
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from saveimage_unimeta.utils.lora import find_lora_info
from saveimage_unimeta.defs.formatters import calc_lora_hash


def test_lora_with_dots():
    """Test LoRA files with dots in their names."""
    print("Testing LoRA handling with dots in filename...")

    # Test cases with various filename patterns
    test_cases = [
        "normal_lora",
        "lora.with.dots",
        "lora.v2.0",
        "model.name.with.many.dots.v1.2.3",
        "name.ending.with.dot.",
        ".starting.with.dot",
        "single.",
        ".single",
        "mixed-chars_123.v2.0.final"
    ]

    print("\n=== Testing LoRA index building and lookup ===")
    for test_name in test_cases:
        print(f"\nTesting: '{test_name}'")

        # Test finding lora info
        info = find_lora_info(test_name)
        if info:
            print(f"  Found in index: {info['filename']} -> {info['abspath']}")
        else:
            print("  Not found in index")

        # Test hash calculation
        try:
            hash_result = calc_lora_hash(test_name, [])
            print(f"  Hash result: {hash_result}")
        except Exception as e:
            print(f"  Hash calculation failed: {e}")

    print("\n=== Testing splitext behavior ===")
    for test_name in test_cases:
        base, ext = os.path.splitext(test_name)
        print(f"'{test_name}' -> base='{base}', ext='{ext}'")


if __name__ == "__main__":
    test_lora_with_dots()
