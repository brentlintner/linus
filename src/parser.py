import os
import re
import shlex
from pygments.util import ClassNotFound
from pygments.lexers import get_lexer_for_filename

# NOTE: We must use this way to generate the placeholder wrapper so this parsing doesn't fail for this file when using this project on itself
def uid(placeholder):
    return r'{{{' + placeholder + r'}}}'

FILE_METADATA_START =       uid('START FILE METADATA')
FILE_METADATA_END =         uid('END FILE METADATA')
SNIPPET_METADATA_START =    uid('START CODE SNIPPET METADATA')
SNIPPET_METADATA_END =      uid('END CODE SNIPPET METADATA')
TERMINAL_METADATA_START =   uid('START TERMINAL METADATA')
TERMINAL_METADATA_END =     uid('END TERMINAL METADATA')
END_OF_FILE =               uid('END OF FILE')
FILE_TREE_PLACEHOLDER =     uid('FILE_TREE_JSON')
FILES_PLACEHOLDER =         uid('FILE_REFERENCES')
FILES_START_SEP =           uid('FILE_REFERENCES START')
FILES_END_SEP =             uid('FILE_REFERENCES END')
CONVERSATION_START_SEP =    uid('CONVERSATION_HISTORY START')
CONVERSATION_END_SEP =      uid('CONVERSATION_HISTORY END')
TERMINAL_LOGS_PLACEHOLDER = uid('TERMINAL_LOGS')

def find_file_references(content):
    file_references = re.findall(r'@(\S+)', content)

    return [re.sub(r"[^\w\s]+$", '', file_reference) for file_reference in file_references]

def find_files(content):
    regex = rf'{FILE_METADATA_START}.*?\nPath: (.*?)\n(?:Chunk: (\d+/\d+)\n)?Language: (.*?)\n{FILE_METADATA_END}(.*?){END_OF_FILE}'
    file_matches = re.finditer(regex, content, flags=re.DOTALL)
    return [(match.group(1), match.group(4), match.group(3), match.group(2)) for match in file_matches] # (path, content, language, chunk)

def find_snippets(content):
    regex = rf'{SNIPPET_METADATA_START}.*?\nLanguage: (.*?)\n{SNIPPET_METADATA_END}(.*?){END_OF_FILE}'
    snippet_matches = re.finditer(regex, content, flags=re.DOTALL)
    return [(match.group(1), match.group(2)) for match in snippet_matches]

def is_file(content):
    return str(content).startswith(FILE_METADATA_START)

def is_snippet(content):
    return str(content).startswith(SNIPPET_METADATA_START)

def is_terminal_log(content):
    return str(content).startswith(TERMINAL_METADATA_START)

def match_code_block():
    file_regex = rf'{FILE_METADATA_START}.*?{FILE_METADATA_END}.*?{END_OF_FILE}'
    snippet_regex = rf'{SNIPPET_METADATA_START}.*?{SNIPPET_METADATA_END}.*?{END_OF_FILE}'
    return rf'({file_regex}|{snippet_regex})'

def match_file(file_path):
    escaped = re.escape(file_path)
    return rf'{FILE_METADATA_START}.*?\nPath: {escaped}\n.*?{FILE_METADATA_END}(.*?){END_OF_FILE}'

def match_snippet():
    return rf'{SNIPPET_METADATA_START}.*?\nLanguage: (.*?)\n{SNIPPET_METADATA_END}(.*?){END_OF_FILE}'

def match_before_conversation_history():
    return rf'^(.*?){CONVERSATION_START_SEP}'

def file_block(file_path, content, language=None, chunk=None):
    language = get_language_from_extension(file_path) if not language else language
    chunk_str = f"Chunk: {chunk}\n" if chunk else ""
    return f"""
{FILE_METADATA_START}
Path: {file_path}
{chunk_str}Language: {language}
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
            return "text" # Fallback
    except ClassNotFound:
        return "text"
    except FileNotFoundError:
        return "text"

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
