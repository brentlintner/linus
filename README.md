# Linus

A terminal-based AI coding partner that helps you write software more efficiently.

## Features

*   **Extreme Terminal Programming:**  Never leave your terminal or touch that disgusting mouse ever again.
*   **Context-Aware Assistance:**  Maintains session history and project context for consistent, relevant suggestions.
*   **File System Integration:**  Reads and writes directly to project files while showing diffs, allowing for seamless integration and modification.
*   **Shell Interation:**  Executes terminal commands on your behalf and analyzes the output for errors.
*   **Fuzzy Search:** Fuzzy searchs specfic project files to reference in the current message.
*   **Tmux Integration:**  Provide terminal output when debugging test failures or other issues.
*   **Customizable Ignored Files**: Supports ignore files and folders, including auto ignoring anything in your `.gitignore` file

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
bin/ai
```

Start a fully featured chat repl with file system integrations:

```sh
bin/ai -iwf
```

List the files the model can access if `-w` is enabled:

```sh
bin/ai -l
```

Show detailed stats about the current session:

```sh
bin/ai -iwfv
```
