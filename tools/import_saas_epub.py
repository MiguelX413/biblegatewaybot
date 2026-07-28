import re
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning

from json_compat import dumps as json_dumps

VERSE_TOKEN = "<<<VERSE:{chapter}:{verse}>>>"
VERSE_TOKEN_PATTERN = re.compile(r"<<<VERSE:(\d+):(\d+)>>>")
VERSE_ID_PATTERN = re.compile(r"^[A-Za-z0-9]+_vchap(\d+)-(\d+)$")

type VerseMap = dict[int, dict[int, str]]
type HeaderMap = dict[int, dict[int, list[str]]]
type ChapterData = dict[str, object]


@dataclass(frozen=True)
class BookSpec:
    title: str
    slug: str
    aliases: tuple[str, ...]
    files: tuple[str, ...]


@dataclass(frozen=True)
class ExtractedBook:
    verses: VerseMap
    headers: HeaderMap


BOOKS = (
    BookSpec(
        "Genesis",
        "genesis",
        ("genesis", "gen"),
        ("OEBPS/Genesis.html", "OEBPS/Genesis1.html"),
    ),
    BookSpec(
        "Exodus",
        "exodus",
        ("exodus", "exod", "exo"),
        ("OEBPS/Exodus.html", "OEBPS/Exodus1.html"),
    ),
    BookSpec("Leviticus", "leviticus", ("leviticus", "lev"), ("OEBPS/Leviticus.html",)),
    BookSpec(
        "Numbers",
        "numbers",
        ("numbers", "num"),
        ("OEBPS/Numbers.html", "OEBPS/Numbers1.html"),
    ),
    BookSpec(
        "Deuteronomy",
        "deuteronomy",
        ("deuteronomy", "deut"),
        ("OEBPS/Deuteronomy.html", "OEBPS/Deuteronomy1.html"),
    ),
    BookSpec("Joshua", "joshua", ("joshua", "josh"), ("OEBPS/Joshua.html",)),
    BookSpec("Judges", "judges", ("judges", "judg"), ("OEBPS/Judges.html",)),
    BookSpec("Ruth", "ruth", ("ruth",), ("OEBPS/Ruth.html",)),
    BookSpec(
        "1 Kingdoms",
        "1samuel",
        ("1 kingdoms", "1kingdoms", "1 samuel", "1samuel"),
        ("OEBPS/1Kingdoms.html",),
    ),
    BookSpec(
        "2 Kingdoms",
        "2samuel",
        ("2 kingdoms", "2kingdoms", "2 samuel", "2samuel"),
        ("OEBPS/2Kingdoms.html",),
    ),
    BookSpec(
        "3 Kingdoms",
        "1kings",
        ("3 kingdoms", "3kingdoms", "1 kings", "1kings"),
        ("OEBPS/3Kingdoms.html",),
    ),
    BookSpec(
        "4 Kingdoms",
        "2kings",
        ("4 kingdoms", "4kingdoms", "2 kings", "2kings"),
        ("OEBPS/4Kingdoms.html",),
    ),
    BookSpec(
        "1 Chronicles",
        "1chronicles",
        ("1 chronicles", "1chronicles", "1 paraleipomenon"),
        ("OEBPS/1Chronicles.html",),
    ),
    BookSpec(
        "2 Chronicles",
        "2chronicles",
        ("2 chronicles", "2chronicles", "2 paraleipomenon"),
        ("OEBPS/2Chronicles.html",),
    ),
    BookSpec(
        "1 Ezra",
        "1esdras",
        ("1 ezra", "1ezra", "1 esdras", "1esdras"),
        ("OEBPS/1Ezra.html",),
    ),
    BookSpec(
        "2 Ezra",
        "2esdras",
        ("2 ezra", "2ezra", "ezra", "2 esdras", "2esdras"),
        ("OEBPS/2Ezra.html",),
    ),
    BookSpec("Nehemiah", "nehemiah", ("nehemiah", "neh"), ("OEBPS/Nehemiah.html",)),
    BookSpec("Tobit", "tobit", ("tobit", "tob"), ("OEBPS/Tobit.html",)),
    BookSpec("Judith", "judith", ("judith", "jdt"), ("OEBPS/Judith.html",)),
    BookSpec("Esther", "esther", ("esther",), ("OEBPS/Esther.html",)),
    BookSpec(
        "1 Maccabees",
        "1maccabees",
        ("1 maccabees", "1maccabees"),
        ("OEBPS/1Maccabees.html",),
    ),
    BookSpec(
        "2 Maccabees",
        "2maccabees",
        ("2 maccabees", "2maccabees"),
        ("OEBPS/2Maccabees.html",),
    ),
    BookSpec(
        "3 Maccabees",
        "3maccabees",
        ("3 maccabees", "3maccabees"),
        ("OEBPS/3Maccabees.html",),
    ),
    BookSpec(
        "Psalm",
        "psalm",
        ("psalm", "psalms", "ps"),
        ("OEBPS/Psalms.html", "OEBPS/Psalms1.html"),
    ),
    BookSpec("Job", "job", ("job",), ("OEBPS/Job.html",)),
    BookSpec(
        "Proverbs",
        "proverbs",
        ("proverbs", "prov", "proverbs of solomon"),
        ("OEBPS/Proverbs.html",),
    ),
    BookSpec(
        "Ecclesiastes",
        "ecclesiastes",
        ("ecclesiastes", "ecclesiast"),
        ("OEBPS/Ecclesiastes.html",),
    ),
    BookSpec(
        "Song of Songs",
        "songofsolomon",
        ("song of songs", "song of solomon"),
        ("OEBPS/SongofSongs.html",),
    ),
    BookSpec(
        "Wisdom",
        "wisdom",
        ("wisdom", "wisdom of solomon"),
        ("OEBPS/WisdomofSolomon.html",),
    ),
    BookSpec(
        "Sirach",
        "sirach",
        ("sirach", "wisdom of sirach", "ben sira"),
        ("OEBPS/WisdomofSirach.html", "OEBPS/WisdomofSirach1.html"),
    ),
    BookSpec("Hosea", "hosea", ("hosea",), ("OEBPS/Hosea.html",)),
    BookSpec("Amos", "amos", ("amos",), ("OEBPS/Amos.html",)),
    BookSpec("Micah", "micah", ("micah",), ("OEBPS/Micah.html",)),
    BookSpec("Joel", "joel", ("joel",), ("OEBPS/Joel.html",)),
    BookSpec("Obadiah", "obadiah", ("obadiah",), ("OEBPS/Obadiah.html",)),
    BookSpec("Jonah", "jonah", ("jonah",), ("OEBPS/Jonah.html",)),
    BookSpec("Nahum", "nahum", ("nahum",), ("OEBPS/Nahum.html",)),
    BookSpec("Habakkuk", "habakkuk", ("habakkuk",), ("OEBPS/Habakkuk.html",)),
    BookSpec("Zephaniah", "zephaniah", ("zephaniah",), ("OEBPS/Zephaniah.html",)),
    BookSpec("Haggai", "haggai", ("haggai",), ("OEBPS/Haggai.html",)),
    BookSpec("Zechariah", "zechariah", ("zechariah",), ("OEBPS/Zechariah.html",)),
    BookSpec("Malachi", "malachi", ("malachi",), ("OEBPS/Malachi.html",)),
    BookSpec(
        "Isaiah", "isaiah", ("isaiah",), ("OEBPS/Isaiah.html", "OEBPS/Isaiah1.html")
    ),
    BookSpec(
        "Jeremiah",
        "jeremiah",
        ("jeremiah",),
        ("OEBPS/Jeremiah.html", "OEBPS/Jeremiah1.html"),
    ),
    BookSpec("Baruch", "baruch", ("baruch",), ("OEBPS/Baruch.html",)),
    BookSpec(
        "Lamentations",
        "lamentations",
        ("lamentations", "lamentations of jeremiah", "lam"),
        ("OEBPS/Lamentations.html",),
    ),
    BookSpec(
        "Epistle of Jeremiah",
        "letterofjeremiah",
        ("epistle of jeremiah", "letter of jeremiah"),
        ("OEBPS/EpistleofJeremiah.html",),
    ),
    BookSpec(
        "Ezekiel",
        "ezekiel",
        ("ezekiel",),
        ("OEBPS/Ezekiel.html", "OEBPS/Ezekiel1.html"),
    ),
    BookSpec("Daniel", "daniel", ("daniel",), ("OEBPS/Daniel.html",)),
)


