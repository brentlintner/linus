import os
import sys
import threading
import time
import hashlib
import re
import uuid
import pathspec
import prompt_toolkit
import difflib
import json
import pygments.util
import shlex
import subprocess
from pygments.lexers import get_lexer_for_filename
from datetime import datetime, timezone
from collections import deque
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.completion import FuzzyCompleter, Completer, Completion
from prompt_toolkit.shortcuts import CompleteStyle
from rich.console import Console
from rich.markdown import Markdown
from rich.theme import Theme
from rich.traceback import install
from google import genai
from google.genai import types

from .everforest import EverforestDarkStyle

from .chat_prefix import DELIMITER, FILE_PREFIX, SNIPPET_PREFIX, FILE_TREE_PLACEHOLDER, FILES_PLACEHOLDER, CONVERSATION_START_SEP, CONVERSATION_END_SEP, FILES_END_SEP, TERMINAL_LOGS_PLACEHOLDER

# TODO: should be in CLI?
install(show_locals=False)

# TODO: should be in CLI?
load_dotenv()

# Use environment variables for configuration (following the new docs)
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') or ''
#GOOGLE_GENAI_USE_VERTEXAI = os.getenv('GOOGLE_GENAI_USE_VERTEXAI')  # We'll assume Gemini API for now
#GOOGLE_CLOUD_PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT')
#GOOGLE_CLOUD_LOCATION = os.getenv('GOOGLE_CLOUD_LOCATION')
GEMINI_MODEL = os.getenv('GEMINI_MODEL') or '' # Keep this, but will use a different format later

PARSER_DEFINITION_FILE = 'src/chat_prefix.py'

history = []

verbose = False

debug_mode = False

custom_theme = Theme({
    "markdown.code": "#dcdcdc",
    "markdown.code_block": "#dcdcdc",
    "markdown.h1": "bold #dcdcdc",
    "markdown.h2": "bold #dcdcdc",
    "markdown.h3": "bold #dcdcdc",
    "markdown.h4": "bold #dcdcdc",
    "markdown.h5": "bold #dcdcdc",
    "markdown.h6": "bold #dcdcdc",
    "markdown.strong": "bold #dcdcdc",
    "markdown.em": "#a7c080",
    "markdown.alert": "bold #e67e80",
    "diff.add": "#a7c080",
    "diff.remove": "#e67e80",
    "diff.header": "#dbbc7f"
})

console = Console(theme=custom_theme)

key_bindings = KeyBindings()

@key_bindings.add(Keys.Up)
def _(event):
    event.current_buffer.history_backward()

@key_bindings.add(Keys.Down)
def _(event):
    event.current_buffer.history_forward()

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

def get_program_from_shebang(shebang_line):
    if not shebang_line.startswith("#!"):
        return None

    lexer = shlex.shlex(shebang_line)
    lexer.wordchars += ".-"
    try:
        lexer.get_token()  # Skip "#!"
        program = lexer.get_token()
        if program == "env":
            program = lexer.get_token() # Get the *next* token after 'env'
        return os.path.basename(program) if program else None
    except EOFError:
        return None

def get_language_from_extension(filename):
    try:
        _, ext = os.path.splitext(filename)
        if ext:
            lexer = get_lexer_for_filename(filename)
            return lexer.name.lower()
        else:
            with open(filename, 'r') as f:
                first_line = f.readline()
            program = get_program_from_shebang(first_line)
            if program:
                if program == "python3" or program == "python":
                    return "python"
                elif program == "bash":
                    return "bash"
                elif program == "sh":
                    return "sh"
                # Could add more mappings here, but keep it minimal
            return "text" # Fallback
    except pygments.util.ClassNotFound:
        return "text"
    except FileNotFoundError:
        return "text"

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

