import logging
import time
import unicodedata
from importlib import import_module
from typing import Any

from quran import parse_quran_reference
from services.alquran_cloud import AlQuranCloudClient, build_quran_passage_url
from services.quran_common import (
    build_inline_result,
    build_quran_passage_text,
    clean_quran_translation_text,
    extract_formatted_ayahs,
)
from state import (
    DEFAULT_QURAN_VERSION,
    EMPTY,
    REQUEST_TIMEOUT_SECONDS,
    InlinePassageResult,
)
from versions import get_qf_translation_hints, get_qf_translation_id

try:
    httpx: Any = import_module("httpx")
except ImportError:  # pragma: no cover - exercised only in dependency-missing envs
    httpx = None


AUTH_BASE_BY_ENV = {
    "prelive": "https://prelive-oauth2.quran.foundation",
    "production": "https://oauth2.quran.foundation",
}
API_BASE_BY_ENV = {
    "prelive": "https://apis-prelive.quran.foundation",
    "production": "https://apis.quran.foundation",
}
TRANSLATIONS_PATH = "/content/api/v4/resources/translations"
CHAPTERS_PATH = "/content/api/v4/chapters"


def _normalize_catalog_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(character for character in normalized if character.isalnum())


def _resolve_qf_env(env: str | None) -> str:
    normalized = (env or "prelive").strip().casefold()
    if normalized in AUTH_BASE_BY_ENV:
        return normalized
    if "prelive" in normalized:
        return "prelive"
    if "oauth2.quran.foundation" in normalized or "apis.quran.foundation" in normalized:
        return "production"
    return "prelive"


def _extract_arabic_text(verse: dict[str, object]) -> str:
    words = verse.get("words")
    if not isinstance(words, list) or not words:
        return ""

    parts: list[str] = []
    for word in words:
        if not isinstance(word, dict):
            continue
        text = word.get("text_uthmani")
        if not isinstance(text, str) or not text:
            continue
        parts.append(text)
    return " ".join(parts).strip()


def _extract_translation_text(verse: dict[str, object]) -> str:
    translations = verse.get("translations")
    if not isinstance(translations, list) or not translations:
        return ""
    first_translation = translations[0]
    if not isinstance(first_translation, dict):
        return ""
    text = first_translation.get("text")
    if not isinstance(text, str):
        return ""
    return clean_quran_translation_text(text)


