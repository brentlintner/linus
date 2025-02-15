# Coding Partner

CLI tool that uses the Gemini API to provide you with a full-featured AI coding partner.

It can help you write code, debug, and even refactor your code.

## Dependencies

*   [Python 3.11+](https://www.python.org/downloads/)
*   [Pipenv](https://pypi.org/project/pipenv/)
*   [Gemini](https://aistudio.google.com/app/apikey)

## Setup

1.  Install dependencies:

    ```sh
    pipenv install
    ```
2.  Copy the example environment file and set your Gemini API key:

    ```sh
    cp .env.example .env
    # Edit .env and set GEMINI_API_KEY
    ```
3.  Run the script:

    ```sh
    bin/ai -h
    ```

## Feature Ideas

*   Cleanup the way gemini responses have extra newlines and extra spaces
*   Support having a tmux session log to reference (ex: errors, etc)
*   Use a context cache and update it as you go (once file is >32K chars)?
*   Prune history of duplicate file or snippets versions when history is too long
*   Support more advanced REPL (arrow keys, multi-line input, etc.) once shift+enter or cmd+enter is pressed
*   Support text to speech output for responses
