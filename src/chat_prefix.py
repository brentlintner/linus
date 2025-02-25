# HACK: We only define these patterns here, in a small file, to avoid this program breaking
#       regex and ballooning history if run on its own source code.
#
#       If you change this file name, change the hardcoded file name in the rest of the code.
#

FILE_METADATA_START = '{{{START FILE METADATA}}}'
FILE_METADATA_END = '{{{END FILE METADATA}}}'

SNIPPET_METADATA_START = '{{{START CODE SNIPPET METADATA}}}'
SNIPPET_METADATA_END = '{{{END CODE SNIPPET METADATA}}}'

END_OF_FILE = '{{{END OF FILE}}}'

FILE_TREE_PLACEHOLDER = '{{{FILE_TREE_JSON}}}'
FILES_PLACEHOLDER = '{{{FILE_REFERENCES}}}'

FILES_START_SEP = '{{{FILE_REFERENCES START}}}'
FILES_END_SEP = '{{{FILE_REFERENCES END}}}'

CONVERSATION_START_SEP = '{{{CONVERSATION_HISTORY START}}}'
CONVERSATION_END_SEP = '{{{CONVERSATION_HISTORY END}}}'

TERMINAL_LOGS_PLACEHOLDER = '{{{TERMINAL_LOGS}}}'

def file_block(file_path, file_contents, language):
    return f"""
{FILE_METADATA_START}"
Path: {file_path}
Language: {language}
{FILE_METADATA_END}
{file_contents}
{END_OF_FILE}
"""

def snippet_block(language, contents):
    return f"""
{SNIPPET_METADATA_START}"
Language: {language}
{SNIPPET_METADATA_END}
{contents}
{END_OF_FILE}
"""
