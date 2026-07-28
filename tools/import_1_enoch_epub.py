import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from zipfile import ZipFile

from bs4 import BeautifulSoup

from json_compat import dumps as json_dumps

EPUB_SECTION_FILES = (
    "OEBPS/chapter-001-chapter-1.html",
    "OEBPS/chapter-002-the-book-of-parables.html",
    "OEBPS/chapter-003-the-book-of-the-luminaries.html",
    "OEBPS/chapter-004-enochs-dream-visions.html",
    "OEBPS/chapter-005-a-narrative-bridge.html",
    "OEBPS/chapter-006-the-epistle-of-enoch.html",
    "OEBPS/chapter-007-the-birth-of-noah.html",
    "OEBPS/chapter-008-a-final-book-by-enoch.html",
)
CHAPTER_SOURCE_URLS = (
    (range(1, 37), "https://doi.org/10.2307/j.ctt22nm5vn.6"),
    (range(37, 72), "https://doi.org/10.2307/j.ctt22nm5vn.7"),
    (range(72, 83), "https://doi.org/10.2307/j.ctt22nm5vn.8"),
    (range(83, 91), "https://doi.org/10.2307/j.ctt22nm5vn.9"),
    (range(91, 92), "https://doi.org/10.2307/j.ctt22nm5vn.10"),
    (range(92, 106), "https://doi.org/10.2307/j.ctt22nm5vn.11"),
    (range(106, 108), "https://doi.org/10.2307/j.ctt22nm5vn.12"),
    (range(108, 109), "https://doi.org/10.2307/j.ctt22nm5vn.13"),
)
VERSE_PREFIX_PATTERN = re.compile(r"^(\d+):(\d+)(?:/|\s+)(.*)$", re.DOTALL)
CONTINUATION_PREFIX_PATTERN = re.compile(r"^(\d+)(?:/|\s+)(.*)$", re.DOTALL)
INLINE_VERSE_MARKER_PATTERN = re.compile(r"\s+((?:(\d+):)?(\d+))/\s*")
FOOTNOTE_NUMBER_PATTERN = re.compile(r"\s*\[\d+\]")
OMITTED_VERSE_RANGE_PATTERN = re.compile(r"^\d+\s*[-–—]\s*\d+\s*(?:\.\s*)+$")

type VerseMap = dict[int, dict[int, str]]
type HeaderMap = dict[int, dict[int, list[str]]]
type ChapterData = dict[str, object]


@dataclass(frozen=True)
class ExtractedText:
    verses: VerseMap
    headers: HeaderMap


def clean_paragraph_text(paragraph) -> str:
    paragraph_copy = BeautifulSoup(str(paragraph), "lxml")
    for tag in paragraph_copy.select("sup.footnote, a.footnote"):
        tag.decompose()
    text = " ".join(paragraph_copy.get_text(" ", strip=True).split())
    text = FOOTNOTE_NUMBER_PATTERN.sub("", text)
    return text.strip()


def clean_heading_text(heading) -> str:
    heading_copy = BeautifulSoup(str(heading), "lxml")
    for tag in heading_copy.select("sup.footnote, a.footnote"):
        tag.decompose()
    return " ".join(heading_copy.get_text(" ", strip=True).split()).strip()


def split_inline_verse_segments(text: str) -> list[tuple[int | None, int, str]]:
    segments: list[tuple[int | None, int, str]] = []
    matches = list(INLINE_VERSE_MARKER_PATTERN.finditer(text))
    if not matches:
        return segments

    for index, match in enumerate(matches):
        segment_start = match.end()
        segment_end = (
            matches[index + 1].start() if index + 1 < len(matches) else len(text)
        )
        chapter = int(match.group(2)) if match.group(2) is not None else None
        verse = int(match.group(3))
        body = text[segment_start:segment_end].strip()
        segments.append((chapter, verse, body))
    return segments


def source_url_for_chapter(chapter: int) -> str:
    for chapters, source_url in CHAPTER_SOURCE_URLS:
        if chapter in chapters:
            return source_url
    raise ValueError(f"No source URL configured for chapter {chapter}")


