import google.generativeai as ai
import os
import sys
import threading
import time
import re
import uuid
import pathspec
import prompt_toolkit
import difflib
import json
from datetime import datetime, timezone
from collections import deque
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import FuzzyCompleter, Completer, Completion
from prompt_toolkit.shortcuts import CompleteStyle
from rich.console import Console
from rich.markdown import Markdown
from rich.theme import Theme

from .chat_prefix import FILE_PREFIX, FILE_TREE_PLACEHOLDER, FILES_PLACEHOLDER, CONVERSATION_START_SEP, CONVERSATION_END_SEP, FILES_END_SEP

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL')

PARSER_DEFINITION_FILE = 'src/chat_prefix.py'

history = []

verbose = False

debug_mode = False

loading = False

# Define a custom theme for Markdown
custom_theme = Theme({
    "markdown.code": "green",  # Style for inline code
    "markdown.code_block": "bright_green",  # Style for code blocks
    "markdown.h1": "bold #FFFFFF",  # Style for H1 headers
    "markdown.h2": "bold #AAAAAA",  # Style for H2 headers
    "markdown.h3": "bold #BBBBBB",  # Style for H3 headers
    "markdown.h4": "bold #CCCCCC",  # Style for H4 headers
    "markdown.h5": "bold #DDDDDD",  # Style for H5 headers
    "markdown.h6": "bold #EEEEEE",  # Style for H6 headers
    "markdown.strong": "bold",
    "markdown.em": "italic",
    "markdown.alert": "bold red",
    # You can add more styles as needed
})

console = Console(theme=custom_theme)  # Initialize Rich Console with custom theme

def verbose_logging():
    global verbose
    verbose = True

def debug_logging():
    verbose_logging()
    global debug_mode
    debug_mode = True

def debug(message):
    global debug_mode
    if debug_mode:
        print(message)

def info(message):
    global verbose
    if verbose:
        console.print(message, style="bold")

def error(message):
    console.print(message, style="bold red")

def tail(filename, n=10):
    try:
        with open(filename) as f:
            return deque(f, n)
    except FileNotFoundError:
        return None

def type_response_out(lines, delay=0.01):
    for string in lines:
        for char in string:
            sys.stdout.write(char)
            sys.stdout.flush()  # Force character output. Important!

            time.sleep(delay)
        print()  # Newline after each string

def prompt_prefix(extra_ignore_patterns=None):
    prompt_prefix_file = os.path.join(os.path.dirname(__file__), '../docs/background.txt')
    try:
        with open(prompt_prefix_file, 'r') as f:
            prefix = f.read()
    except FileNotFoundError:
        return "Could not find background.txt"

    project_structure = generate_project_structure(extra_ignore_patterns)
    project_files = generate_project_file_contents(extra_ignore_patterns)

    prefix = prefix.replace(FILE_TREE_PLACEHOLDER, f'\n{project_structure}\n')
    prefix = prefix.replace(FILES_PLACEHOLDER, f'\n{project_files}\n')

    debug(prefix)

    return prefix

def check_if_env_vars_set():
    if not GEMINI_API_KEY:
        error("Please set the GEMINI_API_KEY environment variable.")
        sys.exit(1)

    if not GEMINI_MODEL:
        error("Please set the GEMINI_MODEL environment variable (ex: GEMINI_MODEL=gemini-1.5-pro")
        sys.exit(1)

def generate_timestamped_uuid():
    uuid_val = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")  # ISO 8601 format in UTC
    return f"{timestamp}-{uuid_val}"

def extract_timestamp(filename):
    match = re.search(r"(\d{8}T\d{6}\.\d{6}Z)", filename)
    if match:
        timestamp_str = match.group(1)
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S.%fZ")
            return timestamp
        except ValueError:
            error(f"Invalid timestamp format: {timestamp_str}")
            return None
    else:
        error("Timestamp not found in filename")
        return None

def history_filename_for_directory(directory):
    """Generates a unique, consistent filename for the given directory."""
    # Use a hash of the absolute directory path for consistency.
    dir_hash = str(hash(os.path.abspath(directory)))
    filename = f"linus-history-{dir_hash}.txt"
    return os.path.join(os.path.dirname(__file__), '../tmp', filename)

def previous_history(resume_from=None):
    # NOTE: resume_from should not be used in this refactored version
    return last_session()

def last_session():
    history_file = history_filename_for_directory(os.getcwd())
    if os.path.exists(history_file):
        return (os.path.basename(history_file), datetime.now())  # Return a dummy timestamp, not used for sorting now
    else:
        return None

def loading_indicator():
    thinking_message = "Linus is thinking"
    while True:
        for i in range(4):  # Animate 3 dots
            dots = "." * i
            print(f'\r{thinking_message}{dots:<4}', end='', flush=True)
            time.sleep(0.2)
            if not loading:
                # Clear the entire line by printing spaces
                print('\r' + ' ' * (len(thinking_message) + 4), end='', flush=True)
                return

