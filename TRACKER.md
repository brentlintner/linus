# Project Management

Anything related to the project management of the project, such as tracking issues, features, bugs, and chores.

## Current

* Add tests (smoke tests (fake API), realworld tests (real API), and unit tests
* Bug: Each file part is immediately written to the file (should be batched?)
* As the model produces the output, the library can monitor the token count live (show in status if verbose)
    * Log token metadata on each response (usage_metadata=GenerateContentResponseUsageMetadata)
* Print Linus is coding file (part 1/X), or typing if streaming, or thinking if stream idles
* Be able to include a whitelist of files instead of just ignore (i.e huge projects...)
* If don't see a file in references or converstatio, ask for them

## Backlog

* Start using concept "open files", i.e periodically or on threshold: compact versions etc, and bring all into Open Files section instead of File References section (that way we can optimize the file references section succinctly)
* If the file references etc is bigger than certain amount, do a simple optimization for now (how? need vector db...)
* Bug: If continuing from a half done file, bring over the remaining queued response
    * If the token count reaches a limit, cut off the model, finish the wrapper if it's a file, show a warning, and force continue
* Bug: Prune is disabled right now
* Bug: Refresh is broken with bad escape position issue
* Pull in language specific files to help the LLM (ex: https://dotcursorrules.com/)
* If a PROJECT.md exists, pull that into the prompt (right near the top)
  * Create one for this project to test out
  * Have defaults as well
    * ex: Always use spaces to indent not tabs (look for .editorconfig files or other files as a reference)
* Use sqlite to store history, file, and project data
* Ignoring Files
  * Auto ignore binary files as well as other common files/dirs that are not code (get list from AI)
  * Have own .linignore file to ignore files and directories
* Terminal Integration
  * Be able to look at console history with @symbol lookup (ex: a tmux session so the recent log to reference (ex: errors, etc))
  * Be able to allow the ai to writing command blocks (whitelist each command) that run in a subshell.
    * We then take the sliced output and show it to the llm as a log file linked to the command. It then can then continue on.
    * Whitelist once per directory for each command? (needs db)
* File Integration
  * Easier ways to provide supplemental files that are huge ex: readme docs, terminal logs
    * Support adding files like PDFs and images to the project (attach as normal but as individual contents (need db setup for this)
    * Just show a Chunk: 1/2 (Or Preview: True), and tell LLM to ask for more if they need tha file (for now manual @ load it all)
  * Keep two versions not pruned instead of only one
  * Before writing files ask for confirmation to accept changes (needs db)

## Icebox

* Bug: Files and tree data should be refreshed every time the project is resumed, depending on the flags enabled
* Bug: Resume is really slow for giant files
* Auto update the project file structure when new files are added or updated (db setup + function calling for this?)
* Use a vector database to store embeddings of files and their contents, and optimize prompt generation for large projects and files
* Support versions of files (need to use local db setup + function calling for this?)
* Handle renaming or deleting file references, for example when refactoring
* Show the token output count for each final response if verbose
* Remember input prompt history inbetween sessions
* Adjust the safety settings
* Support text to speech output for responses
* Show better progress bars, notably when writing a file (extract from file or diff the line and compare to current version)
* Be able to see the git history of a file (useful when able to actually commit?)
* Consider using advanced APIs like function calling and search grounding
* Have privacy confirmation for file system integration, and other sensitive data or destructive operations
* Have extra security confirmation for file system integration, terminal commands run, injection/MITM attacks, heuristics and other sensitive data or destructive operations

### Performance

* Don't pretty print JSON data?
* Try out other models like Claude using a dedicated vertex AI instance
* Try turning down the temperature for more focused responses, maybe helps wrapping? (SET TO 0.4 to 0.6)
* Explore getting the LLM to consistently examine it's changes and consider if it made any mistakes
* For very long conversation histories, consider summarizing earlier parts of the conversation.
* For very large projects, consider using an external memory mechanism like a vector database (with embeddings generated).
* Potentiall start asking for diffs instead of full files, if file-by-file + part-by-part isn't feasible enough)
* If you have exceptionally large files, consider breaking them into smaller chunks and providing them to the LLM separately.
* You could add more metadata to your JSON directory structure, such as timestamps, types, function/class summaries.
* Look into leveraging [explain reasoning](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/explain-reasoning)
* Experiment with parameter values (ex: lower temperature for more focused responses)
