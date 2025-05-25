# Linus

A terminal-based conversational AI coding partner that helps you write software more efficiently.

## Features

*   **Context-Aware Assistance:**  Maintains session history and project context for consistent, relevant suggestions.
*   **File System Integration:**  Reads and writes directly to project files while showing diffs, allowing for seamless integration and modification.
*   **Fuzzy Finder:** Fuzzy search for files to reference in the current message.
*   **Customizable Ignored Files**: Supports ignoring files and folders via `.linignore`, and auto ignoring anything in your `.gitignore` file

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
bin/ai -wf .
```

List the files the model can access if `-f` is used:

```sh
bin/ai -lf .
```

Show detailed stats about the current session:

```sh
bin/ai -wf . -v
```

## Development

```sh
pipenv install --dev
bin/ai -wf . -V
```

## Testing

```sh
bin/test
```

## Linting

```sh
bin/lint
```

## Stats

```sh
bin/stats
```
