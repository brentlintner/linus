# CLI Coding Partner

A python script to provide a repl to a custom gemini llm.

## Dependencies

* [Python 3.9+](https://www.python.org/downloads/)
* [Pipenv](https://pypi.org/project/pipenv/)
* [Gemini](https://aistudio.google.com/app/apikey)

## Setup

```sh
pipenv install
cp .env.example .env
bin/ai
```

## Current Characters

* [Linux Torvalds](docs/background.txt)

## Feature Ideas

* Save history to a tmp file
* Use a context cache and update it as you go (once file is >32K chars)
* With argparser add command to resume the last conversation
* Add a delay argument to cli once it exists
* Have multiple characters and choose one at random (all celebrities or fictional characters on the phone but together)
