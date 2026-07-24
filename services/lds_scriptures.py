import logging
import re
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from bs4 import BeautifulSoup

from parsing import build_passage_header, format_numbered_verse_text
from state import EMPTY, REQUEST_TIMEOUT_SECONDS, InlinePassageResult

try:
    httpx: Any = import_module("httpx")
except ImportError:  # pragma: no cover - exercised only in dependency-missing envs
    httpx = None


LDS_SCRIPTURES_BASE_URL = "https://www.churchofjesuschrist.org/study/scriptures"


@dataclass(frozen=True)
class LdsBook:
    title: str
    slug: str
    version: str
    collection_path: str
    book_path: str
    chapters: int
    aliases: tuple[str, ...]


LDS_BOOKS: tuple[LdsBook, ...] = (
    LdsBook(
        "1 Nephi",
        "1nephi",
        "BOM",
        "bofm",
        "1-ne",
        22,
        ("1 nephi", "1 ne", "1nephi", "1ne"),
    ),
    LdsBook(
        "2 Nephi",
        "2nephi",
        "BOM",
        "bofm",
        "2-ne",
        33,
        ("2 nephi", "2 ne", "2nephi", "2ne"),
    ),
    LdsBook("Jacob", "jacob", "BOM", "bofm", "jacob", 7, ("jacob", "jac")),
    LdsBook("Enos", "enos", "BOM", "bofm", "enos", 1, ("enos",)),
    LdsBook("Jarom", "jarom", "BOM", "bofm", "jarom", 1, ("jarom",)),
    LdsBook("Omni", "omni", "BOM", "bofm", "omni", 1, ("omni",)),
    LdsBook(
        "Words of Mormon",
        "wordsofmormon",
        "BOM",
        "bofm",
        "w-of-m",
        1,
        ("words of mormon", "wordsofmormon", "w of m", "wom"),
    ),
    LdsBook("Mosiah", "mosiah", "BOM", "bofm", "mosiah", 29, ("mosiah", "mos")),
    LdsBook("Alma", "alma", "BOM", "bofm", "alma", 63, ("alma",)),
    LdsBook("Helaman", "helaman", "BOM", "bofm", "hel", 16, ("helaman", "hel")),
    LdsBook(
        "3 Nephi",
        "3nephi",
        "BOM",
        "bofm",
        "3-ne",
        30,
        ("3 nephi", "3 ne", "3nephi", "3ne"),
    ),
    LdsBook(
        "4 Nephi",
        "4nephi",
        "BOM",
        "bofm",
        "4-ne",
        1,
        ("4 nephi", "4 ne", "4nephi", "4ne"),
    ),
    LdsBook("Mormon", "mormon", "BOM", "bofm", "morm", 9, ("mormon", "morm")),
    LdsBook("Ether", "ether", "BOM", "bofm", "ether", 15, ("ether", "eth")),
    LdsBook("Moroni", "moroni", "BOM", "bofm", "moro", 10, ("moroni", "moro", "mor")),
    LdsBook(
        "Doctrine and Covenants",
        "doctrineandcovenants",
        "DC",
        "dc-testament",
        "dc",
        138,
        (
            "doctrine and covenants",
            "doctrine & covenants",
            "d and c",
            "d&c",
            "dc",
        ),
    ),
    LdsBook("Moses", "moses", "PGP", "pgp", "moses", 8, ("moses",)),
    LdsBook("Abraham", "abraham", "PGP", "pgp", "abr", 5, ("abraham", "abr")),
    LdsBook(
        "Joseph Smith—Matthew",
        "josephsmithmatthew",
        "PGP",
        "pgp",
        "js-m",
        1,
        (
            "joseph smith matthew",
            "joseph smith—matthew",
            "joseph smith-matthew",
            "jsm",
            "js-m",
        ),
    ),
    LdsBook(
        "Joseph Smith—History",
        "josephsmithhistory",
        "PGP",
        "pgp",
        "js-h",
        1,
        (
            "joseph smith history",
            "joseph smith—history",
            "joseph smith-history",
            "jsh",
            "js-h",
        ),
    ),
    LdsBook(
        "Articles of Faith",
        "articlesoffaith",
        "PGP",
        "pgp",
        "a-of-f",
        1,
        ("articles of faith", "a of f", "aof", "a-of-f"),
    ),
)

