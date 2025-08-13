import os
import difflib
import pathspec
from .logger import debug
from .config import DEFAULT_IGNORE_PATTERNS
from .parser import (
    file_block,
    get_language_from_extension,
)

def format_number(num, magnitude):
    # TODO: Add more prefixes if needed (e.g., 'G' for billions)
    suffixes = ['', 'K', 'M', 'B', 'T']
    return f'{num:.1f}{suffixes[magnitude]}'

def load_ignore_patterns(extra_ignore_patterns=None, directory=os.getcwd()):
    ignore_patterns = [] + DEFAULT_IGNORE_PATTERNS
    for ignore_file in ['.gitignore', '.linignore']:
        file_path = os.path.join(directory, ignore_file)
        if os.path.exists(file_path):
            with open(file_path, encoding="utf-8") as f:
                ignore_patterns.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])
    if extra_ignore_patterns:
        ignore_patterns.extend(extra_ignore_patterns)
    return ignore_patterns

def generate_diff(file_path, current_content):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.readlines()
    except FileNotFoundError:
        return current_content

    diff = difflib.unified_diff(
        file_content,
        current_content.splitlines(keepends=True),
        fromfile=f"{file_path} (disk)",
        tofile=f"{file_path} (context)",
        n=5
    )

    stringifed_diff = ''.join(diff)

    return stringifed_diff

# NOTE: we don't use the args.files here, because we want to include all non-default ignored files
def generate_project_structure(extra_ignore_patterns=None, include_patterns=None, directory=None):
    if include_patterns is None:
        include_patterns = []
    directory = directory or os.getcwd()  # Use provided directory or default to current.
    ignore_patterns = load_ignore_patterns(extra_ignore_patterns, directory)
    ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)
    include_spec = pathspec.PathSpec.from_lines('gitwildmatch', include_patterns)
    allow_all = "." in include_patterns

    file_tree = [{
        "id": "$root",
        "name": os.path.basename(directory),
        "parent": None,
        "type": "directory"
    }]

    for root, dirs, files in os.walk(directory, topdown=True):
        relative_path = os.path.relpath(root, directory)
        if relative_path == '.':
            relative_path = ''

        # Filter out ignored directories (for walking, not for the list)
        dirs[:] = [d for d in dirs if not ignore_spec.match_file(os.path.join(relative_path, d))]

        # TODO: be better, i.e. add the directory to the tree even if empty or match fails (because it's for a file vs a dir)
        for dir_path in dirs:
            dir_path = os.path.join(relative_path, dir_path)
            dir_parent = os.path.dirname(dir_path)
            allowed = not ignore_spec.match_file(dir_path) and (allow_all or include_spec.match_file(dir_path))

            if allowed:
                debug(f"Project structure (add): {dir_path}")
                file_tree.append({
                    "id": dir_path,
                    "name": os.path.basename(dir_path),
                    "parent": dir_parent != '.' and dir_parent or "$root",
                    "type": "directory"
                })

        for file in files:
            file_path = os.path.join(relative_path, file)
            file_parent = os.path.dirname(file_path)
            allowed = not ignore_spec.match_file(file_path) and (allow_all or include_spec.match_file(file_path))
            if allowed:
                debug(f"Project structure (add): {file_path}")
                file_tree.append({
                    "id": file_path,
                    "name": os.path.basename(file),
                    "parent": file_parent != '.' and file_parent or "$root",
                    "type": "file"
                })

    file_tree = sorted(file_tree, key=lambda x: x['id'])

    return file_tree

def generate_project_file_contents(extra_ignore_patterns=None, include_patterns=None, directory=None):
    if include_patterns is None:
        include_patterns = []
    files = generate_project_file_list(extra_ignore_patterns, include_patterns, directory)
    output = ""

    # TODO: make an array
    for file_path in files.splitlines():
        debug(f"File contents (add): {file_path}")
        # NOTE: we always user version 1 here, since any newer versions will be in conversation history
        output += get_file_contents(file_path)

    return output

def generate_project_file_list(extra_ignore_patterns=None, include_patterns=None, directory=None):
    if include_patterns is None:
        include_patterns = []
    directory = directory or os.getcwd()  # Use provided directory or default to current.
    ignore_patterns = load_ignore_patterns(extra_ignore_patterns, directory)
    ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)
    include_spec = pathspec.PathSpec.from_lines('gitwildmatch', include_patterns)
    allow_all = "." in include_patterns
    output = []  # Use a list to store file names

    for root, dirs, files in os.walk(directory, topdown=True):
        relative_path = os.path.relpath(root, directory)
        if relative_path == '.':
            relative_path = ''

        # Filter out ignored directories
        dirs[:] = [d for d in dirs if not ignore_spec.match_file(os.path.join(relative_path, d))]

        for file in files:
            file_path = os.path.join(relative_path, file)
            allowed = not ignore_spec.match_file(file_path) and (allow_all or include_spec.match_file(file_path))
            if allowed:
                output.append(file_path)

    return "\n".join(output)  # Join with newlines

def get_file_contents(file_path, version=1):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            contents = f.read()
        block = file_block(file_path, contents, get_language_from_extension(file_path), version)
        return f"{block}\n"
    except Exception as e:
        # TODO: use logging here not return
        return f"    Error reading {file_path}: {e}\n"

def human_format_number(num):
    """Converts an integer to a human-readable string (e.g., 1.3M, 450K)."""
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return format_number(num, magnitude)