def get_tmux_pane_content(session_name, pane_id):
    """Captures the entire content of a tmux pane."""
    command = ["tmux", "capture-pane", "-p", "-t", f"{pane_id}", "-S", "-"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error(f"Error capturing pane {pane_id}: {result.stderr}")
        return ""  # Return empty string on error
    return result.stdout

def get_tmux_pane_ids(session_name, pane_id):
    """Gets a list of pane IDs in a tmux session."""
    command = ["tmux", "list-panes", "-s", "-F", "#{pane_id}", "-t", session_name]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        error(f"Error listing panes for {session_name}: {result.stderr}")
        return [] # Return empty list on error.  Important!
    return result.stdout.strip().splitlines()

def get_current_tmux_pane_id():
    """Gets the current tmux pane ID."""
    try:
        return os.environ.get('TMUX_PANE')
    except KeyError:
        return None

def get_tmux_logs():
    """Gets the content of all tmux panes *except* the current one."""
    current_pane_id = get_current_tmux_pane_id()
    if not current_pane_id:
        return "No tmux session detected.\n"

    try:
        session_name = subprocess.run(["tmux", "display-message", "-p", "#S"], capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError as e:
        error(f"Error getting tmux session name: {e}")
        return f"Error getting tmux session name: {e}\n"

    pane_ids = get_tmux_pane_ids(session_name, current_pane_id)
    all_logs = ""

    for pane_id in pane_ids:
        if pane_id != current_pane_id:
            content = get_tmux_pane_content(session_name, pane_id)
            all_logs += f"{DELIMITER}text\n{content}{DELIMITER}\n"
    return all_logs

def prompt_prefix(extra_ignore_patterns=None, include_files=True):
    prompt_prefix_file = os.path.join(os.path.dirname(__file__), '../docs/background.txt')
    try:
        with open(prompt_prefix_file, 'r') as f:
            prefix = f.read()
    except FileNotFoundError:
        return "Could not find background.txt"

    if include_files:
        project_structure = generate_project_structure(extra_ignore_patterns)
        project_files = generate_project_file_contents(extra_ignore_patterns)

        prefix = prefix.replace(FILE_TREE_PLACEHOLDER, f'\n{project_structure}\n')
        prefix = prefix.replace(FILES_PLACEHOLDER, f'\n{project_files}\n')
    else:
        prefix = prefix.replace(FILE_TREE_PLACEHOLDER, '')
        prefix = prefix.replace(FILES_PLACEHOLDER, '')

    return prefix

def check_if_env_vars_set():
    if not GOOGLE_API_KEY:
        error("Please set the GOOGLE_API_KEY environment variable.")
        sys.exit(1)

    if not GEMINI_MODEL:
        error("Please set the GEMINI_MODEL environment variable (ex: GEMINI_MODEL=gemini-1.5-pro-002)")
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
    # Use a hash of the absolute directory path *and* include the directory name
    abs_dir = os.path.abspath(directory)
    dir_name = os.path.basename(abs_dir)  # Get just the directory name
    file_path_bytes = abs_dir.encode('utf-8')
    hasher = hashlib.sha256()
    hasher.update(file_path_bytes)
    dir_hash = hasher.hexdigest()
    filename = f"linus-history-{dir_name}-{dir_hash}.txt"
    return os.path.join(os.path.dirname(__file__), '../tmp', filename)

def last_session():
    history_file = history_filename_for_directory(os.getcwd())
    if os.path.exists(history_file):
        info(f"Resuming from:\n\n {history_file}\n")
        return (os.path.basename(history_file), datetime.now())  # Return a dummy timestamp, not used for sorting now
    else:
        return None

class FilePathCompleter(Completer):
    def __init__(self):
        self.ignore_patterns = self.load_ignore_patterns()
        self.spec = pathspec.PathSpec.from_lines('gitwildmatch', self.ignore_patterns)

    def load_ignore_patterns(self):
        ignore_patterns = []
        for ignore_file in ['.gitignore']:
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

class CommandCompleter(Completer):
    def __init__(self, commands):
        self.commands = commands

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor()

        if '$' not in word_before_cursor:
            return

        for command in self.commands:
            if command.startswith(word_before_cursor[1:]):
                yield Completion(command, start_position=-len(word_before_cursor) + 1)

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
        tofile=f"{file_path} (context)",
    )

    stringifed_diff = ''.join(diff)

    if len(stringifed_diff) == 0:
        # If no diff (i.e. we are re-adding the same file), return full (i.e. current) content
        return current_content

    return stringifed_diff

def generate_project_structure(extra_ignore_patterns=None):
    ignore_patterns = ['.*']  # Ignore dotfiles by default
    for ignore_file in ['.gitignore']:
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
    for ignore_file in ['.gitignore']:
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

def generate_project_file_list(extra_ignore_patterns=None):
    ignore_patterns = ['.*']
    for ignore_file in ['.gitignore']:
        if os.path.exists(ignore_file):
            with open(ignore_file) as f:
                ignore_patterns.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])
    if extra_ignore_patterns:
        ignore_patterns.extend(extra_ignore_patterns)

    spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)
    output = []  # Use a list to store file names

    for root, _, files in os.walk(os.getcwd()):
        relative_path = os.path.relpath(root, os.getcwd())
        if relative_path == '.':
            relative_path = ''
        for file in files:
            file_path = os.path.join(relative_path, file)
            if not spec.match_file(file_path):
                output.append(file_path)  # Append file path to the list

    return "\n".join(output)  # Join with newlines

