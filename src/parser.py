import os
import re
import shlex
from pygments.util import ClassNotFound
from pygments.lexers import get_lexer_for_filename, guess_lexer_for_filename

# NOTE: We must use this way to generate the placeholder wrapper so this parsing doesn't fail for this file when using this project on itself
def placeholder(placeholder):
    return r'{{{' + placeholder + r'}}}'

FILE_METADATA_START =       placeholder('START FILE METADATA')
FILE_METADATA_END =         placeholder('END FILE METADATA')
SNIPPET_METADATA_START =    placeholder('START CODE SNIPPET METADATA')
SNIPPET_METADATA_END =      placeholder('END CODE SNIPPET METADATA')
TERMINAL_METADATA_START =   placeholder('START TERMINAL METADATA')
TERMINAL_METADATA_END =     placeholder('END TERMINAL METADATA')
END_OF_FILE =               placeholder('END OF FILE')
FILE_TREE_PLACEHOLDER =     placeholder('FILE_TREE_JSON')
FILES_PLACEHOLDER =         placeholder('FILE_REFERENCES')
FILES_START_SEP =           placeholder('FILE_REFERENCES START')
FILES_END_SEP =             placeholder('FILE_REFERENCES END')
CONVERSATION_START_SEP =    placeholder('CONVERSATION_HISTORY START')
CONVERSATION_END_SEP =      placeholder('CONVERSATION_HISTORY END')
TERMINAL_LOGS_PLACEHOLDER = placeholder('TERMINAL_LOGS')

def find_file_references(content):
    file_references = re.findall(r'@(\S+)', content)

    return [re.sub(r"[^\w\s]+$", '', file_reference) for file_reference in file_references]

def find_in_progress_file(content):
    regex = rf'{FILE_METADATA_START}.*?\nPath: (.*?)\n.*?NoMoreParts: (True|False).*?{FILE_METADATA_END}'
    file_match = re.search(regex, content, flags=re.DOTALL)

    if file_match:
        file_path = file_match.group(1)
        no_more_parts = file_match.group(2) == 'True'
        return (file_path, no_more_parts)
    else:
        return None

def find_in_progress_snippet(content):
    regex = rf'{SNIPPET_METADATA_START}.*?\nLanguage: (.*?)\n{SNIPPET_METADATA_END}(?:(?!{END_OF_FILE}).)*$'
    snippet_match = re.search(regex, content, flags=re.DOTALL)
    return snippet_match.group(1) if snippet_match else None

def safe_int(value, default=1):
    try:
        if value is None:
            return default
        return int(value)
    except ValueError:
        return default

def find_files(content):
    # This regex should correctly capture all parts of a file block, including the content.
    regex = (
        rf'{FILE_METADATA_START}.*?' +  # Match the start of the metadata
        rf'\nPath: (.*?)\nLanguage: (.*?)\n(?:Version: (\d+)\n)' + # Capture Path, Language, and optional Version
        rf'(?:Part: (\d+)\n)(?:NoMoreParts: (True|False)\n).*?{FILE_METADATA_END}\n?(.*?)(?:{END_OF_FILE})' # Capture Part and NoMoreParts, then the content, and finally the end of file marker
    )

    file_matches = re.finditer(regex, content, flags=re.DOTALL)

    all_file_parts = [(
        match.group(1), # Path
        safe_int(match.group(3)), # Version
        match.group(6),  # Content
        match.group(2),  # Language
        safe_int(match.group(4)), # Part
        match.group(5) == 'True') # NoMoreParts
        for match in file_matches]

    all_files = {}

    # Assemble the parts for each (file, version)
    for path, version, content, language, part, no_more_parts in all_file_parts:
        file_key = (path, version)
        if file_key not in all_files:
            all_files[file_key] = []
        all_files[file_key].append((content, language, part, no_more_parts))
        all_files[file_key].sort(key=lambda x: x[2]) # Ensure parts are in order

    result = []

    for key_tuple, parts_array in all_files.items():
        joined_content = ''.join([part[0] for part in parts_array]) # Join all content parts
        language = parts_array[-1][1] # Get the language from the LAST part
        part_id = max([part[2] for part in parts_array]) # Get the highest part number
        no_more_parts = parts_array[-1][3] # Get the no more parts flag from the LAST part
        result.append(list(key_tuple) + [joined_content.strip(), language, part_id, no_more_parts]) # Use strip here.  Important!

    return result

