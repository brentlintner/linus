import pytest
import os
import sys
from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document

# Correct the path to allow importing modules from 'src'
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from repl import FilePathCompleter, CommandCompleter, create_prompt_session

# --- FilePathCompleter Tests ---

@pytest.fixture
def file_completer(tmp_path, monkeypatch):
    # Setup: create some dummy files and directories
    monkeypatch.chdir(tmp_path)  # Change to the temp directory
    (tmp_path / "file1.txt").write_text("Content 1")
    (tmp_path / "file2.py").write_text("print('hello')")
    os.makedirs(tmp_path / "subdir")
    (tmp_path / "subdir" / "subfile.txt").write_text("Subfile content")
    os.makedirs(tmp_path / ".git")
    (tmp_path / ".git" / "ignore_me.txt").write_text("Ignored")

    # Add a .gitignore file
    (tmp_path / ".gitignore").write_text("*.txt")

    return FilePathCompleter()

def test_file_path_completer_no_at(file_completer):
    # No "@" in the input, should return no completions
    document = Document("file")
    completions = list(file_completer.get_completions(document, None))
    assert len(completions) == 0

def test_file_path_completer_matches(file_completer):
    document = Document("@file")
    completions = list(file_completer.get_completions(document, None))
    assert len(completions) == 1  # Only file2.py, because .txt is ignored
    assert completions[0].text == "file2.py"
    assert completions[0].start_position == -5  # Correct start position

def test_file_path_completer_subdir(file_completer):
    document = Document("@subdir/sub")
    completions = list(file_completer.get_completions(document, None))
    assert len(completions) == 0 # Because subfile.txt is ignored

def test_file_path_completer_ignored(file_completer):
    document = Document("@.git/ignore")
    completions = list(file_completer.get_completions(document, None))
    assert len(completions) == 0  # Should not suggest ignored files

def test_file_path_completer_load_ignore_patterns(tmp_path):
     # Test loading ignore patterns from .gitignore
    (tmp_path / ".gitignore").write_text("*.py\n# comment\n*.txt")
    completer = FilePathCompleter()
    assert "*.py" in completer.ignore_patterns
    assert "*.txt" in completer.ignore_patterns
    assert "# comment" not in completer.ignore_patterns

# --- CommandCompleter Tests ---

@pytest.fixture
def command_completer():
    return CommandCompleter(['reset', 'refresh', 'exit', 'continue'])

def test_command_completer_no_dollar(command_completer):
    document = Document("res")
    completions = list(command_completer.get_completions(document, None))
    assert len(completions) == 0

def test_command_completer_matches(command_completer):
    document = Document("$res")
    completions = list(command_completer.get_completions(document, None))
    assert len(completions) == 1
    assert completions[0].text == 'reset'
    assert completions[0].start_position == -4

def test_command_completer_no_match(command_completer):
    document = Document("$not_a_command")
    completions = list(command_completer.get_completions(document, None))
    assert len(completions) == 0

# --- create_prompt_session Tests ---

def test_create_prompt_session():
    session = create_prompt_session()
    assert session is not None
    assert session.completer is not None  # Check that the combined completer is set
    assert session.key_bindings is not None # Check that we have keybindings
    assert session.multiline == True

# Test the CombinedCompleter.  This needs to mock the sub-completers.
def test_combined_completer(tmp_path, monkeypatch):
    # Use the real create_prompt_session, but mock its sub-completers
    monkeypatch.chdir(tmp_path) # Make sure os.walk in FilePathCompleter finds something
    (tmp_path / "test_file.txt").write_text("exists")

    session = create_prompt_session()

    # Test file completion
    document = Document("@test")
    completions = list(session.completer.get_completions(document, None))  # Call *combined* completer
    assert len(completions) > 0
    assert any(c.text == "test_file.txt" for c in completions)  # Check for a *file* completion


    # Test command completion
    document = Document("$res")
    completions = list(session.completer.get_completions(document, None)) # Call *combined* completer
    assert len(completions) > 0
    assert any(c.text == "reset" for c in completions)  # Check for a *command* completion

    # Test no completion
    document = Document("nothing")
    completions = list(session.completer.get_completions(document, None))
    assert len(completions) == 0

    # Test empty.  Shouldn't crash!
    document = Document("")
    completions = list(session.completer.get_completions(document, None))
    assert len(completions) == 0

# Test keybindings.  This is tricky because we'd ideally simulate key presses.
# This is more of an integration test.  For now, we just test that *something*
# is bound.
def test_keybindings(tmp_path):
    session = create_prompt_session()

    # Very basic check: make sure *some* keybindings exist.
    assert len(session.key_bindings.bindings) > 0

    # We could try to get fancier and check specific bindings, but that's fragile
    # and requires more mocking than it's worth at this point.

    # For example, to check the Up binding:
    # up_binding = [b for b in session.key_bindings.bindings if b.key == Keys.Up]
    # assert len(up_binding) > 0  # Check that *something* is bound to Up.
    # But we don't check *what* that something is.