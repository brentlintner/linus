# HACK: We only define these patterns here, in a small file, to avoid this program breaking
#       regex and ballooning history if run on its own source code.
#
#       If you change this file name, change the hardcoded file name in the rest of the code.

import os
import re
import shlex
from pygments.util import ClassNotFound
from pygments.lexers import get_lexer_for_filename

FILE_METADATA_START = '{{{START FILE METADATA}}}'
FILE_METADATA_END =   '{{{END FILE METADATA}}}'

SNIPPET_METADATA_START = '{{{START CODE SNIPPET METADATA}}}'
SNIPPET_METADATA_END =   '{{{END CODE SNIPPET METADATA}}}'

TERMINAL_METADATA_START = '{{{START TERMINAL METADATA}}}'
TERMINAL_METADATA_END =   '{{{END TERMINAL METADATA}}}'

END_OF_FILE = '{{{END OF FILE}}}'

FILE_TREE_PLACEHOLDER = '{{{FILE_TREE_JSON}}}'
FILES_PLACEHOLDER =     '{{{FILE_REFERENCES}}}'

FILES_START_SEP = '{{{FILE_REFERENCES START}}}'
FILES_END_SEP =   '{{{FILE_REFERENCES END}}}'

CONVERSATION_START_SEP = '{{{CONVERSATION_HISTORY START}}}'
CONVERSATION_END_SEP =   '{{{CONVERSATION_HISTORY END}}}'

TERMINAL_LOGS_PLACEHOLDER = '{{{TERMINAL_LOGS}}}'

MATCH_FILE_DATA = rf'{FILE_METADATA_END}\n?(.*?){END_OF_FILE}'

def find_file_references(content):
    file_references = re.findall(r'@(\S+)', content)

    return [re.sub(r"[^\w\s]+$", '', file_reference) for file_reference in file_references]

def find_files(content):
    regex = rf'{FILE_METADATA_START}.*?\nPath: (.*?)\n.*?{FILE_METADATA_END}(.*?){END_OF_FILE}'
    file_matches = re.finditer(regex, content, flags=re.DOTALL)
    return [(match.group(1), match.group(2)) for match in file_matches]

def find_snippets(content):
    regex = rf'{SNIPPET_METADATA_START}.*?\nLanguage: (.*?)\n{SNIPPET_METADATA_END}(.*?){END_OF_FILE}'
    snippet_matches = re.finditer(regex, content, flags=re.DOTALL)
    return [(match.group(1), match.group(2)) for match in snippet_matches]

def has_starting_block(content):
    return(is_file(content) or
           is_snippet(content) or
           is_terminal_log(content))

def is_file(content):
    return content.startswith(FILE_METADATA_START)

def is_snippet(content):
    return content.startswith(SNIPPET_METADATA_START)

def is_terminal_log(content):
    return content.startswith(TERMINAL_METADATA_START)

def match_any_block():
    starts = '|'.join([FILE_METADATA_START, SNIPPET_METADATA_START, TERMINAL_METADATA_START])
    ends = '|'.join([FILE_METADATA_END, SNIPPET_METADATA_END, TERMINAL_METADATA_END])

    return rf'({starts})(.*?)({ends})(.*?){END_OF_FILE}'

def match_file(file_path):
    escaped = re.escape(file_path)
    return rf'{FILE_METADATA_START}.*?\nPath: {escaped}\n.*?{FILE_METADATA_END}(.*?){END_OF_FILE}'

def match_snippet():
    return rf'{SNIPPET_METADATA_START}.*?\nLanguage: (.*?)\n{SNIPPET_METADATA_END}(.*?){END_OF_FILE}'

def match_before_conersation_history():
    return rf'^(.*?){CONVERSATION_START_SEP}'

def file_block(file_path, content, language):
    return f"""
{FILE_METADATA_START}"
Path: {file_path}
Language: {language}
{FILE_METADATA_END}
{content}
{END_OF_FILE}
"""

def snippet_block(content, language):
    return f"""
{SNIPPET_METADATA_START}"
Language: {language}
{SNIPPET_METADATA_END}
{content}
{END_OF_FILE}
"""

def terminal_log_block(content, title):
    return f"""
{TERMINAL_METADATA_START}"
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
