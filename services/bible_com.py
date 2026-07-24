import json
import logging
import re
from dataclasses import dataclass
from html import unescape
from importlib import import_module
from typing import Any

from bs4 import BeautifulSoup

from parsing import (
    build_passage_header,
    find_requested_book,
    format_numbered_verse_text,
    superscript_leading_verse_numbers,
)
from state import DEFAULT_VERSION, EMPTY, REQUEST_TIMEOUT_SECONDS, InlinePassageResult

try:
    httpx: Any = import_module("httpx")
except ImportError:  # pragma: no cover - exercised only in dependency-missing envs
    httpx = None


BIBLE_COM_BASE_URL = "https://bible.com/bible"
BIBLE_COM_VERSION_IDS: dict[str, int] = {
    "GNA2025": 67,
    "GNADC25": 1665,
    "TKA": 1981,
    "TMA": 1714,
    "TMA-C": 3275,
}
BIBLE_COM_USFM_BY_BOOK_SLUG: dict[str, str] = {
    "genesis": "GEN",
    "exodus": "EXO",
    "leviticus": "LEV",
    "numbers": "NUM",
    "deuteronomy": "DEU",
    "joshua": "JOS",
    "judges": "JDG",
    "ruth": "RUT",
    "1samuel": "1SA",
    "2samuel": "2SA",
    "1kings": "1KI",
    "2kings": "2KI",
    "1chronicles": "1CH",
    "2chronicles": "2CH",
    "ezra": "EZR",
    "nehemiah": "NEH",
    "esther": "EST",
    "job": "JOB",
    "psalm": "PSA",
    "proverbs": "PRO",
    "ecclesiastes": "ECC",
    "songofsolomon": "SNG",
    "isaiah": "ISA",
    "jeremiah": "JER",
    "lamentations": "LAM",
    "ezekiel": "EZK",
    "daniel": "DAN",
    "hosea": "HOS",
    "joel": "JOL",
    "amos": "AMO",
    "obadiah": "OBA",
    "jonah": "JON",
    "micah": "MIC",
    "nahum": "NAM",
    "habakkuk": "HAB",
    "zephaniah": "ZEP",
    "haggai": "HAG",
    "zechariah": "ZEC",
    "malachi": "MAL",
    "matthew": "MAT",
    "mark": "MRK",
    "luke": "LUK",
    "john": "JHN",
    "acts": "ACT",
    "romans": "ROM",
    "1corinthians": "1CO",
    "2corinthians": "2CO",
    "galatians": "GAL",
    "ephesians": "EPH",
    "philippians": "PHP",
    "colossians": "COL",
    "1thessalonians": "1TH",
    "2thessalonians": "2TH",
    "1timothy": "1TI",
    "2timothy": "2TI",
    "titus": "TIT",
    "philemon": "PHM",
    "hebrews": "HEB",
    "james": "JAS",
    "1peter": "1PE",
    "2peter": "2PE",
    "1john": "1JN",
    "2john": "2JN",
    "3john": "3JN",
    "jude": "JUD",
    "revelation": "REV",
    "tobit": "TOB",
    "judith": "JDT",
    "additionstoesther": "ESG",
    "wisdom": "WIS",
    "sirach": "SIR",
    "baruch": "BAR",
    "letterofjeremiah": "LJE",
    "prayerofazariah": "S3Y",
    "susanna": "SUS",
    "belandthedragon": "BEL",
    "1maccabees": "1MA",
    "2maccabees": "2MA",
}


@dataclass(frozen=True)
class BibleComReference:
    book_slug: str
    book_title: str
    book_usfm: str
    start_chapter: int
    start_verse: int | None
    end_chapter: int
    end_verse: int | None


def normalize_block_text(text: str) -> str:
    return " ".join(unescape(text).split()).strip()


