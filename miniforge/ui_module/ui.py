"""UI functions for Miniforge display and interaction."""

from urllib.parse import urlparse, urlunparse

import requests

from ..core.actions import execute_action, parse_actions
from ..core.terminal import bold, cyan, dim, green, red, yellow


def print_header(version, model, work_dir, ollama_url):
    """Print the Miniforge header."""
    print(bold(cyan("\n==========================================")))
    print(bold(cyan(f"  Miniforge v{version} - AI Coding Tool")))
    print(bold(cyan("==========================================\n")))
    print(dim(f"  Model:    {model}"))
    print(dim(f"  Work dir: {work_dir}"))
    print(dim(f"  Ollama:   {ollama_url}"))
    print(dim("  Commands: /help /model /dir /config /gpu /clear /exit"))
    print()


def print_help():
    """Print help information."""
    print()
    print(cyan("========================================"))
    print(cyan("         Miniforge Help"))
    print(cyan("========================================"))
    print()
    print(cyan("COMMANDS:"))
    print("  /help          - Show this help")
    print("  /model <name>  - Switch Ollama model (e.g. /model llama3.1:8b)")
    print("  /dir <path>    - Change working directory")
    print("  /config show   - Show current configuration")
    print("  /config save   - Save current configuration")
    print("  /gpu           - Show Ollama GPU/VRAM runtime status")
    print("  /clear         - Clear conversation history")
    print("  /exit          - Exit Miniforge")
    print()
    print(cyan("EXAMPLE PROMPTS:"))
    examples = [
        '"create a folder named my-project"',
        '"create an index.html with a navbar and hero section"',
        '"write a python script that reads a CSV and prints it"',
        '"list all files in current directory"',
        '"add a dark mode toggle to style.css"',
        '"create unit tests for my function"',
        '"refactor this code to use async/await"',
    ]
    for example in examples:
            
        print(f"  {example}")
    print()


def check_ollama(model: str, ollama_url: str) -> bool:
    """Check if Ollama is running and the model is available."""
    try:
        parsed = urlparse(ollama_url)
        tags_url = urlunparse((parsed.scheme, parsed.netloc, "/api/tags", "", "", ""))
        resp = requests.get(tags_url, timeout=5)
        resp.raise_for_status()
        models = [item["name"] for item in resp.json().get("models", [])]

        model_base = model.split(":")[0]
        available = any(name.startswith(model_base) for name in models)
        if not available:
            print()
            print(yellow(f"[WARN] Model '{model}' not found."))
            if models:
                print(yellow("Available models:"))
                for name in models[:10]:
                    print(f"   - {name}")
                if len(models) > 10:
                    print(f"   ... and {len(models) - 10} more")
            print(yellow(f"\nTo install: ollama pull {model}"))
            return False
        return True
    except requests.exceptions.ConnectionError:
        print()
        print(red("[ERROR] Cannot connect to Ollama!"))
        print(yellow("Start it with: ollama serve"))
        return False
    except requests.exceptions.Timeout:
        print()
        print(red("[ERROR] Ollama is not responding!"))
        print(yellow("Make sure Ollama is running: ollama serve"))
        return False
    except Exception as e:
        print()
        print(red(f"[ERROR] Error checking Ollama: {e}"))
        return False


def _build_ollama_url(ollama_url: str, path: str) -> str:
    """Build a sibling Ollama API URL from the configured endpoint."""
    parsed = urlparse(ollama_url)
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def get_ollama_runtime_status(model: str, ollama_url: str):
    """Return runtime status for the loaded model from Ollama /api/ps."""
    try:
        resp = requests.get(_build_ollama_url(ollama_url, "/api/ps"), timeout=5)
        resp.raise_for_status()
        models = resp.json().get("models", [])
    except Exception:
        return None

    model_base = model.split(":")[0]
    for item in models:
        name = item.get("name", "")
        if name == model or name.startswith(model_base):
            size = item.get("size") or 0
            size_vram = item.get("size_vram") or 0
            context_length = item.get("context_length")
            if size and size_vram >= size:
                processor = "100% GPU"
            elif size_vram > 0 and size:
                processor = f"{round((size_vram / size) * 100)}% GPU"
            else:
                processor = "100% CPU"
            return {
                "name": name,
                "processor": processor,
                "size": size,
                "size_vram": size_vram,
                "context_length": context_length,
            }
    return None


