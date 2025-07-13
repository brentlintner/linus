import os
import time
import re
import json
from google import genai
from google.genai import types
from . import parser
from .parser import FilePartBuffer
from .repl import create_prompt_session
from .tmux_utils import get_tmux_logs
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
    human_format_number
)
from .database import initialize_database, User, Chat, db_proxy

def llm_prompt(ignore_patterns=None, include_patterns=None, cwd=os.getcwd()):
    # TODO: if prompt is larger than 500K characters, show a warning and confirmation (in debug?)
    try:
        with open(PROMPT_PREFIX_FILE, 'r', encoding='utf-8') as f:
            prefix = f.read()
    except FileNotFoundError:
        return "Could not find background.md"

    if include_patterns is None or not include_patterns:
        # No files included, return prefix without file tree and file contents.
        return prefix.replace(parser.FILE_TREE_PLACEHOLDER, '[]').replace(parser.FILES_PLACEHOLDER, '')

    project_structure_json = generate_project_structure(ignore_patterns, include_patterns, cwd)
    project_files = generate_project_file_contents(ignore_patterns, include_patterns, cwd)

    project_structure = json.dumps(
        project_structure_json, indent=2) if is_debug() else json.dumps(project_structure_json, separators=(',', ':'))

    prefix = prefix.replace(parser.FILE_TREE_PLACEHOLDER, f'{project_structure}')
    prefix = prefix.replace(parser.FILES_PLACEHOLDER, f'{project_files}')
    prefix = prefix.replace(parser.TERMINAL_LOGS_PLACEHOLDER, get_tmux_logs())

    with db_proxy:
        chats = Chat.select().join(User).order_by(Chat.timestamp)
        for chat in chats:
            prefix += f'\n**{chat.user.name.capitalize()}:**\n\n{chat.message}'

    prefix += f'\n{parser.CONVERSATION_END_SEP}\n'

    return prefix

def process_user_input(state, prompt_text=""):
    """Processes user input, updating history and handling file references."""
    if not prompt_text:
        return

    human_user, _ = User.get_or_create(name='brent')
    message = prompt_text.strip()

    # Ignore converting file references for now, we will always be adding latest files
    # TODO: eventually we can use this to add specific files to the file references if they are not already "open"
    #       OR we go through all messages, find the max version of each file, and then set those as the file reference version (see how llm handles this)
    # file_references = parser.find_file_references(message)

    Chat.create(user=human_user, message=message)

def process_response_metadata(response, state):
    # Initialize counters
    prompt_token_count = 0
    candidates_token_count = 0
    cached_content_token_count = 0
    total_token_count = 0
    thoughts_token_count = 0
    tool_use_prompt_token_count = 0

    if response and response.usage_metadata:
        prompt_token_count = response.usage_metadata.prompt_token_count or 0
        candidates_token_count = response.usage_metadata.candidates_token_count or 0
        cached_content_token_count = response.usage_metadata.cached_content_token_count or 0
        total_token_count = response.usage_metadata.total_token_count or 0
        thoughts_token_count = response.usage_metadata.thoughts_token_count or 0
        tool_use_prompt_token_count = response.usage_metadata.tool_use_prompt_token_count or 0

    state['session_total_tokens'] += total_token_count

    if is_verbose():
        end_time = time.time()
        start_time = state.get('start_time', end_time)
        duration = end_time - start_time
        console.print()

        if is_debug():
            # --- Grounding Metadata ---
            grounding_metadata = None
            # If the last chunk has candidates and the first candidate has grounding metadata
            if response.candidates and response.candidates[0]:
                grounding_metadata = getattr(response.candidates[0], 'grounding_metadata', None)

                if grounding_metadata and grounding_metadata.grounding_chunks:
                    console.print("Grounding Sources", style="bold yellow")
                    sites = []
                    for result in grounding_metadata.grounding_chunks:
                        ground = result.web or result.retrieved_context
                        if re.search("grounding-api-redirect", ground.uri, re.IGNORECASE):
                            sites.append(ground.title)
                        else:
                            sites.append(ground.uri)

                    for site in list(set(sites)):
                        console.print(f"  - {re.sub(r'https?://', '', site)}")

                    console.print()

            console.print(
                f"{human_format_number(state['session_total_tokens'])} (session), "
                f"{human_format_number(prompt_token_count)} (request), "
                f"{human_format_number(candidates_token_count)} (response), "
                f"{human_format_number(thoughts_token_count)} (thoughts), "
                f"{human_format_number(tool_use_prompt_token_count)} (tool), "
                f"{human_format_number(cached_content_token_count)} (cached), "
                f"{duration:.2f}s ({GEMINI_MODEL})"
            )
        else:
            console.print(
                f"{human_format_number(state['session_total_tokens'])} tokens, "
                f"{human_format_number(prompt_token_count)} prompt, "
                f"{human_format_number(cached_content_token_count)} cached, "
                f"{duration:.2f}s"
            )

