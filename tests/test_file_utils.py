import unittest
import os
import shutil
import tempfile
from unittest.mock import patch
from src.parser import uid
from src.file_utils import (
    load_ignore_patterns,
    is_ignored,
    generate_diff,
    generate_project_structure,
    generate_project_file_contents,
    get_file_contents,
    prune_file_history,
    human_format_number,
    generate_project_file_list
)
import pathspec

class TestFileUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create some mock files and directories
        os.makedirs(os.path.join(self.test_dir, "src", "subdir"), exist_ok=True)
        with open(os.path.join(self.test_dir, "src", "file1.py"), "w") as f:
            f.write("print('hello')")
        with open(os.path.join(self.test_dir, "src", "subdir", "file2.txt"), "w") as f:
            f.write("some text")
        with open(os.path.join(self.test_dir, ".gitignore"), "w") as f:
            f.write("*.txt\n")  # Ignore text files

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def test_load_ignore_patterns(self):
        # Test default patterns
        patterns = load_ignore_patterns()
        self.assertIn('.git*', patterns)

        # Test with .gitignore
        patterns = load_ignore_patterns()
        self.assertIn('*.txt', patterns)

        # Test with extra_ignore_patterns
        patterns = load_ignore_patterns(extra_ignore_patterns=['*.pyc'])
        self.assertIn('*.pyc', patterns)

        # Test with include_patterns (overrides ignores)
        patterns = load_ignore_patterns(include_patterns=['*.txt'])
        self.assertEqual(patterns, ['*.txt'])  # Only include pattern should be present

        # Test combinations
        patterns = load_ignore_patterns(extra_ignore_patterns=['*.log'], include_patterns=['*.txt'])
        self.assertEqual(patterns, ['*.txt'])  # include_patterns takes precedence

        # Test with empty and comment lines in .gitignore
        with open(os.path.join(self.test_dir, ".gitignore"), "w") as f:
            f.write("\n# comment\n*.tmp\n\n")
        patterns = load_ignore_patterns()
        self.assertIn('*.tmp', patterns)
        self.assertNotIn('', patterns)
        self.assertNotIn('# comment', patterns)


    def test_is_ignored(self):
        spec = pathspec.PathSpec.from_lines('gitwildmatch', ['*.txt'])
        self.assertTrue(is_ignored('test.txt', spec))
        self.assertFalse(is_ignored('test.py', spec))
        self.assertTrue(is_ignored('subdir/test.txt', spec))  # Check subdirectory

    def test_generate_diff(self):
        # Existing file with changes
        with open(os.path.join(self.test_dir, "src", "file1.py"), "w") as f:
            f.write("print('hello world')")
        diff = generate_diff(os.path.join("src", "file1.py"), "print('goodbye')")
        self.assertIn("-print('hello world')", diff)
        self.assertIn("+print('goodbye')", diff)

        # File not found
        new_content = "new file content"
        diff = generate_diff("nonexistent_file.py", new_content)
        self.assertEqual(diff, new_content)  # Returns new content

        # Identical content
        with open(os.path.join(self.test_dir, "src", "file1.py"), "w") as f:
            f.write("print('hello')")
        diff = generate_diff(os.path.join("src", "file1.py"), "print('hello')")
        self.assertEqual(diff, "print('hello')")

    def test_generate_project_structure(self):
        # Simple structure
        structure = generate_project_structure()
        self.assertIn('"name": "src"', structure)
        self.assertIn('"name": "file1.py"', structure)
        self.assertIn('"name": "subdir"', structure)

        # With ignored files
        structure = generate_project_structure()
        self.assertNotIn("file2.txt", structure)  # Should be ignored due to .gitignore

        # Empty directory
        empty_dir = tempfile.mkdtemp()
        os.chdir(empty_dir)
        structure = generate_project_structure()
        self.assertIn('"id": "$root"', structure)
        self.assertIn('"name": "', structure)  # Root name should be empty string
        os.chdir(self.test_dir)
        shutil.rmtree(empty_dir)

        # Test sorting and root node
        structure = generate_project_structure()
        data = json.loads(structure)
        self.assertEqual(data[0]["id"], "$root") # Test the first item
        ids = [item["id"] for item in data]
        self.assertEqual(ids, sorted(ids))  # Check if sorted


    def test_generate_project_file_contents(self):
        # Without include_patterns
        contents = generate_project_file_contents()
        self.assertIn("print('hello')", contents)
        self.assertNotIn("some text", contents)  # .txt should be ignored

        # With include_patterns
        contents = generate_project_file_contents(include_patterns=['*.txt'])
        self.assertNotIn("print('hello')", contents)  # .py should not be included
        self.assertIn("some text", contents)

        #With ignored file
        contents = generate_project_file_contents(extra_ignore_patterns=['*.py'])
        self.assertNotIn("print('hello')", contents)


    def test_generate_project_file_list(self):
        # Without include_patterns
        file_list = generate_project_file_list()
        self.assertIn(os.path.join("src", "file1.py"), file_list)
        self.assertNotIn(os.path.join("src", "subdir", "file2.txt"), file_list)

        # With include_patterns
        file_list = generate_project_file_list(include_patterns=['*.txt'])
        self.assertNotIn(os.path.join("src", "file1.py"), file_list)
        self.assertIn(os.path.join("src", "subdir", "file2.txt"), file_list)

    def test_get_file_contents(self):
        # Existing file
        contents = get_file_contents(os.path.join("src", "file1.py"))
        self.assertIn("print('hello')", contents)
        self.assertIn("Language: python", contents)  # Check language

        # Non-existing file
        contents = get_file_contents("nonexistent_file.py")
        self.assertIn("Error reading", contents)

        #Test different extensions and shebang
        with open(os.path.join(self.test_dir, "src", "script.sh"), "w") as f:
            f.write("#!/bin/bash\necho 'hello'")
        contents = get_file_contents(os.path.join("src", "script.sh"))
        self.assertIn("Language: bash", contents)

        with open(os.path.join(self.test_dir, "src", "no_ext"), "w") as f:
            f.write("random text")
        contents = get_file_contents(os.path.join("src", "no_ext"))
        self.assertIn("Language: text", contents)


    def test_prune_file_history(self):
        history = [
            "Some text",
            f"{uid('START FILE METADATA')}\nPath: file1.py\n{{{END FILE METADATA}}}content", "More text",
            """ERROR: Expected files in response section but none were found.
            ERROR: --------------------
            ERROR: {{{START FILE METADATA}}}\nPath: file2.py\n{{{END FILE METADATA}}}content2{{{END OF
                                                                                                FILE}}}
            ERROR: --------------------""" ]

        prune_file_history("file1.py", history)

        self.assertNotIn("file1.py", history[1])  # Check if removed

        self.assertIn("file2.py", history[2])    # Make sure other files stay

        history = ["Some text"]
        prune_file_history("file1.py", history)
        self.assertEqual(history, ["Some text"]) #Should not change history

    def test_human_format_number(self):
        self.assertEqual(human_format_number(1000), '1.0K')
        self.assertEqual(human_format_number(1500), '1.5K')
        self.assertEqual(human_format_number(1234567), '1.2M')
        self.assertEqual(human_format_number(5), '5.0') # Test a small number
