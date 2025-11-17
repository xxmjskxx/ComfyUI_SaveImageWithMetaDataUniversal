"""Provides lightweight test nodes for metadata validation.

These nodes are intended for use in local testing and validation of the
metadata capture process. They mimic the inputs of a typical diffusion
pipeline but produce simple, synthetic image tensors, allowing for fast
execution without the need for actual models. To enable these nodes, the
`METADATA_ENABLE_TEST_NODES` environment variable must be set to `1` before
starting ComfyUI.
"""

from __future__ import annotations

try:  # Prefer torch when available (normal ComfyUI runtime)
    import torch
except ImportError:  # pragma: no cover - fallback for minimal environments
    torch = None  # type: ignore

import numpy as np


def _make_batch(batch_size: int, height: int, width: int, colour: tuple[float, float, float]):
    """Create a batch of solid-color images.

    This function generates a batch of images as either a PyTorch tensor or a
    NumPy array, depending on whether PyTorch is available. The images are
    filled with a single specified color.

    Args:
        batch_size (int): The number of images to generate in the batch.
        height (int): The height of the images.
        width (int): The width of the images.
        colour (tuple[float, float, float]): The RGB color of the images, with
            each component in the range [0.0, 1.0].

    Returns:
        torch.Tensor or numpy.ndarray: A batch of images.
    """
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
    """A test node that generates a solid-color image.

    This node is a lightweight sampler that produces a synthetic image while
    exposing a comprehensive set of inputs that mimic a real diffusion
    pipeline. This allows for testing the metadata capture and saving process
    without the overhead of running a full model.
    """

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        """Define the input types for the `MetadataTestSampler` node.

        This method specifies a wide range of inputs, including prompts, model
        and VAE information, sampler settings, and image dimensions, all of
        which are intended to be captured as metadata.

        Returns:
            dict: A dictionary defining the input schema for the node.
        """
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
    def generate(  # noqa: ARG004
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
        """Generate a solid-color test image for metadata validation.

        This method creates a batch of solid-color images based on the input
        dimensions and color. The other parameters are not used in the image
        generation but are exposed as inputs so they can be captured by the
        `SaveImageWithMetaDataUniversal` node for metadata testing.

        Args:
            positive_prompt (str): The positive prompt.
            negative_prompt (str): The negative prompt.
            model_name (str): The name of the model.
            model_hash (str): The hash of the model.
            vae_name (str): The name of the VAE.
            vae_hash (str): The hash of the VAE.
            clip_name1 (str): The name of the first CLIP model.
            seed (int): The seed for generation.
            steps (int): The number of steps.
            cfg (float): The CFG scale.
            sampler_name (str): The name of the sampler.
            scheduler (str): The name of the scheduler.
            guidance (float): The guidance scale.
            width (int): The width of the output image.
            height (int): The height of the output image.
            batch_size (int): The number of images to generate.
            colour_r (float): The red component of the image color.
            colour_g (float): The green component of the image color.
            colour_b (float): The blue component of the image color.
            generator_version (str): The version of the metadata generator.
            clip_name2 (str, optional): The name of the second CLIP model. Defaults to "".
            clip_name3 (str, optional): The name of the third CLIP model. Defaults to "".
            clip_name4 (str, optional): The name of the fourth CLIP model. Defaults to "".

        Returns:
            tuple[torch.Tensor | np.ndarray]: A tuple containing the batch of
                generated images.
        """
        # These parameters are intentionally unused in this stub node.
        # The Save node reads them via the prompt graph for metadata capture.
        images = _make_batch(batch_size, height, width, (colour_r, colour_g, colour_b))
        return (images,)

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):  # noqa: N802
        """Indicate that the node's output can change even if inputs are the same.

        This method returns `float("nan")` to signal to ComfyUI that this node
        should be re-executed every time the graph is run.

        Returns:
            float: A NaN value.
        """
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
