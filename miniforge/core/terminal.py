"""Terminal styling and color utilities with cross-platform support."""

import sys
import platform
import os


# Detect Windows and enable ANSI support if needed
if platform.system() == "Windows":
    # Try to enable ANSI colors on Windows 10+
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            mode.value |= 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
            kernel32.SetConsoleMode(handle, mode)
    except:
        pass


def colored(text, code):
    """Apply ANSI color code to text (with Windows fallback)."""
    # Check if colors should be disabled
    if os.getenv('NO_COLOR') or not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def cyan(t):
    """Return text in cyan."""
    return colored(t, 96)


def green(t):
    """Return text in green."""
    return colored(t, 92)


def yellow(t):
    """Return text in yellow."""
    return colored(t, 93)


def red(t):
    """Return text in red."""
    return colored(t, 91)


def bold(t):
    """Return text in bold."""
    return colored(t, 1)


def dim(t):
    """Return text in dim."""
    return colored(t, 2)
