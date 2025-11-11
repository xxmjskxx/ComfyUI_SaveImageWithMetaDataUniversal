#!/usr/bin/env python3
"""
CLI Test Script for Running ComfyUI Workflows

This script executes all workflow JSON files from the 'dev_test_workflows' folder
by queuing them to a running ComfyUI server via the HTTP API.

Usage:
    python run_dev_workflows.py --comfyui-path "path/to/ComfyUI" [options]

Requirements:
    - ComfyUI must be installed and accessible
    - Workflow files must be in API JSON format (not UI format)
    - To convert: Enable Dev Mode in ComfyUI UI, then "Save (API format)"
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from send2trash import send2trash
    SEND2TRASH_AVAILABLE = True
except ImportError:
    SEND2TRASH_AVAILABLE = False


class WorkflowRunner:
    """Handles ComfyUI workflow execution via HTTP API."""

    def __init__(
        self,
        comfyui_path: str,
        python_exe: str | None = None,
        host: str = "127.0.0.1",
        port: int = 8188,
        temp_dir: str | None = None,
        extra_args: list[str] | None = None,
    ):
        self.comfyui_path = Path(comfyui_path).resolve()
        self.python_exe = python_exe or sys.executable
        self.host = host
        self.port = port
        self.temp_dir = temp_dir
        self.extra_args = extra_args or []
        self.server_process = None
        self.base_url = f"http://{host}:{port}"

    def is_server_running(self) -> bool:
        """Check if ComfyUI server is accessible."""
        try:
            req = urllib.request.Request(f"{self.base_url}/system_stats")
            urllib.request.urlopen(req, timeout=2)
            return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            return False

    def start_server(self, wait_time: int = 10) -> bool:
        """Start ComfyUI server in background."""
        if self.is_server_running():
            print(f"✓ ComfyUI server already running at {self.base_url}")
            return True

        main_py = self.comfyui_path / "main.py"
        if not main_py.exists():
            print(f"✗ Error: main.py not found at {main_py}")
            return False

        print(f"Starting ComfyUI server at {self.base_url}...")

        # Build command
        cmd = [self.python_exe, str(main_py), "--listen", self.host, "--port", str(self.port)]

        if self.temp_dir:
            cmd.extend(["--temp-directory", self.temp_dir])

        # Add extra arguments (e.g., --windows-standalone-build)
        cmd.extend(self.extra_args)

        try:
            # Start server in background
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.comfyui_path),
            )

            # Wait for server to start
            print(f"Waiting {wait_time}s for server to start...")
            for i in range(wait_time * 2):  # Check every 0.5s
                time.sleep(0.5)
                if self.is_server_running():
                    print("✓ Server started successfully")
                    return True

            print(f"✗ Server did not start within {wait_time}s")
            return False

        except Exception as e:
            print(f"✗ Failed to start server: {e}")
            return False

    def stop_server(self):
        """Stop the ComfyUI server if started by this script."""
        if self.server_process:
            print("Stopping ComfyUI server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
                print("✓ Server stopped")
            except subprocess.TimeoutExpired:
                print("⚠ Server did not stop gracefully, killing...")
                self.server_process.kill()
                self.server_process.wait()

    def queue_workflow(self, workflow: dict) -> tuple[bool, str]:
        """Queue a workflow to the ComfyUI server."""
        try:
            data = json.dumps({"prompt": workflow}).encode("utf-8")
            req = urllib.request.Request(f"{self.base_url}/prompt", data=data)
            req.add_header("Content-Type", "application/json")

            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                prompt_id = result.get("prompt_id", "unknown")
                return True, prompt_id

        except Exception as e:
            return False, str(e)

    def load_workflow(self, workflow_path: Path) -> dict | None:
        """Load and validate a workflow JSON file."""
        try:
            with open(workflow_path, encoding="utf-8") as f:
                workflow = json.load(f)

            # Basic validation - check if it's API format
            if not isinstance(workflow, dict):
                print(f"  ⚠ Warning: {workflow_path.name} is not a dict, might not be API format")

            return workflow

        except json.JSONDecodeError as e:
            print(f"  ✗ Error: Invalid JSON in {workflow_path.name}: {e}")
            return None
        except Exception as e:
            print(f"  ✗ Error loading {workflow_path.name}: {e}")
            return None

    def clean_output_folder(self, output_path: Path) -> bool:
        """Clean the output folder by moving files to recycle bin."""
        if not output_path.exists():
            print(f"⚠ Output folder does not exist: {output_path}")
            print("  (It will be created when workflows run)")
            return True

        if not SEND2TRASH_AVAILABLE:
            print("⚠ Warning: send2trash not installed. Cannot clean output folder.")
            print("  Install with: pip install send2trash")
            return False

        print(f"Cleaning output folder: {output_path}")

        # Get all files and folders in the directory
        items = list(output_path.iterdir())

        if not items:
            print("  ✓ Output folder is already empty")
            return True

        moved_count = 0
        error_count = 0

        for item in items:
            try:
                send2trash(str(item))
                moved_count += 1
                print(f"  ✓ Moved to recycle bin: {item.name}")
            except Exception as e:
                print(f"  ✗ Failed to move {item.name}: {e}")
                error_count += 1

        print(f"  Summary: {moved_count} items moved, {error_count} errors")
        return error_count == 0

    def run_workflows(self, workflow_dir: Path, wait_between: float = 2.0) -> tuple[int, int]:
        """Run all workflows in the specified directory."""
        if not workflow_dir.exists():
            print(f"✗ Error: Directory not found: {workflow_dir}")
            return 0, 0

        # Find all JSON files
        workflow_files = sorted(workflow_dir.glob("*.json"))

        if not workflow_files:
            print(f"⚠ No workflow files found in {workflow_dir}")
            return 0, 0

        print(f"\nFound {len(workflow_files)} workflow(s) to execute:\n")

        success_count = 0
        fail_count = 0

        for workflow_file in workflow_files:
            print(f"Processing: {workflow_file.name}")

            # Load workflow
            workflow = self.load_workflow(workflow_file)
            if workflow is None:
                fail_count += 1
                continue

            # Queue workflow
            success, result = self.queue_workflow(workflow)

            if success:
                print(f"  ✓ Queued successfully (prompt_id: {result})")
                success_count += 1
            else:
                print(f"  ✗ Failed to queue: {result}")
                fail_count += 1

            # Wait between workflows
            if wait_between > 0 and workflow_file != workflow_files[-1]:
                time.sleep(wait_between)

        return success_count, fail_count


def main():
    parser = argparse.ArgumentParser(
        description="Run ComfyUI workflows from dev_test_workflows folder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Windows with full paths and output folder cleanup
  python run_dev_workflows.py --comfyui-path "C:\\StableDiffusion\\ComfyUI" ^
    --python-exe "C:\\StableDiffusion\\python_embeded\\python.exe" ^
    --temp-dir "F:\\StableDiffusion\\ComfyUI" --extra-args "--windows-standalone-build" ^
    --output-folder "C:\\StableDiffusion\\StabilityMatrix-win-x64\\Data\\Packages\\ComfyUI\\output\\Test"

  # Linux/Mac (simpler)
  python run_dev_workflows.py --comfyui-path "/path/to/ComfyUI"

  # Use existing running server
  python run_dev_workflows.py --comfyui-path "." --no-start-server
        """,
    )

    parser.add_argument(
        "--comfyui-path",
        type=str,
        required=True,
        help="Path to ComfyUI installation (containing main.py)",
    )

    parser.add_argument(
        "--python-exe",
        type=str,
        help="Path to Python executable (default: current Python interpreter)",
    )

    parser.add_argument(
        "--workflow-dir",
        type=str,
        default="dev_test_workflows",
        help="Directory containing workflow JSON files (default: dev_test_workflows)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="ComfyUI server host (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8188,
        help="ComfyUI server port (default: 8188)",
    )

    parser.add_argument(
        "--temp-dir",
        type=str,
        help="Temporary directory for ComfyUI (passed as --temp-directory)",
    )

    parser.add_argument(
        "--extra-args",
        type=str,
        help='Extra arguments to pass to ComfyUI (e.g., "--windows-standalone-build --cpu")',
    )

    parser.add_argument(
        "--wait-between",
        type=float,
        default=2.0,
        help="Seconds to wait between workflow executions (default: 2.0)",
    )

    parser.add_argument(
        "--no-start-server",
        action="store_true",
        help="Don't start server, assume it's already running",
    )

    parser.add_argument(
        "--keep-server",
        action="store_true",
        help="Don't stop server after execution (only if started by this script)",
    )

    parser.add_argument(
        "--output-folder",
        type=str,
        help="Path to ComfyUI output Test folder to clean before running workflows",
    )

    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Skip cleaning the output folder before running workflows",
    )

    args = parser.parse_args()

    # Convert workflow_dir to absolute path relative to script location
    script_dir = Path(__file__).parent
    workflow_dir = script_dir / args.workflow_dir

    # Parse extra args
    extra_args = args.extra_args.split() if args.extra_args else []

    # Create runner
    runner = WorkflowRunner(
        comfyui_path=args.comfyui_path,
        python_exe=args.python_exe,
        host=args.host,
        port=args.port,
        temp_dir=args.temp_dir,
        extra_args=extra_args,
    )

    print("=" * 70)
    print("ComfyUI Workflow Test Runner")
    print("=" * 70)
    print(f"ComfyUI Path: {runner.comfyui_path}")
    print(f"Python Exe:   {runner.python_exe}")
    print(f"Server:       {runner.base_url}")
    print(f"Workflow Dir: {workflow_dir}")
    print("=" * 70)

    try:
        # Clean output folder if requested
        if args.output_folder and not args.no_clean:
            output_path = Path(args.output_folder)
            print("\n" + "=" * 70)
            if not runner.clean_output_folder(output_path):
                print("⚠ Warning: Output folder cleanup had errors, continuing anyway...")
            print("=" * 70 + "\n")

        # Start server if needed
        if not args.no_start_server:
            if not runner.start_server():
                print("\n✗ Failed to start server, exiting")
                return 1
        else:
            if not runner.is_server_running():
                print(f"\n✗ Server not running at {runner.base_url}, exiting")
                return 1
            print(f"✓ Using existing server at {runner.base_url}")

        # Run workflows
        success, fail = runner.run_workflows(workflow_dir, args.wait_between)

        # Print summary
        print("\n" + "=" * 70)
        print("Summary:")
        print(f"  ✓ Successful: {success}")
        print(f"  ✗ Failed:     {fail}")
        print(f"  Total:        {success + fail}")
        print("=" * 70)

        return 0 if fail == 0 else 1

    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        return 1

    finally:
        # Stop server if we started it
        if not args.no_start_server and not args.keep_server:
            runner.stop_server()


if __name__ == "__main__":
    sys.exit(main())