class QuranFoundationClient:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        env: str | None,
        fallback_client: AlQuranCloudClient | None = None,
        client=None,
    ):
        if httpx is None:
            raise RuntimeError("httpx is required to use QuranFoundationClient.")
        self._env = _resolve_qf_env(env)
        self._client_id = client_id
        self._client_secret = client_secret
        self._fallback_client = fallback_client
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "scripturebot/1.0"},
        )
        self._access_token: str | None = None
        self._access_token_expires_at: float = 0.0
        self._translation_catalog: list[dict[str, object]] | None = None
        self._translation_ids_by_version: dict[str, int | None] = {}
        self._chapter_verse_counts: dict[int, int] | None = None
        self._verses_api_unavailable = False

    async def initialize(self) -> bool:
        return await self._load_translation_catalog() is not None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
        if self._fallback_client is not None:
            await self._fallback_client.close()

    async def _request_access_token(self) -> str | None:
        auth_base_url = AUTH_BASE_BY_ENV[self._env]
        try:
            response = await self._client.post(
                f"{auth_base_url}/oauth2/token",
                auth=(self._client_id, self._client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "client_credentials", "scope": "content"},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logging.warning("Quran Foundation token request failed: %s", exc)
            return None

        payload = response.json()
        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if not isinstance(access_token, str) or not isinstance(expires_in, int):
            logging.warning("Unexpected Quran Foundation token payload: %s", payload)
            return None

        self._access_token = access_token
        self._access_token_expires_at = time.monotonic() + max(expires_in - 60, 1)
        return access_token

    async def _get_access_token(self) -> str | None:
        if (
            self._access_token is not None
            and time.monotonic() < self._access_token_expires_at
        ):
            return self._access_token
        return await self._request_access_token()

    async def _authorized_get(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        retry_on_401: bool = True,
    ) -> dict[str, object] | None:
        access_token = await self._get_access_token()
        if access_token is None:
            return None

        api_base_url = API_BASE_BY_ENV[self._env]
        try:
            response = await self._client.get(
                f"{api_base_url}{path}",
                params=params,
                headers={
                    "x-auth-token": access_token,
                    "x-client-id": self._client_id,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401 and retry_on_401:
                self._access_token = None
                self._access_token_expires_at = 0.0
                return await self._authorized_get(
                    path,
                    params=params,
                    retry_on_401=False,
                )
            logging.warning("Quran Foundation request failed for %s: %s", path, exc)
            return None
        except httpx.HTTPError as exc:
            logging.warning("Quran Foundation request failed for %s: %s", path, exc)
            return None
        payload = response.json()
        if not isinstance(payload, dict):
            logging.warning(
                "Unexpected Quran Foundation payload for %s: %s", path, payload
            )
            return None
        return payload

    async def _load_translation_catalog(self) -> list[dict[str, object]] | None:
        if self._translation_catalog is not None:
            return self._translation_catalog
        payload = await self._authorized_get(TRANSLATIONS_PATH)
        if payload is None:
            return None
        translations = payload.get("translations")
        if not isinstance(translations, list):
            logging.warning(
                "Unexpected Quran Foundation translations payload: %s", payload
            )
            return None
        self._translation_catalog = [
            translation for translation in translations if isinstance(translation, dict)
        ]
        return self._translation_catalog

    async def _resolve_translation_id(self, version: str) -> int | None:
        version_code = version.upper()
        if version_code in self._translation_ids_by_version:
            return self._translation_ids_by_version[version_code]

        explicit_translation_id = get_qf_translation_id(version)
        if explicit_translation_id is not None:
            self._translation_ids_by_version[version_code] = explicit_translation_id
            return explicit_translation_id

        hints = get_qf_translation_hints(version)
        if not hints:
            self._translation_ids_by_version[version_code] = None
            return None

        translations = await self._load_translation_catalog()
        if translations is None:
            return None

        normalized_hints = {_normalize_catalog_text(hint) for hint in hints}
        for translation in translations:
            translation_id = translation.get("id")
            if not isinstance(translation_id, int):
                continue
            candidates = {
                _normalize_catalog_text(str(translation.get("name") or "")),
                _normalize_catalog_text(str(translation.get("author_name") or "")),
                _normalize_catalog_text(str(translation.get("slug") or "")),
            }
            translated_name = translation.get("translated_name")
            if isinstance(translated_name, dict):
                candidates.add(
                    _normalize_catalog_text(str(translated_name.get("name") or ""))
                )
            if normalized_hints & candidates:
                self._translation_ids_by_version[version_code] = translation_id
                return translation_id

        english_candidates: list[str] = []
        for translation in translations:
            language_name = str(translation.get("language_name") or "").casefold()
            if language_name != "english":
                continue
            name = str(translation.get("name") or "").strip()
            author_name = str(translation.get("author_name") or "").strip()
            if name and author_name:
                english_candidates.append(f"{name} — {author_name}")
            elif name:
                english_candidates.append(name)
        logging.warning(
            "No Quran Foundation translation ID matched %s. "
            "Hints=%s. English catalog samples=%s",
            version,
            hints,
            english_candidates[:12],
        )
        self._translation_ids_by_version[version_code] = None
        return None

    async def _load_chapter_verse_counts(self) -> dict[int, int] | None:
        if self._chapter_verse_counts is not None:
            return self._chapter_verse_counts
        payload = await self._authorized_get(CHAPTERS_PATH)
        if payload is None:
            return None
        chapters = payload.get("chapters")
        if not isinstance(chapters, list):
            logging.warning("Unexpected Quran Foundation chapters payload: %s", payload)
            return None

        counts: dict[int, int] = {}
        for chapter in chapters:
            if not isinstance(chapter, dict):
                continue
            chapter_id = chapter.get("id")
            verses_count = chapter.get("verses_count")
            if not isinstance(chapter_id, int) or not isinstance(verses_count, int):
                continue
            counts[chapter_id] = verses_count
        self._chapter_verse_counts = counts
        return counts

    async def _fetch_verse_by_key(
        self,
        surah: int,
        ayah: int,
        *,
        translation_id: int | None,
    ) -> dict[str, object] | None:
        params: dict[str, str]
        if translation_id is None:
            params = {"words": "true", "word_fields": "text_uthmani"}
        else:
            params = {"translations": str(translation_id)}

        payload = await self._authorized_get(
            f"/content/api/v4/verses/by_key/{surah}:{ayah}",
            params=params,
        )
        if payload is None:
            return None
        verse = payload.get("verse")
        if not isinstance(verse, dict):
            logging.warning(
                "Unexpected Quran Foundation by_key payload for %s:%s: %s",
                surah,
                ayah,
                payload,
            )
            return None
        return verse

    async def _fetch_surah_verses_via_by_key(
        self,
        surah: int,
        *,
        translation_id: int | None,
        start_ayah: int | None,
        end_ayah: int | None,
    ) -> list[dict[str, object]] | None:
        if start_ayah is None or end_ayah is None:
            chapter_verse_counts = await self._load_chapter_verse_counts()
            if chapter_verse_counts is None:
                return None
            max_ayah = chapter_verse_counts.get(surah)
            if max_ayah is None:
                logging.warning("No Quran Foundation verse count for surah %s", surah)
                return None
            first_ayah = start_ayah or 1
            last_ayah = end_ayah or max_ayah
        else:
            first_ayah = start_ayah
            last_ayah = end_ayah

        verses: list[dict[str, object]] = []
        for ayah in range(first_ayah, last_ayah + 1):
            verse = await self._fetch_verse_by_key(
                surah,
                ayah,
                translation_id=translation_id,
            )
            if verse is None:
                return None
            verses.append(verse)
        return verses

    async def _fetch_surah_verses(
        self,
        surah: int,
        version: str,
        *,
        start_ayah: int | None,
        end_ayah: int | None,
    ) -> list[dict[str, object]] | None:
        if self._verses_api_unavailable:
            return None
        translation_id = await self._resolve_translation_id(version)
        params: dict[str, str]
        if translation_id is None:
            params = {"words": "true", "word_fields": "text_uthmani"}
        else:
            params = {"translations": str(translation_id)}

        payload = await self._authorized_get(
            f"/content/api/v4/verses/by_chapter/{surah}",
            params=params,
        )
        if payload is None:
            verses = await self._fetch_surah_verses_via_by_key(
                surah,
                translation_id=translation_id,
                start_ayah=start_ayah,
                end_ayah=end_ayah,
            )
            if verses is None:
                self._verses_api_unavailable = True
                logging.warning(
                    "Quran Foundation verses endpoints appear unavailable in %s; "
                    "falling back to AlQuran Cloud for verse content.",
                    self._env,
                )
            return verses

        verses_payload = payload.get("verses")
        if not isinstance(verses_payload, list):
            logging.warning(
                "Unexpected Quran Foundation verses payload for surah %s/%s: %s",
                surah,
                version,
                payload,
            )
            verses = await self._fetch_surah_verses_via_by_key(
                surah,
                translation_id=translation_id,
                start_ayah=start_ayah,
                end_ayah=end_ayah,
            )
            if verses is None:
                self._verses_api_unavailable = True
                logging.warning(
                    "Quran Foundation verses endpoints appear unavailable in %s; "
                    "falling back to AlQuran Cloud for verse content.",
                    self._env,
                )
            return verses
        return [verse for verse in verses_payload if isinstance(verse, dict)]

    async def get_passage(
        self,
        passage: str,
        version: str = DEFAULT_QURAN_VERSION,
        inline_details: bool = False,
    ) -> str | InlinePassageResult | None:
        reference = parse_quran_reference(passage)
        if reference is None:
            return EMPTY

        surah_sections: list[tuple[int, list[str]]] = []
        translation_hints = get_qf_translation_hints(version)
        text_getter = (
            _extract_translation_text if translation_hints else _extract_arabic_text
        )
        for surah in range(reference.start_surah, reference.end_surah + 1):
            start_ayah = (
                reference.start_ayah if surah == reference.start_surah else None
            )
            end_ayah = reference.end_ayah if surah == reference.end_surah else None
            verses = await self._fetch_surah_verses(
                surah,
                version,
                start_ayah=start_ayah,
                end_ayah=end_ayah,
            )
            if verses is None:
                if self._fallback_client is None:
                    return None
                return await self._fallback_client.get_passage(
                    passage, version, inline_details=inline_details
                )
            formatted_ayahs = extract_formatted_ayahs(
                verses,
                start_ayah=start_ayah,
                end_ayah=end_ayah,
                text_getter=text_getter,
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
