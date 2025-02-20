# AI Coding Partner

Linus is an CLI based AI coding assistant you can xtreme program with.

He can code with you for as long as you need, and you won't even realize he's not human!

Well, almost. But it's pretty good!

## Features

*   **Interactive Code Generation:**  Generates code snippets and full files based on natural language prompts within a CLI environment.
*   **Context-Aware Assistance:**  Maintains session history and project context for consistent, relevant suggestions.
*   **File System Integration:**  Reads and writes directly to project files, allowing for seamless integration and modification (opt-in).
*   **Fuzzy File Referencing:** Use `@` symbol to fuzzy search and reference project files.
*   **Diff View:** Edits to files are shown as unified diffs instead of the entire file contents.
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

## FAQ

*   **Why was this created?**

    I wanted to create a coding assistant that could help me code in a more natural, streamlined way,
    all without having to switch between windows or use a mouse.

## Project Management

### Features

*   Be able to see the git history
*   Be able to look at a tmux session so the recent log to reference (ex: errors, etc)
    *   Or: Be able to wrap processes in a tmux session, i.e. supervisor mode
*   Handle renaming or deleting file references, for example when refactoring
*   Auto update the project file structure when new files are added or updated
*   Be able to possibly get the reply quickly, then send again to get code written (ex: like copilot chat - there is a gemini API method for this?)
*   Consider using advanced VertexAI APIs (ex: [code execution](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/code-execution#googlegenaisdk_tools_code_exec_with_txt-python_genai_sdk), [function calling](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling) and [search grounding](https://ai.google.dev/gemini-api/docs/grounding?lang=python))
*   Be able to shrewdly translate natural language commands and run them using the local user shell (i.e. --shell connect mode) (via function calling)
*   Support text to speech output for responses

### Bugs

*   Syntax highlighting should work but file: and snippet: format are not standard
*   Ensure that mdir -p is used when creating a new file from a file reference

### Chores

*   For very long conversation histories, consider summarizing earlier parts of the conversation.
*   Use a context cache and update it as you go (once file is >32K chars)?
*   For very large projects, consider using an external memory mechanism like a vector database (with embeddings generated).
*   If you have exceptionally large files, consider breaking them into smaller chunks and providing them to the LLM separately.
*   You could add more metadata to your JSON directory structure, such as timestamps, types, function/class summaries.
*   Add a cli flag to make the AI verbose or compact (i.e. the output formatting and character)
