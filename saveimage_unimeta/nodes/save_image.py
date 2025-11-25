"""The core image saver node for writing images and UniMeta metadata.

This module bridges ComfyUI's saver protocol with UniMeta's capture pipeline.
It orchestrates Trace/Capture traversal, filename token expansion, metadata
generation (PNGInfo/EXIF/WebP), JPEG fallback stages, optional workflow dumps,
and hashing sidecars while remaining importable in isolated pytest runs via
runtime stubs.

This module provides the `SaveImageWithMetaDataUniversal` class, which is the
primary node responsible for saving images and embedding rich metadata. It
handles workflow tracing, metadata capture, filename token expansion, and
various image format specifics, including JPEG EXIF fallback logic.
"""

import json
import logging
import os
import re
from datetime import datetime

# Attempt to import ComfyUI's folder_paths; provide a lightweight fallback stub when
# running in isolated unit tests where the real module is absent. This mirrors the
# early stubbing done in tests/conftest.py but adds in-file resilience so that
# importing this module never hard-fails just because the test harness executed
# imports in a different order.
try:  # pragma: no cover - normal runtime path
    import folder_paths
except ModuleNotFoundError:  # pragma: no cover - isolated test fallback

    class _FolderPathsStub:  # minimal surface used by this module
        def __init__(self):
            import os as _os

            self._out = _os.path.abspath("tests/_test_outputs")
            try:
                _os.makedirs(self._out, exist_ok=True)
            except OSError:
                pass  # Directory creation may fail - tests will fail later if needed

        def get_output_directory(self):  # noqa: D401
            return self._out

        def get_save_image_path(self, prefix, output_dir, *_, **__):
            return (output_dir or self._out, prefix, 0, "", prefix)

        def get_folder_paths(self, kind):  # noqa: D401
            return []

        def get_full_path(self, kind, name):  # noqa: D401
            return name

    folder_paths = _FolderPathsStub()
import numpy as np
from ..utils.color import cstr

try:  # Comfy runtime provides this; tests may not
    from comfy.cli_args import args
except (ImportError, ModuleNotFoundError):  # fall back in isolated tests

    class _ArgsStub:
        disable_metadata = False

    args = _ArgsStub()
from PIL import Image
from PIL.PngImagePlugin import PngInfo

try:  # Normal runtime
    from .. import hook
except (ImportError, ModuleNotFoundError):  # circular or missing in isolated test

    class _HookStub:  # minimal attributes used
        current_save_image_node_id = 0
        current_prompt = {}

    hook = _HookStub()  # type: ignore
from .. import defs as defs_module
from ..capture import Capture
from ..defs import CAPTURE_FIELD_LIST
from ..defs import FORCED_INCLUDE_CLASSES
from ..defs.combo import SAMPLER_SELECTION_METHOD
from ..defs.samplers import SAMPLERS
from ..trace import Trace
from ..version import resolve_runtime_version

logger = logging.getLogger(__name__)
_DEBUG_VERBOSE = os.environ.get("METADATA_DEBUG", "0") not in (
    "0",
    "false",
    "False",
    None,
    "",
)
_RULES_VERSION_WARNING_EMITTED = False
_REFRESH_RULES_WORKFLOW = "example_workflows/refresh-rules.json"


def _maybe_warn_outdated_rules() -> None:
    """Warns the user if their metadata rules are outdated.

    This function checks the version of the loaded metadata rules against the
    runtime version of the package. If the versions do not match or the rules
    version is missing, it logs a warning message with instructions on how to
    refresh the rules.
    """
    global _RULES_VERSION_WARNING_EMITTED
    if _RULES_VERSION_WARNING_EMITTED:
        return
    runtime_version = resolve_runtime_version()
    rules_version = getattr(defs_module, "LOADED_RULES_VERSION", None)
    if not rules_version:
        reason = "Metadata capture rules are missing a version stamp."
    elif rules_version != runtime_version:
        reason = (
            "Metadata capture rules are out of date "
            f"(rules={rules_version}, package={runtime_version})."
        )
    else:
        return
    guidance = (
        "Refresh metadata capture rules via "
    )
    nodes_workflow = cstr("Metadata Rule Scanner").YELLOW + " + " + cstr("Save Custom Metadata Rules nodes").YELLOW + " " + \
        "or run the refresh workflow at " + cstr(f"{_REFRESH_RULES_WORKFLOW}.").YELLOW
    version_warning = cstr(f"[Metadata Loader] {reason} {guidance}").warn + nodes_workflow
    logger.warning(version_warning)
    _RULES_VERSION_WARNING_EMITTED = True


