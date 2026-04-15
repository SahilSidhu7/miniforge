# LocalAgent - AI Coding Assistant for Local Models

A powerful AI coding assistant that runs locally using Ollama models. No cloud dependencies, no API keys, no subscriptions—just pure local intelligence helping you code faster.

## 🎯 Overview

LocalAgent is a command-line AI assistant that understands natural language and executes real file operations on your computer. Ask it to "create an HTML file with a navbar," "write a Python script to process CSV files," or "organize my project folder," and it will do exactly that.

The key innovation: **The AI outputs simple, structured commands that Python executes reliably**—no broken tool-calling, no hallucinations of commands that don't exist.

## ✨ Key Features

- **Works with ANY Ollama model** — Qwen, Llama, Mistral, or any model you have installed
- **Local execution only** — Your code stays on your computer; nothing goes to external servers
- **7 built-in actions** — Create files, read files, edit files, run bash commands, list directories, delete files, move files
- **Real-time streaming** — Watch the AI think in real-time as it generates responses
- **Conversation memory** — Maintains context across multiple interactions
- **Simple command system** — `/help`, `/model`, `/dir`, `/clear`, `/exit`
- **No dependencies** — Just Python and the `requests` library

## 📦 Project Structure

```
MiniForgeV2/
├── localagent.py        # Entry point, configuration, main REPL loop
├── terminal.py          # Color utilities for terminal output
├── actions.py           # Action parsing and execution engine
├── models.py            # Ollama API communication and conversation state
├── ui.py                # User interface functions (headers, help, etc.)
└── README.md            # This file
```

### Architecture Explanation

The codebase is organized into **5 logical modules** for clarity and maintainability:

| Module | Responsibility | Key Functions |
|--------|-----------------|--|
| **localagent.py** | Entry point, config, main loop | `main()`, REPL, command handlers |
| **terminal.py** | Terminal styling | `cyan()`, `green()`, `red()`, `bold()`, `dim()` |
| **actions.py** | Parse & execute file operations | `parse_actions()`, `execute_action()` |
| **models.py** | Ollama API communication | `ask_model()`, `ConversationContext` |
| **ui.py** | User interface display | `print_header()`, `print_help()`, `process_response()` |

