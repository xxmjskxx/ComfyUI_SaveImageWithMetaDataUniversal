import os

# We assume tests run with working directory at project root of this custom node.
# Adjust path so we can import the package.
BASE = os.path.dirname(__file__)
PKG_ROOT = os.path.abspath(os.path.join(BASE, '..', 'saveimage_unimeta'))
if PKG_ROOT not in os.sys.path:
    os.sys.path.insert(0, os.path.abspath(os.path.join(BASE, '..')))

from saveimage_unimeta.capture import Capture, MetaField  # type: ignore  # noqa: E402


def _minimal_inputs(positive="a cat", negative=""):
    # Construct minimal mapping structure emulating earlier capture stage
    # Capture.gen_pnginfo_dict expects two snapshots: before_sampler, before_this
    before_sampler = {
        MetaField.POSITIVE_PROMPT: [("n1", positive, "positive")],
        MetaField.NEGATIVE_PROMPT: [("n2", negative, "negative")],
        MetaField.SAMPLER_NAME: [("n3", "Euler a")],
        MetaField.CFG: [("n4", 7.5)],
        MetaField.GUIDANCE: [("n5", 12.3)],
    }
    before_this = before_sampler.copy()
    return before_sampler, before_this


def test_guidance_as_cfg_enabled():
    before_sampler, before_this = _minimal_inputs()
    pnginfo = Capture.gen_pnginfo_dict(before_sampler, before_this, save_civitai_sampler=False)
    # sanity baseline
    assert pnginfo["CFG scale"] == 7.5
    assert pnginfo["Guidance"] == 12.3

    param_str = Capture.gen_parameters_str(pnginfo, include_lora_summary=True, guidance_as_cfg=True)
    # Guidance should be removed, and CFG scale should reflect guidance value (12.3)
    assert "Guidance:" not in param_str
    assert "CFG scale: 12.3" in param_str


def test_guidance_as_cfg_disabled():
    before_sampler, before_this = _minimal_inputs()
    pnginfo = Capture.gen_pnginfo_dict(before_sampler, before_this, save_civitai_sampler=False)
    param_str = Capture.gen_parameters_str(pnginfo, include_lora_summary=True, guidance_as_cfg=False)
    # Original behavior: both fields present with original values
    assert "CFG scale: 7.5" in param_str
    assert "Guidance: 12.3" in param_str
