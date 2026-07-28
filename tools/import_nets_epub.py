import re
import sys
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from bs4 import BeautifulSoup, Tag

from json_compat import dumps as json_dumps

VERSE_TOKEN = "<<<VERSE:{number}>>>"
VERSE_TOKEN_PATTERN = re.compile(r"<<<VERSE:(\d+)>>>")
LEADING_VERSE_PATTERN = re.compile(r"^(\d+)\s+(.*)$", re.DOTALL)
PSALM_HEADING_PATTERN = re.compile(r"^Psalm(?:s of Salomon|s)?\s+(\d+)", re.I)
NUMBER_PATTERN = re.compile(r"^(\d+)(?:\(\d+\))?$")

type VerseMap = dict[int, dict[int, str]]
type HeaderMap = dict[int, dict[int, list[str]]]
type ChapterData = dict[str, object]


@dataclass(frozen=True)
class WorkSpec:
    title: str
    slug: str
    aliases: tuple[str, ...]
    files: tuple[str, ...]
    start_anchor: str | None = None
    end_anchor: str | None = None
    single_chapter: bool = False
    psalm_headings: bool = False
    table_column: int | None = None


@dataclass(frozen=True)
class ExtractedWork:
    verses: VerseMap
    headers: HeaderMap


def chapter_file(number: int, *suffixes: str) -> tuple[str, ...]:
    return tuple(
        f"OEBPS/html/chapter{number:02}{suffix}.html" for suffix in ("", *suffixes)
    )


