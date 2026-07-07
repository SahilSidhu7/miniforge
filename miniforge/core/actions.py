"""Action parsing and execution for Miniforge."""

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from ..utils import create_tree, find_files, get_project_stats

ACTION_KEYS = {
    "TYPE",
    "COMMAND",
    "PATH",
    "DEST",
    "FIND",
    "REPLACE",
    "CONTENT",
    "PATTERN",
    "DETACH",
}
MULTILINE_KEYS = {"CONTENT", "FIND", "REPLACE"}
LONG_RUNNING_COMMAND_RE = re.compile(
    r"\b("
    r"npm\s+(start|run\s+(dev|start|serve|watch))|"
    r"yarn\s+(start|dev|serve|watch)|"
    r"pnpm\s+(start|dev|serve|watch)|"
    r"vite(\s|$)|"
    r"next\s+dev|"
    r"nuxt(\s+dev)?|"
    r"ng\s+serve|"
    r"python\s+-m\s+http\.server|"
    r"python\s+manage\.py\s+runserver|"
    r"flask\s+run|"
    r"uvicorn\b|"
    r"gunicorn\b|"
    r"docker\s+compose\s+up"
    r")\b",
    re.IGNORECASE,
)


def _safe_path(path_str: str, current_dir: Path, root_dir: Optional[Path] = None) -> Tuple[Path, str]:
    """Resolve a path from the current directory and prevent escaping the workspace root."""
    if not path_str or not path_str.strip():
        return None, "Path is empty"

    try:
        current_dir = current_dir.resolve()
        root_dir = root_dir.resolve() if root_dir else current_dir
        raw_path = Path(path_str).expanduser()
        resolved = raw_path.resolve() if raw_path.is_absolute() else (current_dir / raw_path).resolve()
        resolved.relative_to(root_dir)
        return resolved, ""
    except ValueError:
        return None, f"Path escapes working directory: {path_str}"
    except Exception as e:
        return None, str(e)


def _is_binary_file(path: Path) -> bool:
    """Check if a file looks binary."""
    try:
        with open(path, "rb") as file:
            return b"\x00" in file.read(8192)
    except OSError:
        return False


def _handle_cd_command(command: str, current_dir: Path, root_dir: Path):
    """Handle a simple `cd target` command as a persistent directory change."""
    match = re.fullmatch(r'\s*cd(?:\s+/d)?\s+(.+?)\s*', command, re.IGNORECASE)
    if not match:
        return None

    target_text = match.group(1).strip()
    if (target_text.startswith('"') and target_text.endswith('"')) or (
        target_text.startswith("'") and target_text.endswith("'")
    ):
        target_text = target_text[1:-1]

    target_path, err = _safe_path(target_text, current_dir, root_dir)
    if err:
        return False, f"Invalid path: {err}", current_dir
    if not target_path.exists():
        return False, f"Directory not found: {target_text}", current_dir
    if not target_path.is_dir():
        return False, f"Not a directory: {target_text}", current_dir

    return True, f"Current directory: {target_path}", target_path


