import json
import logging
import os
import re
from datetime import datetime

import folder_paths
import nodes
import numpy as np
try:  # Pillow EXIF helper (optional in test env)
    import piexif  # type: ignore
    import piexif.helper  # type: ignore
except Exception:  # noqa: BLE001
    class _PieExifStub:  # minimal stub for tests
        class ExifIFD:
            UserComment = 0x9286

        class ImageIFD:
            Model = 0x0110
            Make = 0x010F

        @staticmethod
        def dump(_mapping):
            # Inflate size to ~10KB so small max_jpeg_exif_kb thresholds cause fallback in tests
            base = b"stub"
            if len(base) < 10 * 1024:
                base = base * ((10 * 1024 // len(base)) + 1)
            return base[:10 * 1024]

        @staticmethod
        def insert(_exif_bytes, _path):
            return None

        class HelperStub:  # type: ignore
            class UserComment:
                @staticmethod
                def dump(value, encoding="unicode"):
                    return value.encode("utf-8") if isinstance(value, str) else b""
        helper = HelperStub  # expose attribute name piexif.helper

    piexif = _PieExifStub()  # type: ignore
try:  # Comfy runtime provides this; tests may not
    from comfy.cli_args import args  # type: ignore
except Exception:  # noqa: BLE001
    class _ArgsStub:
        disable_metadata = False

    args = _ArgsStub()  # type: ignore
from PIL import Image
from PIL.PngImagePlugin import PngInfo

try:  # Normal runtime
    from .. import hook  # type: ignore
except Exception:  # noqa: BLE001 - circular or missing in isolated test
    class _HookStub:  # minimal attributes used
        current_save_image_node_id = 0
        current_prompt = {}

    hook = _HookStub()  # type: ignore
from ..capture import Capture

# from ..utils.deserialize import format_config
from ..defs import load_user_definitions
from ..defs.captures import CAPTURE_FIELD_LIST
from ..defs.combo import SAMPLER_SELECTION_METHOD
from ..defs.meta import MetaField
from ..defs.samplers import SAMPLERS
from ..trace import Trace

#
# SaveImageWithMetaData: main node class to save images.
#
# refer. https://github.com/comfyanonymous/ComfyUI/blob/38b7ac6e269e6ecc5bdd6fefdfb2fb1185b09c9d/nodes.py#L1411
logger = logging.getLogger(__name__)
_DEBUG_VERBOSE = os.environ.get("METADATA_DEBUG", "0") not in (
    "0",
    "false",
    "False",
    None,
    "",
)


class SaveImageWithMetaDataUniversal:
    SAVE_FILE_FORMATS = ["png", "jpeg", "webp"]

    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4
        # Track per-image fallback stages for tests / diagnostics
        self._last_fallback_stages: list[str] = []

    @classmethod
    def INPUT_TYPES(s):  # noqa: N802,N804 (ComfyUI API requires this signature)
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": (
                    "STRING",
                    {
                        "default": "ComfyUI",
                        "tooltip": "You can use %seed%, %width%, %height%, %pprompt%, %nprompt%, %model%, %date% in the filename. Date can accept any variety of the yyyyMMddhhmmss format, e.g. %date:yy-MM-dd%.",
                    },
                ),
                "sampler_selection_method": (
                    SAMPLER_SELECTION_METHOD,
                    {
                        "tooltip": "How to choose which earlier sampler node's settings to record: farthest, nearest, or by node id (see sampler_selection_node_id).",
                    },
                ),
                "sampler_selection_node_id": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 999999999,
                        "step": 1,
                        "tooltip": "When method is 'By node ID', this specifies which sampler node to treat as authoritative for Steps/CFG/etc.",
                    },
                ),
                "file_format": (
                    s.SAVE_FILE_FORMATS,
                    {
                        "tooltip": "Image format for output. PNG retains full metadata; JPEG/WebP may strip or re-encode some fields.",
                    },
                ),
            },
            "optional": {
                "lossless_webp": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "If using WebP, toggles lossless mode (ignores quality slider).",
                    },
                ),
                "quality": (
                    "INT",
                    {
                        "default": 100,
                        "min": 1,
                        "max": 100,
                        "tooltip": "Quality for lossy formats (JPEG/WebP lossy). 100 = best quality, larger files.",
                    },
                ),
                "max_jpeg_exif_kb": (
                    "INT",
                    {
                        "default": 60,
                        "min": 4,
                        "max": 256,
                        "step": 1,
                        "tooltip": "Maximum EXIF size (KB) to embed in JPEG. If exceeded, falls back to parameters-only EXIF or COM marker.",
                    },
                ),
                "save_workflow_json": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Save the workflow as a JSON file alongside the image.",
                    },
                ),
                "add_counter_to_filename": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Automatically append an incrementing counter to avoid overwriting existing files with the same prefix.",
                    },
                ),
                "civitai_sampler": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "Add a Civitai-compatible sampler notation (if enabled) for better import fidelity on Civitai.",
                    },
                ),
                "guidance_as_cfg": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "When enabled, record 'Guidance' value under 'CFG scale' and suppress separate Guidance field. Makes guidance with models like FLUX Civitai-compatible (if enabled).",
                    },
                ),
                "extra_metadata": (
                    "EXTRA_METADATA",
                    {"tooltip": "Additional metadata key-value pairs from the Create Extra MetaData node to include in the saved image."},
                ),
                "save_workflow_image": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "If disabled, the workflow data will not be saved in the image metadata.",
                    },
                ),
                "include_lora_summary": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Include a compact aggregated LoRAs summary line (set False to list only individual Lora_X entries).",
                    },
                ),
                "force_include_node_class": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Comma separated list of node class names to force include in rule scanning even if heuristics would filter them.",
                    },
                ),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "save_images"
    CATEGORY = "SaveImageWithMetaDataUniversal"
    Description = "Save images with extensive metadata support, including prompts, model info, and custom fields. Support for both automated metadata field detection and user-defined metadata rules."
    OUTPUT_NODE = True

    pattern_format = re.compile(r"(%[^%]+%)")

    def save_images(
        self,
        images,
        filename_prefix="ComfyUI",
        sampler_selection_method=SAMPLER_SELECTION_METHOD[0],
        sampler_selection_node_id=0,
        file_format="png",
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
        force_include_node_class="",
    ):
        """Persist images to disk with rich, optionally extended metadata.

        Args:
            images: Batch tensor list from upstream nodes.
            filename_prefix: Template (supports tokens like %seed%, %width%).
            sampler_selection_method: Strategy for sampler field selection.
            sampler_selection_node_id: Node id considered for sampler extraction.
            file_format: Output image format ('png', 'jpeg', 'webp').
            lossless_webp: Whether to use lossless mode for WEBP.
            quality: Quality (1-100) for lossy formats.
            save_workflow_json: Emit workflow JSON alongside saved image.
            add_counter_to_filename: Append numeric counter to avoid collisions.
            civitai_sampler: Emit Civitai compatible sampler key if True.
            max_jpeg_exif_kb: Upper bound for JPEG EXIF size before fallback logic triggers.
            extra_metadata: Additional user-provided key/value entries.
            prompt: Full workflow prompt graph (JSON serializable) for embedding.
            extra_pnginfo: Extra PNG info dictionary from upstream nodes.
            save_workflow_image: If False, omit workflow from embedded metadata.
            include_lora_summary: Override aggregated LoRA summary line inclusion.
            force_include_node_class: Comma separated node class names to force include during rule scanning.

        Returns:
            Tuple containing the original `images` tensor batch (ComfyUI node contract).
        """
        # Refresh definitions each run with smarter merge order. We pass a set
        # of classes seen from the SaveImage node back through the graph so the
        # loader can decide if user JSON is needed or defaults+ext suffice.
        try:
            trace_tree_for_loader = Trace.trace(hook.current_save_image_node_id, hook.current_prompt)
            required_classes = {cls for (_, cls) in trace_tree_for_loader.values()}
        except Exception:
            required_classes = None
        # Force include classes from user input
        if force_include_node_class:
            forced = {c.strip() for c in force_include_node_class.split(",") if c.strip()}
            if forced:
                if required_classes is None:
                    required_classes = set()
                required_classes.update(forced)
        load_user_definitions(required_classes)
        # print(" ".join([cstr("[Metadata Loader] Using Captures File with").msg_o, cstr(f"{len(CAPTURE_FIELD_LIST)}").VIOLET, cstr("for save_images:").msg_o, cstr(format_config(CAPTURE_FIELD_LIST)).end]))
        # print(" ".join([cstr("[Metadata Loader] Using Samplers File with"), cstr(f"{len(SAMPLERS)}").VIOLET, cstr("for save_images:").msg_o, cstr(format_config(SAMPLERS)).end]))
        if _DEBUG_VERBOSE:
            logger.info(
                "[Metadata Loader] Using Captures File with %d entries",
                len(CAPTURE_FIELD_LIST),
            )
            logger.info("[Metadata Loader] Using Samplers File with %d entries", len(SAMPLERS))
        pnginfo_dict_src = self.gen_pnginfo(sampler_selection_method, sampler_selection_node_id, civitai_sampler)
        for k, v in extra_metadata.items():
            if k and v:
                pnginfo_dict_src[k] = v.replace(",", "/")

        results = list()
        self._last_fallback_stages.clear()
        for index, image in enumerate(images):
            # Support both torch tensors (with .cpu()) and raw numpy arrays in test mode.
            try:
                if hasattr(image, "cpu"):
                    arr = image.cpu().numpy()
                else:  # Already numpy or list-like
                    arr = getattr(image, "numpy", lambda: image)()
            except Exception:  # fallback last resort
                arr = image
            i = 255.0 * arr
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))

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
            file = base_filename + "." + file_format
            file_path = os.path.join(full_output_folder, file)

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
                            zeroth_ifd[piexif.ImageIFD.Model] = f"prompt:{json.dumps(prompt, separators=(',', ':'))}".encode()
                        if extra_pnginfo is not None:
                            for i, (k, v) in enumerate(extra_pnginfo.items()):
                                zeroth_ifd[piexif.ImageIFD.Make - i] = f"{k}:{json.dumps(v, separators=(',', ':'))}".encode()
                    if parameters:
                        exif_ifd[piexif.ExifIFD.UserComment] = piexif.helper.UserComment.dump(parameters, encoding="unicode")
                    if zeroth_ifd or exif_ifd:
                        exif_dict = {"0th": zeroth_ifd, "Exif": exif_ifd}
                        exif_bytes = piexif.dump(exif_dict)
                except Exception as e:
                    logger.warning("Failed preparing EXIF for %s: %s", file_format, e)

                save_kwargs = {
                    "optimize": True,
                    "quality": quality,
                }
                if file_format == "webp":  # WebP only: allow lossless flag
                    save_kwargs["lossless"] = lossless_webp
                if exif_bytes is not None and file_format in {"jpeg", "jpg"}:
                    # Guard against oversized EXIF (JPEG limit ~64KB). If too large, fallback to parameters-only EXIF.
                    try:
                        user_limit = int(max_jpeg_exif_kb)
                    except Exception:
                        user_limit = 60
                    # Clamp user input to sane bounds (4KB .. 256KB)
                    if user_limit < 4:
                        user_limit = 4
                    elif user_limit > 256:
                        user_limit = 256
                    max_exif = user_limit * 1024
                    if len(exif_bytes) > max_exif:
                        # Stage 1 fallback: parameters-only EXIF (reduced-exif)
                        try:
                            minimal_exif_full = None
                            if parameters:
                                uc_full = piexif.helper.UserComment.dump(parameters, encoding="unicode")
                                minimal_exif_full = piexif.dump({"0th": {}, "Exif": {piexif.ExifIFD.UserComment: uc_full}})
                            if minimal_exif_full and len(minimal_exif_full) <= max_exif:
                                save_kwargs["exif"] = minimal_exif_full
                                fallback_stage = "reduced-exif"
                            else:
                                # Stage 2 fallback: trimmed parameter string (minimal)
                                trimmed_parameters = self._build_minimal_parameters(parameters) if parameters else parameters
                                if trimmed_parameters and trimmed_parameters != parameters:
                                    uc_trim = piexif.helper.UserComment.dump(trimmed_parameters, encoding="unicode")
                                    minimal_exif_trim = piexif.dump({"0th": {}, "Exif": {piexif.ExifIFD.UserComment: uc_trim}})
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
                        except Exception as e:
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

                img.save(file_path, **save_kwargs)

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
                    except Exception as e:
                        logger.warning(
                            "[SaveImageWithMetaData] Failed to write JPEG COM marker fallback: %s",
                            e,
                        )
                elif file_format in {"jpeg", "jpg"} and ("exif" in save_kwargs) and fallback_stage in {"reduced-exif", "minimal"} and parameters:
                    # EXIF present but we still need to encode fallback stage; rebuild tiny EXIF with appended tag if not already noted
                    try:
                        if "Metadata Fallback:" not in parameters:
                            if parameters.endswith("\n"):
                                parameters = parameters.rstrip("\n")
                            parameters = parameters + f", Metadata Fallback: {fallback_stage}"
                        uc_final = piexif.helper.UserComment.dump(parameters, encoding="unicode")
                        final_exif = piexif.dump({"0th": {}, "Exif": {piexif.ExifIFD.UserComment: uc_final}})
                        piexif.insert(final_exif, file_path)
                    except Exception:
                        pass
                # Record stage for this image
                self._last_fallback_stages.append(fallback_stage)

                # For WebP we cannot pass EXIF directly in older Pillow versions; fall back to piexif.insert if needed
                if exif_bytes is not None and file_format == "webp":
                    try:
                        piexif.insert(exif_bytes, file_path)
                    except Exception:
                        # Non-fatal; WebP EXIF not critical
                        pass

            if save_workflow_json:
                file_path_workflow = os.path.join(full_output_folder, f"{base_filename}.json")
                with open(file_path_workflow, "w", encoding="utf-8") as f:
                    json.dump(extra_pnginfo["workflow"], f)

            results.append({"filename": file, "subfolder": subfolder, "type": self.type})
            try:
                counter = int(counter) + 1
            except Exception:
                counter = 1

        # Pass through original tensor batch as output so downstream nodes can reuse the images
        return {"ui": {"images": results}, "result": (images,)}

    @staticmethod
    def _build_minimal_parameters(full_parameters: str) -> str:
        """Return a trimmed parameter string keeping only a minimal compatibility allowlist.

        Preserves: Prompt header lines, Negative prompt, and a reduced parameter key set:
            Steps, Sampler, CFG scale, Seed, Model, Model hash, VAE, VAE hash,
            All Lora_* fields, Hashes, Metadata generator version.

        Drops: Weight dtype, Size, Batch index/size, shifts, CLIP models, embeddings, extra custom keys.
        """
        if not full_parameters:
            return full_parameters
        lines = full_parameters.strip().splitlines()
        if not lines:
            return full_parameters
        # Collect header (prompt + negative prompt) until we reach a line containing 'Steps:' token or a line with multiple comma-separated fields
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
            logger.warning("[SaveImageWithMetaData] Sampler node not found; falling back to partial metadata generation.")
            return Capture.gen_pnginfo_dict(
                inputs_before_this_node,  # treat inputs before this node as the sampler context
                inputs_before_this_node,
                save_civitai_sampler,
            )

        # get inputs before sampler node
        trace_tree_from_sampler_node = Trace.trace(sampler_node_id, hook.current_prompt)
        inputs_before_sampler_node = Trace.filter_inputs_by_trace_tree(inputs, trace_tree_from_sampler_node)

        # generate PNGInfo from inputs
        pnginfo_dict = Capture.gen_pnginfo_dict(inputs_before_sampler_node, inputs_before_this_node, save_civitai_sampler)
        return pnginfo_dict

    @classmethod
    def format_filename(cls, filename, pnginfo_dict):
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


