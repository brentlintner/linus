import argparse
import os
import sys
import shutil
from rich.traceback import install
from google import genai
from .__version__ import __version__
from .file_utils import generate_project_file_list
from .logger import debug_logging, verbose_logging, quiet_logging
from .chat import coding_repl, check_if_env_vars_set, list_available_models, history_filename_for_directory

install(show_locals=True)

def add_general_args(parser):
    group = parser.add_argument_group(title="General Options")
    # fmt: off
    group.add_argument("-m", "--models", action="store_true", help="List available generative AI models.")
    group.add_argument("-c", "--clean", action="store_true", help="Clean history file for the current project (cwd).")
    group.add_argument("-v", "--verbose", action="store_true", help="Log verbose output.")
    group.add_argument("-q", "--quiet", action="store_true", help="Only print responses, in plain text")
    group.add_argument('--version', action='version', version=f'%(prog)s {__version__}', help="Show the version number and exit.")
    # fmt: on

def add_repl_args(parser):
    group = parser.add_argument_group(title="REPL Options")
    # fmt: off
    group.add_argument("-f", "--files", type=str, help="Comma-separated list of patterns to include.")
    group.add_argument("-i", "--ignore", type=str, help="Comma-separated list of additional ignore patterns.")
    group.add_argument("-w", "--writeable", action="store_true", help="Enable auto-writing to files from AI responses.")
    group.add_argument("-n", "--no-resume", action="store_true", help="Do not resume previous conversation. Start a new chat.")
    # fmt: on

def add_debug_args(parser):
    group = parser.add_argument_group(title="Debug Options")
    # fmt: off
    group.add_argument("-V", "--debug", action="store_true", help="Log debug output.")
    group.add_argument("-d", "--directory", type=str, help="Specify working directory (used internally, see bin/ai entry point).")
    # fmt: on

def add_file_listing_args(parser):
    group = parser.add_argument_group(title="File Listing Options")
    # fmt: off
    group.add_argument("-l", "--list-files", action="store_true", help="List all files that will be included if -f is set.")
    group.add_argument("-t", "--tokens", action="store_true", help="List all files, their token counts, and the total token count.")
    # fmt: on

def create_parser():
    parser = argparse.ArgumentParser(
        prog="ai-code",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        add_help=True
    )

    add_repl_args(parser)
    add_file_listing_args(parser)
    add_general_args(parser)
    add_debug_args(parser)

    parser._optionals.title = "Help Options"

    return parser

def clean_history_files(cwd=os.getcwd()):
    history_file = history_filename_for_directory(cwd)
    if os.path.exists(history_file):
        try:
            os.remove(history_file)
            print(f"Cleaned history file: {history_file}")
        except Exception as e:
            print(f"Error cleaning history file: {e}")
    else:
        print("No history file found for the current directory.")

def handle_list_files(args):
    directory = args.directory
    extra_ignore_patterns = args.ignore.split(',') if args.ignore else None
    include_patterns = args.files.split(',') if args.files else None
    files = generate_project_file_list(extra_ignore_patterns, include_patterns, directory)
    print(files)

def handle_tokens(args):
    directory = args.directory
    client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))

    extra_ignore_patterns = args.ignore.split(',') if args.ignore else []
    include_patterns = args.files.split(',') if args.files else []
    file_paths = generate_project_file_list(extra_ignore_patterns, include_patterns, directory)
    total_tokens = 0
    for file_path in file_paths.splitlines():
        try:
            with open(os.path.join(directory, file_path), 'r', encoding='utf-8') as f:
                content = f.read()
            tokens = client.models.count_tokens(model=os.getenv('GEMINI_MODEL') or '', contents=content).total_tokens
            total_tokens += tokens or 0
        except FileNotFoundError:
            print(f"{file_path}: NOT FOUND", file=sys.stderr)
        except Exception as e:
            print(f"Error with {file_path}: {e}", file=sys.stderr)

    print(f"Total tokens: {total_tokens}")

def configure_logger(args):
    if args.debug:
        debug_logging()
    if args.verbose:
        verbose_logging()
    if args.quiet:
        quiet_logging()

def main():
    parser = create_parser()
    args = parser.parse_args()

    configure_logger(args)

    if args.clean:
        clean_history_files(args.directory)
        sys.exit(0)

    check_if_env_vars_set()

    if args.models:
        list_available_models()
        sys.exit(0)

    # Correctly handle the --files argument
    if args.files == ".":
        include_files = ["."]  # Special case for current directory
    elif args.files:
        include_files = args.files.split(',')
    else:
        include_files = None  # No files specified

    if args.list_files:
        if args.files:
            handle_list_files(args)
        sys.exit(0)
    elif args.tokens:
        if args.files:
            handle_tokens(args)
        sys.exit(0)

    if args.directory:
        os.chdir(args.directory)

    resume = not args.no_resume

    coding_repl(
        resume=resume,
        writeable=args.writeable,
        ignore_patterns=args.ignore,
        include_patterns=include_files,
        cwd=args.directory
    )

if __name__ == "__main__":
    main()