def get_file_contents(file_path):
    try:
        with open(file_path, 'r') as f:
            contents = f.read()
        return f"{FILE_PREFIX}{file_path}\n{contents}\n{DELIMITER}\n"
    except Exception as e:
        return f"    Error reading {file_path}: {e}\n"

def prune_file_history(file_path):
    global history
    # Refined regex to match content only between FILE_PREFIX and the next FILE_PREFIX or FILES_END_SEP
    file_regex = re.compile(
        rf'{FILE_PREFIX}{re.escape(file_path)}\n(.*?)(?=(?:{FILE_PREFIX}|{FILES_END_SEP}|{CONVERSATION_END_SEP}|$))',
        flags=re.DOTALL
    )

    debug(f"Regex being used: {file_regex.pattern}")

    for i in range(len(history)):
        debug(f"Before pruning history[{i}]:\n{history[i]}")
        history[i] = file_regex.sub(f'@{file_path}\n', history[i])
        debug(f"After pruning history[{i}]:\n{history[i]}")

def list_available_models():
    check_if_env_vars_set()

    # Configure the client (using environment variables)
    client = genai.Client(api_key=GOOGLE_API_KEY)

    for m in client.models.list():
        console.print(f"{(m.name or '').replace('models/', '')} ({m.description})")

def split_at(delimiter, input_string):
    parts = input_string.split(delimiter, 1)  # Split at most once

    if len(parts) < 2:  # No delimiter found
        return input_string, ""
    else:
        return parts[0], parts[1]

