
import os
import sys
import time
import hashlib
import re
import uuid
from datetime import datetime, timezone
from collections import deque, defaultdict
from rich.console import Console
from rich.markdown import Markdown
from google import genai
from google.genai import types

from . import parser
from .repl import create_prompt_session
from .theme import EverforestDarkStyle
from .config import (
    GOOGLE_API_KEY,
    GEMINI_MODEL,
    CONSOLE_THEME,
    PROMPT_PREFIX_FILE
)
from .file_utils import (
    generate_project_structure,
    generate_project_file_contents,
    prune_file_history,
    generate_diff,
    get_file_contents
)

history = []

verbose = False

debug_mode = False

console = Console(theme=CONSOLE_THEME)

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

def prompt_prefix(extra_ignore_patterns=None, include_files=True):
    try:
        with open(PROMPT_PREFIX_FILE, 'r') as f:
            prefix = f.read()
    except FileNotFoundError:
        return "Could not find background.txt"

    if include_files:
        project_structure = generate_project_structure(extra_ignore_patterns)
        project_files = generate_project_file_contents(extra_ignore_patterns)

        prefix = prefix.replace(parser.FILE_TREE_PLACEHOLDER, f'\n{project_structure}\n')
        prefix = prefix.replace(parser.FILES_PLACEHOLDER, f'\n{project_files}\n')
    else:
        prefix = prefix.replace(parser.FILE_TREE_PLACEHOLDER, '')
        prefix = prefix.replace(parser.FILES_PLACEHOLDER, '')

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

def list_available_models():
    check_if_env_vars_set()

    # Configure the client (using environment variables)
    client = genai.Client(api_key=GOOGLE_API_KEY)

    for m in client.models.list():
        console.print(f"{(m.name or '').replace('models/', '')} ({m.description})")

