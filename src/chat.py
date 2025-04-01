import os
import sys
import time
import hashlib
import re
import uuid
import json
from datetime import datetime, timezone
from collections import deque, defaultdict
from google import genai
from google.genai import types
from pygments.lexer import include
from . import parser
from .repl import create_prompt_session
from .logger import (
    console,
    is_verbose,
    is_debug,
    debug,
    error,
    print_markdown
)
from .config import (
    GOOGLE_API_KEY,
    GEMINI_MODEL,
    PROMPT_PREFIX_FILE
)
from .file_utils import (
    generate_project_structure,
    generate_project_file_contents,
    generate_diff,
    get_file_contents,
    human_format_number
)

history = []

def tail(filename, n=10):
    try:
        with open(filename, encoding='utf-8') as f:
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

def prompt_prefix(extra_ignore_patterns=None, include_patterns=None, cwd=os.getcwd()):
    try:
        with open(PROMPT_PREFIX_FILE, 'r', encoding='utf-8') as f:
            prefix = f.read()
    except FileNotFoundError:
        return "Could not find background.md"

    if include_patterns is None or not include_patterns:
        # No files included, return prefix without file tree and file contents.
        return prefix.replace(parser.FILE_TREE_PLACEHOLDER, '[]').replace(parser.FILES_PLACEHOLDER, '')

    project_structure_json = generate_project_structure(extra_ignore_patterns, include_patterns, cwd)
    project_files = generate_project_file_contents(extra_ignore_patterns, include_patterns, cwd)

    project_structure = json.dumps(
        project_structure_json, indent=2) if is_debug() else json.dumps(project_structure_json, separators=(',', ':'))

    prefix = prefix.replace(parser.FILE_TREE_PLACEHOLDER, f'{project_structure}')
    prefix = prefix.replace(parser.FILES_PLACEHOLDER, f'{project_files}')

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

def last_session(cwd=os.getcwd()):
    # NOTE: directory argument no longer needed, pass it from cli
    history_file = history_filename_for_directory(cwd)
    if os.path.exists(history_file):
        debug(f"Resuming from:\n\n {history_file}\n")
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
        if no_more_parts:
            # We only care about the *last* part having this flag
            debug(f"Received **all parts** of {file_path} (v{version})")
            self.final_parts[(file_path, version)] = True
        else:
            debug(f"Received part {current_part} of {file_path} (v{version})")
            self.buffer[(file_path, version)][current_part] = part_data

    def is_complete(self, file_path, version):
        # TODO: debug log if we are missing any parts (i.e. have 2, but not 1)
        return (file_path, version) in self.final_parts

    def assemble(self, file_path, version):
        if not self.is_complete(file_path, version):
            return None

        sorted_parts = sorted(self.buffer[(file_path, version)].items())
        # TODO: ignore the nomoreparts (part 0)? should be empty always
        full_content = ''.join(part_data for _, part_data in sorted_parts)
        del self.buffer[(file_path, version)]
        del self.final_parts[(file_path, version)]  # Clean up
        return full_content