def parse_bible_com_reference(passage: str) -> BibleComReference | None:
    normalized = " ".join(str(passage).split()).strip()
    if not normalized:
        return None

    requested_book = find_requested_book(normalized)
    if requested_book is None:
        return None

    book_slug, book_title = requested_book
    book_usfm = BIBLE_COM_USFM_BY_BOOK_SLUG.get(book_slug)
    if book_usfm is None:
        return None

    match = re.fullmatch(
        r"(?i)(.+?)\s+(\d+)(?::(\d+))?(?:-(?:(\d+):)?(\d+))?$",
        normalized,
    )
    if match is None:
        chapter_match = re.fullmatch(r"(?i)(.+?)\s+(\d+)(?:-(\d+))?$", normalized)
        if chapter_match is None:
            return None
        return BibleComReference(
            book_slug=book_slug,
            book_title=book_title,
            book_usfm=book_usfm,
            start_chapter=int(chapter_match.group(2)),
            start_verse=None,
            end_chapter=int(chapter_match.group(3) or chapter_match.group(2)),
            end_verse=None,
        )

    start_chapter = int(match.group(2))
    start_verse = int(match.group(3)) if match.group(3) else None
    if start_verse is None and match.group(4) is None and match.group(5) is not None:
        end_chapter = int(match.group(5))
        end_verse = None
    else:
        end_chapter = int(match.group(4) or start_chapter)
        end_verse = int(match.group(5)) if match.group(5) else start_verse

    if end_chapter < start_chapter:
        return None
    if (
        end_chapter == start_chapter
        and start_verse
        and end_verse
        and end_verse < start_verse
    ):
        return None

    return BibleComReference(
        book_slug=book_slug,
        book_title=book_title,
        book_usfm=book_usfm,
        start_chapter=start_chapter,
        start_verse=start_verse,
        end_chapter=end_chapter,
        end_verse=end_verse,
    )


def _build_usfm_reference(reference: BibleComReference) -> str:
    base = f"{reference.book_usfm}.{reference.start_chapter}"
    if (
        reference.start_verse is None
        and reference.end_chapter == reference.start_chapter
    ):
        return base
    if (
        reference.start_verse is None
        and reference.end_verse is None
        and reference.end_chapter != reference.start_chapter
    ):
        return base
    if reference.end_chapter == reference.start_chapter:
        if reference.start_verse is None:
            return base
        if reference.end_verse is None or reference.end_verse == reference.start_verse:
            return f"{base}.{reference.start_verse}"
        return f"{base}.{reference.start_verse}-{reference.end_verse}"
    if reference.start_verse is None:
        return base
    if reference.end_verse is None:
        return f"{base}.{reference.start_verse}"
    return (
        f"{base}.{reference.start_verse}-{reference.end_chapter}.{reference.end_verse}"
    )


def build_bible_com_passage_url(
    passage: str, version: str = DEFAULT_VERSION
) -> str | None:
    reference = parse_bible_com_reference(passage)
    version_id = BIBLE_COM_VERSION_IDS.get(version.upper())
    if reference is None or version_id is None:
        return None
    return f"{BIBLE_COM_BASE_URL}/{version_id}/{_build_usfm_reference(reference)}"


def _extract_page_props(html: str) -> dict | None:
    soup = BeautifulSoup(html, "lxml")
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data is None or not next_data.string:
        return None
    try:
        payload = json.loads(next_data.string)
    except json.JSONDecodeError:
        return None
    return payload.get("props", {}).get("pageProps")


def extract_chapter_content(html: str) -> str | None:
    page_props = _extract_page_props(html)
    if page_props is None:
        return None
    chapter_info = page_props.get("chapterInfo") or {}
    content = chapter_info.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    return content


