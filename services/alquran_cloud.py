import logging
import re
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from parsing import build_passage_header, format_numbered_verse_text
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
QURAN_REFERENCE_PATTERN = re.compile(
    r"(?i)^\s*"
    r"(?:qur(?:an|['’ʾ]an)|al(?:[\s-]+)qur(?:an|['’ʾ]an)|koran)"
    r"\s+"
    r"(\d{1,3})"
    r"(?:\:(\d{1,3})(?:-(\d{1,3}))?)?"
    r"\s*$"
)


@dataclass(frozen=True)
class QuranReference:
    surah: int
    start_ayah: int | None
    end_ayah: int | None


def parse_quran_reference(passage: str) -> QuranReference | None:
    normalized = " ".join(str(passage).split()).strip()
    if not normalized:
        return None

    match = QURAN_REFERENCE_PATTERN.fullmatch(normalized)
    if match is None:
        return None

    surah = int(match.group(1))
    start_ayah = int(match.group(2)) if match.group(2) else None
    end_ayah = int(match.group(3)) if match.group(3) else start_ayah
    if not 1 <= surah <= 114:
        return None
    if start_ayah is not None and start_ayah < 1:
        return None
    if end_ayah is not None and end_ayah < 1:
        return None
    if start_ayah is not None and end_ayah is not None and end_ayah < start_ayah:
        return None
    return QuranReference(surah=surah, start_ayah=start_ayah, end_ayah=end_ayah)


def format_quran_reference(reference: QuranReference) -> str:
    if reference.start_ayah is None:
        return f"Qurʾan {reference.surah}"
    if reference.end_ayah is None or reference.end_ayah == reference.start_ayah:
        return f"Qurʾan {reference.surah}:{reference.start_ayah}"
    return f"Qurʾan {reference.surah}:{reference.start_ayah}-{reference.end_ayah}"


def build_quran_passage_url(
    passage: str, version: str = DEFAULT_QURAN_VERSION
) -> str | None:
    del version
    reference = parse_quran_reference(passage)
    if reference is None:
        return None
    if reference.start_ayah is None:
        return f"{QURAN_PUBLIC_BASE_URL}/{reference.surah}"
    return (
        f"{QURAN_PUBLIC_BASE_URL}/{reference.surah}"
        f"?startingVerse={reference.start_ayah}"
    )


def parse_surah_payload(
    payload: dict[str, Any],
    version: str = DEFAULT_QURAN_VERSION,
    *,
    reference: QuranReference,
    inline_details: bool = False,
) -> str | InlinePassageResult:
    data = payload.get("data")
    if not isinstance(data, dict):
        return EMPTY

    ayahs = data.get("ayahs")
    if not isinstance(ayahs, list) or not ayahs:
        return EMPTY

    formatted_ayahs: list[str] = []
    for ayah in ayahs:
        if not isinstance(ayah, dict):
            continue
        number = ayah.get("numberInSurah")
        text = ayah.get("text")
        if not isinstance(number, int):
            continue
        formatted = format_numbered_verse_text(number, str(text or ""))
        if formatted:
            formatted_ayahs.append(formatted)

    if not formatted_ayahs:
        return EMPTY

    header = build_passage_header(format_quran_reference(reference), version)
    final_text = "\n\n".join([header, "\n".join(formatted_ayahs)]).strip()
    if not inline_details:
        return final_text

    content = " ".join(final_text.split())
    description = f"{content[:150]}..." if len(content) > 153 else content
    return InlinePassageResult(
        passage=final_text,
        result_id=f"quran/{format_quran_reference(reference)}/{version}",
        title=header,
        description=description,
        header_url=build_quran_passage_url(format_quran_reference(reference), version),
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

        url = f"{ALQURAN_CLOUD_API_BASE_URL}/surah/{reference.surah}/{edition_id}"
        params: dict[str, int] = {}
        if reference.start_ayah is not None:
            params["offset"] = reference.start_ayah - 1
            if reference.end_ayah is not None:
                params["limit"] = reference.end_ayah - reference.start_ayah + 1

        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logging.warning(
                "Error fetching %s from AlQuran Cloud with %s: %s",
                passage,
                edition_id,
                exc,
            )
            return None

        payload = response.json()
        if payload.get("status") != "OK":
            logging.warning(
                "AlQuran Cloud error for %s/%s: %s",
                passage,
                version,
                payload,
            )
            return None

        return parse_surah_payload(
            payload,
            version=version,
            reference=reference,
            inline_details=inline_details,
        )
