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
        message = f"DEBUG: {message}" if message else ""
        console.print(message, style="bold yellow")

def info(message):
    global verbose
    if verbose:
        message = f"INFO: {message}" if message else ""
        console.print(message, style="bold")

def error(message):
    console.print(f"ERROR: {message}", style="bold red")

def print_markdown_code(code_block):
    console.print(Markdown(code_block, code_theme=EverforestDarkStyle))
    console.print()

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

def prompt_prefix(extra_ignore_patterns=None, include_patterns=None):
    try:
        with open(PROMPT_PREFIX_FILE, 'r') as f:
            prefix = f.read()
    except FileNotFoundError:
        return "Could not find background.md"

    project_structure = generate_project_structure(extra_ignore_patterns)
    project_files = generate_project_file_contents(extra_ignore_patterns, include_patterns)

    prefix = prefix.replace(parser.FILE_TREE_PLACEHOLDER, f'\n{project_structure}\n')
    prefix = prefix.replace(parser.FILES_PLACEHOLDER, f'\n{project_files}\n')

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

class FilePartBuffer:
    def __init__(self):
        self.buffer = defaultdict(lambda: defaultdict(str))
        # Remove total_parts, no longer needed
        self.final_parts = {} # Keep track of files with a final part

    def add(self, file_path, part_data, current_part, no_more_parts, version):
        self.buffer[(file_path, version)][current_part] = part_data
        if no_more_parts:
            # We only care about the *last* part having this flag
            self.final_parts[(file_path, version)] = current_part
        info(f"Added part {current_part} of {file_path} (v{version}) (NoMoreParts: {no_more_parts})")

    def is_complete(self, file_path, version):
        if (file_path, version) not in self.final_parts:
            return False  # We haven't seen a final part yet

        final_part_index = self.final_parts[(file_path, version)]

        # Check if *all* parts up to and including the final part exist
        for part_num in range(1, final_part_index + 1):
            if part_num not in self.buffer[(file_path, version)]:
                return False  # Missing a part

        return True

    def assemble(self, file_path, version):
        if not self.is_complete(file_path, version):
            return None

        sorted_parts = sorted(self.buffer[(file_path, version)].items())
        full_content = ''.join(part_data for _, part_data in sorted_parts)
        del self.buffer[(file_path, version)]
        del self.final_parts[(file_path, version)]  # Clean up
        return full_content