def _is_truthy(value) -> bool:
    """Interpret common string values as booleans."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _should_detach_command(command: str, action) -> bool:
    """Detect commands that should run in a separate terminal."""
    return _is_truthy(action.get("detach")) or bool(LONG_RUNNING_COMMAND_RE.search(command))


def _launch_in_terminal(command: str, current_dir: Path) -> Tuple[bool, str]:
    """Launch a command in a separate terminal window without blocking."""
    system = platform.system()

    try:
        if system == "Windows":
            comspec = os.environ.get("COMSPEC", "cmd.exe")
            creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            process = subprocess.Popen(
                [comspec, "/k", command],
                cwd=str(current_dir),
                creationflags=creationflags,
            )
            return True, f"Started in new terminal (PID {process.pid})"

        if system == "Darwin":
            escaped_dir = str(current_dir).replace("\\", "\\\\").replace('"', '\\"')
            escaped_cmd = command.replace("\\", "\\\\").replace('"', '\\"')
            script = (
                'tell application "Terminal" to do script '
                f'"cd \\"{escaped_dir}\\"; {escaped_cmd}"'
            )
            process = subprocess.Popen(["osascript", "-e", script], cwd=str(current_dir))
            return True, f"Started in Terminal.app (PID {process.pid})"

        terminal_candidates = (
            ("x-terminal-emulator", "-e"),
            ("gnome-terminal", "--"),
            ("konsole", "-e"),
            ("xfce4-terminal", "-e"),
            ("xterm", "-e"),
        )
        for executable, flag in terminal_candidates:
            terminal_path = shutil.which(executable)
            if not terminal_path:
                continue

            process = subprocess.Popen(
                [terminal_path, flag, "sh", "-lc", command],
                cwd=str(current_dir),
            )
            return True, f"Started in {Path(terminal_path).name} (PID {process.pid})"

        process = subprocess.Popen(
            command,
            shell=True,
            cwd=str(current_dir),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True, f"Started in background without terminal (PID {process.pid})"
    except Exception as e:
        return False, f"Detached launch failed: {e}"


def parse_actions(text):
    """Extract all action blocks from model response."""
    actions = []
    matches = re.findall(r"<<<ACTION>>>(.*?)<<<END>>>", text, re.DOTALL)

    for match in matches:
        action = {}
        current_key = None
        buffer = []

        def flush_buffer():
            nonlocal current_key, buffer
            if current_key:
                action[current_key.lower()] = "\n".join(buffer).rstrip("\n")
            current_key = None
            buffer = []

        for line in match.strip().splitlines():
            if line.strip().startswith("```"):
                continue

            key, sep, value = line.partition(":")
            normalized_key = key.strip().upper()

            if sep and normalized_key in ACTION_KEYS:
                flush_buffer()
                cleaned_value = value.lstrip()

                if normalized_key == "TYPE":
                    action["type"] = cleaned_value.strip().lower()
                elif normalized_key in MULTILINE_KEYS:
                    current_key = normalized_key
                    if cleaned_value:
                        buffer.append(cleaned_value)
                else:
                    action[normalized_key.lower()] = cleaned_value.strip()
            elif current_key:
                buffer.append(line)

        flush_buffer()

        if "type" in action:
            actions.append(action)

    return actions


def execute_action(action, current_dir, root_dir=None):
    """Execute a single parsed action. Returns (success, output, next_dir)."""
    atype = action.get("type", "")
    current_dir = current_dir.resolve()
    root_dir = root_dir.resolve() if root_dir else current_dir

    try:
        if atype == "bash":
            cmd = action.get("command", "")
            if not cmd.strip():
                return False, "No command provided", current_dir

            cd_result = _handle_cd_command(cmd, current_dir, root_dir)
            if cd_result is not None:
                return cd_result

            try:
                if _should_detach_command(cmd, action):
                    success, output = _launch_in_terminal(cmd, current_dir)
                    return success, output, current_dir

                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=str(current_dir),
                    timeout=60,
                )
                output = result.stdout.strip() or result.stderr.strip() or "(completed)"
                return result.returncode == 0, output, current_dir
            except subprocess.TimeoutExpired:
                return False, "Command timed out (60s limit)", current_dir
            except Exception as e:
                return False, f"Bash error: {e}", current_dir

        elif atype == "create_file":
            path_str = action.get("path", "")
            if not path_str:
                return False, "No path provided", current_dir

            path, err = _safe_path(path_str, current_dir, root_dir)
            if err:
                return False, f"Invalid path: {err}", current_dir

            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists() and path.is_file():
                    return False, f"File already exists: {path.name}", current_dir

                path.write_text(action.get("content", ""), encoding="utf-8")
                return True, f"Created {path.name}", current_dir
            except PermissionError:
                return False, f"Permission denied: cannot write to {path.parent}", current_dir
            except Exception as e:
                return False, f"Create failed: {e}", current_dir

        elif atype == "read_file":
            path_str = action.get("path", "")
            if not path_str:
                return False, "No path provided", current_dir

            path, err = _safe_path(path_str, current_dir, root_dir)
            if err:
                return False, f"Invalid path: {err}", current_dir
            if not path.exists():
                return False, f"File not found: {path.name}", current_dir
            if path.is_dir():
                return False, f"Is a directory, not a file: {path.name}", current_dir

            try:
                if _is_binary_file(path):
                    return False, f"Binary file (cannot read): {path.name}", current_dir

                content = path.read_text(encoding="utf-8")
                if len(content) > 5000:
                    content = content[:5000] + "\n\n... (file truncated at 5000 chars)"
                return True, content, current_dir
            except UnicodeDecodeError:
                return False, f"Cannot decode file (not UTF-8): {path.name}", current_dir
            except Exception as e:
                return False, f"Read failed: {e}", current_dir

        elif atype == "edit_file":
            path_str = action.get("path", "")
            if not path_str:
                return False, "No path provided", current_dir

            path, err = _safe_path(path_str, current_dir, root_dir)
            if err:
                return False, f"Invalid path: {err}", current_dir
            if not path.exists():
                return False, f"File not found: {path.name}", current_dir
            if path.is_dir():
                return False, f"Is a directory: {path.name}", current_dir

            try:
                find = action.get("find", "")
                replace = action.get("replace", "")
                if not find:
                    return False, "No FIND text provided", current_dir

                content = path.read_text(encoding="utf-8")
                if find not in content:
                    preview = content[:200].replace("\n", "\\n")
                    return False, f"Text not found in file (preview: {preview}...)", current_dir

                new_content = content.replace(find, replace, 1)
                if new_content == content:
                    return False, "Edit produced no change", current_dir

                path.write_text(new_content, encoding="utf-8")
                return True, f"Edited {path.name}", current_dir
            except UnicodeDecodeError:
                return False, f"Cannot decode file (not UTF-8): {path.name}", current_dir
            except Exception as e:
                return False, f"Edit failed: {e}", current_dir

        elif atype == "list_dir":
            path_str = action.get("path", ".")
            path, err = _safe_path(path_str, current_dir, root_dir)
            if err:
                return False, f"Invalid path: {err}", current_dir
            if not path.exists():
                return False, f"Directory not found: {path_str}", current_dir
            if not path.is_dir():
                return False, f"Not a directory: {path_str}", current_dir

            try:
                lines = []
                for item in sorted(path.iterdir()):
                    try:
                        if item.is_dir():
                            lines.append(f"[DIR]  {item.name}/")
                        else:
                            size = item.stat().st_size
                            if size < 1024:
                                size_str = f"{size}B"
                            elif size < 1024 * 1024:
                                size_str = f"{size / 1024:.1f}KB"
                            else:
                                size_str = f"{size / (1024 * 1024):.1f}MB"
                            lines.append(f"[FILE] {item.name} ({size_str})")
                    except OSError:
                        lines.append(f"? {item.name}")
                return True, "\n".join(lines) if lines else "(empty directory)", current_dir
            except PermissionError:
                return False, f"Permission denied: {path.name}", current_dir
            except Exception as e:
                return False, f"List failed: {e}", current_dir

        elif atype == "delete_file":
            path_str = action.get("path", "")
            if not path_str:
                return False, "No path provided", current_dir

            path, err = _safe_path(path_str, current_dir, root_dir)
            if err:
                return False, f"Invalid path: {err}", current_dir
            if not path.exists():
                return False, f"Not found: {path_str}", current_dir

            try:
                if path.is_dir():
                    shutil.rmtree(path)
                    return True, f"Deleted directory: {path.name}", current_dir
                path.unlink()
                return True, f"Deleted file: {path.name}", current_dir
            except PermissionError:
                return False, f"Permission denied: {path.name}", current_dir
            except Exception as e:
                return False, f"Delete failed: {e}", current_dir

        elif atype == "move_file":
            src_str = action.get("path", "")
            dest_str = action.get("dest", "")
            if not src_str or not dest_str:
                return False, "PATH and DEST both required", current_dir

            src, err = _safe_path(src_str, current_dir, root_dir)
            if err:
                return False, f"Invalid source path: {err}", current_dir
            dest, err = _safe_path(dest_str, current_dir, root_dir)
            if err:
                return False, f"Invalid dest path: {err}", current_dir
            if not src.exists():
                return False, f"Source not found: {src_str}", current_dir

            if dest.exists() and dest.is_dir():
                dest = dest / src.name

            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))
                return True, f"Moved {src.name} -> {dest.name}", current_dir
            except PermissionError:
                return False, f"Permission denied: cannot move to {dest.parent.name}", current_dir
            except Exception as e:
                return False, f"Move failed: {e}", current_dir

        elif atype == "copy_dir":
            src_str = action.get("path", "")
            dest_str = action.get("dest", "")
            if not src_str or not dest_str:
                return False, "PATH and DEST both required", current_dir

            src, err = _safe_path(src_str, current_dir, root_dir)
            if err:
                return False, f"Invalid source: {err}", current_dir
            dest, err = _safe_path(dest_str, current_dir, root_dir)
            if err:
                return False, f"Invalid dest: {err}", current_dir
            if not src.exists():
                return False, f"Source not found: {src_str}", current_dir
            if not src.is_dir():
                return False, f"Source is not a directory: {src_str}", current_dir

            try:
                shutil.copytree(str(src), str(dest), dirs_exist_ok=False)
                return True, f"Copied {src.name} -> {dest.name}", current_dir
            except FileExistsError:
                return False, f"Destination already exists: {dest_str}", current_dir
            except Exception as e:
                return False, f"Copy failed: {e}", current_dir

        elif atype == "find_files":
            search_dir = action.get("path", ".")
            pattern = action.get("pattern", "*")
            path, err = _safe_path(search_dir, current_dir, root_dir)
            if err:
                return False, f"Invalid path: {err}", current_dir
            if not path.exists():
                return False, f"Directory not found: {search_dir}", current_dir

            try:
                files = find_files(path, pattern, recursive=True)
                if not files:
                    return True, "(no files found)", current_dir
                relative_files = [str(file.relative_to(root_dir)) for file in files[:50]]
                return True, "\n".join(relative_files), current_dir
            except Exception as e:
                return False, f"Find failed: {e}", current_dir

        elif atype == "tree":
            tree_dir = action.get("path", ".")
            path, err = _safe_path(tree_dir, current_dir, root_dir)
            if err:
                return False, f"Invalid path: {err}", current_dir
            if not path.exists():
                return False, f"Directory not found: {tree_dir}", current_dir
            if not path.is_dir():
                return False, f"Not a directory: {tree_dir}", current_dir

            try:
                tree_output = create_tree(path, max_depth=4)
                if len(tree_output) > 2000:
                    tree_output = tree_output[:2000] + "\n... (truncated)"
                return True, tree_output, current_dir
            except Exception as e:
                return False, f"Tree failed: {e}", current_dir

        elif atype == "stats":
            stats_dir = action.get("path", ".")
            path, err = _safe_path(stats_dir, current_dir, root_dir)
            if err:
                return False, f"Invalid path: {err}", current_dir
            if not path.exists():
                return False, f"Directory not found: {stats_dir}", current_dir
            if not path.is_dir():
                return False, f"Not a directory: {stats_dir}", current_dir

            try:
                stats = get_project_stats(path)
                output = (
                    "Project Statistics\n"
                    f"Files: {stats['total_files']}\n"
                    f"Directories: {stats['total_dirs']}\n"
                    f"Lines of Code: {stats['total_lines']}\n"
                    f"Size: {stats['size_mb']} MB\n"
                    f"File Types: {stats['file_types']}"
                )
                return True, output, current_dir
            except Exception as e:
                return False, f"Stats failed: {e}", current_dir

        return False, f"Unknown action type: {atype}", current_dir

    except Exception as e:
        return False, f"Unexpected error: {e}", current_dir
