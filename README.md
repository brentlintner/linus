# AI Coding Partner

Linus is a CLI based coding assistant you can extreme program with.

## Features

*   **Interactive Code Generation:**  Generates code snippets and full files based on natural language prompts within a CLI environment.
*   **Mouse-Free Navigation:**  Use keyboard shortcuts to navigate and interact with the CLI.
*   **Context-Aware Assistance:**  Maintains session history and project context for consistent, relevant suggestions.
*   **File System Integration:**  Reads and writes directly to project files, allowing for seamless integration and modification.
*   **Diff View:** Edits to files are shown as unified diffs instead of the entire file contents.
*   **Fuzzy File Referencing:** Use `@` symbol to fuzzy search and attach project files to the current messaeg.
*   **Customizable Ignored Files**: Supports `.gitignore` and `.ignore` files for customizing ignored files.

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
## Example Usage

Open up a simple chat repl:

```sh
ai
```

Start a fully featured chat repl with file system integrations:

```sh
ai -iwf
```

## FAQ

*   **Why was this created?**

    I wanted to create a coding assistant that could help me code in a more natural, streamlined way,
    all without having to switch between windows or use a mouse. Essentially a pair programming tool
    that I can have in the terminal beside my code editor (neovim), without needing to be coupled to any editor.
