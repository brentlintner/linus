# Coding Partner

A CLI based tool that simulates a coding partner by providing "helpful" suggestions and comments.

## Dependencies

* [Python 3.9+](https://www.python.org/downloads/)
* [Pipenv](https://pypi.org/project/pipenv/)
* [Gemini](https://aistudio.google.com/app/apikey)

## Setup

```sh
pipenv install
cp .env.example .env
bin/ai -h
```

## Feature Ideas

* Use a context cache and update it as you go (once file is >32K chars)
* Add a delay argument to cli once it exists
* Have multiple characters and choose one at random (all celebrities or fictional characters on the phone but together)
* Make it easier to distinguish between the user and the character (bold white text?)
* Make it easier to specify a history file (autocomplete)
* Support more advanced REPL (arrow keys, multi-line input, etc.)
* Be able to paste files or snippets, or reference them
* Add "is thinking" terminal logging
