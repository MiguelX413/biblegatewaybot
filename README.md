# biblegatewaybot

Telegram bot built on `python-telegram-bot` that fetches Bible passages from biblegateway.com.

This repository now uses `uv` for dependency management.

The `uv.lock` file should be committed to version control for reproducible installs.

Setup:

- `uv sync`

Basic commands:

- `uv run python -m py_compile biblegatewaybot.py bot.py handlers.py config.py state.py parsing.py services/bible_gateway.py versions.py`
- `uv run biblegatewaybot`
- `uv run python -m unittest discover -s tests`

Configuration:

- set `TOKEN` in the environment, or provide a local `secrets.py`
- optional: `ADMIN_ID`
- optional: `BOTFAMILY_HASH`

Runtime model:

- the bot now runs with `python-telegram-bot` long polling
- bible scraping uses async `httpx`
- chat and user state is persisted locally in `bot-state.pkl`

Project layout:

- `biblegatewaybot.py`: thin entrypoint
- `bot.py`: PTB application wiring
- `handlers.py`: command, conversation, inline, and message handlers
- `services/bible_gateway.py`: BibleGateway and BibleHub scraping/parsing
- `parsing.py`: command parsing helpers
- `state.py`: constants and lightweight state models
- `config.py`: environment and local-secret loading
- `tests/`: parsing and scraper normalization tests

Notes:

- this codebase uses `python-telegram-bot` instead of the old `webapp2` and Google App Engine services stack.
