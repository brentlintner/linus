import pytest
import os
import re
import sys

src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))

sys.path.insert(0, src_path)

import parser

# Test data using multi-line strings and the placeholder function

TEST_FILE_1 = f"""
{parser.placeholder('START FILE METADATA')}
Path: test_file_1.py
Language: python
Version: 1
NoMoreParts: True
{parser.placeholder('END FILE METADATA')}
print('Hello from test file 1')
{parser.placeholder('END OF FILE')}
"""

TEST_FILE_2_PARTS = f"""
{parser.placeholder('START FILE METADATA')}
Path: test_file_2.py
Language: python
Version: 1
Part: 1
{parser.placeholder('END FILE METADATA')}
def some_function():
{parser.placeholder('END OF FILE')}
""" + f"""
{parser.placeholder('START FILE METADATA')}
Path: test_file_2.py
Language: python
Version: 1
Part: 2
{parser.placeholder('END FILE METADATA')}
    pass
{parser.placeholder('END OF FILE')}
"""

TEST_FILE_3_MULTIPLE_VERSIONS = f"""
{parser.placeholder('START FILE METADATA')}
Path: test_file_3.py
Language: python
Version: 1
NoMoreParts: True
{parser.placeholder('END FILE METADATA')}
# Old version
{parser.placeholder('END OF FILE')}
""" + f"""
{parser.placeholder('START FILE METADATA')}
Path: test_file_3.py
Language: python
Version: 2
NoMoreParts: True
{parser.placeholder('END FILE METADATA')}
# New version
{parser.placeholder('END OF FILE')}
"""

TEST_FILE_4_NO_PART = f"""
{parser.placeholder('START FILE METADATA')}
Path: test_file_4.py
Language: python
Version: 1
{parser.placeholder('END FILE METADATA')}
# File with no Part, assumes part 1.
{parser.placeholder('END OF FILE')}
"""

TEST_FILE_5_ONLY_PART = f"""
{parser.placeholder('START FILE METADATA')}
Path: test_file_5.py
Language: python
Version: 1
Part: 2
{parser.placeholder('END FILE METADATA')}
# File with only Part, assumes *not* the last part.
{parser.placeholder('END OF FILE')}
"""

TEST_SNIPPET = f"""
{parser.placeholder('START CODE SNIPPET METADATA')}
Language: python
{parser.placeholder('END CODE SNIPPET METADATA')}
def my_snippet():
    print('Hello from snippet')
{parser.placeholder('END OF FILE')}
"""

def test_find_files():
    assert parser.find_files(TEST_FILE_1) == [['test_file_1.py', 1, "print('Hello from test file 1')", 'python', 1, True]]
    # test_file_2 needs to have NoMoreParts: True now.
    assert parser.find_files(TEST_FILE_2_PARTS) == [['test_file_2.py', 1, 'def some_function():\n    pass', 'python', 2, False]]
    assert parser.find_files(TEST_FILE_3_MULTIPLE_VERSIONS) == [['test_file_3.py', 2, '# New version', 'python', 1, True]]
    assert parser.find_files("Some random text with no file blocks") == []
    assert parser.find_files(TEST_FILE_4_NO_PART) == [['test_file_4.py', 1, '# File with no Part, assumes part 1.', 'python', 1, False]]
    assert parser.find_files(TEST_FILE_5_ONLY_PART) == [['test_file_5.py', 1, '# File with only Part, assumes *not* the last part.', 'python', 2, False]]

def test_find_snippets():
    assert parser.find_snippets(TEST_SNIPPET) == [('python', "def my_snippet():\n    print('Hello from snippet')")]
    assert parser.find_snippets("Some random text with no snippets") == []

def test_find_file_references():
    assert parser.find_file_references("This is a reference to @test_file_1.py") == ['test_file_1.py']
    assert parser.find_file_references("Multiple references: @file_1.txt and @file_2.txt") == ['file_1.txt', 'file_2.txt']
    assert parser.find_file_references("Reference with punctuation, @file_3.txt.") == ['file_3.txt']
    assert parser.find_file_references("No file references here.") == []

def test_find_in_progress_file():
    in_progress = f"""
{parser.placeholder('START FILE METADATA')}
Path: incomplete.py
Language: python
Version: 1
Part: 1
NoMoreParts: False
{parser.placeholder('END FILE METADATA')}
    """
    assert parser.find_in_progress_file(in_progress) == ('incomplete.py', False)
    assert parser.find_in_progress_file(TEST_FILE_1) == ('test_file_1.py', True)  # Complete file
    assert parser.find_in_progress_file("No file metadata here") == (None, None)