class SaveImageWithMetaDataUniversal:
    """A ComfyUI node to save images with universal node support for metadata embedding.

    This node is responsible for saving images in various formats (PNG, JPEG,
    WebP) while embedding comprehensive metadata captured from the workflow.
    It supports dynamic filename generation, workflow tracing to find the
    correct sampler, and handles the complexities of different metadata
    formats, including size limitations in JPEGs.
    """
    SAVE_FILE_FORMATS = ["png", "jpeg", "webp"]

    def __init__(self):
        """Initialize the `SaveImageWithMetaDataUniversal` node.

        This constructor sets up the initial state of the node, including the
        output directory and default compression level.
        """
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4
        # Track per-image fallback stages for tests / diagnostics
        self._last_fallback_stages: list[str] = []

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        """Define the input types for the `SaveImageWithMetaDataUniversal` node.

        This method specifies the inputs that the node accepts, including the
        images to be saved, filename options, sampler selection method, file
        format, and various other settings to control the output and metadata.

        Returns:
            dict: A dictionary defining the input schema for the node.
        """
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": (
                    "STRING",
                    {
                        "default": "ComfyUI",
                        "tooltip": (
                            "You can use %seed%, %width%, %height%, %pprompt%, %nprompt%, %model%, %date% in the "
                            "filename. Date can accept any variety of the yyyyMMddhhmmss format, e.g. %date:yy-MM-dd%."
                        ),
                    },
                ),
                "sampler_selection_method": (
                    SAMPLER_SELECTION_METHOD,
                    {
                        "tooltip": (
                            "How to choose which earlier sampler node's settings to record: farthest, nearest, "
                            "or by node id (see sampler_selection_node_id)."
                        ),
                    },
                ),
                "sampler_selection_node_id": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 999999999,
                        "step": 1,
                        "tooltip": (
                            "When method is 'By node ID', this specifies which sampler node to treat as "
                            "authoritative for Steps/CFG/etc."
                        ),
                    },
                ),
                "file_format": (
                    cls.SAVE_FILE_FORMATS,
                    {
                        "tooltip": (
                            "Image format for output. PNG retains full metadata; JPEG/WebP may strip or "
                            "re-encode some fields."
                        ),
                    },
                ),
            },
            "optional": {
                "lossless_webp": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": ("If using WebP, toggles lossless mode (ignores quality slider)."),
                    },
                ),
                "quality": (
                    "INT",
                    {
                        "default": 100,
                        "min": 1,
                        "max": 100,
                        "tooltip": ("Quality for lossy formats (JPEG/WebP lossy). 100 = best quality, larger files."),
                    },
                ),
                "max_jpeg_exif_kb": (
                    "INT",
                    {
                        "default": 60,
                        "min": 1,
                        "max": 64,  # Hard UI cap: real single APP1 EXIF segment practical limit ~64KB
                        "step": 1,
                        "tooltip": (
                            "Maximum EXIF payload (KB) to attempt embedding in JPEG.\nPractical hard cap ~64KB due to "
                            "single APP1 (EXIF) segment size; larger blocks are rejected or stripped. If exceeded, "
                            "fallback stages apply: reduced-exif (parameters only) -> minimal (trimmed) -> com-marker."
                            "\nYou should have no issues writing smaller workflows and metadata, but should "
                            "use PNG/WebP for full workflow storage with larger workflows and metadata."
                        ),
                    },
                ),
                "save_workflow_json": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": ("Save the workflow as a JSON file alongside the image."),
                    },
                ),
                "add_counter_to_filename": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": (
                            "Automatically append an incrementing counter to avoid overwriting existing files "
                            "with the same prefix."
                        ),
                    },
                ),
                "civitai_sampler": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "Add a Civitai-compatible sampler notation (if enabled) for better import fidelity on "
                            "Civitai."
                        ),
                    },
                ),
                "guidance_as_cfg": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "When enabled, record 'Guidance' value under 'CFG scale' and suppress separate Guidance "
                            "field. Makes guidance with models like FLUX Civitai-compatible (if enabled)."
                        ),
                    },
                ),
                "extra_metadata": (
                    "EXTRA_METADATA",
                    {
                        "tooltip": (
                            "Additional metadata key-value pairs from the Create Extra MetaData node to include in "
                            "the saved image."
                        )
                    },
                ),
                "save_workflow_image": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": ("If disabled, the workflow data will not be saved in the image metadata."),
                    },
                ),
                "include_lora_summary": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "Include a compact aggregated LoRAs summary line (set False to list only individual "
                            "Lora_X entries)."
                        ),
                    },
                ),
                "suppress_missing_class_log": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": (
                            "Hide the informational log about missing classes \nthat triggers a user JSON merge "
                            "('[Metadata Loader] Missing classes in defaults+ext ...').\nCan be useful to disable if "
                            "debugging problematic nodes"
                        ),
                    },
                ),
                # New unified hashing log control (models, LoRAs, embeddings, etc.)
                "model_hash_log": (
                    ["none", "filename", "path", "detailed", "debug"],
                    {
                        "default": "none",
                        "tooltip": (
                            "Artifact hashing log: filename=short, path=full, detailed=resolution+sidecar, "
                            "debug=+candidates+full hash."[:140]
                        ),
                    },
                ),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "save_images"
    CATEGORY = "SaveImageWithMetaDataUniversal"
    DESCRIPTION = (
        "Save images with extensive metadata support, including prompts, model info, and custom fields. "
        "Supports both automated metadata field detection and user-defined metadata rules."
    )
    OUTPUT_NODE = True

    pattern_format = re.compile(r"(%[^%]+%)")

    def save_images(
        self,
        images,
        filename_prefix="ComfyUI",
        sampler_selection_method=SAMPLER_SELECTION_METHOD[0],
        sampler_selection_node_id=0,
        file_format="png",
        model_hash_log="none",
        lossless_webp=True,
        quality=100,
        save_workflow_json=False,
        add_counter_to_filename=True,
        civitai_sampler=False,
        max_jpeg_exif_kb=60,
        extra_metadata={},
        prompt=None,
        extra_pnginfo=None,
        save_workflow_image=True,
        include_lora_summary=True,
        guidance_as_cfg=False,
        suppress_missing_class_log=False,
    ):
        """Save images to disk with embedded metadata.

        This is the main execution method for the node. It processes each image,
        generates the metadata, formats the filename, and saves the image in the
        specified format. It also handles the logic for JPEG EXIF size limits and
        fallback mechanisms.

        Args:
            images (torch.Tensor): A batch of images to be saved.
            filename_prefix (str, optional): The prefix for the output filename,
                which can contain tokens such as `%seed%` or
                `%date:yy-MM-dd%`. Defaults to "ComfyUI".
            sampler_selection_method (str, optional): The method to select the
                sampler node. Defaults to the first method in `SAMPLER_SELECTION_METHOD`.
            sampler_selection_node_id (int, optional): The ID of the sampler node
                to use when the selection method is "By node ID". Defaults to 0.
            file_format (str, optional): The output file format. Defaults to "png".
            model_hash_log (str, optional): The logging level for model hashing.
                Defaults to "none".
            lossless_webp (bool, optional): Whether to use lossless compression
                for WebP images. Defaults to True.
            quality (int, optional): The quality for lossy formats (JPEG/WebP).
                Defaults to 100.
            save_workflow_json (bool, optional): Whether to save the workflow as a
                separate JSON file. Defaults to False.
            add_counter_to_filename (bool, optional): Whether to add a counter
                to the filename to prevent overwrites. Defaults to True.
            civitai_sampler (bool, optional): Whether to add Civitai-compatible
                sampler information. Defaults to False.
            max_jpeg_exif_kb (int, optional): The maximum size of the EXIF data
                in kilobytes for JPEGs. Defaults to 60.
            extra_metadata (dict, optional): Additional metadata to be included.
                Defaults to {}.
            prompt (dict, optional): The workflow prompt. Injected by ComfyUI.
                Defaults to None.
            extra_pnginfo (dict, optional): Additional PNG info. Injected by
                ComfyUI. Defaults to None.
            save_workflow_image (bool, optional): Whether to save the workflow
                data within the image metadata. Defaults to True.
            include_lora_summary (bool, optional): Whether to include a summary
                of LoRAs in the metadata. Defaults to True.
            guidance_as_cfg (bool, optional): Whether to treat guidance as CFG
                scale. Defaults to False.
            suppress_missing_class_log (bool, optional): Whether to suppress
                warnings about missing node classes. Defaults to False.

        Returns:
            dict: A dictionary containing the UI data and the result, which
                includes the original images for passthrough.
        """
        # Refresh definitions each run with smarter merge order. We pass a set
        # of classes seen from the SaveImage node back through the graph so the
        # loader can decide if user JSON is needed or defaults+ext suffice.
        try:
            trace_tree_for_loader = Trace.trace(hook.current_save_image_node_id, hook.current_prompt)
            required_classes = {cls for (_, cls) in trace_tree_for_loader.values()}
        except (KeyError, AttributeError, TypeError, ValueError):
            required_classes = None
        # Merge any globally forced include classes provided by MetadataRuleScanner
        if FORCED_INCLUDE_CLASSES:
            if required_classes is None:
                required_classes = set()
            required_classes.update(FORCED_INCLUDE_CLASSES)
        # Defer to node module export so tests can monkeypatch node.load_user_definitions
        from . import node as _node  # local import to avoid circular at module load

        _node.load_user_definitions(required_classes, suppress_missing_log=suppress_missing_class_log)
        _maybe_warn_outdated_rules()
        # Ensure piexif references are patched via node module during tests
        piexif = _node.piexif  # noqa: F841 - used implicitly by subsequent code references
        # Apply unified hash logging preference
        try:
            from ..defs import formatters as _formatters_mod

            # Reinitialize hash logger only when the mode actually changes
            try:
                new_mode = (model_hash_log or "none").lower()
            except (AttributeError, TypeError, ValueError):
                new_mode = "none"
            try:
                current_mode = getattr(_formatters_mod, "HASH_LOG_MODE", "none")
            except (AttributeError, TypeError):
                current_mode = "none"
            if new_mode != current_mode and hasattr(_formatters_mod, "set_hash_log_mode"):
                _formatters_mod.set_hash_log_mode(new_mode)  # resets internal init flag intentionally
            # Proactively ensure logger is initialized when mode isn't none
            if new_mode != "none" and hasattr(_formatters_mod, "_ensure_logger"):
                try:
                    _formatters_mod._ensure_logger()
                except (RuntimeError, AttributeError):
                    # Logger initialization is non-critical; safe to ignore errors during fallback.
                    pass
        except (ImportError, AttributeError):  # pragma: no cover
            pass
        if _DEBUG_VERBOSE:
            logger.info(
                cstr("[Metadata Loader] Using Captures File with %d entries").msg,
                len(CAPTURE_FIELD_LIST),
            )
            logger.info(
                cstr("[Metadata Loader] Using Samplers File with %d entries").msg,
                len(SAMPLERS),
            )
        pnginfo_dict_src = self.gen_pnginfo(sampler_selection_method, sampler_selection_node_id, civitai_sampler)
        for k, v in extra_metadata.items():
            if k and v:
                pnginfo_dict_src[k] = v.replace(",", "/")

        ui_entries: list[dict[str, str]] = []
        self._last_fallback_stages.clear()
        for index, image in enumerate(images):
            # Support both torch tensors (with .cpu()) and raw numpy arrays in test mode.
            try:
                if hasattr(image, "cpu"):
                    arr = image.cpu().numpy()
                else:  # Already numpy or list-like
                    arr = getattr(image, "numpy", lambda: image)()
            except (AttributeError, TypeError, ValueError):  # fallback last resort
                arr = image
            scaled_pixels = 255.0 * arr
            img = Image.fromarray(np.clip(scaled_pixels, 0, 255).astype(np.uint8))

            pnginfo_dict = pnginfo_dict_src.copy()
            if len(images) >= 2:
                pnginfo_dict["Batch index"] = index
                pnginfo_dict["Batch size"] = len(images)

            metadata = None
            parameters = ""
            if not args.disable_metadata:
                metadata = PngInfo()
                parameters = Capture.gen_parameters_str(
                    pnginfo_dict,
                    include_lora_summary=include_lora_summary,
                    guidance_as_cfg=guidance_as_cfg,
                )
                if pnginfo_dict:
                    metadata.add_text("parameters", parameters)
                if prompt is not None and save_workflow_image:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        if not save_workflow_image and x == "workflow":
                            continue
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            filename_prefix = self.format_filename(filename_prefix, pnginfo_dict)
            output_path = os.path.join(self.output_dir, filename_prefix)
            if not os.path.exists(os.path.dirname(output_path)):
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            # Derive width/height from the actual PIL image (robust to input array layout)
            width, height = img.width, img.height
            save_path_info = folder_paths.get_save_image_path(filename_prefix, self.output_dir, width, height)
            # Support both legacy (4-tuple) and extended (5-tuple) return signatures
            if len(save_path_info) == 5:
                full_output_folder, filename, counter, subfolder, filename_prefix = save_path_info
            elif len(save_path_info) == 4:
                full_output_folder, filename, counter, subfolder = save_path_info
            else:
                # Fallback: minimal construction
                full_output_folder = self.output_dir
                filename = filename_prefix
                counter = 0
                subfolder = ""
            base_filename = filename
            if add_counter_to_filename:
                base_filename += f"_{counter:05}_"
            output_filename = base_filename + "." + file_format
            file_path = os.path.join(full_output_folder, output_filename)

            if file_format == "png":
                # PNG: embed via PNGInfo
                img.save(
                    file_path,
                    pnginfo=metadata,
                    compress_level=self.compress_level,
                )
            else:
                # Build EXIF/comment for JPEG & WebP up-front (avoid two-pass insert for JPEG reliability)
                exif_bytes = None
                fallback_stage = "none"
                try:
                    zeroth_ifd = {}
                    exif_ifd = {}
                    if save_workflow_image:
                        if prompt is not None:
                            zeroth_ifd[piexif.ImageIFD.Model] = (
                                f"prompt:{json.dumps(prompt, separators=(',', ':'))}".encode()
                            )
                        if extra_pnginfo is not None:
                            # Walk backwards from the Make tag so successive extra_pnginfo keys land in unused slots.
                            for tag_offset, (k, v) in enumerate(extra_pnginfo.items()):
                                zeroth_ifd[piexif.ImageIFD.Make - tag_offset] = (
                                    f"{k}:{json.dumps(v, separators=(',', ':'))}".encode()
                                )
                    if parameters:
                        exif_ifd[piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(
                            parameters,
                            encoding="unicode",
                        )
                    if zeroth_ifd or exif_ifd:
                        exif_dict = {"0th": zeroth_ifd, "Exif": exif_ifd}
                        exif_bytes = piexif.dump(exif_dict)
                except (KeyError, ValueError, OSError, TypeError) as e:
                    logger.warning("Failed preparing EXIF for %s: %s", file_format, e)

                save_kwargs = {
                    "optimize": True,
                    "quality": quality,
                }
                if file_format == "webp":  # WebP only: allow lossless flag
                    save_kwargs["lossless"] = lossless_webp
                if exif_bytes is not None and file_format in {"jpeg", "jpg"}:
                    # Guard against oversized EXIF.
                    # Two limits:
                    # 1. User-configurable logical limit (max_jpeg_exif_kb / env hard max) to keep files reasonable.
                    # 2. JPEG segment technical limit (~64KB single APP1) enforced by Pillow.
                    try:
                        segment_limit = int(
                            os.environ.get("METADATA_JPEG_EXIF_SEGMENT_LIMIT", "65500")
                        )  # soft technical ceiling
                    except Exception:
                        segment_limit = 65500
                    # Clamp segment limit to sane range (50KB .. 65533)
                    if segment_limit < 50000:
                        segment_limit = 50000
                    elif segment_limit > 65533:
                        segment_limit = 65533
                    try:
                        user_limit = int(max_jpeg_exif_kb)
                    except Exception:
                        user_limit = 60
                    # Clamp user input to sane bounds with optional env override.
                    # Default hard ceiling stays at 256KB to preserve broad decoder compatibility.
                    # Power users can raise (e.g. 512, 768) via METADATA_JPEG_EXIF_HARD_MAX_KB for experimentation.
                    try:
                        hard_max_env = int(os.environ.get("METADATA_JPEG_EXIF_HARD_MAX_KB", "256"))
                    except Exception:
                        hard_max_env = 256
                    # Enforce an absolute safety cap to avoid pathological multi-MB EXIF blocks
                    if hard_max_env < 64:
                        # Prevent users from accidentally lowering below a reasonable experimental range
                        hard_max_env = 64
                    elif hard_max_env > 2048:
                        # 2MB absolute ceiling (already extreme for EXIF) to avoid memory abuse
                        hard_max_env = 2048
                    if user_limit < 4:
                        user_limit = 4
                    elif user_limit > hard_max_env:
                        user_limit = hard_max_env
                    max_exif = user_limit * 1024
                    exif_size = len(exif_bytes)
                    if exif_size > max_exif or exif_size > segment_limit:
                        if len(exif_bytes) > segment_limit:
                            logger.info(
                                "[SaveImageWithMetaData] EXIF size %d exceeds segment limit %d; applying fallback",
                                exif_size,
                                segment_limit,
                            )
                        # Stage 1 fallback: parameters-only EXIF (reduced-exif)
                        try:
                            minimal_exif_full = None
                            if parameters:
                                uc_full = piexif.helper.UserComment.dump(parameters, encoding="unicode")
                                minimal_exif_full = piexif.dump(
                                    {
                                        "0th": {},
                                        "Exif": {piexif.ExifIFD.UserComment: uc_full},
                                    }
                                )
                            if minimal_exif_full and len(minimal_exif_full) <= max_exif:
                                save_kwargs["exif"] = minimal_exif_full
                                fallback_stage = "reduced-exif"
                            else:
                                # Stage 2 fallback: trimmed parameter string (minimal)
                                trimmed_parameters = (
                                    self._build_minimal_parameters(parameters) if parameters else parameters
                                )
                                if trimmed_parameters and trimmed_parameters != parameters:
                                    uc_trim = piexif.helper.UserComment.dump(trimmed_parameters, encoding="unicode")
                                    minimal_exif_trim = piexif.dump(
                                        {
                                            "0th": {},
                                            "Exif": {piexif.ExifIFD.UserComment: uc_trim},
                                        }
                                    )
                                    if len(minimal_exif_trim) <= max_exif:
                                        parameters = trimmed_parameters
                                        save_kwargs["exif"] = minimal_exif_trim
                                        fallback_stage = "minimal"
                                    else:
                                        # Final fallback: COM marker with trimmed parameters
                                        parameters = trimmed_parameters
                                        save_kwargs.pop("exif", None)
                                        exif_bytes = None
                                        fallback_stage = "com-marker"
                                else:
                                    # No trimming helped, go straight to COM marker
                                    save_kwargs.pop("exif", None)
                                    exif_bytes = None
                                    fallback_stage = "com-marker"
                        except (OSError, ValueError, KeyError, TypeError) as e:
                            logger.warning(
                                "[SaveImageWithMetaData] Failed fallback handling for oversized EXIF (%d bytes): %s",
                                len(exif_bytes),
                                e,
                            )
                            save_kwargs.pop("exif", None)
                            exif_bytes = None
                            fallback_stage = "com-marker"
                    else:
                        save_kwargs["exif"] = exif_bytes

                # Attempt initial save; catch Pillow EXIF size error and retry with fallback.
                try:
                    img.save(file_path, **save_kwargs)
                    if file_format in {"jpeg", "jpg"} and _DEBUG_VERBOSE:
                        logger.debug(
                            cstr("[SaveImageWithMetaData] JPEG save EXIF=%s size=%s fallback=%s").msg,
                            "yes" if "exif" in save_kwargs else "no",
                            exif_size if "exif_size" in locals() else 0,
                            fallback_stage,
                        )
                except ValueError as e:
                    if "EXIF data is too long" in str(e) and file_format in {"jpeg", "jpg"} and "exif" in save_kwargs:
                        logger.warning(
                            "[SaveImageWithMetaData] Pillow rejected EXIF (%s). Retrying with COM marker fallback.",
                            e,
                        )
                        # Drop EXIF and force COM marker path; mark fallback if not already set.
                        save_kwargs.pop("exif", None)
                        if fallback_stage == "none":
                            fallback_stage = "reduced-exif"
                        # Retry minimal save (no EXIF) – parameters will be written via COM path below
                        img.save(file_path, optimize=True, quality=quality)
                    else:
                        raise

                # JPEG COM marker fallback if EXIF removed due to size
                if file_format in {"jpeg", "jpg"} and parameters and ("exif" not in save_kwargs):
                    try:
                        # Append a COM marker manually (Pillow lacks direct API; reopen & resave with info)
                        # Append fallback stage indicator to parameters line if triggered
                        if fallback_stage != "none" and "Metadata Fallback:" not in parameters:
                            if parameters.endswith("\n"):
                                parameters = parameters.rstrip("\n")
                            if ", Metadata Fallback:" not in parameters:
                                parameters = parameters + f", Metadata Fallback: {fallback_stage}"
                        with Image.open(file_path) as im2:
                            im2.save(
                                file_path,
                                optimize=True,
                                quality=quality,
                                comment=parameters.encode("utf-8", "ignore")[:60000],  # ensure within marker limits
                            )
                    except (OSError, ValueError) as e:
                        logger.warning(
                            "[SaveImageWithMetaData] Failed to write JPEG COM marker fallback: %s",
                            e,
                        )
                elif (
                    file_format in {"jpeg", "jpg"}
                    and ("exif" in save_kwargs)
                    and fallback_stage in {"reduced-exif", "minimal"}
                    and parameters
                ):
                    # EXIF present but we still need to encode fallback stage; rebuild tiny EXIF
                    # with appended tag if not already noted
                    try:
                        if "Metadata Fallback:" not in parameters:
                            if parameters.endswith("\n"):
                                parameters = parameters.rstrip("\n")
                            parameters = parameters + f", Metadata Fallback: {fallback_stage}"
                        uc_final = piexif.helper.UserComment.dump(parameters, encoding="unicode")
                        final_exif = piexif.dump({"0th": {}, "Exif": {piexif.ExifIFD.UserComment: uc_final}})
                        piexif.insert(final_exif, file_path)
                    except (OSError, ValueError, KeyError, TypeError):
                        # Non-fatal: failed to write fallback EXIF metadata. Image is still saved.
                        pass
                # Record stage for this image
                self._last_fallback_stages.append(fallback_stage)

                # For WebP we cannot pass EXIF directly in older Pillow versions; fall back to piexif.insert if needed
                if exif_bytes is not None and file_format == "webp":
                    try:
                        piexif.insert(exif_bytes, file_path)
                    except (OSError, ValueError, RuntimeError):
                        # Non-fatal; WebP EXIF not critical
                        pass

            if save_workflow_json:
                file_path_workflow = os.path.join(full_output_folder, f"{base_filename}.json")
                with open(file_path_workflow, "w", encoding="utf-8") as f:
                    json.dump(extra_pnginfo["workflow"], f)

            ui_entries.append({"filename": output_filename, "subfolder": subfolder, "type": self.type})
            try:
                counter = int(counter) + 1
            except (TypeError, ValueError):
                counter = 1

        # Pass through original tensor batch as output so downstream nodes can reuse the images
        return {"ui": {"images": ui_entries}, "result": (images,)}

    @staticmethod
    def _build_minimal_parameters(full_parameters: str) -> str:
        """Generate a trimmed parameter string for JPEG fallback.

        This method creates a minimal version of the parameter string to be used
        when the full metadata exceeds the size limits for JPEG EXIF data. It
        preserves the most critical information while dropping less essential
        fields.
        Preserves: Prompt header lines, Negative prompt, and a reduced parameter key set:
            Steps, Sampler, CFG scale, Seed, Model, Model hash, VAE, VAE hash,
            All Lora_* fields, Hashes, Metadata generator version.

        Drops: Weight dtype, Size, Batch index/size, shifts, CLIP models, embeddings, extra custom keys.

        Args:
            full_parameters (str): The complete parameter string.

        Returns:
            str: The trimmed, minimal parameter string.
        """
        if not full_parameters:
            return full_parameters
        lines = full_parameters.strip().splitlines()
        if not lines:
            return full_parameters
        # Collect header (prompt + negative prompt) until we reach a line containing 'Steps:' token
        # or a line with multiple comma-separated fields
        header = []
        tail_lines = []
        for i, line in enumerate(lines):
            if i < len(lines) - 1:  # header lines except last
                if line.startswith("Negative prompt:") or not (", " in line and ":" in line):
                    header.append(line)
                    continue
            # Parameter line (could be multi-line in test mode)
            tail_lines = lines[i:]
            break
        if not tail_lines:
            # Only header present
            return "\n".join(header) + "\n"
        # Merge tail lines back (production mode usually single)
        param_blob = " ".join(tail_lines)
        parts = [p.strip() for p in param_blob.split(",") if ":" in p]
        allow_prefixes = ("Lora_",)
        allow_keys = {
            "Steps",
            "Sampler",
            "CFG scale",
            "Seed",
            "Model",
            "Model hash",
            "VAE",
            "VAE hash",
            "Hashes",
            "Metadata generator version",
        }
        kept_segments = []
        for seg in parts:
            key = seg.split(":", 1)[0].strip()
            if key in allow_keys or any(key.startswith(pref) for pref in allow_prefixes):
                kept_segments.append(seg)
        # Reconstruct
        minimal_line = ", ".join(kept_segments)
        out_lines = header + [minimal_line]
        return "\n".join(line for line in out_lines if line) + ("\n" if out_lines else "")

    @classmethod
    def gen_pnginfo(cls, sampler_selection_method, sampler_selection_node_id, save_civitai_sampler):
        """Generate the PNG info dictionary from the workflow.

        This method traces the workflow graph to identify the relevant sampler
        and other nodes, then captures their input values to generate a
        dictionary of metadata.

        Args:
            sampler_selection_method (str): The method for selecting the sampler node.
            sampler_selection_node_id (int): The ID of the sampler node to use.
            save_civitai_sampler (bool): Whether to include Civitai-compatible
                sampler info.

        Returns:
            dict: A dictionary containing the captured metadata.
        """
        # get all node inputs
        inputs = Capture.get_inputs()

        # get sampler node before this node
        trace_tree_from_this_node = Trace.trace(hook.current_save_image_node_id, hook.current_prompt)
        inputs_before_this_node = Trace.filter_inputs_by_trace_tree(inputs, trace_tree_from_this_node)
        sampler_node_id = Trace.find_sampler_node_id(
            trace_tree_from_this_node,
            sampler_selection_method,
            sampler_selection_node_id,
        )

        if sampler_node_id == -1:
            # No sampler node found along the trace. Fall back to using inputs
            # available before this SaveImage node to still emit partial metadata
            # (model, vae, prompts, size, etc.). This prevents fully empty A111
            # metadata and when exotic samplers are used or the sampler list is incomplete
            # and prevents a fatal error if no sampler node is found.
            logger.warning(
                "[SaveImageWithMetaData] Sampler node not found; falling back to partial metadata generation."
            )
            return Capture.gen_pnginfo_dict(
                inputs_before_this_node,  # treat inputs before this node as the sampler context
                inputs_before_this_node,
                save_civitai_sampler,
            )

        # get inputs before sampler node
        trace_tree_from_sampler_node = Trace.trace(sampler_node_id, hook.current_prompt)
        inputs_before_sampler_node = Trace.filter_inputs_by_trace_tree(inputs, trace_tree_from_sampler_node)

        # generate PNGInfo from inputs
        pnginfo_dict = Capture.gen_pnginfo_dict(
            inputs_before_sampler_node,
            inputs_before_this_node,
            save_civitai_sampler,
        )
        return pnginfo_dict

    @classmethod
    def format_filename(cls, filename, pnginfo_dict):
        """Format the output filename using tokens from the metadata.

        This method replaces tokens such as `%seed%`, `%width%`, and `%date%`
        in the filename prefix with their corresponding values from the
        `pnginfo_dict`.

        Args:
            filename (str): The filename prefix containing tokens.
            pnginfo_dict (dict): The dictionary of metadata.

        Returns:
            str: The formatted filename.
        """
        result = re.findall(cls.pattern_format, filename)
        for segment in result:
            parts = segment.replace("%", "").split(":")
            key = parts[0]
            if key == "seed":
                filename = filename.replace(segment, str(pnginfo_dict.get("Seed", "")))
            elif key == "width":
                w = pnginfo_dict.get("Size", "x").split("x")[0]
                filename = filename.replace(segment, str(w))
            elif key == "height":
                w = pnginfo_dict.get("Size", "x").split("x")[1]
                filename = filename.replace(segment, str(w))
            elif key == "pprompt":
                prompt = pnginfo_dict.get("Positive prompt", "").replace("\n", " ")
                if len(parts) >= 2:
                    length = int(parts[1])
                    prompt = prompt[:length]
                filename = filename.replace(segment, prompt.strip())
            elif key == "nprompt":
                prompt = pnginfo_dict.get("Negative prompt", "").replace("\n", " ")
                if len(parts) >= 2:
                    length = int(parts[1])
                    prompt = prompt[:length]
                filename = filename.replace(segment, prompt.strip())
            elif key == "model":
                model = pnginfo_dict.get("Model", "")
                model = os.path.splitext(os.path.basename(model))[0]
                if len(parts) >= 2:
                    length = int(parts[1])
                    model = model[:length]
                filename = filename.replace(segment, model)
            elif key == "date":
                now = datetime.now()
                date_table = {
                    "yyyy": now.year,
                    "MM": now.month,
                    "dd": now.day,
                    "hh": now.hour,
                    "mm": now.minute,
                    "ss": now.second,
                }
                if len(parts) >= 2:
                    date_format = parts[1]
                    for k, v in date_table.items():
                        date_format = date_format.replace(k, str(v).zfill(len(k)))
                    filename = filename.replace(segment, date_format)
                else:
                    date_format = "yyyyMMddhhmmss"
                    for k, v in date_table.items():
                        date_format = date_format.replace(k, str(v).zfill(len(k)))
                    filename = filename.replace(segment, date_format)

        return filename
