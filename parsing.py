import re
from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, Any, cast

from state import DEFAULT_BIBLE_VERSION
from versions import (
    APOCRYPHA_BOOK_DATA,
    BOOKS,
    LDS_STANDARD_WORKS_BOOK_DATA,
    LDS_STANDARD_WORKS_BOOK_SLUGS,
    NONCANON_BOOK_SLUGS,
    SEFARIA_EXTRA_BOOK_DATA,
    VERSION_PROVIDERS,
    VERSION_SUPPORTED_BOOK_SLUGS,
    ScriptureSystemId,
    format_version_label,
    get_version_system,
    resolve_version_code,
)

type VersionFallback = tuple[str, ...]
type VersionSelection = tuple[VersionFallback, ...]

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
PREFERRED_NONCANON_VERSION_BY_BOOK_SLUG = {
    "jubilees": "CHARLES",
    "letterofaristeas": "ARISTEAS",
    "megillatantiochus": "OPENSID",
    "psalm154": "ESHEL",
    "testamentsofthetwelvepatriarchs": "CHARLES",
}

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
SUPERSCRIPT_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"
SUPERSCRIPT_TO_DIGITS = str.maketrans(SUPERSCRIPT_DIGITS, "0123456789")


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


def format_parallel_passage_entities(
    passages: Sequence[tuple[str, str | None]],
) -> tuple[str, Sequence[MessageEntity]] | None:
    """Format several passages into one message, if Telegram can accept it."""

    message_parts: list[str] = []
    entities: list[Any] = []
    offset = 0
    for index, (text, header_url) in enumerate(passages):
        blocks = text.split("\n\n", 1)
        header, body = (blocks[0], blocks[1]) if len(blocks) == 2 else (text, "")
        header = header.strip()
        body = body.strip()
        if index:
            separator = "\n"
            message_parts.append(separator)
            offset += len(separator)

        message_parts.append(header)
        entities.append(
            _RuntimeMessageEntity(
                type=_RuntimeMessageEntityType.BOLD, offset=offset, length=len(header)
            )
        )
        if header_url:
            entities.append(
                _RuntimeMessageEntity(
                    type=_RuntimeMessageEntityType.TEXT_LINK,
                    offset=offset,
                    length=len(header),
                    url=header_url,
                )
            )
        offset += len(header)

        if body:
            message_parts.append("\n")
            offset += 1
            message_parts.append(body)
            entities.append(
                _RuntimeMessageEntity(
                    type=_RuntimeMessageEntityType.EXPANDABLE_BLOCKQUOTE,
                    offset=offset,
                    length=len(body),
                )
            )
            offset += len(body)

    message_text = "".join(message_parts)
    if len(message_text) > TELEGRAM_MESSAGE_LIMIT:
        return None
    utf16_entities = _RuntimeMessageEntity.adjust_message_entities_to_utf_16(
        message_text, entities
    )
    return message_text, cast(Sequence[MessageEntity], utf16_entities)