def find_snippets(content):
    regex = rf'{SNIPPET_METADATA_START}.*?\nLanguage: (.*?)\n{SNIPPET_METADATA_END}\n?(.*?)(?:{END_OF_FILE})'
    snippet_matches = re.finditer(regex, content, flags=re.DOTALL)
    return [(match.group(1), match.group(2).rstrip('\n')) for match in snippet_matches] # Still rstrip this one, it seems.

def is_file(content):
    return str(content).strip().startswith(FILE_METADATA_START)

def is_snippet(content):
    return str(content).strip().startswith(SNIPPET_METADATA_START)

def is_terminal_log(content):
    return str(content).strip().startswith(TERMINAL_METADATA_START)

def match_code_block():
    file_regex = rf'{FILE_METADATA_START}.*?{FILE_METADATA_END}.*?{END_OF_FILE}'
    snippet_regex = rf'{SNIPPET_METADATA_START}.*?{SNIPPET_METADATA_END}.*?{END_OF_FILE}'
    return rf'({file_regex}|{snippet_regex})'

def match_file(file_path):
    escaped = re.escape(file_path)
    return rf'{FILE_METADATA_START}.*?\nPath: {escaped}\n.*?{FILE_METADATA_END}\n?(.*?){END_OF_FILE}'

def match_snippet():
    return rf'{SNIPPET_METADATA_START}.*?\nLanguage: (.*?)\n.*?{SNIPPET_METADATA_END}\n?(.*?){END_OF_FILE}'

def match_before_conversation_history():
    return rf'^(.*?){CONVERSATION_START_SEP}'

def file_block(file_path, content, language=None, part=1, version=1):
    language = get_language_from_extension(file_path) if not language else language
    return f"""
{FILE_METADATA_START}
Path: {file_path}
Language: {language}
Version: {version}
Part: {part}
NoMoreParts: True
{FILE_METADATA_END}
{content}
{END_OF_FILE}
"""

def snippet_block(content, language):
    return f"""
{SNIPPET_METADATA_START}
Language: {language}
{SNIPPET_METADATA_END}
{content}
{END_OF_FILE}
"""

def terminal_log_block(content, title):
    return f"""
{TERMINAL_METADATA_START}
Session: {title}
{TERMINAL_METADATA_END}
{content}
{END_OF_FILE}
"""

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

            # Use guess_lexer_for_filename, passing filename *and* first_line
            try:
                lexer = guess_lexer_for_filename(filename, first_line)
                return lexer.name.lower()
            except ClassNotFound:
                return "text"  # Special case if guess_lexer can't figure it out.

    except ClassNotFound:
        return "text"
    except FileNotFoundError:
        return "text"
    except Exception as e:
        print(f"Error in get_language_from_extension: {e}")
        return "text"

def get_program_from_shebang(shebang_line):
    if not shebang_line.startswith("#!"):
        return None

    # Split shebang using shlex, to correctly handle arguments and spaces
    lexer = shlex.shlex(shebang_line[2:], posix=True)  # [2:] to skip the '#!'
    lexer.whitespace_split = True
    parts = list(lexer)

    if not parts:
        return None

    program = parts[0]  # First element after splitting
    # print(f"Initial program: {program}")  # Debug print

    if program == "env":
        if len(parts) > 1:
            program = parts[1]
            # print(f"Program after 'env': {program}") # Debug print
        else:
            # print("'env' with no program") # Debug print
            return None

    # print(f"Returning program: {os.path.basename(program)}")  # Debug print
    return program.strip() # Remove .strip()