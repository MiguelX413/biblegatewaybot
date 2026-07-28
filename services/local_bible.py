import json
import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from json_compat import loads as json_loads
from parsing import (
    build_passage_header,
    find_requested_book,
    normalize_display_reference,
    normalize_reference_lookup_key,
    register_runtime_books,
    superscript_leading_verse_numbers,
    to_sup,
)
from state import DEFAULT_BIBLE_VERSION, EMPTY, InlinePassageResult
from versions import (
    BookData,
    LanguageCode,
    ScriptureSystemId,
    Version,
    register_runtime_book_slugs,
    register_runtime_version,
)

OFFLINE_BIBLES_PATH = Path(__file__).resolve().parent.parent / "offline"
OFFLINE_VERSIONS_PATH = OFFLINE_BIBLES_PATH / "versions"
OFFLINE_WORKS_PATH = OFFLINE_BIBLES_PATH / "works"


@dataclass(frozen=True)
class LocalSourceLinks:
    work_url: str | None
    chapter_urls: tuple[str | None, ...]


LOCAL_SOURCE_URLS: dict[str, dict[str, LocalSourceLinks]] = {}


@dataclass(frozen=True)
class LocalVersionMetadata:
    code: str
    name: str
    language: LanguageCode
    scripture_system: ScriptureSystemId
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class LocalWorkMetadata:
    version_code: str
    book: BookData
    path: Path
    source_links: LocalSourceLinks


@dataclass(frozen=True)
class LocalPassageBlock:
    text: str
    is_verse: bool


def _normalize_local_text(value) -> list[LocalPassageBlock]:
    if isinstance(value, str):
        text = superscript_leading_verse_numbers(value)
        return [LocalPassageBlock(text, is_verse=True)] if text else []
    if isinstance(value, list):
        result: list[LocalPassageBlock] = []
        for item in value:
            if isinstance(item, str):
                text = superscript_leading_verse_numbers(item)
                if text:
                    result.append(LocalPassageBlock(text, is_verse=True))
        return result
    return []


def _normalize_local_headers(value: object) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, str):
        result: list[str] = []
        for item in value:
            if isinstance(item, str):
                header = item.strip()
                if header:
                    result.append(header)
        return result
    return []


def _strip_leading_verse_number(text: str, verse: int) -> str:
    normalized = text.strip()
    if not normalized:
        return ""
    return re.sub(
        rf"^{verse}(?:-\d+)?\s+",
        "",
        normalized,
        count=1,
    ).strip()


def _format_structured_local_verse(chapter: int, verse: int, text: str) -> str:
    verse_text = _strip_leading_verse_number(text, verse)
    if not verse_text:
        return ""
    marker = str(chapter) if verse == 1 else to_sup(str(verse))
    return f"{marker} {verse_text}"


def _normalize_local_passage_part(entry: object) -> list[LocalPassageBlock]:
    if isinstance(entry, LocalPassageBlock):
        return [entry]
    if isinstance(entry, dict):
        parts: list[LocalPassageBlock] = []
        chapter = entry.get("chapter")
        verse = entry.get("verse")
        text = entry.get("text")
        if (
            isinstance(chapter, int)
            and isinstance(verse, int)
            and isinstance(text, str)
        ):
            formatted = _format_structured_local_verse(chapter, verse, text)
            if formatted:
                parts.append(LocalPassageBlock(formatted, is_verse=True))
        return parts
    if isinstance(entry, Sequence) and not isinstance(entry, str):
        parts = []
        for item in entry:
            parts.extend(_normalize_local_passage_part(item))
        return parts
    return _normalize_local_text(entry)


def _join_local_passage_blocks(blocks: Sequence[LocalPassageBlock]) -> str:
    paragraphs: list[str] = []
    verse_run: list[str] = []

    for block in blocks:
        if block.is_verse:
            verse_run.append(block.text)
            continue
        if verse_run:
            paragraphs.append("\n".join(verse_run))
            verse_run.clear()
        paragraphs.append(block.text)

    if verse_run:
        paragraphs.append("\n".join(verse_run))
    return "\n\n".join(paragraphs)