def _chunk_header(header: str, body: str) -> str:
    """Build a reference header for the verses that occur in one message chunk."""

    verse_matches = list(re.finditer(f"[{SUPERSCRIPT_DIGITS}]+", body))
    chapter_match = re.search(r"(?m)^(\d+)\s+", body)
    if not verse_matches and chapter_match is None:
        return header

    chapter_starts_chunk = chapter_match is not None and (
        not verse_matches or chapter_match.start() < verse_matches[0].start()
    )
    first_verse = (
        "1"
        if chapter_starts_chunk
        else verse_matches[0].group().translate(SUPERSCRIPT_TO_DIGITS)
    )
    last_verse = (
        verse_matches[-1].group().translate(SUPERSCRIPT_TO_DIGITS)
        if verse_matches
        else "1"
    )
    reference, separator, version = header.rpartition(" ")
    if not separator:
        return header

    reference_match = re.match(r"^(.*?)(\d+)(?::|$)", reference)
    if reference_match is None:
        chapter_reference = reference
    elif chapter_match is None:
        chapter_reference = f"{reference_match.group(1)}{reference_match.group(2)}"
    else:
        chapter_reference = f"{reference_match.group(1)}{chapter_match.group(1)}"
    verse_range = (
        first_verse if first_verse == last_verse else f"{first_verse}-{last_verse}"
    )
    return f"{chapter_reference}:{verse_range} {version}"


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

    def make_chunk(chunk_body: str) -> tuple[str, Sequence[MessageEntity]]:
        return _build_passage_message(
            _chunk_header(header, chunk_body), chunk_body, header_url=header_url
        )

    paragraphs = [
        paragraph.strip() for paragraph in body.split("\n\n") if paragraph.strip()
    ]
    if not paragraphs:
        paragraphs = [body.strip()]

    current_parts: list[str] = []
    for paragraph in paragraphs:
        candidate_parts = current_parts + [paragraph]
        candidate_body = "\n\n".join(candidate_parts)
        candidate_text, candidate_entities = make_chunk(candidate_body)
        if len(candidate_text) <= TELEGRAM_MESSAGE_LIMIT:
            current_parts = candidate_parts
            current_chunk = (candidate_text, candidate_entities)
            continue

        if current_parts:
            chunks.append(current_chunk)
            current_parts = []

        if len(paragraph) <= TELEGRAM_MESSAGE_LIMIT:
            current_parts = [paragraph]
            current_chunk = make_chunk(paragraph)
            continue

        lines = paragraph.splitlines() or [paragraph]
        line_buffer: list[str] = []
        for line in lines:
            line_candidate = "\n".join(line_buffer + [line]).strip()
            line_text, line_entities = make_chunk(line_candidate)
            if len(line_text) <= TELEGRAM_MESSAGE_LIMIT:
                line_buffer.append(line)
                current_chunk = (line_text, line_entities)
                continue

            if line_buffer:
                chunks.append(current_chunk)
                line_buffer = []

            remaining = line.strip()
            available = TELEGRAM_MESSAGE_LIMIT - len(header) - 1
            while remaining:
                piece = remaining[:available].rstrip()
                chunk_text, chunk_entities = make_chunk(piece)
                chunks.append((chunk_text, chunk_entities))
                remaining = remaining[len(piece) :].lstrip()

        current_parts = ["\n".join(line_buffer).strip()] if line_buffer else []

    if current_parts:
        final_body = "\n\n".join(current_parts)
        chunks.append(make_chunk(final_body))
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
        "/get <reference> <fallbacks>&<parallel versions>\n"
        "/search <keyword>\n"
        "/setdefault <version selection>\n\n"
        "/linkembeds on|off\n\n"
        "Examples:\n"
        "/get John 3:16\n"
        "/get 1 cor 13:4-7 NLT\n"
        "/get 1 Maccabees 1 NIV,NRSVue&GNADC\n"
        "/search the greatest commandment\n"
        "/setdefault NASB\n"
        "/setdefault NIV,NRSVue&GNADC\n\n"
        f"Inline mode:\n{bot_handle} john 3:16\n"
        f"{bot_handle} 1co13 nasb"
    )


def build_passage_from_ref(ref) -> str:
    book = ref[0]
    if book == "Revelation of Jesus Christ":
        book = "Revelation"
    return f"{book} {ref[1]}:{ref[2]}-{ref[3]}:{ref[4]}"


def single_version_selection(version: str) -> VersionSelection:
    return ((version,),)


def coerce_version_selection(value: str | VersionSelection) -> VersionSelection:
    if isinstance(value, str):
        return single_version_selection(value)
    return value


def parse_version_selection(token: str) -> VersionSelection | None:
    """Parse ordered fallback groups joined by ``&``.

    Within a group, comma-separated versions are tried left-to-right. Groups are
    fetched in parallel-display order.
    """

    groups = token.split("&")
    if not groups or any(not group for group in groups):
        return None

    selection: list[VersionFallback] = []
    for group in groups:
        candidates = group.split(",")
        if not candidates or any(not candidate for candidate in candidates):
            return None
        resolved = tuple(resolve_version_code(candidate) for candidate in candidates)
        if any(version is None for version in resolved):
            return None
        selection.append(tuple(version for version in resolved if version is not None))
    return tuple(selection)


