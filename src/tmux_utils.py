import subprocess
import os

from .chat import error
from .parser import terminal_log_block

def get_tmux_pane_content(session_name, pane_id):
    command = ["tmux", "capture-pane", "-p", "-t", f"{pane_id}", "-S", "-"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error(f"Error capturing pane {pane_id}: {result.stderr}")
        return ""  # Return empty string on error
    return result.stdout

def get_tmux_pane_ids(session_name, pane_id):
    command = ["tmux", "list-panes", "-s", "-F", "#{pane_id}", "-t", session_name]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error(f"Error listing panes for {session_name}: {result.stderr}")
        return [] # Return empty list on error.  Important!
    return result.stdout.strip().splitlines()

def get_current_tmux_pane_id():
    """Gets the current tmux pane ID."""
    try:
        return os.environ.get('TMUX_PANE')
    except KeyError:
        return None

def get_tmux_logs():
    current_pane_id = get_current_tmux_pane_id()
    if not current_pane_id:
        return "No tmux session detected.\n"

    try:
        session_name = subprocess.run(["tmux", "display-message", "-p", "#S"], capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError as e:
        error(f"Error getting tmux session name: {e}")
        return f"Error getting tmux session name: {e}\n"

    pane_ids = get_tmux_pane_ids(session_name, current_pane_id)
    all_logs = ""

    for pane_id in pane_ids:
        if pane_id != current_pane_id:
            content = get_tmux_pane_content(session_name, pane_id)
            # TODO: use "-F\#W-\#P-\#T" as title
            title = f"Pane {pane_id}"
            all_logs += terminal_log_block(content, title)
    return all_logs

