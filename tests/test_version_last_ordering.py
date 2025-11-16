"""Test that Metadata generator version is always the last field in the parameter string."""
import importlib
from saveimage_unimeta.defs.meta import MetaField

MODULE_PATH = "saveimage_unimeta.capture"


def test_version_is_last_in_parameter_string():
    """Verify that 'Metadata generator version' always appears as the last field."""
    cap = importlib.import_module(MODULE_PATH)

    # Build synthetic inputs with various fields
    inputs = {
        MetaField.STEPS: [("n1", 28)],
        MetaField.CFG: [("n1", 6.5)],
        MetaField.SAMPLER: [("n2", "euler")],
        MetaField.SCHEDULER: [("n2", "karras")],
        MetaField.SEED: [("n3", 123456789)],
        MetaField.WIDTH: [("n4", 832)],
        MetaField.HEIGHT: [("n4", 1216)],
        MetaField.MODEL_NAME: [("n5", "test_model.safetensors")],
        MetaField.VAE_NAME: [("n6", "test_vae.safetensors")],
    }

    gen_params = getattr(cap.Capture, "gen_parameters_str", None)
    assert gen_params is not None, "gen_parameters_str not exposed"

    param_str = gen_params(inputs, inputs)

    # The parameter string should end with "Metadata generator version: X.Y.Z"
    # Strip whitespace and check the last line
    lines = [ln.strip() for ln in param_str.splitlines() if ln.strip()]
    assert len(lines) > 0, "Parameter string should not be empty"

    last_line = lines[-1]
    assert last_line.startswith("Metadata generator version:"), (
        f"Last line should be 'Metadata generator version:', but got: {last_line}\n"
        f"Full parameter string:\n{param_str}"
    )


def test_version_is_last_with_lora_and_embeddings():
    """Verify version is last even with LoRA and embedding fields present."""
    cap = importlib.import_module(MODULE_PATH)

    # Build inputs with LoRA and embedding fields that come after in dict order
    inputs = {
        MetaField.STEPS: [("n1", 28)],
        MetaField.SEED: [("n3", 123456789)],
        MetaField.LORA_MODEL_NAME: [("n7", "lora1.safetensors"), ("n7", "lora2.safetensors")],
        MetaField.LORA_STRENGTH_MODEL: [("n7", 0.8), ("n7", 0.6)],
        MetaField.LORA_STRENGTH_CLIP: [("n7", 0.7), ("n7", 0.5)],
    }

    gen_params = getattr(cap.Capture, "gen_parameters_str", None)
    assert gen_params is not None, "gen_parameters_str not exposed"

    param_str = gen_params(inputs, inputs)
    lines = [ln.strip() for ln in param_str.splitlines() if ln.strip()]

    last_line = lines[-1]
    assert last_line.startswith("Metadata generator version:"), (
        f"Version should be last even with LoRA fields, but got: {last_line}\n"
        f"Full parameter string:\n{param_str}"
    )


def test_version_is_last_with_hashes_summary():
    """Verify version is last even when Hashes summary is present."""
    cap = importlib.import_module(MODULE_PATH)

    inputs = {
        MetaField.STEPS: [("n1", 28)],
        MetaField.SEED: [("n3", 123456789)],
        MetaField.MODEL_NAME: [("n5", "test_model.safetensors")],
        MetaField.MODEL_HASH: [("n5", "abc1234567")],
    }

    gen_params = getattr(cap.Capture, "gen_parameters_str", None)
    assert gen_params is not None, "gen_parameters_str not exposed"

    param_str = gen_params(inputs, inputs)
    lines = [ln.strip() for ln in param_str.splitlines() if ln.strip()]

    last_line = lines[-1]
    # Hashes might be on the second-to-last line, but version should always be last
    assert last_line.startswith("Metadata generator version:"), (
        f"Version should be last after Hashes, but got: {last_line}\n"
        f"Full parameter string:\n{param_str}"
    )