class FilePathCompleter(Completer):
    def __init__(self):
        self.ignore_patterns = self.load_ignore_patterns()
        self.spec = pathspec.PathSpec.from_lines('gitwildmatch', self.ignore_patterns)

    def load_ignore_patterns(self):
        ignore_patterns = []
        for ignore_file in ['.gitignore', '.ignore']:
            if os.path.exists(ignore_file):
                with open(ignore_file) as f:
                    ignore_patterns.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])
        return ignore_patterns

    def is_ignored(self, path):
        return self.spec.match_file(path)

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor()

        if '@' not in word_before_cursor:
            return

        for root, _, items in os.walk(os.getcwd()):
            for item in items:
                path = re.sub(r'^\./', '', os.path.relpath(os.path.join(root, item)))
                if not self.is_ignored(path) and item.startswith(word_before_cursor[1:]):  # Skip the '@' character
                    yield Completion(path, start_position=-len(word_before_cursor) + 1)

def generate_diff(file_path, current_content):
    try:
        with open(file_path, 'r') as f:
            file_content = f.readlines()
    except FileNotFoundError:
        return current_content  # If file not found, return current content

    diff = difflib.unified_diff(
        file_content,
        current_content.splitlines(keepends=True),
        fromfile=f"{file_path} (disk)",
        tofile=f"{file_path} (context)"
    )

    stringifed_diff = ''.join(diff)

    if len(stringifed_diff) == 0:
        # If no diff (i.e. we are re-adding the same file), return full (i.e. current) content
        return current_content

    return stringifed_diff

def generate_project_structure(extra_ignore_patterns=None):
    ignore_patterns = ['.*']  # Ignore dotfiles by default
    for ignore_file in ['.gitignore', '.ignore']:
        if os.path.exists(ignore_file):
            with open(ignore_file) as f:
                ignore_patterns.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])

    if extra_ignore_patterns:
        ignore_patterns.extend(extra_ignore_patterns)

    spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)

    file_tree = [{
        "id": "$root",
        "name": os.path.basename(os.getcwd()),
        "parent": None,
        "type": "directory"
    }]

    for root, dirs, files in os.walk(os.getcwd()):
        relative_path = os.path.relpath(root, os.getcwd())
        relative_path = '' if relative_path == '.' else relative_path

        dirs[:] = [dir for dir in dirs if not spec.match_file(os.path.join(relative_path, dir))]
        files[:] = [file for file in files if not spec.match_file(os.path.join(relative_path, file))]

        for dir in dirs:
            dir_path = os.path.join(relative_path, dir)
            dir_parent = os.path.dirname(dir_path)

            file_tree.append({
                "id": dir_path,
                "name": os.path.basename(dir_path),
                "parent": dir_parent != '.' and dir_parent or "$root",
                "type": "directory"
            })

        for file in files:
            file_path = os.path.join(relative_path, file)
            file_parent = os.path.dirname(file_path)

            file_tree.append({
                "id": file_path,
                "name": os.path.basename(file),
                "parent": file_parent != '.' and file_parent or "$root",
                "type": "file"
            })

    file_tree = sorted(file_tree, key=lambda x: x['id'])

    return json.dumps(file_tree, indent=2)

def generate_project_file_contents(extra_ignore_patterns=None):
    ignore_patterns = ['.*']  # Ignore dotfiles by default
    for ignore_file in ['.gitignore', '.ignore']:
        if os.path.exists(ignore_file):
            with open(ignore_file) as f:
                ignore_patterns.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])

    if extra_ignore_patterns:
        ignore_patterns.extend(extra_ignore_patterns)

    spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)
    output = ""

    for root, _, files in os.walk(os.getcwd()):
        relative_path = os.path.relpath(root, os.getcwd())
        if relative_path == '.':
            relative_path = ''

        # Output files and their contents
        for file in files:
            file_path = os.path.join(relative_path, file)
            if not spec.match_file(file_path):
                output += get_file_contents(file_path)

    return output

def get_file_contents(file_path):
    try:
        with open(file_path, 'r') as f:
            contents = f.read()
        return f"{FILE_PREFIX}{file_path}\n{contents}\n```\n"
    except Exception as e:
        return f"    Error reading {file_path}: {e}\n"

def prune_file_history(file_path):
    global history
    # Refined regex to match content only between FILE_PREFIX and the next FILE_PREFIX or FILES_END_SEP
    file_regex = re.compile(
        rf'{FILE_PREFIX}{re.escape(file_path)}\n(.*?)(?=(?:{FILE_PREFIX}|{FILES_END_SEP}|{CONVERSATION_END_SEP}|$))',
        re.DOTALL
    )

    debug(f"Regex being used: {file_regex.pattern}")

    for i in range(len(history)):
        debug(f"Before pruning history[{i}]:\n{history[i]}")
        history[i] = file_regex.sub(f'@{file_path}\n', history[i])
        debug(f"After pruning history[{i}]:\n{history[i]}")

def list_available_models():
    check_if_env_vars_set()

    ai.configure(api_key=GEMINI_API_KEY)

    for m in ai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            console.print(f"{m.name.replace('models/', '')} ({m.description})")

