# Linus

A CLI based conversational AI coding partner that helps you write software more efficiently.

## Features

* **Highly Tuned:**  Built on a custom, finely tuned prompt and model config for optimal performance.
* **Context-Aware:**  Automatically includes up-to-date project files, directory structure, terminal logs, and other relevant context in each request.
* **Persistent Memory:**  Maintains a history of interactions, allowing the AI to remember past conversations and context.
* **File System Integration:**  Writes directly to project files while showing diffs.
* **Command Completion:** Fuzzy search files to reference (`@`), or run specific commands (`$`).
* **Ignore Files**: Alongside a default ignore list, supports custom ignores via `.linignore`, and auto ignores anything in your `.gitignore` file.
* **Tmux Integration**:  Automatically adds relevant panes and their history to the prompt.
* **Project Specific Customization**: Supports per-project `.lin.md` files for further customization of the AI's behaviour and context.

## Dependencies

*   [Python 3.11+](https://www.python.org/downloads/)
*   [Pipenv](https://pypi.org/project/pipenv/)
*   [Gemini](https://aistudio.google.com/app/apikey)

## Setup

```sh
pipenv install
cp .env.example .env
open .env # Edit .env and set your API key and model (run `ai -m` with a valid key to see available models)
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
bin/ai -vwf .
```

## Development

```sh
pipenv install --dev
bin/ai -Vwf .
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
