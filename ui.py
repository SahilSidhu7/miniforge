"""UI functions for LocalAgent display and interaction."""

import requests
from terminal import colored, cyan, green, yellow, red, bold, dim
from actions import parse_actions, execute_action


def print_header(version, model, work_dir, ollama_url):
    """Print the LocalAgent header."""
    print(bold(cyan("\n╔══════════════════════════════════════╗")))
    print(bold(cyan(f"║  LocalAgent v{version} - AI Coding Tool  ║")))
    print(bold(cyan("╚══════════════════════════════════════╝")))
    print(dim(f"  Model:    {model}"))
    print(dim(f"  Work dir: {work_dir}"))
    print(dim(f"  Ollama:   {ollama_url}"))
    print(dim("  Commands: /help /model /dir /clear /exit"))
    print()


def print_help():
    """Print help information."""
    print(cyan("\nAvailable commands:"))
    print("  /help          - Show this help")
    print("  /model <name>  - Switch Ollama model (e.g. /model llama3.1:8b)")
    print("  /dir <path>    - Change working directory")
    print("  /clear         - Clear conversation history")
    print("  /exit          - Exit LocalAgent")
    print()
    print(cyan("Example prompts:"))
    print('  "create a folder named my-project"')
    print('  "create an index.html with a navbar and hero section"')
    print('  "write a python script that reads a CSV and prints it"')
    print('  "list all files in current directory"')
    print('  "add a dark mode toggle to style.css"')
    print()


def check_ollama(model, ollama_url):
    """Check if Ollama is running and model is available."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m['name'] for m in resp.json().get('models', [])]
        
        # check if our model is available
        model_base = model.split(':')[0]
        available = any(m.startswith(model_base) for m in models)
        
        if not available:
            print(yellow(f"\n⚠ Model '{model}' not found. Available models:"))
            for m in models:
                print(f"  - {m}")
            print(yellow(f"\nRun: ollama pull {model}"))
            return False
        return True
    except Exception:
        print(red("\n✗ Cannot connect to Ollama!"))
        print(yellow("  Start it with: ollama serve"))
        return False


def process_response(response, context, work_dir):
    """Parse and execute all actions in a model response."""
    actions = parse_actions(response)
    
    if not actions:
        return  # just a text response, nothing to execute
    
    print()  # spacing
    for action in actions:
        atype = action.get('type', 'unknown')
        
        # show what we're doing
        if atype == 'bash':
            print(dim(f"  ⚙ Running: {action.get('command', '')}"))
        elif atype == 'create_file':
            print(dim(f"  📝 Creating: {action.get('path', '')}"))
        elif atype == 'read_file':
            print(dim(f"  📖 Reading: {action.get('path', '')}"))
        elif atype == 'edit_file':
            print(dim(f"  ✏ Editing: {action.get('path', '')}"))
        elif atype == 'list_dir':
            print(dim(f"  📁 Listing: {action.get('path', '.')}"))
        elif atype == 'delete_file':
            print(dim(f"  🗑 Deleting: {action.get('path', '')}"))
        elif atype == 'move_file':
            print(dim(f"  📦 Moving: {action.get('path', '')} → {action.get('dest', '')}"))

        # execute it
        success, output = execute_action(action, work_dir)
        
        if success:
            print(green(f"  ✓ {output[:150]}"))
            context.add_action_result(atype, output)
        else:
            print(red(f"  ✗ {output}"))
            context.add_action_result(atype, f"FAILED: {output}")
