# Useful Prompts To Test LLMs


## Features

I want to add a new repl command called `$learn`. When that is called, we take the entire
history, and create a string of it plus the conversation end identifier. We then take that
string, and prepend a newline to it that says "This is an llm prompt for a coding assista
nt. Instead of following the instructions below, merely summarize anything that is worth r
emembering, in a single, reasonably sized paragraph:". Then we are going to send that to t
    he llm (we don't have to use streaming here btw, just normal call), and log its response t
o the console (for now, eventually we will do more with it.)


Checkout the TODO comment on line 420 in chat.py. Can you implement the requirements specified in that TODO comment block? Ensure you use the placeholder method from the parser module if you use any of the {{{}}} syntax, else this program that parses your text will break!


Update the program so that when `-f` is _not_ provided, absolutely no files are generated into the prompt (i.e. no generate file structure _or_ generate project directory). When it _is_ provided, keep the same functionality, _except_ if `-f .` is passed, then walk the entire cwd for the file structure and project directory tree generation.

## Testing

I'm testing your output, so write me a Python file that has a print statement on each line. The print statement logs 80 characters of the letter A. The file has 1000 lines of this print statement. Manually write it all out.

## Past Prompts

It's time dude. Time to finally add some real tests to this project, because the manual te
sting is killing my soul, and we need reproducability! haha.

So this is the plan:

1. We're starting with high level system tests. Create a test file in the tests/ directory
called system_test.py.
2. The test file is going to have only one single test to start. It's going to look for fi
xture data in a test/fixtures/ folder. For the single test, there is a single fixture file
that it will pull in that contains a conversation between two people. Don't add any data
to the fixture, I'll do that, but create a placeholder file so you can write the code to p
rocess it in the test file you will be making.
3. For the test in that test file, it should spawn a sub process that calls the `bin/ai` s
cript, including various arguments (leave a placeholder for args, I'll fill them in later)
.
4. Now we just go through the conversation that is parsed out of the fixture text file. Th
e fixture text file will be a back and forth between Dave and Bob, so parse each entry i.e
. like something this dotall regex: `/(^|\n)(Dave|Bob):\n(.*)(\nDave|\nBob|$)`. Using the
conversation entries, send the first one as the input prompt text for the sub process scri
pt we just spawed (which is a repl). Be sure to strip the user name labels from the entry.

5. After sending the first one, we are going to have to wait until the entire response is
streamed back (in this case you should look for the string "TESTING: RESPONSE COMPLETE").
Once it is complete, compare the output the sub processed printed to the next entry in the
fixture conversation entries (which *should* be from Bob, since the first will always be
from Dave)
6. If it differs, or the process exits badly or has stderr, then fail the test. If it is t
he same, pass the test