WORKS = (
    WorkSpec("Genesis", "genesis", ("genesis", "gen"), chapter_file(1)),
    WorkSpec("Exodus", "exodus", ("exodus", "exod", "exo"), chapter_file(2)),
    WorkSpec("Leviticus", "leviticus", ("leviticus", "lev"), chapter_file(3)),
    WorkSpec("Numbers", "numbers", ("numbers", "num"), chapter_file(4)),
    WorkSpec(
        "Deuteronomy",
        "deuteronomy",
        ("deuteronomy", "deut"),
        chapter_file(5),
    ),
    WorkSpec("Joshua", "joshua", ("joshua", "josh"), chapter_file(6)),
    WorkSpec("Judges", "judges", ("judges", "judg"), chapter_file(7), table_column=0),
    WorkSpec(
        "Judges B",
        "judgesb",
        ("judges b", "judgesb"),
        chapter_file(7),
        table_column=1,
    ),
    WorkSpec("Ruth", "ruth", ("ruth",), chapter_file(8)),
    WorkSpec(
        "1 Samuel",
        "1samuel",
        ("1 samuel", "1samuel", "1 reigns"),
        chapter_file(9),
    ),
    WorkSpec(
        "2 Samuel",
        "2samuel",
        ("2 samuel", "2samuel", "2 reigns"),
        chapter_file(10),
    ),
    WorkSpec(
        "1 Kings",
        "1kings",
        ("1 kings", "1kings", "3 reigns"),
        chapter_file(11),
    ),
    WorkSpec(
        "2 Kings",
        "2kings",
        ("2 kings", "2kings", "4 reigns"),
        chapter_file(12),
    ),
    WorkSpec(
        "1 Chronicles",
        "1chronicles",
        ("1 chronicles", "1chronicles", "1 supplements"),
        chapter_file(13),
    ),
    WorkSpec(
        "2 Chronicles",
        "2chronicles",
        ("2 chronicles", "2chronicles", "2 supplements"),
        chapter_file(14),
    ),
    WorkSpec("1 Esdras", "1esdras", ("1 esdras", "1esdras"), chapter_file(15)),
    WorkSpec("2 Esdras", "2esdras", ("2 esdras", "2esdras"), chapter_file(16)),
    WorkSpec("Esther", "esther", ("esther",), chapter_file(17), table_column=0),
    WorkSpec(
        "Esther Alpha",
        "estheralpha",
        ("esther alpha", "alpha esther"),
        chapter_file(17),
        table_column=1,
    ),
    WorkSpec("Judith", "judith", ("judith", "jdt"), chapter_file(18)),
    WorkSpec("Tobit", "tobit", ("tobit", "tob"), chapter_file(19), table_column=0),
    WorkSpec(
        "Tobit GI",
        "tobitgi",
        ("tobit gi",),
        chapter_file(19),
        table_column=1,
    ),
    WorkSpec(
        "1 Maccabees",
        "1maccabees",
        ("1 maccabees", "1maccabees"),
        chapter_file(20),
    ),
    WorkSpec(
        "2 Maccabees",
        "2maccabees",
        ("2 maccabees", "2maccabees"),
        chapter_file(21),
    ),
    WorkSpec(
        "3 Maccabees",
        "3maccabees",
        ("3 maccabees", "3maccabees"),
        chapter_file(22),
    ),
    WorkSpec(
        "4 Maccabees",
        "4maccabees",
        ("4 maccabees", "4maccabees"),
        chapter_file(23),
    ),
    WorkSpec(
        "Psalms",
        "psalm",
        ("psalm", "psalms", "ps"),
        chapter_file(24, "a"),
        psalm_headings=True,
    ),
    WorkSpec(
        "Prayer of Manasseh",
        "prayerofmanasseh",
        ("prayer of manasseh", "prayer of manasses"),
        chapter_file(25),
        single_chapter=True,
    ),
    WorkSpec("Proverbs", "proverbs", ("proverbs", "prov"), chapter_file(26)),
    WorkSpec(
        "Ecclesiastes",
        "ecclesiastes",
        ("ecclesiastes", "ecclesiast"),
        chapter_file(27),
    ),
    WorkSpec(
        "Song of Solomon",
        "songofsolomon",
        ("song of solomon", "song of songs"),
        chapter_file(28),
    ),
    WorkSpec("Job", "job", ("job", "iob"), chapter_file(29)),
    WorkSpec(
        "Wisdom",
        "wisdom",
        ("wisdom", "wisdom of solomon"),
        chapter_file(30),
    ),
    WorkSpec("Sirach", "sirach", ("sirach", "ben sira"), chapter_file(31, "a")),
    WorkSpec(
        "Psalms of Solomon",
        "psalmsofsolomon",
        ("psalms of solomon", "psalms of salomon"),
        chapter_file(32),
        psalm_headings=True,
    ),
    WorkSpec(
        "Hosea",
        "hosea",
        ("hosea", "hosee"),
        chapter_file(33),
        "pa04ch01sec1",
        "pa04ch01sec2",
    ),
    WorkSpec(
        "Amos",
        "amos",
        ("amos",),
        chapter_file(33),
        "pa04ch01sec2",
        "pa04ch01sec3",
    ),
    WorkSpec(
        "Micah",
        "micah",
        ("micah", "michaias"),
        chapter_file(33),
        "pa04ch01sec3",
        "pa04ch01sec4",
    ),
    WorkSpec(
        "Joel",
        "joel",
        ("joel", "ioel"),
        chapter_file(33, "a"),
        "pa04ch01sec4",
        "pa04ch01sec5",
    ),
    WorkSpec(
        "Obadiah",
        "obadiah",
        ("obadiah", "abdias"),
        chapter_file(33, "a"),
        "pa04ch01sec5",
        "pa04ch01sec6",
        single_chapter=True,
    ),
    WorkSpec(
        "Jonah",
        "jonah",
        ("jonah", "ionas"),
        chapter_file(33, "a"),
        "pa04ch01sec6",
        "pa04ch01sec7",
    ),
    WorkSpec(
        "Nahum",
        "nahum",
        ("nahum", "naoum"),
        chapter_file(33, "a"),
        "pa04ch01sec7",
        "pa04ch01sec8",
    ),
    WorkSpec(
        "Habakkuk",
        "habakkuk",
        ("habakkuk", "habbakoum"),
        chapter_file(33, "a"),
        "pa04ch01sec8",
        "pa04ch01sec9",
    ),
    WorkSpec(
        "Zephaniah",
        "zephaniah",
        ("zephaniah", "sophonias"),
        chapter_file(33, "a"),
        "pa04ch01sec9",
        "pa04ch01sec10",
    ),
    WorkSpec(
        "Haggai",
        "haggai",
        ("haggai", "haggaios"),
        chapter_file(33, "a"),
        "pa04ch01sec10",
        "pa04ch01sec11",
    ),
    WorkSpec(
        "Zechariah",
        "zechariah",
        ("zechariah", "zacharias"),
        chapter_file(33, "a"),
        "pa04ch01sec11",
        "pa04ch01sec12",
    ),
    WorkSpec(
        "Malachi",
        "malachi",
        ("malachi", "malachias"),
        chapter_file(33, "a"),
        "pa04ch01sec12",
    ),
    WorkSpec("Isaiah", "isaiah", ("isaiah", "esaias"), chapter_file(34, "a")),
    WorkSpec("Jeremiah", "jeremiah", ("jeremiah", "ieremias"), chapter_file(35, "a")),
    WorkSpec("Baruch", "baruch", ("baruch", "barouch"), chapter_file(36)),
    WorkSpec("Lamentations", "lamentations", ("lamentations", "lam"), chapter_file(37)),
    WorkSpec(
        "Letter of Jeremiah",
        "letterofjeremiah",
        ("letter of jeremiah", "letter of ieremias"),
        chapter_file(38),
        single_chapter=True,
    ),
    WorkSpec("Ezekiel", "ezekiel", ("ezekiel", "iezekiel"), chapter_file(39)),
    WorkSpec(
        "Susanna",
        "susanna",
        ("susanna", "sousanna"),
        chapter_file(40),
        single_chapter=True,
        table_column=0,
    ),
    WorkSpec(
        "Susanna Theodotion",
        "susannatheodotion",
        ("susanna theodotion", "sousanna theodotion"),
        chapter_file(40),
        single_chapter=True,
        table_column=1,
    ),
    WorkSpec("Daniel", "daniel", ("daniel",), chapter_file(41), table_column=0),
    WorkSpec(
        "Daniel Theodotion",
        "danieltheodotion",
        ("daniel theodotion",),
        chapter_file(41),
        table_column=1,
    ),
    WorkSpec(
        "Bel and the Dragon",
        "belandthedragon",
        ("bel and the dragon",),
        chapter_file(42),
        single_chapter=True,
        table_column=0,
    ),
    WorkSpec(
        "Bel and the Dragon Theodotion",
        "belandthedragontheodotion",
        ("bel and the dragon theodotion",),
        chapter_file(42),
        single_chapter=True,
        table_column=1,
    ),
)


