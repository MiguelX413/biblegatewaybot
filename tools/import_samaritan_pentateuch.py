import hashlib
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

from json_compat import dumps as json_dumps
from json_compat import loads as json_loads

SOURCE_URL = "https://doi.org/10.5281/zenodo.7734632"
ZENODO_RECORD_API_ROOT = "https://zenodo.org/api/records"
REQUIRED_FEATURES = ("otype", "oslots", "book", "chapter", "verse", "sign")
SQUARE_TO_SAMARITAN = str.maketrans(
    {
        "א": "ࠀ",
        "ב": "ࠁ",
        "ג": "ࠂ",
        "ד": "ࠃ",
        "ה": "ࠄ",
        "ו": "ࠅ",
        "ז": "ࠆ",
        "ח": "ࠇ",
        "ט": "ࠈ",
        "י": "ࠉ",
        "כ": "ࠊ",
        "ך": "ࠊ",
        "ל": "ࠋ",
        "מ": "ࠌ",
        "ם": "ࠌ",
        "נ": "ࠍ",
        "ן": "ࠍ",
        "ס": "ࠎ",
        "ע": "ࠏ",
        "פ": "ࠐ",
        "ף": "ࠐ",
        "צ": "ࠑ",
        "ץ": "ࠑ",
        "ק": "ࠒ",
        "ר": "ࠓ",
        "ש": "ࠔ",
        "ת": "ࠕ",
    }
)


@dataclass(frozen=True)
class BookSpec:
    title: str
    slug: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class Section:
    node: int
    value: str
    first_slot: int
    last_slot: int


@dataclass(frozen=True)
class DownloadedDataset:
    version: str
    size: int
    source_url: str


BOOKS = {
    spec.title: spec
    for spec in (
        BookSpec("Genesis", "genesis", ("genesis", "gen")),
        BookSpec("Exodus", "exodus", ("exodus", "exod", "exo")),
        BookSpec("Leviticus", "leviticus", ("leviticus", "lev")),
        BookSpec("Numbers", "numbers", ("numbers", "num")),
        BookSpec("Deuteronomy", "deuteronomy", ("deuteronomy", "deut")),
    )
}


def _parse_node_feature(text: str, feature_name: str) -> dict[int, str]:
    values: dict[int, str] = {}
    current_node = 0
    in_data = False

    for line in text.splitlines():
        if not in_data:
            if not line:
                in_data = True
            continue

        if "\t" in line:
            raw_node, value = line.split("\t", 1)
            if not raw_node.isdigit():
                raise ValueError(
                    f"Invalid node identifier in Text-Fabric feature {feature_name}"
                )
            current_node = int(raw_node)
        else:
            current_node += 1
            value = line
        values[current_node] = value

    if not in_data:
        raise ValueError(f"Text-Fabric feature {feature_name} has no data section")
    return values


def _slot_bounds(value: str, node: int) -> tuple[int, int]:
    slots: list[tuple[int, int]] = []
    for part in value.split(","):
        match = re.fullmatch(r"(\d+)(?:-(\d+))?", part.strip())
        if match is None:
            raise ValueError(f"Invalid slot mapping for Text-Fabric node {node}")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if end < start:
            raise ValueError(f"Reversed slot mapping for Text-Fabric node {node}")
        slots.append((start, end))
    if not slots:
        raise ValueError(f"Missing slot mapping for Text-Fabric node {node}")
    return slots[0][0], slots[-1][1]


def _sections(
    values: dict[int, str], oslots: dict[int, str], feature_name: str
) -> list[Section]:
    result: list[Section] = []
    for node, value in values.items():
        slot_value = oslots.get(node)
        if slot_value is None:
            raise ValueError(
                f"Text-Fabric {feature_name} node {node} has no slot mapping"
            )
        first_slot, last_slot = _slot_bounds(slot_value, node)
        result.append(Section(node, value, first_slot, last_slot))
    return sorted(result, key=lambda section: section.first_slot)


