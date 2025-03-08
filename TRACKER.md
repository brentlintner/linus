# Project Management

Anything related to the project management of the project, such as tracking issues, features, bugs, and chores.

## Current

* Use Chunk instead of Part?
* Remove code snippets from output formats and the stream parsing, leave ai to write as markdown

## Backlog

* Bug: each file the ai writes (or the parser parses) never has a trailing new line

* Add tests (smoke tests (fake API), realworld tests (real API), and unit tests

* Open Files / Optimize Prompt
    * If too many files are open on boot, have a threshold or error out (too big for context window)
    * Start using concept "open files", i.e periodically or on threshold: compact versions etc, and bring all into Open Files section instead of File References section (that way we can optimize the file references section succinctly)
        * If you don't have an open file, then ask to open them (can use function calling here)
    * Auto compact versions if too many files are open (perhaps like 100K too many characters)
    * Consider pre-asking the llm (if there is no file referenced) if it thinks the request is just a conversational response or a task (which means data etc should be provided)
        * Else if there is a file reference or it might be a request that needs the project, do a vector lookup and update open files
    * If the file references (aka open files) etc is bigger than certain amount, do a simple optimization for now (how? need vector db...)
        * Simple calculation for now (limit size), eventually use a vector database to store embeddings of files and their contents, and include most related files each time
        * This will be especially useful for the random part lengths the model produces

* Flexible History
    * On resume, should show full files not the last part
    * Use sqlite to store history, file, and project data
    * Bug: Prune is disabled right now (NOTE: we are going to change this anyways when we introduce only "open files")

## Icebox

* File Splitting Issues
    * Convey that if you see a mistake in the file you just wrote, make a new version of it, that isn't a part (hmmm use Chunk)
    * Bug?: If a newer version is given across force continues, then don't print the previous

* Splitting Files
    * Consider using the role="model" for unfinished file part convos for the LLM to understand the context better?
    * Build in a fallback that if a part is not seen in the next force continue, then consider it done

* Update to latest google-genai version

* Use -f ., and if not set don't add any files or directory structures

* Bugs
    * Files and tree data should be refreshed every time the project is resumed, depending on the flags enabled
    * Resume is really slow for giant files

* Ignoring Files
    * Auto ignore binary files as well as other common files/dirs that are not code (get list from AI)
    * Have own .linignore file to ignore files and directories

* Terminal Integration
    * Be able to look at console history with @symbol lookup (ex: a tmux session so the recent log to reference (ex: errors, etc))
    * Be able to allow the ai to writing command blocks (whitelist each command) that run in a subshell.
        * Use automatic function calling for this (have a cli flag to enable this, else it will ask to run it)
        * We then take the sliced output and show it to the llm as an open log file linked to the command. It then can then continue on.
        * Whitelist once per directory for each command? (needs db)

* File Integration
    * Easier ways to provide supplemental files that are huge ex: readme docs, terminal logs
        * Support adding images and files from a Url (types.Part.from_uri)
        * Support adding files like PDFs and images to the project (attach as normal but as individual contents using genai api (need db setup for this)
        * Just show a Chunk: 1/2 (Or Preview: True), and tell LLM to ask for more if they need tha file (for now manual @ load it all)
    * Keep two versions not pruned instead of only one
    * Before writing files ask for confirmation to accept changes (needs db)

* Prompt Customization
    * Pull in language specific files to help the LLM (ex: https://dotcursorrules.com/)
    * If a PROJECT.md exists, pull that into the prompt (right near the top)
        * Create one for this project to test out
        * Have defaults as well
            * ex: Always use spaces to indent not tabs (look for .editorconfig files or other files as a reference)

* Auto update the project file structure when new files are added or updated (db setup + function calling for this?)
* Use a vector database to store embeddings of files and their contents, and optimize prompt generation for large projects and files
* Track versions of files even after pruning (need to use local db setup + function calling for this?)
* Handle renaming or deleting file references, for example when refactoring
* Show the token output count for each final response if verbose
* Remember input prompt history inbetween sessions (keep in the db and fill in if prompt_toolkit allows it?)
* Consider safety settings
* Support text to speech output for responses
* Show better progress bars, notably when writing a file (extract from file or diff the line and compare to current version)
* Be able to see the git history of a file (useful when able to actually commit?)
* Consider using advanced APIs like function calling and search grounding
* Have privacy confirmation for file system integration, and other sensitive data or destructive operations
* Have extra security confirmation for file system integration, terminal commands run, injection/MITM attacks, heuristics and other sensitive data or destructive operations
* Retrieval augmented generation (RAG) features

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
