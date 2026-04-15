#!/usr/bin/env python3
"""
LocalAgent - AI Coding Assistant for Local Models
==================================================
Works with ANY Ollama model. No Claude Code required.
No broken tool calling. The model outputs simple text
commands, Python executes them reliably.

Usage:
    python localagent.py

Requirements:
    pip install requests
    ollama running with any model
"""

import os
import sys
from pathlib import Path

# Import from local modules
from terminal import cyan, green, yellow, red, bold, dim
from models import ask_model, ConversationContext
from ui import print_header, print_help, check_ollama, process_response

# ── CONFIG (edit these) ────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "qwen2.5-coder:7b"   # any ollama model works
WORK_DIR   = Path(os.getcwd())
VERSION    = "1.0.0"
# ──────────────────────────────────────────────────────────────────────────────

# ── Action format the model must follow ───────────────────────────────────────
SYSTEM_PROMPT = """You are a local AI coding assistant. You help users by executing real actions on their computer.

## HOW TO RESPOND

For every task, you MUST use action blocks to do things. Action blocks look like this:

<<<ACTION>>>
TYPE: bash
COMMAND: mkdir my_folder
<<<END>>>

<<<ACTION>>>
TYPE: create_file
PATH: index.html
CONTENT:
<!DOCTYPE html>
<html>
<body>Hello World</body>
</html>
<<<END>>>

<<<ACTION>>>
TYPE: read_file
PATH: package.json
<<<END>>>

<<<ACTION>>>
TYPE: edit_file
PATH: app.py
FIND: old text here
REPLACE: new text here
<<<END>>>

<<<ACTION>>>
TYPE: list_dir
PATH: .
<<<END>>>

## AVAILABLE ACTION TYPES
- bash: run any terminal command
- create_file: create a new file with content
- read_file: read an existing file
- edit_file: find and replace text in a file
- list_dir: list directory contents
- delete_file: delete a file
- move_file: move/rename a file (add DEST: line)

## RULES
1. ALWAYS use action blocks for any file or system operation
2. You can use multiple action blocks in one response
3. After action blocks, briefly explain what you did
4. If a task needs multiple steps, do them all
5. Keep explanations short and practical
6. If you're unsure about something, ask the user

## IMPORTANT
- Work in the current directory unless told otherwise
- Always verify operations worked
- For bash commands, prefer simple direct commands
- On Windows, use Windows commands (mkdir, dir, copy, etc.)
"""




# ── Main Loop ──────────────────────────────────────────────────────────────────
def main():
    global MODEL, WORK_DIR
    
    print_header(VERSION, MODEL, WORK_DIR, OLLAMA_URL)
    
    # check ollama
    if not check_ollama(MODEL, OLLAMA_URL):
        sys.exit(1)
    
    print(green("✓ Ollama connected. Ready!\n"))
    
    context = ConversationContext(max_turns=8)
    work_dir = WORK_DIR
    
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
                    context = ConversationContext(max_turns=8)
                    print(green("  ✓ Conversation cleared"))
                elif cmd == '/model':
                    if arg:
                        MODEL = arg
                        print(green(f"  ✓ Switched to model: {MODEL}"))
                        if not check_ollama(MODEL, OLLAMA_URL):
                            print(yellow(f"  Run: ollama pull {MODEL}"))
                    else:
                        print(yellow(f"  Current model: {MODEL}"))
                        print(yellow("  Usage: /model llama3.1:8b"))
                elif cmd == '/dir':
                    if arg:
                        new_dir = Path(arg).expanduser().resolve()
                        if new_dir.exists():
                            work_dir = new_dir
                            os.chdir(work_dir)
                            print(green(f"  ✓ Working directory: {work_dir}"))
                        else:
                            print(red(f"  ✗ Directory not found: {new_dir}"))
                    else:
                        print(yellow(f"  Current directory: {work_dir}"))
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
            response = ask_model(context.get_messages_with_results(), SYSTEM_PROMPT, MODEL, OLLAMA_URL)
            
            if response.startswith("ERROR:"):
                print()
                print(red(response))
                context.messages.pop()  # remove failed message
                continue
            
            context.add_assistant(response)
            
            # execute any actions in the response
            process_response(response, context, work_dir)
            print()  # spacing after response
            
        except KeyboardInterrupt:
            print(cyan("\n\nType /exit to quit, or keep going!"))
        except EOFError:
            break

if __name__ == "__main__":
    main()