# scripturebot

Telegram bot built on `python-telegram-bot` that fetches scripture passages from BibleGateway, Bible.com, Sefaria, LDS scripture pages, and optional local/offline files.

This repository now uses `uv` for dependency management.

The `uv.lock` file should be committed to version control for reproducible installs.

Setup:

- `uv sync`

Basic commands:

- `uv run python -m py_compile scripturebot.py bot.py handlers.py config.py state.py parsing.py services/bible_gateway.py services/lds_scriptures.py versions.py`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run python scripturebot.py`
- `uv run python -m unittest discover -s tests`

Configuration:

- set `TOKEN` in the environment, or provide a local `secrets.py`
- optional: `ADMIN_ID`
- optional: `BOTFAMILY_HASH`
- optional: `OFFLINE_BIBLES_PATH`
- optional: `OFFLINE_ONLY=1`

Runtime model:

- the bot now runs with `python-telegram-bot` long polling
- BibleGateway, Bible.com, Sefaria, and LDS scraping use async `httpx`
- Book of Mormon, Doctrine and Covenants, and Pearl of Great Price passages are fetched from the official Church scripture pages under versions `BOM`, `DC`, and `PGP`
- Bible.com-backed Arabic versions include `GNA2025`, `GNADC25`, `TMA`, `TMA-C`, and `TKA`
- Sefaria-backed versions support JPS-family texts and additional apocrypha not available on BibleGateway
- optional local/offline passage files are checked before remote providers
- chat and user state is persisted locally in `scripturebot-state.pkl`

Project layout:

- `scripturebot.py`: thin entrypoint
- `bot.py`: PTB application wiring
- `handlers.py`: command, conversation, inline, and message handlers
- `services/bible_gateway.py`: BibleGateway scraping/parsing
- `services/bible_com.py`: Bible.com / YouVersion scraping/parsing
- `services/sefaria.py`: Sefaria scraping/parsing
- `services/lds_scriptures.py`: LDS standard works scraping/parsing
- `services/local_bible.py`: optional local/offline passage loading
- `parsing.py`: command parsing helpers
- `versions.py`: version metadata and book/version support tables
- `state.py`: constants and lightweight state models
- `config.py`: environment and local-secret loading
- `tests/`: parsing and scraper normalization tests

Notes:

- this codebase uses `python-telegram-bot` instead of the old `webapp2` and Google App Engine services stack.
- `/get` uses trailing-version syntax: `/get John 3:16 NLT`
- combine versions with ordered fallbacks and parallels: `/get 1 Maccabees 1 NIV,NRSVue&GNADC` tries `NIV`, then `NRSVue`, and also returns `GNADC`; commas denote fallbacks and `&` denotes separately returned versions
- the same syntax works for defaults: `/setdefault NIV,NRSVue&GNADC`; all versions in one default selection must belong to the same scripture system
- chapter requests are supported, but whole-book requests are not
- Bible.com Arabic examples: `/get Matthew 3 TMA`, `/get Tobit 9 GNADC25`, `/get 2 Maccabees 6 TKA`
- LDS scripture examples: `/get 1 Nephi 3:7 BOM`, `/get D&C 1:1 DC`, `/get Abraham 3:22 PGP`
- apocrypha defaults to `NRSVue` when available and otherwise falls back to supported Sefaria-backed versions
- Sefaria/apocrypha examples: `/get Tobit 4:7 NABRE`, `/get 3 Maccabees 1:1`, `/get Jubilees 1:1`
- accepted Bible.com version aliases include `GNADC`, `TMA-C`, `TKA`, `TKʿ`, and `ت.ك.ع`
- offline passage files live under `OFFLINE_BIBLES_PATH` as `<VERSION>.json`
- each offline JSON file should be an object mapping references like `John 3:16` to either a string, a list of paragraph strings, or an object with `title`, `text`, and optional `description`