def clean_text(element: Tag) -> str:
    text = " ".join(element.get_text(" ", strip=True).split())
    return text.replace(" - ", "-").strip()


def _verse_id(tag: Tag) -> tuple[int, int] | None:
    if tag.attrs is None:
        return None
    raw_id = tag.get("id")
    if not isinstance(raw_id, str):
        return None
    match = VERSE_ID_PATTERN.fullmatch(raw_id)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _element_with_verse_tokens(element: Tag) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(str(element), "lxml")
    for tag in soup.find_all(["img", "a"]):
        if tag.name == "a" and tag.find_parent("sup") is not None:
            continue
        tag.decompose()
    for tag in soup.find_all(True):
        verse_id = _verse_id(tag)
        if verse_id is not None:
            chapter, verse = verse_id
            tag.replace_with(f" {VERSE_TOKEN.format(chapter=chapter, verse=verse)} ")
            continue
        if tag.name == "sup":
            tag.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())
    return re.sub(r"\b([B-HJ-Z])\s+([a-z]{2,})", r"\1\2", text)


def _append_verse(verses: VerseMap, chapter: int, verse: int, text: str) -> None:
    normalized = text.strip()
    if not normalized:
        return
    chapter_verses = verses.setdefault(chapter, {})
    existing = chapter_verses.get(verse)
    chapter_verses[verse] = f"{existing} {normalized}" if existing else normalized


