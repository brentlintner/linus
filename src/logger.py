from rich.console import Console
from rich.markdown import Markdown
from pygments import styles
from .theme import EverforestDarkStyle, ConsoleTheme

VERBOSE_ON = False

DEBUG_ON = False

console = Console(theme=ConsoleTheme)

styles.STYLES["everforest-dark"] = EverforestDarkStyle

def quiet_logging():
    global VERBOSE_ON
    VERBOSE_ON = False
    global DEBUG_ON
    DEBUG_ON = False

def verbose_logging():
    global VERBOSE_ON
    VERBOSE_ON = True

def debug_logging():
    verbose_logging()
    global DEBUG_ON
    DEBUG_ON = True

def is_debug():
    return DEBUG_ON

def is_verbose():
    return VERBOSE_ON

def debug(message):
    if DEBUG_ON:
        message = f"DEBUG: {message}" if message else ""
        console.print(message, style="bold yellow")

def error(message):
    console.print(f"ERROR: {message}", style="bold red")

def print_markdown(block, end="\n"):
    console.print(Markdown(block, code_theme="everforest-dark"), end=end)
