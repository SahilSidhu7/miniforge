#!/usr/bin/env python3
"""
Miniforge - AI Coding Assistant for Local Models
=================================================
Works with ANY Ollama model. No Claude Code required.
No broken tool calling. The model outputs simple text
commands, Python executes them reliably.

Usage:
    python -m miniforge              # Start interactive REPL
    python -m miniforge /path/to/dir # Start in specific directory
    python -m miniforge --model <name> # Use a different model
    python -m miniforge --config <path> # Use config file
    python -m miniforge /help        # Show help

Requirements:
    pip install requests
    ollama running with any model
"""

import os
import sys
import argparse
from pathlib import Path

# Ensure parent directory is in path for package imports
# This allows the module to work when run as: python -m miniforge
if __name__ == "__main__" and __package__ is None:
    parent = Path(__file__).parent.parent
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))

# Import from local modules
from .core.terminal import cyan, green, yellow, red, bold, dim
from .core.models import ask_model, ConversationContext, should_require_actions
from .ui_module.ui import (
    print_header,
    print_help,
    check_ollama,
    get_ollama_runtime_status,
    print_gpu_status,
    process_response,
)
from .config import Config

VERSION = "2.0.0"

# ── Action format the model must follow ───────────────────────────────────────
SYSTEM_PROMPT = """You are a professional local AI coding assistant. You help users by executing real actions on their computer.

## ACTIONS AVAILABLE (12 total)
bash, create_file, read_file, edit_file, list_dir, delete_file, move_file, copy_dir, find_files, tree, stats

## HOW TO RESPOND

For actionable requests, use action blocks first and do not switch into tutorial mode.
Actionable requests include creating files, editing code, inspecting a project, running commands, scaffolding apps, or verifying changes.
Only answer with plain prose when the user is clearly asking for explanation or advice rather than asking you to do work.

Valid action block format:

<<<ACTION>>>
TYPE: bash
COMMAND: npm install
<<<END>>>

<<<ACTION>>>
TYPE: bash
COMMAND: npm start
DETACH: true
<<<END>>>

<<<ACTION>>>
TYPE: create_file
PATH: index.html
CONTENT:
<!DOCTYPE html>
<body>
  <h1>Hello</h1>
</body>
</html>
<<<END>>>

<<<ACTION>>>
TYPE: read_file
PATH: config.json
<<<END>>>

<<<ACTION>>>
TYPE: edit_file
PATH: app.py
FIND: old_code()
REPLACE: new_code()
<<<END>>>

<<<ACTION>>>
TYPE: tree
PATH: .
<<<END>>>

<<<ACTION>>>
TYPE: stats
PATH: .
<<<END>>>

## RULES
1. Use action blocks for file/system operations
2. Multiple blocks per response (2-10) if needed
3. Verify operations worked
4. After the blocks, add a short plain-language status summary
5. Ask if unsure - don't guess
6. Relative paths: src/file.py
7. Home paths: ~/folder
8. Current dir: .
9. If the user says "make", "create", "build", "edit", "fix", "show", "list", "find", "read", "run", or similar, you must emit at least one action block
10. Never answer actionable requests with numbered instructions unless the user explicitly asked for instructions instead of execution
11. Do not run interactive, long-running, or input-waiting programs unless the user explicitly asked you to run them
12. If the user explicitly asks to run a long-running server or watch command, use TYPE: bash with DETACH: true so it runs in a separate terminal
13. After creating or editing app/code files, prefer stopping after file actions unless the user explicitly asked for execution
14. If the user asks to edit or fix an existing file, read it first when needed and then use edit_file on that file instead of unrelated bash commands
15. If create_file fails because a file exists, switch to read_file or edit_file for that file instead of retrying the same create

## Don't hallucinate commands!"""




