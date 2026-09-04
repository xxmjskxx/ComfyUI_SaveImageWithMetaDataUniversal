# Security: Workflow Redaction & Filename Safety

Status: Implemented (always-on filename sanitization + opt-out workflow redaction).
Last Updated: 2026-09-03

## 1. Why This Exists
Workflow JSON embedded into saved images can contain secret-like values (API keys, tokens, passwords, authorization headers) and absolute filesystem paths. Separately, filename tokens such as `%model%` or `%pprompt%` interpolate user-controlled text into the output path, which could otherwise produce absolute paths, directory traversal, or invalid filenames. This module neutralizes both risks without ever preventing an image from being saved.

## 2. Workflow Redaction (`sanitize_metadata` toggle)

The save node exposes a `sanitize_metadata` BOOLEAN toggle, **default on**. When enabled, the embedded workflow JSON (`prompt` and `extra_pnginfo`) is passed through `saveimage_unimeta/utils/redaction.py` before it is written to the image or sidecar.

The sanitizer redacts:
- Values whose key normalizes to a known secret name: `api_key`/`apikey`, `api_token`, `access_token`, `refresh_token`, `auth_token`, `authorization`, `bearer`, `client_secret`, `private_key`, `secret_key`, `password`, `passwd`, `secret`, `token`.
- `Bearer <credential>` literals.
- Absolute paths: Windows drive-letter (`C:\...`), UNC (`\\server\share`), and POSIX (`/Users/...`, `/home/...`).
- Control characters (replaced with spaces; newlines/tabs are preserved).

### Scope
- **In scope:** the embedded workflow JSON only (`prompt` + `extra_pnginfo`).
- **Out of scope:** values from the `extra_metadata` node input and the A1111-style `parameters` text produced by `Capture.gen_pnginfo`. Explicit `extra_metadata` is treated as intentional user input and is not sanitized.

### Fidelity tradeoff
Redaction recurses through **every string** in the workflow JSON, including the generation prompt stored in `CLIPTextEncode` node inputs. If a prompt contains a path-like substring (`C:\...`, `/home/...`) or a literal `Bearer ...`, that substring is redacted in the embedded `prompt` workflow while the same text remains unsanitized in the `parameters` text. The two embedded copies of the prompt can therefore differ. This is accepted: exact key matches and path/credential regexes are narrowly targeted, and ordinary prose is preserved.

### Bounded and fail-open
The sanitizer is bounded (`MAX_METADATA_DEPTH`, `MAX_METADATA_ITEMS`, `MAX_METADATA_STRING_CHARS`, `MAX_METADATA_KEY_CHARS`). If a limit is exceeded it raises `MetadataSanitizationError`; the save node catches this, logs a warning, and embeds the raw (unsanitized) workflow rather than failing the save.

## 3. Filename Safety (always-on)

After token expansion, the save node passes the filename template through `saveimage_unimeta/utils/pathsafety.py`. This is always on and has no toggle:

- Normalizes separators and strips drive letters, UNC roots, and leading slashes.
- Drops `.` and `..` components (no directory traversal).
- Neutralizes reserved Windows device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).
- Replaces invalid filename characters (`< > : " | ? *` and control characters).
- Clamps each path component to 120 chars and the full template to 512.

The result is always a safe relative path, so the image is always written inside the output directory. If sanitization leaves nothing usable it falls back to `image`.

## 4. Guarantees
- Sanitization never mutates its input (the live ComfyUI prompt cache is not corrupted).
- Neither redaction nor path sanitization can fail a save; both degrade gracefully.
- The `.sha256` sidecar hashing behavior is unchanged by this module.
