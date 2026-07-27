import html
import re

from parsing import format_numbered_verse_text
from quran import (
    QuranReference,
    format_quran_machine_reference,
    format_quran_reference,
    quran_surah_display_name,
)
from state import EMPTY, InlinePassageResult

HTML_TAG_RE = re.compile(r"<[^>]+>")
FOOTNOTE_SUP_RE = re.compile(r"<sup\b[^>]*>.*?</sup>", re.IGNORECASE | re.DOTALL)


def clean_quran_translation_text(text: str) -> str:
    without_footnotes = FOOTNOTE_SUP_RE.sub("", text)
    without_tags = HTML_TAG_RE.sub("", without_footnotes)
    return " ".join(html.unescape(without_tags).split()).strip()


def extract_formatted_ayahs(
    verses: list[dict[str, object]],
    *,
    start_ayah: int | None = None,
    end_ayah: int | None = None,
    text_getter,
) -> list[str]:
    formatted_ayahs: list[str] = []
    for verse in verses:
        number = verse.get("verse_number")
        if not isinstance(number, int):
            number = verse.get("numberInSurah")
        if not isinstance(number, int):
            continue
        if start_ayah is not None and number < start_ayah:
            continue
        if end_ayah is not None and number > end_ayah:
            continue
        text = text_getter(verse)
        if not text:
            continue
        formatted = format_numbered_verse_text(number, text)
        if formatted:
            formatted_ayahs.append(formatted)
    return formatted_ayahs


def build_quran_passage_text(
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
        blocks: list[str] = []
        for surah_number, ayahs in surah_sections:
            if not ayahs:
                continue
            surah_header = f"{quran_surah_display_name(surah_number)} ({surah_number})"
            blocks.append(f"{surah_header}\n\n" + "\n".join(ayahs))
        body = "\n\n".join(blocks).strip()

    if not body:
        return EMPTY
    return f"{header}\n\n{body}"


def build_inline_result(
    final_text: str,
    *,
    reference: QuranReference,
    version: str,
    header_url: str | None,
) -> InlinePassageResult:
    content = " ".join(final_text.split())
    description = f"{content[:150]}..." if len(content) > 153 else content
    return InlinePassageResult(
        passage=final_text,
        result_id=f"quran/{format_quran_machine_reference(reference)}/{version}",
        title=format_quran_reference(reference, version),
        description=description,
        header_url=header_url,
    )
