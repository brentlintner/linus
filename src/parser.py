import os
import re
import shlex
from collections import defaultdict
from pygments.util import ClassNotFound
from pygments.lexers import get_lexer_for_filename, guess_lexer_for_filename
from .logger import debug

# NOTE: We must use this way to generate the placeholder wrapper so this parsing doesn't fail for this file when
#       using this project on itself
def placeholder(name):
    return r'{{{' + name + r'}}}'

FILE_METADATA_START =       placeholder('START FILE METADATA')
FILE_METADATA_END =         placeholder('END FILE METADATA')
SNIPPET_METADATA_START =    placeholder('START CODE SNIPPET METADATA')
SNIPPET_METADATA_END =      placeholder('END CODE SNIPPET METADATA')
TERMINAL_METADATA_START =   placeholder('START TERMINAL METADATA')
TERMINAL_METADATA_END =     placeholder('END TERMINAL METADATA')
END_OF_FILE =               placeholder('END OF FILE')
END_OF_SNIPPET =            placeholder('END OF CODE SNIPPET')
END_OF_TERMINAL_LOG =       placeholder('END OF TERMINAL LOG')
FILE_TREE_PLACEHOLDER =     placeholder('FILE_TREE_JSON')
FILES_PLACEHOLDER =         placeholder('FILE_REFERENCES')
FILES_START_SEP =           placeholder('FILE_REFERENCES START')
FILES_END_SEP =             placeholder('FILE_REFERENCES END')
TERMINAL_LOGS_PLACEHOLDER = placeholder('TERMINAL_LOGS')
PROJECT_SPECIFIC_GUIDE =    placeholder('PROJECT_SPECIFIC_GUIDE')
GLOBAL_USER_GUIDE =         placeholder('GLOBAL_USER_GUIDE')

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

def find_file_references(content):
    file_references = re.findall(r'@(\S+)', content)

    return [re.sub(r"[^\w\s]+$", '', file_reference) for file_reference in file_references]

# TODO: find all in progress files
def find_in_progress_file(content):
    regex = rf'{FILE_METADATA_START}.*?\nPath: (.*?)\n'
    file_match = re.search(regex, content, flags=re.DOTALL)

    if file_match:
        file_path = file_match.group(1)
        return file_path

    return None

def find_in_progress_snippet(content):
    regex = rf'{SNIPPET_METADATA_START}.*?\nLanguage: (.*?)\n'
    snippet_match = re.search(regex, content, flags=re.DOTALL)
    return snippet_match.group(1) if snippet_match else None

def safe_int(value, default=1):
    try:
        if value is None:
            return default
        return int(value)
    except ValueError:
        return default

