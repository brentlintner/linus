# Tracker

Anything related to the project management of the project, such as tracking issues, features, bugs, and chores.

## Epics

* Make stable regardless of file size and output length
* Make stable in terms of runnable code generation and context awareness
* Does having more succinct, highly cohesive, short method code help the AI's context awareness?
* Have a test suite

## Backlog

* Context IDEA:
    * Include LSP based information in the prompt, such as function signatures, class definitions, and mention in comments that files they are from?
    * Any other metadata that can help the LLM understand the context better? (aside from picking files or parts of a file based on vector database)
    * Maybe last edited, last modified, and other metadata that can help the LLM understand the context better?
    * Meh on commit history...

* Focusing model experience
    * (DONE) Turn down temperature
    * (DONE) Tweak prompt to be more focused and concise (updated flow considering recency, guidance and primacy)
    * Considering only showing the last tmux command (i.e. everything after 2nd last "^\$$")

* Tests
    * Integration tests for client injectiong (parsing mainly)
    * Unit for tmux, parser, file utils etc
    * System tests, really needed? Maybe something to run optionally since it hits the API and is slow + costs money
        * First system test: Need no color + quiet + test for testing?
        * Smoke test that runs multiple times, with a minimal prompt?
        * Need to escape+enter?

* Need to ideally keep prompts <200K characters for better pricing
    * Auto compact flag (-a)
    * Auto compact when certain threshold is reached (i.e. 100K tokens in metadata)
    * Auto compact goes through the conversation history and removes all files or the last one? (and llm_prompt generation is the same, version 1 always)
    * $compact command runs same method as auto compact (but removes all files?)
    * Now $reset will clear the conversation history and file references, then re-initialize the database and llm prompt will be updated automatically as usual
    * Remove Files table as we won't use it anymore for now
    * NOTE: ensure db is saved for linus message (or is it just the debug tmp file not saving immediately?)

* File Split / EOF Handling
    * (DONE) When adding parts only look for a single \n after metadata header (so we don't lose indentation)
    * (DONE) Always add a trailing newline to files
    * Needed? Ensure files in the initial file references section are back to back (no newline between parts, like llm does)

* Project Customization
    * Per project .lin.md so it only applies if the context applies?
    * language .linrc - Pull in language specific files in the Database to help the LLM (ex: https://dotcursorrules.com/)- add to .linrc
    * library .linrc - Pull in best practices, cheatsheets and other useful information in general (or make the main background have that?)
        * To start: Always use spaces to indent not tabs (look for .editorconfig files or other files as a reference)

## Icebox

### Bugs

### Features

* Scrub terminal logs for sensitive data like keys, passwords or hashes

* Consider handling prompt feedback cases https://ai.google.dev/api/generate-content#v1beta.GenerateContentResponse

* Have option to enable or disable search grounding?

* Considering using FinishReason API to determine if the LLM ran out of tokens or not
    * Not a big issue with latest models though, but helpful for debug mode?

* Even quicker streaming (look for \n\n, and leave right side of it for next prompt)

* Polishing
    * Include top level directory name if it is ignored
    * Print separate consistency now that you changed end logs earlier
    * Finish linting
    * Eventually, -o to set initially open files (now defaults to -f), -f will just limit the files to the project
    * Add unicode > OR Remove '> ' from the prompt? (clean copy/paste)

* Remember input prompt history inbetween sessions (keep in the db and fill in if prompt_toolkit allows it?)

* Terminal Integration v2
    * Be able to allow the ai to writing command blocks (whitelist each command) that run in a subshell, like tests.
        * Use automatic function calling for this (have a cli flag to enable this, else it will ask to run it)
        * We then take the sliced output and show it to the llm as an open log file linked to the command. It then can then continue on.
        * Whitelist once per directory for each command? (needs db)

* Learning:
    * Explore getting the LLM to consistently examine it's changes and consider if it made any mistakes
        * After files have been written, send a hidden reply from me saying "check your last message, did you miss anything or make any mistakes? If so, fix them. If not print only "NOPE"
        * If it says "NOPE", then it can continue on
        * If it fixes something, then it will continue on itself (only do this once or twice, i.e. have similar limit like force continue)
        * Additionally, if the tests fail, then we would ofc tell the model that first, with something akin to "the tests failed, was there something that you missed?" sort of thing
    * Consider using a meta-learning approach to improve the model's performance
    * ex: $learn command tells model to summarize the conversation into a paragraph, this is stored in the db and all are added to the prompt per project

* Ensuring Code Complete / Fallback Error Handling
    * Explore getting the LLM to consistently examine it's changes and consider if it made any mistakes
    * Meta-add to prompt? "check your code after, and if you see a mistake, make a new version of the file"
    * If something I ask to do results in bad code (ex: recursive import), then ask me what to do, we can always make a new version for it
    * Double ensure if Linus thinks he is stumped, then asks me for help, as I can write code too.

* Open Files / Compaction Optimizations
    * Always merge multiple parts into one file after LLM sends it
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

* Ignoring Files
    * Auto ignore binary files as well as other common files/dirs that are not code (get list from AI)

* File Integration
    * Easier ways to provide supplemental files that are huge ex: readme docs, terminal logs
        * Support adding images and files from a Url (types.Part.from_uri)
        * Support adding files like PDFs and images to the project (attach as normal but as individual contents using genai api (need db setup for this)
        * Just show a Chunk: 1/2 (Or Preview: True), and tell LLM to ask for more if they need tha file (for now manual @ load it all)

* ? Track versions of files even after pruning (need to use local db setup + function calling for this?)
* Handle renaming or deleting file references, for example when refactoring (metadata delete? shell commands?))
* Consider safety settings
* Support text to speech output for responses
* Show better progress bars, notably when writing a file (extract from file or diff the line and compare to current version)
* Be able to see the git history of a file (useful when able to actually commit?)
    * Have the concept of "Git Blame" mapping to conversation fingerprint points
* Have privacy confirmation for file system integration, and other sensitive data or destructive operations
* Have extra security confirmation for file system integration, terminal commands run, injection/MITM attacks, heuristics and other sensitive data or destructive operations
* Retrieval augmented generation (RAG) features

### Performance

* Try turning down the temperature for more focused responses, maybe helps wrapping? (SET TO 0.4 to 0.6)
* For very long conversation histories, consider summarizing earlier parts of the conversation.
* If you have exceptionally large files, consider breaking them into smaller chunks and providing them to the LLM separately.
* You could add more metadata to your JSON directory structure, such as timestamps, types, function/class summaries.
* Look into leveraging [explain reasoning](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/prompts/explain-reasoning)
* Experiment with parameter values (ex: lower temperature for more focused responses)
* Try out other models like Claude using a dedicated vertex AI instance (and different library?)
