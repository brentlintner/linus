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
from google.genai import types # Make sure types is imported
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
        error("Please set the GEMINI_MODEL environment variable (ex: GEMINI_MODEL=gemini-1.5-pro-latest)") # Updated example
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
    history_file = history_filename_for_directory(cwd)
    if os.path.exists(history_file):
        debug(f"Resuming from:\n\n {history_file}\n")
        return (os.path.basename(history_file), datetime.now())
    else:
        return None

def list_available_models():
    check_if_env_vars_set()
    client = genai.Client(api_key=GOOGLE_API_KEY)
    for m in client.models.list():
        name = (m.name or '').replace('models/', '')
        description = m.description or "No description"
        input_limit = human_format_number(m.input_token_limit) if m.input_token_limit else "N/A"
        output_limit = human_format_number(m.output_token_limit) if m.output_token_limit else "N/A"
        console.print(f"{name} ({description} - {input_limit} input - {output_limit} output)")

class FilePartBuffer:
    def __init__(self):
        self.buffer = defaultdict(lambda: defaultdict(str))
        self.final_parts = {}

    def add(self, file_path, part_data, current_part, no_more_parts, version):
        if no_more_parts:
            debug(f"Received **all parts signal** for {file_path} (v{version})")
            self.final_parts[(file_path, version)] = True
        # Always add content, even for NoMoreParts block if it has (empty) content
        # Part 0 (NoMoreParts=True) content is usually empty, but parser might give it.
        # Content for NoMoreParts block itself is not added to the assembled file usually.
        # The `parser.find_files` gives the content of the *actual data part*.
        # Let's only buffer actual content parts.
        if not no_more_parts or (no_more_parts and current_part != 0) : # part_id for NoMoreParts block is 0
             debug(f"Received part {current_part} of {file_path} (v{version}) with content")
             self.buffer[(file_path, version)][current_part] = part_data
        elif no_more_parts and current_part == 0:
             debug(f"Received NoMoreParts signal for {file_path} v{version} (part 0), content ignored for buffer.")


    def is_complete(self, file_path, version):
        return (file_path, version) in self.final_parts

    def assemble(self, file_path, version):
        if not self.is_complete(file_path, version):
            return None
        # Ensure all numbered parts are present if `final_parts` is true due to NoMoreParts block
        # This check might be redundant if `is_complete` is the sole gatekeeper.
        # `parser.find_files` already aggregates content from multiple parts before `file_part_buffer.add` is called
        # if the entire file (all its textual parts + NoMoreParts block) is in the input to `find_files`.
        # However, when streaming, `add` is called per received block.

        sorted_parts = sorted(self.buffer.get((file_path, version), {}).items())
        full_content = ''.join(part_data for _, part_data in sorted_parts) # Changed from \n to direct join

        # Clean up after assembly
        if (file_path, version) in self.buffer:
            del self.buffer[(file_path, version)]
        if (file_path, version) in self.final_parts:
            del self.final_parts[(file_path, version)]
        return full_content

def compact_history(history_list, history_filename=None):
    if not history_list:
        return history_list
    history_content = history_list[0]
    try:
        before_file_refs, after_file_refs = history_content.split(parser.FILES_START_SEP, 1)
    except ValueError:
        debug("Compact: FILES_START_SEP not found, no file compaction possible.")
        return history_list

    all_file_versions = parser.find_files(after_file_refs)
    if not all_file_versions:
        debug("No files found in history to prune.")
        return history_list

    latest_versions = defaultdict(int)
    for path, version, *_ in all_file_versions:
        if path not in latest_versions or version > latest_versions[path]:
            latest_versions[path] = version

    files_to_remove = [(path, ver) for path, ver, *_ in all_file_versions if ver < latest_versions.get(path, -1)]
    if not files_to_remove:
        debug("No older file versions found to prune.")
        return history_list

    compacted_after_file_refs = after_file_refs
    removed_count = 0
    for path, version in files_to_remove:
        debug(f"Compact: Removing v{version} of {path}")
        # Regex to match the entire file block including its NoMoreParts signal block
        # This needs to be robust. Using existing matchers.
        pattern_content_block = parser.match_file_with_version(path, version)
        pattern_nomoreparts_block = parser.match_no_more_parts_file_with_version(path, version)

        # Count occurrences before removal for accurate `removed_count`
        # This is complex because one removal might affect subsequent matches if not careful with DOTALL
        # Simpler: assume each (path,version) corresponds to one content part and one NoMoreParts part.
        compacted_after_file_refs = re.sub(pattern_content_block, '', compacted_after_file_refs, flags=re.DOTALL)
        compacted_after_file_refs = re.sub(pattern_nomoreparts_block, '', compacted_after_file_refs, flags=re.DOTALL)
        removed_count +=1 # Count distinct (path, version) pairs removed

    debug(f"Removed {removed_count} older file version blocks in total.")
    if removed_count == 0: return history_list

    compacted_history_content = f"{before_file_refs}{parser.FILES_START_SEP}{compacted_after_file_refs.strip()}\n" # Ensure newline

    if history_filename:
        try:
            with open(history_filename, 'w', encoding='utf-8') as f:
                f.write(compacted_history_content)
            debug(f"Compacted history written to {history_filename}")
        except Exception as e:
            error(f"Failed to write compacted history to {history_filename}: {e}")
    return [compacted_history_content]
