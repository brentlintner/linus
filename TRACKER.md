# Project Management

Anything related to the project management of the project, such as tracking issues, features, bugs, and chores.

## Current

* If parts still an issue...
    * Parse metadata into dict, then make it so only special parts have NoMoreParts and only non-special parts have Part
    * Turn down temperature

## Backlog

* Use -f ., and if not set don't add any files or directory structures

* Even quicker streaming (look for \n\n, and leave right side of it for next prompt)

* Add tests (smoke tests (fake API), realworld tests (real API), and unit tests

* Ensuring Code Complete / Fallback Error Handling
    * Explore getting the LLM to consistently examine it's changes and consider if it made any mistakes
    * Add to prompt? "check your code after, and if you see a mistake, make a new version of the file"
    * If something I ask to do results in bad code (ex: recursive import), then ask me what to do, we can always make a new version for it
    * Double ensure if Linus thinks he is stumped, then asks me for help, as I can write code too.

* Open Files / Compaction Optimizations
    * Start using concept "open files", i.e periodically or on threshold: compact versions etc, and bring all into Open Files section instead of File References section (that way we can optimize the file references section succinctly)
        * If you don't have an open file, then ask to open them (can use function calling here)
    * If too many files are open on boot, have a threshold or error out (too big for context window)
    * Auto compact versions if too many files are open (perhaps like 100K too many characters)
    * Consider pre-asking the llm (if there is no file referenced) if it thinks the request is just a conversational response or a task (which means data etc should be provided)
        * Else if there is a file reference or it might be a request that needs the project, do a vector lookup and update open files
    * If the file references (aka open files) etc is bigger than certain amount, do a simple optimization for now (how? need vector db...)
        * Simple calculation for now (limit size), eventually use a vector database to store embeddings of files and their contents, and include most related files each time
        * This will be especially useful for the random part lengths the model produces
    * Flexible History, using sqlite to store history, file, and project data
    * Prune is disabled right now (NOTE: we are going to change this anyways when we introduce only "open files")
    * Use a vector database to store embeddings of files and their contents, and optimize prompt generation for large projects and files
    * For very large projects, consider using an external memory mechanism like a vector database (with embeddings generated).

## Icebox

### Bugs

* Sometimes can print a diff if long running? (1.5 pro issue?)

* If model stops mid file, even if continue, it won't write the file
* Files and tree data should be refreshed every time the project is resumed, depending on the flags enabled
* Resume is really slow for giant files
* Ensure trailing newlines don't happen a lot
    * This means we drop an empty last part too?

### Features

* Be able to talk to the AI as a normal repl session (like Gemini web app)

* ? Remove code snippets from output formats and the stream parsing, leave ai to write as markdown

* Prompt Customization
    * Pull in language specific files to help the LLM (ex: https://dotcursorrules.com/)
    * If a PROJECT.md exists, pull that into the prompt (right near the top)
        * Create one for this project to test out
        * Have defaults as well
            * ex: Always use spaces to indent not tabs (look for .editorconfig files or other files as a reference)

* Ignoring Files
    * Auto ignore binary files as well as other common files/dirs that are not code (get list from AI)
    * Have own .linignore file to ignore files and directories

* Terminal Integration
    * Be able to see test output in the terminal (ex: pytest, etc), just let it run the commnads?
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

* Auto update the project file structure when new files are added or updated (db setup + function calling for this?)
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

* Try out other models like Claude using a dedicated vertex AI instance
* Try turning down the temperature for more focused responses, maybe helps wrapping? (SET TO 0.4 to 0.6)
* For very long conversation histories, consider summarizing earlier parts of the conversation.
* Potentiall start asking for diffs instead of full files, if file-by-file + part-by-part isn't feasible enough)
* If you have exceptionally large files, consider breaking them into smaller chunks and providing them to the LLM separately.
* You could add more metadata to your JSON directory structure, such as timestamps, types, function/class summaries.
* Look into leveraging [explain reasoning](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/explain-reasoning)
* Experiment with parameter values (ex: lower temperature for more focused responses)
