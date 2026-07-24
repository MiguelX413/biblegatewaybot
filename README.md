# scripturebot

Telegram bot built on `python-telegram-bot` that fetches Bible passages from biblegateway.com.

This repository now uses `uv` for dependency management.

The `uv.lock` file should be committed to version control for reproducible installs.

Setup:

- `uv sync`

Basic commands:

- `uv run python -m py_compile scripturebot.py bot.py handlers.py config.py state.py parsing.py services/bible_gateway.py versions.py`
- `uv run scripturebot`
- `uv run python -m unittest discover -s tests`

Configuration:

- set `TOKEN` in the environment, or provide a local `secrets.py`
- optional: `ADMIN_ID`
- optional: `BOTFAMILY_HASH`
- optional: `OFFLINE_BIBLES_PATH`
- optional: `OFFLINE_ONLY=1`

Runtime model:

- the bot now runs with `python-telegram-bot` long polling
- bible scraping uses async `httpx`
- optional local/offline passage files are checked before remote providers
- chat and user state is persisted locally in `scripturebot-state.pkl`

Project layout:

- `scripturebot.py`: thin entrypoint
- `bot.py`: PTB application wiring
- `handlers.py`: command, conversation, inline, and message handlers
- `services/bible_gateway.py`: BibleGateway and BibleHub scraping/parsing
- `services/local_bible.py`: optional local/offline passage loading
- `parsing.py`: command parsing helpers
- `state.py`: constants and lightweight state models
- `config.py`: environment and local-secret loading
- `tests/`: parsing and scraper normalization tests

Notes:

- this codebase uses `python-telegram-bot` instead of the old `webapp2` and Google App Engine services stack.
- offline passage files live under `OFFLINE_BIBLES_PATH` as `<VERSION>.json`
- each offline JSON file should be an object mapping references like `John 3:16` to either a string, a list of paragraph strings, or an object with `title`, `text`, and optional `description`
