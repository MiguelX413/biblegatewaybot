# biblegatewaybot

Telegram bot built on `python-telegram-bot` that fetches Bible passages from biblegateway.com.

This repository now uses `uv` for dependency management.

Setup:

- `uv sync`

Basic commands:

- `uv run python -m py_compile biblegatewaybot.py versions.py`
- `uv run biblegatewaybot`

Configuration:

- set `TOKEN` in the environment, or provide a local `secrets.py`
- optional: `ADMIN_ID`
- optional: `BOTFAMILY_HASH`

Runtime model:

- the bot now runs with `python-telegram-bot` long polling
- chat and user state is persisted locally in `bot-state.pkl`
- legacy App Engine files in this repo are no longer the active runtime path

Notes:

- `biblegatewaybot.py` now uses `python-telegram-bot` instead of `webapp2` and Google App Engine services.
- `app.yaml`, `appengine_config.py`, `cron.yaml`, `queue.yaml`, and `index.yaml` are legacy files from the old deployment model.
