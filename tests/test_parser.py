import pytest
import os
import sys

# Make sure the src directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import src.parser as parser

# Helper to create delimiter strings using the placeholder function
ph = parser.placeholder

FILE_METADATA_START = ph('START FILE METADATA')
FILE_METADATA_END = ph('END FILE METADATA')
SNIPPET_METADATA_START = ph('START CODE SNIPPET METADATA')
SNIPPET_METADATA_END = ph('END CODE SNIPPET METADATA')
END_OF_FILE = ph('END OF FILE')
END_OF_SNIPPET = ph('END OF CODE SNIPPET')

def test_find_file_references():
    content_no_refs = "This is some text without file references."
    content_with_refs = "Please check @file1.py and also @path/to/file2.txt, maybe @file3."
    content_with_punctuation = "Look at @file4.py! And @file5.c?"
    content_mixed = "Reference @file6.js, then some text, then @another/file.ts."
    content_edge_cases = "@start_of_string @middle.txt @end_of_string.?"

    assert parser.find_file_references(content_no_refs) == []
    assert parser.find_file_references(content_with_refs) == ["file1.py", "path/to/file2.txt", "file3"]
    assert parser.find_file_references(content_with_punctuation) == ["file4.py", "file5.c"]
    assert parser.find_file_references(content_mixed) == ["file6.js", "another/file.ts"]
    assert parser.find_file_references(content_edge_cases) == ["start_of_string", "middle.txt", "end_of_string"]


def test_parse_metadata_basic():
    metadata_str = "Path: my/file.py\nLanguage: python\nVersion: 3\nPart: 2"
    expected = {'Path': 'my/file.py', 'Language': 'python', 'Version': 3, 'Part': 2, 'NoMoreParts': False}
    assert parser.parse_metadata(metadata_str) == expected

def test_parse_metadata_defaults():
    metadata_str_no_part_version = "Path: my/file.py\nLanguage: python"
    expected_no_part_version = {'Path': 'my/file.py', 'Language': 'python', 'Version': 1, 'Part': 1, 'NoMoreParts': False}
    assert parser.parse_metadata(metadata_str_no_part_version) == expected_no_part_version

    metadata_str_only_part = "Path: my/file.py\nPart: 5"
    expected_only_part = {'Path': 'my/file.py', 'Version': 1, 'Part': 5, 'NoMoreParts': False}
    assert parser.parse_metadata(metadata_str_only_part) == expected_only_part

    metadata_str_only_version = "Path: my/file.py\nVersion: 2"
    expected_only_version = {'Path': 'my/file.py', 'Version': 2, 'Part': 1, 'NoMoreParts': False}
    assert parser.parse_metadata(metadata_str_only_version) == expected_only_version

def test_parse_metadata_no_more_parts():
    metadata_str_true = "Path: my/file.py\nNoMoreParts: True\nVersion: 2"
    # Part becomes 0 when NoMoreParts is True
    expected_true = {'Path': 'my/file.py', 'NoMoreParts': True, 'Version': 2, 'Part': 0}
    assert parser.parse_metadata(metadata_str_true) == expected_true

    metadata_str_false = "Path: my/file.py\nNoMoreParts: false"
    # Part becomes 0 when NoMoreParts is explicitly false too? Yes, according to implementation.
    expected_false = {'Path': 'my/file.py', 'NoMoreParts': False, 'Version': 1, 'Part': 0}
    assert parser.parse_metadata(metadata_str_false) == expected_false

    # NoMoreParts overrides Part number
    metadata_str_override = "Path: my/file.py\nNoMoreParts: True\nPart: 3"
    expected_override = {'Path': 'my/file.py', 'NoMoreParts': True, 'Part': 0, 'Version': 1}
    assert parser.parse_metadata(metadata_str_override) == expected_override

def test_find_files_single_part():
    content = f"""
Some text before.
{FILE_METADATA_START}
Path: single.txt
Language: text
Version: 1
Part: 1
{FILE_METADATA_END}
This is the content.
{END_OF_FILE}
{FILE_METADATA_START}
Path: single.txt
Language: text
Version: 1
NoMoreParts: True
{FILE_METADATA_END}
{END_OF_FILE}
Some text after.
"""
    expected = [
        ['single.txt', 1, 'This is the content.\n', 'text', 0, True] # Part is 0 because NoMoreParts is True
    ]
    assert parser.find_files(content) == expected

