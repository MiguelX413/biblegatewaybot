import logging
from importlib import import_module
from typing import Any

from parsing import format_numbered_verse_text
from quran import (
    QuranReference,
    format_quran_machine_reference,
    format_quran_reference,
    parse_quran_reference,
    quran_surah_display_name,
)
from state import (
    DEFAULT_QURAN_VERSION,
    EMPTY,
    REQUEST_TIMEOUT_SECONDS,
    InlinePassageResult,
)

try:
    httpx: Any = import_module("httpx")
except ImportError:  # pragma: no cover - exercised only in dependency-missing envs
    httpx = None


ALQURAN_CLOUD_API_BASE_URL = "https://api.alquran.cloud/v1"
QURAN_PUBLIC_BASE_URL = "https://quran.com"
ALQURAN_CLOUD_EDITION_IDS: dict[str, str] = {
    "UTHMANI": "quran-uthmani",
    "QSI": "en.sahih",
    "QPICK": "en.pickthall",
    "QYUSUF": "en.yusufali",
    "QAYATI": "fa.ayati",
    "QFOOL": "fa.fooladvand",
    "QSODIK": "uz.sodik",
    "QJAL": "ur.jalandhry",
    "QDIYANET": "tr.diyanet",
    "QKULIEV": "ru.kuliev",
}


def build_quran_passage_url(
    passage: str | QuranReference, version: str = DEFAULT_QURAN_VERSION
) -> str | None:
    del version
    reference = (
        passage
        if isinstance(passage, QuranReference)
        else parse_quran_reference(passage)
    )
    if reference is None:
        return None
    if reference.start_ayah is None:
        return f"{QURAN_PUBLIC_BASE_URL}/{reference.start_surah}"
    return (
        f"{QURAN_PUBLIC_BASE_URL}/{reference.start_surah}"
        f"?startingVerse={reference.start_ayah}"
    )


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

    formatted_ayahs: list[str] = []
    for ayah in ayahs:
        if not isinstance(ayah, dict):
            continue
        number = ayah.get("numberInSurah")
        text = ayah.get("text")
        if not isinstance(number, int):
            continue
        if start_ayah is not None and number < start_ayah:
            continue
        if end_ayah is not None and number > end_ayah:
            continue
        formatted = format_numbered_verse_text(number, str(text or ""))
        if formatted:
            formatted_ayahs.append(formatted)
    return formatted_ayahs


def _build_quran_passage_text(
    reference: QuranReference,
    version: str,
    surah_sections: list[tuple[int, list[str]]],
) -> str:
    header = format_quran_reference(reference, version)
    if not surah_sections:
        return EMPTY

    if len(surah_sections) == 1:
        body = "\n".join(surah_sections[0][1]).strip()
    else:
        blocks = []
        for surah_number, ayahs in surah_sections:
            if not ayahs:
                continue
            surah_header = f"{quran_surah_display_name(surah_number)} ({surah_number})"
            blocks.append(f"{surah_header}\n\n" + "\n".join(ayahs))
        body = "\n\n".join(blocks).strip()

    if not body:
        return EMPTY
    return f"{header}\n\n{body}"


def _build_inline_result(
    final_text: str,
    *,
    reference: QuranReference,
    version: str,
) -> InlinePassageResult:
    content = " ".join(final_text.split())
    description = f"{content[:150]}..." if len(content) > 153 else content
    return InlinePassageResult(
        passage=final_text,
        result_id=f"quran/{format_quran_machine_reference(reference)}/{version}",
        title=format_quran_reference(reference, version),
        description=description,
        header_url=build_quran_passage_url(reference, version),
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

    final_text = _build_quran_passage_text(
        reference,
        version,
        [(reference.start_surah, formatted_ayahs)],
    )
    if final_text == EMPTY:
        return EMPTY
    if not inline_details:
        return final_text
    return _build_inline_result(final_text, reference=reference, version=version)


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

        edition_id = ALQURAN_CLOUD_EDITION_IDS.get(version.upper())
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

        final_text = _build_quran_passage_text(reference, version, surah_sections)
        if final_text == EMPTY:
            return EMPTY
        if not inline_details:
            return final_text
        return _build_inline_result(final_text, reference=reference, version=version)
