import subprocess
import os
import re

from .logger import error
from .parser import terminal_log_block

def get_tmux_pane_content(__session_name__, pane_id, history=200):
    command = ["tmux", "capture-pane", "-p", "-t", f"{pane_id}", "-S", f"-{history}"]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    if result.returncode != 0:
        error(f"Error capturing pane {pane_id}: {result.stderr}")
        return ""  # Return empty string on error
    return result.stdout

def get_tmux_panes(session_name):
    command = ["tmux", "list-panes", "-s", "-F", "#D{{{}}}#W-#P-#T", "-t", session_name]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    if result.returncode != 0:
        error(f"Error listing panes for {session_name}: {result.stderr}")
        return [] # Return empty list on error.  Important!
    panes = result.stdout.strip().splitlines()
    panes = [pane.split("{{{}}}") for pane in panes]

    # TODO: (possible to just give no pane + -S - somehow?)
    return [[pid, title] for pid, title in panes if not re.search(r"n?vim", title, flags=re.IGNORECASE)]

def get_current_tmux_pane_id():
    """Gets the current tmux pane ID."""
    try:
        return os.environ.get('TMUX_PANE')
    except KeyError:
        return None

def get_tmux_logs():
    current_pane_id = get_current_tmux_pane_id()
    if not current_pane_id:
        return ""

    try:
        command = ["tmux", "display-message", "-p", "#S"]
        session_name = subprocess.run(command, capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError as e:
        error(f"Error getting tmux session name: {e}")
        return f"Error getting tmux session name: {e}\n"

    panes = get_tmux_panes(session_name)

    all_logs = ""

    for pid, title in panes:
        if pid != current_pane_id:
            content = get_tmux_pane_content(session_name, pid)
            all_logs += terminal_log_block(content, title)

    return all_logs