def _parse_reference_components(
    reference: str,
) -> tuple[str, int, int | None, int, int | None] | None:
    requested_book = find_requested_book(reference)
    if requested_book is None:
        return None

    _, book_title = requested_book
    normalized = " ".join(reference.split()).strip()
    chapter_match = re.fullmatch(
        rf"{re.escape(book_title)}\s+(\d+)(?:-(\d+))?$", normalized
    )
    if chapter_match is not None:
        start_chapter = int(chapter_match.group(1))
        end_chapter = int(chapter_match.group(2) or start_chapter)
        return book_title, start_chapter, None, end_chapter, None

    match = re.fullmatch(
        rf"{re.escape(book_title)}\s+(\d+)(?::(\d+))?(?:-(?:(\d+):)?(\d+))?$",
        normalized,
    )
    if match is None:
        return None

    start_chapter = int(match.group(1))
    start_verse = int(match.group(2)) if match.group(2) else None
    end_verse: int | None
    if match.group(4) is not None:
        end_chapter = int(match.group(3) or start_chapter)
        end_verse = int(match.group(4))
    else:
        end_chapter = start_chapter
        end_verse = start_verse

    return book_title, start_chapter, start_verse, end_chapter, end_verse


def _verse_sort_key(reference: str) -> tuple[int, int]:
    match = re.search(r"(\d+):(\d+)$", reference)
    if match is None:
        return 0, 0
    return int(match.group(1)), int(match.group(2))


def _format_composed_reference(
    book_title: str,
    start_chapter: int,
    start_verse: int | None,
    end_chapter: int,
    end_verse: int | None,
) -> str:
    if start_verse is None and end_verse is None:
        if start_chapter == end_chapter:
            return f"{book_title} {start_chapter}"
        return normalize_display_reference(
            f"{book_title} {start_chapter}-{end_chapter}"
        )

    start = f"{book_title} {start_chapter}"
    if start_verse is not None:
        start = f"{start}:{start_verse}"

    if start_chapter == end_chapter and start_verse == end_verse:
        return start
    if (
        start_chapter == end_chapter
        and start_verse is not None
        and end_verse is not None
    ):
        return normalize_display_reference(f"{start}-{end_verse}")

    end = str(end_chapter)
    if end_verse is not None:
        end = f"{end}:{end_verse}"
    return normalize_display_reference(f"{start}-{end}")


def _compose_local_passage(
    passage: str, entries: dict[str, tuple[str, object]]
) -> tuple[str, list[object]] | None:
    components = _parse_reference_components(passage)
    if components is None:
        return None

    book_title, start_chapter, start_verse, end_chapter, end_verse = components
    verse_entries: list[tuple[str, object]] = []
    for original_reference, entry in entries.values():
        parsed = _parse_reference_components(original_reference)
        if parsed is None:
            continue
        (
            entry_book_title,
            entry_start_chapter,
            entry_start_verse,
            entry_end_chapter,
            entry_end_verse,
        ) = parsed
        if (
            entry_book_title != book_title
            or entry_start_verse is None
            or entry_end_verse is None
            or entry_start_chapter != entry_end_chapter
            or entry_start_verse != entry_end_verse
        ):
            continue
        if entry_start_chapter < start_chapter or entry_start_chapter > end_chapter:
            continue
        if (
            start_verse is not None
            and entry_start_chapter == start_chapter
            and entry_start_verse < start_verse
        ):
            continue
        if (
            end_verse is not None
            and entry_start_chapter == end_chapter
            and entry_start_verse > end_verse
        ):
            continue
        verse_entries.append((original_reference, entry))

    if not verse_entries:
        return None

    verse_entries.sort(key=lambda item: _verse_sort_key(item[0]))
    text_entries = [entry for _, entry in verse_entries]
    if not any(_normalize_local_passage_part(entry) for entry in text_entries):
        return None

    reference_title = _format_composed_reference(
        book_title, start_chapter, start_verse, end_chapter, end_verse
    )
    return reference_title, text_entries


