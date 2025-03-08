import unittest
import os
import re
import textwrap
import sys

src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.append(src_path)

from src import parser

class TestParser(unittest.TestCase):

    def setUp(self):
        """Setup temporary directory and files for testing."""
        self.test_dir = os.path.join(os.path.dirname(__file__), 'tmp')
        os.makedirs(self.test_dir, exist_ok=True)

        self.test_file1_path = os.path.join(self.test_dir, 'test_file1.py')
        with open(self.test_file1_path, 'w') as f:
            f.write("print('Hello from test_file1')")

        self.test_file2_path = os.path.join(self.test_dir, 'test_file2.txt')
        with open(self.test_file2_path, 'w') as f:
            f.write("This is a test file.")

    def tearDown(self):
        """Clean up the temporary directory and files."""
        for filename in os.listdir(self.test_dir):
            file_path = os.path.join(self.test_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(self.test_dir)

    def _create_test_file(self, file_name, content):
        file_path = os.path.join(self.test_dir, file_name)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path


    def _generate_file_metadata(self, path, language='python', version=1, part=1, no_more_parts=True):
        return f"""
{parser.FILE_METADATA_START}
Path: {path}
Language: {language}
Version: {version}
Part: {part}
NoMoreParts: {no_more_parts}
{parser.FILE_METADATA_END}
"""

    def _generate_snippet_metadata(self, language='python'):
        return f"""
{parser.SNIPPET_METADATA_START}
Language: {language}
{parser.SNIPPET_METADATA_END}
"""

    def test_find_file_references(self):
        content = "This is some text with a @file_reference.txt and another @one/two/test.py, and @invalid@ref."
        expected = ['file_reference.txt', 'one/two/test.py', 'invalid']
        actual = parser.find_file_references(content)
        self.assertEqual(actual, expected)

        content = "No file references here."
        expected = []
        actual = parser.find_file_references(content)
        self.assertEqual(actual, expected)

        content = "@"  # edge case
        expected = []
        actual = parser.find_file_references(content)
        self.assertEqual(actual, expected)

        content = "@@"
        expected = []
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

        content = "  @valid_ref  "  # test leading/trailing spaces
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
        test_file_path = "test_file.py"
        content = self._generate_file_metadata(test_file_path, no_more_parts=False) + "Some content"
        expected = (test_file_path, False)
        actual = parser.find_in_progress_file(content)
        self.assertEqual(actual, expected)

        test_file_path = "another_file.txt"
        content = self._generate_file_metadata(test_file_path, language="text", version=2, part=3, no_more_parts=True) + "More content"
        expected = (test_file_path, True)
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
        content = self._generate_snippet_metadata() + "print('Hello')"
        expected = "python"
        actual = parser.find_in_progress_snippet(content)
        self.assertEqual(actual, expected)


        content = self._generate_snippet_metadata(language="javascript") + "console.log('Hello');"
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
        self.assertEqual(parser.safe_int("10.5"), 1)
        self.assertEqual(parser.safe_int("-1"), -1)

    def test_find_files(self):
        content = self._generate_file_metadata("test_file.py") + "print('Hello')\n" + parser.END_OF_FILE
        expected = [("test_file.py", 1, "print('Hello')", "python", 1, True)]
        actual = parser.find_files(content)
        self.assertEqual(actual, expected)

        # Multiple parts
        content = (
            self._generate_file_metadata("test_file.py", no_more_parts=False) + "print('Hello')\n" + parser.END_OF_FILE +
            self._generate_file_metadata("test_file.py", part=2, no_more_parts=True) + "print('World')\n" + parser.END_OF_FILE
        )
        expected = [("test_file.py", 1, "print('Hello')print('World')", "python", 2, True)]
        actual = parser.find_files(content)
        self.assertEqual(actual, expected)

        # Multiple files and versions
        content = (
            self._generate_file_metadata("file1.py") + "content1\n" + parser.END_OF_FILE +
            self._generate_file_metadata("file2.txt", language="text") + "content2\n" + parser.END_OF_FILE +
            self._generate_file_metadata("file1.py", version=2) + "content3\n" + parser.END_OF_FILE
        )
        expected = [
            ("file1.py", 1, "content1", "python", 1, True),
            ("file2.txt", 1, "content2", "text", 1, True),
            ("file1.py", 2, "content3", "python", 1, True),
        ]
        actual = parser.find_files(content)
        self.assertEqual(actual, expected)

        # No files
        content = "No files here."
        expected = []
        actual = parser.find_files(content)
        self.assertEqual(actual, expected)

        # Missing fields
        content = f"""
{parser.FILE_METADATA_START}
Path: missing.txt
{parser.FILE_METADATA_END}
"""
        self.assertEqual(parser.find_files(content), [])

        # Empty file content
        content = self._generate_file_metadata("empty_file.py") + parser.END_OF_FILE
        expected = [("empty_file.py", 1, "", "python", 1, True)]
        actual = parser.find_files(content)
        self.assertEqual(actual, expected)


    def test_find_snippets(self):
        content = self._generate_snippet_metadata() + "print('Hello')\n" + parser.END_OF_FILE
        expected = [("python", "\nprint('Hello')\n")]
        actual = parser.find_snippets(content)
        self.assertEqual(actual, expected)

        # Multiple snippets
        content = (
            self._generate_snippet_metadata() + "print('Hello')\n" + parser.END_OF_FILE +
            self._generate_snippet_metadata(language="javascript") + "console.log('World')\n" + parser.END_OF_FILE
        )
        expected = [
            ("python", "\nprint('Hello')\n"),
            ("javascript", "\nconsole.log('World')\n"),
        ]
        actual = parser.find_snippets(content)
        self.assertEqual(actual, expected)

        #No snippets
        content = "No snippets here."
        expected = []
        actual = parser.find_snippets(content)
        self.assertEqual(actual, expected)

    def test_is_file(self):
        content = self._generate_file_metadata("test.txt")
        self.assertTrue(parser.is_file(content))

        content = self._generate_snippet_metadata()
        self.assertFalse(parser.is_file(content))

        content = "Just some text"
        self.assertFalse(parser.is_file(content))

    def test_is_snippet(self):
        content = self._generate_snippet_metadata()
        self.assertTrue(parser.is_snippet(content))

        content = self._generate_file_metadata("test.txt")
        self.assertFalse(parser.is_snippet(content))

        content = "Just some text"
        self.assertFalse(parser.is_snippet(content))

    def test_is_terminal_log(self):
        content = f"{parser.TERMINAL_METADATA_START}\nSession: test\n{parser.TERMINAL_METADATA_END}"
        self.assertTrue(parser.is_terminal_log(content))

        content = self._generate_file_metadata("test.txt")
        self.assertFalse(parser.is_terminal_log(content))

        content = "Just some text"
        self.assertFalse(parser.is_terminal_log(content))

    def test_match_code_block(self):
        content = self._generate_file_metadata("test_file.py") + "print('Hello')\n" + parser.END_OF_FILE
        self.assertTrue(bool(re.search(parser.match_code_block(), content, flags=re.DOTALL)))

        content = self._generate_snippet_metadata() + "print('Hello')\n" + parser.END_OF_FILE
        self.assertTrue(bool(re.search(parser.match_code_block(), content, flags=re.DOTALL)))

        content = "No code blocks here."
        self.assertFalse(bool(re.search(parser.match_code_block(), content, flags=re.DOTALL)))

    def test_match_file(self):
        content = self._generate_file_metadata("test_file.py") + "print('Hello')\n" + parser.END_OF_FILE
        self.assertTrue(bool(re.search(parser.match_file('test_file.py'), content, flags=re.DOTALL)))
        self.assertFalse(bool(re.search(parser.match_file('other_file.py'), content, flags=re.DOTALL)))

    def test_match_snippet(self):
        content = self._generate_snippet_metadata() + "print('Hello')\n" + parser.END_OF_FILE
        self.assertTrue(bool(re.search(parser.match_snippet(), content, flags=re.DOTALL)))

        content = self._generate_file_metadata("test_file.py") + "print('Hello')\n" + parser.END_OF_FILE
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
NoMoreParts: True
{parser.FILE_METADATA_END}
print('Hello')
{parser.END_OF_FILE}
"""
        actual = parser.file_block(file_path, content)
        self.assertEqual(textwrap.dedent(actual), textwrap.dedent(expected))

        # Language override
        expected_js = f"""
{parser.FILE_METADATA_START}
Path: test.py
Language: javascript
Version: 1
Part: 1
NoMoreParts: True
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
        self.assertEqual(parser.get_language_from_extension("test"), "text")

        # Shebang
        self._create_test_file('test.sh', "#!/bin/bash\necho 'Hello'")
        self.assertEqual(parser.get_language_from_extension(os.path.join(self.test_dir, 'test.sh')), "bash")

        #Invalid file
        self.assertEqual(parser.get_language_from_extension("invalid.unknown"), "text")

        # Test no file
        self.assertEqual(parser.get_language_from_extension("no_such_file.py"), 'text')

    def test_get_program_from_shebang(self):
        self.assertEqual(parser.get_program_from_shebang("#!/usr/bin/env python3"), "python3")
        self.assertEqual(parser.get_program_from_shebang("#!/bin/bash"), "bash")
        self.assertEqual(parser.get_program_from_shebang("#!/usr/bin/python"), "python")
        self.assertEqual(parser.get_program_from_shebang("#!"), None)
        self.assertEqual(parser.get_program_from_shebang(""), None)
        self.assertEqual(parser.get_program_from_shebang("#!/usr/bin/env"), None)
        self.assertEqual(parser.get_program_from_shebang('invalid'), None)

if __name__ == '__main__':
    unittest.main()