def coding_repl(resume=False, interactive=False, writeable=False, ignore_patterns=None, include_files=False):
    start_time = time.time()

    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Split the comma-separated ignore patterns into a list
    extra_ignore_patterns = ignore_patterns.split(',') if ignore_patterns else None

    history_filename = history_filename_for_directory(os.getcwd())
    previous_session = last_session()

    if resume and previous_session:
        session_file = os.path.join(os.path.dirname(__file__), f"../tmp/{previous_session[0]}")
        with open(session_file, 'r') as f:
            session_history = f.read()

        history.append(session_history)

        recap = re.sub(rf'(.*?){CONVERSATION_START_SEP}\n+', '', session_history, flags=re.DOTALL)

        file_matches = re.finditer(rf'^{FILE_PREFIX}(.*?)$', recap, flags=re.MULTILINE)

        for match in file_matches:
            file_path = match.group(1)

            recap = re.sub(
                rf'^{FILE_PREFIX}{re.escape(file_path)}$',
                rf'#### {file_path}\n\n{DELIMITER}{get_language_from_extension(file_path)}',
                recap,
                flags=re.MULTILINE)

        recap = re.sub(
            rf'^{SNIPPET_PREFIX}(.*?)$',
            rf'#### \1\n\n{DELIMITER}\1',
            recap,
            flags=re.MULTILINE)

        markdown = Markdown(recap, code_theme=EverforestDarkStyle)

        console.print(markdown)
        console.print()
    else:
        # Start fresh, but *only* if no history file exists *and* resume is true.  Otherwise, we're in a new session.
        if not previous_session and resume:
            history.append(prompt_prefix(extra_ignore_patterns, include_files))
            if history_filename:
                with open(history_filename, 'w') as f:
                    f.write(''.join(history))
        elif previous_session and not resume:
            os.remove(history_filename)
            history.append(prompt_prefix(extra_ignore_patterns, include_files)) # and then start fresh
            if history_filename:
                with open(history_filename, 'w') as f:
                    f.write(''.join(history))

    prompt_style = prompt_toolkit.styles.Style.from_dict({ '': '#8CB9B3 bold' })

    file_completer = FuzzyCompleter(FilePathCompleter()) if interactive else None
    command_completer = FuzzyCompleter(CommandCompleter(['reset', 'refresh', 'exit'])) if interactive else None
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

    session = PromptSession(
        style=prompt_style,
        multiline=True,
        key_bindings=key_bindings,
        completer=CombinedCompleter(),
        complete_style=CompleteStyle.MULTI_COLUMN)

    def calculate_history_stats():
        # token_count = client.models.count_tokens(model=GEMINI_MODEL, contents=''.join(history))
        total_characters = sum(len(entry) for entry in history)
        total_lines = sum(len(entry.splitlines()) for entry in history)
        # return token_count.total_tokens, total_lines
        return total_characters, total_lines

    def reset_history():
        global history
        history.clear()
        history.append(prompt_prefix(extra_ignore_patterns, include_files))
        if history_filename:
            with open(history_filename, 'w') as f:
                f.write(''.join(history))
        print(' ', flush=True)
        console.print("History reset.", style="bold yellow")

    def refresh_project_context():
        global history
        history[0] = prompt_prefix(extra_ignore_patterns, include_files)
        if history_filename:
            with open(history_filename, 'w') as f:
                f.write(''.join(history))
        print(' ', flush=True)
        console.print("Project context refreshed.", style="bold yellow")

    if verbose:
        end_time = time.time()
        duration = end_time - start_time
        total_characters, total_lines = calculate_history_stats()
        info(f"{total_lines} lines, {total_characters} characters, {duration:.2f}s ({GEMINI_MODEL})")

    while True:
        try:
            prompt_text = session.prompt("> ")
            if prompt_text.startswith('$exit'):
                break

            if prompt_text.startswith('$reset'):
                reset_history()
                continue

            if prompt_text.startswith('$refresh'):
                refresh_project_context()
                continue

            if prompt_text == '':
                continue

            history.append(f'\n**Brent:**\n\n' + prompt_text + '\n')

            # Handle multiple file references
            file_references = re.findall(r'@(\S+)', prompt_text)
            file_references = [re.sub(r"[^\w\s]+$", '', file_reference) for file_reference in file_references]
            for file_path in file_references:
                if os.path.isfile(file_path):
                    prune_file_history(file_path)

                    with open(file_path, 'r') as f:
                        file_content = f.read()
                    history.append(f'\n{FILE_PREFIX}{file_path}\n{file_content}\n{DELIMITER}\n')

            request_text = ''.join(history) + f'\n{CONVERSATION_END_SEP}\n'

            # Prepare contents for generate_content
            contents = [types.Part.from_text(text=request_text)]

            start_time = time.time()
            # Use generate_content_stream instead of generate_content
            stream = client.models.generate_content_stream(model=GEMINI_MODEL, contents=contents)

            full_response_text = ""
            queued_response_text = ""

            console.print()
            with console.status("", spinner="point") as status:
                for chunk in stream:
                    if not chunk.text: continue

                    full_response_text += chunk.text
                    queued_response_text += chunk.text

                    # TODO: here need to be more sophisticated to catch when delimiter is in the actual text
                    sections = re.split(rf"({DELIMITER}.*?{DELIMITER}|{FILE_PREFIX}.*?\n.*?\n{DELIMITER})", queued_response_text, flags=re.DOTALL)

                    if len(sections) == 1 and not queued_response_text.startswith(DELIMITER): continue

                    queued_response_text = "" # Reset because we're processing the sections

                    for index, section in enumerate(sections):
                        is_code_block = section.startswith(DELIMITER)
                        is_last_section = index == len(sections) - 1

                        if not is_code_block and is_last_section:
                            # TODO: split the last section on \n\n and print the first part, then queue the second part
                            queued_response_text = section
                            continue

                        if is_code_block:
                            file_path_match = re.search(rf'^{FILE_PREFIX}(.*)\n', section)
                            is_file = bool(file_path_match)

                            # Be greedy here since it's just a section
                            content_match = re.match(rf'^{DELIMITER}.*\n(.*)\n{DELIMITER}', section, flags=re.DOTALL)
                            content = content_match.group(1) if content_match else ""

                            if is_file:
                                file_path = file_path_match.group(1)
                                code = generate_diff(file_path, content)
                                is_diff = os.path.exists(file_path) and content != code
                                language = "diff" if is_diff else get_language_from_extension(file_path)

                                console.print(Markdown(f"#### {file_path}"))
                            else:
                                code = content
                                # Be greedy here since it's just a section
                                language_match = re.match(rf'^{SNIPPET_PREFIX}(.*)\n', section)
                                language = language_match.group(1) if language_match else 'text'

                                console.print(Markdown(f"#### {language}")) # Keep this

                            console.print()

                            section = f"{DELIMITER}{language if language != 'text' else ''}\n{code}\n{DELIMITER}"

                        console.print(Markdown(section, code_theme=EverforestDarkStyle))
                        console.print()

                # Handle any remaining text in the queue
                if queued_response_text:
                    markdown = Markdown(queued_response_text, code_theme=EverforestDarkStyle)
                    console.print(markdown)
                    console.print()
                    queued_response_text = ""

                status.stop()

            end_time = time.time()
            duration = end_time - start_time

            # --- Post-processing after the entire response is received ---

            # Now we process the *entire* response for file writes, pruning, and history
            def replace_with_diff_for_history(match):
                file_path = match.group(1)
                file_content = match.group(2)
                return f'{FILE_PREFIX}{file_path}\n{file_content}\n{DELIMITER}'

            # Prepare for history (don't show diffs in history, just the final content)
            history_response = re.sub(
                rf'{FILE_PREFIX}(.*?)\n(.*?)\n{DELIMITER}',
                replace_with_diff_for_history,
                full_response_text,
                flags=re.DOTALL
            )

            # Prune file history *after* the entire response is received, but before history is appended
            file_references = re.findall(rf'{FILE_PREFIX}(.*?)\n(.*?)\n{DELIMITER}', full_response_text, flags=re.DOTALL)
            for file_path, _ in file_references:
                prune_file_history(file_path)

            history.append(f'\n**Linus:**\n\n' + history_response + '\n')

            if writeable:
                for file_path, file_content in file_references:
                    info(f":w {file_path}")
                    directory = os.path.dirname(file_path)
                    if directory and not os.path.exists(directory):
                        os.makedirs(directory)

                    with open(file_path, 'w') as f:
                        f.write(file_content)

                if len(file_references) > 0:
                    print()

            if history_filename:
                with open(history_filename, 'w') as f:
                    f.write(''.join(history))

            if verbose:
                total_characters, total_lines = calculate_history_stats()
                info(f"{total_lines} lines, {total_characters} characters, {duration:.2f}s ({GEMINI_MODEL})")

        except KeyboardInterrupt:
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break
        except EOFError:  # Ctrl+D exits
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break
        except Exception:
            print("Linus has glitched!\n")
            console.print_exception(show_locals=False)
