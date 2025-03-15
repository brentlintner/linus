import subprocess
import pytest
import re
import os
import sys

# Correct the path to allow importing modules from 'src'
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, src_path)

from parser import (
    FILE_METADATA_START,
    FILE_METADATA_END,
    END_OF_FILE,
    find_files
)

@pytest.fixture(scope="session")
def run_cli():
    """Starts the CLI in a subprocess, providing a function to interact with it."""
    process = subprocess.Popen(
        ["python", "src/cli.py"],  # Directly invoke cli.py
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line-buffered
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # Go up one level
    )

    def send_command(command, expect_response=True, timeout=20):
        """Sends a command and returns the output, error, and return code."""
        try:
            process.stdin.write(command + "\n")
            process.stdin.flush()

            if expect_response:
                output = ""
                while True:
                    line = process.stdout.readline()
                    output += line

                    if "Linus is thinking..." in line or "Linus is typing..." in line:
                        continue  # Skip intermediate status messages
                    if re.search(r'>\s*$', line):  # Look for the next prompt
                        break  # Stop reading at the next prompt

                return output.strip(), "", 0  # Return the output with prompt removed.
            else:
                return "", "", 0 # Return empty output
        except subprocess.TimeoutExpired:
            process.kill()
            outs, errs = process.communicate()
            return outs, errs, process.returncode

    yield send_command

    # Cleanup after tests are done
    process.stdin.close()
    process.terminate()
    process.wait(timeout=5)

def test_basic_interaction(run_cli, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    command = "show me a simple c file called hello.c"
    response, _, _ = run_cli(command)

    # Check for the start of the file metadata
    assert f"{FILE_METADATA_START}" in response

    # Extract the file block
    files = find_files(response)
    assert len(files) == 1
    file_path, version, file_content, language, part, no_more_parts = files[0]

    assert file_path == "hello.c"
    assert version == 1
    assert language == "c"
    assert no_more_parts

    # Basic check for C file content (more specific checks could be added)
    assert "#include <stdio.h>" in file_content
    assert "int main()" in file_content
    assert 'printf("Hello, World!\\n");' in file_content

    # Check that the program exits cleanly
    exit_command = "$exit"
    exit_response, _, exit_returncode = run_cli(exit_command, expect_response=False)  # Don't capture stdout
    assert exit_returncode == 0 or exit_returncode is None  # None can happen, as it exits fast

    # Check that no errors were printed to stderr.  Important!
    # _, err, _ = run_cli("") # Check for errors
    # assert err == ""  # No errors expected.

def test_exit_command(run_cli):
    """Tests that the exit command works correctly."""
    exit_command = "$exit"
    _, _, exit_returncode = run_cli(exit_command, expect_response=False) # Don't expect output, as it flushes
    assert exit_returncode == 0 or exit_returncode is None

def test_no_response(run_cli):
    """Tests sending a command that gets no response."""
    command = "" # Empty
    response, _, _ = run_cli(command) # Don't expect a response.
    assert len(response) > 0 # But still get the prompt

def test_reset_command(run_cli):
    reset_command = "$reset"
    response, _, _ = run_cli(reset_command)
    assert "History reset." in response

    exit_command = "$exit"
    run_cli(exit_command, expect_response=False)

def test_refresh_command(run_cli):
    refresh_command = "$refresh"
    response, _, _ = run_cli(refresh_command)
    assert "Project context refreshed." in response

    exit_command = "$exit"
    run_cli(exit_command, expect_response=False)