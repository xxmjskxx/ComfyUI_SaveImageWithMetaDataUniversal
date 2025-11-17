---
post_title: "Development Workflow Testing Guide"
author1: "ComfyUI SaveMeta Maintainers"
post_slug: "dev-workflow-testing"
microsoft_alias: "none"
featured_image: ""
categories:
	- "guides"
tags:
	- "testing"
	- "cli"
	- "workflows"
ai_note: "Updated with the help of GitHub Copilot (GPT-5.1-Codex)."
summary: "How to run ComfyUI dev workflows and validate metadata entirely from the CLI."
post_date: 2025-11-17
---

## Overview

Use the CLI helpers in `tests/tools/` to run dev workflows without touching the UI and to verify that generated images still carry the expected metadata. The two scripts ship with the repo and stay aligned with the latest node behavior:

- `run_dev_workflows.py` queues workflows against a ComfyUI instance, optionally launching the server for you.
- `validate_metadata.py` scans finished outputs and confirms that hashes, prompts, LoRAs, and fallback markers match the workflow graph.

## Prerequisites

- Python 3.9+ (matches your ComfyUI runtime).
- ComfyUI checkout with `main.py` plus any models referenced by your workflows.
- Optional: `send2trash` if you want the runner to clean the `output/Test` folder safely.

Install the helper dependency when you need cleanup support:

```cmd
python tests/tools/run_dev_workflows.py ^
```

## Local Workflow Directory

`run_dev_workflows.py` expects API-format workflows under `tests/comfyui_cli_tests/dev_test_workflows/` by default. Keep this directory out of source control so you can reference local-only model paths.

1. Enable **Dev Mode** inside the ComfyUI UI.
python tests/tools/validate_metadata.py ^
3. Drop the JSON inside `tests/comfyui_cli_tests/dev_test_workflows/your_suite/`.
4. Repeat for every scenario you want to cover (Flux, SDXL, stub runs, etc.).

You can override the folder with `--workflow-dir`, so feel free to organize additional suites elsewhere.

## Running Workflows

The script lives at `tests/tools/run_dev_workflows.py`. Run it with the Python interpreter that should host ComfyUI so that binaries and CUDA libraries match.

**Windows (single line):**

```cmd
python tests/tools/run_dev_workflows.py ^
```

**Windows (multi-line for readability):**

```cmd
python tests/tools/run_dev_workflows.py ^
	--comfyui-path "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI_windows_portable" ^
	--python-exe "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI_windows_portable\python_embeded\python.exe" ^
	--temp-dir "F:\StableDiffusion\ComfyUI" ^
	--output-folder "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI_windows_portable\ComfyUI\output\Test" ^
	--extra-args "--windows-standalone-build" ^
	--server-wait 30
```

**Linux/macOS:**

### Common scenarios

- Use an existing server: `--no-start-server` keeps the script from spawning `main.py`; it will fail fast if nothing is listening on `host:port`.

### Host, port, and pacing

- `--host` and `--port` default to `127.0.0.1:8188`. Update both when running multiple instances side by side.
- `--wait-between` inserts a delay (seconds) between queue requests. Increase it when your GPU needs more breathing room.
- `--server-wait` is the startup timeout. Raise it (for example `--server-wait 45`) if ComfyUI needs longer than 10 seconds to compile custom nodes.

## Command Reference

### run_dev_workflows.py flags

| Flag | Purpose | Default |
| --- | --- | --- |
| `--comfyui-path` | Directory containing `main.py`. | required |
| `--python-exe` | Interpreter used to launch ComfyUI. | current Python |
| `--workflow-dir` | Relative path below `tests/comfyui_cli_tests/` or an absolute folder. | `dev_test_workflows` |
| `--host`, `--port` | HTTP endpoint used for API calls. | `127.0.0.1`, `8188` |
| `--temp-dir` | Passed to ComfyUI as `--temp-directory`. | unset |
| `--extra-args` | Additional ComfyUI CLI switches, space-separated in one quoted string. | unset |
| `--server-wait` | Seconds to wait for ComfyUI startup before abandoning. | `10` |
| `--wait-between` | Seconds between queued prompts. | `2.0` |
| `--no-start-server` | Skip launching `main.py` (requires a running server). | `False` |
| `--keep-server` | Leave the spawned server alive after the final workflow. | `False` |
| `--output-folder` | Folder to clean before queuing (pairs with `send2trash`). | unset |
| `--no-clean` | Leave previous outputs untouched even if `--output-folder` is set. | `False` |
| `--enable-test-stubs` | Export `METADATA_ENABLE_TEST_NODES=1` for MetadataTestSampler runs. | `False` |

