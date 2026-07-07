"""Configuration management for Miniforge."""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """Load and manage Miniforge configuration."""
    
    # Default values
    DEFAULTS = {
        "ollama_url": "http://localhost:11434/api/generate",
        "model": "qwen2.5-coder:7b",
        "timeout": 300,
        "max_turns": 8,
        "temperature": 0.1,
        "num_predict": 4096,
        "num_ctx": 4096,
    }
    
    def __init__(self):
        self.config = self.DEFAULTS.copy()
        self.config_path = self._find_config()
        
        if self.config_path:
            self._load_config()
    
    def _find_config(self) -> Optional[Path]:
        """Find config file in common locations."""
        candidates = [
            Path.cwd() / "miniforge.json",
            Path.home() / ".miniforge" / "config.json",
            Path.home() / ".config" / "miniforge" / "config.json",
            Path(__file__).parent / "miniforge.json",
        ]
        
        for path in candidates:
            if path.exists():
                return path
        return None
    
    def _load_config(self):
        """Load configuration from file."""
        try:
            if self.config_path and self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                self.config.update(user_config)
        except Exception as e:
            print(f"Warning: Failed to load config: {e}")
    
    def get(self, key: str, default=None):
        """Get config value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set config value."""
        self.config[key] = value
    
    def save(self, path: Optional[Path] = None):
        """Save configuration to file."""
        save_path = path or self.config_path or (Path.home() / ".config" / "miniforge" / "config.json")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(save_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.config_path = save_path
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def show(self):
        """Display all configuration."""
        for key, value in sorted(self.config.items()):
            print(f"  {key}: {value}")


def create_default_config(path: Path) -> bool:
    """Create a default configuration file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    
    config_template = {
        "ollama_url": "http://localhost:11434/api/generate",
        "model": "qwen2.5-coder:7b",
        "timeout": 300,
        "max_turns": 8,
        "temperature": 0.1,
        "num_predict": 4096,
        "num_ctx": 4096,
    }
    
    try:
        with open(path, 'w') as f:
            json.dump(config_template, f, indent=2)
        return True
    except Exception as e:
        print(f"Error creating config: {e}")
        return False
