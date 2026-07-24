import re
from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, Any, cast

from state import DEFAULT_VERSION
from versions import (
    APOCRYPHA_BOOK_DATA,
    APOCRYPHA_BOOK_SLUGS,
    LDS_STANDARD_WORKS_BOOK_DATA,
    VERSION_PROVIDERS,
    VERSION_SUPPORTED_BOOK_SLUGS,
    VERSIONS,
    format_version_label,
)

_RuntimeMessageEntity: type[Any]
_RuntimeMessageEntityType: type[Any]
_RuntimeMessageLimit: Any

try:
    telegram_module = import_module("telegram")
    telegram_constants = import_module("telegram.constants")
except (
    ImportError
):  # pragma: no cover - exercised only in dependency-missing environments

    class _FallbackMessageEntityType:
        BOLD = "bold"
        EXPANDABLE_BLOCKQUOTE = "expandable_blockquote"
        TEXT_LINK = "text_link"

    @dataclass(frozen=True)
    class _FallbackMessageEntity:
        type: str
        offset: int
        length: int
        url: str | None = None

        @staticmethod
        def adjust_message_entities_to_utf_16(
            text: str, entities: Sequence[_FallbackMessageEntity]
        ) -> Sequence[_FallbackMessageEntity]:
            return entities

    _RuntimeMessageEntity = _FallbackMessageEntity
    _RuntimeMessageEntityType = _FallbackMessageEntityType
else:
    _RuntimeMessageEntity = telegram_module.MessageEntity
    _RuntimeMessageEntityType = telegram_constants.MessageEntityType
    _RuntimeMessageLimit = telegram_constants.MessageLimit

if TYPE_CHECKING:
    from telegram import MessageEntity
    from telegram.constants import MessageEntityType, MessageLimit
else:
    MessageEntity = Any
    MessageEntityType = Any
    MessageLimit = Any


def ensure_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    return str(value)


def build_bot_handle(application: Any) -> str:
    username = application.bot.username or "scripturebot"
    return f"@{username}"


TELEGRAM_MESSAGE_LIMIT = (
    int(_RuntimeMessageLimit.MAX_TEXT_LENGTH)
    if "_RuntimeMessageLimit" in globals()
    else 4096
)
INLINE_CONTINUATION_NOTICE = "…continued; use /get for the full passage."

SUPERSCRIPT_TRANSLATION = str.maketrans(
    {
        "0": "⁰",
        "1": "¹",
        "2": "²",
        "3": "³",
        "4": "⁴",
        "5": "⁵",
        "6": "⁶",
        "7": "⁷",
        "8": "⁸",
        "9": "⁹",
        "-": "⁻",
    }
)


def to_sup(text: str) -> str:
    return text.translate(SUPERSCRIPT_TRANSLATION)


def format_numbered_verse_text(verse_number: int | str, text: str) -> str:
    verse_text = ensure_text(text).strip()
    if not verse_text:
        return ""
    return f"{to_sup(str(verse_number))} {verse_text}"


def superscript_leading_verse_numbers(text: str) -> str:
    normalized = ensure_text(text).strip()
    if not normalized:
        return ""
    return re.sub(
        r"(?m)^(\d+(?:-\d+)?)\s+",
        lambda match: f"{to_sup(match.group(1))} ",
        normalized,
    )


def _build_passage_message(
    header: str,
    body: str,
    *,
    include_header: bool = True,
    header_url: str | None = None,
) -> tuple[str, Sequence[MessageEntity]]:
    header = header.strip()
    body = body.strip()
    if include_header:
        message_text = f"{header}\n{body}" if body else header
        entities = [
            _RuntimeMessageEntity(
                type=_RuntimeMessageEntityType.BOLD, offset=0, length=len(header)
            )
        ]
        if header_url:
            entities.append(
                _RuntimeMessageEntity(
                    type=_RuntimeMessageEntityType.TEXT_LINK,
                    offset=0,
                    length=len(header),
                    url=header_url,
                )
            )
    else:
        message_text = body
        entities = []

    if body:
        body_offset = len(header) + 1 if include_header else 0
        entities.append(
            _RuntimeMessageEntity(
                type=_RuntimeMessageEntityType.EXPANDABLE_BLOCKQUOTE,
                offset=body_offset,
                length=len(body),
            )
        )
    utf16_entities = _RuntimeMessageEntity.adjust_message_entities_to_utf_16(
        message_text, entities
    )
    return message_text, cast(Sequence[MessageEntity], utf16_entities)