def _entries_from_chapters(
    book_title: str, chapters: object
) -> dict[str, tuple[str, object]] | None:
    if not isinstance(chapters, list):
        return None

    entries: dict[str, tuple[str, object]] = {}
    work_zero: tuple[object, ...] = ()
    for chapter_index, chapter in enumerate(chapters):
        if chapter is None:
            continue
        if not isinstance(chapter, dict):
            return None

        verses = chapter.get("verses")
        headers = chapter.get("headers", {})
        if not isinstance(verses, list):
            return None
        if not isinstance(headers, Mapping):
            return None

        normalized_headers: dict[int, list[str]] = {}
        for raw_verse, raw_headers in headers.items():
            try:
                verse_number = int(raw_verse)
            except TypeError, ValueError:
                return None
            if verse_number < 0:
                return None
            if not isinstance(raw_headers, list):
                return None
            header_values = _normalize_local_headers(raw_headers)
            if not header_values:
                continue
            normalized_headers[verse_number] = header_values

        for verse in verses:
            if verse is not None and not isinstance(verse, str):
                return None

        chapter_number = chapter_index
        zero_text = verses[0].strip() if verses and verses[0] else ""
        zero_content: list[object] = [
            *(
                LocalPassageBlock(header, is_verse=False)
                for header in normalized_headers.get(0, ())
            ),
            *([LocalPassageBlock(zero_text, is_verse=False)] if zero_text else []),
        ]

        if chapter_number == 0:
            if any(verse is not None for verse in verses[1:]):
                return None
            work_zero = tuple(zero_content)
            continue

        for verse_index, verse in enumerate(verses):
            if verse_index == 0:
                continue
            if verse is None:
                continue
            if not isinstance(verse, str):
                return None
            reference = f"{book_title} {chapter_number}:{verse_index}"
            entry: list[object] = []
            if chapter_number == 1 and verse_index == 1:
                entry.extend(work_zero)
            if verse_index == 1:
                entry.extend(zero_content)
            entry.extend(
                LocalPassageBlock(header, is_verse=False)
                for header in normalized_headers.get(verse_index, ())
            )
            entry.append(
                {
                    "chapter": chapter_number,
                    "verse": verse_index,
                    "text": verse,
                }
            )
            entries[normalize_reference_lookup_key(reference)] = (
                reference,
                tuple(entry),
            )
    return entries


def format_local_passage_entry(
    reference: str,
    entry,
    version: str = DEFAULT_BIBLE_VERSION,
    inline_details: bool = False,
) -> str | InlinePassageResult:
    title = reference.strip()
    description = None
    text_parts: list[LocalPassageBlock]

    if isinstance(entry, Sequence) and not isinstance(entry, str):
        text_parts = []
        for item in entry:
            text_parts.extend(_normalize_local_passage_part(item))
    elif isinstance(entry, dict):
        title = str(entry.get("title") or title).strip()
        description = entry.get("description")
        text_value = entry.get("text")
        if isinstance(text_value, Sequence) and not isinstance(text_value, str):
            text_parts = []
            for item in text_value:
                text_parts.extend(_normalize_local_passage_part(item))
        else:
            text_parts = _normalize_local_passage_part(entry)
    else:
        text_parts = _normalize_local_passage_part(entry)

    if not text_parts:
        return EMPTY

    header = build_passage_header(title, version)
    passage_body = _join_local_passage_blocks(text_parts)
    final_text = f"{header}\n\n{passage_body}".strip()
    if not inline_details:
        return final_text

    inline_description = (
        str(description).strip()
        if isinstance(description, str) and description.strip()
        else " ".join(final_text.split())[:150]
    )
    if len(inline_description) > 153:
        inline_description = f"{inline_description[:150]}..."
    return InlinePassageResult(
        passage=final_text,
        result_id=f"{title}/{version}",
        title=header,
        description=inline_description,
    )


def get_local_passage_url(passage: str, version: str) -> str | None:
    requested_book = find_requested_book(passage)
    if requested_book is None:
        return None
    book_slug, _ = requested_book
    source_links = LOCAL_SOURCE_URLS.get(version.upper(), {}).get(book_slug)
    if source_links is None:
        return None

    components = _parse_reference_components(passage)
    if components is None:
        return source_links.work_url

    _, start_chapter, _, _, _ = components
    if 0 <= start_chapter < len(source_links.chapter_urls):
        chapter_url = source_links.chapter_urls[start_chapter]
        if chapter_url:
            return chapter_url
    return source_links.work_url


