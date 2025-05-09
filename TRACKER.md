# Project Management

Anything related to the project management of the project, such as tracking issues, features, bugs, and chores.

## Epics

* Make stable regardless of file size and output length
* Make stable in terms of runnable code generation and context awareness
* Does having more succinct, highly cohesive, short method code help the AI's context awareness?
* Have a test suite

## Current

* Allow using a specific model depending on project (use a .linrc file?)

* Compact/File Rework
    * Always merge multiple parts into one file after LLM sends it
    * Bug: Add file metadata start to incomplete file block?
    * Should consider dynamic putting it together with vector etc

* Refresh should run $compact first so it "prunes all files in the conversation history"

* Still hallucinating and writing both our conversations. Should make that more forceful or even re-add it to my own reply?
    * Possible it is because of the "wait before coding" prompt and it's not clear enough
    * --> possible the massive amount of files, and it lost context
    * I.e add 'remember the 'Instructions' section you should follow'

## Backlog

* Snippets find files causes out of range (just remove snippets formatting?)
* Bug: Parts don't have a newline at the end if we strip the last line?

* Even quicker streaming (look for \n\n, and leave right side of it for next prompt)
* Always add a trailing newline to files only if the existing one does, else always remove it

* Polishing
    * Include top level directory name if it is ignored
    * Print separate consistency now that you changed end logs earlier
    * Add back the request/response token logging separate
    * Finish linting
    * Eventually, -o to set initially open files (now defaults to -f), -f will just limit the files to the project
    * Add unicode > OR Remove '> ' from the prompt? (clean copy/paste)

* File List
    * Include top level directory name if it is ignored?

* Sqlite DB
    * Prune history not working (keeps previous version?)
        * "Auto compact" history based on context window size (i.e. keep a few versions of each file if possible)
        * Only prune a file once it gets too big, and only prune the oldest versions

* Prompt Engineering
    * It's still talking about parts etc
    * Try to avoid writing tests, leave that to separate (causes attention shift for llm?)
    * Allow llm to say, you're wrong about your request
    * Prompt should have flow to where the LLM _will_ start writing and responding
    * Current "wait before coding" is too good (waits even when it finishes a file and needs to write another?)
    * "If you make a mistake that breaks the current codebase, correct it by sending a new version of the file."

* Tests
    * First system test: Need no color + quiet + test for testing
    * Smoke test that runs multiple times, with a minimal prompt.
    * Need to escape+enter

* Learning:
    * Explore getting the LLM to consistently examine it's changes and consider if it made any mistakes
        * After files have been written, send a hidden reply from me saying "check your last message, did you miss anything or make any mistakes? If so, fix them. If not print only "NOPE"
        * If it says "NOPE", then it can continue on
        * If it fixes something, then it will continue on itself (only do this once or twice, i.e. have similar limit like force continue)
        * Additionally, if the tests fail, then we would ofc tell the model that first, with something akin to "the tests failed, was there something that you missed?" sort of thing
    * Consider using a meta-learning approach to improve the model's performance
    * ex: $learn command tells model to summarize the conversation into a paragraph, this is stored in the db and all are added to the prompt per project

* Prompt Customization
    * Linus keeps using metadata {{{}}} syntax (use PROJECT.md instead)
    * Pull in language specific files in the Database to help the LLM (ex: https://dotcursorrules.com/)
    * Pull in best practices, cheatsheets and other useful information from the Database
    * If a PROJECT.md exists, pull that into the Database
        * Create one for this project to test out
        * For example: don't use the {{}} syntax inline in any file's content, use the placeholder method in parser.py
        * Have defaults as well
            * ex: Always use spaces to indent not tabs (look for .editorconfig files or other files as a reference)

* Ensuring Code Complete / Fallback Error Handling
    * Explore getting the LLM to consistently examine it's changes and consider if it made any mistakes
    * Add to prompt? "check your code after, and if you see a mistake, make a new version of the file"
    * If something I ask to do results in bad code (ex: recursive import), then ask me what to do, we can always make a new version for it
    * Double ensure if Linus thinks he is stumped, then asks me for help, as I can write code too.

* Open Files / Compaction Optimizations
    * Split open files at a certain threshold (i.e. LLM learns examples from it)
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

* Selling: SaaS web app, or just a cli download (forever license), or commerical license for commercial use (?)

### Bugs

* Sometimes can print a diff if long running? (1.5 pro issue?)

* If parts still an issue...
    * Turn down temperature?

* If model stops mid file, even if continue, it won't write the file
* Files and tree data should be refreshed every time the project is resumed, depending on the flags enabled
* Resume is really slow for giant files
* Ensure trailing newlines don't happen a lot
    * This means we drop an empty last part too?

### Features

* Be able to talk to the AI as a normal repl session (like Gemini web app)

* ? Remove code snippets from output formats and the stream parsing, leave ai to write as markdown

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
    * Have the concept of "Git Blame" mapping to conversation fingerprint points
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