def coding_repl(resume=False, writeable=False, ignore_patterns=None, include_patterns=None, cwd=os.getcwd()):
    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Split the comma-separated ignore patterns into a list
    extra_ignore_patterns = ignore_patterns.split(',') if ignore_patterns else None

    # Convert include_patterns to a list if it's not None, otherwise keep it as None
    if include_patterns is not None and "." in include_patterns:
        include_patterns = ["."]  # Treat "." as a special case, including all files.

    history_filename = history_filename_for_directory(cwd) # Use the passed directory.
    previous_session = last_session(cwd)

    if resume and previous_session:
        prompt_history_file = os.path.join(os.path.dirname(__file__), f"../tmp/{previous_session[0]}")
        with open(prompt_history_file, 'r', encoding='utf-8') as f:
            prompt_history = f.read()

        history.append(prompt_history)

        recap = re.sub(parser.match_before_conversation_history(), '', prompt_history, flags=re.DOTALL)

        files = parser.find_files(recap)

        for file_path, version, content, _, _, _ in files:
            language = parser.get_language_from_extension(file_path)
            # HACK: ideally we avoid doing this per file, but it's a quick fix for now
            replaced_content = content.replace("\\", "\\\\")
            suffix = " (EMPTY)" if not replaced_content else ""
            recap = re.sub(
                parser.match_file(file_path),
                rf'#### {file_path} (v{version}){suffix}\n\n```{language}\n{replaced_content}\n```',
                recap,
                flags=re.DOTALL,
                count=1)
            # HACK: extra parts are not removed just the first one
            recap = re.sub(parser.match_file(file_path), '', recap, flags=re.DOTALL)

        recap = re.sub(
            parser.match_snippet(),
            r'#### \1\n\n```\1\n\2\n```',
            recap,
            flags=re.DOTALL)

        print_markdown(recap)
    else:
        # Start fresh, but *only* if no history file exists *and* resume is true.  Otherwise, we're in a new session.
        if not previous_session and resume:
            history.append(prompt_prefix(extra_ignore_patterns, include_patterns, cwd)) # Pass directory
            if history_filename:
                with open(history_filename, 'w', encoding='utf-8') as f:
                    f.write(''.join(history))
        elif previous_session and not resume:
            os.remove(history_filename)
            history.append(prompt_prefix(extra_ignore_patterns, include_patterns, cwd)) # and then start fresh, pass directory
            if history_filename:
                with open(history_filename, 'w', encoding='utf-8') as f:
                    f.write(''.join(history))

    session = create_prompt_session(cwd)

    # Initialize session-level token count
    session_total_tokens = 0

    def calculate_history_stats():
        total_characters = sum(len(entry) for entry in history)
        total_lines = sum(len(entry.splitlines()) for entry in history)
        return total_characters, total_lines

    def reset_history():
        history.clear()
        history.append(prompt_prefix(extra_ignore_patterns, include_patterns, cwd))
        if history_filename:
            with open(history_filename, 'w', encoding='utf-8') as f:
                f.write(''.join(history))
        print(' ', flush=True)
        console.print("History reset.", style="bold yellow")

    def refresh_project_context():
        prefix = prompt_prefix(extra_ignore_patterns, include_patterns, cwd)
        history[0] = re.sub(parser.match_before_conversation_history(), prefix, history[0], flags=re.DOTALL)
        if history_filename:
            with open(history_filename, 'w', encoding='utf-8') as f:
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

        history_snapshot = '\n'.join(history)

        file_references = parser.find_file_references(prompt_text)

        for file_path in file_references:
            if not os.path.isfile(os.path.join(cwd, file_path)): # Use os.path.join with directory
                continue

            # Find the highest existing version of the referenced file.
            highest_version = 0
            for existing_file_path, version, _, _, _, _ in parser.find_files(history_snapshot):
                if existing_file_path == file_path:
                    highest_version = max(highest_version, version)

            new_version = highest_version + 1

            debug(f"Appending file {file_path} (v{new_version}) to history")
            history.append(get_file_contents(os.path.join(cwd, file_path), new_version)) # Use os.path.join

        if history_filename:
            with open(history_filename, 'w', encoding='utf-8') as f:
                f.write(''.join(history))

    # TODO: ensure everything after the conversation history is used, and before is not modified
    def compact_history():
        """Compacts files in the history list to only the latest version."""
        history_content = '\n'.join(history)

        before_file_refs, after_file_refs = history_content.split(parser.FILES_START_SEP, 1)

        # Find all file instances (path, version) in the history
        all_file_versions = parser.find_files(after_file_refs)

        if not all_file_versions:
            debug("No files found in history to prune.")
            return # Nothing to do

        # Determine the latest version for each file path
        latest_versions = defaultdict(int)
        for path, version, *_ in all_file_versions:
            if path not in latest_versions or not version < latest_versions[path]:
                latest_versions[path] = version

        # Identify older versions to remove
        files_to_remove = []
        for path, version, *_ in all_file_versions:
            if version < latest_versions[path]:
                files_to_remove.append((path, version))

        if not files_to_remove:
            debug("No older file versions found to prune.")
            return # Nothing to do

        # Remove the identified older versions using parser.match_file
        removed_count = 0
        for path, version in files_to_remove:
            debug(f"Removing older version {version} of file {path}.")
            after_file_refs = re.sub(parser.match_file_with_version(path, version), '', after_file_refs, flags=re.DOTALL)
            # TODO: remove the nomoreparts from the history too!!
            removed_count += 1

        debug(f"Removed {removed_count} older file version blocks in total.")

        if removed_count == 0:
            return

        history.clear()

        history.append(f"{before_file_refs.strip()}\n{parser.FILES_START_SEP}\n{after_file_refs}")

        if history_filename:
            with open(history_filename, 'w', encoding='utf-8') as f:
                f.write(''.join(history))

    def send_request_to_ai(is_continuation=False):
        """Sends a request to the AI and processes the streamed response."""
        nonlocal session_total_tokens

        # NOTE: We need set this here because is_continuation can be manually set to True in the chunk processing loop below
        should_add_user_prefix = not is_continuation

        request_text = ''.join(history) + f'\n{parser.CONVERSATION_END_SEP}\n'

        contents = [types.Part.from_text(text=request_text)]

        start_time = time.time()

        stream = client.models.generate_content_stream(model=GEMINI_MODEL, contents=contents)

        full_response_text = ""
        queued_response_text = ""

        assembled_files = {}  # Store successfully assembled files here.

        with console.status("Linus is thinking...", spinner="point") as status:
            for chunk in stream:
                if not chunk.text:
                    continue

                queued_response_text += chunk.text
                full_response_text += chunk.text

                # Check for the *start* of a file block
                in_progress_file = parser.find_in_progress_file(queued_response_text)

                if in_progress_file:
                    in_progress_file_path = in_progress_file
                    status.update(f"Linus is writing {in_progress_file_path}...")

                    # Split into before_file and rest
                    before_file_start, rest = queued_response_text.split(parser.FILE_METADATA_START, 1)
                    queued_response_text = parser.FILE_METADATA_START + rest

                    if before_file_start:
                        print_markdown(before_file_start)
                else:
                    status.update("Linus is typing...")

                queued_has_complete_code_block = re.search(parser.match_code_block(), queued_response_text, flags=re.DOTALL)

                if not queued_has_complete_code_block:
                    continue

                sections = re.split(parser.match_code_block(), queued_response_text, flags=re.DOTALL)

                queued_response_text = "" # Reset the queue and process the split sections

                for index, section in enumerate(sections):
                    if not section:
                        continue

                    is_code_block = re.match(parser.match_code_block(), section, flags=re.DOTALL)
                    is_last_section = index == len(sections) - 1

                    if not is_code_block and is_last_section:
                        # Continue on, because another file could be right after
                        queued_response_text += section
                        continue

                    if not is_code_block:
                        print_markdown(section, end="")
                        continue

                    is_file = parser.is_file(section)

                    if is_file:
                        # Now we get a boolean for no_more_parts
                        files = parser.find_files(section)

                        if not files:
                            error("Expected files in response section but none were found.")
                            error("")
                            error(section)
                            error("")
                            continue

                        # TODO: need to look for multiple files here? I think we can assume not because we're streaming
                        file_path, version, file_content, language, part_id, no_more_parts = files[0]

                        file_part_buffer.add(file_path, file_content, part_id, no_more_parts, version)

                        if file_part_buffer.is_complete(file_path, version):
                            file_content = (file_part_buffer.assemble(file_path, version) or "").strip('\n')
                            assembled_files[(file_path, version)] = file_content  # Store assembled file
                            code = generate_diff(file_path, file_content)
                            is_diff = os.path.exists(os.path.join(cwd, file_path)) and code != file_content # Use os.path.join
                            language = "diff" if is_diff else parser.get_language_from_extension(file_path)

                            suffix = " (EMPTY)" if not file_content else ""
                            print_markdown(f"#### {file_path} v{version}{suffix}", end="")

                            section = f"```{language}\n{code}\n```"
                            print_markdown(section)
                            status.update("Linus is typing...")
                        else:
                            continue  # Important: Don't process incomplete chunks

                    else:
                        status.update("Linus is typing...")
                        file_path = None
                        language, code = parser.find_snippets(section)[0]
                        section = f"```{language}\n{code}\n```"
                        print_markdown(section)

            # Handle any remaining text in the queue (non-code block parts)
            if queued_response_text:
                in_progress_file = parser.find_in_progress_file(queued_response_text)

                # We have cut off mid file part
                if in_progress_file:
                    debug("Stopped mid file part, force continue required...")
                    # Split into before_file and the incomplete file block
                    before_file, after_file = queued_response_text.split(parser.FILE_METADATA_START, 1)

                    # Queued text *starts* with a file metadata start block
                    if not before_file:
                        incomplete_file_block = queued_response_text
                    # Queued text has a file metadata start block in the middle
                    else:
                        incomplete_file_block = after_file

                    # Remove the last line from the incomplete file content, in case its cut off
                    content_lines = incomplete_file_block.splitlines()
                    if len(content_lines) > 1:
                        content_lines.pop() # Remove last line
                    incomplete_file_block = "\n".join(content_lines)

                    # Now we *need* to add the end of file
                    files = parser.find_files(incomplete_file_block, incomplete=True)

                    # TODO: be more robust and handle if we are cut off mid file metadata, or there is
                    # less than 2 lines in the mid content block
                    if not files:
                        error("Expected incomplete file in queued response section but none were found.")
                        error("")
                        error(incomplete_file_block)
                        error("")
                        return False

                    file_path, version, file_content, language, part_id, no_more_parts = files[0]

                    file_part_buffer.add(file_path, file_content, part_id, no_more_parts, version)

                    full_response_text = re.sub(
                        parser.match_file(file_path, incomplete=True),
                        f"{file_content}\n{parser.END_OF_FILE}",
                        full_response_text)

                    if before_file:
                        print_markdown(before_file, end="")

                    queued_response_text = ""
                    is_continuation = True

                else:
                    files = parser.find_files(full_response_text)
                    unfinished_files = [file for file in files if not file[5]] # No more parts

                    # We have cut off mid normal text (i.e. have not seen nomoreparts for a file)
                    if unfinished_files:
                        debug("Stopped with unfinished files, force continue required...")
                        print_markdown(queued_response_text, end="")
                        queued_response_text = "" # Clear the queue
                        is_continuation = True
                    else:
                        debug('Response text left in queue, but no files or incomplete file parts found.')
                        print_markdown(queued_response_text, end="")
                        queued_response_text = "" # Clear the queue
                        is_continuation = False # Important, stops potential infinite loops

        status.stop()

        # --- Metadata and Logging (AFTER processing all chunks) ---

        last_chunk = chunk # HACK: 'chunk' is still in scope from the loop

        # Initialize counters
        prompt_token_count = 0
        candidates_token_count = 0
        cached_content_token_count = 0
        total_token_count = 0

        if last_chunk and last_chunk.usage_metadata:
            prompt_token_count = last_chunk.usage_metadata.prompt_token_count or 0
            candidates_token_count = last_chunk.usage_metadata.candidates_token_count or 0
            cached_content_token_count = last_chunk.usage_metadata.cached_content_token_count or 0
            total_token_count = last_chunk.usage_metadata.total_token_count or 0

        # --- History and File Writing ---

        if should_add_user_prefix:
            history.append('\n**Linus:**\n')

        history.append(f'\n{full_response_text}\n')

        if history_filename:
            with open(history_filename, 'w', encoding='utf-8') as f:
                f.write(''.join(history))

        if is_continuation:
            return True

        if writeable:
            # Write all assembled files
            if assembled_files:
                console.print("\nFiles Changed\n", style="bold")
            for (file_path, version), file_content in assembled_files.items():
                console.print(f"  {file_path}", style="bold green")
                full_path = os.path.join(cwd, file_path)  # Get full path for writing
                directory_path = os.path.dirname(full_path) # Get directory part of the path
                if directory_path and not os.path.exists(directory_path):
                    os.makedirs(directory_path)
                with open(full_path, 'w', encoding='utf-8') as f: # Use full path
                    f.write(file_content)

            if len(assembled_files) > 0:
                print()

        # Update session total tokens
        session_total_tokens += total_token_count

        if is_verbose():
            end_time = time.time()
            duration = end_time - start_time
            total_characters, total_lines = calculate_history_stats()
            console.print()
            console.print(
                f"{human_format_number(total_lines)} lines, "
                f"{human_format_number(total_characters)} characters, "
                f"{human_format_number(total_token_count)} tokens, "
                f"{human_format_number(session_total_tokens)} session tokens, "
                f"{duration:.2f}s ({GEMINI_MODEL.replace('gemini-', '')})"
            )

        return False

    file_part_buffer = FilePartBuffer()
    force_continue = False
    force_continue_counter = 0

    while True:
        try:
            if force_continue:
                if force_continue_counter > 5:
                    error(f"Model is stuck (maxCount = {force_continue_counter}. Please manually continue.")
                    force_continue = False
                    continue

                force_continue_counter += 1
                debug(f"Forcing continuation... attempts={force_continue_counter}")
                force_continue = send_request_to_ai(is_continuation=True)
                continue

            if not force_continue:
                force_continue_counter = 0

            prompt_text = session.prompt("> ")

            if should_exit(prompt_text):
                break

            if prompt_text.startswith('$compact'):
                compact_history()
                continue

            if prompt_text.startswith('$reset'):
                reset_history()
                continue

            if prompt_text.startswith('$refresh'):
                refresh_project_context()
                continue

            if prompt_text.startswith('$continue'):
                process_user_input()
                force_continue = send_request_to_ai(is_continuation=True)
                continue

            process_user_input(prompt_text)

            force_continue = send_request_to_ai(is_continuation=False)

        except KeyboardInterrupt:
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break
        except EOFError:
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break
        except Exception:
            print("Linus has glitched!\n")
            console.print_exception(show_locals=True)