def process_request_stream(stream, state):
    """Processes the streamed response from the AI."""
    full_response_text = ""
    queued_response_text = ""

    cwd = state['cwd']
    assembled_files = {}
    file_part_buffer = state['file_part_buffer']

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
                    file_path, version, file_content, language, part_id, no_more_parts = files[0] # Get the first file only (hacky, but works for now)

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
                    snippets = parser.find_snippets(section)
                    if snippets:
                        language, code = snippets[0]  # Get the first snippet (TODO: handle multiple snippets? will there be multiple based on parsing?)
                        section = f"```{language}\n{code}\n```"
                        print_markdown(section)

        # Keep the last chunk for metadata processing (*it is still in scope here unless we got zero chunks but that's another issue*)
        last_chunk = chunk

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
                    incomplete_file_block = f"{parser.FILE_METADATA_START}{after_file}"

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
                    state['force_continue'] = False
                    return full_response_text, last_chunk, assembled_files

                file_path, version, file_content, language, part_id, no_more_parts = files[0]  # Get the first file only (hacky, but works for now)

                file_part_buffer.add(file_path, file_content, part_id, no_more_parts, version)

                full_response_text = re.sub(
                    parser.match_file(file_path, incomplete=True),
                    f"{file_content}\n{parser.END_OF_FILE}",
                    full_response_text)

                if before_file:
                    print_markdown(before_file, end="")

                queued_response_text = ""
                state['force_continue'] = True # Force continue to handle the incomplete file
            else:
                files = parser.find_files(full_response_text)
                unfinished_files = [file for file in files if not file[5]] # No more parts (check the last element, no_more_parts)

                # We have cut off mid normal text (i.e. have not seen nomoreparts for a file)
                if unfinished_files:
                    debug("Stopped with unfinished files, force continue required...")
                    print_markdown(queued_response_text, end="")
                    queued_response_text = "" # Clear the queue
                    state['force_continue'] = True
                # We just have normal text left, print it
                else:
                    print_markdown(queued_response_text, end="")
                    queued_response_text = "" # Clear the queue
                    state['force_continue'] = False # Important, stops potential infinite loops

    status.stop()

    return full_response_text, last_chunk, assembled_files

def process_response(full_response_text, assembled_files, state):
    llm_user, _ = User.get_or_create(name='linus')

    # If we are forcing a continuation, we need to append the response to the last chat message by the llm user
    if state['force_continue']:
        # TODO: handle no chats found (should not happen)
        last_chat = Chat.select().where(Chat.user == llm_user).order_by(Chat.timestamp.desc()).get_or_none()
        last_chat.message += f"\n\n{full_response_text.strip()}\n"
        last_chat.message = last_chat.message.strip()
        last_chat.save()
        return

    cwd = state['cwd']

    Chat.create(user=llm_user, message=full_response_text.strip())

    if state['writeable']:
        # Write all assembled files
        if assembled_files:
            console.print("\nFiles Changed\n", style="bold yellow")
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

def print_recap():
    # Show recap of previous chats
    # TODO: add flag to not show previous chats on resume
    with db_proxy:
        chats = Chat.select().join(User).order_by(Chat.timestamp)
        for chat in chats:
            message = chat.message.strip()

            files = parser.find_files(message)
            for file_path, version, content, _, _, _ in files:
                language = parser.get_language_from_extension(file_path)
                # HACK: ideally we avoid doing this per file, but it's a quick fix for now
                replaced_content = content.replace("\\", "\\\\")
                suffix = " (EMPTY)" if not replaced_content else ""
                message = re.sub(
                    parser.match_file(file_path),
                    rf'#### {file_path} (v{version}){suffix}\n\n```{language}\n{replaced_content}\n```',
                    message,
                    flags=re.DOTALL,
                    count=1)
                # HACK: extra parts are not removed just the first one
                message = re.sub(parser.match_file(file_path), '', message, flags=re.DOTALL)

            message = re.sub(
                parser.match_snippet(),
                r'#### \1\n\n```\1\n\2\n```',
                message,
                flags=re.DOTALL)

            print_markdown(f'**{chat.user.name.capitalize()}:**\n\n{message}')