# ── Main Loop ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Miniforge - AI Coding Assistant",
        add_help=False  # We handle help ourselves
    )
    parser.add_argument('directory', nargs='?', default=None, help='Working directory')
    parser.add_argument('--model', '-m', default=None, help='Ollama model to use')
    parser.add_argument('--config', '-c', default=None, help='Config file path')
    parser.add_argument('--url', '-u', default=None, help='Ollama API URL')
    parser.add_argument('--help-text', action='store_true', help='Show help and exit')
    
    args = parser.parse_args()
    
    # Load configuration
    config = Config()
    if args.config:
        config.config_path = Path(args.config)
        config._load_config()
    
    # Override config with CLI args
    ollama_url = args.url or config.get('ollama_url')
    model = args.model or config.get('model')
    timeout = config.get('timeout', 300)
    temperature = config.get('temperature', 0.1)
    num_predict = config.get('num_predict', 4096)
    num_ctx = config.get('num_ctx', 4096)
    
    # Determine working directory
    if args.directory:
        if args.directory == '/help':
            print_help()
            return
        work_dir = Path(args.directory).expanduser().resolve()
        if not work_dir.exists():
            print(red(f"[ERROR] Directory not found: {work_dir}"))
            sys.exit(1)
    else:
        work_dir = Path.cwd()
    
    # Change to working directory
    os.chdir(work_dir)
    
    # Show help if requested
    if args.help_text:
        print_help()
        return
    
    print_header(VERSION, model, work_dir, ollama_url)
    
    # check ollama
    if not check_ollama(model, ollama_url):
        sys.exit(1)

    runtime_status = get_ollama_runtime_status(model, ollama_url)
    if runtime_status and runtime_status.get("size_vram", 0) == 0 and num_ctx > 4096:
        print(yellow(f"[INFO] Lowering num_ctx from {num_ctx} to 4096 to help 8 GB GPUs fit the model in VRAM."))
        num_ctx = 4096
    
    print(green("[OK] Ollama connected. Ready!\n"))
    
    context = ConversationContext(max_turns=config.get('max_turns', 8))
    
    while True:
        try:
            # get user input
            print(bold(yellow("You: ")), end="")
            user_input = input().strip()
            
            if not user_input:
                continue
            
            # ── Handle slash commands ────────────────────────────────────────
            if user_input.startswith('/'):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                
                if cmd == '/exit':
                    print(cyan("Goodbye!"))
                    break
                elif cmd == '/help':
                    print_help()
                elif cmd == '/clear':
                    context.clear()
                    print(green("  [OK] Conversation cleared"))
                elif cmd == '/model':
                    if arg:
                        model = arg
                        config.set('model', model)
                        print(green(f"  [OK] Switched to model: {model}"))
                        if not check_ollama(model, ollama_url):
                            print(yellow(f"  Run: ollama pull {model}"))
                    else:
                        print(yellow(f"  Current model: {model}"))
                        print(yellow("  Usage: /model llama3.1:8b"))
                elif cmd == '/dir':
                    if arg:
                        new_dir = Path(arg).expanduser().resolve()
                        if new_dir.exists():
                            work_dir = new_dir
                            os.chdir(work_dir)
                            print(green(f"  [OK] Working directory: {work_dir}"))
                        else:
                            print(red(f"  [ERROR] Directory not found: {new_dir}"))
                    else:
                        print(yellow(f"  Current directory: {work_dir}"))
                elif cmd == '/config':
                    if arg == 'show':
                        print(cyan("Configuration:"))
                        config.show()
                    elif arg == 'save':
                        if config.save():
                            print(green(f"  [OK] Config saved"))
                        else:
                            print(red("  [ERROR] Failed to save config"))
                    else:
                        print(yellow("  Usage: /config show|save"))
                elif cmd == '/gpu':
                    print_gpu_status(model, ollama_url, num_ctx)
                else:
                    print(yellow(f"  Unknown command: {cmd}. Type /help for help."))
                continue
            
            # ── Send to model ────────────────────────────────────────────────
            # add working directory context to first message
            user_msg = user_input
            if not context.messages:
                user_msg = f"[Working directory: {work_dir}]\n\n{user_input}"
            
            context.add_user(user_msg)
            
            print()  # spacing before response
            print(cyan("Assistant: "), end="", flush=True)
            require_actions = should_require_actions(user_input)
            response = ask_model(
                context.get_messages_with_results(), 
                SYSTEM_PROMPT, 
                model, 
                ollama_url,
                timeout=timeout,
                temperature=temperature,
                num_predict=num_predict,
                num_ctx=num_ctx,
                require_actions=require_actions
            )
            
            if response.startswith("ERROR:"):
                print()
                print(red(response))
                context.messages.pop()  # remove failed message
                continue
            
            context.add_assistant(response)
            
            # execute any actions in the response
            work_dir = process_response(response, context, work_dir)
            print()  # spacing after response
            
        except KeyboardInterrupt:
            print(cyan("\n\nType /exit to quit, or keep going!"))
        except EOFError:
            break
        except Exception as e:
            print(red(f"\nUnexpected error: {e}"))


if __name__ == "__main__":
    main()