def parse_chapter_content(
    content_html: str,
    *,
    start_verse: int | None = None,
    end_verse: int | None = None,
) -> list[str]:
    soup = BeautifulSoup(content_html, "lxml")
    chapter = soup.select_one(".chapter")
    if chapter is None:
        return []

    blocks: list[str] = []
    pending_headings: list[str] = []
    current_content_index: int | None = None
    for child in chapter.find_all("div", recursive=False):
        classes = set(child.get("class") or [])
        if "label" in classes:
            continue
        if "note" in classes:
            continue
        if "cl" in classes or any(
            css_class.startswith(("ms", "s")) for css_class in classes
        ):
            heading = normalize_block_text(child.get_text(" ", strip=True))
            if heading:
                pending_headings.append(heading)
            continue
        if not classes.intersection({"p", "q", "m", "pi", "li", "pc", "pm", "mi"}):
            continue

        verse_parts: list[str] = []
        for verse in child.select("span.verse[data-usfm]"):
            data_usfm = verse.get("data-usfm", "")
            if not isinstance(data_usfm, str):
                continue
            try:
                verse_number = int(data_usfm.rsplit(".", 1)[-1])
            except ValueError:
                continue
            if start_verse is not None and verse_number < start_verse:
                continue
            if end_verse is not None and verse_number > end_verse:
                continue

            content = verse.select_one("span.content")
            if content is None:
                continue
            text = normalize_block_text(content.get_text(" ", strip=True))
            if not text:
                continue
            verse_parts.append(format_numbered_verse_text(verse_number, text))

        if verse_parts:
            if pending_headings:
                blocks.extend(pending_headings)
                pending_headings = []
            blocks.append(" ".join(verse_parts).strip())
            current_content_index = len(blocks) - 1
            continue

        for note in child.select(".note"):
            note.decompose()

        text = normalize_block_text(child.get_text(" ", strip=True))
        if not text:
            continue

        verse_match = re.match(r"^(\d+)\b", text)
        if verse_match:
            verse_number = int(verse_match.group(1))
            if start_verse is not None and verse_number < start_verse:
                continue
            if end_verse is not None and verse_number > end_verse:
                continue
            if pending_headings:
                blocks.extend(pending_headings)
                pending_headings = []
            blocks.append(superscript_leading_verse_numbers(text))
            current_content_index = len(blocks) - 1
            continue

        if current_content_index is not None:
            blocks[current_content_index] = f"{blocks[current_content_index]}\n{text}"
        else:
            if pending_headings:
                blocks.extend(pending_headings)
                pending_headings = []
            blocks.append(text)
            current_content_index = len(blocks) - 1

    return blocks


class BibleComClient:
    def __init__(self, client=None):
        if httpx is None:
            raise RuntimeError("httpx is required to use BibleComClient.")
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

    async def get_passage(
        self, passage: str, version: str = DEFAULT_VERSION, inline_details: bool = False
    ) -> str | InlinePassageResult | None:
        reference = parse_bible_com_reference(passage)
        version_id = BIBLE_COM_VERSION_IDS.get(version.upper())
        if reference is None or version_id is None:
            return None

        blocks: list[str] = []
        for chapter_number in range(reference.start_chapter, reference.end_chapter + 1):
            url = (
                f"{BIBLE_COM_BASE_URL}/{version_id}/"
                f"{reference.book_usfm}.{chapter_number}"
            )
            html = await self.fetch_text(url)
            if html is None:
                return None
            content_html = extract_chapter_content(html)
            if content_html is None:
                continue
            chapter_blocks = parse_chapter_content(
                content_html,
                start_verse=(
                    reference.start_verse
                    if chapter_number == reference.start_chapter
                    else None
                ),
                end_verse=(
                    reference.end_verse
                    if chapter_number == reference.end_chapter
                    else None
                ),
            )
            blocks.extend(chapter_blocks)

        if not blocks:
            return EMPTY

        header = build_passage_header(passage, version)
        final_text = "\n\n".join([header, *blocks]).strip()
        if not inline_details:
            return final_text

        content = " ".join(final_text.split())
        description = f"{content[:150]}..." if len(content) > 153 else content
        return InlinePassageResult(
            passage=final_text,
            result_id=f"{passage}/{version}",
            title=header,
            description=description,
        )
