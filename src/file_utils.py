import os
import re
import difflib
import pathspec

from .config import DEFAULT_IGNORE_PATTERNS
from .parser import file_block, get_language_from_extension, match_file

def load_ignore_patterns(extra_ignore_patterns=None, include_patterns=None):
    if include_patterns:
        # If include_patterns are specified, ONLY use those.
        return [] + include_patterns

    ignore_patterns = [] + DEFAULT_IGNORE_PATTERNS
    for ignore_file in ['.gitignore']:
        if os.path.exists(ignore_file):
            with open(ignore_file) as f:
                ignore_patterns.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])
    if extra_ignore_patterns:
        ignore_patterns.extend(extra_ignore_patterns)
    return ignore_patterns

def is_ignored(path, spec):
    return spec.match_file(path)

def generate_diff(file_path, current_content):
    try:
        with open(file_path, 'r') as f:
            file_content = f.readlines()
    except FileNotFoundError:
        return current_content  # If file not found, return current content

    diff = difflib.unified_diff(
        file_content,
        current_content.splitlines(keepends=True),
        fromfile=f"{file_path} (disk)",
        tofile=f"{file_path} (context)",
    )

    stringifed_diff = ''.join(diff)

    if len(stringifed_diff) == 0:
        # If no diff (i.e. we are re-adding the same file), return full (i.e. current) content
        return current_content

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

        dirs[:] = [dir for dir in dirs if not is_ignored(os.path.join(relative_path, dir), spec)]
        files[:] = [file for file in files if not is_ignored(os.path.join(relative_path, file), spec)]

        for dir in dirs:
            dir_path = os.path.join(relative_path, dir)
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

def generate_project_file_contents(extra_ignore_patterns=None, include_patterns=None):
    ignore_patterns = load_ignore_patterns(extra_ignore_patterns, include_patterns)
    spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)
    output = ""

    for root, _, files in os.walk(os.getcwd()):
        relative_path = os.path.relpath(root, os.getcwd())
        if relative_path == '.':
            relative_path = ''

        # Output files and their contents
        for file in files:
            file_path = os.path.join(relative_path, file)
            if include_patterns:
                if spec.match_file(file_path):
                    output += get_file_contents(file_path)
            elif not is_ignored(file_path, spec):
                output += get_file_contents(file_path)

    return output

def generate_project_file_list(extra_ignore_patterns=None, include_patterns=None):
    ignore_patterns = load_ignore_patterns(extra_ignore_patterns, include_patterns)
    spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)
    output = []  # Use a list to store file names

    for root, _, files in os.walk(os.getcwd()):
        relative_path = os.path.relpath(root, os.getcwd())
        if relative_path == '.':
            relative_path = ''
        for file in files:
            file_path = os.path.join(relative_path, file)
            if include_patterns:
                if spec.match_file(file_path):
                    output.append(file_path)
            elif not is_ignored(file_path, spec):
                output.append(file_path)  # Append file path to the list

    return "\n".join(output)  # Join with newlines

def get_file_contents(file_path, version=1):
    try:
        with open(file_path, 'r') as f:
            contents = f.read()
        block = file_block(file_path, contents, get_language_from_extension(file_path), version=version)
        return f"{block}\n"
    except Exception as e:
        # TODO: use logging here not return
        return f"    Error reading {file_path}: {e}\n"

def prune_file_history(file_path, history):
    """Removes previous mentions of the given file from the history."""
    for index, entry in enumerate(history):
        if re.match(match_file(file_path), entry):
            history[index] = re.sub(match_file(file_path), '', entry, flags=re.DOTALL)

def human_format_number(num):
    """Converts an integer to a human-readable string (e.g., 1.3M, 450K)."""
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    # Add more prefixes if needed (e.g., 'G' for billions)
    return '%.1f%s' % (num, ['', 'K', 'M', 'B', 'T'][magnitude])