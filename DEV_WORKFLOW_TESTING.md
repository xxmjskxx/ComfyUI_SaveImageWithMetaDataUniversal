# Development Workflow Testing Guide

This guide explains how to use the `run_dev_workflows.py` script to test workflows locally without committing them to the repository.

## Overview

The `run_dev_workflows.py` script allows you to:
- Execute multiple ComfyUI workflows from the command line
- Test workflows with local model paths that shouldn't be committed
- Automate workflow testing without using the web UI

## Setup

### 1. Create the Test Script (Local Only)

The script `run_dev_workflows.py` should be created in the root of this custom node pack but is excluded from git via `.gitignore`. You can copy it from the repository history or recreate it as needed.

### 2. Create the Workflow Directory

Create a `dev_test_workflows` folder in the root of this custom node pack:

```
ComfyUI_SaveImageWithMetaDataUniversal/
├── dev_test_workflows/        # Your local test workflows (not committed)
│   ├── test_workflow_1.json
│   ├── test_workflow_2.json
│   └── ...
├── run_dev_workflows.py        # Test runner script (not committed)
├── example_workflows/          # Example workflows (committed)
└── ...
```

### 3. Prepare Workflow Files

Workflows must be in **API JSON format**, not the standard UI format.

To convert workflows to API format:
1. Open ComfyUI web UI
2. Go to Settings → Enable "Dev Mode"
3. Load your workflow
4. Click "Save (API format)" button
5. Save to `dev_test_workflows/` folder

You can use workflows from `example_workflows/` as templates, but update the model paths to match your local environment.

## Usage

### Basic Usage (Windows)

Using the command format from your environment:

```bash
python run_dev_workflows.py ^
  --comfyui-path "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI_windows_portable" ^
  --python-exe "C:\StableDiffusion\StabilityMatrix-win-x64\Data\Packages\ComfyUI_windows_portable\python_embeded\python.exe" ^
  --temp-dir "F:\StableDiffusion\ComfyUI" ^
  --extra-args "--windows-standalone-build"
```

### Basic Usage (Linux/Mac)

```bash
python run_dev_workflows.py --comfyui-path "/path/to/ComfyUI"
```

### Use Existing Running Server

If ComfyUI is already running:

```bash
python run_dev_workflows.py --comfyui-path "." --no-start-server
```

### Keep Server Running After Tests

By default, the script stops the server after execution. To keep it running:

```bash
python run_dev_workflows.py --comfyui-path "/path/to/ComfyUI" --keep-server
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--comfyui-path` | Path to ComfyUI installation (containing main.py) | *Required* |
| `--python-exe` | Path to Python executable | Current Python |
| `--workflow-dir` | Directory containing workflow JSON files | `dev_test_workflows` |
| `--host` | ComfyUI server host | `127.0.0.1` |
| `--port` | ComfyUI server port | `8188` |
| `--temp-dir` | Temporary directory for ComfyUI | None |
| `--extra-args` | Extra arguments to pass to ComfyUI | None |
| `--wait-between` | Seconds to wait between workflow executions | `2.0` |
| `--no-start-server` | Don't start server, assume it's already running | `False` |
| `--keep-server` | Don't stop server after execution | `False` |

## Example Workflows

The `example_workflows/` folder contains sample workflows you can use as templates:

- `flux.json` - FLUX model workflow
- `lora_embedding_vae.json` - Workflow with LoRA, embeddings, and VAE
- `extra_metadata.json` - Using extra metadata nodes
- And more...

Copy these to `dev_test_workflows/` and update model paths for your environment.

## Troubleshooting

### "Server did not start"
- Check that `--comfyui-path` points to the correct directory containing `main.py`
- Verify the Python executable path is correct
- Check if port 8188 is already in use
- Try increasing wait time or starting server manually first

### "Invalid JSON" errors
- Ensure workflows are in API format (not UI format)
- Use "Save (API format)" in ComfyUI Dev Mode
- Validate JSON syntax in a JSON validator

### Workflows not found
- Verify `dev_test_workflows/` folder exists
- Check that workflow files have `.json` extension
- Use `--workflow-dir` to specify a different directory

### Model path errors
- Update model paths in workflows to match your local environment
- Check that models exist at the specified paths
- Verify model file permissions

## Notes

- Both `run_dev_workflows.py` and `dev_test_workflows/` are excluded from git
- This allows you to keep local test workflows with machine-specific paths
- The script only queues workflows; it doesn't wait for completion or check results
- For detailed workflow execution, monitor the ComfyUI server console output
- Workflows are executed sequentially with a 2-second delay between them (configurable)

## Advanced Usage

### Custom Workflow Directory

```bash
python run_dev_workflows.py --comfyui-path "." --workflow-dir "my_custom_tests"
```

### Multiple Environments

Create different workflow folders for different test scenarios:

```
dev_test_workflows/
├── flux_tests/
├── sd15_tests/
└── sdxl_tests/
```

Then run:

```bash
python run_dev_workflows.py --comfyui-path "." --workflow-dir "dev_test_workflows/flux_tests"
```

### Batch Testing

Create a batch file (Windows) or shell script (Linux/Mac) to run multiple test suites:

**test_all.bat (Windows):**
```batch
@echo off
python run_dev_workflows.py --comfyui-path "%COMFYUI_PATH%" --workflow-dir "dev_test_workflows/flux_tests"
python run_dev_workflows.py --comfyui-path "%COMFYUI_PATH%" --workflow-dir "dev_test_workflows/sd15_tests" --no-start-server
```

**test_all.sh (Linux/Mac):**
```bash
#!/bin/bash
python run_dev_workflows.py --comfyui-path "$COMFYUI_PATH" --workflow-dir "dev_test_workflows/flux_tests"
python run_dev_workflows.py --comfyui-path "$COMFYUI_PATH" --workflow-dir "dev_test_workflows/sd15_tests" --no-start-server
```