def extract_text_from_html(html: str) -> ExtractedText:
    soup = BeautifulSoup(html, "lxml")
    verses: VerseMap = {}
    headers: HeaderMap = {}
    pending_headers: list[str] = []
    current_chapter: int | None = None
    current_verse: int | None = None

    def attach_pending_headers(chapter: int, verse: int) -> None:
        if not pending_headers:
            return
        headers.setdefault(chapter, {}).setdefault(verse, []).extend(pending_headers)
        pending_headers.clear()

    for element in soup.find_all(["h1", "h2", "h3", "p"]):
        if element.name != "p":
            element_classes = cast(list[str] | None, element.get("class"))
            if element_classes and "chapter-number" in element_classes:
                continue
            heading = clean_heading_text(element)
            if heading:
                pending_headers.append(heading)
            continue

        paragraph = element
        text = clean_paragraph_text(paragraph)
        if not text:
            continue
        if OMITTED_VERSE_RANGE_PATTERN.fullmatch(text):
            continue

        prefixed_match = VERSE_PREFIX_PATTERN.match(text)
        if prefixed_match is not None:
            chapter = int(prefixed_match.group(1))
            verse = int(prefixed_match.group(2))
            body = prefixed_match.group(3).strip()
            current_chapter = chapter
            current_verse = verse
            attach_pending_headers(chapter, verse)
            inline_segments = split_inline_verse_segments(body)
            if inline_segments:
                first_inline_start = INLINE_VERSE_MARKER_PATTERN.search(body)
                assert first_inline_start is not None
                leading_body = body[: first_inline_start.start()].strip()
                if leading_body:
                    verses.setdefault(chapter, {})[verse] = leading_body
                for inline_chapter, inline_verse, inline_body in inline_segments:
                    current_chapter = inline_chapter or current_chapter
                    current_verse = inline_verse
                    if inline_body:
                        verses.setdefault(current_chapter, {})[current_verse] = (
                            inline_body
                        )
            elif body:
                verses.setdefault(chapter, {})[verse] = body
            continue

        continuation_match = CONTINUATION_PREFIX_PATTERN.match(text)
        if (
            continuation_match is not None
            and current_chapter is not None
            and current_verse is not None
        ):
            verse = int(continuation_match.group(1))
            body = continuation_match.group(2).strip()
            current_verse = verse
            attach_pending_headers(current_chapter, verse)
            inline_segments = split_inline_verse_segments(body)
            if inline_segments:
                first_inline_start = INLINE_VERSE_MARKER_PATTERN.search(body)
                assert first_inline_start is not None
                leading_body = body[: first_inline_start.start()].strip()
                if leading_body:
                    verses.setdefault(current_chapter, {})[verse] = leading_body
                for inline_chapter, inline_verse, inline_body in inline_segments:
                    current_chapter = inline_chapter or current_chapter
                    current_verse = inline_verse
                    if inline_body:
                        verses.setdefault(current_chapter, {})[current_verse] = (
                            inline_body
                        )
            elif body:
                verses.setdefault(current_chapter, {})[verse] = body
            continue

        inline_segments = split_inline_verse_segments(text)
        if (
            inline_segments
            and current_chapter is not None
            and current_verse is not None
        ):
            attach_pending_headers(current_chapter, current_verse)
            first_inline_start = INLINE_VERSE_MARKER_PATTERN.search(text)
            assert first_inline_start is not None
            current_body = text[: first_inline_start.start()].strip()
            if current_body:
                chapter_verses = verses.setdefault(current_chapter, {})
                existing = chapter_verses.get(current_verse, "")
                chapter_verses[current_verse] = (
                    f"{existing} {current_body}".strip() if existing else current_body
                )
            for inline_chapter, inline_verse, inline_body in inline_segments:
                current_chapter = inline_chapter or current_chapter
                current_verse = inline_verse
                if inline_body:
                    verses.setdefault(current_chapter, {})[current_verse] = inline_body
            continue

        if current_chapter is None or current_verse is None:
            continue

        attach_pending_headers(current_chapter, current_verse)
        chapter_verses = verses.setdefault(current_chapter, {})
        existing = chapter_verses.get(current_verse, "")
        chapter_verses[current_verse] = (
            f"{existing} {text}".strip() if existing else text
        )

    return ExtractedText(verses=verses, headers=headers)


