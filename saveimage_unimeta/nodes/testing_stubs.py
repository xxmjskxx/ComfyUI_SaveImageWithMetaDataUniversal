"""Lightweight metadata test nodes.

These nodes are only intended for local metadata validation runs. They expose
inputs that mimic the metadata surface of typical diffusion pipelines while
producing synthetic image tensors (solid-colour frames) to keep execution fast.
Enable them by setting METADATA_ENABLE_TEST_NODES=1 before ComfyUI starts.
"""

from __future__ import annotations

try:  # Prefer torch when available (normal ComfyUI runtime)
    import torch
except ImportError:  # pragma: no cover - fallback for minimal environments
    torch = None  # type: ignore

import numpy as np


def _make_batch(batch_size: int, height: int, width: int, colour: tuple[float, float, float]):
    batch_size = max(1, int(batch_size))
    height = max(1, int(height))
    width = max(1, int(width))
    r, g, b = (min(1.0, max(0.0, c)) for c in colour)

    if torch is not None:
        images = torch.zeros((batch_size, height, width, 3), dtype=torch.float32)
        images[..., 0] = r
        images[..., 1] = g
        images[..., 2] = b
        return images

    # Numpy fallback keeps interface compatible with Save node tests
    arr = np.zeros((batch_size, height, width, 3), dtype=np.float32)
    arr[..., 0] = r
    arr[..., 1] = g
    arr[..., 2] = b
    return arr


class MetadataTestSampler:
    """Generate a solid-colour image while exposing metadata-friendly inputs."""

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        return {
            "required": {
                "positive_prompt": (
                    "STRING",
                    {
                        "default": "Synthetic prompt for metadata validation",
                        "multiline": True,
                        "tooltip": "Positive prompt recorded in metadata.",
                    },
                ),
                "negative_prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "tooltip": "Negative prompt recorded in metadata.",
                    },
                ),
                "model_name": (
                    "STRING",
                    {
                        "default": "test_models/fake-model.safetensors",
                        "tooltip": "Model name reported in metadata (no file access).",
                    },
                ),
                "model_hash": (
                    "STRING",
                    {
                        "default": "FAKEHASH001",
                        "tooltip": "Precomputed hash string (optional metadata stub).",
                    },
                ),
                "vae_name": (
                    "STRING",
                    {
                        "default": "test_vaes/fake-vae.safetensors",
                        "tooltip": "VAE name reported in metadata (no file access).",
                    },
                ),
                "vae_hash": (
                    "STRING",
                    {
                        "default": "FAKEVAE001",
                        "tooltip": "Precomputed VAE hash string.",
                    },
                ),
                "clip_name1": (
                    "STRING",
                    {
                        "default": "test_clip/fake-clip-1.safetensors",
                        "tooltip": "Primary CLIP/encoder name recorded in metadata.",
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 123456,
                        "min": 0,
                        "max": 2**31 - 1,
                        "tooltip": "Seed value recorded in metadata.",
                    },
                ),
                "steps": (
                    "INT",
                    {
                        "default": 6,
                        "min": 1,
                        "max": 150,
                        "tooltip": "Step count recorded in metadata.",
                    },
                ),
                "cfg": (
                    "FLOAT",
                    {
                        "default": 3.0,
                        "min": 0.0,
                        "max": 30.0,
                        "step": 0.1,
                        "tooltip": "CFG scale recorded in metadata.",
                    },
                ),
                "sampler_name": (
                    "STRING",
                    {
                        "default": "euler",
                        "tooltip": "Sampler name recorded in metadata.",
                    },
                ),
                "scheduler": (
                    "STRING",
                    {
                        "default": "normal",
                        "tooltip": "Scheduler recorded in metadata.",
                    },
                ),
                "guidance": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.0,
                        "max": 30.0,
                        "step": 0.1,
                        "tooltip": "Guidance value; optionally mapped to CFG by the saver.",
                    },
                ),
                "width": (
                    "INT",
                    {
                        "default": 512,
                        "min": 16,
                        "max": 4096,
                        "tooltip": "Output width for synthetic image.",
                    },
                ),
                "height": (
                    "INT",
                    {
                        "default": 512,
                        "min": 16,
                        "max": 4096,
                        "tooltip": "Output height for synthetic image.",
                    },
                ),
                "batch_size": (
                    "INT",
                    {
                        "default": 1,
                        "min": 1,
                        "max": 8,
                        "tooltip": "Number of images to generate (metadata records batch info).",
                    },
                ),
                "colour_r": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.01,
                        "tooltip": "Red channel (0-1) for synthetic output.",
                    },
                ),
                "colour_g": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.01,
                        "tooltip": "Green channel (0-1) for synthetic output.",
                    },
                ),
                "colour_b": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.01,
                        "tooltip": "Blue channel (0-1) for synthetic output.",
                    },
                ),
                "generator_version": (
                    "STRING",
                    {
                        "default": "metadata-stub-1.0",
                        "tooltip": "Optional version string recorded under Metadata generator version.",
                    },
                ),
            },
            "optional": {
                "clip_name2": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Secondary CLIP entry (leave blank to skip).",
                    },
                ),
                "clip_name3": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Tertiary CLIP entry (leave blank to skip).",
                    },
                ),
                "clip_name4": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Additional CLIP entry (leave blank to skip).",
                    },
                ),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "generate"
    CATEGORY = "SaveImageWithMetaDataUniversal/Test"
    DESCRIPTION = "Produce a solid-colour image for metadata validation workflows."

    @staticmethod
    def generate(
        positive_prompt: str,
        negative_prompt: str,
        model_name: str,
        model_hash: str,
        vae_name: str,
        vae_hash: str,
        clip_name1: str,
        seed: int,
        steps: int,
        cfg: float,
        sampler_name: str,
        scheduler: str,
        guidance: float,
        width: int,
        height: int,
        batch_size: int,
        colour_r: float,
        colour_g: float,
        colour_b: float,
        generator_version: str,
        clip_name2: str = "",
        clip_name3: str = "",
        clip_name4: str = "",
    ):
        # suppress unused-variable warnings: the Save node reads these via the prompt graph
        _ = (
            positive_prompt,
            negative_prompt,
            model_name,
            model_hash,
            vae_name,
            vae_hash,
            clip_name1,
            clip_name2,
            clip_name3,
            clip_name4,
            seed,
            steps,
            cfg,
            sampler_name,
            scheduler,
            guidance,
            generator_version,
        )
        images = _make_batch(batch_size, height, width, (colour_r, colour_g, colour_b))
        return (images,)

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):  # noqa: N802
        return float("nan")


TEST_NODE_CLASS_MAPPINGS = {
    "MetadataTestSampler": MetadataTestSampler,
}

TEST_NODE_DISPLAY_NAME_MAPPINGS = {
    "MetadataTestSampler": "Metadata Test Sampler",
}

__all__ = [
    "MetadataTestSampler",
    "TEST_NODE_CLASS_MAPPINGS",
    "TEST_NODE_DISPLAY_NAME_MAPPINGS",
]