### validate_metadata.py flags

| Flag | Purpose | Default |
| --- | --- | --- |
| `--output-folder` | Location of the ComfyUI `output/Test` directory to scan. | required |
| `--workflow-dir` | Workflow source so the validator can read expected metadata. | `dev_test_workflows` |
| `--comfyui-models-path` | Optionally tell the validator where to find cached model hashes. | unset |
| `--verbose` | Print every pass/fail detail instead of summaries only. | `False` |

## Cleaning the Output Folder

Set `--output-folder` to point at `ComfyUI/output/Test`. When `send2trash` is available, every file inside gets recycled before your run so validation works against a clean slate. Add `--no-clean` whenever you want to keep previous diagnostics for comparison.

**Example:**

```cmd
python tests/tools/run_dev_workflows.py ^
	--comfyui-path "C:\StableDiffusion\ComfyUI" ^
	--output-folder "C:\StableDiffusion\ComfyUI\output\Test" ^
	--no-clean
```

```bash
python tests/tools/run_dev_workflows.py --comfyui-path "/path/to/ComfyUI" --enable-test-stubs --workflow-dir "tests/comfyui_cli_tests/dev_test_workflows/stubs"
```

## Validating Metadata

Once renders finish, run the validator so regressions are obvious before opening a PR.

**Windows:**

```cmd
python tests/tools/validate_metadata.py --output-folder "C:\StableDiffusion\...\ComfyUI\output\Test"
```

**Linux/macOS:**

```bash
python tests/tools/validate_metadata.py --output-folder "/path/to/ComfyUI/output/Test"
```
- Reads PNG, JPEG, and WebP metadata using Pillow + piexif when available.
- Reconstructs expected metadata straight from each workflow graph (including LoRA stacks, sampler choices, VAE loaders, and filename tokens).
- Flags missing hashes, mismatched prompts, incorrect sampler selection, or fallback paths (e.g., JPEG `com-marker`).
```cmd
python tests/tools/run_dev_workflows.py ^
	--comfyui-path "%COMFYUI_PATH%" ^

timeout /t 120

python tests/tools/validate_metadata.py ^
	--output-folder "%OUTPUT_TEST%"
```

Adjust the wait or swap `timeout` for a smarter queue poller if you need to guarantee completion before validation.

## Advanced Usage

- **Custom suites:** `--workflow-dir "tests/comfyui_cli_tests/dev_test_workflows/flux"` lets you rotate through multiple folders without editing files.
- **Scripted regression packs:** chain several runner invocations in a `.bat` or `.sh` file, toggling `--no-start-server` after the first call to reuse the same ComfyUI session.
- **Remote GPUs:** expose `main.py` via SSH tunnel, then point `--host` at `127.0.0.1` and `--port` at your forwarded socket.

## Troubleshooting

- **Server never starts:** confirm `main.py` exists under `--comfyui-path`, pass the right interpreter via `--python-exe`, and ensure the port is free before retrying.
- **Workflows skipped:** check that each JSON is API format (Dev Mode → Save API). The loader warns when it reads non-dict content.
- **Cleanup skipped:** install `send2trash` or run manual deletes if the dependency is missing; the script intentionally refuses to `rm -rf` by itself.
- **Metadata mismatches:** open the validator log (it tees to stdout + file) to see which field failed. Often it points to mismatched model paths or Save node settings.

## Notes

- `dev_test_workflows/` stays ignored by git so you can store proprietary checkpoints or workflow variants safely.
- The runner only queues jobs; it does not poll for completion. Watch the ComfyUI console for progress or add your own polling if needed.
- Keep `METADATA_TEST_MODE=1` in your environment when you want deterministic hashes that align with CI expectations.