def test_find_files_multi_part():
    content = f"""
{FILE_METADATA_START}
Path: multi.py
Language: python
Version: 2
Part: 1
{FILE_METADATA_END}
Part one content.
{END_OF_FILE}
{FILE_METADATA_START}
Path: multi.py
Language: python
Version: 2
Part: 2
{FILE_METADATA_END}
Part two content.
{END_OF_FILE}
{FILE_METADATA_START}
Path: multi.py
Language: python
Version: 2
NoMoreParts: True
{FILE_METADATA_END}
{END_OF_FILE}
"""
    expected = [
        ['multi.py', 2, 'Part one content.Part two content.\n', 'python', 0, True]
    ]
    assert parser.find_files(content) == expected

def test_find_files_multiple_files():
    content = f"""
{FILE_METADATA_START}
Path: file1.txt
Version: 1
Part: 1
{FILE_METADATA_END}
Content 1.
{END_OF_FILE}
{FILE_METADATA_START}
Path: file1.txt
Version: 1
NoMoreParts: True
{FILE_METADATA_END}
{END_OF_FILE}

Some separator text.

{FILE_METADATA_START}
Path: file2.js
Language: javascript
Version: 3
Part: 1
{FILE_METADATA_END}
Content 2.
{END_OF_FILE}
{FILE_METADATA_START}
Path: file2.js
Language: javascript
Version: 3
NoMoreParts: True
{FILE_METADATA_END}
{END_OF_FILE}
"""
    expected = [
        ['file1.txt', 1, 'Content 1.\n', None, 0, True],
        ['file2.js', 3, 'Content 2.\n', 'javascript', 0, True]
    ]
    # Sort results because finditer doesn't guarantee order relative to other files
    result = sorted(parser.find_files(content), key=lambda x: x[0])
    assert result == expected

def test_find_files_multiple_versions():
    content = f"""
{FILE_METADATA_START}
Path: main.c
Version: 1
Part: 1
{FILE_METADATA_END}
Old content.
{END_OF_FILE}
{FILE_METADATA_START}
Path: main.c
Version: 1
NoMoreParts: True
{FILE_METADATA_END}
{END_OF_FILE}

{FILE_METADATA_START}
Path: main.c
Version: 2
Part: 1
{FILE_METADATA_END}
New content.
{END_OF_FILE}
{FILE_METADATA_START}
Path: main.c
Version: 2
NoMoreParts: True
{FILE_METADATA_END}
{END_OF_FILE}
"""
    expected = [
        ['main.c', 1, 'Old content.\n', None, 0, True],
        ['main.c', 2, 'New content.\n', None, 0, True]
    ]
    result = sorted(parser.find_files(content), key=lambda x: x[1]) # Sort by version
    assert result == expected

def test_find_files_incomplete():
    content_incomplete_part = f"""
{FILE_METADATA_START}
Path: incomplete.txt
Version: 1
Part: 1
{FILE_METADATA_END}
Some content here
""" # No END_OF_FILE or NoMoreParts block

    content_no_nomoreparts = f"""
{FILE_METADATA_START}
Path: incomplete.txt
Version: 1
Part: 1
{FILE_METADATA_END}
Some content here
{END_OF_FILE}
""" # Has END_OF_FILE but missing NoMoreParts block

    expected_incomplete = [
        ['incomplete.txt', 1, 'Some content here\n', None, 1, False] # NoMoreParts is False
    ]

    assert parser.find_files(content_incomplete_part, incomplete=True) == expected_incomplete
    # When incomplete=False (default), it shouldn't find the blocks without END_OF_FILE
    assert parser.find_files(content_incomplete_part) == []
    # When incomplete=False, it *should* find the block with END_OF_FILE, even without NoMoreParts
    # HACK: This currently fails because find_files expects a NoMoreParts block to consider a file complete.
    assert parser.find_files(content_no_nomoreparts) == expected_incomplete