def format_passage_entities(
    text: str, header_url: str | None = None
) -> tuple[str, Sequence[MessageEntity]]:
    blocks = text.split("\n\n", 1)
    if len(blocks) == 2:
        header, body = blocks
    else:
        header, body = text, ""
    return _build_passage_message(header, body, header_url=header_url)


def format_passage_chunks(
    text: str, header_url: str | None = None
) -> list[tuple[str, Sequence[MessageEntity]]]:
    blocks = text.split("\n\n", 1)
    if len(blocks) == 2:
        header, body = blocks
    else:
        header, body = text, ""

    full_message, full_entities = _build_passage_message(
        header, body, header_url=header_url
    )
    if len(full_message) <= TELEGRAM_MESSAGE_LIMIT:
        return [(full_message, full_entities)]

    if not body:
        return [(full_message[:TELEGRAM_MESSAGE_LIMIT], full_entities)]

    chunks: list[tuple[str, Sequence[MessageEntity]]] = []
    paragraphs = [
        paragraph.strip() for paragraph in body.split("\n\n") if paragraph.strip()
    ]
    if not paragraphs:
        paragraphs = [body.strip()]

    current_parts: list[str] = []
    current_header = True
    for paragraph in paragraphs:
        candidate_parts = current_parts + [paragraph]
        candidate_body = "\n\n".join(candidate_parts)
        candidate_text, candidate_entities = _build_passage_message(
            header,
            candidate_body,
            include_header=current_header,
            header_url=header_url if current_header else None,
        )
        if len(candidate_text) <= TELEGRAM_MESSAGE_LIMIT:
            current_parts = candidate_parts
            current_chunk = (candidate_text, candidate_entities)
            continue

        if current_parts:
            chunks.append(current_chunk)
            current_parts = []
            current_header = False

        if len(paragraph) <= TELEGRAM_MESSAGE_LIMIT:
            current_parts = [paragraph]
            current_chunk = _build_passage_message(
                header,
                paragraph,
                include_header=current_header,
                header_url=header_url if current_header else None,
            )
            continue

        lines = paragraph.splitlines() or [paragraph]
        line_buffer: list[str] = []
        for line in lines:
            line_candidate = "\n".join(line_buffer + [line]).strip()
            line_text, line_entities = _build_passage_message(
                header,
                line_candidate,
                include_header=current_header,
                header_url=header_url if current_header else None,
            )
            if len(line_text) <= TELEGRAM_MESSAGE_LIMIT:
                line_buffer.append(line)
                current_chunk = (line_text, line_entities)
                continue

            if line_buffer:
                chunks.append(current_chunk)
                current_header = False
                line_buffer = []

            remaining = line.strip()
            available = TELEGRAM_MESSAGE_LIMIT - (
                len(header) + 1 if current_header else 0
            )
            while remaining:
                piece = remaining[:available].rstrip()
                chunk_text, chunk_entities = _build_passage_message(
                    header,
                    piece,
                    include_header=current_header,
                    header_url=header_url if current_header else None,
                )
                chunks.append((chunk_text, chunk_entities))
                current_header = False
                remaining = remaining[len(piece) :].lstrip()

        current_parts = ["\n".join(line_buffer).strip()] if line_buffer else []

    if current_parts:
        final_body = "\n\n".join(current_parts)
        chunks.append(
            _build_passage_message(
                header,
                final_body,
                include_header=current_header,
                header_url=header_url if current_header else None,
            )
        )
    return chunks


