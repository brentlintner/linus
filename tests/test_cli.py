import pytest
import os
import sys
import shutil
from unittest.mock import patch, MagicMock

# Correct the path to allow importing modules from 'src'
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from cli import (
    create_parser,
    clean_history_files,
    handle_list_files,
    handle_tokens,
    main
)
import cli
from file_utils import generate_project_file_list

# Mock genai.Client for tests that require it.
@pytest.fixture
def mock_genai_client():
    with patch('cli.genai.Client') as mock_client:
        yield mock_client

@pytest.fixture
def parser():
    return create_parser()

def test_create_parser(parser):
    assert parser is not None
    assert parser.description == 'ai-code'

def test_clean_history_files_success(tmp_path):
    # Create a temporary directory and files to simulate history
    temp_hist_dir = tmp_path / "tmp"
    temp_hist_dir.mkdir()
    (temp_hist_dir / "history1.txt").write_text("Some history")
    (temp_hist_dir / "history2.txt").write_text("More history")

    # Call the function with the temporary directory
    clean_history_files(str(temp_hist_dir))

    # Check if the directory is empty now
    assert not any(temp_hist_dir.iterdir())

def test_clean_history_files_error(tmp_path, monkeypatch):
    # Create a temporary directory
    temp_hist_dir = tmp_path / "tmp"
    temp_hist_dir.mkdir()

    # Mock shutil.rmtree to raise an exception
    def mock_rmtree(path):
        raise OSError("Mocked error")
    monkeypatch.setattr(shutil, 'rmtree', mock_rmtree)

    # Capture the output
    with patch('sys.stdout', new_callable=MagicMock) as mock_stdout:
        clean_history_files(str(temp_hist_dir))
        mock_stdout.assert_called_once() # Check that something was printed
        assert "Error cleaning history files" in mock_stdout.method_calls[0].args[0]  # Check for error message

def test_handle_list_files(parser, capsys, tmp_path, monkeypatch):
    # Set up environment
    monkeypatch.chdir(tmp_path)

    # Create some dummy files
    (tmp_path / "file1.txt").write_text("Content 1")
    (tmp_path / "file2.py").write_text("print('hello')")
    os.makedirs(tmp_path / ".git")
    (tmp_path / ".git" / "ignore_me.txt").write_text("Ignored")

    # Call with include pattern.
    args = parser.parse_args(['--list-files', '--files', '*.py'])
    handle_list_files(args)
    captured = capsys.readouterr()
    assert "file2.py" in captured.out
    assert "file1.txt" not in captured.out  # Not included
    assert ".git" not in captured.out

    # Call with ignore pattern
    args = parser.parse_args(['--list-files', '--ignore', '*1.txt'])
    handle_list_files(args)
    captured = capsys.readouterr()
    assert "file2.py" in captured.out
    assert "file1.txt" not in captured.out

    # Call with no filters
    args = parser.parse_args(['--list-files'])
    handle_list_files(args)
    captured = capsys.readouterr()
    assert "file1.txt" in captured.out
    assert "file2.py" in captured.out
    assert ".git" not in captured.out  # Should still be ignored by default


def test_handle_tokens(parser, mock_genai_client, tmp_path, monkeypatch):
    # Set up environment
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test_file.txt").write_text("Some test content")

    # Mock the count_tokens method
    mock_count_tokens = MagicMock()
    mock_count_tokens.total_tokens = 10  # Example token count
    mock_genai_client.return_value.models.count_tokens.return_value = mock_count_tokens

    # Test with valid file
    args = parser.parse_args(['--tokens', '--files', 'test_file.txt'])
    with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key', 'GEMINI_MODEL': 'test-model'}):
        handle_tokens(args)
        mock_genai_client.return_value.models.count_tokens.assert_called_once_with(model='test-model', contents='Some test content')

    # Test with non-existent file
    args = parser.parse_args(['--tokens', '--files', 'no_such_file.txt'])
    with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key', 'GEMINI_MODEL': 'test-model'}), \
         patch('sys.stderr', new_callable=MagicMock) as mock_stderr: # Capture stderr
        handle_tokens(args)
        assert "no_such_file.txt: NOT FOUND" in mock_stderr.method_calls[0].args[0]

    mock_genai_client.return_value.models.count_tokens.reset_mock()  # Reset for next test

    # Test with exception during count
    mock_genai_client.return_value.models.count_tokens.side_effect = Exception("Mocked error")
    args = parser.parse_args(['--tokens', '--files', 'test_file.txt'])
    with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_key', 'GEMINI_MODEL': 'test-model'}), \
         patch('sys.stderr', new_callable=MagicMock) as mock_stderr:  # Capture stderr
        handle_tokens(args)
        assert "Error with test_file.txt: Mocked error" in mock_stderr.method_calls[0].args[0]

@patch('cli.coding_repl')
@patch('cli.check_if_env_vars_set')
@patch('cli.list_available_models')
@patch('cli.clean_history_files')
@patch('cli.handle_list_files')
@patch('cli.handle_tokens')
@patch('cli.os.chdir')
def test_main_function(
        mock_chdir,
        mock_handle_tokens,
        mock_handle_list_files,
        mock_clean,
        mock_list_models,
        mock_check_env,
        mock_coding_repl,
        parser
    ):

    # Test --models
    sys.argv = ['ai-code', '--models']
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
    mock_list_models.assert_called_once()

    # Test --clean
    sys.argv = ['ai-code', '--clean']
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
    mock_clean.assert_called_once()

    # Test --list-files
    sys.argv = ['ai-code', '--list-files']
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
    mock_handle_list_files.assert_called_once()

    # Test --tokens
    sys.argv = ['ai-code', '--tokens']
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 0
    mock_handle_tokens.assert_called_once()

    # Test normal operation (coding REPL)
    sys.argv = ['ai-code']
    main()
    mock_coding_repl.assert_called_once()
    mock_coding_repl.assert_called_with(resume=True, writeable=False, ignore_patterns=None, include_files=None)

    # Test coding repl with options
    sys.argv = ['ai-code', '--no-resume', '--writeable', '--ignore', 'ignore1,ignore2', '--files', 'file1,file2']
    main()
    mock_coding_repl.assert_called_with(resume=False, writeable=True, ignore_patterns='ignore1,ignore2', include_files='file1,file2')

    # Test changing directory
    sys.argv = ['ai-code', '--directory', '/some/path']
    main()
    mock_chdir.assert_called_with('/some/path')


    # Test debug mode.
    with patch('cli.debug_logging') as mock_debug:
        sys.argv = ['ai-code', '--debug']
        main()
        mock_debug.assert_called_once()

    # Test verbose mode
    with patch('cli.verbose_logging') as mock_verbose:
        sys.argv = ['ai-code', '--verbose']
        main()
        mock_verbose.assert_called_once()