def build_chapters(
    verse_map: VerseMap,
    header_map: HeaderMap,
) -> list[ChapterData | None]:
    chapters: list[ChapterData | None] = [None]
    previous_chapter = 0
    for chapter in sorted(verse_map):
        if chapter <= previous_chapter:
            raise ValueError(f"Chapter order is not strictly increasing: {chapter}")
        while len(chapters) < chapter:
            chapters.append(None)

        raw_verses = verse_map[chapter]
        raw_headers = header_map.get(chapter, {})
        unknown_header_verses = raw_headers.keys() - raw_verses.keys()
        if unknown_header_verses:
            invalid_verse = min(unknown_header_verses)
            raise ValueError(f"Header has no matching verse: {chapter}:{invalid_verse}")
        verse_numbers = sorted(raw_verses)
        chapter_verses: list[str | None] = [None]
        previous_verse = 0
        for verse in verse_numbers:
            if verse <= previous_verse:
                raise ValueError(
                    f"Verse order is not strictly increasing: {chapter}:{verse}"
                )
            while len(chapter_verses) < verse:
                chapter_verses.append(None)
            chapter_verses.append(raw_verses[verse])
            previous_verse = verse
        chapters.append(
            {
                "headers": {
                    str(verse): list(raw_headers[verse])
                    for verse in sorted(raw_headers)
                },
                "source_url": source_url_for_chapter(chapter),
                "verses": chapter_verses,
            }
        )
        previous_chapter = chapter

    return chapters


def import_epub(epub_path: Path) -> list[ChapterData | None]:
    verse_map: VerseMap = {}
    header_map: HeaderMap = {}
    with ZipFile(epub_path) as archive:
        for section_file in EPUB_SECTION_FILES:
            html = archive.read(section_file).decode("utf-8", "ignore")
            extracted = extract_text_from_html(html)
            for chapter, verses in extracted.verses.items():
                verse_map.setdefault(chapter, {}).update(verses)
            for chapter, verse_headers in extracted.headers.items():
                target_headers = header_map.setdefault(chapter, {})
                for verse, headings in verse_headers.items():
                    target_headers.setdefault(verse, []).extend(headings)
    return build_chapters(verse_map, header_map)


def version_payload() -> dict[str, object]:
    return {
        "code": "HERM",
        "name": "Hermeneia",
        "language": "EN",
        "system": "bible",
        "aliases": [],
    }


def work_payload(chapters: list[ChapterData | None]) -> dict[str, object]:
    return {
        "version_code": "HERM",
        "title": "1 Enoch",
        "slug": "1enoch",
        "aliases": ["1 enoch", "1enoch", "first enoch", "enoch"],
        "source_url": "https://doi.org/10.2307/j.ctt22nm5vn",
        "chapters": chapters,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: python -m tools.import_1_enoch_epub <input.epub> <offline-dir>",
            file=sys.stderr,
        )
        return 2

    epub_path = Path(sys.argv[1])
    offline_dir = Path(sys.argv[2])
    chapters = import_epub(epub_path)

    versions_dir = offline_dir / "versions"
    works_dir = offline_dir / "works"
    version_path = versions_dir / "HERM.json"
    work_path = works_dir / "1enoch.herm.json"

    versions_dir.mkdir(parents=True, exist_ok=True)
    works_dir.mkdir(parents=True, exist_ok=True)

    version_path.write_text(
        json_dumps(version_payload(), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    work_path.write_text(
        json_dumps(work_payload(chapters), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    verse_count = 0
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        verses = chapter.get("verses")
        if not isinstance(verses, list):
            continue
        verse_count += sum(
            1
            for verse_index, verse in enumerate(verses)
            if verse_index > 0 and isinstance(verse, str) and verse
        )
    print(f"Wrote {version_path} and {work_path} with {verse_count} verse entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
