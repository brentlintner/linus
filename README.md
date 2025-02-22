# Coding Partner

Linus is a CLI based coding assistant that can be the passenger or the driver in a pair programming session.

## Features

*   **Interactive Code Generation:**  Generates code snippets and full files based on natural language prompts within a CLI environment.
*   **Mouse-Free Navigation:**  Use keyboard shortcuts to navigate and interact with the CLI.
*   **Context-Aware Assistance:**  Maintains session history and project context for consistent, relevant suggestions.
*   **File System Integration:**  Reads and writes directly to project files, allowing for seamless integration and modification.
*   **Diff View:** Edits to files are shown as unified diffs instead of the entire file contents.
*   **Fuzzy File Referencing:** Use `@` symbol to fuzzy search and attach project files to the current message.
*   **Customizable Ignored Files**: Supports `.gitignore` and `.ignore` files for customizing ignored files.

## Dependencies

*   [Python 3.11+](https://www.python.org/downloads/)
*   [Pipenv](https://pypi.org/project/pipenv/)
*   [Gemini](https://aistudio.google.com/app/apikey)

## Setup

```sh
pipenv install
cp .env.example .env
open .env # Edit .env and set your API key and model (ex: 'gemini-flash-2.0')
bin/ai -h
```

## Using

Open up a simple chat repl:

```sh
ai
```

Start a fully featured chat repl with file system integrations:

```sh
ai -iwf
```

List the files the model can access if `-w` is enabled:

```sh
bin/ai -l
```

Show detailed stats about the current session:

```sh
ai -iwfv
```

## FAQ

*   **Why was this created?**

    I wanted to create a coding assistant that could help me code in a more natural, streamlined way,
    all without having to switch between windows or use a mouse. Essentially a pair programming tool
    that I can have in the terminal beside my code editor (neovim), without needing to be coupled to any editor.
