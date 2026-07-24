import re
from typing import Any

from state import DEFAULT_VERSION
from versions import (
    APOCRYPHA_BOOK_DATA,
    APOCRYPHA_VERSION_CODES,
    VERSION_PROVIDERS,
    VERSION_SUPPORTED_APOCRYPHA_BOOKS,
    VERSION_SUPPORTED_BOOK_SLUGS,
    VERSIONS,
)


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


def _compile_alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias)
    escaped = escaped.replace(r"\ ", r"\s+")
    return re.compile(rf"(?i)\b{escaped}\b")


APOCRYPHA_ALIAS_PATTERNS = [
    (_compile_alias_pattern(alias), book["title"])
    for book in APOCRYPHA_BOOK_DATA
    for alias in book["aliases"]
]
APOCRYPHA_ALIAS_PATTERNS.sort(key=lambda item: len(item[0].pattern), reverse=True)
APOCRYPHA_SLUG_TO_TITLE = {book["slug"]: book["title"] for book in APOCRYPHA_BOOK_DATA}


def find_apocrypha_book(text: str) -> str | None:
    for pattern, title in APOCRYPHA_ALIAS_PATTERNS:
        if pattern.search(text):
            return title
    return None


def passage_uses_apocrypha(text: str) -> bool:
    return find_apocrypha_book(text) is not None


def version_supports_apocrypha(version: str) -> bool:
    return version.upper() in APOCRYPHA_VERSION_CODES


def supported_apocrypha_books(version: str) -> frozenset[str]:
    return VERSION_SUPPORTED_APOCRYPHA_BOOKS.get(version.upper(), frozenset())


def version_supports_apocrypha_book(version: str, book_title: str) -> bool:
    return book_title in supported_apocrypha_books(version)


def get_version_provider(version: str) -> str | None:
    return VERSION_PROVIDERS.get(version.upper())


def supported_book_slugs(version: str) -> frozenset[str]:
    return VERSION_SUPPORTED_BOOK_SLUGS.get(version.upper(), frozenset())


def version_supports_book_slug(version: str, book_slug: str) -> bool:
    return book_slug in supported_book_slugs(version)


def parse_apocrypha_reference(text: str) -> str | None:
    for pattern, title in APOCRYPHA_ALIAS_PATTERNS:
        match = re.search(
            rf"(?i)\b{pattern.pattern[4:-2]}\b\s+(\d+)(?::(\d+)(?:-(\d+)(?::(\d+))?)?)?",
            text,
        )
        if not match:
            continue

        start_chapter = match.group(1)
        start_verse = match.group(2)
        end_number = match.group(3)
        end_verse = match.group(4)

        if start_verse is None:
            return f"{title} {start_chapter}"
        if end_number is None:
            return f"{title} {start_chapter}:{start_verse}"
        if end_verse is None:
            return f"{title} {start_chapter}:{start_verse}-{end_number}"
        return f"{title} {start_chapter}:{start_verse}-{end_number}:{end_verse}"
    return None


def decode_linked_reference(reference: str) -> str:
    for slug, title in sorted(
        APOCRYPHA_SLUG_TO_TITLE.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if reference.lower().startswith(slug):
            remainder = reference[len(slug) :].replace("V", ":")
            if remainder:
                return f"{title} {remainder}"
            return title
    return reference.replace("V", ":")


def parse_get_request(
    text: str, default_version: str = DEFAULT_VERSION
) -> tuple[str | None, str | None]:
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