def send_request_to_ai(state, client):
    """Sends a request to the AI and processes the streamed response."""
    request_text = llm_prompt(
        ignore_patterns=state['ignore_patterns'],
        include_patterns=state['include_patterns'],
        cwd=state['cwd']
    )

    if is_debug():
        id = state['cwd'].replace(os.path.sep, '_')
        tmp_file = f"tmp/linus_request_{id}.txt"
        with open(tmp_file, 'w', encoding='utf-8') as f:
            f.write(request_text)
        debug(f"Current request saved to {tmp_file}")

    state['start_time'] = time.time()

    tools = [types.Tool(google_search=types.GoogleSearch()), types.Tool(url_context=types.UrlContext())]
    config = types.GenerateContentConfig(tools=tools, response_modalities=["TEXT"])
    contents = [types.Part.from_text(text=request_text)]

    stream = client.models.generate_content_stream(model=GEMINI_MODEL, contents=contents, config=config)

    full_response_text, last_chunk, assembled_files = process_request_stream(stream, state)

    process_response(full_response_text, assembled_files, state)

    process_response_metadata(last_chunk, state) # HACK: 'chunk' is still in scope from the loop

# TODO: make into a class or better structure?
def session_state(cwd, resume=False, writeable=False, ignore_patterns=None, include_patterns=None):
    # Split the comma-separated ignore patterns into a list
    ignore_patterns = ignore_patterns.split(',') if ignore_patterns else None

    # Convert include_patterns to a list if it's not None, otherwise keep it as None
    if include_patterns is not None and "." in include_patterns:
        include_patterns = ["."]  # Treat "." as a special case, including all files.

    return {
        'session_total_tokens': 0,
        'file_part_buffer': FilePartBuffer(),
        'force_continue': False,
        'force_continue_counter': 0,
        'writeable': writeable,
        'resume': resume,
        'ignore_patterns': ignore_patterns,
        'include_patterns': include_patterns,
        'cwd': cwd,
    }

def repl_loop(session, client, state):
    while True:
        try:
            if state['force_continue']:
                if state['force_continue_counter'] > 5:
                    error(f"Model is stuck (maxCount = {state['force_continue_counter']}. Please manually continue.")
                    state['force_continue'] = False
                    continue

                state['force_continue_counter'] += 1
                debug(f"Forcing continuation... attempts={state['force_continue_counter']}")
                send_request_to_ai(state, client)
                continue

            if not state['force_continue']:
                state['force_continue_counter'] = 0

            prompt_text = session.prompt("> ")

            if prompt_text.startswith('$exit'):
                break

            # TODO: essentially strip all chat history of file references (so all files are v1 (open files))
            if prompt_text.startswith('$compact'):
                debug("(TODO) Compacting database...")
                break

            if prompt_text.startswith('$reset'):
                debug("(TODO) Resetting chat history...")
                break

            if prompt_text.startswith('$continue'):
                state['force_continue'] = True
                send_request_to_ai(state, client)
                continue

            process_user_input(state, prompt_text)

            state['force_continue'] = False  # Reset force continue state
            send_request_to_ai(state, client)

        except KeyboardInterrupt:
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break
        except EOFError:
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break
        except Exception:
            print("Linus has glitched!\n")
            console.print_exception(show_locals=True)

def coding_repl(resume=False, writeable=False, ignore_patterns=None, include_patterns=None, cwd=os.getcwd()):
    initialize_database(cwd)

    client = genai.Client(api_key=GOOGLE_API_KEY)

    session = create_prompt_session(cwd)

    state = session_state(cwd, resume, writeable, ignore_patterns, include_patterns)

    print_recap()

    repl_loop(session, client, state)
