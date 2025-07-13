import pytest
import os
import sys
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from src.chat import compact_history # This function is removed

# Helper function to load fixture content
def load_fixture(filename):
    fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', filename)
    try:
        with open(fixture_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        pytest.fail(f"Fixture file not found: {fixture_path}. Please create it.")
    except Exception as e:
        pytest.fail(f"Error reading fixture file {fixture_path}: {e}")

# The compact_history function has been removed, so the corresponding test
# is also removed.  If we add database-related tests for chat history,
# they would go here.