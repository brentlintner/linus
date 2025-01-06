import google.generativeai as ai
import os
import sys
import threading
import time
import re
import uuid
import argparse
import prompt_toolkit
from datetime import datetime, timezone
from collections import deque
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter
from dotenv import load_dotenv
from google.generativeai import caching

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL')

history = []

verbose = False

loading = False

def verbose_logging():
    global verbose
    verbose = True

def info(message):
    if verbose:
        print(message)

def error(message):
    print(message)

def tail(filename, n=10):
    try:
        with open(filename) as f:
            return deque(f, n)
    except FileNotFoundError:
        return None

def type_response_out(lines, delay=0):
    for string in lines:
        for char in string:
            sys.stdout.write(char)
            sys.stdout.flush()  # Force character output. Important!

            time.sleep(delay)
        print()  # Newline after each string

def prompt_prefix():
    prompt_prefix_file = os.path.join(os.path.dirname(__file__), '../docs/background.txt')
    with open(prompt_prefix_file, 'r') as f:
        return f.read()

def check_if_env_vars_set():
    if not GEMINI_API_KEY:
        error("Please set the GEMINI_API_KEY environment variable.")
        sys.exit(1)

    if not GEMINI_MODEL:
        error("Please set the GEMINI_MODEL environment variable (ex: GEMINI_MODEL=gemini-1.5-pro")
        sys.exit(1)

def generate_timestamped_uuid():
    uuid_val = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")  # ISO 8601 format in UTC
    return f"{timestamp}-{uuid_val}"

def extract_timestamp(filename):
    match = re.search(r"(\d{8}T\d{6}\.\d{6}Z)", filename)
    if match:
        timestamp_str = match.group(1)
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S.%fZ")
            return timestamp
        except ValueError:
            error(f"Invalid timestamp format: {timestamp_str}")
            return None
    else:
        error("Timestamp not found in filename")
        return None


def previous_history(resume_from=None):
    if resume_from and resume_from is not True:
        timestamp = extract_timestamp(resume_from)
        if timestamp:
            return (os.path.basename(resume_from), timestamp)
        else:
            error("Invalid history file")
            return None

    return last_session()

def last_session():
    directory = os.path.join(os.path.dirname(__file__), '../tmp')
    files_with_timestamps = []
    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            timestamp = extract_timestamp(filename)
            if timestamp:  # Only add files with valid timestamps
                files_with_timestamps.append((filename, timestamp))

    # Sort the files by timestamp in descending order
    files_with_timestamps.sort(key=lambda item: item[1], reverse=True)

    latest_file = files_with_timestamps[0] if files_with_timestamps else None

    return latest_file if latest_file else None


def print_history():
    directory = os.path.join(os.path.dirname(__file__), '../tmp')

    files_with_timestamps = []

    for filename in os.listdir(directory):
        if filename.endswith(".txt"):
            timestamp = extract_timestamp(filename)
            if timestamp:
                files_with_timestamps.append((filename, timestamp))

    files_with_timestamps.sort(key=lambda item: item[1], reverse=True)

    for filename, timestamp in files_with_timestamps:
        print(f"{timestamp} - {filename}")

def loading_indicator():
    while True:
        for char in '|/-\\':
            print(f'\r{char}', end='', flush=True)

            time.sleep(0.1)
            if not loading:
                print('\r ', end='', flush=True)
                return

def cli_parser():
    parser = argparse.ArgumentParser(
        prog="ai-chat", add_help=False,
        description="Chat with a Gemini AI based pair programming assistant")

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

    return parser


def coding_repl(resume=False, subject=None):
    os.mkdir('tmp') if not os.path.exists('tmp') else None

    ai.configure(api_key=GEMINI_API_KEY)

    model = ai.GenerativeModel('models/' + GEMINI_MODEL)

    previous_session = previous_history(resume) if resume else None

    if previous_session:
        info(f"Resuming session: {previous_session[0]}") if previous_session else None
        session_file = os.path.join(os.path.dirname(__file__), f"../tmp/{previous_session[0]}")
        recap = tail(session_file, 100)
        sanitized_recap = re.sub(r'.*Past conversation:', '', ''.join(recap), flags=re.DOTALL).strip()
        sanitized_recap_again = re.sub(r'\n*(Linus:\s|Brent:\s)', r'\n\n\1\n\n', sanitized_recap)
        print(re.sub(r'^\n*([^\n])', r'\1', re.sub(r'([^\d][\.\!\?\)\*])\s\s', r'\1\n\n', sanitized_recap_again), flags=re.DOTALL))
        print()
        with open(session_file, 'r') as f:
            for line in f.readlines():
                history.append(line)
    else:
        info("No previous session found. Starting a new session.") if resume else None
        history.append(prompt_prefix())

    first_message = False if resume else True
    history_filename = None
    if resume and previous_session:
        history_filename = os.path.join(os.path.dirname(__file__), f"../tmp/{previous_session[0]}")

    session = prompt_toolkit.PromptSession()

    while True:
        try:
            prompt_text = session.prompt("> ", multiline=True, mouse_support=True)
            if prompt_text == 'exit':
                break

            global loading
            loading = True
            loading_thread = threading.Thread(target=loading_indicator, daemon=True)
            loading_thread.start()

            history.append('\nBrent: \n\n' + prompt_text + '\n')
            response = model.generate_content(''.join(history))
            history.append('\nLinus: \n\n' + response.text + '\n')

            if first_message and not history_filename:
                if subject:
                    chat_subject = '_'.join(subject)
                    print(f"Using subject: {chat_subject}")
                else:
                    chat_subject_response = model.generate_content(
                        'Summarize the following piece of text in a file name compatible string:\n\n' + prompt_text)
                    chat_subject = chat_subject_response.text.strip()

                history_filename = os.path.join(
                    os.path.dirname(__file__), f"../tmp/linus-{chat_subject}-{generate_timestamped_uuid()}.txt")

                first_message = False

            if history_filename:
                with open(history_filename, 'w') as f:
                    f.write(''.join(history))

            sanitized_response = re.sub(r'([^\d][\.\!\?\)\*])\s\s', r'\1\n\n', response.text)

            loading = False  # This makes the loading indicator stop
            loading_thread.join()

            print()
            type_response_out(sanitized_response.split('\n'))

            # TODO: if a code snippet log all at once
            # TODO: go through each file and insert pretty printed version?
            # Check if the response contains a code snippet
            # if "// [START code_snippet:" in response.text:
                # Extract the code snippet
                # code_snippet = response.text.split("// [START code_snippet:")[1].split("// [END code_snippet:")[0]

                # Pretty print and highlight the code
                # print(highlight(code_snippet, PythonLexer(), TerminalFormatter()))

        except KeyboardInterrupt:
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break
        except EOFError:  # Ctrl+D exits
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break
        except Exception as e:
            print(f"Linus has frozen. {e}")

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

    coding_repl(resume=args.resume, subject=args.subject)

if __name__ == "__main__":
    cli()
