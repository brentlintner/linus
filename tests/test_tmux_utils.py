import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Make sure the src directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tmux_utils import get_tmux_pane_content, get_tmux_panes, get_tmux_logs

@patch('src.tmux_utils.subprocess.run')
def test_get_tmux_panes(mock_subprocess_run):
    """Tests fetching and parsing of tmux panes."""
    # Mock the output of the tmux list-panes command
    # Verify that the function correctly parses the output
    # Test with normal output, empty output, and output with special characters
    pass

@patch('src.tmux_utils.subprocess.run')
def test_get_tmux_pane_content(mock_subprocess_run):
    """Tests fetching content from a specific tmux pane."""
    # Mock the output of the tmux capture-pane command
    # Verify the function returns the correct content
    pass

@patch('src.tmux_utils.get_tmux_panes')
@patch('src.tmux_utils.get_tmux_pane_content')
@patch('src.tmux_utils.get_current_tmux_pane_id')
def test_get_tmux_logs(mock_get_pane_id, mock_get_content, mock_get_panes):
    """Tests the aggregation of logs from multiple tmux panes."""
    # Mock the return values of the helper functions
    # Verify that get_tmux_logs correctly calls the helpers and assembles the logs
    # Test the case where the current pane is correctly excluded
    pass

def test_get_current_tmux_pane_id():
    """Tests retrieval of the current pane ID from environment variables."""
    # Use patch.dict to simulate the presence and absence of the TMUX_PANE env var
    pass
