import os
from collections.abc import Sequence

try:  # Runtime import
    from comfy.sd1_clip import expand_directory_list  # type: ignore
except Exception:  # noqa: BLE001 - test fallback
    def expand_directory_list(paths):  # type: ignore
        # Simplistic passthrough stub for tests
        return list(paths)

__all__ = ["get_embedding_file_path"]


def get_embedding_file_path(embedding_name: str, clip: object) -> str | None:
    """Resolve an embedding filename to an absolute path if it exists.

    The lookup expands the `clip.embedding_directory` attribute (string or sequence
    of strings) using ComfyUI's `expand_directory_list`, then searches each
    directory for the provided base name with or without a known extension.

    Search order per directory:
      1. Exact `embedding_name` as‑is (allows explicit extension callers)
      2. Append each of: `.safetensors`, `.pt`, `.bin`

    A small security guard ensures the resolved file path remains inside the
    candidate directory (defensive against path traversal tokens in
    `embedding_name`).

    Args:
        embedding_name: Base file name (may optionally already include an
            extension). Should NOT contain parent references intended to escape
            search roots.
        clip: Object with an `embedding_directory` attribute (string or
            iterable of strings). This mirrors the structure on ComfyUI CLIP
            objects. Attribute absence or emptiness raises `ValueError` for
            clearer upstream diagnostics.

    Returns:
        Absolute path to the first matching embedding file, or `None` if no
        candidate is found.

    Raises:
        ValueError: If the embedding directory attribute is missing/empty, the
            expansion yields no valid directories, or expansion fails.
    """
    embedding_directory = getattr(clip, "embedding_directory", None)
    if not embedding_directory:
        raise ValueError(
            "The 'embedding_directory' attribute in the clip object is None or empty."  # noqa: E501
        )

    if isinstance(embedding_directory, str):
        embedding_dirs: Sequence[str] = [embedding_directory]
    elif isinstance(embedding_directory, list | tuple | set):
        embedding_dirs = [str(p) for p in embedding_directory]
    else:  # Fallback: treat single unknown object as string repr
        embedding_dirs = [str(embedding_directory)]

    try:
        expanded: list[str] = expand_directory_list(list(embedding_dirs))
    except (OSError, TypeError, ValueError) as e:  # Narrow common failures
        raise ValueError(f"Error expanding directory list: {e}") from e
    except Exception as e:  # pragma: no cover - defensive catch
        raise ValueError(f"Unexpected error expanding directory list: {e}") from e

    if not expanded:
        raise ValueError("No valid directories found after expansion.")

    valid_file: str | None = None
    extensions = [".safetensors", ".pt", ".bin"]

    for embed_dir in expanded:
        embed_dir_abs = os.path.abspath(embed_dir)
        if not os.path.isdir(embed_dir_abs):
            continue

        embed_path = os.path.abspath(os.path.join(embed_dir_abs, embedding_name))
        try:
            if os.path.commonpath([embed_dir_abs, embed_path]) != embed_dir_abs:
                # Path attempted to escape search root – ignore
                continue
        except (OSError, ValueError):  # Invalid path comparison edge cases
            continue

        # Direct file match
        if os.path.isfile(embed_path):
            valid_file = embed_path
        else:  # Try with extensions
            for ext in extensions:
                candidate_path = embed_path + ext
                if os.path.isfile(candidate_path):
                    valid_file = candidate_path
                    break

        if valid_file:
            break

    return valid_file
