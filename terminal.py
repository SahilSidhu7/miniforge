"""Terminal styling and color utilities."""

def colored(text, code):
    """Apply ANSI color code to text."""
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