class LocalBibleClient:
    def __init__(self, base_path: Path | None = None):
        self._base_path = (
            Path(base_path) if base_path is not None else OFFLINE_BIBLES_PATH
        )
        self._versions_path = self._base_path / "versions"
        self._works_path = self._base_path / "works"
        self._cache: dict[str, dict[str, tuple[str, object]]] = {}
        self._version_metadata_by_code: dict[str, LocalVersionMetadata] = {}
        self._works_by_version: dict[str, list[LocalWorkMetadata]] = {}
        self._legacy_paths_by_version: dict[str, Path] = {}
        self._scan_offline_versions()

    async def close(self) -> None:
        return None

    def _parse_version_metadata(self, raw_data: object) -> LocalVersionMetadata | None:
        if not isinstance(raw_data, dict):
            return None

        code = raw_data.get("code")
        name = raw_data.get("name")
        language = raw_data.get("language")
        scripture_system = raw_data.get("system")
        aliases = raw_data.get("aliases", [])
        if (
            not isinstance(code, str)
            or not code.strip()
            or not isinstance(name, str)
            or not name.strip()
            or not isinstance(language, str)
            or not isinstance(scripture_system, str)
            or not isinstance(aliases, list)
        ):
            return None

        try:
            language_code = LanguageCode(language.upper())
            system_id = ScriptureSystemId(scripture_system.lower())
        except ValueError:
            return None

        return LocalVersionMetadata(
            code=code.strip().upper(),
            name=name.strip(),
            language=language_code,
            scripture_system=system_id,
            aliases=tuple(
                alias.strip()
                for alias in aliases
                if isinstance(alias, str) and alias.strip()
            ),
        )

    def _parse_work_metadata(
        self, path: Path, raw_data: object
    ) -> LocalWorkMetadata | None:
        if not isinstance(raw_data, dict):
            return None

        version_code = raw_data.get("version_code")
        title = raw_data.get("title")
        slug = raw_data.get("slug")
        aliases = raw_data.get("aliases")
        source_url = raw_data.get("source_url")
        chapters = raw_data.get("chapters")
        if (
            not isinstance(version_code, str)
            or not version_code.strip()
            or not isinstance(title, str)
            or not title.strip()
            or not isinstance(slug, str)
            or not slug.strip()
            or not isinstance(aliases, list)
            or not all(isinstance(alias, str) and alias.strip() for alias in aliases)
            or (
                source_url is not None
                and (not isinstance(source_url, str) or not source_url.strip())
            )
            or not isinstance(chapters, list)
        ):
            return None

        chapter_urls: list[str | None] = []
        for chapter in chapters:
            if chapter is None:
                chapter_urls.append(None)
                continue
            if not isinstance(chapter, dict):
                return None
            chapter_source_url = chapter.get("source_url")
            if chapter_source_url is None:
                chapter_urls.append(None)
                continue
            if (
                not isinstance(chapter_source_url, str)
                or not chapter_source_url.strip()
            ):
                return None
            chapter_urls.append(chapter_source_url.strip())

        book: BookData = {
            "title": title.strip(),
            "slug": slug.strip().lower(),
            "aliases": tuple(alias.strip() for alias in aliases),
        }
        if isinstance(source_url, str) and source_url.strip():
            book["source_url"] = source_url.strip()

        return LocalWorkMetadata(
            version_code=version_code.strip().upper(),
            book=book,
            path=path,
            source_links=LocalSourceLinks(
                work_url=source_url.strip() if isinstance(source_url, str) else None,
                chapter_urls=tuple(chapter_urls),
            ),
        )

    def _merge_books(self, works: list[LocalWorkMetadata]) -> tuple[BookData, ...]:
        books_by_slug: dict[str, BookData] = {}
        for work in works:
            book = work.book
            existing = books_by_slug.get(book["slug"])
            if existing is None:
                books_by_slug[book["slug"]] = book
                continue
            if existing["title"] != book["title"]:
                raise ValueError(
                    "Conflicting offline book metadata for "
                    f"{work.version_code}/{book['slug']}"
                )
            if existing.get("source_url") != book.get("source_url"):
                raise ValueError(
                    "Conflicting offline book URLs for "
                    f"{work.version_code}/{book['slug']}"
                )
            merged: BookData = {
                "title": book["title"],
                "slug": book["slug"],
                "aliases": tuple(dict.fromkeys(existing["aliases"] + book["aliases"])),
            }
            if "source_url" in book:
                merged["source_url"] = book["source_url"]
            books_by_slug[book["slug"]] = merged
        return tuple(books_by_slug.values())

    def _scan_offline_versions(self) -> None:
        LOCAL_SOURCE_URLS.clear()

        if self._versions_path.exists():
            for path in sorted(self._versions_path.glob("*.json")):
                try:
                    raw_data = json_loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    logging.warning(
                        "Error loading offline version file %s: %s", path, exc
                    )
                    continue

                metadata = self._parse_version_metadata(raw_data)
                if metadata is None:
                    logging.warning("Invalid offline version metadata file %s", path)
                    continue
                self._version_metadata_by_code[metadata.code] = metadata

        if self._works_path.exists():
            for path in sorted(self._works_path.glob("*.json")):
                try:
                    raw_data = json_loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    logging.warning("Error loading offline work file %s: %s", path, exc)
                    continue

                work = self._parse_work_metadata(path, raw_data)
                if work is None:
                    logging.warning("Invalid offline work metadata file %s", path)
                    continue
                self._works_by_version.setdefault(work.version_code, []).append(work)

        for path in sorted(self._base_path.glob("*.json")):
            self._legacy_paths_by_version[path.stem.upper()] = path

        for version_code, version_metadata in self._version_metadata_by_code.items():
            works = self._works_by_version.get(version_code, [])
            if not works:
                continue
            try:
                books = self._merge_books(works)
            except ValueError as exc:
                logging.warning("%s", exc)
                continue

            LOCAL_SOURCE_URLS[version_code] = {
                work.book["slug"]: work.source_links for work in works
            }
            register_runtime_books(books, version_metadata.scripture_system)
            register_runtime_book_slugs(tuple(book["slug"] for book in books))
            register_runtime_version(
                version_metadata.scripture_system,
                version_metadata.language,
                Version.local(
                    version_metadata.name,
                    version_metadata.code,
                    frozenset(book["slug"] for book in books),
                    aliases=version_metadata.aliases,
                ),
            )

    def _load_structured_work_entries(
        self, version_code: str
    ) -> dict[str, tuple[str, object]] | None:
        works = self._works_by_version.get(version_code, [])
        if not works:
            return {}

        normalized_entries: dict[str, tuple[str, object]] = {}
        for work in works:
            try:
                raw_data = json_loads(work.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logging.warning(
                    "Error loading offline work file %s: %s", work.path, exc
                )
                return None

            chapters = raw_data.get("chapters")
            if chapters is not None:
                chapter_entries = _entries_from_chapters(work.book["title"], chapters)
                if chapter_entries is None:
                    logging.warning(
                        "Offline work file %s must contain valid chapter arrays",
                        work.path,
                    )
                    return None
                normalized_entries.update(chapter_entries)
                continue

            passages = raw_data.get("passages")
            if not isinstance(passages, dict):
                logging.warning(
                    "Offline work file %s must contain either chapters or passages",
                    work.path,
                )
                return None

            normalized_entries.update(
                {
                    normalize_reference_lookup_key(reference): (reference, entry)
                    for reference, entry in passages.items()
                    if isinstance(reference, str)
                }
            )
        return normalized_entries

    def _load_legacy_version_entries(
        self, version_code: str
    ) -> dict[str, tuple[str, object]] | None:
        path = self._legacy_paths_by_version.get(version_code)
        if path is None:
            return {}

        try:
            raw_data = json_loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logging.warning("Error loading offline Bible file %s: %s", path, exc)
            return None

        if not isinstance(raw_data, dict):
            logging.warning("Offline Bible file %s must contain a JSON object", path)
            return None

        return {
            normalize_reference_lookup_key(reference): (reference, entry)
            for reference, entry in raw_data.items()
            if isinstance(reference, str)
        }

    def _load_version_entries(
        self, version: str
    ) -> dict[str, tuple[str, object]] | None:
        version_code = version.upper()
        if version_code in self._cache:
            return self._cache[version_code]

        structured_entries = self._load_structured_work_entries(version_code)
        if structured_entries is None:
            return None
        if structured_entries:
            self._cache[version_code] = structured_entries
            return structured_entries

        legacy_entries = self._load_legacy_version_entries(version_code)
        if legacy_entries is None:
            return None
        self._cache[version_code] = legacy_entries
        return legacy_entries

    async def get_passage(
        self,
        passage: str,
        version: str = DEFAULT_BIBLE_VERSION,
        inline_details: bool = False,
    ) -> str | InlinePassageResult | None:
        entries = self._load_version_entries(version)
        if entries is None:
            return None

        lookup_key = normalize_reference_lookup_key(passage)
        if not lookup_key:
            return EMPTY

        entry = entries.get(lookup_key)
        if entry is None:
            composed = _compose_local_passage(passage, entries)
            if composed is None:
                return EMPTY
            reference, text_parts = composed
            return format_local_passage_entry(
                reference, text_parts, version=version, inline_details=inline_details
            )

        reference, value = entry
        return format_local_passage_entry(
            reference, value, version=version, inline_details=inline_details
        )
