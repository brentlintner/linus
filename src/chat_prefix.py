# HACK: We only define these patterns here, in a small file, to avoid this program breaking
#       regex and ballooning history if run on its own source code.
#
#       If you change this file name, change the hardcoded file name in the rest of the code.
#
FILE_PREFIX = '```file: '
SNIPPET_PREFIX = '```snippet: '

FILE_TREE_PLACEHOLDER = '{{{FILE_TREE_JSON}}}'
FILES_PLACEHOLDER = '{{{FILE_REFERENCES}}}'

FILES_START_SEP = '{{{FILE_REFERENCES START}}}'
FILES_END_SEP = '{{{FILE_REFERENCES END}}}'

CONVERSATION_START_SEP = '{{{CONVERSATION_HISTORY START}}}'
CONVERSATION_END_SEP = '{{{CONVERSATION_HISTORY END}}}'

TERMINAL_LOGS_PLACEHOLDER = '{{{TERMINAL_LOGS}}}'
