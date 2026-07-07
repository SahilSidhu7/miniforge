# Miniforge

Miniforge is a small command-line AI coding assistant that runs against a local Ollama model.
It sends your prompt to the model, looks for structured action blocks in the reply, and then executes those actions in the current working directory.

## What This Project Contains

```
miniforge/
|-- miniforge/
|   |-- __main__.py        # CLI entry point
|   |-- config.py          # Config loading and saving
|   |-- utils.py           # Small helper functions
|   |-- core/
|   |   |-- models.py      # Ollama requests and conversation logic
|   |   |-- actions.py     # Parse and execute action blocks
|   |   `-- terminal.py    # Terminal colors
|   `-- ui_module/
|       `-- ui.py          # Terminal output helpers
|-- tests/                 # Basic regression tests
|-- setup.cfg              # Package metadata
|-- setup.py               # Minimal setuptools shim
`-- README.md
```

## Requirements

- Python 3.8+
- Ollama running locally
- An installed Ollama model, for example `qwen2.5-coder:7b`

Install the Python dependency:

```bash
pip install requests
```

## Install

For development:

```bash
pip install -e .
```

For a normal install:

```bash
pip install .
```

## Run

From the current directory:

```bash
miniforge
```

In a specific project directory:

```bash
miniforge /path/to/project
```

Or run directly from source:

```bash
python -m miniforge
```

## Commands

- `/help`
- `/model <name>`
- `/dir <path>`
- `/config show`
- `/config save`
- `/gpu`
- `/clear`
- `/exit`

## GPU Notes

Miniforge sends requests to Ollama; Ollama decides whether the model runs on CPU or GPU.
The default `num_ctx` is tuned to `4096` so 7B coding models are more likely to fit on 8 GB GPUs such as an RTX 4060.

To verify the active offload split after your first prompt:

```bash
miniforge
/gpu
```

## Main Actions

The model can return these action types:

- `bash`
- `create_file`
- `read_file`
- `edit_file`
- `list_dir`
- `delete_file`
- `move_file`
- `copy_dir`
- `find_files`
- `tree`
- `stats`

## Example Prompts

```text
create an index.html with a navbar
make a React calculator
list all files in the current directory
find all Python files
show the project tree
```

## Test

```bash
python -m unittest discover -s tests -p "test_*.py"
```