def _containing_section(
    child: Section, containers: list[Section], start_index: int
) -> tuple[Section, int]:
    index = start_index
    while index < len(containers) and containers[index].last_slot < child.first_slot:
        index += 1
    if index >= len(containers):
        raise ValueError(f"No containing section for Text-Fabric node {child.node}")
    container = containers[index]
    if child.first_slot < container.first_slot or child.last_slot > container.last_slot:
        raise ValueError(f"No containing section for Text-Fabric node {child.node}")
    return container, index


def extract_books(features: dict[str, str]) -> dict[str, dict[int, dict[int, str]]]:
    parsed = {
        name: _parse_node_feature(features[name], name)
        for name in ("oslots", "book", "chapter", "verse", "sign")
    }
    oslots = parsed["oslots"]
    books = _sections(parsed["book"], oslots, "book")
    chapters = _sections(parsed["chapter"], oslots, "chapter")
    verses = _sections(parsed["verse"], oslots, "verse")
    signs = parsed["sign"]

    extracted: dict[str, dict[int, dict[int, str]]] = {}
    book_index = 0
    chapter_index = 0
    for verse in verses:
        book, book_index = _containing_section(verse, books, book_index)
        chapter, chapter_index = _containing_section(verse, chapters, chapter_index)
        if book.value not in BOOKS:
            raise ValueError(f"Unsupported Samaritan Pentateuch book: {book.value}")
        try:
            chapter_number = int(chapter.value)
            verse_number = int(verse.value)
        except ValueError as exc:
            raise ValueError(
                f"Invalid chapter or verse number at Text-Fabric node {verse.node}"
            ) from exc

        missing_slot = next(
            (
                slot
                for slot in range(verse.first_slot, verse.last_slot + 1)
                if slot not in signs
            ),
            None,
        )
        if missing_slot is not None:
            raise ValueError(f"Missing sign value for Text-Fabric slot {missing_slot}")
        text = " ".join(
            "".join(
                signs[slot] for slot in range(verse.first_slot, verse.last_slot + 1)
            ).split()
        )
        if not text:
            raise ValueError(f"Empty text for Text-Fabric verse node {verse.node}")
        chapter_verses = extracted.setdefault(book.value, {}).setdefault(
            chapter_number, {}
        )
        if verse_number in chapter_verses:
            raise ValueError(
                f"Duplicate verse {book.value} {chapter_number}:{verse_number}"
            )
        chapter_verses[verse_number] = text
    return extracted


def square_to_samaritan(text: str) -> str:
    return text.translate(SQUARE_TO_SAMARITAN)


def _version_key(path: str) -> tuple[int, ...]:
    name = PurePosixPath(path).name
    if not re.fullmatch(r"\d+(?:\.\d+)*", name):
        return ()
    return tuple(int(part) for part in name.split("."))


def _select_prefix(paths: set[str]) -> str:
    candidates: list[str] = []
    for path in paths:
        pure_path = PurePosixPath(path)
        if pure_path.name != "otype.tf":
            continue
        prefix = "" if str(pure_path.parent) == "." else str(pure_path.parent)
        has_required_features = all(
            _feature_path(prefix, feature) in paths for feature in REQUIRED_FEATURES
        )
        if has_required_features:
            candidates.append(prefix)
    if not candidates:
        raise ValueError(
            "No complete Samaritan Pentateuch Text-Fabric feature set found"
        )
    return max(candidates, key=lambda prefix: (_version_key(prefix), prefix))


def _feature_path(prefix: str, feature: str) -> str:
    return f"{prefix}/{feature}.tf" if prefix else f"{feature}.tf"