def format_inline_passage_entities(
    text: str, header_url: str | None = None
) -> tuple[str, Sequence[MessageEntity]]:
    chunks = format_passage_chunks(text, header_url=header_url)
    if len(chunks) == 1:
        return chunks[0]

    blocks = text.split("\n\n", 1)
    if len(blocks) == 2:
        header, body = blocks
    else:
        header, body = text, ""

    header = header.strip()
    body = body.strip()
    reserved = len(header) + 2 + len(INLINE_CONTINUATION_NOTICE)
    available = max(0, TELEGRAM_MESSAGE_LIMIT - reserved)
    preview_body = body[:available].rstrip()
    if preview_body and not preview_body.endswith((" ", "\n")):
        preview_body = preview_body.rstrip(" ,;:")

    if preview_body:
        preview_body = f"{preview_body}\n{INLINE_CONTINUATION_NOTICE}"
    else:
        preview_body = INLINE_CONTINUATION_NOTICE

    return _build_passage_message(header, preview_body, header_url=header_url)


def build_passage_header(reference: str, version: str) -> str:
    return f"{reference} {format_version_label(version)}".strip()


def command_list(application: Any) -> str:
    bot_handle = build_bot_handle(application)
    return (
        "/get <reference>\n"
        "/get <reference> <version>\n"
        "/search <keyword>\n"
        "/setdefault <version>\n\n"
        "Examples:\n"
        "/get John 3:16\n"
        "/get 1 cor 13:4-7 NLT\n"
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


APOCRYPHA_SLUG_TO_TITLE: dict[str, str] = {
    book["slug"]: book["title"] for book in APOCRYPHA_BOOK_DATA
}
BOOK_SLUG_SPECIAL_CASES = {
    "revelationofjesuschrist": ("revelation", "Revelation"),
    "songofsongs": ("songofsolomon", "Song of Solomon"),
    "psalms": ("psalm", "Psalm"),
}
BOOK_NAME_ALIASES: dict[str, tuple[str, str]] = {
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
for book in LDS_STANDARD_WORKS_BOOK_DATA:
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


def supported_versions_for_book_slug(book_slug: str) -> frozenset[str]:
    return frozenset(
        version
        for version, book_slugs in VERSION_SUPPORTED_BOOK_SLUGS.items()
        if book_slug in book_slugs
    )


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
    match = re.search(r"(?i)^\s*((?:[1-4]\s+)?[a-z][a-z'&\-\u2014\s]+?)\s+\d", text)
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


def resolve_auto_version(
    version: str, passage: str, *, explicit_version: bool = False
) -> str:
    if explicit_version:
        return version

    requested_book = find_requested_book(passage)
    if requested_book is None:
        return version

    book_slug, _ = requested_book
    supported_versions = supported_versions_for_book_slug(book_slug)
    if len(supported_versions) == 1:
        return next(iter(supported_versions))

    if (
        book_slug in APOCRYPHA_BOOK_SLUGS
        and not version_supports_book_slug(version, book_slug)
        and not version_supports_book_slug("NIV", book_slug)
    ):
        return "NRSVUE"
    return version


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
) -> tuple[str | None, str | None, bool]:
    words = text.split()
    if not words:
        return None, None, False

    first_word = words[0]
    normalized = first_word.split("@", 1)[0].lower()
    if normalized != "/get":
        return None, None, False

    arguments = words[1:]
    if not arguments:
        return default_version, None, False

    if len(arguments) == 1 and arguments[0].upper() in VERSIONS:
        return arguments[0].upper(), None, True

    version = default_version
    explicit_version = False
    if arguments[-1].upper() in VERSIONS:
        version = arguments[-1].upper()
        arguments = arguments[:-1]
        explicit_version = True

    passage = " ".join(arguments).strip()
    if not passage:
        return version, None, explicit_version

    return version, passage, explicit_version


def other_version(current_version: str) -> str:
    return "NIV" if current_version == "NASB" else "NASB"
