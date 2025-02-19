import argparse
import os
import sys
import shutil
from .chat import coding_repl, debug_logging, verbose_logging, print_history, check_if_env_vars_set, list_available_models

def create_parser():
    parser = argparse.ArgumentParser(
        prog="ai-chat",
        description="Chat with a Gemini AI based pair programming assistant.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # fmt: off
    parser.add_argument("-r", "--resume", nargs="?", const=True, default=False, help="Resume previous conversation.")
    parser.add_argument("-s", "--subject", nargs="+", help="Override subject; otherwise generate from first message.")
    parser.add_argument("-l", "--history", action="store_true", help="Show previous conversations.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Log verbose output.")
    parser.add_argument("-V", "--debug", action="store_true", help="Log debug output.")
    parser.add_argument("-i", "--interactive", action="store_true", help="Enable fuzzy file finding with @ symbol.")
    parser.add_argument("-w", "--writeable", action="store_true", help="Enable auto-writing to files from AI responses.")
    parser.add_argument("-d", "--directory", type=str, default=os.getcwd(), help="Specify working directory.")
    parser.add_argument("-g", "--ignore", type=str, help="Comma-separated list of additional ignore patterns.")
    parser.add_argument("-c", "--clean", action="store_true", help="Remove all history files in the tmp/ directory.")
    parser.add_argument("-m", "--models", action="store_true", help="List available generative AI models.")
    # fmt: on

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
    else:
        print(f"{tmp_dir}/ directory does not exist.")

def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.debug:
        debug_logging()
    if args.verbose:
        verbose_logging()
    if args.history:
        print_history()
        sys.exit(0)
    if args.clean:
        clean_history_files()

    check_if_env_vars_set()

    if args.models:
        list_available_models()
        sys.exit(0)

    os.chdir(args.directory)

    coding_repl(
        resume=args.resume,
        subject=args.subject,
        interactive=args.interactive,
        writeable=args.writeable,
        ignore_patterns=args.ignore,
    )

if __name__ == "__main__":
    main()