def format_version_selection(selection: VersionSelection) -> str:
    return " & ".join(" → ".join(group) for group in selection)


def parse_reference_version_query(
    text: str, default_version: str | VersionSelection = DEFAULT_BIBLE_VERSION
) -> tuple[VersionSelection, str, bool]:
    normalized = ensure_text(text).strip()
    if not normalized:
        return coerce_version_selection(default_version), "", False

    words = normalized.split()
    selection = parse_version_selection(words[-1]) if len(words) > 1 else None
    if selection is not None:
        return selection, " ".join(words[:-1]).strip(), True

    return coerce_version_selection(default_version), normalized, False


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
for book in SEFARIA_EXTRA_BOOK_DATA:
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


def get_book_scripture_system(book_slug: str) -> ScriptureSystemId:
    return "lds" if book_slug in LDS_STANDARD_WORKS_BOOK_SLUGS else "bible"


def get_passage_scripture_system(passage: str) -> ScriptureSystemId | None:
    requested_book = find_requested_book(passage)
    if requested_book is None:
        return None
    book_slug, _ = requested_book
    return get_book_scripture_system(book_slug)


def supported_book_slugs(version: str) -> frozenset[str]:
    return VERSION_SUPPORTED_BOOK_SLUGS.get(version.upper(), frozenset())


def version_supports_book_slug(version: str, book_slug: str) -> bool:
    return book_slug in supported_book_slugs(version)


def supported_versions_for_book_slug(
    book_slug: str, *, scripture_system: ScriptureSystemId | None = None
) -> frozenset[str]:
    return frozenset(
        version
        for version, book_slugs in VERSION_SUPPORTED_BOOK_SLUGS.items()
        if book_slug in book_slugs
        and (
            scripture_system is None or get_version_system(version) == scripture_system
        )
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
    for special_case in ("psalm 151", "psalm 154"):
        if re.search(rf"(?i)^\s*{re.escape(special_case)}(?=\s+\d)", text):
            return special_case.title()

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


def is_book_only_request(text: str) -> bool:
    normalized = canonicalize_reference(text)
    if not normalized:
        return False

    collapsed = re.sub(r"[^a-z0-9]+", "", normalized.lower())
    if collapsed in BOOK_NAME_ALIASES:
        return True
    return collapsed in BOOK_SLUG_SPECIAL_CASES or collapsed in BOOKS


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
    supported_versions = supported_versions_for_book_slug(
        book_slug, scripture_system=get_book_scripture_system(book_slug)
    )
    if len(supported_versions) == 1:
        return next(iter(supported_versions))

    if book_slug in NONCANON_BOOK_SLUGS and not version_supports_book_slug(
        version, book_slug
    ):
        if version_supports_book_slug("NRSVUE", book_slug):
            return "NRSVUE"
        preferred_version = PREFERRED_NONCANON_VERSION_BY_BOOK_SLUG.get(book_slug)
        if preferred_version and preferred_version in supported_versions:
            return preferred_version
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
    text: str, default_version: str | VersionSelection = DEFAULT_BIBLE_VERSION
) -> tuple[VersionSelection | None, str | None, bool]:
    words = text.split()
    if not words:
        return None, None, False

    first_word = words[0]
    normalized = first_word.split("@", 1)[0].lower()
    if normalized != "/get":
        return None, None, False

    arguments = words[1:]
    if not arguments:
        return coerce_version_selection(default_version), None, False

    selection = parse_version_selection(arguments[0]) if len(arguments) == 1 else None
    if selection is not None:
        return selection, None, True

    selection = coerce_version_selection(default_version)
    explicit_version = False
    parsed_selection = parse_version_selection(arguments[-1])
    if parsed_selection is not None:
        selection = parsed_selection
        arguments = arguments[:-1]
        explicit_version = True

    passage = " ".join(arguments).strip()
    if not passage:
        return selection, None, explicit_version

    return selection, passage, explicit_version


def other_version(current_version: str) -> str:
    return "NIV" if current_version == "NASB" else "NASB"
