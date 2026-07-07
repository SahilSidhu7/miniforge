"""Utility functions for Miniforge."""

import os
from pathlib import Path
from typing import Dict, List


def find_files(directory: Path, pattern: str = "*", recursive: bool = True) -> List[Path]:
    """Find files matching a glob pattern."""
    try:
        iterator = directory.rglob(pattern) if recursive else directory.glob(pattern)
        return [path for path in iterator if path.is_file()]
    except Exception:
        return []


def count_lines(path: Path) -> int:
    """Count lines in a text file."""
    try:
        if path.is_file():
            with open(path, "r", encoding="utf-8", errors="ignore") as file:
                return sum(1 for _ in file)
    except OSError:
        return 0
    return 0


def get_project_stats(directory: Path) -> Dict:
    """Get aggregate file statistics for a project directory."""
    stats = {
        "total_files": 0,
        "total_dirs": 0,
        "total_lines": 0,
        "file_types": {},
        "size_mb": 0,
    }

    try:
        for root, dirs, files in os.walk(directory):
            stats["total_dirs"] += len(dirs)
            for filename in files:
                path = Path(root) / filename
                stats["total_files"] += 1
                stats["total_lines"] += count_lines(path)

                ext = path.suffix or "no_ext"
                stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1

                try:
                    stats["size_mb"] += path.stat().st_size / (1024 * 1024)
                except OSError:
                    pass
    except OSError:
        pass

    stats["size_mb"] = round(stats["size_mb"], 2)
    return stats


def create_tree(directory: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0) -> str:
    """Create an ASCII tree for a directory."""
    if current_depth >= max_depth:
        return ""

    lines = []
    try:
        items = sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        for index, item in enumerate(items):
            is_last = index == len(items) - 1
            current_prefix = "`-- " if is_last else "|-- "
            next_prefix = "    " if is_last else "|   "

            if item.is_dir():
                lines.append(f"{prefix}{current_prefix}{item.name}/")
                subtree = create_tree(item, prefix + next_prefix, max_depth, current_depth + 1)
                if subtree:
                    lines.append(subtree)
            else:
                lines.append(f"{prefix}{current_prefix}{item.name}")
    except OSError:
        pass

    return "\n".join(lines)


def suggest_model():
    """Suggest appropriate models based on task profile."""
    return {
        "Small/Fast": "neural-chat:7b",
        "Balanced": "qwen2.5-coder:7b",
        "Powerful": "llama2:13b",
        "Very Fast": "tinyllama:1b",
    }


def validate_workspace(directory: Path) -> Dict:
    """Validate whether a directory looks like a project workspace."""
    try:
        is_empty = not any(directory.iterdir())
    except OSError:
        is_empty = True

    return {
        "is_valid": directory.exists() and directory.is_dir(),
        "is_git": (directory / ".git").exists(),
        "has_package_json": (directory / "package.json").exists(),
        "has_requirements": (directory / "requirements.txt").exists(),
        "has_config": (directory / "config.json").exists() or (directory / "config.yaml").exists(),
        "is_empty": is_empty,
    }
