import pytest
import os
import sys
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.chat import compact_history

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


def test_compact_history_removes_old_version():
    """
    Tests that compact_history removes the older version (v1) of a file
    when a newer version (v2) exists.
    """
    input_history_str = load_fixture("compact_history_input_remove_old.txt")
    expected_history_str = load_fixture("compact_history_expected_remove_old.txt")

    # compact_history expects a list containing the history string as the first element
    input_history_list = [input_history_str]

    # Call the function (pass None for filename as we don't test writing here)
    compacted_history_list = compact_history(input_history_list, None)

    # The function should return a list with the compacted string as the first element
    assert len(compacted_history_list) == 1, "compact_history should return a list with one element"
    result_str = compacted_history_list[0]

    # Compare the result string with the expected string
    # Use pytest's multiline string comparison helpers if available, or simple assert
    assert result_str.strip() == expected_history_str.strip()

# You can add more test cases below following the same pattern
# def test_compact_history_multiple_files():
#     input_history_str = load_fixture("compact_history_input_multi.txt")
#     expected_history_str = load_fixture("compact_history_expected_multi.txt")
#     ...

# def test_compact_history_no_removals():
#     input_history_str = load_fixture("compact_history_input_no_remove.txt")
#     expected_history_str = load_fixture("compact_history_expected_no_remove.txt") # Should be same as input
#     ...