def _append_text_with_tokens(
    text: str,
    verses: VerseMap,
    current_reference: tuple[int, int] | None,
) -> tuple[int, int] | None:
    markers = list(VERSE_TOKEN_PATTERN.finditer(text))
    if not markers:
        if current_reference is not None:
            _append_verse(verses, *current_reference, text)
        return current_reference

    cursor = 0
    if current_reference is not None:
        _append_verse(verses, *current_reference, text[: markers[0].start()])
    for index, marker in enumerate(markers):
        current_reference = (int(marker.group(1)), int(marker.group(2)))
        next_start = (
            markers[index + 1].start() if index + 1 < len(markers) else len(text)
        )
        _append_verse(verses, *current_reference, text[marker.end() : next_start])
        cursor = next_start
    if cursor < len(text) and current_reference is not None:
        _append_verse(verses, *current_reference, text[cursor:])
    return current_reference


def _first_reference_in_text(text: str) -> tuple[int, int] | None:
    marker = VERSE_TOKEN_PATTERN.search(text)
    if marker is None:
        return None
    return int(marker.group(1)), int(marker.group(2))


def _attach_pending_headers(
    headers: HeaderMap,
    pending_headers: list[str],
    reference: tuple[int, int] | None,
) -> None:
    if not pending_headers or reference is None:
        return
    chapter, verse = reference
    headers.setdefault(chapter, {}).setdefault(verse, []).extend(pending_headers)
    pending_headers.clear()


def _eligible_paragraph(element: Tag) -> bool:
    classes = set(element.get("class", ()))
    return bool(classes & {"chapter1", "rindent", "psalm2"})


