## Project Management

Anything related to the project management of the project, such as tracking issues, features, bugs, and chores.

### Bugs

### Features

*   Be able to see the git history
*   Be able to look at console history (ex: a tmux session so the recent log to reference (ex: errors, etc))
*   Be able to possibly get the reply quickly (ex: [streaming](https://github.com/googleapis/python-genai?tab=readme-ov-file#streaming))

*   Be able to export as pip package, so can we can use it on WIP branches for itself!
*   Handle renaming or deleting file references, for example when refactoring
*   Auto update the project file structure when new files are added or updated
*   Be able to allow the ai to run certain cli commands
*   Support versions of files (need to use local db setup for this)
*   Support text to speech output for responses
*   Auto ignore binary files as well as other common files that are not code (don't assume your large .ignore/.gitignore is present)
*   Have privacy confirmation for file system integration, and other sensitive data or destructive operations

### Chores

*   Look into leveraging [explain reasoning](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/explain-reasoning)
*   Migrate to google-genai (https://github.com/googleapis/python-genai)
*   Consider using advanced VertexAI APIs (ex: [code execution](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/code-execution#googlegenaisdk_tools_code_exec_with_txt-python_genai_sdk), [function calling](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling) and [search grounding](https://ai.google.dev/gemini-api/docs/grounding?lang=python))
*   For very long conversation histories, consider summarizing earlier parts of the conversation.
*   Use a context cache and update it as you go (once file is >32K chars)?
*   For very large projects, consider using an external memory mechanism like a vector database (with embeddings generated).
*   If you have exceptionally large files, consider breaking them into smaller chunks and providing them to the LLM separately.
*   You could add more metadata to your JSON directory structure, such as timestamps, types, function/class summaries.
*   Add a cli flag to make the AI verbose or compact (i.e. the output formatting and character)
*   Experiment with [perimiter values](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/adjust-parameter-values)
