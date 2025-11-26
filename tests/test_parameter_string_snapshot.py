import importlib
import re
from saveimage_unimeta.defs.meta import MetaField

MODULE_PATH = "saveimage_unimeta.capture"

# NOTE (future improvements): This test intentionally verifies only a minimal,
# stable subset of the parameter string contract to avoid brittle full snapshots.
# Potential safe extensions if/when we want tighter regression detection:
#   - Assert presence/format of width/height (e.g. combined size line or separate fields).
#   - Enforce uniqueness of core keys (Steps, Sampler, Seed) explicitly.
#   - Add ordering check for CFG scale relative to Steps and Sampler.
#   - Parametrize with METADATA_TEST_MODE=1 to validate multiline rendering variant.
#   - Introduce a partial snapshot (filtered allowlist) while still permitting additive fields.
# Keep this list updated if formatting guarantees evolve.


def _build_inputs(scheduler: str = "karras", sampler: str = "euler"):
    sampler_entry = [("n2", sampler)]
    return {
        MetaField.STEPS: [("n1", 28)],
        MetaField.CFG: [("n1", 6.5)],
        MetaField.SAMPLER_NAME: sampler_entry,
        MetaField.SCHEDULER: [("n2", scheduler)],
        MetaField.SEED: [("n3", 123456789)],
        MetaField.WIDTH: [("n4", 832)],
        MetaField.HEIGHT: [("n4", 1216)],
    }


def _render_lines(cap_module, inputs):
    gen_params = getattr(cap_module.Capture, "gen_parameters_str", None)
    assert gen_params is not None, "gen_parameters_str not exposed"
    param_str = gen_params(inputs, inputs)
    return [ln.strip() for ln in param_str.splitlines() if ln.strip()]


def test_parameter_string_core_lines(monkeypatch):
    cap = importlib.import_module(MODULE_PATH)
    inputs = _build_inputs(scheduler="normal")
    lines = _render_lines(cap, inputs)

    assert any(re.match(r"Steps:\s*28", line) for line in lines), lines
    assert any(re.match(r"CFG scale:\s*6\.5", line) for line in lines), lines
    # Default (non-Civitai) path must retain raw sampler_scheduler, even for "normal"
    assert any("Sampler: euler_normal" == line for line in lines if line.lower().startswith("sampler:")), lines
    assert any(re.match(r"Seed:\s*123456789", line) for line in lines), lines

    steps_line = next(i for i, line in enumerate(lines) if line.startswith("Steps:"))
    sampler_line = next(i for i, line in enumerate(lines) if line.startswith("Sampler:"))
    seed_line = next(i for i, line in enumerate(lines) if line.startswith("Seed:"))
    assert steps_line < sampler_line < seed_line, lines


def test_parameter_string_preserves_scheduler_suffix(monkeypatch):
    cap = importlib.import_module(MODULE_PATH)
    inputs = _build_inputs(scheduler="karras")
    lines = _render_lines(cap, inputs)

    assert any("Sampler: euler_karras" == line for line in lines if line.lower().startswith("sampler:")), lines


def test_parameter_string_civitai_sampler_formatting(monkeypatch):
    cap = importlib.import_module(MODULE_PATH)
    inputs = _build_inputs(scheduler="karras", sampler="dpmpp_2m")
    pnginfo = cap.Capture.gen_pnginfo_dict(inputs, inputs, save_civitai_sampler=True)
    param_str = cap.Capture.gen_parameters_str(pnginfo)
    lines = [ln.strip() for ln in param_str.splitlines() if ln.strip()]

    assert any("Sampler: DPM++ 2M Karras" == line for line in lines if line.lower().startswith("sampler:")), lines
