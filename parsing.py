import re
from typing import Any

from state import DEFAULT_VERSION
from versions import (
    APOCRYPHA_BOOK_DATA,
    VERSION_PROVIDERS,
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
    username = application.bot.username or "scripturebot"
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


APOCRYPHA_SLUG_TO_TITLE = {book["slug"]: book["title"] for book in APOCRYPHA_BOOK_DATA}
BOOK_SLUG_SPECIAL_CASES = {
    "revelationofjesuschrist": ("revelation", "Revelation"),
    "songofsongs": ("songofsolomon", "Song of Solomon"),
    "psalms": ("psalm", "Psalm"),
}
BOOK_NAME_ALIASES = {
    "gen": ("genesis", "Genesis"),
    "ge": ("genesis", "Genesis"),
    "ex": ("exodus", "Exodus"),
    "exo": ("exodus", "Exodus"),
    "exod": ("exodus", "Exodus"),
    "lev": ("leviticus", "Leviticus"),
    "num": ("numbers", "Numbers"),
    "deut": ("deuteronomy", "Deuteronomy"),
    "jos": ("joshua", "Joshua"),
    "josh": ("joshua", "Joshua"),
    "judg": ("judges", "Judges"),
    "jdg": ("judges", "Judges"),
    "ps": ("psalm", "Psalm"),
    "psa": ("psalm", "Psalm"),
    "prov": ("proverbs", "Proverbs"),
    "prv": ("proverbs", "Proverbs"),
    "eccl": ("ecclesiastes", "Ecclesiastes"),
    "ecc": ("ecclesiastes", "Ecclesiastes"),
    "sos": ("songofsolomon", "Song of Solomon"),
    "song": ("songofsolomon", "Song of Solomon"),
    "isa": ("isaiah", "Isaiah"),
    "jer": ("jeremiah", "Jeremiah"),
    "ezek": ("ezekiel", "Ezekiel"),
    "dan": ("daniel", "Daniel"),
    "hos": ("hosea", "Hosea"),
    "obad": ("obadiah", "Obadiah"),
    "mic": ("micah", "Micah"),
    "hab": ("habakkuk", "Habakkuk"),
    "zep": ("zephaniah", "Zephaniah"),
    "hag": ("haggai", "Haggai"),
    "zech": ("zechariah", "Zechariah"),
    "mal": ("malachi", "Malachi"),
    "mt": ("matthew", "Matthew"),
    "matt": ("matthew", "Matthew"),
    "mk": ("mark", "Mark"),
    "mrk": ("mark", "Mark"),
    "lk": ("luke", "Luke"),
    "jn": ("john", "John"),
    "jhn": ("john", "John"),
    "acts": ("acts", "Acts"),
    "ac": ("acts", "Acts"),
    "rom": ("romans", "Romans"),
    "ro": ("romans", "Romans"),
    "1co": ("1corinthians", "1 Corinthians"),
    "2co": ("2corinthians", "2 Corinthians"),
    "gal": ("galatians", "Galatians"),
    "eph": ("ephesians", "Ephesians"),
    "php": ("philippians", "Philippians"),
    "phil": ("philippians", "Philippians"),
    "col": ("colossians", "Colossians"),
    "1th": ("1thessalonians", "1 Thessalonians"),
    "2th": ("2thessalonians", "2 Thessalonians"),
    "1ti": ("1timothy", "1 Timothy"),
    "2ti": ("2timothy", "2 Timothy"),
    "phm": ("philemon", "Philemon"),
    "heb": ("hebrews", "Hebrews"),
    "jas": ("james", "James"),
    "1pe": ("1peter", "1 Peter"),
    "2pe": ("2peter", "2 Peter"),
    "1jn": ("1john", "1 John"),
    "2jn": ("2john", "2 John"),
    "3jn": ("3john", "3 John"),
    "jud": ("jude", "Jude"),
    "rev": ("revelation", "Revelation"),
    "re": ("revelation", "Revelation"),
}
for book in APOCRYPHA_BOOK_DATA:
    for alias in book["aliases"]:
        BOOK_NAME_ALIASES[re.sub(r"[^a-z0-9]+", "", alias.lower())] = (
            book["slug"],
            book["title"],
        )


def get_version_provider(version: str) -> str | None:
    return VERSION_PROVIDERS.get(version.upper())


def supported_book_slugs(version: str) -> frozenset[str]:
    return VERSION_SUPPORTED_BOOK_SLUGS.get(version.upper(), frozenset())


def version_supports_book_slug(version: str, book_slug: str) -> bool:
    return book_slug in supported_book_slugs(version)


def normalize_book_name(book_name: str) -> tuple[str | None, str]:
    collapsed = re.sub(r"[^a-z0-9]+", "", book_name.lower())
    if collapsed in BOOK_NAME_ALIASES:
        return BOOK_NAME_ALIASES[collapsed]
    if collapsed in BOOK_SLUG_SPECIAL_CASES:
        return BOOK_SLUG_SPECIAL_CASES[collapsed]

    normalized_title = " ".join(part for part in book_name.split()).strip()
    if not collapsed:
        return None, normalized_title
    return collapsed, normalized_title


def extract_leading_book_name(text: str) -> str | None:
    match = re.search(r"(?i)^\s*((?:[1-4]\s+)?[a-z][a-z'\s]+?)\s+\d", text)
    if match:
        return " ".join(match.group(1).split()).strip()

    compact_match = re.search(r"(?i)^\s*([1-4]?[a-z]{2,})(?=\d)", text)
    if compact_match:
        return compact_match.group(1).strip()

    return None


def find_requested_book(text: str) -> tuple[str, str] | None:
    book_name = extract_leading_book_name(
        text.lower().replace("revelations", "revelation")
    )
    if book_name is None:
        return None

    slug, title = normalize_book_name(book_name.title())
    if slug is None:
        return None
    return slug, title


def version_supports_passage(version: str, passage: str) -> tuple[bool, str | None]:
    requested_book = find_requested_book(passage)
    if requested_book is None:
        return True, None

    book_slug, book_title = requested_book
    return version_supports_book_slug(version, book_slug), book_title


def canonicalize_reference(text: str) -> str:
    normalized = ensure_text(text).strip()
    if not normalized:
        return ""

    book_name = extract_leading_book_name(
        normalized.lower().replace("revelations", "revelation")
    )
    if book_name:
        _, canonical_title = normalize_book_name(book_name.title())
        normalized = re.sub(
            rf"(?i)^\s*{re.escape(book_name)}",
            canonical_title,
            normalized,
            count=1,
        )

    normalized = re.sub(r"^((?:[1-4]\s+)?[A-Za-z ]+?)(\d)", r"\1 \2", normalized)
    normalized = re.sub(r"\s*:\s*", ":", normalized)
    normalized = re.sub(r"\s*-\s*", "-", normalized)
    normalized = " ".join(normalized.split())
    return normalized


def normalize_reference_lookup_key(text: str) -> str:
    normalized = canonicalize_reference(text)
    if not normalized:
        return ""
    return normalized.lower()


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