def test_find_in_progress_snippet():
    in_progress = f"""
{parser.placeholder('START CODE SNIPPET METADATA')}
Language: python
{parser.placeholder('END CODE SNIPPET METADATA')}
print('Incomplete snippet')
"""
    assert parser.find_in_progress_snippet(in_progress) == 'python'
    assert parser.find_in_progress_snippet(TEST_SNIPPET) == None # Complete snippet
    assert parser.find_in_progress_snippet("No snippet metadata") == None

def test_get_language_from_extension():
    assert parser.get_language_from_extension("test.py") == "python"
    assert parser.get_language_from_extension("test.js") == "javascript"
    assert parser.get_language_from_extension("test.txt") == "text"
    assert parser.get_language_from_extension("no_extension") == "text"

    # Test shebang handling
    assert parser.get_language_from_extension("script.sh") == 'bash' # Assuming the file contains a bash shebang
    assert parser.get_language_from_extension("script_no_ext") == 'text' # Assuming no shebang
    assert parser.get_language_from_extension("python_script") == 'python' #Assuming a python shebang

def test_get_program_from_shebang():
    assert parser.get_program_from_shebang("#!/usr/bin/env python3") == "python3"
    assert parser.get_program_from_shebang("#!/bin/bash") == "bash"
    assert parser.get_program_from_shebang("#!/usr/bin/sh") == "sh"
    assert parser.get_program_from_shebang("#!/usr/bin/env node") == 'node'
    assert parser.get_program_from_shebang("no shebang") == None
    assert parser.get_program_from_shebang("") == None

def test_safe_int():
    assert parser.safe_int("10") == 10
    assert parser.safe_int("abc") == 1
    assert parser.safe_int(None) == 1
    assert parser.safe_int("5.5") == 1

# Create test files so get_language_from_extension has something to open
# Doing it inside a fixture to avoid file system clutter.
@pytest.fixture(scope="session", autouse=True)
def create_test_files(tmp_path_factory):
    tmpdir = tmp_path_factory.mktemp("test_files")
    (tmpdir / "script.sh").write_text("#!/bin/bash\necho 'Hello from bash'")
    (tmpdir / "script_no_ext").write_text("Just some text")
    (tmpdir / "python_script").write_text("#!/usr/bin/env python3\nprint('Hello from python')")
    (tmpdir / "test.txt").write_text("Just a text file")


    # Change to the temp directory so the tests can find these files
    os.chdir(tmpdir)
    yield  # This makes the fixture available, and the code after yield runs at teardown

    # Go back to where we started. Very important!
    os.chdir(os.path.dirname(__file__))
    # No explicit cleanup of the temporary directory is needed.  pytest handles it!

def test_is_file():
    assert parser.is_file(TEST_FILE_1) == True
    assert parser.is_file(TEST_SNIPPET) == False

def test_is_snippet():
    assert parser.is_snippet(TEST_SNIPPET) == True
    assert parser.is_snippet(TEST_FILE_1) == False

def test_is_terminal_log():
    terminal_log = f"""
{parser.placeholder('START TERMINAL METADATA')}
Session: Some Terminal
{parser.placeholder('END TERMINAL METADATA')}
Some terminal output.
{parser.placeholder('END OF FILE')}
"""
    assert parser.is_terminal_log(terminal_log) == True
    assert parser.is_terminal_log(TEST_FILE_1) == False

def test_match_code_block():
    # Positive test cases
    assert re.search(parser.match_code_block(), TEST_FILE_1, re.DOTALL)
    assert re.search(parser.match_code_block(), TEST_SNIPPET, re.DOTALL)

    # Negative test cases (shouldn't match a full block)
    assert not re.search(parser.match_code_block(), "random text", re.DOTALL)

def test_match_file(file_to_match="test_file_1.py"):
    assert re.search(parser.match_file(file_to_match), TEST_FILE_1, re.DOTALL)
    assert not re.search(parser.match_file("wrong_file.py"), TEST_FILE_1, re.DOTALL)

def test_match_snippet():
    assert re.search(parser.match_snippet(), TEST_SNIPPET, re.DOTALL)

    # Negative: should not match file
    assert not re.search(parser.match_snippet(), TEST_FILE_1, re.DOTALL)