LDS_BOOK_BY_SLUG = {book.slug: book for book in LDS_BOOKS}


@dataclass(frozen=True)
class LdsReference:
    book: LdsBook
    start_chapter: int
    start_verse: int | None
    end_chapter: int
    end_verse: int | None


def normalize_lds_book_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


LDS_BOOK_BY_ALIAS = {
    normalize_lds_book_name(alias): book for book in LDS_BOOKS for alias in book.aliases
}


def format_reference_title(reference: LdsReference) -> str:
    if (
        reference.start_chapter == reference.end_chapter
        and reference.start_verse is None
        and reference.end_verse is None
    ):
        return f"{reference.book.title} {reference.start_chapter}"

    start = f"{reference.book.title} {reference.start_chapter}"
    if reference.start_verse is not None:
        start = f"{start}:{reference.start_verse}"

    if (
        reference.start_chapter == reference.end_chapter
        and reference.start_verse is not None
        and reference.end_verse == reference.start_verse
    ):
        return start

    if (
        reference.start_chapter == reference.end_chapter
        and reference.end_verse is not None
        and reference.start_verse is not None
    ):
        return f"{start}-{reference.end_verse}"

    end = str(reference.end_chapter)
    if reference.end_verse is not None:
        end = f"{end}:{reference.end_verse}"
    return f"{start}-{end}"


def parse_lds_reference(passage: str) -> LdsReference | None:
    normalized = " ".join(passage.split()).strip()
    if not normalized:
        return None

    match = re.fullmatch(
        r"(?i)(.+?)\s+(\d+)(?::(\d+))?(?:-(?:(\d+):)?(\d+))?$",
        normalized,
    )
    if match is None:
        chapter_match = re.fullmatch(r"(?i)(.+?)\s+(\d+)(?:-(\d+))?$", normalized)
        if chapter_match is None:
            return None

        book_name = normalize_lds_book_name(chapter_match.group(1))
        book = LDS_BOOK_BY_ALIAS.get(book_name)
        if book is None:
            return None

        start_chapter = int(chapter_match.group(2))
        end_chapter = int(chapter_match.group(3) or start_chapter)
        if not (1 <= start_chapter <= end_chapter <= book.chapters):
            return None
        return LdsReference(book, start_chapter, None, end_chapter, None)

    book_name = normalize_lds_book_name(match.group(1))
    book = LDS_BOOK_BY_ALIAS.get(book_name)
    if book is None:
        return None

    start_chapter = int(match.group(2))
    start_verse = int(match.group(3)) if match.group(3) else None
    if start_verse is None and match.group(4) is None and match.group(5) is not None:
        end_chapter = int(match.group(5))
        end_verse = None
    else:
        end_chapter = int(match.group(4) or start_chapter)
        end_verse = int(match.group(5)) if match.group(5) else start_verse

    if not (1 <= start_chapter <= book.chapters and 1 <= end_chapter <= book.chapters):
        return None
    if end_chapter < start_chapter:
        return None
    if (
        end_chapter == start_chapter
        and start_verse
        and end_verse
        and end_verse < start_verse
    ):
        return None

    return LdsReference(
        book=book,
        start_chapter=start_chapter,
        start_verse=start_verse,
        end_chapter=end_chapter,
        end_verse=end_verse,
    )


def _extract_verse_number(verse_tag) -> int | None:
    verse_number = verse_tag.select_one(".verse-number")
    if verse_number is None:
        return None
    match = re.search(r"\d+", verse_number.get_text(" ", strip=True))
    return int(match.group()) if match else None