#
# CreateExtraMetaData: Create extra metadata key-value pairs for saved images.
#
class CreateExtraMetaDataUniversal:
    @classmethod
    def INPUT_TYPES(s):  # noqa: N802,N804
        return {
            "required": {
                "key1": ("STRING", {"default": "", "multiline": False}),
                "value1": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "key2": ("STRING", {"default": "", "multiline": False}),
                "value2": ("STRING", {"default": "", "multiline": False}),
                "key3": ("STRING", {"default": "", "multiline": False}),
                "value3": ("STRING", {"default": "", "multiline": False}),
                "key4": ("STRING", {"default": "", "multiline": False}),
                "value4": ("STRING", {"default": "", "multiline": False}),
                "extra_metadata": ("EXTRA_METADATA",),
            },
        }

    RETURN_TYPES = ("EXTRA_METADATA",)
    FUNCTION = "create_extra_metadata"
    CATEGORY = "SaveImageWithMetaDataUniversal"
    Description = "Manually create extra metadata key-value pairs to include in saved images. Keys and values should be strings. Commas in values will be replaced with slashes."

    def create_extra_metadata(
        self,
        extra_metadata={},
        key1="",
        value1="",
        key2="",
        value2="",
        key3="",
        value3="",
        key4="",
        value4="",
    ):
        extra_metadata.update(
            {
                key1: value1,
                key2: value2,
                key3: value3,
                key4: value4,
            }
        )
        return (extra_metadata,)


