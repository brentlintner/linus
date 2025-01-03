import google.generativeai as ai
import os
import sys
import re

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter
from dotenv import load_dotenv
from google.generativeai import caching

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL')
GEMINI_DISPLAY_NAME = os.getenv('GEMINI_DISPLAY_NAME')

# TODO: save history to a file and/or use a cache and update it as you go
history = []

def load_context_cache():
    cache_file = os.path.join(os.path.dirname(__file__), '../docs/background.txt')
    with open(cache_file, 'r') as f:
        return f.read()

def delete_context_cache(cache):
    try:
        cache.delete()
        print("Context cache deleted.")
    except Exception as e:
        print(f"Error deleting context cache: {e}")

def check_if_env_vars_set():
    if not GEMINI_API_KEY:
        print("Please set the GEMINI_API_KEY environment variable.")
        sys.exit(1)

    if not GEMINI_MODEL:
        print("Please set the GEMINI_MODEL environment variable.")
        sys.exit(1)

    if not GEMINI_DISPLAY_NAME:
        print("Please set the GEMINI_DISPLAY_NAME environment variable.")
        sys.exit(1)

def coding_repl():
    ai.configure(api_key=GEMINI_API_KEY)

    history.append(load_context_cache())

    # Create a cache with the context
    # cache = caching.CachedContent.create(
        # model='models/' + GEMINI_MODEL,
        # display_name=GEMINI_DISPLAY_NAME,
        # system_instruction=context_cache,
        # ttl=None # No expiration
    # )
    # TODO: cache.update(ttl=datetime.timedelta(hours=2)) on loop?

    # Construct a GenerativeModel which uses the created cache.
    # model = ai.GenerativeModel.from_cached_content(cached_content=cache)
    model = ai.GenerativeModel('models/' + GEMINI_MODEL)

    while True:
        try:
            user_input = input("> ")
            if user_input == 'exit':
                break
            history.append('Brent: ' + user_input + '\n')
            response = model.generate_content('\n'.join(history))
            history.append('Linus: ' + response.text + '\n')
            print('\n' + re.sub(r'([\.\!\?])\s\s', r'\1\n\n', response.text))

            # Check if the response contains a code snippet
            if "// [START code_snippet:" in response.text:
                # Extract the code snippet
                code_snippet = response.text.split("// [START code_snippet:")[1].split("// [END code_snippet:")[0]

                # Pretty print and highlight the code
                print(highlight(code_snippet, PythonLexer(), TerminalFormatter()))

        except KeyboardInterrupt:
            if input("\nReally quit? (y/n) ").lower() == 'y':
                break

if __name__ == "__main__":
    check_if_env_vars_set()
    coding_repl()