def clean_heading(element: Tag) -> str:
    return " ".join(element.get_text(" ", strip=True).split())


def _chapter_marker(paragraph: Tag) -> int | None:
    strong = paragraph.find("strong", recursive=False)
    if strong is not None:
        text = clean_heading(strong)
        match = NUMBER_PATTERN.fullmatch(text)
        if match:
            return int(match.group(1))
    return None


def _plain_chapter_candidate(paragraph: Tag) -> int | None:
    leading = re.match(r"^\s*(\d+)\s+", paragraph.get_text(" ", strip=True))
    return int(leading.group(1)) if leading else None


def _psalm_marker(paragraph: Tag) -> int | None:
    strong = paragraph.find("strong")
    if strong is None:
        return None
    match = PSALM_HEADING_PATTERN.match(clean_heading(strong))
    return int(match.group(1)) if match else None


def clean_paragraph(paragraph: Tag, chapter_marker: int | None) -> str:
    copy_soup = BeautifulSoup(str(paragraph), "xml")
    copy = copy_soup.find("p")
    if copy is None:
        return ""
    if chapter_marker is not None:
        strong = copy.find("strong", recursive=False)
        if strong is not None:
            strong.decompose()
    for sup in copy.find_all("sup"):
        if sup.find("a") is not None:
            sup.decompose()
            continue
        marker = NUMBER_PATTERN.fullmatch(clean_heading(sup))
        if marker is None:
            sup.decompose()
            continue
        sup.replace_with(f" {VERSE_TOKEN.format(number=marker.group(1))} ")
    for tag in copy.find_all(["a", "img"]):
        tag.decompose()
    text = " ".join(copy.get_text(" ", strip=True).split())
    if chapter_marker is not None:
        text = re.sub(rf"^{chapter_marker}\s+", "", text, count=1)
    return text


def _append_verse(verses: VerseMap, chapter: int, verse: int, text: str) -> None:
    normalized = text.strip()
    if not normalized:
        return
    chapter_verses = verses.setdefault(chapter, {})
    existing = chapter_verses.get(verse)
    chapter_verses[verse] = f"{existing} {normalized}" if existing else normalized


def _selected_elements(soup: BeautifulSoup, table_column: int | None) -> list[Tag]:
    if table_column is None:
        return list(soup.find_all(["h3", "p"]))
    elements: list[Tag] = []
    for row in soup.find_all("tr"):
        cells = row.find_all("td", recursive=False)
        if table_column < len(cells):
            elements.extend(cells[table_column].find_all(["h3", "p"]))
    return elements


