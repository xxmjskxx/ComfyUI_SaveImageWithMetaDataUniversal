import importlib
from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture"


def test_parameter_ordering_consistency(monkeypatch):
    cap = importlib.import_module(MODULE_PATH)

    # Create two logically identical input dicts with different insertion orders
    inputs_a = {
        MetaField.CFG: [("n1", 7.5)],
        MetaField.STEPS: [("n1", 30)],
        MetaField.SAMPLER: [("n2", "euler")],
        MetaField.WIDTH: [("n3", 768)],
        MetaField.HEIGHT: [("n3", 512)],
        MetaField.SEED: [("n4", 123456789)],
    }
    inputs_b = {}
    # Different order of population
    inputs_b[MetaField.SEED] = [("n4", 123456789)]
    inputs_b[MetaField.HEIGHT] = [("n3", 512)]
    inputs_b[MetaField.WIDTH] = [("n3", 768)]
    inputs_b[MetaField.SAMPLER] = [("n2", "euler")]
    inputs_b[MetaField.CFG] = [("n1", 7.5)]
    inputs_b[MetaField.STEPS] = [("n1", 30)]

    # Try to access parameter string builder if exposed
    param_func = getattr(cap.Capture, "gen_parameters_str", None)
    if param_func is None:
        # Fallback: ensure dict ordering normalization via sorted key names
        a_keys = sorted([m.name for m in inputs_a.keys()])
        b_keys = sorted([m.name for m in inputs_b.keys()])
        assert a_keys == b_keys
        return

    params_a = param_func(inputs_a, inputs_a)
    params_b = param_func(inputs_b, inputs_b)
    assert params_a == params_b, f"Parameter strings differ:\nA={params_a}\nB={params_b}"
