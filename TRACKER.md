# Project Management

Anything related to the project management of the project, such as tracking issues, features, bugs, and chores.

## Current

* Optimize output token limit by showing plan first, then file-to-file and part-by-part (no show code first)
  * Limit your response to 8000 characters: If you are writing a large file, split it up into smaller chunks and send the first chunk, then the second chunk, etc.

## Backlog

* Be able to look at console history with @symbol lookup (ex: a tmux session so the recent log to reference (ex: errors, etc))
* Use sqlite to store history, file, and project data
* Easier ways to provide supplemental files that are huge ex: readme docs, terminal logs
  * Just show a Part: 1, and tell LLM to ask for more, then for now manual @ load it all
* Keep two versions not pruned instead of only one
* Be able to allow the ai to writing command blocks (whitelist each command) that run in a subshell.
  * We then take the sliced output and show it to the llm as a log file linked to the command. It then can then continue on.

## Icebox

* Bug: When the streamed text for a file/snippet is the first character of the stream it renders before the content and breaks
* Bug: Snippets and files that are inside markdown blocks (ex: lists) are not being highlighted properly
* Bug: Any source code file with backticks in it breaks the pretty printing in the terminal
* Bug: Files and tree data should be refreshed every time the project is loaded, depending on the flags enabled
* Bug: Resume is really slow for giant files

* Auto update the project file structure when new files are added or updated (db setup + function calling for this?)
* Use a vector database to store embeddings of files and their contents, and optimize prompt generation for large projects and files
* Auto ignore binary files as well as other common files that are not code (don't assume your large .ignore/.gitignore is present)
* Support versions of files (need to use local db setup + function calling for this?)
* Handle renaming or deleting file references, for example when refactoring
* Show the token output count for each final response if verbose
* Remember input prompt history inbetween sessions
* Support text to speech output for responses
* Show better progress bars, notably when writing a file (extract from file or diff the line and compare to current version)
* Be able to see the git history of a file (useful when able to actually commit?)
* Consider using advanced APIs like function calling and search grounding
* Have privacy confirmation for file system integration, and other sensitive data or destructive operations

### Performance

* For very long conversation histories, consider summarizing earlier parts of the conversation.
* For very large projects, consider using an external memory mechanism like a vector database (with embeddings generated).
* Potentiall start asking for diffs instead of full files, if file-by-file + part-by-part isn't feasible enough)
* If you have exceptionally large files, consider breaking them into smaller chunks and providing them to the LLM separately.
* You could add more metadata to your JSON directory structure, such as timestamps, types, function/class summaries.
* Look into leveraging [explain reasoning](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/explain-reasoning)
* Experiment with parameter values (ex: lower temperature for more focused responses)