def load_features(source_path: Path) -> tuple[dict[str, str], str]:
    source_path = Path(source_path)
    if source_path.is_dir():
        paths = {
            path.relative_to(source_path).as_posix()
            for path in source_path.rglob("*.tf")
        }
        prefix = _select_prefix(paths)
        return (
            {
                feature: (source_path / _feature_path(prefix, feature)).read_text(
                    encoding="utf-8"
                )
                for feature in REQUIRED_FEATURES
            },
            PurePosixPath(prefix).name if prefix else source_path.name,
        )

    if not source_path.is_file():
        raise ValueError(f"Dataset source does not exist: {source_path}")
    try:
        with ZipFile(source_path) as archive:
            paths = set(archive.namelist())
            prefix = _select_prefix(paths)
            return (
                {
                    feature: archive.read(_feature_path(prefix, feature)).decode(
                        "utf-8"
                    )
                    for feature in REQUIRED_FEATURES
                },
                PurePosixPath(prefix).name if prefix else source_path.stem,
            )
    except (BadZipFile, OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"Unable to read dataset archive: {source_path}") from exc


def _resolve_zenodo_record_api_url() -> str:
    request = Request(SOURCE_URL, method="HEAD")
    try:
        with urlopen(request) as response:
            resolved_url = response.geturl()
    except OSError as exc:
        raise ValueError("Unable to resolve Samaritan Pentateuch DOI") from exc

    parsed = urlparse(resolved_url)
    match = re.fullmatch(r"/records/(\d+)/?", parsed.path)
    if parsed.scheme != "https" or parsed.hostname != "zenodo.org" or match is None:
        raise ValueError(
            f"Samaritan Pentateuch DOI resolved unexpectedly: {resolved_url}"
        )
    return f"{ZENODO_RECORD_API_ROOT}/{match.group(1)}"


def download_latest_dataset(destination: Path) -> DownloadedDataset:
    record_api_url = _resolve_zenodo_record_api_url()
    try:
        with urlopen(record_api_url) as response:
            metadata = json_loads(response.read())
    except (OSError, ValueError) as exc:
        raise ValueError("Unable to read Samaritan Pentateuch Zenodo metadata") from exc

    if not isinstance(metadata, dict):
        raise ValueError("Invalid Samaritan Pentateuch Zenodo metadata")
    files = metadata.get("files")
    if not isinstance(files, list):
        raise ValueError("Samaritan Pentateuch Zenodo record has no files")
    archives = [
        entry
        for entry in files
        if isinstance(entry, dict)
        and isinstance(entry.get("key"), str)
        and entry["key"].lower().endswith(".zip")
        and isinstance(entry.get("links"), dict)
        and isinstance(entry["links"].get("self"), str)
    ]
    if not archives:
        raise ValueError("Samaritan Pentateuch Zenodo record has no ZIP archive")
    archive = max(
        archives,
        key=lambda entry: (
            entry.get("size") if isinstance(entry.get("size"), int) else 0
        ),
    )
    download_url = archive["links"]["self"]
    checksum = archive.get("checksum")
    expected_md5 = (
        checksum.removeprefix("md5:").lower()
        if isinstance(checksum, str) and checksum.startswith("md5:")
        else None
    )
    version = metadata.get("metadata", {}).get("version")
    version_label = version if isinstance(version, str) else "latest"
    size = archive.get("size") if isinstance(archive.get("size"), int) else 0
    version_doi_url = metadata.get("doi_url")
    if not isinstance(version_doi_url, str) or not version_doi_url.startswith(
        "https://doi.org/"
    ):
        raise ValueError("Samaritan Pentateuch Zenodo record has no version DOI")

    digest = hashlib.md5(usedforsecurity=False)
    try:
        with urlopen(download_url) as response, Path(destination).open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                digest.update(chunk)
    except OSError as exc:
        raise ValueError("Unable to download Samaritan Pentateuch dataset") from exc

    if expected_md5 is not None and digest.hexdigest() != expected_md5:
        raise ValueError("Downloaded Samaritan Pentateuch dataset checksum mismatch")
    return DownloadedDataset(version_label, size, version_doi_url)


