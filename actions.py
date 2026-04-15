"""Action parsing and execution for LocalAgent."""

import re
import subprocess
import shutil
from pathlib import Path


def parse_actions(text):
    """Extract all action blocks from model response."""
    actions = []
    pattern = r'<<<ACTION>>>(.*?)<<<END>>>'
    matches = re.findall(pattern, text, re.DOTALL)
    
    for match in matches:
        lines = match.strip().split('\n')
        action = {}
        content_lines = []
        in_content = False
        
        for line in lines:
            if line.startswith('TYPE:'):
                action['type'] = line.split(':', 1)[1].strip().lower()
            elif line.startswith('COMMAND:'):
                action['command'] = line.split(':', 1)[1].strip()
            elif line.startswith('PATH:'):
                action['path'] = line.split(':', 1)[1].strip()
            elif line.startswith('DEST:'):
                action['dest'] = line.split(':', 1)[1].strip()
            elif line.startswith('FIND:'):
                action['find'] = line.split(':', 1)[1].strip()
            elif line.startswith('REPLACE:'):
                action['replace'] = line.split(':', 1)[1].strip()
            elif line.startswith('CONTENT:'):
                in_content = True
                rest = line.split(':', 1)[1].strip()
                if rest:
                    content_lines.append(rest)
            elif in_content:
                content_lines.append(line)
        
        if content_lines:
            action['content'] = '\n'.join(content_lines)
        
        if 'type' in action:
            actions.append(action)
    
    return actions


def execute_action(action, work_dir):
    """Execute a single parsed action. Returns (success, output)."""
    atype = action.get('type', '')
    
    try:
        # ── bash ──────────────────────────────────────────────────────────────
        if atype == 'bash':
            cmd = action.get('command', '')
            if not cmd:
                return False, "No command provided"
            result = subprocess.run(
                cmd, shell=True, capture_output=True,
                text=True, cwd=str(work_dir), timeout=60
            )
            output = result.stdout.strip() or result.stderr.strip() or "(no output)"
            return result.returncode == 0, output

        # ── create_file ───────────────────────────────────────────────────────
        elif atype == 'create_file':
            path = work_dir / action.get('path', '')
            content = action.get('content', '')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            return True, f"Created {path}"

        # ── read_file ─────────────────────────────────────────────────────────
        elif atype == 'read_file':
            path = work_dir / action.get('path', '')
            if not path.exists():
                return False, f"File not found: {path}"
            content = path.read_text(encoding='utf-8')
            # truncate long files
            if len(content) > 3000:
                content = content[:3000] + "\n... (truncated)"
            return True, content

        # ── edit_file ─────────────────────────────────────────────────────────
        elif atype == 'edit_file':
            path = work_dir / action.get('path', '')
            if not path.exists():
                return False, f"File not found: {path}"
            find    = action.get('find', '')
            replace = action.get('replace', '')
            content = path.read_text(encoding='utf-8')
            if find not in content:
                return False, f"Text not found in file: '{find}'"
            new_content = content.replace(find, replace, 1)
            path.write_text(new_content, encoding='utf-8')
            return True, f"Edited {path}"

        # ── list_dir ──────────────────────────────────────────────────────────
        elif atype == 'list_dir':
            path = work_dir / action.get('path', '.')
            if not path.exists():
                return False, f"Directory not found: {path}"
            items = sorted(path.iterdir())
            lines = []
            for item in items:
                prefix = "📁" if item.is_dir() else "📄"
                lines.append(f"{prefix} {item.name}")
            return True, '\n'.join(lines) if lines else "(empty directory)"

        # ── delete_file ───────────────────────────────────────────────────────
        elif atype == 'delete_file':
            path = work_dir / action.get('path', '')
            if not path.exists():
                return False, f"Not found: {path}"
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            return True, f"Deleted {path}"

        # ── move_file ─────────────────────────────────────────────────────────
        elif atype == 'move_file':
            src  = work_dir / action.get('path', '')
            dest = work_dir / action.get('dest', '')
            if not src.exists():
                return False, f"Source not found: {src}"
            shutil.move(str(src), str(dest))
            return True, f"Moved {src} → {dest}"

        else:
            return False, f"Unknown action type: {atype}"

    except subprocess.TimeoutExpired:
        return False, "Command timed out (60s)"
    except PermissionError as e:
        return False, f"Permission denied: {e}"
    except Exception as e:
        return False, f"Error: {e}"
