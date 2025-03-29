import os
import re
from prompt_toolkit.styles import Style
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.completion import FuzzyCompleter, Completer, Completion
from prompt_toolkit.shortcuts import CompleteStyle
import pathspec

from .config import DEFAULT_IGNORE_PATTERNS

key_bindings = KeyBindings()

@key_bindings.add(Keys.Up)
def _(event):
    event.current_buffer.history_backward()

@key_bindings.add(Keys.Down)
def _(event):
    event.current_buffer.history_forward()

class FilePathCompleter(Completer):
    def __init__(self, cwd=os.getcwd()):
        self.ignore_patterns = self.load_ignore_patterns()
        self.spec = pathspec.PathSpec.from_lines('gitwildmatch', self.ignore_patterns)
        self.cwd = cwd

    def load_ignore_patterns(self):
        ignore_patterns = [] + DEFAULT_IGNORE_PATTERNS
        for ignore_file in ['.gitignore']:
            if os.path.exists(ignore_file):
                with open(ignore_file, encoding='utf-8') as f:
                    ignore_patterns.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])
        return ignore_patterns

    def is_ignored(self, path):
        return self.spec.match_file(path)

    def get_completions(self, document, __complete_event__):
        word_before_cursor = document.get_word_before_cursor()

        # Check if we are completing a command or a path
        if '@' not in word_before_cursor:
            return

        for root, dirs, items in os.walk(self.cwd, topdown=True):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self.is_ignored(os.path.join(root, d))]
            for item in items:
                path = re.sub(r'^\./', '', os.path.relpath(os.path.join(root, item)))
                if not self.is_ignored(path) and item.startswith(word_before_cursor[1:]):  # Skip the '@' character
                    yield Completion(path, start_position=-len(word_before_cursor) + 1)


class CommandCompleter(Completer):
    def __init__(self, commands):
        self.commands = commands

    def get_completions(self, document, __complete_event__):
        word_before_cursor = document.get_word_before_cursor()

        if '$' not in word_before_cursor:
            return

        for command in self.commands:
            if command.startswith(word_before_cursor[1:]):
                yield Completion(command, start_position=-len(word_before_cursor) + 1)

def create_prompt_session(cwd):
    prompt_style = Style.from_dict({'': '#8CB9B3 bold'})

    file_completer = FuzzyCompleter(FilePathCompleter(cwd))
    command_completer = FuzzyCompleter(CommandCompleter(['reset', 'refresh', 'exit', 'continue']))

    # Combine completers
    class CombinedCompleter(Completer):
        def get_completions(self, document, complete_event):
            # Use file completer if '@' detected, otherwise use command completer
            if '@' in document.text:
                if file_completer:
                    yield from file_completer.get_completions(document, complete_event)
            elif '$' in document.text:
                if command_completer:
                    yield from command_completer.get_completions(document, complete_event)

    return PromptSession(
        style=prompt_style,
        multiline=True,
        key_bindings=key_bindings,
        completer=CombinedCompleter(),
        complete_style=CompleteStyle.MULTI_COLUMN)