def test_match_before_conversation_history():
    test_string = f"Some preamble\n{parser.CONVERSATION_START_SEP}The conversation"
    match = re.match(parser.match_before_conversation_history(), test_string, re.DOTALL)
    assert match
    assert match.group(1) == "Some preamble\n"

    # Negative case
    test_string_2 = f"No conversation sep"
    match = re.match(parser.match_before_conversation_history(), test_string_2, re.DOTALL)
    assert not match

def test_file_block():
    content = "print('Hello')"
    expected = f"""
{parser.placeholder('START FILE METADATA')}
Path: test.py
Language: python
Version: 1
Part: 1
NoMoreParts: False
{parser.placeholder('END FILE METADATA')}
{content}
{parser.placeholder('END OF FILE')}

{parser.placeholder('START FILE METADATA')}
Path: test.py
Language: python
Version: 1
Part: 2
NoMoreParts: True
{parser.placeholder('END FILE METADATA')}
{content}
{parser.placeholder('END OF FILE')}
"""
    assert parser.file_block("test.py", content) == expected

def test_snippet_block():
    content = "print('Hello')"
    expected = f"""
{parser.placeholder('START CODE SNIPPET METADATA')}
Language: python
{parser.placeholder('END CODE SNIPPET METADATA')}
{content}
{parser.placeholder('END OF FILE')}
"""
    assert parser.snippet_block(content, "python") == expected

def test_terminal_log_block():
    content = "Some terminal output"
    expected = f"""
{parser.placeholder('START TERMINAL METADATA')}
Session: My Terminal
{parser.placeholder('END TERMINAL METADATA')}
{content}
{parser.placeholder('END OF FILE')}
"""
    assert parser.terminal_log_block(content, "My Terminal") == expected

def test_find_files_multiple_versions():
    test_input = f"""
{parser.placeholder('START FILE METADATA')}
Path: test.py
Language: python
Version: 1
NoMoreParts: True
{parser.placeholder('END FILE METADATA')}
Version 1 content
{parser.placeholder('END OF FILE')}

{parser.placeholder('START FILE METADATA')}
Path: test.py
Language: python
Version: 2
NoMoreParts: True
{parser.placeholder('END FILE METADATA')}
Version 2 content
{parser.placeholder('END OF FILE')}
"""

    expected_output = [
        ['test.py', 2, 'Version 2 content', 'python', 1, True]
    ]

    assert parser.find_files(test_input) == expected_output

def test_parse_metadata():
    metadata_str = """
Path: test.py
Language: python
Version: 2
Part: 3
NoMoreParts: True
    """
    expected_metadata = {
        'Path': 'test.py',
        'Language': 'python',
        'Version': 2,
        'Part': 3,
        'NoMoreParts': True
    }
    assert parser.parse_metadata(metadata_str) == expected_metadata

    # Test with missing fields
    metadata_str_missing = """
Path: test.py
Language: python
    """
    expected_missing = {
        'Path': 'test.py',
        'Language': 'python',
        'Version': 1,  # Default
        'Part': 1,  # Default
        'NoMoreParts': False # Default
    }
    assert parser.parse_metadata(metadata_str_missing) == expected_missing

     # Test with extra spaces
    metadata_str_spaces = """
 Path :  test.py
Language  :  python
Version:   2
    """
    expected_spaces = {
        'Path': 'test.py',
        'Language': 'python',
        'Version': 2,
        'Part': 1,
        'NoMoreParts': False
    }
    assert parser.parse_metadata(metadata_str_spaces) == expected_spaces

    #Test with No Part, but with NoMoreParts
    metadata_str_no_part = """
Path: test.py
Language: python
Version: 1
NoMoreParts: True
"""
    expected_no_part = {
        'Path': 'test.py',
        'Language': 'python',
        'Version': 1,
        'NoMoreParts': True,
        'Part': 1 # Default
    }
    assert parser.parse_metadata(metadata_str_no_part) == expected_no_part

    # Test with only Part, no NoMoreParts (should default to False)
    metadata_str_only_part = """
    Path: test.py
    Language: python
    Version: 1
    Part: 2
    """
    expected_only_part = {
        'Path': 'test.py',
        'Language': 'python',
        'Version': 1,
        'Part': 2,
        'NoMoreParts': False
    }
    assert parser.parse_metadata(metadata_str_only_part) == expected_only_part