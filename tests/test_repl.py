import unittest
import os
import tempfile
import shutil
from prompt_toolkit.completion import Completion
from src.repl import FilePathCompleter, CommandCompleter, create_prompt_session
from prompt_toolkit.document import Document

class TestRepl(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        # Create mock files and directories for testing FilePathCompleter
        os.makedirs(os.path.join(self.test_dir, "src", "subdir"), exist_ok=True)
        with open(os.path.join(self.test_dir, "src", "file1.py"), "w") as f:
            f.write("print('hello')")
        with open(os.path.join(self.test_dir, "src", "subdir", "file2.txt"), "w") as f:
            f.write("some text")
        with open(os.path.join(self.test_dir, ".gitignore"), "w") as f:
            f.write("*.txt\n")

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def test_file_path_completer(self):
        completer = FilePathCompleter()

        # Test basic completion
        document = Document(text="@file1", cursor_position=6)
        completions = list(completer.get_completions(document, None))
        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0].text, 'src/file1.py')
        self.assertEqual(completions[0].start_position, -5)


        # Test with ignored files
        document = Document(text="@file2", cursor_position=6)
        completions = list(completer.get_completions(document, None))
        self.assertEqual(len(completions), 0)  # file2.txt is ignored

        # Test subdirectory
        document = Document(text="@subdir/file2", cursor_position=13)
        completions = list(completer.get_completions(document, None))
        self.assertEqual(len(completions), 0) # file2.txt is ignored

        # Test no match
        document = Document(text="@nonexistent", cursor_position=12)
        completions = list(completer.get_completions(document, None))
        self.assertEqual(len(completions), 0)

        # Test with no @ symbol
        document = Document(text="file1", cursor_position=5)
        completions = list(completer.get_completions(document, None))
        self.assertEqual(len(completions), 0)

    def test_file_path_completer_load_ignore_patterns(self):
        completer = FilePathCompleter()

        # Test .gitignore loading
        self.assertIn("*.txt", completer.ignore_patterns)

        # Test default patterns loading
        self.assertIn(".git*", completer.ignore_patterns)

    def test_file_path_completer_is_ignored(self):
        completer = FilePathCompleter()
        # Mock the spec for controlled testing.  Don't rely on .gitignore
        completer.spec = pathspec.PathSpec.from_lines('gitwildmatch', ['*.txt'])

        self.assertTrue(completer.is_ignored("test.txt"))
        self.assertFalse(completer.is_ignored("test.py"))

    def test_command_completer(self):
        completer = CommandCompleter(['reset', 'refresh', 'exit'])

        # Test basic completion
        document = Document(text="$re", cursor_position=3)
        completions = list(completer.get_completions(document, None))
        self.assertEqual(len(completions), 2)
        self.assertIn(Completion('reset', start_position=-2), completions)
        self.assertIn(Completion('refresh', start_position=-2), completions)

        # Test full command
        document = Document(text="$exit", cursor_position=5)
        completions = list(completer.get_completions(document, None))
        self.assertEqual(len(completions), 1)
        self.assertEqual(completions[0].text, 'exit')

        # Test no match
        document = Document(text="$abc", cursor_position=4)
        completions = list(completer.get_completions(document, None))
        self.assertEqual(len(completions), 0)

        # Test with no $ symbol
        document = Document(text="exit", cursor_position=4)
        completions = list(completer.get_completions(document, None))
        self.assertEqual(len(completions), 0)

    def test_create_prompt_session(self):
        # This is more of an integration test, just checking for basic creation
        session = create_prompt_session()
        self.assertIsNotNone(session)
        self.assertTrue(hasattr(session, 'prompt'))

if __name__ == '__main__':
    unittest.main()