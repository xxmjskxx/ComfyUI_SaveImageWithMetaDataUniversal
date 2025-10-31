#!/usr/bin/env python3
"""
Debug script to demonstrate the issue with dots in LoRA names.
This helps understand where the problem occurs in filename resolution.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from saveimage_unimeta.utils.lora import find_lora_info
    from saveimage_unimeta.defs.formatters import calc_lora_hash
    imports_available = True
except ImportError as e:
    logger.warning("Could not import LoRA utilities: %s", e)
    imports_available = False


def test_lora_with_dots():
    """Test LoRA files with dots in their names."""
    logger.info("Testing LoRA handling with dots in filename...")

    if not imports_available:
        logger.error("Required imports not available, skipping test")
        return

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

    logger.info("=== Testing LoRA index building and lookup ===")
    for test_name in test_cases:
        logger.info("Testing: '%s'", test_name)

        # Test finding lora info
        try:
            info = find_lora_info(test_name)
            if info:
                logger.info("  Found in index: %s -> %s", info['filename'], info['abspath'])
            else:
                logger.info("  Not found in index")
        except Exception as e:
            logger.error("  Index lookup failed: %s", e)

        # Test hash calculation
        try:
            hash_result = calc_lora_hash(test_name, [])
            logger.info("  Hash result: %s", hash_result)
        except Exception as e:
            logger.error("  Hash calculation failed: %s", e)

    logger.info("=== Testing splitext behavior ===")
    for test_name in test_cases:
        base, ext = os.path.splitext(test_name)
        logger.info("'%s' -> base='%s', ext='%s'", test_name, base, ext)


if __name__ == '__main__':
    test_lora_with_dots()
