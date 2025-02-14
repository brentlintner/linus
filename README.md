# Coding Partner

A CLI based tool that simulates a coding partner by providing "helpful" suggestions and comments.

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

## Usage

*   Start a new session: `bin/ai`
*   Resume a previous session: `bin/ai -r` or `bin/ai --resume`

## Feature Ideas

*   Use the tmux session feature to understand all the commands
*   Use a context cache and update it as you go (once file is >32K chars)
*   Add a delay argument to cli once it exists
*   Have multiple characters and choose one at random (all celebrities or fictional characters on the phone but together)
*   Make it easier to specify a history file (autocomplete)
*   Support more advanced REPL (arrow keys, multi-line input, etc.)
*   Be able to paste files or snippets, or reference them so the AI can see them
*   Be able to view files that get printed out (keep track in tmp folder file?)
*   Be able to update files themselves based on new code the AI suggests
*   Add "is thinking" terminal logging
*   Add fuzzy path finder completer
