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

## Project Management

### Features

*   Be able to export as pip package, so can we can use it on WIP branches for itself!
*   Be able to see the git history
*   Be able to look at consolel history (ex: a tmux session so the recent log to reference (ex: errors, etc))
*   Handle renaming or deleting file references, for example when refactoring
*   Auto update the project file structure when new files are added or updated
*   Be able to possibly get the reply quickly, then send again to get code written (ex: like copilot chat - there is a gemini API method for this?)
*   Consider using advanced VertexAI APIs (ex: [code execution](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/code-execution#googlegenaisdk_tools_code_exec_with_txt-python_genai_sdk), [function calling](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling) and [search grounding](https://ai.google.dev/gemini-api/docs/grounding?lang=python))
*   Be able to allow the ai to run certain cli commands
*   Support text to speech output for responses
*   Auto ignore binary files as well as other common files that are not code (don't assume your large .ignore/.gitignore is present)
*   Have privacy confirmation for file system integration, and other sensitive data or destructive operations

### Bugs

### Chores

*   For very long conversation histories, consider summarizing earlier parts of the conversation.
*   Use a context cache and update it as you go (once file is >32K chars)?
*   For very large projects, consider using an external memory mechanism like a vector database (with embeddings generated).
*   If you have exceptionally large files, consider breaking them into smaller chunks and providing them to the LLM separately.
*   You could add more metadata to your JSON directory structure, such as timestamps, types, function/class summaries.
*   Add a cli flag to make the AI verbose or compact (i.e. the output formatting and character)
