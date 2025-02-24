# Project Management

Anything related to the project management of the project, such as tracking issues, features, bugs, and chores.

## Current

*   Streaming case: when code snippets are tabbed (i.e. inside a markdown list)
*   Remove the background from highlighted code
*   Get around 8K output token limit (tell AI to write diffs + summarize->file-by-file)

## Backlog

*   Show the token output count for each final response if verbose
*   Be able to look at console history (ex: a tmux session so the recent log to reference (ex: errors, etc))
*   Support versions of files (need to use local db setup + function calling for this)
*   Auto update the project file structure when new files are added or updated (db setup + function calling for this?)
*   Handle renaming or deleting file references, for example when refactoring
*   Use a vector database to store embeddings of files and their contents, and optimize prompt generation for large projects and files
*   Auto ignore binary files as well as other common files that are not code (don't assume your large .ignore/.gitignore is present)

## Icebox

*   Remember input prompt history inbetween sessions
*   Be able to allow the ai to run certain cli commands
*   Support text to speech output for responses
*   Show better progress bars, notably when writing a file (extract from file or diff the line and compare to current version)
*   Be able to see the git history of a file (useful when able to actually commit?)
*   Consider using advanced APIs like function calling and search grounding
*   For very long conversation histories, consider summarizing earlier parts of the conversation.
*   Easier ways to provide supplementat doc files or will search grounding solve that?
*   For very large projects, consider using an external memory mechanism like a vector database (with embeddings generated).
*   If you have exceptionally large files, consider breaking them into smaller chunks and providing them to the LLM separately.
*   You could add more metadata to your JSON directory structure, such as timestamps, types, function/class summaries.
*   Look into leveraging [explain reasoning](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/explain-reasoning)
*   Have privacy confirmation for file system integration, and other sensitive data or destructive operations
*   Experiment with parameter values (temperature etc)
