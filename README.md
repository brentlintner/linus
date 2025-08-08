# Linus

A terminal based, conversational AI coding partner. Batteries and sass fully included.

## Features

* **You're the Navigator**: Linus acts as your pair programmer. He proposes a plan, but you give the final approval. No code gets written without your say-so.
* **Complete Project Context**: Reads your current codebase, directory structure, conversation history, and terminal logs to deeply understand every request.
* **Native Terminal Experience**: Built from the ground up for the command line, with a focus on speed and a keyboard-driven workflow.
* **Live Web Access**: Grounded with up-to-the-minute search results. Just paste a URL, and it will read the content.
* **Seamless Tmux Integration**: Automatically incorporates the content and history of relevant `tmux` panes into its context.
* **Per-Project Customization**: Fine-tune behaviour and provide lasting instructions for each project using a simple `.lin.md` file.
* **Optimized for Code Generation**: Uses a finely-tuned model and prompt configuration engineered specifically for consistent, surgical, high-quality code output.

## Dependencies

* [Python 3.11+](https://www.python.org/downloads/)
* [Pipenv](https://pypi.org/project/pipenv/)
* [Gemini](https://aistudio.google.com/app/apikey)

## Setup

```sh
git clone git@github.com:brentlintner/coding-partner.git
cd coding-partner
alias ai=/path/to/coding-partner/bin/ai
pipenv sync
cp .env.example .env
open .env # Edit .env and set your API key and model (run `ai -m` with a valid key to see available models)
ai -h
```

## Usage

Start up a simple chat repl with no open files, just the project directory structure, terminal pane logs, and conversation history:

```sh
ai
```

### Project File Access

Use the `-f` flag to enable read access for various files or directories (command delimited).

```sh
ai -f .
```

Use the `-w` flag to enable file system write access. If not enabled, code will only be displayed in the chat, but not actually written to files.

```sh
ai -wf .
```

You can also list the files the model can access if `-f` is used with the `-l` flag. Helpful if you have a large project and want to see what files are available for the AI to read.

```sh
ai -lf .
```

Additionally, you can list the total token size of the files in your project with the `-t` flag to get an idea of how large the prompt will be:

```sh
ai -tf .
```

### Ignoring Files

On top of the default ignore list, you can ignore files and directories by creating a `.linignore` file in your project root. This file supports glob patterns, similar to `.gitignore`.

### Command Completion

You can reference files in your project by typing `@` followed by a fuzzy search of the file name. For example, typing `@README` will show you a list of files that match `README`, and you can select one to reference its full path in your chat.

### Project Specific Customization

You can create a `.lin.md` file in your project root to customize the AI's behaviour and context for that specific project. This file can include instructions, context, or any other information you want the AI to consider when interacting with your project.

### Prompt Optimization

Currently there is no automatic prompt size optimization, so you need to be careful about the size of your project. If you find that the prompt is too large, use a more granular `-f` flag to limit the files the AI has open, and use a `.linignore` file or the `-i` flag to ignore specific files or directories.

### Cleaning Up

To clean up your project and remove any generated files, you can use the `-c` flag:

```sh
ai -c
```

### Verbose Mode

To see more details about the AI's actions, such as searches performed, token usage, and more, you can enable verbose mode by adding the `-v` flag:

```sh
ai -vwf .
```

## Development

```sh
pipenv sync --dev # Install all dependencies including development dependencies
bin/ai -Vwf . # Start a development session with debug output and file access
```

## Testing

```sh
bin/test
```

Or with coverage:

```sh
bin/test-cov
```

## Linting

```sh
bin/lint
```

## Stats

```sh
bin/stats
```
