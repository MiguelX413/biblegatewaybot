import logging
from collections.abc import Iterable
from urllib.parse import quote

from state import DEFAULT_VERSION, EMPTY, InlinePassageResult, REQUEST_TIMEOUT_SECONDS

try:
    import httpx
except (
    ImportError
):  # pragma: no cover - exercised only in dependency-missing environments
    httpx = None

SEFARIA_API_BASE_URL = "https://www.sefaria.org/api/v3/texts"


def _flatten_text(value) -> Iterable[str]:
    if isinstance(value, str):
        text = " ".join(value.split()).strip()
        if text:
            yield text
        return
    if isinstance(value, list):
        for item in value:
            yield from _flatten_text(item)


def parse_passage_payload(
    payload: dict, version: str = DEFAULT_VERSION, inline_details: bool = False
) -> str | InlinePassageResult:
    versions = payload.get("versions") or []
    if not versions:
        return EMPTY

    text_parts = list(_flatten_text(versions[0].get("text")))
    if not text_parts:
        return EMPTY

    reference = str(payload.get("ref") or "").strip() or "Requested passage"
    header = f"{reference} ({version})"
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