def coding_repl(resume=False, writeable=False, ignore_patterns=None, include_patterns=None, cwd=os.getcwd()):
    global history
    client = genai.Client(api_key=GOOGLE_API_KEY)
    extra_ignore_patterns = ignore_patterns.split(',') if ignore_patterns else None
    if include_patterns is not None and "." in include_patterns:
        include_patterns = ["."]

    history_filename = history_filename_for_directory(cwd)
    previous_session = last_session(cwd)

    if resume and previous_session:
        prompt_history_file = os.path.join(os.path.dirname(__file__), f"../tmp/{previous_session[0]}")
        with open(prompt_history_file, 'r', encoding='utf-8') as f:
            prompt_history = f.read()
        history.append(prompt_history)
        recap = re.sub(parser.match_before_conversation_history(), '', prompt_history, flags=re.DOTALL)
        # Recapping logic remains the same...
        files = parser.find_files(recap)
        for file_path, version, content, _, _, _ in files:
            language = parser.get_language_from_extension(file_path)
            replaced_content = content.replace("\\", "\\\\") # Basic escaping for display
            suffix = " (EMPTY)" if not replaced_content else ""
            # Use a more robust way to replace only the specific file block being recapped
            # This current sub might be too greedy if multiple versions/mentions exist in recap
            recap = re.sub(
                parser.match_file_with_version(file_path, version), # Match specific version
                rf'#### {file_path} (v{version}){suffix}\n\n```{language}\n{replaced_content}\n```\n',
                recap,
                flags=re.DOTALL,
                count=1) # Replace only the first occurrence matching this version
            # Remove its associated NoMoreParts block too
            recap = re.sub(parser.match_no_more_parts_file_with_version(file_path, version), '', recap, flags=re.DOTALL, count=1)
        recap = re.sub(
            parser.match_snippet(),
            r'#### \1\n\n```\1\n\2\n```\n',
            recap,
            flags=re.DOTALL)
        print_markdown(recap)

    else:
        history.clear() # Ensure history is clean if not resuming or no prev session
        if previous_session and not resume: # Explicitly starting new, remove old
            try:
                os.remove(history_filename)
            except OSError as e:
                debug(f"Could not remove old history file {history_filename}: {e}")
        history.append(prompt_prefix(extra_ignore_patterns, include_patterns, cwd))
        # Initial history write is handled by the main loop or process_user_input

    session = create_prompt_session(cwd)
    session_total_tokens = 0
    file_part_buffer = FilePartBuffer() # Moved here, one buffer per REPL session

    def calculate_history_stats():
        total_characters = sum(len(entry) for entry in history)
        total_lines = sum(len(entry.splitlines()) for entry in history)
        return total_characters, total_lines

    def reset_history_action():
        nonlocal session_total_tokens
        history.clear()
        file_part_buffer.__init__() # Reset buffer too
        history.append(prompt_prefix(extra_ignore_patterns, include_patterns, cwd))
        if history_filename:
            with open(history_filename, 'w', encoding='utf-8') as f:
                f.write(''.join(history))
        session_total_tokens = 0
        print(' ', flush=True)
        console.print("History reset.", style="bold yellow")

    def refresh_project_context_action():
        if not history: # Should not happen if reset_history_action initializes
            history.append("") # Ensure history has at least one element

        current_conversation = ""
        if parser.CONVERSATION_START_SEP in history[0]:
             # Preserve conversation part if it exists within the first history element
            _, current_conversation = history[0].split(parser.CONVERSATION_START_SEP, 1)
            current_conversation = parser.CONVERSATION_START_SEP + current_conversation

        new_prefix = prompt_prefix(extra_ignore_patterns, include_patterns, cwd)
        history[0] = new_prefix + current_conversation

        if history_filename:
            with open(history_filename, 'w', encoding='utf-8') as f:
                f.write(''.join(history))
        print(' ', flush=True)
        console.print("Project context refreshed.", style="bold yellow")

    def process_user_input(prompt_text=""):
        if not prompt_text: return
        history.append(f'\n**Brent:**\n\n{prompt_text}\n')
        # File referencing logic
        history_snapshot = ''.join(history) # Use current history for finding highest version
        file_references = parser.find_file_references(prompt_text)
        for file_path in file_references:
            full_file_path = os.path.join(cwd, file_path)
            if not os.path.isfile(full_file_path):
                # Optionally, print a warning if a referenced file doesn't exist
                # error(f"Referenced file not found: {file_path}")
                continue
            highest_version = 0
            # parser.find_files needs the content where files are defined, not the whole history blindly
            # Assuming file definitions are appended. Look in the part of history that contains file blocks.
            # For simplicity, search the whole snapshot; compact_history will clean up.
            for existing_fp, ver, _, _, _, _ in parser.find_files(history_snapshot):
                if existing_fp == file_path:
                    highest_version = max(highest_version, ver)
            new_version = highest_version + 1
            debug(f"Appending file {file_path} (v{new_version}) to history context")
            file_content_block = get_file_contents(full_file_path, new_version) # Pass full_file_path
            history.append(file_content_block)
        if history_filename:
            with open(history_filename, 'w', encoding='utf-8') as f:
                f.write(''.join(history))

    def send_request_to_ai(is_continuation_from_user_cmd=False):
        nonlocal session_total_tokens
        should_add_linus_prefix = not is_continuation_from_user_cmd

        request_text = ''.join(history)
        # Ensure CONVERSATION_END_SEP is only added if not already somehow present from continuation
        if not request_text.strip().endswith(parser.CONVERSATION_END_SEP):
             request_text += f'\n{parser.CONVERSATION_END_SEP}\n'

        contents = [types.Part.from_text(text=request_text)]
        start_time = time.time()
        stream = client.models.generate_content_stream(model=GEMINI_MODEL, contents=contents)

        full_response_text = ""
        queued_response_text = ""
        assembled_files = {}

        # Use the class member file_part_buffer

        with console.status("Linus is thinking...", spinner="point") as status:
            active_chunk = None
            for chunk in stream:
                active_chunk = chunk # Keep track of the latest chunk
                if not chunk.text: continue
                queued_response_text += chunk.text
                full_response_text += chunk.text

                while True: # Inner loop to process queued_response_text
                    made_progress_in_inner_loop = False
                    meta_indices = [queued_response_text.find(s) for s in [parser.FILE_METADATA_START, parser.SNIPPET_METADATA_START] if s]
                    valid_meta_indices = [idx for idx in meta_indices if idx != -1]
                    earliest_meta_idx = min(valid_meta_indices) if valid_meta_indices else -1

                    if earliest_meta_idx == 0: pass # Starts with metadata
                    elif earliest_meta_idx > 0: # Leading plain text
                        text_to_print = queued_response_text[:earliest_meta_idx]
                        status.update("Linus is typing...")
                        print_markdown(text_to_print, end="")
                        queued_response_text = queued_response_text[earliest_meta_idx:]
                        made_progress_in_inner_loop = True
                    else: # No metadata in queue, all plain text
                        newline_idx = queued_response_text.find("\n")
                        if newline_idx != -1:
                            text_to_print = queued_response_text[:newline_idx+1]
                            status.update("Linus is typing...")
                            print_markdown(text_to_print, end="")
                            queued_response_text = queued_response_text[newline_idx+1:]
                            made_progress_in_inner_loop = True
                        else: break # Break inner loop, wait for more stream

                    if not queued_response_text.strip():
                        if not made_progress_in_inner_loop: break
                        else: continue

                    single_block_pattern = rf"^({parser.FILE_METADATA_START}(?:.|\n)*?{parser.END_OF_FILE}|{parser.SNIPPET_METADATA_START}(?:.|\n)*?{parser.END_OF_SNIPPET})"
                    block_match = re.match(single_block_pattern, queued_response_text, re.DOTALL)

                    if block_match:
                        block_text_content = block_match.group(1)
                        if parser.is_file(block_text_content):
                            parsed_files = parser.find_files(block_text_content) # find_files on just this block
                            if parsed_files:
                                file_path, version, file_content_part, lang, part_id, no_more_parts = parsed_files[0]
                                if not file_part_buffer.is_complete(file_path, version): # Update status if not already complete
                                     status.update(f"Linus is writing {file_path}...")
                                file_part_buffer.add(file_path, file_content_part, part_id, no_more_parts, version)
                                if file_part_buffer.is_complete(file_path, version):
                                    assembled_content = (file_part_buffer.assemble(file_path, version) or "").strip('\n')
                                    assembled_files[(file_path, version)] = assembled_content
                                    code_to_display = generate_diff(os.path.join(cwd,file_path), assembled_content) # Pass full path to generate_diff
                                    actual_lang = parser.get_language_from_extension(file_path)
                                    display_lang = "diff" if os.path.exists(os.path.join(cwd, file_path)) and code_to_display != assembled_content else actual_lang
                                    suffix = " (EMPTY)" if not assembled_content else ""
                                    print_markdown(f"#### {file_path} v{version}{suffix}")
                                    print_markdown(f"```{display_lang}\n{code_to_display}\n```")
                                    status.update("Linus is typing...")
                        elif parser.is_snippet(block_text_content):
                            parsed_snippets = parser.find_snippets(block_text_content)
                            if parsed_snippets:
                                lang, code = parsed_snippets[0]
                                status.update("Linus is typing...")
                                print_markdown(f"```{lang}\n{code}\n```")
                        else: # Should not happen if patterns are correct
                             status.update("Linus is typing...")
                             print_markdown(block_text_content, end="") # Print as-is to avoid loss
                        queued_response_text = queued_response_text[len(block_text_content):].lstrip()
                        made_progress_in_inner_loop = True
                    else: # No complete single block at start, might be incomplete
                        if queued_response_text.startswith(parser.FILE_METADATA_START):
                            in_prog_file_p = parser.find_in_progress_file(queued_response_text)
                            if in_prog_file_p: status.update(f"Linus is writing {in_prog_file_p}...")
                        elif queued_response_text.startswith(parser.SNIPPET_METADATA_START):
                             status.update("Linus is writing a snippet...") # Generic snippet status
                        break # Break inner loop, need more data
                    if not made_progress_in_inner_loop: break

            if queued_response_text.strip(): # Print any final plain text after loop
                status.update("Linus is typing...")
                print_markdown(queued_response_text)
            queued_response_text = "" # Clear queue

        status.stop()

        last_chunk_finish_reason = None
        if active_chunk and active_chunk.candidates:
            last_chunk_finish_reason = active_chunk.candidates[0].finish_reason

        is_continuation_needed = False
        if last_chunk_finish_reason and \
           last_chunk_finish_reason != types.FinishReason.STOP and \
           last_chunk_finish_reason != types.FinishReason.FINISH_REASON_UNSPECIFIED:
            debug(f"Continuation needed due to AI finish reason: {last_chunk_finish_reason.name}")
            is_continuation_needed = True
        else: # Check buffer and raw response if AI claims STOP or unspecified
            for fp_key, buffered_parts in list(file_part_buffer.buffer.items()):
                if buffered_parts and not file_part_buffer.is_complete(fp_key[0], fp_key[1]):
                    debug(f"Continuation needed: File {fp_key[0]} v{fp_key[1]} is incomplete in buffer.")
                    is_continuation_needed = True
                    break
            if not is_continuation_needed:
                all_files_in_resp = parser.find_files(full_response_text) # find_files aggregates parts
                for _, _, _, _, _, no_more_parts_flag in all_files_in_resp:
                    if not no_more_parts_flag:
                        debug("Continuation needed: A file in the raw response is missing its NoMoreParts signal.")
                        is_continuation_needed = True
                        break

        if should_add_linus_prefix:
            history.append('\n**Linus:**\n')
        history.append(f'\n{full_response_text}\n')

        if history_filename:
            with open(history_filename, 'w', encoding='utf-8') as f: f.write(''.join(history))

        if writeable and assembled_files:
            console.print("\nFiles Changed\n", style="bold")
            for (file_path, version), file_content_to_write in assembled_files.items():
                console.print(f"  {file_path}", style="bold green")
                full_write_path = os.path.join(cwd, file_path)
                os.makedirs(os.path.dirname(full_write_path), exist_ok=True)
                with open(full_write_path, 'w', encoding='utf-8') as f: f.write(file_content_to_write)
            if assembled_files: print()

        # Token counting and verbose logging
        prompt_token_count, candidates_token_count, cached_content_token_count, total_token_count = 0,0,0,0
        if active_chunk and active_chunk.usage_metadata:
            m = active_chunk.usage_metadata
            prompt_token_count = m.prompt_token_count or 0
            candidates_token_count = m.candidates_token_count or 0
            # cached_content_token_count = m.cached_content_token_count or 0 # If available
            total_token_count = m.total_token_count or 0
        session_total_tokens += total_token_count
        if is_verbose():
            duration = time.time() - start_time
            chars, lines = calculate_history_stats()
            console.print()
            if is_debug():
                console.print(f"{human_format_number(session_total_tokens)} (sess), {human_format_number(prompt_token_count)} (req), {human_format_number(candidates_token_count)} (res), {human_format_number(lines)} (lns), {human_format_number(chars)} (ch), {duration:.2f}s ({GEMINI_MODEL})")
            else:
                console.print(f"{human_format_number(session_total_tokens)} tokens, {duration:.2f}s")

        return is_continuation_needed

    force_continue_flag = False
    force_continue_attempts = 0
    MAX_CONTINUE_ATTEMPTS = 5

    while True:
        try:
            if history_filename: # Save before each prompt
                with open(history_filename, 'w', encoding='utf-8') as f: f.write("".join(history))

            if force_continue_flag:
                if force_continue_attempts >= MAX_CONTINUE_ATTEMPTS:
                    error(f"Model stuck after {force_continue_attempts} attempts. Please use $continue or enter new input.")
                    force_continue_flag = False
                    force_continue_attempts = 0
                    continue
                force_continue_attempts += 1
                debug(f"Forcing continuation... (attempt {force_continue_attempts})")
                force_continue_flag = send_request_to_ai(is_continuation_from_user_cmd=True) # True because it's an auto-continue
                continue

            force_continue_attempts = 0 # Reset if not forcing
            prompt_text = session.prompt("> ")

            if prompt_text.startswith('$exit'): break
            if prompt_text.startswith('$compact'):
                history = compact_history(history, history_filename)
                print(' ', flush=True); console.print("History compacted.", style="bold yellow")
                continue
            if prompt_text.startswith('$reset'):
                reset_history_action()
                continue
            if prompt_text.startswith('$refresh'):
                refresh_project_context_action()
                continue
            if prompt_text.startswith('$continue'):
                process_user_input() # Process empty input just to save history with Linus prefix if needed
                force_continue_flag = send_request_to_ai(is_continuation_from_user_cmd=True)
                continue

            process_user_input(prompt_text)
            force_continue_flag = send_request_to_ai(is_continuation_from_user_cmd=False)

        except KeyboardInterrupt:
            if input("\nReally quit? (y/n) ").lower() == 'y': break
        except EOFError:
            if input("\nReally quit? (y/n) ").lower() == 'y': break
        except Exception:
            print("Linus has glitched!\n")
            console.print_exception(show_locals=True)
            # Maybe offer a $reset or $continue or try to recover state?
            # For now, just loop. User can $reset if needed.
