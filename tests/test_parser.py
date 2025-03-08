import unittest
import os
import textwrap
import sys

src_path = os.path.join(os.path.dirname(__file__), 'src')

sys.path.append(src_path)

from src import parser

class TestParser(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory and files for testing.
        self.test_dir = os.path.join(os.path.dirname(__file__), 'tmp')
        os.makedirs(self.test_dir, exist_ok=True)

        self.test_file1_path = os.path.join(self.test_dir, 'test_file1.py')
        with open(self.test_file1_path, 'w') as f:
            f.write("print('Hello from test_file1')")

        self.test_file2_path = os.path.join(self.test_dir, 'test_file2.txt')
        with open(self.test_file2_path, 'w') as f:
            f.write("This is a test file.")

        self.test_file3_path = os.path.join(self.test_dir, 'test_file3.sh')
        with open(self.test_file3_path, 'w') as f:
            f.write("#!/bin/bash\necho 'Hello from test_file3'")

    def tearDown(self):
        # Clean up the temporary directory and files.
        for filename in os.listdir(self.test_dir):
            file_path = os.path.join(self.test_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(self.test_dir)

    def test_find_file_references(self):
        content = "This is some text with a @file_reference.txt and another @one/two/test.py, and @invalid@ref."
        expected = ['file_reference.txt', 'one/two/test.py', 'invalid']
        actual = parser.find_file_references(content)
        self.assertEqual(actual, expected)

        content = "No file references here."
        expected = []
        actual = parser.find_file_references(content)
        self.assertEqual(actual, expected)

        content = "@" # edge case - just the @
        expected = []  # should not pick this one up
        actual = parser.find_file_references(content)
        self.assertEqual(actual, expected)

        content = "@@"
        expected = [] # also don't pick up just @@
        actual = parser.find_file_references(content)
        self.assertEqual(actual, expected)

        content = "@valid_ref"
        expected = ["valid_ref"]
        actual = parser.find_file_references(content)
        self.assertEqual(actual, expected)

        content = "@valid-ref"
        expected = ["valid-ref"]
        actual = parser.find_file_references(content)
        self.assertEqual(actual, expected)

        content = "  @valid_ref  "
        expected = ["valid_ref"]
        actual = parser.find_file_references(content)
        self.assertEqual(actual, expected)

        content = "@valid_ref.py, other stuff"
        expected = ["valid_ref.py"]
        actual = parser.find_file_references(content)
        self.assertEqual(actual, expected)

        content = "@valid_ref.py.foo, other stuff"
        expected = ["valid_ref.py.foo"]
        actual = parser.find_file_references(content)
        self.assertEqual(actual, expected)


    def test_find_in_progress_file(self):
        content = f"""
{parser.FILE_METADATA_START}
Path: test_file.py
Language: python
Version: 1
Part: 1
NoMoreParts: False
{parser.FILE_METADATA_END}
Some content
"""
        expected = ("test_file.py", False)
        actual = parser.find_in_progress_file(content)
        self.assertEqual(actual, expected)

        content = f"""
{parser.FILE_METADATA_START}
Path: another_file.txt
Language: text
Version: 2
Part: 3
NoMoreParts: True
{parser.FILE_METADATA_END}
More content
"""
        expected = ("another_file.txt", True)
        actual = parser.find_in_progress_file(content)
        self.assertEqual(actual, expected)

        content = "No file metadata here."
        expected = None
        actual = parser.find_in_progress_file(content)
        self.assertEqual(actual, expected)

        # Incomplete metadata
        content = f"""
{parser.FILE_METADATA_START}
Path: incomplete.py
{parser.FILE_METADATA_END}
        """
        self.assertIsNone(parser.find_in_progress_file(content))

    def test_find_in_progress_snippet(self):
        content = f"""
{parser.SNIPPET_METADATA_START}
Language: python
{parser.SNIPPET_METADATA_END}
print('Hello')
"""
        expected = "python"
        actual = parser.find_in_progress_snippet(content)
        self.assertEqual(actual, expected)

        content = f"""
{parser.SNIPPET_METADATA_START}
Language: javascript
{parser.SNIPPET_METADATA_END}
console.log('Hello');
"""
        expected = "javascript"
        actual = parser.find_in_progress_snippet(content)
        self.assertEqual(actual, expected)

        content = "No snippet metadata here."
        expected = None
        actual = parser.find_in_progress_snippet(content)
        self.assertEqual(actual, expected)

    def test_safe_int(self):
        self.assertEqual(parser.safe_int("10"), 10)
        self.assertEqual(parser.safe_int(None), 1)
        self.assertEqual(parser.safe_int("abc"), 1)
        self.assertEqual(parser.safe_int("10.5"), 1)  # Test with float string.
        self.assertEqual(parser.safe_int("-1"), -1)  # Test negative

    def test_find_files(self):
        content = f"""
{parser.FILE_METADATA_START}
Path: test_file.py
Language: python
Version: 1
Part: 1
NoMoreParts: True
{parser.FILE_METADATA_END}
print('Hello')
{parser.END_OF_FILE}
"""
        expected = [("test_file.py", 1, "print('Hello')", "python", 1, True)]
        actual = parser.find_files(content)
        self.assertEqual(actual, expected)

        # Test multiple parts
        content = f"""
{parser.FILE_METADATA_START}
Path: test_file.py
Language: python
Version: 1
Part: 1
NoMoreParts: False
{parser.FILE_METADATA_END}
print('Hello')
{parser.END_OF_FILE}
{parser.FILE_METADATA_START}
Path: test_file.py
Language: python
Version: 1
Part: 2
NoMoreParts: True
{parser.FILE_METADATA_END}
print('World')
{parser.END_OF_FILE}
"""
        expected = [("test_file.py", 1, "print('Hello')print('World')", "python", 2, True)]
        actual = parser.find_files(content)
        self.assertEqual(actual, expected)

        # Test multiple files and versions
        content = f"""
{parser.FILE_METADATA_START}
Path: file1.py
Language: python
Version: 1
Part: 1
NoMoreParts: True
{parser.FILE_METADATA_END}
content1
{parser.END_OF_FILE}
{parser.FILE_METADATA_START}
Path: file2.txt
Language: text
Version: 1
Part: 1
NoMoreParts: True
{parser.FILE_METADATA_END}
content2
{parser.END_OF_FILE}
{parser.FILE_METADATA_START}
Path: file1.py
Language: python
Version: 2
Part: 1
NoMoreParts: True
{parser.FILE_METADATA_END}
content3
{parser.END_OF_FILE}
"""
        expected = [
            ("file1.py", 1, "content1", "python", 1, True),
            ("file2.txt", 1, "content2", "text", 1, True),
            ("file1.py", 2, "content3", "python", 1, True),
        ]
        actual = parser.find_files(content)
        self.assertEqual(actual, expected)

        # Test no files
        content = "No files here."
        expected = []
        actual = parser.find_files(content)
        self.assertEqual(actual, expected)

        # Test missing fields
        content = f"""
{parser.FILE_METADATA_START}
Path: missing.txt
{parser.FILE_METADATA_END}
"""
        # Expect empty results, as it won't match.
        self.assertEqual(parser.find_files(content), [])

        # Test file with no content
        content = f"""
{parser.FILE_METADATA_START}
Path: empty_file.py
Language: python
Version: 1
Part: 1
NoMoreParts: True
{parser.FILE_METADATA_END}

{parser.END_OF_FILE}
"""
        expected = [("empty_file.py", 1, "", "python", 1, True)]
        actual = parser.find_files(content)
        self.assertEqual(actual, expected)

    def test_find_snippets(self):
        content = f"""
{parser.SNIPPET_METADATA_START}
Language: python
{parser.SNIPPET_METADATA_END}
print('Hello')
{parser.END_OF_FILE}
"""
        expected = [("python", "\nprint('Hello')\n")]
        actual = parser.find_snippets(content)
        self.assertEqual(actual, expected)

        # Test multiple snippets
        content = f"""
{parser.SNIPPET_METADATA_START}
Language: python
{parser.SNIPPET_METADATA_END}
print('Hello')
{parser.END_OF_FILE}
{parser.SNIPPET_METADATA_START}
Language: javascript
{parser.SNIPPET_METADATA_END}
console.log('World')
{parser.END_OF_FILE}
"""
        expected = [
            ("python", "\nprint('Hello')\n"),
            ("javascript", "\nconsole.log('World')\n"),
        ]
        actual = parser.find_snippets(content)
        self.assertEqual(actual, expected)

        # Test no snippets
        content = "No snippets here."
        expected = []
        actual = parser.find_snippets(content)
        self.assertEqual(actual, expected)

    def test_is_file(self):
        content = f"{parser.FILE_METADATA_START}\nPath: test.txt\n{parser.FILE_METADATA_END}"
        self.assertTrue(parser.is_file(content))

        content = f"{parser.SNIPPET_METADATA_START}\nLanguage: python\n{parser.SNIPPET_METADATA_END}"
        self.assertFalse(parser.is_file(content))

        content = "Just some text"
        self.assertFalse(parser.is_file(content))

    def test_is_snippet(self):
        content = f"{parser.SNIPPET_METADATA_START}\nLanguage: python\n{parser.SNIPPET_METADATA_END}"
        self.assertTrue(parser.is_snippet(content))

        content = f"{parser.FILE_METADATA_START}\nPath: test.txt\n{parser.FILE_METADATA_END}"
        self.assertFalse(parser.is_snippet(content))

        content = "Just some text"
        self.assertFalse(parser.is_snippet(content))

    def test_is_terminal_log(self):
        content = f"{parser.TERMINAL_METADATA_START}\nSession: test\n{parser.TERMINAL_METADATA_END}"
        self.assertTrue(parser.is_terminal_log(content))

        content = f"{parser.FILE_METADATA_START}\nPath: test.txt\n{parser.FILE_METADATA_END}"
        self.assertFalse(parser.is_terminal_log(content))

        content = "Just some text"
        self.assertFalse(parser.is_terminal_log(content))

    def test_match_code_block(self):
        content = f"""
{parser.FILE_METADATA_START}
Path: test_file.py
Language: python
{parser.FILE_METADATA_END}
print('Hello')
{parser.END_OF_FILE}
"""
        self.assertTrue(bool(re.search(parser.match_code_block(), content, flags=re.DOTALL)))

        content = f"""
{parser.SNIPPET_METADATA_START}
Language: python
{parser.SNIPPET_METADATA_END}
print('Hello')
{parser.END_OF_FILE}
"""
        self.assertTrue(bool(re.search(parser.match_code_block(), content, flags=re.DOTALL)))

        content = "No code blocks here."
        self.assertFalse(bool(re.search(parser.match_code_block(), content, flags=re.DOTALL)))

    def test_match_file(self):
        content = f"""
{parser.FILE_METADATA_START}
Path: test_file.py
Language: python
{parser.FILE_METADATA_END}
print('Hello')
{parser.END_OF_FILE}
"""
        self.assertTrue(bool(re.search(parser.match_file('test_file.py'), content, flags=re.DOTALL)))
        self.assertFalse(bool(re.search(parser.match_file('other_file.py'), content, flags=re.DOTALL)))
    def test_match_snippet(self):
        content = f"""
{parser.SNIPPET_METADATA_START}
Language: python
{parser.SNIPPET_METADATA_END}
print('Hello')
{parser.END_OF_FILE}
"""
        self.assertTrue(bool(re.search(parser.match_snippet(), content, flags=re.DOTALL)))

        content = f"""
{parser.FILE_METADATA_START}
Path: test_file.py
Language: python
{parser.FILE_METADATA_END}
print('Hello')
{parser.END_OF_FILE}
"""
        self.assertFalse(bool(re.search(parser.match_snippet(), content, flags=re.DOTALL)))

        content = "No snippets here."
        self.assertFalse(bool(re.search(parser.match_snippet(), content, flags=re.DOTALL)))

    def test_match_before_conversation_history(self):
        content = f"Some text before{parser.CONVERSATION_START_SEP}and some text after."
        match = re.match(parser.match_before_conversation_history(), content, flags=re.DOTALL)
        self.assertEqual(match.group(1), "Some text before")

        content = f"Only text before {parser.CONVERSATION_START_SEP}"
        match = re.match(parser.match_before_conversation_history(), content, flags=re.DOTALL)
        self.assertEqual(match.group(1), "Only text before ")

        content = f"{parser.CONVERSATION_START_SEP}Only text after"
        match = re.match(parser.match_before_conversation_history(), content, flags=re.DOTALL)
        self.assertEqual(match.group(1), "")

        content = "No conversation history here."
        match = re.match(parser.match_before_conversation_history(), content, flags=re.DOTALL)
        self.assertIsNone(match)

    def test_file_block(self):
        content = "print('Hello')"
        file_path = "test.py"
        expected = f"""
{parser.FILE_METADATA_START}
Path: test.py
Language: python
Version: 1
Part: 1
{parser.FILE_METADATA_END}
print('Hello')
{parser.END_OF_FILE}
"""
        actual = parser.file_block(file_path, content)
        self.assertEqual(textwrap.dedent(actual), textwrap.dedent(expected))

        # Test with language override
        expected_js = f"""
{parser.FILE_METADATA_START}
Path: test.py
Language: javascript
Version: 1
Part: 1
{parser.FILE_METADATA_END}
print('Hello')
{parser.END_OF_FILE}
"""
        actual_js = parser.file_block(file_path, content, language='javascript')
        self.assertEqual(textwrap.dedent(actual_js), textwrap.dedent(expected_js))

    def test_snippet_block(self):
        content = "print('Hello')"
        language = "python"
        expected = f"""
{parser.SNIPPET_METADATA_START}
Language: python
{parser.SNIPPET_METADATA_END}
print('Hello')
{parser.END_OF_FILE}
"""
        actual = parser.snippet_block(content, language)
        self.assertEqual(textwrap.dedent(actual), textwrap.dedent(expected))

    def test_terminal_log_block(self):
        content = "Some terminal output"
        title = "Test Session"
        expected = f"""
{parser.TERMINAL_METADATA_START}
Session: {title}
{parser.TERMINAL_METADATA_END}
{content}
{parser.END_OF_FILE}
"""
        actual = parser.terminal_log_block(content, title)
        self.assertEqual(textwrap.dedent(actual), textwrap.dedent(expected))

    def test_get_language_from_extension(self):
        self.assertEqual(parser.get_language_from_extension("test.py"), "python")
        self.assertEqual(parser.get_language_from_extension("test.js"), "javascript")
        self.assertEqual(parser.get_language_from_extension("test.txt"), "text")
        self.assertEqual(parser.get_language_from_extension("test"), "text")  # No extension

        # Test shebang
        with open(os.path.join(self.test_dir, 'test.sh'), 'w') as f:
            f.write("#!/bin/bash\necho 'Hello'")
        self.assertEqual(parser.get_language_from_extension(os.path.join(self.test_dir, 'test.sh')), "bash")

        # Test invalid file
        self.assertEqual(parser.get_language_from_extension("invalid.unknown"), "text")

        # Test no file
        self.assertEqual(parser.get_language_from_extension("no_such_file.py"), 'text')

    def test_get_program_from_shebang(self):
        self.assertEqual(parser.get_program_from_shebang("#!/usr/bin/env python3"), "python3")
        self.assertEqual(parser.get_program_from_shebang("#!/bin/bash"), "bash")
        self.assertEqual(parser.get_program_from_shebang("#!/usr/bin/python"), "python")
        self.assertEqual(parser.get_program_from_shebang("#!"), None)
        self.assertEqual(parser.get_program_from_shebang(""), None) # Empty string
        self.assertEqual(parser.get_program_from_shebang("#!/usr/bin/env"), None) # Incomplete env shebang
        self.assertEqual(parser.get_program_from_shebang('invalid'), None)

if __name__ == '__main__':
    unittest.main()
