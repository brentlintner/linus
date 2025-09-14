import pytest
import os
import sys
import json

# Make sure the src directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.file_utils import (
    generate_project_structure,
    generate_project_file_list,
    generate_project_file_contents,
    load_ignore_patterns,
    generate_diff
)
from src.config import DEFAULT_IGNORE_PATTERNS

# The fixture directory is created manually, so we can reference it directly.
FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures', 'file_utils_project')

def test_load_ignore_patterns():
    """Tests that ignore patterns are loaded from default, .gitignore, and .linignore."""
    # Test loading patterns from the created fixture directory
    extra_patterns = ["*.custom"]
    patterns = load_ignore_patterns(extra_patterns, FIXTURE_DIR)

    # Assert that default patterns are loaded
    assert ".git/" in patterns
    assert all(p in patterns for p in DEFAULT_IGNORE_PATTERNS)

    # Assert that .gitignore patterns are added
    assert "build/" in patterns
    assert "*.log" in patterns

    # Assert that .linignore patterns are added
    assert "*.txt" in patterns

    # Assert that extra patterns passed as arguments are added
    assert "*.custom" in patterns

def test_generate_project_structure_with_ignores():
    """Tests the generation of the file tree, respecting all ignore files."""
    # Use FIXTURE_DIR as the target directory
    structure = generate_project_structure(cwd=FIXTURE_DIR, include_patterns=["."])
    paths = {item['id'] for item in structure}

    # Assert that ignored files/dirs are NOT in the resulting tree
    assert 'build' not in paths
    assert 'build/output.log' not in paths
    assert 'file2.txt' not in paths

    # Assert that non-ignored files ARE in the tree
    assert 'file1.py' in paths
    assert 'subdir' in paths
    assert 'subdir/file3.js' in paths

def test_generate_project_structure_with_includes():
    """Tests the generation of the file tree with specific include patterns."""
    # Test with include_patterns=["*.py"]
    structure_py = generate_project_structure(cwd=FIXTURE_DIR, include_patterns=["*.py"])
    paths_py = {item['id'] for item in structure_py}
    assert 'file1.py' in paths_py
    assert 'subdir/file3.js' not in paths_py

    # Test with include_patterns=["subdir/*"]
    structure_subdir = generate_project_structure(cwd=FIXTURE_DIR, include_patterns=["subdir/*"])
    paths_subdir = {item['id'] for item in structure_subdir}
    assert 'subdir/file3.js' in paths_subdir
    assert 'file1.py' not in paths_subdir

def test_generate_project_file_list():
    """Tests generation of the file list, respecting ignore and include rules."""
    # Test with ignores
    file_list_ignores = generate_project_file_list(cwd=FIXTURE_DIR, include_patterns=["."])
    assert 'file1.py' in file_list_ignores
    assert 'subdir/file3.js' in file_list_ignores
    assert 'file2.txt' not in file_list_ignores
    assert 'build/output.log' not in file_list_ignores

    # Test with includes
    file_list_includes = generate_project_file_list(cwd=FIXTURE_DIR, include_patterns=["*.js"])
    assert 'subdir/file3.js' in file_list_includes
    assert 'file1.py' not in file_list_includes

def test_generate_project_file_contents():
    """Tests that the correct file contents are aggregated into blocks."""
    contents = generate_project_file_contents(cwd=FIXTURE_DIR, include_patterns=["*.py"])
    assert "Path: file1.py" in contents
    assert 'print("hello from file1.py")' in contents
    assert "Path: subdir/file3.js" not in contents

def test_diff_generation(tmp_path):
    """Tests the generation of diffs for existing files."""
    file = tmp_path / "test.txt"
    original_content = "line one\nline two\n"
    file.write_text(original_content)

    new_content = "line one\nline two changed\nline three\n"
    diff = generate_diff(str(file), new_content)

    assert "---" in diff
    assert "+++" in diff
    assert "-line two" in diff
    assert "+line two changed" in diff
    assert "+line three" in diff
