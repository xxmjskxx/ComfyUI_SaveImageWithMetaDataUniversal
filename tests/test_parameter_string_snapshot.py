import importlib
import re
from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.defs.meta import MetaField

MODULE_PATH = "ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture"


def test_parameter_string_core_lines(monkeypatch):
    cap = importlib.import_module(MODULE_PATH)
    # Build synthetic inputs for required fields
    inputs = {
        MetaField.STEPS: [("n1", 28)],
        MetaField.CFG: [("n1", 6.5)],
        MetaField.SAMPLER: [("n2", "euler")],
        MetaField.SCHEDULER: [("n2", "karras")],
        MetaField.SEED: [("n3", 123456789)],
        MetaField.WIDTH: [("n4", 832)],
        MetaField.HEIGHT: [("n4", 1216)],
    }

    gen_params = getattr(cap.Capture, "gen_parameters_str", None)
    assert gen_params is not None, "gen_parameters_str not exposed"

    param_str = gen_params(inputs, inputs)
    # Normalize line endings
    lines = [ln.strip() for ln in param_str.splitlines() if ln.strip()]

    # Core expectations
    assert any(re.match(r"Steps:\s*28", l) for l in lines), lines
    assert any(re.match(r"CFG scale:\s*6\.5", l) for l in lines), lines
    # Sampler with scheduler karras should map to Euler Karras
    assert any("Euler Karras" in l for l in lines if l.lower().startswith("sampler:")), lines
    assert any(re.match(r"Seed:\s*123456789", l) for l in lines), lines

    # Ordering heuristic: Steps before Sampler before Seed (if present)
    order_map = {key: idx for idx, key in enumerate(lines)}
    steps_line = next(i for i,l in enumerate(lines) if l.startswith("Steps:"))
    sampler_line = next(i for i,l in enumerate(lines) if l.startswith("Sampler:"))
    seed_line = next(i for i,l in enumerate(lines) if l.startswith("Seed:"))
    assert steps_line < sampler_line < seed_line, lines