This modular design makes the code easy to understand, edit, and extend.

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Ollama running locally (https://ollama.ai)
- An Ollama model installed (e.g., `ollama pull qwen2.5-coder:7b`)

### Installation

1. **Clone or download this project:**
   ```bash
   cd MiniForgeV2
   ```

2. **Install the required Python package:**
   ```bash
   pip install requests
   ```

3. **Ensure Ollama is running:**
   ```bash
   ollama serve
   ```
   (Run this in a separate terminal)

4. **Start LocalAgent:**
   ```bash
   python localagent.py
   ```

## 💬 Usage Guide

### Starting the Assistant

```bash
python localagent.py
```

You'll see:
```
╔══════════════════════════════════════╗
║  LocalAgent v1.0.0 - AI Coding Tool  ║
╚══════════════════════════════════════╝
  Model:    qwen2.5-coder:7b
  Work dir: /home/user/projects
  Ollama:   http://localhost:11434/api/generate
  Commands: /help /model /dir /clear /exit

✓ Ollama connected. Ready!

You:
```

### Example Prompts

Try any of these commands:

```
You: create a folder structure for a web project with html, css, js folders
You: create an index.html with a bootstrap navbar and hero section
You: write a python script that reads a CSV file and prints it as a table
You: create a .gitignore file for a Python project
You: list all files in the current directory
You: edit index.html and add a footer
You: create a README.md file with project documentation
```

### Built-in Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `/help` | Show available commands and examples | `/help` |
| `/model <name>` | Switch to a different Ollama model | `/model llama3.1:8b` |
| `/dir <path>` | Change working directory | `/dir ~/Desktop` |
| `/clear` | Clear conversation history | `/clear` |
| `/exit` | Exit the program | `/exit` |

## 🔧 How It Works

### The Action System

LocalAgent uses a **structured action format** to execute tasks:

```
<<<ACTION>>>
TYPE: create_file
PATH: index.html
CONTENT:
<!DOCTYPE html>
<html>
<body>Hello World</body>
</html>
<<<END>>>
```

The AI generates these action blocks, and Python parses and executes them reliably.

### Supported Actions

| Action | Purpose |
|--------|---------|
| `bash` | Run terminal commands (mkdir, npm install, python script.py, etc.) |
| `create_file` | Create a new file with content |
| `read_file` | Read and display file contents |
| `edit_file` | Find and replace text in existing files |
| `list_dir` | Show directory contents (files & folders) |
| `delete_file` | Delete a file or folder |
| `move_file` | Move or rename files/folders |

### Conversation Flow

1. **User enters a prompt** → "create an index.html file"
2. **LocalAgent sends prompt to Ollama model** → Model understands the request
3. **Model generates action blocks** → Structured commands to execute
4. **LocalAgent parses actions** → Extracts TYPE, PATH, CONTENT, etc.
5. **Python executes actions** → Creates, reads, edits files
6. **Results sent back to model** → "Done! I created index.html with 150 lines"
7. **Loop continues** → User can ask follow-up questions

## 🎓 Learning Outcomes

Building this project demonstrates several important computer science concepts:

### 1. **Software Architecture**
   - Modular design with clear separation of concerns
   - Each module has a single responsibility
   - Import flow: `localagent.py` → `ui.py` → `actions.py` & `terminal.py`

### 2. **API Integration**
   - HTTP REST API calls using the `requests` library
   - Streaming responses (real-time token generation)
   - Error handling and timeouts

### 3. **Parsing & Parsing**
   - Regular expressions to extract action blocks
   - Parsing structured text format (`<<<ACTION>>>...<<<END>>>`)
   - Handling edge cases (multiline content, special characters)

### 4. **State Management**
   - Conversation context tracking with message history
   - Trimming old messages to keep context size manageable
   - Action result logging for context injection

### 5. **File System Operations**
   - Reading/writing files in Python (path management)
   - Directory operations (listing, creating, deleting)
   - Error handling (file not found, permission denied, etc.)

### 6. **Process Execution**
   - Running shell commands from Python (`subprocess`)
   - Capturing stdout/stderr output
   - Timeout handling for long-running processes

### 7. **User Interface**
   - ANSI color codes for terminal styling
   - Command-line REPL (Read-Eval-Print Loop)
   - User input validation and command parsing

### 8. **Concurrency Concepts**
   - Streaming requests (iterating over response chunks)
   - Buffering and output management
   - Real-time feedback to users

## 🔐 Security Considerations

- **Local execution only** — No data sent to external servers
- **Command validation** — All bash commands are explicitly executed by the user's request
- **Timeout protection** — Commands abort after 60 seconds
- **Path validation** — File operations are restricted to the working directory
- **No arbitrary code execution** — The AI can't run Python directly; it uses only the 7 predefined actions

## 🎯 Use Cases

1. **Student Projects** — Quickly scaffold project structures and generate boilerplate code
2. **Rapid Prototyping** — Create HTML/CSS/JS mockups instantly
3. **File Management** — Organize projects, create folder structures
4. **Script Generation** — Write small Python/bash scripts through conversation
5. **Documentation** — Generate README files, code comments, etc.
6. **Learning** — Understand how AI integration and file operations work

## 📊 Technical Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.8+ |
| **AI Runtime** | Ollama (any model supported) |
| **HTTP Client** | `requests` library |
| **Command Execution** | `subprocess` module |
| **File System** | `pathlib` module |
| **Parsing** | Regular expressions |
| **Styling** | ANSI color codes |

## 🛠️ Customization

### Changing the Default Model

Edit `localagent.py`:
```python
MODEL = "qwen2.5-coder:7b"  # Change this to any Ollama model
```

Then restart and use `/model qwen2.5-coder:1.5b` at runtime.

### Changing the Working Directory

Use the `/dir` command at runtime:
```
You: /dir ~/my-projects
✓ Working directory: /home/user/my-projects
```

### Adjusting Conversation Context

Edit `localagent.py`:
```python
context = ConversationContext(max_turns=8)  # Increase for longer conversations
```

## 📈 Future Enhancements

Possible improvements for this project:

- [ ] Support for image generation/viewing
- [ ] Plugin system for custom action types
- [ ] Conversation history persistence (save/load chats)
- [ ] Web UI instead of CLI
- [ ] Support for multiple AI models in parallel
- [ ] Code syntax highlighting in terminal
- [ ] Undo/redo functionality
- [ ] Integration with git (commit, branch operations)
- [ ] Unit tests for action execution
- [ ] Logging system for debugging

## 🐛 Troubleshooting

### "Cannot connect to Ollama"
- Ensure Ollama is running: `ollama serve` in another terminal
- Check the URL: default is `http://localhost:11434`

### "Model not found"
- Pull the model: `ollama pull qwen2.5-coder:7b`
- Or switch to an available model: `/model llama2`

### "Permission denied" when editing files
- Ensure you have write permissions in the working directory
- Try changing to a different directory: `/dir ~/Desktop`

### Response is slow
- You may be using a large model (7B, 13B parameters)
- Try a smaller model: `ollama pull mistral:7b`
- Or run on a more powerful machine

## 📚 References & Resources

- **Ollama Documentation**: https://github.com/ollama/ollama
- **Available Models**: https://ollama.ai/library
- **Python Requests Library**: https://docs.python-requests.org/
- **Python subprocess Module**: https://docs.python.org/3/library/subprocess.html
- **Regular Expressions in Python**: https://docs.python.org/3/library/re.html

## 👨‍🏫 For Teachers

This project is excellent for teaching:

1. **Software Engineering** — Modular design, separation of concerns
2. **API Integration** — HTTP requests, streaming responses, error handling
3. **File I/O** — Reading, writing, and manipulating files
4. **Process Management** — Running external commands safely
5. **State Management** — Conversation history, context trimming
6. **Error Handling** — Try-catch, validation, graceful degradation

Students can extend this project by:
- Adding new action types
- Building a web UI
- Implementing persistence
- Adding unit tests
- Creating a plugin system

## 📄 License

This project is provided as-is for educational purposes.

---

**Questions?** Ask the LocalAgent itself! It's quite helpful. 😊

```
You: how do I create a Python virtual environment?
Assistant: I'll create a comprehensive guide for you...
```