#
# ShowGeneratedUserRules: Display the contents of generated_user_rules.py
#
class ShowGeneratedUserRules:
    @classmethod
    def INPUT_TYPES(s):  # noqa: N802,N804
        return {"required": {}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("generated_user_rules.py",)
    FUNCTION = "show_rules"
    CATEGORY = "SaveImageWithMetaDataUniversal/rules"
    Description = "Display the contents of generated_user_rules.py for review or editing."

    def _rules_path(self) -> str:
        base_py = os.path.dirname(os.path.dirname(__file__))  # .../py
        return os.path.join(base_py, "defs", "ext", "generated_user_rules.py")

    def show_rules(self) -> tuple[str]:
        path = self._rules_path()
        if not os.path.exists(path):
            return ("",)
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            logger.warning("[Metadata Rules] I/O error reading %s: %s", path, e)
            return (f"Error reading generated_user_rules.py: {e}",)
        return (content,)


#
# SaveGeneratedUserRules: Save edited rules text back to generated_user_rules.py
#
class SaveGeneratedUserRules:
    @classmethod
    def INPUT_TYPES(s):  # noqa: N802,N804
        return {
            "required": {
                "rules_text": ("STRING", {"default": "", "multiline": True}),
                "append": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "If true, append new rules to existing file; if false, overwrite existing file.",
                    },
                ),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "save_rules"
    CATEGORY = "SaveImageWithMetaDataUniversal/rules"
    Description = "Save the edited rules text back to generated_user_rules.py, with syntax validation."

    def _rules_path(self) -> str:
        base_py = os.path.dirname(os.path.dirname(__file__))  # .../py
        return os.path.join(base_py, "defs", "ext", "generated_user_rules.py")

    def _validate_python(self, text: str) -> tuple[bool, str | None]:
        import ast

        try:
            ast.parse(text)
            return True, None
        except SyntaxError as e:
            return False, f"SyntaxError: {e.msg} at line {e.lineno}:{e.offset}"
        except (ValueError, TypeError) as e:  # unlikely for source text but explicit
            return False, f"Error: {e}"

    def _find_dict_span(self, text: str, name: str) -> tuple[int | None, int | None]:
        """Finds the span of the dict assigned to `name` (e.g., name = { ... }). Returns (start_idx, end_idx) of the braces, or (None, None)."""
        import re

        m = re.search(rf"\b{name}\s*=\s*\{{", text)
        if not m:
            return None, None
        start = m.end() - 1  # position of '{'
        depth = 0
        i = start
        in_str = False
        esc = False
        quote = ""
        while i < len(text):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == quote:
                    in_str = False
            else:
                if ch in ('"', "'"):
                    in_str = True
                    quote = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return start, i
            i += 1
        return None, None

    def _parse_top_level_entries(self, body: str) -> list[tuple[str, str]]:
        """Parse top-level entries of a dict body (without surrounding braces) into an ordered list of (key, value_text)."""
        entries = []
        i = 0
        n = len(body)
        while i < n:
            # skip whitespace and commas
            while i < n and body[i] in " \t\r\n,":
                i += 1
            if i >= n:
                break
            # expect key string starting with '"'
            if body[i] not in ('"', "'"):
                # not a standard quoted key; skip this char
                i += 1
                continue
            quote = body[i]
            i += 1
            key_start = i
            esc = False
            while i < n:
                ch = body[i]
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == quote:
                    break
                i += 1
            key = body[key_start:i]
            i += 1  # skip closing quote
            # skip whitespace to colon
            while i < n and body[i] in " \t\r\n":
                i += 1
            if i >= n or body[i] != ":":
                continue
            i += 1  # skip colon
            # skip whitespace before value
            while i < n and body[i] in " \t\r\n":
                i += 1
            # capture value until next comma at depth 0
            val_start = i
            depth = 0
            in_str = False
            esc = False
            str_q = ""
            while i < n:
                ch = body[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == str_q:
                        in_str = False
                else:
                    if ch in ('"', "'"):
                        in_str = True
                        str_q = ch
                    elif ch in "{[(":
                        depth += 1
                    elif ch in ")]}":
                        depth -= 1
                    elif ch == "," and depth == 0:
                        break
                i += 1
            val_end = i
            value_text = body[val_start:val_end].rstrip()
            entries.append((key, value_text))
            # skip comma
            if i < n and body[i] == ",":
                i += 1
        return entries

    def _rebuild_dict(self, name: str, existing_text: str, new_text: str) -> str:
        # Find spans
        es, ee = self._find_dict_span(existing_text, name)
        if es is None:
            # If dict not found in existing, but present in new, just return existing as-is with appended section
            ns, ne = self._find_dict_span(new_text, name)
            if ns is None:
                return existing_text  # nothing to do
            # Insert whole block from new
            block = new_text[ns : ne + 1]
            return existing_text + f"\n\n{name} = {block}\n"

        # Extract bodies
        e_body = existing_text[es + 1 : ee]
        nms = self._find_dict_span(new_text, name)
        if nms == (None, None):
            return existing_text  # no updates for this dict
        ns, ne = nms
        n_body = new_text[ns + 1 : ne]

        e_entries = self._parse_top_level_entries(e_body)
        n_entries = self._parse_top_level_entries(n_body)

        # Build maps for quick lookup
        e_map = {k: v for k, v in e_entries}
        order = [k for k, _ in e_entries]
        # Merge: update changed and add new
        for k, v in n_entries:
            nv_norm = v.strip()
            ev_norm = e_map.get(k, "").strip()
            if k in e_map:
                if nv_norm != ev_norm:
                    e_map[k] = v  # update
            else:
                e_map[k] = v
                order.append(k)

        # Reconstruct dict body with consistent formatting
        def indent_value(val):
            val = val.rstrip()
            lines = val.splitlines()
            if not lines:
                return val
            return "\n".join([lines[0]] + [("    " + ln) for ln in lines[1:]])

        new_body_lines = []
        for k in order:
            v = e_map[k]
            # ensure each entry ends with a comma; Python allows trailing comma
            entry_text = f'    "{k}": {indent_value(v)},'
            new_body_lines.append(entry_text)
        new_body = "\n" + "\n".join(new_body_lines) + "\n"

        # Rebuild file content
        return existing_text[:es] + "{" + new_body + "}" + existing_text[ee + 1 :]

    def save_rules(self, rules_text: str = "", append: bool = True) -> tuple[str]:
        path = self._rules_path()
        # Validate user text always
        ok, err = self._validate_python(rules_text)
        if not ok:
            return (f"Refused to write: provided text has errors. {err}",)

        if not append:
            # Overwrite entirely
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(rules_text)
            except OSError as e:
                logger.warning("[Metadata Rules] Overwrite failed %s: %s", path, e)
                return (f"Failed to overwrite {path}: {e}",)
            return (f"Overwritten {path}",)

        # Append/merge mode
        try:
            if not os.path.exists(path):
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(rules_text)
                except OSError as e:
                    logger.warning("[Metadata Rules] Create failed %s: %s", path, e)
                    return (f"Failed to create {path}: {e}",)
                return (f"Created {path}",)

            try:
                with open(path, encoding="utf-8") as f:
                    existing = f.read()
            except OSError as e:
                logger.warning("[Metadata Rules] Read existing failed %s: %s", path, e)
                return (f"Failed to read existing {path}: {e}",)

            merged = existing
            for dict_name in ("SAMPLERS", "CAPTURE_FIELD_LIST"):
                merged = self._rebuild_dict(dict_name, merged, rules_text)

            ok2, err2 = self._validate_python(merged)
            if not ok2:
                return (f"Merge aborted: merged content failed validation: {err2}",)

            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(merged)
            except OSError as e:
                logger.warning("[Metadata Rules] Write merged failed %s: %s", path, e)
                return (f"Failed to write merged {path}: {e}",)
            return (f"Merged updates into {path}",)
        except Exception as e:  # pragma: no cover - catch-all for unexpected logic errors
            logger.exception("[Metadata Rules] Unexpected merge failure for %s", path)
            return (f"Failed to merge into {path}: {e}",)


#
# --- Heuristic Definitions For MetadataRuleScanner ---
#
"""
HEURISTIC_RULES: List of dicts defining rules to identify metadata fields from node inputs. Used by MetadataRuleScanner to suggest metadata capture rules for nodes classes.

HEURISTIC_RULES supports: keywords, excluded_keywords, exact_only (True/False), required_context, required_class_keywords, required_class_regex, required_class_keyword_groups, excluded_class_keywords

keywords: tuple of keywords to match input field names (case-insensitive, partial match unless exact_only is True)

excluded_keywords: tuple of keywords that must NOT be present in input field names

exact_only: if True, only exact matches of keywords are considered

required_context: list of keywords that must be present in any input field name on the node (case-insensitive, partial match) to consider this rule applicable

required_class_keywords: list of keywords that must be present in the node class name (case-insensitive, partial match) to consider this rule applicable

required_class_regex: list of regex patterns that must match the node class name to consider this rule applicable

required_class_keyword_groups: dict with "groups" (list of keyword lists) and "mins" (list of minimum counts) specifying groups of keywords where at least the specified minimum number of keywords from each group must be present in the node class name (case-insensitive, partial match)

excluded_class_keywords: tuple of keywords that must NOT be present in the node class name (case-insensitive, partial match)

type: a string or list/tuple/set of strings denoting allowed ComfyUI input types (e.g., "FLOAT", "INT", "STRING"). If provided, only inputs whose declared type matches one of these are considered.

"fields" (output structure enhancement): For is_multi rules, the scanner now returns either a single "field_name" (if only one match) or a list of all matching input names under "fields". This avoids losing information when multiple similarly-patterned inputs exist (e.g., lora_1 .. lora_5). For hash_field companions the same structure (fields / field_name) is mirrored plus "format".
"""
HEURISTIC_RULES = [
    {
        "metafield": MetaField.MODEL_NAME,
        "keywords": ("ckpt_name", "base_ckpt_name", "checkpoint", "ckpt"),
        "format": "calc_model_hash",
        "hash_field": MetaField.MODEL_HASH,
        "required_class_keywords": [
            "loader",
            "load",
            "select",
            "selector",
            "ByteDanceSeedreamNode",
        ],
        "excluded_class_keywords": ["lora"],
    },
    {
        "metafield": MetaField.MODEL_NAME,
        "keywords": ("unet_name", "model_name", "model"),
        "format": "calc_unet_hash",
        "hash_field": MetaField.MODEL_HASH,
        "required_class_keywords": ["loader", "load", "select", "selector"],
        "excluded_class_keywords": ["lora"],
    },
    {
        "metafield": MetaField.VAE_NAME,
        "keywords": ("vae_name", "vae"),
        "format": "calc_vae_hash",
        "hash_field": MetaField.VAE_HASH,
        "required_class_keywords": ["loader", "vae", "load"],
        "excluded_class_keywords": ["encode", "decode"],
        "exact_only": True,
    },
    {
        "metafield": MetaField.CLIP_MODEL_NAME,
        "keywords": ("clip_name", "clip_name1", "clip_name2", "clip_name3"),
        "is_multi": True,
        "required_class_regex": [
            r"load\s*.*\s*clip",
        ],
        "required_class_keywords": ["clip loader", "load clip", "cliploader"],
        "sort_numeric": True,
    },
    {
        "metafield": MetaField.POSITIVE_PROMPT,
        "keywords": (
            "prompt",
            "text",
            "positive_prompt",
            "t5xxl",
            "clip_l",
            "prompt_positive",
            "text_positive",
            "positive",
            "positive_g",
            "positive_l",
            "text_g",
            "text_l",
            "conditioning.positive",
        ),
        "validate": "is_positive_prompt",
        "required_context": ["clip"],
        "required_class_keywords": [
            "encode",
            "prompt",
            "positive",
            "ByteDanceSeedreamNode",
        ],
    },
    {
        "metafield": MetaField.NEGATIVE_PROMPT,
        "keywords": (
            "prompt",
            "text",
            "negative_prompt",
            "prompt_negative",
            "text_negative",
            "negative",
            "t5xxl",
            "clip_l",
            "negative_g",
            "negative_l",
            "conditioning.negative",
        ),
        "validate": "is_negative_prompt",
        "required_context": ["clip"],
        "required_class_keywords": ["encode", "prompt", "negative"],
    },
    {
        "metafield": MetaField.SEED,
        "keywords": ("seed", "noise_seed", "random_seed"),
        "required_class_keywords": ["sampler", "seed", "ByteDanceSeedreamNode"],
        "type": ("INT"),
    },
    {
        "metafield": MetaField.STEPS,
        "keywords": ("steps",),
        "required_context": ("seed", "cfg", "denoise", "scheduler"),
        "required_class_keywords": ["sampler", "scheduler", "steps"],
        "type": ("INT"),
    },
    {
        "metafield": MetaField.CFG,
        "keywords": ("cfg", "cfg_scale"),
        "required_class_keywords": ["sampler", "cfg"],
        "type": ("FLOAT"),
    },
    {
        "metafield": MetaField.GUIDANCE,
        "keywords": ("guidance",),
        "required_class_keywords": ["sampler", "guidance", "clip", "encode"],
        "excluded_keywords": ("cfg",),
        "type": ("FLOAT"),
    },
    {
        "metafield": MetaField.SAMPLER_NAME,
        "keywords": ("sampler_name", "sampler", "sampler_mode"),
        "required_class_keywords": ["sampler"],
    },
    {
        "metafield": MetaField.SCHEDULER,
        "keywords": ("scheduler", "scheduler_name"),
        "required_class_keywords": ["sampler", "scheduler", "sigmas"],
    },
    {
        "metafield": MetaField.DENOISE,
        "keywords": ("denoise",),
        "required_class_keywords": ["sampler", "scheduler"],
        "type": ("FLOAT"),
    },
    {
        "metafield": MetaField.MAX_SHIFT,
        "keywords": ("max_shift",),
        "required_class_keywords": ["ModelSampling"],
        "type": ("FLOAT"),
    },
    {
        "metafield": MetaField.BASE_SHIFT,
        "keywords": ("base_shift",),
        "required_class_keywords": ["ModelSampling"],
        "type": ("FLOAT"),
    },
    {
        "metafield": MetaField.SHIFT,
        "keywords": ("shift",),
        "required_class_keywords": ["ModelSampling"],
        "excluded_keywords": ("base_shift", "max_shift"),
        "exact_only": True,
        "type": ("FLOAT"),
    },
    {
        "metafield": MetaField.WEIGHT_DTYPE,
        "keywords": ("weight_dtype",),
        # Prefer model-related classes
        "required_class_regex": [
            r"loader\s*.*\s*model",
            r"load\s*.*\s*model",
            r"model\s*.*\s*loader",
            r"select\s*.*\s*model",
            r"model\s*.*\s*selector",
        ],
        "required_class_keyword_groups": {
            "groups": [
                ["loader", "load", "select", "selector"],
                ["models", "model"],
            ],
            "mins": [1, 1],
        },
        # Fallback simple keywords
        "required_class_keywords": [
            "loader",
            "load",
            "select",
            "selector",
            "diffusion",
            "model",
        ],
    },
    {
        "metafield": MetaField.IMAGE_WIDTH,
        "keywords": (
            "width",
            "empty_latent_width",
            "resolution",
            "dimensions",
            "dimension",
        ),
        "required_context": ["height", "batch_size"],
        "required_class_keywords": [
            "latent",
            "loader",
            "load3d",
            "ByteDanceSeedreamNode",
        ],
    },
    {
        "metafield": MetaField.IMAGE_HEIGHT,
        "keywords": (
            "height",
            "empty_latent_height",
            "resolution",
            "dimensions",
            "dimension",
        ),
        "required_context": ["width", "batch_size"],
        "required_class_keywords": [
            "latent",
            "loader",
            "load3d",
            "ByteDanceSeedreamNode",
        ],
    },
    {
        "metafield": MetaField.LORA_MODEL_NAME,
        "keywords": ("lora_name", "lora"),
        "keywords_regex": (r"^lora_name_?\d{0,2}$", r"^lora_\d{1,2}$"),
        "is_multi": True,
        "format": "calc_lora_hash",
        "hash_field": MetaField.LORA_MODEL_HASH,
        "required_class_keywords": ["lora", "loader", "load"],
        "sort_numeric": True,
        "excluded_keywords": ("lora_syntax", "loaded_loras", "text"),
    },
    {
        "metafield": MetaField.LORA_STRENGTH_MODEL,
        "keywords": (
            "strength_model",
            "lora_strength",
            "lora_wt",
            "strength",
            "weight",
            "wt",
            "model_str",
            "lora_str",
        ),
        "keywords_regex": (
            r"^strength_model_?\d{0,2}$",
            r"^lora_strength_?\d{0,2}$",
            r"^lora_wt_?\d{0,2}$",
            r"^strength_0?\d$",
        ),
        "required_context": ["lora_name"],
        "is_multi": True,
        "required_class_keywords": ["lora", "loader", "load"],
        "type": "FLOAT",
        "sort_numeric": True,
    },
    {
        "metafield": MetaField.LORA_STRENGTH_CLIP,
        "keywords": (
            "strength_clip",
            "clip_strength",
            "clip_str",
            "strength",
            "weight",
            "wt",
            "clip",
        ),
        "keywords_regex": (r"^clip_str_?\d{0,2}$", r"^strength_clip_?\d{0,2}$"),
        "required_context": ["lora_name"],
        "is_multi": True,
        "required_class_keywords": ["lora", "loader", "load"],
        "type": "FLOAT",
        "sort_numeric": True,
    },
]


#
# --- MetadataRuleScanner: Scans installed nodes to suggest rules for capturing metadata ---
#
class MetadataRuleScanner:
    @classmethod
    def INPUT_TYPES(s):  # noqa: N802,N804
        return {
            "required": {
                "exclude_keywords": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "mask,find,resize,rotate,detailer,bus,scale,vision,text to,crop,xy,plot,controlnet,save,trainlora,postshot,loramanager",
                        "tooltip": "Comma-separated keywords to exclude nodes whose class names contain any of them.",
                    },
                )
            },
            "optional": {
                "include_existing": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": "If true, also rescan nodes already present in current capture definitions (useful after runtime changes).",
                    },
                ),
                "mode": (
                    ("new_only", "all", "existing_only"),
                    {
                        "default": "new_only",
                        "tooltip": "new_only: only new fields for existing nodes; all: full suggestions; existing_only: only nodes already captured.",
                    },
                ),
                "force_include_metafields": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "",
                        "tooltip": "Comma-separated MetaField names to always include even if already present (e.g. MODEL_HASH,LORA_MODEL_HASH).",
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("suggested_rules_json", "diff_report")
    FUNCTION = "scan_for_rules"
    CATEGORY = "SaveImageWithMetaDataUniversal/rules"
    DESCRIPTION = "Scans installed nodes to suggest rules for capturing metadata and outputs the rules in JSON format. 'exclude_keywords' can filter out irrelevant nodes by their class names."
    NODE_NAME = "Metadata Rule Scanner"

    def find_common_prefix(self, strings):
        if not strings or len(strings) < 2:
            return None
        prefix = os.path.commonprefix(strings)
        return prefix.rstrip("0123456789_") if prefix and not prefix.isdigit() else None

    def scan_for_rules(
        self,
        exclude_keywords="",
        include_existing=False,
        mode="new_only",
        force_include_metafields="",
    ):
        if _DEBUG_VERBOSE:
            logger.info("[Metadata Scanner] Starting scan...")
        suggested_nodes, suggested_samplers = {}, {}
        exclude_list = [kw.strip().lower() for kw in exclude_keywords.split(",") if kw.strip()]
        all_nodes = {k: v for k, v in nodes.NODE_CLASS_MAPPINGS.items() if hasattr(v, "INPUT_TYPES")}

        # Backward compatibility: older workflows that only set include_existing=True expect full duplication.
        initial_mode = mode or "new_only"
        if include_existing and initial_mode == "new_only":
            effective_mode = "all"
            if _DEBUG_VERBOSE:
                logger.info("[Metadata Scanner] include_existing=True upgraded mode from 'new_only' to 'all' (compat mode).")
        else:
            effective_mode = initial_mode
        force_include_set = {tok.strip().upper() for tok in force_include_metafields.split(",") if tok.strip()}
        # Diff counters
        new_nodes_count = 0
        existing_nodes_with_new = 0
        total_new_fields = 0
        total_existing_fields_included = 0
        total_skipped_fields = 0

        # --- Stage 1: Smarter Sampler Detection ---
        for class_name, class_object in all_nodes.items():
            if any(kw in class_name.lower() for kw in exclude_list):
                continue
            if "sampler" in class_name.lower():
                try:
                    # A node is a potential sampler if it has positive and negative inputs.
                    inputs = class_object.INPUT_TYPES().get("required", {})
                    candidate = None
                    if "positive" in inputs and "negative" in inputs:
                        candidate = {"positive": "positive", "negative": "negative"}
                    elif "base_positive" in inputs and "base_negative" in inputs:
                        candidate = {
                            "positive": "base_positive",
                            "negative": "base_negative",
                        }
                    elif "guider" in inputs:
                        candidate = {"positive": "guider"}
                    if candidate:
                        if class_name in SAMPLERS:
                            existing_map = SAMPLERS.get(class_name, {})
                            if effective_mode == "existing_only" or effective_mode == "all":
                                # Include full (all) only if mode == all; existing_only returns existing intersection
                                if effective_mode == "all":
                                    suggested_samplers[class_name] = candidate
                                elif effective_mode == "existing_only":
                                    # intersect keys
                                    inter = {k: v for k, v in candidate.items() if k in existing_map}
                                    if inter:
                                        suggested_samplers[class_name] = inter
                            elif effective_mode == "new_only":
                                diff = {k: v for k, v in candidate.items() if k not in existing_map}
                                if diff:
                                    suggested_samplers[class_name] = diff
                        else:
                            # brand new sampler
                            if effective_mode != "existing_only":
                                suggested_samplers[class_name] = candidate
                        if class_name in suggested_samplers:
                            if _DEBUG_VERBOSE:
                                logger.info(
                                    "[Metadata Scanner] Found potential sampler: %s",
                                    class_name,
                                )
                except Exception as e:
                    if _DEBUG_VERBOSE:
                        logger.debug(
                            "[Metadata Scanner] Sampler detection error for %s: %s",
                            class_name,
                            e,
                        )
                    continue

        # --- Stage 2: More Accurate Capture Rule Detection ---
        for class_name, class_object in all_nodes.items():
            if any(kw in class_name.lower() for kw in exclude_list):
                continue
            is_existing = class_name in CAPTURE_FIELD_LIST
            if is_existing and effective_mode == "new_only":
                # We'll process but later filter out existing fields.
                pass
            elif is_existing and effective_mode == "existing_only":
                # Process to allow potential field diff display (existing subset)
                pass
            elif is_existing and effective_mode == "all":
                pass
            elif not is_existing and effective_mode == "existing_only":
                # Skip brand new nodes in existing_only mode
                continue
            elif not is_existing and effective_mode in ("new_only", "all"):
                pass  # include

            try:
                inputs, node_suggestions = class_object.INPUT_TYPES(), {}
                req_inputs = inputs.get("required", {}) or {}
                opt_inputs = inputs.get("optional", {}) or {}
                all_input_names = set(req_inputs.keys()) | set(opt_inputs.keys())
                lower_class_name = class_name.lower()

                # Build a map of input field -> declared type string (uppercased), when available
                field_types = {}

                def _declared_type_for(name):
                    val = req_inputs.get(name)
                    if val is None:
                        val = opt_inputs.get(name)
                    dtype = None
                    if isinstance(val, tuple | list) and len(val) > 0:
                        first = val[0]
                        if isinstance(first, str):
                            dtype = first
                        elif isinstance(first, tuple | list) and len(first) > 0 and isinstance(first[0], str):
                            # e.g., a list/tuple of possible types; take the first string as representative
                            dtype = first[0]
                    elif isinstance(val, str):
                        dtype = val
                    return dtype.upper() if isinstance(dtype, str) else None

                for nm in all_input_names:
                    try:
                        field_types[nm] = _declared_type_for(nm)
                    except Exception:
                        field_types[nm] = None

                for rule in HEURISTIC_RULES:
                    # --- Check for excluded class keywords ---
                    excluded_kws = rule.get("excluded_class_keywords")
                    if excluded_kws and any(kw in lower_class_name for kw in excluded_kws):
                        continue

                    # Advanced required-class matching: regex or keyword groups (fallback to simple any-of)
                    def _matches_required_class(rule_obj, lower_name):
                        # 1) Regex patterns (any match passes)
                        patterns = rule_obj.get("required_class_regex") or []
                        for pat in patterns:
                            try:
                                if re.search(pat, lower_name):
                                    return True
                            except Exception:
                                # ignore invalid patterns
                                pass

                        # 2) Keyword groups with per-group minimums
                        groups_spec = rule_obj.get("required_class_keyword_groups")
                        if groups_spec:
                            groups = None
                            mins = None
                            if isinstance(groups_spec, dict):
                                groups = groups_spec.get("groups")
                                mins = groups_spec.get("mins") or groups_spec.get("required")
                            elif isinstance(groups_spec, list):
                                # list of dicts: [{"keywords": [...], "min": 1}, ...]
                                groups = [g.get("keywords", []) for g in groups_spec if isinstance(g, dict)]
                                mins = [g.get("min", 1) for g in groups_spec if isinstance(g, dict)]
                            if isinstance(groups, list | tuple) and isinstance(mins, list | tuple) and len(groups) == len(mins) and groups:
                                name_simple = re.sub(r"[ _-]+", "", lower_name)
                                all_ok = True
                                for kws, min_req in zip(groups, mins):
                                    count = 0
                                    for kw in kws or []:
                                        if not isinstance(kw, str):
                                            continue
                                        kw_l = kw.lower()
                                        if kw_l in lower_name:
                                            count += 1
                                        else:
                                            kw_simple = re.sub(r"[ _-]+", "", kw_l)
                                            if kw_simple and kw_simple in name_simple:
                                                count += 1
                                    try:
                                        need = int(min_req)
                                    except Exception:
                                        need = 1
                                    if need > count:
                                        all_ok = False
                                        break
                                if all_ok:
                                    return True

                        # 3) Simple any-of keywords (legacy behavior)
                        class_kws2 = rule_obj.get("required_class_keywords")
                        if class_kws2:
                            for kw in class_kws2:
                                try:
                                    if isinstance(kw, str) and kw.lower() in lower_name:
                                        return True
                                except Exception:
                                    pass
                            return False
                        # No constraints -> accept
                        return True

                    if not _matches_required_class(rule, lower_class_name):
                        continue

                    context_kws = rule.get("required_context")
                    if context_kws and not any(any(ctx in name.lower() for ctx in context_kws) for name in all_input_names):
                        continue

                    if rule["metafield"] in node_suggestions:
                        continue

                    # Unified helper collections (exclusions & type) built lazily when needed
                    excluded_kws = tuple(rule.get("excluded_keywords") or ())
                    excluded_kws = tuple(kw.lower() for kw in excluded_kws if isinstance(kw, str))
                    allowed_types = rule.get("type")
                    if isinstance(allowed_types, list | tuple | set):
                        allowed_types_norm = {str(t).upper() for t in allowed_types}
                    elif allowed_types is not None:
                        allowed_types_norm = {str(allowed_types).upper()}
                    else:
                        allowed_types_norm = None

                    def _type_ok(field_name: str) -> bool:
                        if allowed_types_norm is None:
                            return True
                        ftype = field_types.get(field_name)
                        if not ftype:
                            return False
                        return ftype in allowed_types_norm

                    # --- EARLY MULTI-FIELD HANDLING ---
                    if rule.get("is_multi"):
                        # Gather matching field names
                        kws_norm = [kw.lower() if isinstance(kw, str) else str(kw).lower() for kw in rule.get("keywords", [])]
                        regex_patterns = rule.get("keywords_regex") or []
                        matching_fields = []
                        for fn in all_input_names:
                            lname = fn.lower()
                            if excluded_kws and any(ex_kw in lname for ex_kw in excluded_kws):
                                continue
                            if not _type_ok(fn):
                                continue
                            matched = False
                            if rule.get("exact_only"):
                                if any(lname == kw for kw in kws_norm):
                                    matched = True
                            else:
                                if any(kw in lname for kw in kws_norm):
                                    matched = True
                            if not matched and regex_patterns:
                                for pat in regex_patterns:
                                    try:
                                        if re.search(pat, fn, re.IGNORECASE):  # noqa: F823
                                            matched = True
                                            break
                                    except Exception:
                                        continue
                            if matched:
                                matching_fields.append(fn)
                        if matching_fields:
                            # Optional numeric-aware sorting
                            if rule.get("sort_numeric"):
                                import re

                                def _num_key(s):
                                    m = re.search(r"(\d+)(?!.*\d)", s)
                                    return (
                                        int(m.group(1)) if m else 1_000_000,
                                        s.lower(),
                                    )

                                matching_fields = sorted(matching_fields, key=_num_key)
                            else:
                                matching_fields = sorted(matching_fields)
                            if len(matching_fields) == 1:
                                suggestion = {"field_name": matching_fields[0]}
                                if rule.get("validate"):
                                    suggestion["validate"] = rule["validate"]
                                node_suggestions[rule["metafield"]] = suggestion
                                if rule.get("format") and rule.get("hash_field"):
                                    node_suggestions[rule["hash_field"]] = {
                                        "field_name": matching_fields[0],
                                        "format": rule["format"],
                                    }
                            else:
                                suggestion = {"fields": matching_fields}
                                if rule.get("validate"):
                                    suggestion["validate"] = rule["validate"]
                                node_suggestions[rule["metafield"]] = suggestion
                                if rule.get("format") and rule.get("hash_field"):
                                    node_suggestions[rule["hash_field"]] = {
                                        "fields": matching_fields,
                                        "format": rule["format"],
                                    }
                        # Multi handled; move to next rule
                        continue

                    # --- Exact-first then partial matching in keyword order ---
                    best_field = None
                    lower_names = {name: name.lower() for name in all_input_names}
                    if excluded_kws:
                        lower_names_filtered = {
                            name: lname
                            for name, lname in lower_names.items()
                            if not any(ex_kw in lname for ex_kw in excluded_kws) and _type_ok(name)
                        }
                    else:
                        lower_names_filtered = {name: lname for name, lname in lower_names.items() if _type_ok(name)}

                    exact_only = bool(rule.get("exact_only"))

                    regex_patterns = rule.get("keywords_regex") or []
                    # 1) exact matches first, in keyword order
                    for kw in rule["keywords"]:
                        kw_norm = kw.lower() if isinstance(kw, str) else str(kw).lower()
                        for name, lname in lower_names_filtered.items():
                            if lname == kw_norm:
                                best_field = name
                                break
                        if best_field:
                            break
                    # 2) if none, allow substring matches in keyword order (unless exact_only)
                    if not best_field and not exact_only:
                        for kw in rule["keywords"]:
                            kw_norm = kw.lower() if isinstance(kw, str) else str(kw).lower()
                            for name, lname in lower_names_filtered.items():
                                if kw_norm in lname:
                                    best_field = name
                                    break
                            if best_field:
                                break
                    # 2.5) regex patterns if still none
                    if not best_field and regex_patterns:
                        for pat in regex_patterns:
                            try:
                                for name in lower_names_filtered.keys():
                                    if re.search(pat, name, re.IGNORECASE):
                                        best_field = name
                                        break
                                if best_field:
                                    break
                            except Exception:
                                continue

                    if best_field:
                        # Construct the rule dictionary in the correct order
                        # Keep name fields human-readable; attach format only to the hash field when present.
                        suggestion = {"field_name": best_field}
                        if rule.get("validate"):
                            suggestion["validate"] = rule["validate"]

                        node_suggestions[rule["metafield"]] = suggestion

                        # Automatically add the corresponding hash field rule and attach formatter there
                        if rule.get("format") and rule.get("hash_field"):
                            hash_field = rule.get("hash_field")
                            hash_suggestion = {
                                "field_name": best_field,
                                "format": rule["format"],
                            }
                            node_suggestions[hash_field] = hash_suggestion

                    # (multi case already handled above)

                if node_suggestions:
                    if is_existing:
                        existing_rules = CAPTURE_FIELD_LIST.get(class_name, {}) or {}
                        candidate_total = len(node_suggestions)
                        final_map = {}
                        if effective_mode == "new_only":
                            for mf, data in node_suggestions.items():
                                if mf not in existing_rules or mf.name in force_include_set:
                                    tagged = dict(data)
                                    tagged.setdefault(
                                        "status",
                                        "new" if mf not in existing_rules else "existing",
                                    )
                                    final_map[mf] = tagged
                        elif effective_mode == "existing_only":
                            for mf, data in node_suggestions.items():
                                if mf in existing_rules or mf.name in force_include_set:
                                    tagged = dict(data)
                                    tagged.setdefault(
                                        "status",
                                        "existing" if mf in existing_rules else "new",
                                    )
                                    final_map[mf] = tagged
                        elif effective_mode == "all":
                            for mf, data in node_suggestions.items():
                                tagged = dict(data)
                                tagged.setdefault(
                                    "status",
                                    "existing" if mf in existing_rules else "new",
                                )
                                final_map[mf] = tagged
                        if final_map:
                            suggested_nodes[class_name] = final_map
                            new_here = sum(1 for mf in final_map if final_map[mf].get("status") == "new")
                            existing_here = sum(1 for mf in final_map if final_map[mf].get("status") == "existing")
                            total_new_fields += new_here
                            total_existing_fields_included += existing_here
                            skipped = candidate_total - len(final_map)
                            if skipped > 0:
                                total_skipped_fields += skipped
                            if new_here > 0:
                                existing_nodes_with_new += 1
                    else:
                        if effective_mode != "existing_only":
                            tagged_map = {}
                            for mf, data in node_suggestions.items():
                                tagged = dict(data)
                                tagged.setdefault("status", "new")
                                tagged_map[mf] = tagged
                            suggested_nodes[class_name] = tagged_map
                            new_nodes_count += 1
                            total_new_fields += len(tagged_map)
            except Exception as e:
                logger.warning("[Scanner Warning] Could not process '%s': %s", class_name, e)

        # Build sampler status map
        sampler_status = {}
        if suggested_samplers:
            for s_name, mapping in suggested_samplers.items():
                existing_map = SAMPLERS.get(s_name, {})
                sampler_status[s_name] = {
                    k: {
                        "value": v,
                        "status": ("existing" if k in existing_map else "new"),
                    }
                    for k, v in mapping.items()
                }

        final_output = {
            "nodes": {},
            "samplers": {},
            "samplers_status": sampler_status,
            "summary": {},
        }
        if suggested_nodes:
            final_output["nodes"] = {node: {mf.name: data for mf, data in rules.items()} for node, rules in suggested_nodes.items()}
        if suggested_samplers:
            final_output["samplers"] = suggested_samplers
        final_output["summary"] = {
            "mode": effective_mode,
            "new_nodes": new_nodes_count,
            "existing_nodes_with_new_fields": existing_nodes_with_new,
            "total_new_fields": total_new_fields,
            "total_existing_fields_included": total_existing_fields_included,
            "total_skipped_fields": total_skipped_fields,
            "force_included_metafields": sorted(list(force_include_set)) if force_include_set else [],
        }

        diff_report = (
            f"Mode={effective_mode}; New nodes={new_nodes_count}; Existing nodes w/ new fields={existing_nodes_with_new}; "
            f"New fields={total_new_fields}; Existing fields included={total_existing_fields_included}; Skipped fields={total_skipped_fields}; "
            f"Force include={','.join(sorted(force_include_set)) if force_include_set else 'None'}"
        )

        return (json.dumps(final_output, indent=4), diff_report)


