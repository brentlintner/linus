import os
import re
import difflib
import pathspec
from .logger import debug
from .config import DEFAULT_IGNORE_PATTERNS
from .parser import find_files, file_block, get_language_from_extension, match_file

def format_number(num, magnitude):
    # TODO: Add more prefixes if needed (e.g., 'G' for billions)
    suffixes = ['', 'K', 'M', 'B', 'T']
    return f'{num:.1f}{suffixes[magnitude]}'

def load_ignore_patterns(extra_ignore_patterns=None):
    ignore_patterns = [] + DEFAULT_IGNORE_PATTERNS
    for ignore_file in ['.gitignore']:
        if os.path.exists(ignore_file):
            with open(ignore_file, encoding="utf-8") as f:
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
def generate_project_structure(extra_ignore_patterns=None):
    ignore_patterns = load_ignore_patterns(extra_ignore_patterns)
    spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)

    file_tree = [{
        "id": "$root",
        "name": os.path.basename(os.getcwd()),
        "parent": None,
        "type": "directory"
    }]

    for root, dirs, files in os.walk(os.getcwd()):
        relative_path = os.path.relpath(root, os.getcwd())
        relative_path = '' if relative_path == '.' else relative_path

        dirs[:] = [dir for dir in dirs if not spec.match_file(os.path.join(relative_path, dir))]
        files[:] = [file for file in files if not spec.match_file(os.path.join(relative_path, file))]

        for dir_path in dirs:
            dir_path = os.path.join(relative_path, dir_path)
            dir_parent = os.path.dirname(dir_path)

            file_tree.append({
                "id": dir_path,
                "name": os.path.basename(dir_path),
                "parent": dir_parent != '.' and dir_parent or "$root",
                "type": "directory"
            })

        for file in files:
            file_path = os.path.join(relative_path, file)
            file_parent = os.path.dirname(file_path)

            file_tree.append({
                "id": file_path,
                "name": os.path.basename(file),
                "parent": file_parent != '.' and file_parent or "$root",
                "type": "file"
            })

    file_tree = sorted(file_tree, key=lambda x: x['id'])

    return file_tree

def generate_project_file_contents(extra_ignore_patterns=None, include_patterns=[]):
    ignore_patterns = load_ignore_patterns(extra_ignore_patterns)
    ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)
    include_spec = pathspec.PathSpec.from_lines('gitwildmatch', include_patterns)
    include_all = "." in include_patterns
    output = ""

    for root, _, files in os.walk(os.getcwd()):
        relative_path = os.path.relpath(root, os.getcwd())
        if relative_path == '.':
            relative_path = ''

        # Output files and their contents
        for file in files:
            file_path = os.path.join(relative_path, file)
            is_ignored = ignore_spec.match_file(file_path) and not (include_patterns and include_spec.match_file(file_path))
            if not is_ignored:
                output += get_file_contents(file_path)

    return output

def generate_project_file_list(extra_ignore_patterns=None, include_patterns=[]):
    ignore_patterns = load_ignore_patterns(extra_ignore_patterns)
    ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)
    include_spec = pathspec.PathSpec.from_lines('gitwildmatch', include_patterns)
    include_all = "." in include_patterns
    output = []  # Use a list to store file names

    for root, _, files in os.walk(os.getcwd()):
        relative_path = os.path.relpath(root, os.getcwd())
        if relative_path == '.':
            relative_path = ''
        for file in files:
            file_path = os.path.join(relative_path, file)
            is_ignored = ignore_spec.match_file(file_path) and not (include_patterns and include_spec.match_file(file_path))
            if not is_ignored:
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

def prune_file_history(file_path, history, current_version):
    """Removes previous mentions of the given file from the history."""
    pruned_history = '\n'.join(history)

    files = find_files(pruned_history)

    # Find all files in the current history entry
    for existing_file_path, version, _, _, _, _ in files:
        # If the file paths match and the version is older, remove all file blocks (i.e. all parts)
        if existing_file_path == file_path and version < current_version:
            debug(f"Pruning file {file_path} (v{version}) from history")
            pruned_history = re.sub(match_file(existing_file_path), '', pruned_history, flags=re.DOTALL)

    history.clear()

    history.append(pruned_history)


def human_format_number(num):
    """Converts an integer to a human-readable string (e.g., 1.3M, 450K)."""
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return format_number(num, magnitude)