def _clean_verse_text(verse_tag) -> str:
    verse_copy = BeautifulSoup(str(verse_tag), "lxml")
    for tag in verse_copy.select(".study-note-ref, .page-break, [data-pointer-type]"):
        tag.decompose()
    verse_number = verse_copy.select_one(".verse-number")
    if verse_number is not None:
        verse_number.extract()
    return " ".join(verse_copy.get_text(" ", strip=True).split())


def parse_passage_html(
    html: str,
    reference: LdsReference,
    *,
    inline_details: bool = False,
) -> str | InlinePassageResult:
    soup = BeautifulSoup(html, "lxml")
    verse_tags = soup.select("p.verse")
    if not verse_tags:
        return EMPTY

    selected_lines: list[str] = []
    for verse_tag in verse_tags:
        verse_number = _extract_verse_number(verse_tag)
        if verse_number is None:
            continue

        if reference.start_verse is not None and verse_number < reference.start_verse:
            continue
        if reference.end_verse is not None and verse_number > reference.end_verse:
            continue

        verse_text = _clean_verse_text(verse_tag)
        if verse_text:
            selected_lines.append(format_numbered_verse_text(verse_number, verse_text))

    if not selected_lines:
        return EMPTY

    header = build_passage_header(
        format_reference_title(reference), reference.book.version
    )
    final_text = "\n\n".join([header, *selected_lines]).strip()
    if not inline_details:
        return final_text

    content = " ".join(final_text.split())
    description = f"{content[:150]}..." if len(content) > 153 else content
    return InlinePassageResult(
        passage=final_text,
        result_id=f"{reference.book.slug}.{reference.start_chapter}/{reference.book.version}",
        title=header,
        description=description,
    )


class LdsScripturesClient:
    def __init__(self, client=None):
        if httpx is None:
            raise RuntimeError("httpx is required to use LdsScripturesClient.")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "scripturebot/1.0"},
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch_text(self, url: str) -> str | None:
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            logging.warning("Error fetching %s: %s", url, exc)
            return None

    async def _get_chapter_html(self, book: LdsBook, chapter: int) -> str | None:
        url = (
            f"{LDS_SCRIPTURES_BASE_URL}/"
            f"{book.collection_path}/{book.book_path}/{chapter}?lang=eng"
        )
        return await self.fetch_text(url)

    async def get_passage(
        self,
        passage: str,
        version: str,
        inline_details: bool = False,
    ) -> str | InlinePassageResult | None:
        reference = parse_lds_reference(passage)
        if reference is None:
            return EMPTY
        if reference.book.version != version.upper():
            return EMPTY

        chapter_outputs: list[str] = []
        for chapter in range(reference.start_chapter, reference.end_chapter + 1):
            chapter_reference = LdsReference(
                book=reference.book,
                start_chapter=chapter,
                start_verse=(
                    reference.start_verse
                    if chapter == reference.start_chapter
                    else None
                ),
                end_chapter=chapter,
                end_verse=(
                    reference.end_verse if chapter == reference.end_chapter else None
                ),
            )
            html = await self._get_chapter_html(reference.book, chapter)
            if html is None:
                return None
            chapter_text = parse_passage_html(
                html, chapter_reference, inline_details=False
            )
            if chapter_text == EMPTY:
                return EMPTY
            chapter_outputs.append(str(chapter_text))

        if len(chapter_outputs) == 1:
            result_text = chapter_outputs[0]
        else:
            header = build_passage_header(format_reference_title(reference), version)
            body_parts: list[str] = []
            for chapter_output in chapter_outputs:
                parts = chapter_output.split("\n\n")
                body_parts.extend(parts[1:] if len(parts) > 1 else parts)
            result_text = "\n\n".join([header, *body_parts]).strip()

        if not inline_details:
            return result_text

        content = " ".join(result_text.split())
        description = f"{content[:150]}..." if len(content) > 153 else content
        return InlinePassageResult(
            passage=result_text,
            result_id=f"{reference.book.slug}.{reference.start_chapter}/{version}",
            title=build_passage_header(format_reference_title(reference), version),
            description=description,
        )