def extract_book_from_html(html_documents: tuple[str, ...]) -> ExtractedBook:
    verses: VerseMap = {}
    headers: HeaderMap = {}
    pending_headers: list[str] = []
    current_reference: tuple[int, int] | None = None

    for html in html_documents:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
            soup = BeautifulSoup(html, "lxml")
        for element in soup.find_all(["p", "ol"]):
            if element.name == "p":
                classes = set(element.get("class", ()))
                if "psalm" in classes:
                    current_reference = None
                    continue
                if "sub1" in classes:
                    header = clean_text(element)
                    if header:
                        pending_headers.append(header)
                    continue
                if not _eligible_paragraph(element):
                    continue

                text = _element_with_verse_tokens(element)
                if not text:
                    continue
                _attach_pending_headers(
                    headers,
                    pending_headers,
                    _first_reference_in_text(text) or current_reference,
                )
                current_reference = _append_text_with_tokens(
                    text, verses, current_reference
                )
                continue

            classes = set(element.get("class", ()))
            if "olstyle" not in classes:
                continue
            verse_id = _verse_id(element)
            if verse_id is not None:
                current_reference = verse_id
                _attach_pending_headers(headers, pending_headers, current_reference)
            for list_item in element.find_all("li", recursive=False):
                text = _element_with_verse_tokens(list_item)
                if not text:
                    continue
                _attach_pending_headers(
                    headers,
                    pending_headers,
                    _first_reference_in_text(text) or current_reference,
                )
                current_reference = _append_text_with_tokens(
                    text, verses, current_reference
                )

    return ExtractedBook(verses=verses, headers=headers)


def build_chapters(extracted: ExtractedBook) -> list[ChapterData | None]:
    if not extracted.verses:
        return [None]
    chapters: list[ChapterData | None] = [None]
    for chapter_number in range(1, max(extracted.verses) + 1):
        raw_verses = extracted.verses.get(chapter_number)
        if raw_verses is None:
            chapters.append(None)
            continue
        chapter_verses: list[str | None] = [None]
        for verse_number in range(1, max(raw_verses) + 1):
            chapter_verses.append(raw_verses.get(verse_number))
        chapter_headers = extracted.headers.get(chapter_number, {})
        chapters.append(
            {
                "headers": {
                    str(verse): headings
                    for verse, headings in sorted(chapter_headers.items())
                },
                "verses": chapter_verses,
            }
        )
    return chapters


def version_payload() -> dict[str, object]:
    return {
        "code": "SAAS",
        "name": "St. Athanasius Academy Septuagint",
        "language": "EN",
        "system": "bible",
        "aliases": ["OSB"],
    }


def book_payload(
    spec: BookSpec, chapters: list[ChapterData | None]
) -> dict[str, object]:
    return {
        "title": spec.title,
        "slug": spec.slug,
        "aliases": list(spec.aliases),
        "chapters": chapters,
    }


def import_epub(epub_path: Path, offline_dir: Path) -> tuple[int, int]:
    version_dir = offline_dir / "SAAS"
    books_dir = version_dir / "books"
    version_dir.mkdir(parents=True, exist_ok=True)
    books_dir.mkdir(parents=True, exist_ok=True)

    version_path = version_dir / "version.json"
    version_path.write_text(
        json_dumps(version_payload(), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    book_count = 0
    verse_count = 0
    with ZipFile(epub_path) as archive:
        archive_names = frozenset(archive.namelist())
        for spec in BOOKS:
            missing_files = [path for path in spec.files if path not in archive_names]
            if missing_files:
                raise ValueError(f"Missing EPUB content file: {missing_files[0]}")
            documents = tuple(
                archive.read(path).decode("utf-8", "ignore") for path in spec.files
            )
            extracted = extract_book_from_html(documents)
            chapters = build_chapters(extracted)
            if len(chapters) == 1:
                raise ValueError(f"No verses extracted for {spec.title}")
            book_path = books_dir / f"{spec.slug}.json"
            book_path.write_text(
                json_dumps(
                    book_payload(spec, chapters),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            book_count += 1
            verse_count += sum(len(verses) for verses in extracted.verses.values())
    return book_count, verse_count


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: python -m tools.import_saas_epub <input.epub> <offline-dir>",
            file=sys.stderr,
        )
        return 2
    book_count, verse_count = import_epub(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"Wrote {book_count} SAAS books with {verse_count} verse entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