def _elements_for_work(html_documents: tuple[str, ...], spec: WorkSpec) -> list[Tag]:
    document_elements = [
        _selected_elements(BeautifulSoup(html, "xml"), spec.table_column)
        for html in html_documents
    ]
    if spec.start_anchor is None:
        return [element for elements in document_elements for element in elements]

    selected: list[Tag] = []
    found_start = False
    for elements in document_elements:
        for element in elements:
            if not found_start and element.find(id=spec.start_anchor) is not None:
                found_start = True
                continue
            if (
                found_start
                and spec.end_anchor is not None
                and element.find(id=spec.end_anchor) is not None
            ):
                return selected
            if found_start:
                selected.append(element)
    return selected


def extract_work_from_html(
    html_documents: tuple[str, ...], spec: WorkSpec
) -> ExtractedWork:
    verses: VerseMap = {}
    headers: HeaderMap = {}
    current_chapter: int | None = 1 if spec.single_chapter else None
    current_verse: int | None = None
    active = spec.single_chapter
    pending_headers: list[str] = []

    for element in _elements_for_work(html_documents, spec):
        if element.name == "h3":
            heading = clean_heading(element)
            if spec.psalm_headings:
                match = PSALM_HEADING_PATTERN.match(heading)
                if match:
                    current_chapter = int(match.group(1))
                    current_verse = None
                    active = True
                    continue
            if current_chapter is not None:
                pending_headers.append(heading)
            continue

        paragraph = element
        psalm_marker = _psalm_marker(paragraph) if spec.psalm_headings else None
        if psalm_marker is not None:
            current_chapter = psalm_marker
            current_verse = None
            active = True
            continue

        chapter_marker = _chapter_marker(paragraph)
        if chapter_marker is None and not spec.single_chapter:
            candidate = _plain_chapter_candidate(paragraph)
            if candidate is not None and (
                (current_chapter is None and candidate == 1)
                or (
                    current_chapter is not None
                    and current_verse is not None
                    and candidate == current_chapter + 1
                    and candidate < current_verse
                )
            ):
                chapter_marker = candidate
        if chapter_marker is not None:
            current_chapter = chapter_marker
            current_verse = 1
            active = True
        if not active:
            continue

        text = clean_paragraph(paragraph, chapter_marker)
        if not text:
            continue
        leading_match = LEADING_VERSE_PATTERN.match(text)

        if chapter_marker is None and leading_match is not None:
            current_verse = int(leading_match.group(1))
            text = leading_match.group(2)
        markers = list(VERSE_TOKEN_PATTERN.finditer(text))
        if current_verse is None:
            if markers and markers[0].start() == 0:
                current_verse = int(markers[0].group(1))
            else:
                continue

        assert current_chapter is not None
        assert current_verse is not None
        if pending_headers:
            headers.setdefault(current_chapter, {}).setdefault(
                current_verse, []
            ).extend(pending_headers)
            pending_headers.clear()

        cursor = 0
        for marker in markers:
            _append_verse(
                verses,
                current_chapter,
                current_verse,
                text[cursor : marker.start()],
            )
            current_verse = int(marker.group(1))
            cursor = marker.end()
        _append_verse(verses, current_chapter, current_verse, text[cursor:])

    return ExtractedWork(verses=verses, headers=headers)


def build_chapters(extracted: ExtractedWork) -> list[ChapterData | None]:
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
        "code": "NETS",
        "name": "New English Translation of the Septuagint",
        "language": "EN",
        "system": "bible",
        "aliases": [],
    }


def book_payload(
    spec: WorkSpec, chapters: list[ChapterData | None]
) -> dict[str, object]:
    return {
        "title": spec.title,
        "slug": spec.slug,
        "aliases": list(spec.aliases),
        "chapters": chapters,
    }


def import_epub(epub_path: Path, offline_dir: Path) -> tuple[int, int]:
    version_dir = offline_dir / "NETS"
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
        for spec in WORKS:
            missing_files = [path for path in spec.files if path not in archive_names]
            if missing_files:
                raise ValueError(f"Missing EPUB content file: {missing_files[0]}")
            documents = tuple(
                archive.read(path).decode("utf-8", "ignore") for path in spec.files
            )
            extracted = extract_work_from_html(documents, spec)
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
            "Usage: python -m tools.import_nets_epub <input.epub> <offline-dir>",
            file=sys.stderr,
        )
        return 2
    book_count, verse_count = import_epub(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"Wrote {book_count} NETS books with {verse_count} verse entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