def coding_repl(resume=False, subject=None, interactive=False, writeable=False, ignore_patterns=None):
    start_time = time.time()

    os.mkdir('tmp') if not os.path.exists('tmp') else None

    ai.configure(api_key=GEMINI_API_KEY)

    model = ai.GenerativeModel('models/' + GEMINI_MODEL)

    # Split the comma-separated ignore patterns into a list
    extra_ignore_patterns = ignore_patterns.split(',') if ignore_patterns else None

    history_filename = history_filename_for_directory(os.getcwd())
    previous_session = previous_history()

    if resume and previous_session:
        session_file = os.path.join(os.path.dirname(__file__), f"../tmp/{previous_session[0]}")
        with open(session_file, 'r') as f:
            recap = f.read()

        # HACK: need to centralize this logic with the one inside the user input loop
        recap = re.sub(rf'(.*?){CONVERSATION_START_SEP}\n+', '', recap, flags=re.DOTALL)
        recap = re.sub(rf'^{FILE_PREFIX}(.*?)$', rf'#### \1\n\n{FILE_PREFIX}', recap, flags=re.MULTILINE)

        markdown = Markdown(recap)
        console.print(markdown)

        with open(session_file, 'r') as f:
            history.append(f.read())
    else:
        debug("No previous session found. Starting a new session.") if resume else None
        # Start fresh, but *only* if no history file exists *and* resume is true.  Otherwise, we're in a new session.
        if not previous_session and resume:
            history.append(prompt_prefix(extra_ignore_patterns))
        elif previous_session and not resume:
            # New session requested, but a history file exists:  Delete it!
            try:
              os.remove(history_filename)
            except:
              pass # Don't error if we can't remove it for some reason
            history.append(prompt_prefix(extra_ignore_patterns)) # and then start fresh


    first_message = False if resume else True

    prompt_style = prompt_toolkit.styles.Style.from_dict({ '': '#8CB9B3 bold' })

    completer = FuzzyCompleter(FilePathCompleter()) if interactive else None

    session = PromptSession(style=prompt_style, multiline=True, completer=completer, complete_style=CompleteStyle.MULTI_COLUMN)

    def calculate_history_stats():
        total_lines = sum(len(entry.splitlines()) for entry in history)
        total_chars = sum(len(entry) for entry in history)
        return total_lines, total_chars

    if verbose:
        end_time = time.time()
        duration = end_time - start_time
        total_lines, total_chars = calculate_history_stats()
        info(f"\n{total_lines} lines, {total_chars} characters, {duration:.2f}s ({GEMINI_MODEL})")

    while True:
        try:
            prompt_text = session.prompt("> ")
            if prompt_text == 'exit':
                break

            if prompt_text == '':
                continue

            global loading
            loading = True
            loading_thread = threading.Thread(target=loading_indicator, daemon=True)
            loading_thread.start()

            history.append('\nBrent:\n\n' + prompt_text + '\n')

            # Handle multiple file references
            file_references = re.findall(r'@(\S+)', prompt_text)
            file_references = [re.sub(r"[^\w\s]+$", '', file_reference) for file_reference in file_references]
            for file_path in file_references:
                if os.path.isfile(file_path):
                    # Prune previous versions of the file
                    prune_file_history(file_path)

                    with open(file_path, 'r') as f:
                        file_content = f.read()
                    history.append(f'\n{FILE_PREFIX}{file_path}\n{file_content}\n```\n')

            request_text = ''.join(history) + f'\n{CONVERSATION_END_SEP}\n'

            debug(request_text)

            start_time = time.time()
            response = model.generate_content(request_text)
            end_time = time.time()
            duration = end_time - start_time

            response_text = response.text

            def replace_with_diff(match):
                file_path = match.group(1)
                file_content = match.group(2)
                diff = generate_diff(file_path, file_content)
                return f'#### {file_path}\n\n{FILE_PREFIX}{file_path}\n{diff}\n```'

            redacted_response = re.sub(
                rf'{FILE_PREFIX}(.*?)\n(.*?)\n```',
                replace_with_diff,
                response_text,
                flags=re.DOTALL
            )

            # NOTE: do this after generating the diffs above
            file_references = re.findall(rf'{FILE_PREFIX}(.*?)\n(.*?)\n```', response_text, re.DOTALL)

            # Prune previous versions of the file
            for file_path, _ in file_references:
                prune_file_history(file_path)

            history.append('\nLinus:\n\n' + response_text + '\n')

            loading = False  # This makes the loading indicator stop
            loading_thread.join()

            console.print()
            markdown = Markdown(redacted_response)  # Convert response to Markdown
            console.print(markdown)

            # TODO: don't wastefully update a file if the diff was empty earlier on
            if writeable:
                for file_path, file_content in file_references:
                    with open(file_path, 'w') as f:
                        f.write(file_content)

            if history_filename:
                with open(history_filename, 'w') as f:
                    f.write(''.join(history))

            if verbose:
                total_lines, total_chars = calculate_history_stats()
                info(f"\n{total_lines} lines, {total_chars} characters, {duration:.2f}s ({GEMINI_MODEL})")

        except KeyboardInterrupt:
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break
        except EOFError:  # Ctrl+D exits
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break
        # except Exception as e:
            # print(f"Linus has glitched. {e}")
