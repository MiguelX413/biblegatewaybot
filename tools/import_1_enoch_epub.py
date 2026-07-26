import re
import sys
from pathlib import Path
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
VERSE_PREFIX_PATTERN = re.compile(r"^(\d+):(\d+)(?:/|\s+)(.*)$", re.DOTALL)
CONTINUATION_PREFIX_PATTERN = re.compile(r"^(\d+)(?:/|\s+)(.*)$", re.DOTALL)
INLINE_VERSE_MARKER_PATTERN = re.compile(r"\s+((?:(\d+):)?(\d+))/\s*")
FOOTNOTE_NUMBER_PATTERN = re.compile(r"\s*\[\d+\]")


def clean_paragraph_text(paragraph) -> str:
    paragraph_copy = BeautifulSoup(str(paragraph), "lxml")
    for tag in paragraph_copy.select("sup.footnote, a.footnote"):
        tag.decompose()
    text = " ".join(paragraph_copy.get_text(" ", strip=True).split())
    text = FOOTNOTE_NUMBER_PATTERN.sub("", text)
    return text.strip()


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


def extract_verses_from_html(html: str) -> dict[int, dict[int, str]]:
    soup = BeautifulSoup(html, "lxml")
    verses: dict[int, dict[int, str]] = {}
    current_chapter: int | None = None
    current_verse: int | None = None

    for paragraph in soup.find_all("p"):
        text = clean_paragraph_text(paragraph)
        if not text:
            continue

        prefixed_match = VERSE_PREFIX_PATTERN.match(text)
        if prefixed_match is not None:
            chapter = int(prefixed_match.group(1))
            verse = int(prefixed_match.group(2))
            body = prefixed_match.group(3).strip()
            current_chapter = chapter
            current_verse = verse
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

        chapter_verses = verses.setdefault(current_chapter, {})
        existing = chapter_verses.get(current_verse, "")
        chapter_verses[current_verse] = (
            f"{existing} {text}".strip() if existing else text
        )

    return verses


def build_chapters(
    verse_map: dict[int, dict[int, str]],
) -> list[list[str | None] | None]:
    chapters: list[list[str | None] | None] = []
    previous_chapter = 0
    for chapter in sorted(verse_map):
        if chapter <= previous_chapter:
            raise ValueError(f"Chapter order is not strictly increasing: {chapter}")
        while len(chapters) < chapter - 1:
            chapters.append(None)

        raw_verses = verse_map[chapter]
        verse_numbers = sorted(raw_verses)
        chapter_verses: list[str | None] = []
        previous_verse = 0
        for verse in verse_numbers:
            if verse <= previous_verse:
                raise ValueError(
                    f"Verse order is not strictly increasing: {chapter}:{verse}"
                )
            while len(chapter_verses) < verse - 1:
                chapter_verses.append(None)
            chapter_verses.append(raw_verses[verse])
            previous_verse = verse
        chapters.append(chapter_verses)
        previous_chapter = chapter

    return chapters


def import_epub(epub_path: Path) -> list[list[str | None] | None]:
    verse_map: dict[int, dict[int, str]] = {}
    with ZipFile(epub_path) as archive:
        for section_file in EPUB_SECTION_FILES:
            html = archive.read(section_file).decode("utf-8", "ignore")
            chapter_verses = extract_verses_from_html(html)
            for chapter, verses in chapter_verses.items():
                verse_map.setdefault(chapter, {}).update(verses)
    return build_chapters(verse_map)


def version_payload() -> dict[str, object]:
    return {
        "code": "HERM",
        "name": "Hermeneia",
        "language": "EN",
        "system": "bible",
        "aliases": [],
    }


def work_payload(chapters: list[list[str | None] | None]) -> dict[str, object]:
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
            "Usage: python tools/import_1_enoch_epub.py <input.epub> <offline-dir>",
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
    verse_count = sum(
        1 for chapter in chapters if chapter for verse in chapter if verse
    )
    print(f"Wrote {version_path} and {work_path} with {verse_count} verse entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
