import pytest
import os
import sys

# Make sure the src directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.logger import quiet_logging, verbose_logging, debug_logging, is_verbose, is_debug

def test_logging_flags():
    """
    Tests the state changes of logging flags.
    """
    # Set a baseline state first
    quiet_logging()
    assert not is_verbose()
    assert not is_debug()

    verbose_logging()
    assert is_verbose()
    assert not is_debug()

    debug_logging()
    assert is_verbose() # debug implies verbose
    assert is_debug()

    quiet_logging()
    assert not is_verbose()
    assert not is_debug()
