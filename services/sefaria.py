import logging
import re
from collections.abc import Iterable
from importlib import import_module
from typing import Any
from urllib.parse import quote

from parsing import build_passage_header, format_numbered_verse_text
from state import DEFAULT_VERSION, EMPTY, REQUEST_TIMEOUT_SECONDS, InlinePassageResult

try:
    httpx: Any = import_module("httpx")
except (
    ImportError
):  # pragma: no cover - exercised only in dependency-missing environments
    httpx = None

SEFARIA_API_BASE_URL = "https://sefaria.org/api/v3/texts"


def build_sefaria_passage_url(passage: str) -> str:
    normalized = " ".join(str(passage).split()).strip()
    if not normalized:
        return "https://sefaria.org"
    path = re.sub(r"\s+(\d)", r".\1", normalized, count=1).replace(" ", "_")
    return f"https://sefaria.org/{quote(path, safe='._:-')}"


def _flatten_text(value) -> Iterable[str]:
    if isinstance(value, str):
        text = " ".join(value.split()).strip()
        if text:
            yield text
        return
    if isinstance(value, list):
        for item in value:
            yield from _flatten_text(item)


def _extract_start_verse(reference: str) -> int | None:
    match = re.search(r":(\d+)", reference)
    if match is None:
        return None
    return int(match.group(1))


def _format_text_parts(reference: str, value) -> list[str]:
    start_verse = _extract_start_verse(reference)
    if (
        isinstance(value, list)
        and value
        and all(isinstance(item, str) for item in value)
    ):
        first_verse = start_verse or 1
        return [
            formatted
            for index, item in enumerate(value)
            if (formatted := format_numbered_verse_text(first_verse + index, item))
        ]
    return list(_flatten_text(value))


def parse_passage_payload(
    payload: dict, version: str = DEFAULT_VERSION, inline_details: bool = False
) -> str | InlinePassageResult:
    versions = payload.get("versions") or []
    if not versions:
        return EMPTY

    reference = str(payload.get("ref") or "").strip() or "Requested passage"
    text_parts = _format_text_parts(reference, versions[0].get("text"))
    if not text_parts:
        return EMPTY

    header = build_passage_header(reference, version)
    final_text = "\n\n".join([header, *text_parts]).strip()

    if not inline_details:
        return final_text

    content = " ".join(final_text.split())
    description = f"{content[:150]}..." if len(content) > 153 else content
    return InlinePassageResult(
        passage=final_text,
        result_id=f"{reference}/{version}",
        title=header,
        description=description,
    )


class SefariaClient:
    def __init__(self, version_titles: dict[str, str], client=None):
        if httpx is None:
            raise RuntimeError("httpx is required to use SefariaClient.")
        self._version_titles = {
            code.upper(): title for code, title in version_titles.items()
        }
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "scripturebot/1.0"},
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_passage(
        self, passage: str, version: str = DEFAULT_VERSION, inline_details: bool = False
    ) -> str | InlinePassageResult | None:
        version_title = self._version_titles.get(version.upper())
        if not version_title:
            logging.warning("No Sefaria version title configured for %s", version)
            return None

        url = f"{SEFARIA_API_BASE_URL}/{quote(passage, safe='')}"
        params = {
            "version": f"english|{version_title}",
            "return_format": "text_only",
        }
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logging.warning("Error fetching %s from Sefaria: %s", passage, exc)
            return None

        payload = response.json()
        if payload.get("warnings"):
            logging.info(
                "Sefaria warnings for %s/%s: %s", passage, version, payload["warnings"]
            )
        return parse_passage_payload(
            payload, version=version, inline_details=inline_details
        )