def test_find_snippets():
    content = f"""
Some text.
{SNIPPET_METADATA_START}
Language: python
{SNIPPET_METADATA_END}
print("Hello")
def func():
    pass
{END_OF_SNIPPET}
More text.
{SNIPPET_METADATA_START}
Language: bash
{SNIPPET_METADATA_END}
echo "World"
ls -l
{END_OF_SNIPPET}
End text.
"""
    expected = [
        ('python', 'print("Hello")\ndef func():\n    pass\n'),
        ('bash', 'echo "World"\nls -l\n')
    ]
    assert parser.find_snippets(content) == expected

# Need to create dummy files for get_language_from_extension tests
@pytest.fixture(scope="module", autouse=True)
def create_dummy_files(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("parser_test_files")
    files_to_create = {
        "script.py": "#!/usr/bin/env python\nprint('hello')",
        "script.sh": "#!/bin/sh\necho 'hello'",
        "script_bash": "#!/usr/bin/env bash\necho 'hello'",
        "no_extension": "#!/usr/bin/python3\n# -*- coding: utf-8 -*-\nprint('test')",
        "plain.txt": "Simple text file.",
        "unknown_ext.foobar": "File with unknown extension.",
        "no_shebang.py": "print('no shebang python')",
        "tricky_shebang.sh": "#! /usr/bin/env sh -x\necho 'tricky'",
        "dot.file": "A file starting with a dot."
    }
    for name, content in files_to_create.items():
        file_path = tmp_dir / name
        file_path.write_text(content, encoding='utf-8')

    # Change working directory for the test module
    original_cwd = os.getcwd()
    os.chdir(tmp_dir)
    yield tmp_dir # Provide the temp directory path if needed, not strictly necessary here
    os.chdir(original_cwd) # Change back after tests


def test_get_language_from_extension():
    # Files that do exist (see create_dummy_files fixture)
    assert parser.get_language_from_extension("script.py") == "python"
    assert parser.get_language_from_extension("script.sh") == "sh"
    assert parser.get_language_from_extension("script_bash") == "bash" # Checks shebang overrides filename if no ext
    assert parser.get_language_from_extension("no_extension") == "python" # Checks shebang without extension
    assert parser.get_language_from_extension("plain.txt") == "text"
    assert parser.get_language_from_extension("unknown_ext.foobar") == "text" # Fallback for unknown
    assert parser.get_language_from_extension("no_shebang.py") == "python" # Uses extension if no shebang
    assert parser.get_language_from_extension("tricky_shebang.sh") == "sh" # Handles args in shebang
    assert parser.get_language_from_extension("dot.file") == "text" # Fallback for dotfiles without known ext/shebang

    # Files that do not exist
    assert parser.get_language_from_extension("not-existing-file.xyz") == "text"
    assert parser.get_language_from_extension("not-existing-script.py") == "python"
    assert parser.get_language_from_extension("not-existing-script.sh") == "sh"

def test_file_block_generation():
    file_path = "my/test.py"
    content = "print('hello')"
    expected = f"""
{FILE_METADATA_START}
Path: {file_path}
Language: python
Version: 1
Part: 1
{FILE_METADATA_END}
{content}
{END_OF_FILE}

{FILE_METADATA_START}
Path: {file_path}
Language: python
Version: 1
NoMoreParts: True
{FILE_METADATA_END}
{END_OF_FILE}
"""
    assert parser.file_block(file_path, content) == expected

def test_file_block_generation_with_version_language():
    file_path = "my/other.txt"
    content = "some data"
    expected = f"""
{FILE_METADATA_START}
Path: {file_path}
Language: customlang
Version: 5
Part: 1
{FILE_METADATA_END}
{content}
{END_OF_FILE}

{FILE_METADATA_START}
Path: {file_path}
Language: customlang
Version: 5
NoMoreParts: True
{FILE_METADATA_END}
{END_OF_FILE}
"""
    assert parser.file_block(file_path, content, language="customlang", version=5) == expected


def test_snippet_block_generation():
    content = "line1\nline2"
    language = "yaml"
    expected = f"""
{SNIPPET_METADATA_START}
Language: {language}
{SNIPPET_METADATA_END}
{content}
{END_OF_SNIPPET}
"""
    assert parser.snippet_block(content, language) == expected