def parse_metadata(metadata_str):
    """Parses the metadata string into a dictionary.
       Handles missing fields and defaults.  Prioritizes 'NoMoreParts'.
    """
    metadata = {}
    for line in metadata_str.splitlines():
        match = re.match(r'^\s*([^:]+):\s*(.*?)\s*$', line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            if key == 'NoMoreParts':
                metadata[key] = value.lower() == 'true'
            elif key in ('Part', 'Version'):
                metadata[key] = safe_int(value, 1)  # Safe integer conversion for Part and Version
            else:
                metadata[key] = value

    # Set defaults if not present, but ONLY if NoMoreParts isn't explicitly set.
    if 'NoMoreParts' not in metadata:
        metadata['Part'] = metadata.get('Part', 1)
        metadata['NoMoreParts'] = False  # Default if 'Part' is present but 'NoMoreParts' is not.
    else:
        # If NoMoreParts *is* present, 'Part' is irrelevant.  We set it to a consistent 0.
        metadata['Part'] = 0

    metadata['Version'] = metadata.get('Version', 1)  # Version always defaults to 1 if not present

    return metadata

def find_files(content, incomplete=False):
    """
    This finds any file metadata+content blocks up to the end of the string or end of file block
    """
    if incomplete:
        regex = rf'{FILE_METADATA_START}\n?(Path: .*?){FILE_METADATA_END}\n?(.*)(?:{END_OF_FILE})?'
    else:
        regex = rf'{FILE_METADATA_START}\n?(Path: .*?){FILE_METADATA_END}\n?(.*?){END_OF_FILE}'

    file_matches = re.finditer(regex, content, flags=re.DOTALL)

    all_file_parts = []
    for match in file_matches:
        metadata_str = match.group(1)
        content = match.group(2)

        metadata = parse_metadata(metadata_str)

        all_file_parts.append({
            'path': metadata.get('Path'),
            'version': metadata.get('Version', 1),
            'content': re.sub(r'\n$', '', content), # Remove trailing newline before the end of file metadata (b/c it's in regex)
            'language': metadata.get('Language'),
            'part': metadata.get('Part'),
            'no_more_parts': metadata.get('NoMoreParts')
        })

    all_files = {}

    for part_data in all_file_parts:
        file_key = (part_data['path'], part_data['version'])
        if file_key not in all_files:
            all_files[file_key] = []
        all_files[file_key].append(part_data)
        all_files[file_key].sort(key=lambda x: x['part'])

    result = []

    for _key_tuple, parts_array in all_files.items():
        # TODO: be robust and just ignore the nomoreparts content?
        joined_content = ''.join([part['content'] for part in parts_array]) + '\n'  # Join all parts together with a newline at the end
        final_part = parts_array[0] # The first part (0) will have no_more_parts set to True if it exists
        result.append([
            final_part['path'],
            final_part['version'],
            joined_content,
            final_part['language'],
            final_part['part'],
            final_part['no_more_parts']
        ])

    return result

def find_snippets(content):
    snippet_matches = re.finditer(match_snippet(), content, flags=re.DOTALL)
    return [(match.group(1), match.group(2)) for match in snippet_matches]

def is_file(content):
    return str(content).strip().startswith(FILE_METADATA_START)

def is_snippet(content):
    return str(content).strip().startswith(SNIPPET_METADATA_START)

def is_terminal_log(content):
    return str(content).strip().startswith(TERMINAL_METADATA_START)

def match_code_block():
    file_regex = rf'{FILE_METADATA_START}.*?{FILE_METADATA_END}.*?{END_OF_FILE}'
    snippet_regex = rf'{SNIPPET_METADATA_START}.*?{SNIPPET_METADATA_END}.*?{END_OF_SNIPPET}'
    return rf'({file_regex}|{snippet_regex})'

def match_file(file_path, incomplete=False):
    escaped = re.escape(file_path)

    if incomplete:
        return rf'\n?{FILE_METADATA_START}\nPath: {escaped}\n.*?{FILE_METADATA_END}\n?(.*)(?:{END_OF_FILE})?\n?'

    return rf'\n?{FILE_METADATA_START}\nPath: {escaped}\n.*?{FILE_METADATA_END}\n?(.*?){END_OF_FILE}\n?'

def match_file_with_version(file_path, version):
    escaped = re.escape(file_path)
    version = str(version)

    return rf'\n?{FILE_METADATA_START}\nPath: {escaped}\n.*?Version: {version}.*?{FILE_METADATA_END}\n?(.*?){END_OF_FILE}\n?'

def match_no_more_parts_file_with_version(file_path, version):
    escaped = re.escape(file_path)
    version = str(version)

    return rf'\n?{FILE_METADATA_START}\nPath: {escaped}\n.*?Version: {version}.*?NoMoreParts: True.*?{FILE_METADATA_END}\n?(.*?){END_OF_FILE}\n?'

def match_snippet():
    return rf'{SNIPPET_METADATA_START}.*?\nLanguage: (.*?)\n.*?{SNIPPET_METADATA_END}\n?(.*?){END_OF_SNIPPET}'

def match_metadata():
    return rf'({FILE_METADATA_START}.*?{FILE_METADATA_END}|{SNIPPET_METADATA_START}.*?{SNIPPET_METADATA_END}|{TERMINAL_METADATA_START}.*?{TERMINAL_METADATA_END})'

def file_block(file_path, content, language=None, version=1):
    language = get_language_from_extension(file_path) if not language else language
    part = 1
    return f"""
{FILE_METADATA_START}
Path: {file_path}
Language: {language}
Version: {version}
Part: {part}
{FILE_METADATA_END}
{content}
{END_OF_FILE}

{FILE_METADATA_START}
Path: {file_path}
Language: {language}
Version: {version}
NoMoreParts: True
{FILE_METADATA_END}
{END_OF_FILE}
"""

def snippet_block(content, language):
    return f"""
{SNIPPET_METADATA_START}
Language: {language}
{SNIPPET_METADATA_END}
{content}
{END_OF_SNIPPET}
"""

def terminal_log_block(content, title):
    return f"""
{TERMINAL_METADATA_START}
Name: {title}
{TERMINAL_METADATA_END}
{content}
{END_OF_TERMINAL_LOG}
"""

def get_language_from_extension(filename):
    try:
        _, ext = os.path.splitext(filename)
        if ext and ext != '.sh':
            lexer = get_lexer_for_filename(filename)
            lexer_name = lexer.name.lower()
            if lexer_name == 'text only':
                return "text"
            return lexer_name

        if not os.path.exists(filename):
            if ext == '.sh':
                return "sh"
            else:
                return "text"

        with open(filename, 'r', encoding='utf-8') as f:
            first_line = f.readline()

        program = get_program_from_shebang(first_line)

        if program:
            if "python" in program:
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
    program = program.split('/')[-1]  # Get the last part of the path

    if program == 'env':
        if len(parts) > 1:
            program = parts[1]
        else:
            return None

    return program.strip()