def coding_repl(resume=False, writeable=False, ignore_patterns=None, include_files=[]):
    start_time = time.time()

    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Split the comma-separated ignore patterns into a list
    extra_ignore_patterns = ignore_patterns.split(',') if ignore_patterns else None
    include_patterns = include_files.split(',') if include_files else None

    history_filename = history_filename_for_directory(os.getcwd())
    previous_session = last_session()

    if resume and previous_session:
        session_file = os.path.join(os.path.dirname(__file__), f"../tmp/{previous_session[0]}")
        with open(session_file, 'r') as f:
            session_history = f.read()

        history.append(session_history)

        recap = re.sub(parser.match_before_conversation_history(), '', session_history, flags=re.DOTALL)

        files = parser.find_files(recap)

        # TODO: what happens with multiple file parts here?

        for file_path, _, _, _, _, _ in files:
            print(f"Reading file: {file_path}")
            print()
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

        print_markdown_code(recap)
    else:
        # Start fresh, but *only* if no history file exists *and* resume is true.  Otherwise, we're in a new session.
        if not previous_session and resume:
            history.append(prompt_prefix(extra_ignore_patterns, include_patterns))
            if history_filename:
                with open(history_filename, 'w') as f:
                    f.write(''.join(history))
        elif previous_session and not resume:
            os.remove(history_filename)
            history.append(prompt_prefix(extra_ignore_patterns, include_patterns)) # and then start fresh
            if history_filename:
                with open(history_filename, 'w') as f:
                    f.write(''.join(history))

    session = create_prompt_session()

    # Initialize session-level token count
    session_total_tokens = 0

    def calculate_history_stats():
        # token_count = client.models.count_tokens(model=GEMINI_MODEL, contents=''.join(history))
        total_characters = sum(len(entry) for entry in history)
        total_lines = sum(len(entry.splitlines()) for entry in history)
        # return token_count.total_tokens, total_lines
        return total_characters, total_lines

    def reset_history():
        global history
        history.clear()
        history.append(prompt_prefix(extra_ignore_patterns, include_patterns))
        if history_filename:
            with open(history_filename, 'w') as f:
                f.write(''.join(history))
        print(' ', flush=True)
        console.print("History reset.", style="bold yellow")

    # TODO: should prune/compact as well after refreshing?
    def refresh_project_context():
        global history
        prefix = prompt_prefix(extra_ignore_patterns, include_patterns)
        history[0] = re.sub(parser.match_before_conversation_history(), prefix, history[0], flags=re.DOTALL)
        if history_filename:
            with open(history_filename, 'w') as f:
                f.write(''.join(history))
        print(' ', flush=True)
        console.print("Project context refreshed.", style="bold yellow")

    def should_exit(prompt_text):
        return prompt_text.startswith('$exit')

    def process_user_input(prompt_text=""):
        """Processes user input, updating history and handling file references."""
        if not prompt_text:
            return

        history.append(f'\n**Brent:**\n\n{prompt_text}\n')

        file_references = parser.find_file_references(prompt_text)

        for file_path in file_references:
            if not os.path.isfile(file_path): continue

            # TODO
            # prune_file_history(file_path, history)

            history.append(get_file_contents(file_path))

    def send_request_to_ai():
        """Sends a request to the AI and processes the streamed response."""
        nonlocal session_total_tokens

        request_text = ''.join(history) + f'\n{parser.CONVERSATION_END_SEP}\n'

        contents = [types.Part.from_text(text=request_text)]

        start_time = time.time()

        stream = client.models.generate_content_stream(model=GEMINI_MODEL, contents=contents)


        # Initialize counters for this request
        prompt_token_count = 0
        candidates_token_count = 0
        cached_content_token_count = 0
        total_token_count = 0

        full_response_text = ""
        queued_response_text = ""

        assembled_files = {}  # Store successfully assembled files here.

        with console.status("Linus is thinking...", spinner="point") as status:
            for chunk in stream:
                if not chunk.text:
                    continue

                # Accumulate token counts from usage metadata, handling potential None values
                if chunk.usage_metadata:
                    prompt_token_count += chunk.usage_metadata.prompt_token_count or 0
                    candidates_token_count += chunk.usage_metadata.candidates_token_count or 0
                    cached_content_token_count += chunk.usage_metadata.cached_content_token_count or 0
                    total_token_count += chunk.usage_metadata.total_token_count or 0

                queued_response_text += chunk.text
                full_response_text += chunk.text

                queued_has_complete_code_block = re.search(parser.match_code_block(), queued_response_text, flags=re.DOTALL)

                # TODO: if anything left of first code block, log it it
                # queued_has_incomplete_file = parser.find_in_progress_file(queued_response_text)
                # if queued_has_incomplete_file:

                if not queued_has_complete_code_block:
                    status.update("Linus is typing...")
                    debug("No complete code block detected, queueing...")
                    continue

                sections = re.split(parser.match_code_block(), queued_response_text, flags=re.DOTALL)

                queued_response_text = "" # Reset the queue and process the split sections

                for index, section in enumerate(sections):
                    if not section:
                        continue

                    is_code_block = re.match(parser.match_code_block(), section, flags=re.DOTALL)

                    is_last_section = index == len(sections) - 1

                    # TODO: add the typing/coding part back

                    if not is_code_block and is_last_section:
                        # Continue on, because another file could be right after
                        debug("Last section is not a full code block, queueing...")
                        queued_response_text += section
                        continue

                    if not is_code_block:
                        debug("Non-code block detected, processing...")
                        console.print(Markdown(section, code_theme=EverforestDarkStyle), end="")
                        continue
                    else:
                        is_file = parser.is_file(section)

                        if is_file:
                            # Now we get a boolean for no_more_parts
                            files = parser.find_files(section)

                            if not files:
                                error("Expected files in response section but none were found.")
                                error("-" * 20)
                                error(section)
                                error("-" * 20)
                                print()
                                continue

                            debug("Code block detected, processing...")

                            # TODO: need to look for multiple files here? I think we can assume not because we're streaming
                            file_path, version, file_content, language, part_id, no_more_parts = files[0]

                            status.update(f"Linus is writing {file_path}...")

                            info(f"Received chunk {part_id} for {file_path} (NoMoreParts: {no_more_parts})")
                            file_part_buffer.add(file_path, file_content, part_id, no_more_parts, version)

                            if file_part_buffer.is_complete(file_path, version):
                                status.update("Linus is typing...")
                                info(f"All chunks received for {file_path} (v{version})")
                                file_content = (file_part_buffer.assemble(file_path, version) or "").strip('\n')
                                assembled_files[(file_path, version)] = file_content  # Store assembled file
                                code = generate_diff(file_path, file_content)
                                is_diff = os.path.exists(file_path) and file_content != code
                                language = "diff" if is_diff else parser.get_language_from_extension(file_path)

                                console.print()
                                console.print(Markdown(f"#### {file_path}"))
                                section = f"```{language}\n{code}\n```"
                                print_markdown_code(section)
                            else:
                                debug(f"Waiting for more chunks of {file_path}")
                                continue  # Important: Don't process incomplete chunks

                        else:
                            status.update("Linus is typing...")
                            debug('Snippet handling')
                            file_path = None
                            language, code = parser.find_snippets(section)[0]
                            console.print()
                            console.print(Markdown(f"#### {file_path or language}"))
                            section = f"```{language}\n{code}\n```"
                            print_markdown_code(section)

            # TODO: we need to process potential file blocks at the end of the response
            # Handle any remaining text in the queue (non-code block parts)
            if queued_response_text:
                # Check for incomplete file block
                # unfinished_file = parser.find_in_progress_file(queued_response_text)
                # if unfinished_file:
                    # debug(f"Incomplete file block for {unfinished_file} detected. Continuing...")
                    # status.stop()
                    # return True, queued_response_text

                debug("Processing remaining queued text...")
                console.print()
                console.print(Markdown(queued_response_text.strip('\n')))
                console.print()
                queued_response_text = ""

        status.stop()

        # --- History and File Writing ---

        # History prune first before appending, but also after the response is fully processed
        # for file_path, version, file_content, language, part_id, parts_total in parser.find_files(full_response_text):
            # prune_file_history(file_path, history)

        # TODO:
        #
        # - Check for incomplete file blocks for any files (i.e. parts_total not in parts)
        #   If this is the case, return True, ""
        #
        # Do this both for not all parts and cut off (i.e. model messed up and needs to be re-fed)
        # If either of this is the case, keep track, and only print the Linus part once
        files = parser.find_files(full_response_text)
        unfinished_files = []

        # Check for unfinished files
        for file_path, version, _, _, _, no_more_parts in files:
            if (file_path, version) not in assembled_files:  # Only check files we haven't already assembled
                if not file_part_buffer.is_complete(file_path, version):
                    unfinished_files.append((file_path, version))

        if len(unfinished_files) > 0:
            debug(f"Unfinished files: {unfinished_files}")
            history.append(f'\n\n{full_response_text}\n\n')
            if history_filename:
                with open(history_filename, 'w') as f:
                    f.write(''.join(history))
            return True

        history.append(f'\n**Linus:**\n\n{full_response_text}\n')

        if writeable:
            # Write all assembled files
            for (file_path, _), file_content in assembled_files.items():
                info(f":w {file_path}")
                directory = os.path.dirname(file_path)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                with open(file_path, 'w') as f:
                    f.write(file_content)

            if len(assembled_files) > 0:
                print()


        if history_filename:
            with open(history_filename, 'w') as f:
                f.write(''.join(history))

        # Update session total tokens
        session_total_tokens += total_token_count

        if verbose:
            end_time = time.time()
            duration = end_time - start_time
            total_characters, total_lines = calculate_history_stats()
            console.print(
                f"{total_lines} lines, "
                f"{total_characters} characters, "
                f"{total_token_count} tokens, "
                f"{session_total_tokens} total, "
                f"{duration:.2f}s ({GEMINI_MODEL.replace('gemini-', '')})"
            )

        return False

    if verbose:
        end_time = time.time()
        duration = end_time - start_time
        total_characters, total_lines = calculate_history_stats()
        console.print(
            f"{total_lines} lines, "
            f"{total_characters} characters, "
            f"0 tokens, "
            f"0 total, "
            f"{duration:.2f}s ({GEMINI_MODEL.replace('gemini-', '')})"
        )

    # TODO: fill up file part buffer from history on resume
    file_part_buffer = FilePartBuffer()
    force_continue = False
    force_continue_counter = 0

    while True:
        try:
            if force_continue:
                info("Forcing continue...")
                if force_continue_counter > 5:
                    error("Model is stuck. Please restart.")
                    break
                force_continue_counter += 1
                force_continue = send_request_to_ai()
                continue
            else:
                force_continue_counter = 0

            prompt_text = session.prompt("> ")

            if should_exit(prompt_text):
                break

            if prompt_text.startswith('$reset'):
                reset_history()
                continue

            if prompt_text.startswith('$refresh'):
                refresh_project_context()
                continue

            if prompt_text.startswith('$continue'):
                process_user_input()
                force_continue = send_request_to_ai()
                continue

            process_user_input(prompt_text)

            force_continue = send_request_to_ai()

        except KeyboardInterrupt:
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break
        except EOFError:
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break
        except Exception:
            print("Linus has glitched!\n")
            console.print_exception(show_locals=True)