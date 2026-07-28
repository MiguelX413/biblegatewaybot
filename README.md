# scripturebot

Telegram bot built on `python-telegram-bot` that fetches scripture passages from BibleGateway, Bible.com, Sefaria, LDS scripture pages, AlQuran Cloud, and optional local/offline files.

This repository now uses `uv` for dependency management.

The `uv.lock` file should be committed to version control for reproducible installs.

Setup:

- `uv sync`
- optional faster JSON paths:
  - `uv sync --extra orjson`
  - `uv sync --extra ujson`
  - `uv sync --extra speed`
  - prefers `orjson`, then `ujson`, then stdlib `json`

Basic commands:

- `uv run python -m py_compile scripturebot.py bot.py handlers.py config.py state.py parsing.py services/bible_gateway.py services/lds_scriptures.py versions.py`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run python scripturebot.py`
- `uv run python -m unittest discover -s tests`

Configuration:

- set `TOKEN` in the environment, or copy `secrets.example.py` to a local `secrets.py` and fill it in
- optional: `ADMIN_IDS`
  - in `secrets.py`, may be a Python collection like `{123456789, 987654321}`
  - in environment variables, use a comma-separated string like `123456789,987654321`
- optional: `BOTFAMILY_HASH`
- optional: `OFFLINE_ONLY=1`
- optional: `QURAN_BACKEND` (`auto`, `qf`, or `alquran_cloud`)
- optional: `QF_CLIENT_ID`
- optional: `QF_CLIENT_SECRET`
- optional: `QF_ENV` (`prelive` or `production`)

Runtime model:

- the bot now runs with `python-telegram-bot` long polling
- BibleGateway, Bible.com, Sefaria, LDS, and Qurʾan fetching use async `httpx`
- LDS scripture passages are fetched from the official Church scripture pages under language-based versions such as `LDSENG`, `LDSESP`, `LDSPOR`, `LDSFRA`, and `LDSDEU`
- Bible.com-backed Arabic versions include `GNA2025`, `GNADC25`, `TMA`, `TMA-C`, and `TKA`
- AlQuran Cloud-backed Qurʾan versions include Arabic `QURAN`, English `ṢI` / `QPICK` / `QYUSUF`, Persian `QAYATI` / `QFOOL`, Uzbek `QSODIK`, Urdu `QJAL`, Turkish `QDIYANET`, and Russian `QKULIEV`
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
- `services/alquran_cloud.py`: Qurʾan fetching/parsing via AlQuran Cloud
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
- the default Bible selection is `NIV,NRSVue`, so apocryphal passages unavailable in NIV naturally fall back to NRSVue
- the same syntax works for defaults: `/setdefault NIV,NRSVue&GNADC`; all versions in one default selection must belong to the same scripture system
- Qurʾan examples: `/get Quran 1 QURAN`, `/get Quran 2:255 ṢI`, `/get Quran 112 QPICK`
- `/linkembeds off` or `/linkembeds on` enables or suppresses link previews for passage headers and welcome/source links in the current DM or group; DM settings also apply to that user's inline results
- chapter requests are supported, but whole-book requests are not
- Bible.com Arabic examples: `/get Matthew 3 TMA`, `/get Tobit 9 GNADC25`, `/get 2 Maccabees 6 TKA`
- LDS scripture examples: `/get 1 Nephi 3:7 LDSENG`, `/get D&C 1:1 LDSESP`, `/get Abraham 3:22 LDSFRA`
- apocrypha defaults to `NRSVue` when available and otherwise falls back to supported Sefaria-backed versions
- Sefaria/apocrypha examples: `/get Tobit 4:7 NABRE`, `/get 3 Maccabees 1:1`, `/get Jubilees 1:1`
- offline 1 Enoch example: `/get 1 Enoch 1:1 HERM`
- accepted Bible.com version aliases include `GNADC`, `TMA-C`, `TKA`, `TKʿ`, and `ت.ك.ع`
- offline passage files live under the hardcoded `offline/` directory and are discovered automatically at startup
- offline version-family files live under `offline/<VERSION>/version.json`
- offline one-book-per-file text files live under `offline/<VERSION>/books/`
- version files declare `code`, `name`, `language`, `system`, and optional `aliases`
- book files declare `title`, `slug`, `aliases`, optional `source_url`, and `chapters` or `passages`
- `tools/import_1_enoch_epub.py` converts the Hermeneia 1 Enoch EPUB into `offline/HERM/version.json` and `offline/HERM/books/1enoch.json`, stripping footnote markers entirely
- `tools/import_nets_epub.py` converts the NETS EPUB into `offline/NETS/version.json` and one JSON file per book under `offline/NETS/books/`