class FileChunkBuffer:
    def __init__(self):
        self.buffer = defaultdict(lambda: defaultdict(str))
        self.total_chunks = {}

    def add_chunk(self, file_path, chunk_data, chunk_id):
        current_chunk, total_chunks = map(int, chunk_id.split('/'))
        self.buffer[file_path][current_chunk] = chunk_data
        self.total_chunks[file_path] = total_chunks
        debug(f"Added chunk {current_chunk} of {total_chunks} for {file_path}")

    def is_complete(self, file_path):
        if file_path not in self.total_chunks:
            return False
        return len(self.buffer[file_path]) == self.total_chunks[file_path]

    def assemble(self, file_path):
        if not self.is_complete(file_path):
            return None

        sorted_chunks = sorted(self.buffer[file_path].items())
        full_content = ''.join(chunk_data for _, chunk_data in sorted_chunks)
        del self.buffer[file_path]
        del self.total_chunks[file_path]
        return full_content

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

        recap = re.sub(parser.match_before_conersation_history(), '', session_history, flags=re.DOTALL)

        files = parser.find_files(recap)

        for file_path, _, _, _ in files:
            language = parser.get_language_from_extension(file_path)
            recap = re.sub(
                parser.match_file(file_path),
                rf'#### {file_path}\n\n```{language}\n\1\n```',
                recap,
                flags=re.DOTALL)

        recap = re.sub(
            parser.match_snippet(),
            r'#### \1\n\n```\1\n\2\n```',
            recap,
            flags=re.DOTALL)

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

    session = create_prompt_session(interactive)

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

    file_chunk_buffer = FileChunkBuffer()

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

            history.append(f'\n**Brent:**\n\n{prompt_text}\n')

            file_references = parser.find_file_references(prompt_text)

            for file_path in file_references:
                if not os.path.isfile(file_path): continue

                prune_file_history(file_path, history)

                history.append(get_file_contents(file_path))

            request_text = ''.join(history) + f'\n{parser.CONVERSATION_END_SEP}\n'

            contents = [types.Part.from_text(text=request_text)]

            start_time = time.time()

            stream = client.models.generate_content_stream(model=GEMINI_MODEL, contents=contents)

            full_response_text = ""
            queued_response_text = ""  # Used for non-code block text

            console.print()
            with console.status("", spinner="point") as status:
                for chunk in stream:
                    if not chunk.text:
                        continue

                    full_response_text += chunk.text
                    queued_response_text += chunk.text

                    sections = re.split(parser.match_code_block(), queued_response_text, flags=re.DOTALL)

                    if len(sections) == 1 and not re.match(parser.match_code_block(), queued_response_text, flags=re.DOTALL):
                        debug("Waiting for more content...")
                        continue

                    queued_response_text = ""

                    for index, section in enumerate(sections):
                        if not section:
                            continue

                        is_code_block = parser.is_file(section) or parser.is_snippet(section)
                        is_last_section = index == len(sections) - 1

                        if not is_code_block and is_last_section:
                            debug("Waiting for more content (not code block)...")
                            queued_response_text = section
                            continue

                        if is_code_block:
                            debug("Code block detected, processing...")
                            is_file = parser.is_file(section)

                            if is_file:
                                file_path, file_content, language, chunk_id = parser.find_files(section)[0]

                                if chunk_id:
                                    debug(f"Received chunk {chunk_id} for {file_path}")
                                    file_chunk_buffer.add_chunk(file_path, file_content, chunk_id)

                                    if file_chunk_buffer.is_complete(file_path):
                                        debug(f"All chunks received for {file_path}")
                                        file_content = file_chunk_buffer.assemble(file_path)
                                        code = generate_diff(file_path, file_content)
                                        is_diff = os.path.exists(file_path) and file_content != code
                                        language = "diff" if is_diff else parser.get_language_from_extension(file_path)

                                        console.print(Markdown(f"#### {file_path}"))
                                        console.print()
                                        section = f"```{language}\n{code}\n```"

                                        console.print(Markdown(section, code_theme=EverforestDarkStyle))
                                        console.print()
                                    else:
                                        debug(f"Waiting for more chunks of {file_path}")
                                        continue  # Important: Don't process incomplete chunks
                                else:
                                    # Regular file handling (no chunks).
                                    code = generate_diff(file_path, file_content)
                                    is_diff = os.path.exists(file_path) and file_content != code
                                    language = "diff" if is_diff else parser.get_language_from_extension(file_path)
                                    console.print(Markdown(f"#### {file_path}"))
                                    console.print()
                                    section = f"```{language}\n{code}\n```"
                                    console.print(Markdown(section, code_theme=EverforestDarkStyle))
                                    console.print()

                            else:
                                # Snippet handling
                                file_path = None
                                language, code = parser.find_snippets(section)[0]
                                console.print(Markdown(f"#### {file_path or language}"))
                                console.print()
                                section = f"```{language}\n{code}\n```"
                                console.print(Markdown(section, code_theme=EverforestDarkStyle))
                                console.print()

                # Handle any remaining text in the queue (non-code block parts)
                if queued_response_text:
                    markdown = Markdown(queued_response_text, code_theme=EverforestDarkStyle)
                    console.print(markdown)
                    console.print()
                    queued_response_text = ""

            status.stop()

            end_time = time.time()
            duration = end_time - start_time

            # --- History and File Writing ---
            #  *Crucially*, after the *entire* response has been processed and printed.

            # History pruning and appending happens *after* processing the full response
            for file_path, file_content, _, chunk_id in parser.find_files(full_response_text):
                prune_file_history(file_path, history)
                # If it's a complete file (no chunk ID), add it to the history
                if not chunk_id:
                    history.append(get_file_contents(file_path))

            history.append(f'\n**Linus:**\n\n{full_response_text}\n')

            if writeable:
                # We iterate over the *original* full_response_text. This is important
                # because we want to write *all* file chunks, not just complete files.
                for file_path, file_content, _, _ in parser.find_files(full_response_text):
                    info(f":w {file_path}")
                    directory = os.path.dirname(file_path)
                    if directory and not os.path.exists(directory):
                        os.makedirs(directory)

                    with open(file_path, 'w') as f:
                        f.write(file_content)

                if len(parser.find_files(full_response_text)) > 0:
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
        except EOFError:
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break
        except Exception:
            print("Linus has glitched!\n")
            console.print_exception(show_locals=True)

