"""Miniforge - Local AI Coding Assistant"""

__version__ = "2.0.0"
__author__ = "Your Name"
__description__ = "Run AI coding assistant locally from any directory"

from .core.models import ask_model, ConversationContext
from .core.actions import parse_actions, execute_action
from .core.terminal import cyan, green, yellow, red, bold, dim
from .ui_module.ui import print_header, print_help, check_ollama, process_response
from .config import Config
from .utils import find_files, create_tree, get_project_stats

__all__ = [
    'ask_model',
    'ConversationContext',
    'parse_actions',
    'execute_action',
    'cyan',
    'green',
    'yellow',
    'red',
    'bold',
    'dim',
    'print_header',
    'print_help',
    'check_ollama',
    'process_response',
    'Config',
    'find_files',
    'create_tree',
    'get_project_stats',
]
