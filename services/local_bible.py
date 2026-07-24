import json
import logging
from pathlib import Path

from parsing import (
    build_passage_header,
    normalize_reference_lookup_key,
    superscript_leading_verse_numbers,
)
from state import DEFAULT_VERSION, EMPTY, InlinePassageResult


def _normalize_local_text(value) -> list[str]:
    if isinstance(value, str):
        text = superscript_leading_verse_numbers(value)
        return [text] if text else []
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, str):
                text = superscript_leading_verse_numbers(item)
                if text:
                    result.append(text)
        return result
    return []


def format_local_passage_entry(
    reference: str, entry, version: str = DEFAULT_VERSION, inline_details: bool = False
) -> str | InlinePassageResult:
    title = reference.strip()
    description = None
    text_parts: list[str]

    if isinstance(entry, dict):
        title = str(entry.get("title") or title).strip()
        description = entry.get("description")
        text_parts = _normalize_local_text(entry.get("text"))
    else:
        text_parts = _normalize_local_text(entry)

    if not text_parts:
        return EMPTY

    header = build_passage_header(title, version)
    final_text = "\n\n".join([header, *text_parts]).strip()
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


class LocalBibleClient:
    def __init__(self, base_path: Path):
        self._base_path = Path(base_path)
        self._cache: dict[str, dict[str, tuple[str, object]]] = {}

    async def close(self) -> None:
        return None

    def _version_path(self, version: str) -> Path:
        return self._base_path / f"{version.upper()}.json"

    def _load_version_entries(
        self, version: str
    ) -> dict[str, tuple[str, object]] | None:
        version_code = version.upper()
        if version_code in self._cache:
            return self._cache[version_code]

        path = self._version_path(version_code)
        if not path.exists():
            self._cache[version_code] = {}
            return self._cache[version_code]

        try:
            raw_data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logging.warning("Error loading offline Bible file %s: %s", path, exc)
            return None

        if not isinstance(raw_data, dict):
            logging.warning("Offline Bible file %s must contain a JSON object", path)
            return None

        normalized_entries = {
            normalize_reference_lookup_key(reference): (reference, entry)
            for reference, entry in raw_data.items()
            if isinstance(reference, str)
        }
        self._cache[version_code] = normalized_entries
        return normalized_entries

    async def get_passage(
        self, passage: str, version: str = DEFAULT_VERSION, inline_details: bool = False
    ) -> str | InlinePassageResult | None:
        entries = self._load_version_entries(version)
        if entries is None:
            return None

        lookup_key = normalize_reference_lookup_key(passage)
        if not lookup_key:
            return EMPTY

        entry = entries.get(lookup_key)
        if entry is None:
            return EMPTY

        reference, value = entry
        return format_local_passage_entry(
            reference, value, version=version, inline_details=inline_details
        )
