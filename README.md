# biblegatewaybot

Telegram bot hosted on Google App Engine that fetches Bible passages from biblegateway.com.

This repository now uses `uv` for dependency management.

Setup:

- `uv sync`

Basic commands:

- `uv run python -m py_compile biblegatewaybot.py versions.py`
- `uv run biblegatewaybot`

Notes:

- `biblegatewaybot.py` was updated for Python 3 string and URL handling.
- `app.yaml` still targets the legacy App Engine Python 2.7 runtime. That deployment model has not been migrated in this change.
