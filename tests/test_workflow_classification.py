"""Tests for Trace.classify_workflow_kind (txt2img vs img2img classification)."""

import importlib

try:  # Allow running tests both as editable install and from custom_nodes checkout
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta import trace as trace_mod
    from ComfyUI_SaveImageWithMetaDataUniversal.saveimage_unimeta.capture import Capture
except ModuleNotFoundError:  # pragma: no cover - fallback for local execution paths
    trace_mod = importlib.import_module("saveimage_unimeta.trace")
    Capture = importlib.import_module("saveimage_unimeta.capture").Capture


def _classify(sampler_id, prompt):
    return trace_mod.Trace.classify_workflow_kind(sampler_id, prompt)


def test_txt2img_empty_latent():
    """A sampler fed by an empty latent is txt2img."""
    prompt = {
        "sampler": {"class_type": "KSampler", "inputs": {"latent_image": ["latent", 0]}},
        "latent": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512}},
    }
    assert _classify("sampler", prompt) == "txt2img"


def test_img2img_load_image_to_vae_encode():
    """A sampler fed through VAEEncode from LoadImage is img2img."""
    prompt = {
        "sampler": {"class_type": "KSampler", "inputs": {"latent_image": ["vae", 0]}},
        "vae": {"class_type": "VAEEncode", "inputs": {"pixels": ["img", 0], "vae": ["ckpt", 2]}},
        "img": {"class_type": "LoadImage", "inputs": {"image": "foo.png"}},
    }
    assert _classify("sampler", prompt) == "img2img"


def test_img2img_masked_latent():
    """A masked latent path (LoadImageMask) is img2img."""
    prompt = {
        "sampler": {"class_type": "KSampler", "inputs": {"latent_image": ["vae", 0]}},
        "vae": {"class_type": "VAEEncode", "inputs": {"pixels": ["mask", 0]}},
        "mask": {"class_type": "LoadImageMask", "inputs": {"image": "mask.png", "channel": "red"}},
    }
    assert _classify("sampler", prompt) == "img2img"


def test_vae_encode_variant_is_img2img():
    """VAE encoder variants (e.g. inpaint) also classify img2img."""
    prompt = {
        "sampler": {"class_type": "KSampler", "inputs": {"latent_image": ["vae", 0]}},
        "vae": {"class_type": "VAEEncodeForInpaint", "inputs": {"pixels": ["img", 0]}},
        "img": {"class_type": "LoadImage", "inputs": {}},
    }
    assert _classify("sampler", prompt) == "img2img"


def test_no_sampler_defaults_to_txt2img():
    """A missing sampler node defaults to txt2img."""
    assert _classify("missing", {}) == "txt2img"


def test_multi_sampler_uses_selected_latent():
    """Each sampler is classified from its own latent input, not the others."""
    prompt = {
        "sampler_t2i": {"class_type": "KSampler", "inputs": {"latent_image": ["empty", 0]}},
        "empty": {"class_type": "EmptyLatentImage", "inputs": {}},
        "sampler_i2i": {"class_type": "KSampler", "inputs": {"latent_image": ["vae", 0]}},
        "vae": {"class_type": "VAEEncode", "inputs": {"pixels": ["img", 0]}},
        "img": {"class_type": "LoadImage", "inputs": {}},
    }
    assert _classify("sampler_t2i", prompt) == "txt2img"
    assert _classify("sampler_i2i", prompt) == "img2img"


def test_denoising_strength_emitted_for_img2img():
    """img2img params rename Denoise to A1111's 'Denoising strength'."""
    pnginfo = {
        "Positive prompt": "a cat",
        "Negative prompt": "",
        "Steps": 20,
        "Denoise": 0.6,
        "_workflow_kind": "img2img",
    }
    params = Capture.gen_parameters_str(pnginfo)
    assert "Denoising strength: 0.6" in params
    assert "Denoise:" not in params


def test_denoise_suppressed_for_txt2img():
    """txt2img params omit denoise entirely (not meaningful for txt2img)."""
    pnginfo = {
        "Positive prompt": "a cat",
        "Negative prompt": "",
        "Steps": 20,
        "Denoise": 1.0,
        "_workflow_kind": "txt2img",
    }
    params = Capture.gen_parameters_str(pnginfo)
    assert "Denoise" not in params
