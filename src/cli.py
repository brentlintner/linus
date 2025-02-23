import argparse
import os
import sys
import shutil
from .chat import coding_repl, debug_logging, verbose_logging, check_if_env_vars_set, list_available_models, history_filename_for_directory, generate_project_file_contents, generate_project_file_list
from .__version__ import __version__
from google import genai
from google.genai import types

def add_general_args(parser):
    group = parser.add_argument_group(title="General Options")
    # fmt: off
    group.add_argument("-m", "--models", action="store_true", help="List available generative AI models.")
    group.add_argument("-c", "--clean", action="store_true", help="Remove all history files in the tmp/ directory.")
    group.add_argument("-v", "--verbose", action="store_true", help="Log verbose output.")
    group.add_argument('--version', action='version', version=f'%(prog)s {__version__}', help="Show the version number and exit.")
    # fmt: on

def add_repl_args(parser):
    group = parser.add_argument_group(title="REPL Options")
    # fmt: off
    group.add_argument("-f", "--files", action="store_true", help="Include project files in the prompt.")
    group.add_argument("-i", "--interactive", action="store_true", help="Enable fuzzy file finding with @ symbol, and commands with the $ symbol.")
    group.add_argument("-w", "--writeable", action="store_true", help="Enable auto-writing to files from AI responses.")
    group.add_argument("-n", "--no-resume", action="store_true", help="Do not resume previous conversation. Start a new chat.")
    # fmt: on

def add_debug_args(parser):
    group = parser.add_argument_group(title="Debug Options")
    # fmt: off
    group.add_argument("-V", "--debug", action="store_true", help="Log debug output.")
    group.add_argument("-d", "--directory", type=str, default=os.getcwd(), help="Specify working directory.")
    # fmt: on

def add_file_listing_args(parser):
    group = parser.add_argument_group(title="File Listing Options")
    # fmt: off
    group.add_argument("-l", "--list-files", action="store_true", help="List all files that will be included if -f is set.")
    group.add_argument("-t", "--tokens", action="store_true", help="List all files, their token counts, and the total token count.")
    group.add_argument("-g", "--ignore", type=str, help="Comma-separated list of additional ignore patterns.")
    # fmt: on

def create_parser():
    parser = argparse.ArgumentParser(
        prog="ai-code",
        description="Pair program with a Gemini AI based assistant.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        add_help=True
    )

    add_repl_args(parser)
    add_file_listing_args(parser)
    add_general_args(parser)
    add_debug_args(parser)

    parser._optionals.title = "Help Options"

    return parser

def clean_history_files(tmp_dir='tmp'):
    """Remove all history files in the specified directory."""
    if os.path.exists(tmp_dir):
        try:
            shutil.rmtree(tmp_dir)
            os.makedirs(tmp_dir)
            print(f"Cleaned history files in {tmp_dir}/")
        except Exception as e:
            print(f"Error cleaning history files: {e}")

def handle_list_files(args):
    extra_ignore_patterns = args.ignore.split(',') if args.ignore else None
    files = generate_project_file_list(extra_ignore_patterns)
    print(files)

def handle_tokens(args):
    client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))

    extra_ignore_patterns = args.ignore.split(',') if args.ignore else None
    file_paths = generate_project_file_list(extra_ignore_patterns)
    total_tokens = 0
    for file_path in file_paths.splitlines():
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            tokens = client.models.count_tokens(model=os.getenv('GEMINI_MODEL') or '', contents=content).total_tokens
            total_tokens += tokens or 0
        except FileNotFoundError:
            print(f"{file_path}: NOT FOUND", file=sys.stderr)
        except Exception as e:
            print(f"Error with {file_path}: {e}", file=sys.stderr)

    print(f"Total tokens: {total_tokens}")

def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.debug:
        debug_logging()
    if args.verbose:
        verbose_logging()
    if args.clean:
        clean_history_files()
        sys.exit(0)

    check_if_env_vars_set()

    if args.models:
        list_available_models()
        sys.exit(0)

    os.chdir(args.directory)

    if args.list_files:
        handle_list_files(args)
        sys.exit(0)
    elif args.tokens:
        handle_tokens(args)
        sys.exit(0)

    resume = not args.no_resume

    coding_repl(
        resume=resume,
        interactive=args.interactive,
        writeable=args.writeable,
        ignore_patterns=args.ignore,
        include_files=args.files,
    )

if __name__ == "__main__":
    main()