def print_gpu_status(model: str, ollama_url: str, configured_num_ctx: int):
    """Print a short GPU/runtime summary for the selected model."""
    status = get_ollama_runtime_status(model, ollama_url)
    print(cyan("GPU status:"))

    if not status:
        print(yellow("  No loaded Ollama model found yet. Send one prompt, then run /gpu again."))
        print(dim(f"  Configured context: {configured_num_ctx}"))
        return

    print(dim(f"  Loaded model:       {status['name']}"))
    print(dim(f"  Processor split:    {status['processor']}"))
    print(dim(f"  Loaded into VRAM:   {status['size_vram'] / (1024 ** 3):.2f} GB"))
    print(dim(f"  Total model size:   {status['size'] / (1024 ** 3):.2f} GB"))
    if status["context_length"] is not None:
        print(dim(f"  Active context:     {status['context_length']}"))
    print(dim(f"  Configured context: {configured_num_ctx}"))

    if status["size_vram"] == 0:
        print(yellow("  Ollama is keeping this model on CPU/RAM right now."))
        if configured_num_ctx > 4096:
            print(yellow("  Try lowering num_ctx to 4096 or 2048 so it fits in VRAM on 8 GB GPUs."))
        else:
            print(yellow("  If this stays CPU-only, restart Ollama and confirm CUDA is available."))
    elif status["size_vram"] < status["size"]:
        print(yellow("  The model is only partially offloaded to GPU, so some work is still on CPU/RAM."))
        print(yellow("  Reducing num_ctx can improve full-GPU fit on smaller cards."))
    else:
        print(green("  Ollama is fully using the GPU for this loaded model."))


def process_response(response: str, context, work_dir, verbose: bool = False):
    """Parse and execute all actions in a model response."""
    actions = parse_actions(response)
    if not actions:
        return work_dir

    print()
    print(dim(f" Executing {len(actions)} action{'s' if len(actions) != 1 else ''}..."))
    print()

    success_count = 0
    fail_count = 0
    current_dir = work_dir.resolve()
    root_dir = work_dir.resolve()

    for index, action in enumerate(actions, 1):
        atype = action.get("type", "unknown")
        action_desc = ""

        if atype == "bash":
            action_desc = f"bash: {action.get('command', '')[:50]}"
            if str(action.get("detach", "")).strip().lower() in {"1", "true", "yes", "y", "on"}:
                action_desc += " [detached]"
        elif atype == "create_file":
            action_desc = f"create: {action.get('path', '')}"
        elif atype == "read_file":
            action_desc = f"read: {action.get('path', '')}"
        elif atype == "edit_file":
            action_desc = f"edit: {action.get('path', '')}"
        elif atype == "list_dir":
            action_desc = f"list: {action.get('path', '.')}"
        elif atype == "delete_file":
            action_desc = f"delete: {action.get('path', '')}"
        elif atype == "move_file":
            action_desc = f"move: {action.get('path', '')} -> {action.get('dest', '')}"
        elif atype == "copy_dir":
            action_desc = f"copy: {action.get('path', '')} -> {action.get('dest', '')}"
        elif atype == "find_files":
            action_desc = f"find: {action.get('pattern', '*')} in {action.get('path', '.')}"
        elif atype == "tree":
            action_desc = f"tree: {action.get('path', '.')}"
        elif atype == "stats":
            action_desc = f"stats: {action.get('path', '.')}"

        if action_desc:
            print(dim(f"  [{index}/{len(actions)}] {action_desc}"))

        success, output, current_dir = execute_action(action, current_dir, root_dir)
        if success:
            display_output = output[:100] if len(output) > 100 else output
            print(green(f"       [OK] {display_output}"))
            success_count += 1
            context.add_action_result(atype, output)
        else:
            print(red(f"       [ERROR] {output}"))
            fail_count += 1
            context.add_action_result(atype, f"FAILED: {output}")

    if len(actions) > 1:
        print()
        summary = f"  {success_count} succeeded"
        if fail_count > 0:
            summary += f", {fail_count} failed"
        print(dim(summary))

    return current_dir