#
# --- SaveCustomMetadataRules: Saves user-defined rules, typically from MetadataRuleScanner,
# to samplers and captures JSON files and generates a Python extension ---
#
class SaveCustomMetadataRules:
    @classmethod
    def INPUT_TYPES(s):  # noqa: N802, N804
        return {"required": {"rules_json_string": ("STRING", {"multiline": True})}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "save_rules"
    CATEGORY = "SaveImageWithMetaDataUniversal/rules"
    DESCRIPTION = "Saves custom metadata capture rules to user_captures.json and user_samplers.json, and generates a Python extension allowing imported nodes to have their 'field_name's and values written to metadata."
    NODE_NAME = "Save Custom Metadata Rules"
    OUTPUT_NODE = True

    def save_rules(self, rules_json_string):
        # This path needs to be consistent with the loading paths.
        PY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # noqa: N806
        USER_CAPTURES_FILE = os.path.join(PY_DIR, "user_captures.json")  # noqa: N806
        USER_SAMPLERS_FILE = os.path.join(PY_DIR, "user_samplers.json")  # noqa: N806
        EXT_DIR = os.path.join(PY_DIR, "defs", "ext")  # noqa: N806
        os.makedirs(EXT_DIR, exist_ok=True)
        GENERATED_EXT_FILE = os.path.join(EXT_DIR, "generated_user_rules.py")  # noqa: N806

        saved_files = []
        try:
            data = json.loads(rules_json_string)
            raw_nodes = data.get("nodes", {}) if isinstance(data.get("nodes"), dict) else {}
            sanitized_nodes = {}
            for node_name, meta_map in raw_nodes.items():
                if not isinstance(meta_map, dict):
                    continue
                cleaned = {}
                for mf_name, rule in meta_map.items():
                    if isinstance(rule, dict):
                        r2 = {k: v for k, v in rule.items() if k != "status"}
                        cleaned[mf_name] = r2
                    else:
                        cleaned[mf_name] = rule
                sanitized_nodes[node_name] = cleaned
            if sanitized_nodes:
                with open(USER_CAPTURES_FILE, "w") as f:
                    json.dump(sanitized_nodes, f, indent=4)
                saved_files.append("user_captures.json")
            if "samplers" in data and isinstance(data["samplers"], dict):
                with open(USER_SAMPLERS_FILE, "w") as f:
                    json.dump(data["samplers"], f, indent=4)
                saved_files.append("user_samplers.json")

            # Additionally, emit a Python extension that wires up formatter callables
            # so that downstream loading can import functions (merge 1 path as well).
            try:
                nodes_dict = sanitized_nodes
                samplers_dict = data.get("samplers", {})
                # Build a simple Python module text
                lines = []
                lines.append("from ..meta import MetaField")
                lines.append(
                    "from ..formatters import (calc_model_hash, calc_vae_hash, calc_lora_hash, calc_unet_hash, convert_skip_clip, get_scaled_width, get_scaled_height, extract_embedding_names, extract_embedding_hashes)"
                )
                lines.append("from ..validators import is_positive_prompt, is_negative_prompt")
                # Common selectors from built-in extensions
                lines.append(
                    "from .efficiency_nodes import (get_lora_model_name_stack, get_lora_model_hash_stack, get_lora_strength_model_stack, get_lora_strength_clip_stack)"
                )
                lines.append("")
                # A mapping of known callable names to actual objects
                lines.append("KNOWN = {")
                lines.append("    'calc_model_hash': calc_model_hash,")
                lines.append("    'calc_vae_hash': calc_vae_hash,")
                lines.append("    'calc_lora_hash': calc_lora_hash,")
                lines.append("    'calc_unet_hash': calc_unet_hash,")
                lines.append("    'convert_skip_clip': convert_skip_clip,")
                lines.append("    'get_scaled_width': get_scaled_width,")
                lines.append("    'get_scaled_height': get_scaled_height,")
                lines.append("    'extract_embedding_names': extract_embedding_names,")
                lines.append("    'extract_embedding_hashes': extract_embedding_hashes,")
                lines.append("    'is_positive_prompt': is_positive_prompt,")
                lines.append("    'is_negative_prompt': is_negative_prompt,")
                lines.append("    'get_lora_model_name_stack': get_lora_model_name_stack,")
                lines.append("    'get_lora_model_hash_stack': get_lora_model_hash_stack,")
                lines.append("    'get_lora_strength_model_stack': get_lora_strength_model_stack,")
                lines.append("    'get_lora_strength_clip_stack': get_lora_strength_clip_stack,")
                lines.append("}")
                lines.append("")
                # Ensure valid assignment syntax on a single statement
                lines.append("SAMPLERS = " + json.dumps(samplers_dict, indent=4))
                lines.append("")
                lines.append("CAPTURE_FIELD_LIST = {")
                # We need to render MetaField keys; write as MetaField.NAME
                for node_name, rules in nodes_dict.items():
                    lines.append("    " + json.dumps(node_name) + ": {")
                    for metafield_name, rule in rules.items():
                        # Convert function names to identifiers
                        rule_copy = dict(rule)
                        # Known callable fields: 'format'
                        if isinstance(rule_copy.get("format"), str):
                            rule_copy["format"] = rule_copy["format"]
                        # Known keys are field_name, fields, prefix, selector, validate, format
                        # Build the dict literal by hand to allow non-quoted callables
                        body_parts = []
                        if "field_name" in rule_copy:
                            body_parts.append(f"'field_name': {json.dumps(rule_copy['field_name'])}")
                        if "fields" in rule_copy and isinstance(rule_copy.get("fields"), list | tuple):
                            body_parts.append(f"'fields': {json.dumps(rule_copy['fields'])}")
                        if "prefix" in rule_copy:
                            body_parts.append(f"'prefix': {json.dumps(rule_copy['prefix'])}")
                        if "selector" in rule_copy:
                            sel = rule_copy["selector"]
                            if isinstance(sel, str):
                                body_parts.append("'selector': KNOWN[" + json.dumps(sel) + "]")
                            else:
                                body_parts.append(f"'selector': {json.dumps(sel)}")
                        if "validate" in rule_copy:
                            val = rule_copy["validate"]
                            if isinstance(val, str):
                                body_parts.append("'validate': KNOWN[" + json.dumps(val) + "]")
                            else:
                                body_parts.append(f"'validate': {json.dumps(val)}")
                        if "format" in rule_copy:
                            fmt = rule_copy["format"]
                            if isinstance(fmt, str):
                                body_parts.append("'format': KNOWN[" + json.dumps(fmt) + "]")
                            else:
                                body_parts.append(f"'format': {json.dumps(fmt)}")
                        body = ", ".join(body_parts)
                        lines.append(f"        MetaField.{metafield_name}: {{" + body + "},")
                    lines.append("    },")
                lines.append("}")

                with open(GENERATED_EXT_FILE, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
                saved_files.append("defs/ext/generated_user_rules.py")
            except Exception as gen_err:
                # Non-fatal; JSON files saved above ensure functionality.
                logger.warning(
                    "[Metadata Loader] Could not generate python ext from rules: %s",
                    gen_err,
                )
            if not saved_files:
                return ("No valid 'nodes' or 'samplers' sections found.",)
            return (f"Successfully saved: {', '.join(saved_files)}",)
        except Exception as e:
            raise ValueError(f"Error saving rules: {e}")
