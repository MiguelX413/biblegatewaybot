import logging
from importlib import import_module
from typing import Any

from quran import (
    QuranReference,
    parse_quran_reference,
)
from quran import (
    format_quran_reference as _format_quran_reference,
)
from services.quran_common import (
    build_inline_result,
    build_quran_passage_text,
    extract_formatted_ayahs,
)
from state import (
    DEFAULT_QURAN_VERSION,
    EMPTY,
    REQUEST_TIMEOUT_SECONDS,
    InlinePassageResult,
)
from versions import ALL_VERSIONS, get_alquran_cloud_edition_id, get_qf_translation_id

try:
    httpx: Any = import_module("httpx")
except ImportError:  # pragma: no cover - exercised only in dependency-missing envs
    httpx = None


ALQURAN_CLOUD_API_BASE_URL = "https://api.alquran.cloud/v1"
QURAN_PUBLIC_BASE_URL = "https://quran.com"
ALQURAN_CLOUD_EDITION_IDS: dict[str, str] = {
    version.code.upper(): version.alquran_cloud_edition_id
    for version in ALL_VERSIONS
    if version.alquran_cloud_edition_id is not None
}


def build_quran_passage_url(
    passage: str | QuranReference, version: str = DEFAULT_QURAN_VERSION
) -> str | None:
    reference = (
        passage
        if isinstance(passage, QuranReference)
        else parse_quran_reference(passage)
    )
    if reference is None:
        return None
    translation_id = get_qf_translation_id(version)
    query_suffix = f"?translations={translation_id}" if translation_id else ""
    if reference.start_ayah is None:
        return f"{QURAN_PUBLIC_BASE_URL}/{reference.start_surah}{query_suffix}"
    if reference.start_surah == reference.end_surah:
        if reference.end_ayah is None or reference.start_ayah == reference.end_ayah:
            return (
                f"{QURAN_PUBLIC_BASE_URL}/{reference.start_surah}/"
                f"{reference.start_ayah}{query_suffix}"
            )
        return (
            f"{QURAN_PUBLIC_BASE_URL}/{reference.start_surah}/"
            f"{reference.start_ayah}-{reference.end_ayah}{query_suffix}"
        )
    return (
        f"{QURAN_PUBLIC_BASE_URL}/{reference.start_surah}/{reference.start_ayah}"
        f"{query_suffix}"
    )


def format_quran_reference(
    reference: str | QuranReference, version: str = DEFAULT_QURAN_VERSION
) -> str:
    parsed_reference = (
        reference
        if isinstance(reference, QuranReference)
        else parse_quran_reference(reference)
    )
    if parsed_reference is None:
        return str(reference)
    return _format_quran_reference(parsed_reference, version)


def _extract_formatted_ayahs(
    payload: dict[str, Any],
    *,
    start_ayah: int | None = None,
    end_ayah: int | None = None,
) -> list[str]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return []

    ayahs = data.get("ayahs")
    if not isinstance(ayahs, list) or not ayahs:
        return []
    return extract_formatted_ayahs(
        ayahs,
        start_ayah=start_ayah,
        end_ayah=end_ayah,
        text_getter=lambda ayah: str(ayah.get("text") or "").strip(),
    )


def parse_surah_payload(
    payload: dict[str, Any],
    version: str = DEFAULT_QURAN_VERSION,
    *,
    reference: QuranReference,
    inline_details: bool = False,
) -> str | InlinePassageResult:
    formatted_ayahs = _extract_formatted_ayahs(
        payload,
        start_ayah=reference.start_ayah,
        end_ayah=reference.end_ayah,
    )
    if not formatted_ayahs:
        return EMPTY

    final_text = build_quran_passage_text(
        reference,
        version,
        [(reference.start_surah, formatted_ayahs)],
    )
    if final_text == EMPTY:
        return EMPTY
    if not inline_details:
        return final_text
    return build_inline_result(
        final_text,
        reference=reference,
        version=version,
        header_url=build_quran_passage_url(reference, version),
    )


class AlQuranCloudClient:
    def __init__(self, client=None):
        if httpx is None:
            raise RuntimeError("httpx is required to use AlQuranCloudClient.")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "scripturebot/1.0"},
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _fetch_surah_payload(
        self, surah: int, edition_id: str
    ) -> dict[str, Any] | None:
        url = f"{ALQURAN_CLOUD_API_BASE_URL}/surah/{surah}/{edition_id}"
        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logging.warning(
                "Error fetching surah %s from AlQuran Cloud with %s: %s",
                surah,
                edition_id,
                exc,
            )
            return None

        payload = response.json()
        if payload.get("status") != "OK":
            logging.warning(
                "AlQuran Cloud error for surah %s/%s: %s",
                surah,
                edition_id,
                payload,
            )
            return None
        return payload

    async def get_passage(
        self,
        passage: str,
        version: str = DEFAULT_QURAN_VERSION,
        inline_details: bool = False,
    ) -> str | InlinePassageResult | None:
        reference = parse_quran_reference(passage)
        if reference is None:
            return EMPTY

        edition_id = get_alquran_cloud_edition_id(version)
        if edition_id is None:
            logging.warning("No AlQuran Cloud edition configured for %s", version)
            return None

        surah_sections: list[tuple[int, list[str]]] = []
        for surah in range(reference.start_surah, reference.end_surah + 1):
            payload = await self._fetch_surah_payload(surah, edition_id)
            if payload is None:
                return None

            start_ayah = (
                reference.start_ayah if surah == reference.start_surah else None
            )
            end_ayah = reference.end_ayah if surah == reference.end_surah else None
            formatted_ayahs = _extract_formatted_ayahs(
                payload,
                start_ayah=start_ayah,
                end_ayah=end_ayah,
            )
            if not formatted_ayahs:
                return EMPTY
            surah_sections.append((surah, formatted_ayahs))

        final_text = build_quran_passage_text(reference, version, surah_sections)
        if final_text == EMPTY:
            return EMPTY
        if not inline_details:
            return final_text
        return build_inline_result(
            final_text,
            reference=reference,
            version=version,
            header_url=build_quran_passage_url(reference, version),
        )
