from typing import Any

from state import DEFAULT_VERSION
from versions import VERSIONS


def ensure_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    return str(value)


def build_bot_handle(application: Any) -> str:
    username = application.bot.username or "biblegatewaybot"
    return f"@{username}"


def command_list(application: Application) -> str:
    bot_handle = build_bot_handle(application)
    return (
        "/get <reference>\n"
        "/get<version> <reference>\n"
        "/search <keyword>\n"
        "/setdefault <version>\n\n"
        "Examples:\n"
        "/get John 3:16\n"
        "/getNLT 1 cor 13:4-7\n"
        "/search the greatest commandment\n"
        "/setdefault NASB\n\n"
        f"Inline mode:\n{bot_handle} john 3:16\n"
        f"{bot_handle} 1co13 nasb"
    )


def build_passage_from_ref(ref) -> str:
    book = ref[0]
    if book == "Revelation of Jesus Christ":
        book = "Revelation"
    return f"{book} {ref[1]}:{ref[2]}-{ref[3]}:{ref[4]}"


def parse_get_request(text: str, default_version: str = DEFAULT_VERSION) -> tuple[str | None, str | None]:
    words = text.split()
    if not words:
        return None, None

    first_word = words[0]
    normalized = first_word.split("@", 1)[0].lower()
    version = normalized[4:].upper() if len(normalized) > 4 else default_version
    if version not in VERSIONS:
        return None, None

    passage = text[len(first_word) :].strip()
    if not passage:
        return version, None

    first_passage_word = passage.split()[0].upper()
    if (
        len(normalized) == 4
        and first_passage_word in VERSIONS
        and passage[len(first_passage_word) :].strip()
    ):
        version = first_passage_word
        passage = passage[len(first_passage_word) :].strip()

    return version, passage


def other_version(current_version: str) -> str:
    return "NIV" if current_version == "NASB" else "NASB"
