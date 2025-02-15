import argparse
import os
import sys
from .chat import coding_repl, verbose_logging, print_history, check_if_env_vars_set

def cli_parser():
    parser = argparse.ArgumentParser(
        prog="ai-chat", add_help=False,
        description="Chat with a Gemini AI based pair programming assistant.")

    parser.add_argument(
        "--resume", "-r", nargs="?", const=True, default=False,
        help="Resume a previous conversation. Will use last created session if no argument is provided.")

    parser.add_argument(
        "--subject", "-s", nargs="+",
        help="Overrides the subject instead of generating one from the first message")

    parser.add_argument(
        "--help", "-h", action="store_true",
        help="Print this help message")

    parser.add_argument(
        "--history", "-l", action="store_true",
        help="Show a list of previous conversations")

    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Log verbose output")

    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Enable the ability to fuzzy find and reference files for the AI to read using the @ symbol")

    parser.add_argument(
        "--writeable", "-w", action="store_true",
        help="Enable the ability to automatically write to files based on the AI's responses")

    parser.add_argument('--directory', '-d', type=str, help='Specify cwd for file reference completion')

    return parser

def cli():
    parser = cli_parser()
    args = parser.parse_args()

    if args.verbose:
        verbose_logging()

    if args.history:
        print_history()
        sys.exit(0)

    if args.help:
        parser.print_help()
        sys.exit(0)

    check_if_env_vars_set()

    if args.directory:
        os.chdir(args.directory)

    coding_repl(resume=args.resume, subject=args.subject, interactive=args.interactive, writeable=args.writeable)

if __name__ == "__main__":
    cli()