def _chapter_payload(chapters: dict[int, dict[int, str]]) -> list[object | None]:
    result: list[object | None] = [None] * (max(chapters) + 1)
    for chapter_number, verses in chapters.items():
        verse_values: list[str | None] = [None] * (max(verses) + 1)
        for verse_number, text in verses.items():
            verse_values[verse_number] = text
        result[chapter_number] = {"verses": verse_values}
    return result


def _write_version(
    offline_dir: Path,
    extracted: dict[str, dict[int, dict[int, str]]],
    *,
    code: str,
    name: str,
    aliases: list[str],
    use_samaritan_script: bool,
    source_url: str,
) -> None:
    version_dir = Path(offline_dir) / code
    books_dir = version_dir / "books"
    books_dir.mkdir(parents=True, exist_ok=True)
    version_dir.joinpath("version.json").write_text(
        json_dumps(
            {
                "aliases": aliases,
                "code": code,
                "language": "SMP",
                "name": name,
                "system": "bible",
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    for title, spec in BOOKS.items():
        chapters = extracted[title]
        if use_samaritan_script:
            chapters = {
                chapter: {
                    verse: square_to_samaritan(text) for verse, text in verses.items()
                }
                for chapter, verses in chapters.items()
            }
        books_dir.joinpath(f"{spec.slug}.json").write_text(
            json_dumps(
                {
                    "aliases": list(spec.aliases),
                    "chapters": _chapter_payload(chapters),
                    "slug": spec.slug,
                    "source_url": source_url,
                    "title": spec.title,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )


def import_text_fabric(
    source_path: Path, offline_dir: Path, *, source_url: str = SOURCE_URL
) -> tuple[int, int, str]:
    features, dataset_version = load_features(source_path)
    extracted = extract_books(features)
    missing_books = set(BOOKS) - set(extracted)
    if missing_books:
        missing_list = ", ".join(sorted(missing_books))
        raise ValueError(f"Dataset is missing books: {missing_list}")

    _write_version(
        offline_dir,
        extracted,
        code="SP",
        name="Samaritan Pentateuch, Samaritan script",
        aliases=["SAMARITAN", "SAMARITANSCRIPT", "SPSAMARITAN"],
        use_samaritan_script=True,
        source_url=source_url,
    )
    _write_version(
        offline_dir,
        extracted,
        code="SPSQUARE",
        name="Samaritan Pentateuch, Square script",
        aliases=["SPSQ", "SQUARESP", "SQUARESCRIPT"],
        use_samaritan_script=False,
        source_url=source_url,
    )
    verse_count = sum(
        len(verses) for chapters in extracted.values() for verses in chapters.values()
    )
    return len(BOOKS), verse_count, dataset_version


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(
            "Usage: python -m tools.import_samaritan_pentateuch "
            "[dataset-directory-or-zip] <offline-dir>",
            file=sys.stderr,
        )
        return 2

    if len(sys.argv) == 2:
        offline_dir = Path(sys.argv[1])
        with tempfile.TemporaryDirectory() as temporary_dir:
            archive_path = Path(temporary_dir, "samaritan-pentateuch.zip")
            print(f"Downloading the latest dataset from {SOURCE_URL} ...")
            downloaded = download_latest_dataset(archive_path)
            if downloaded.size:
                print(
                    f"Downloaded {downloaded.version} "
                    f"({downloaded.size / 1_000_000:.1f} MB)"
                )
            book_count, verse_count, dataset_version = import_text_fabric(
                archive_path, offline_dir, source_url=downloaded.source_url
            )
    else:
        book_count, verse_count, dataset_version = import_text_fabric(
            Path(sys.argv[1]), Path(sys.argv[2])
        )
    print(
        f"Wrote {book_count} books with {verse_count} verse entries each for SP "
        f"and SPSQUARE from Text-Fabric {dataset_version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
