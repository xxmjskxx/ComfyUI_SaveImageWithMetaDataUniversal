# Contributing

Thank you for your interest in improving the SaveImageWithMetaData Universal node pack.

## Development Environment
1. Clone the repository inside your ComfyUI `custom_nodes` directory.
2. Ensure Python version matches the ComfyUI embed (e.g. 3.10/3.11 depending on build).
3. (Optional) Create a virtual environment if working outside the embedded interpreter.

## Installation (Extras for Testing)
If you run tests outside the ComfyUI runtime, install minimal deps:
```
pip install -r requirements-dev.txt
```
(If `requirements-dev.txt` does not exist yet, typical packages: `pytest`, `ruff`.)

## Linting
We use Ruff; line length is 140.
```
ruff check .
```
Auto-fix (safe fixes only):
```
ruff check . --fix
```

## Testing
```
pytest -q
```
Run a single test:
```
pytest tests/test_lora_summary_toggle.py::test_include_lora_summary_toggle -q
```
Enable deterministic multiline parameter formatting:
```
METADATA_TEST_MODE=1 pytest -q
```
On Windows (cmd):
```
set METADATA_TEST_MODE=1 && pytest -q
```

## Commit Guidelines
- Follow Google-style docstrings for all functions/classes (Args / Returns / Raises).
- Keep lines <= 140 characters.
- Prefer small, focused commits.
- Reference related issues in commit messages when applicable.

## Adding New Metadata Fields
1. Add enum entry to `saveimage_unimeta/defs/meta.py`.
2. Add rule to `saveimage_unimeta/defs/captures.py` (or extension under `defs/ext/`).
3. (Optional) Update ordering in `Capture.gen_parameters_str`.
4. Add / update tests.

## Environment Flags
- `METADATA_NO_HASH_DETAIL`: Suppress structured hash detail JSON.
- `METADATA_NO_LORA_SUMMARY`: Suppress aggregated `LoRAs:` summary (per‑LoRA entries remain).
- `METADATA_TEST_MODE`: Multiline deterministic formatting for tests.
- `METADATA_DEBUG_PROMPTS`: Verbose prompt logging.

## LoRA Summary Override
The node UI parameter `include_lora_summary` overrides `METADATA_NO_LORA_SUMMARY`.

Precedence: UI explicit True/False > env flag > default include.

## Submitting PRs
- Ensure all tests pass.
- Ensure no new Ruff violations.
- Avoid large unrelated refactors in feature/bugfix PRs.

## License
Contributions are accepted under the same license as the host project.
