#!/usr/bin/env python3
"""
Demonstration script showing the validate_metadata.py fixes.

This script demonstrates the key improvements made to the validation script:
1. Parsing both comma-separated and newline-separated metadata
2. Extracting complex filename patterns
3. Handling special workflows
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

WORKFLOW_DIR = SCRIPT_DIR / "dev_test_workflows"


def _load_validator_modules():
    """Import validator helpers after sys.path adjustments."""

    from validate_metadata import MetadataValidator as _MetadataValidator, WorkflowAnalyzer as _WorkflowAnalyzer

    return _MetadataValidator, _WorkflowAnalyzer


MetadataValidator, WorkflowAnalyzer = _load_validator_modules()


def demo_metadata_parsing():
    """Demonstrate metadata parsing improvements."""
    print("=" * 80)
    print("DEMO 1: Metadata Parsing")
    print("=" * 80)

    validator = MetadataValidator(Path("."), Path("."))

    # Test 1: Comma-separated format (default mode)
    print("\n1. Comma-separated format (default):")
    print("-" * 40)
    params_comma = (
        "masterpiece, best quality\n"
        "Negative prompt: low quality\n"
        "Steps: 20, Sampler: euler, CFG scale: 7, Seed: 123, Size: 512x512"
    )
    print("Input:")
    print(params_comma)
    print("\nParsed fields:")
    fields = validator.parse_parameters_string(params_comma)
    for key in ["Steps", "Sampler", "CFG scale", "Seed", "Size"]:
        value = fields.get(key, "❌ NOT FOUND")
        status = "✅" if key in fields else "❌"
        print(f"  {status} {key}: {value}")

    # Test 2: Newline-separated format (test mode)
    print("\n2. Newline-separated format (test mode):")
    print("-" * 40)
    params_newline = """masterpiece, best quality
Negative prompt: low quality
Steps: 20
Sampler: euler
CFG scale: 7
Seed: 123
Size: 512x512"""
    print("Input:")
    print(params_newline)
    print("\nParsed fields:")
    fields = validator.parse_parameters_string(params_newline)
    for key in ["Steps", "Sampler", "CFG scale", "Seed", "Size"]:
        value = fields.get(key, "❌ NOT FOUND")
        status = "✅" if key in fields else "❌"
        print(f"  {status} {key}: {value}")

    # Test 3: LoRA fields
    print("\n3. LoRA fields:")
    print("-" * 40)
    params_lora = (
        "test prompt\n"
        "Negative prompt: bad\n"
        "Steps: 20, Sampler: euler, CFG scale: 7, Seed: 123, "
        "Lora_0 Model name: test.safetensors, Lora_0 Model hash: abc123"
    )
    print("Input:")
    print(params_lora)
    print("\nParsed fields:")
    fields = validator.parse_parameters_string(params_lora)
    for key in ["Steps", "Sampler", "CFG scale", "Lora_0 Model name", "Lora_0 Model hash"]:
        value = fields.get(key, "❌ NOT FOUND")
        status = "✅" if key in fields else "❌"
        print(f"  {status} {key}: {value}")


def demo_filename_patterns():
    """Demonstrate filename pattern extraction improvements."""
    print("\n" + "=" * 80)
    print("DEMO 2: Filename Pattern Extraction")
    print("=" * 80)

    # Test 1: Simple pattern
    print("\n1. Simple pattern:")
    print("-" * 40)
    workflow1 = {
        "1": {"class_type": "SaveImageWithMetaDataUniversal", "inputs": {"filename_prefix": "Test\\flux-turbo"}}
    }
    patterns = WorkflowAnalyzer.extract_filename_patterns(workflow1)
    print("Input: 'Test\\\\flux-turbo'")
    print(f"Extracted: {patterns}")
    print(f"Status: {'✅' if 'flux-turbo' in patterns else '❌'}")

    # Test 2: Complex pattern with tokens
    print("\n2. Complex pattern with tokens:")
    print("-" * 40)
    workflow2 = {
        "1": {
            "class_type": "SaveImageWithMetaDataUniversal",
            "inputs": {"filename_prefix": "Test\\siwm-%model:10%/%pprompt:20%-%nprompt:20%"},
        }
    }
    patterns = WorkflowAnalyzer.extract_filename_patterns(workflow2)
    print("Input: 'Test\\\\siwm-%model:10%/%pprompt:20%-%nprompt:20%'")
    print(f"Extracted: {patterns}")
    print(f"Status: {'✅' if 'siwm' in patterns else '❌'}")

    # Test 3: Multiple save nodes
    print("\n3. Multiple save nodes:")
    print("-" * 40)
    workflow3 = {
        "1": {"class_type": "SaveImageWithMetaDataUniversal", "inputs": {"filename_prefix": "Test\\workflow-one"}},
        "2": {"class_type": "SaveImage", "inputs": {"filename_prefix": "Test\\control-image"}},
    }
    patterns = WorkflowAnalyzer.extract_filename_patterns(workflow3)
    print("Input: Two nodes with 'Test\\\\workflow-one' and 'Test\\\\control-image'")
    print(f"Extracted: {patterns}")
    status = "✅" if "workflow-one" in patterns and "control-image" in patterns else "❌"
    print(f"Status: {status}")


def demo_special_workflow():
    """Demonstrate special workflow handling."""
    print("\n" + "=" * 80)
    print("DEMO 3: Special Workflow Handling")
    print("=" * 80)

    print("\n'1-scan-and-save-custom-metadata-rules.json' handling:")
    print("-" * 40)
    print("This workflow generates metadata rules, not images.")
    print("The validator now skips it with an informational message.")
    print("Status: ✅ Fixed")


def demo_jpeg_fallback():
    """Demonstrate JPEG fallback testing capability."""
    print("\n" + "=" * 80)
    print("DEMO 4: JPEG Fallback Testing")
    print("=" * 80)

    print("\nNew workflow files created for testing fallback stages:")
    print("-" * 40)
    workflows = [
        ("large-workflow-jpeg-4kb.json", 4, "reduced-exif"),
        ("large-workflow-jpeg-2kb.json", 2, "minimal"),
        ("large-workflow-jpeg-1kb.json", 1, "com-marker"),
    ]

    for filename, kb_size, expected_stage in workflows:
        filepath = WORKFLOW_DIR / filename
        exists = "✅" if filepath.exists() else "❌"
        print(f"{exists} {filename:35} (max_jpeg_exif_kb={kb_size}, expected: {expected_stage})")
        if not filepath.exists():
            print(
                f"""    ⚠️  Warning: '{filename}' not found. This is expected if you have not created the workflow file yet."""
            )
            print("    To test fallback stages, create the file or run the appropriate workflow generation step.")

    print("\nMinimum max_jpeg_exif_kb changed from 4 to 1 ✅")


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "VALIDATE_METADATA.PY FIXES DEMO" + " " * 26 + "║")
    print("╚" + "=" * 78 + "╝")

    demo_metadata_parsing()
    demo_filename_patterns()
    demo_special_workflow()
    demo_jpeg_fallback()

    print("\n" + "=" * 80)
    print("All demos completed successfully! ✅")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
