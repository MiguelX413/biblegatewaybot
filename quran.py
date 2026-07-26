import re
import unicodedata
from dataclasses import dataclass

from versions import get_version, resolve_version_code

QURAN_SCRIPTURE_NAME = "Qurʾān"
QURAN_REFERENCE_SEPARATOR = "–"

SCRIPTURE_PREFIX_PATTERN = re.compile(
    r"(?i)^\s*(?:qur(?:an|['’ʾ]an)|al(?:[\s-]+)qur(?:an|['’ʾ]an)|koran)\s+"
)
SURA_PREFIX_PATTERN = re.compile(r"(?i)^\s*sur(?:a|ah)\s+")
SINGLE_SURAH_PATTERN = re.compile(r"^(\d{1,3})$")
SINGLE_SURAH_AYAH_PATTERN = re.compile(r"^(\d{1,3}):(\d{1,3})(?:-(\d{1,3}))?$")
WHOLE_SURAH_RANGE_PATTERN = re.compile(r"^(\d{1,3})-(\d{1,3})$")
CROSS_SURAH_AYAH_RANGE_PATTERN = re.compile(
    r"^(\d{1,3}):(\d{1,3})-(\d{1,3}):(\d{1,3})$"
)


@dataclass(frozen=True)
class QuranSurahData:
    number: int
    display_name: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class QuranReference:
    start_surah: int
    start_ayah: int | None
    end_surah: int
    end_ayah: int | None

    @property
    def surah(self) -> int:
        return self.start_surah

    @property
    def is_cross_surah(self) -> bool:
        return self.start_surah != self.end_surah

    @property
    def is_whole_surah_range(self) -> bool:
        return self.start_ayah is None and self.end_ayah is None


def _ascii_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(character for character in normalized if ord(character) < 128)


def _normalize_alias(text: str) -> str:
    normalized = _ascii_text(text.casefold())
    return " ".join(normalized.replace("-", " ").split())


def _surah_aliases(name: str, *extras: str) -> tuple[str, ...]:
    alias_set = {name, _ascii_text(name)}
    ascii_name = _ascii_text(name)
    alias_set.add(ascii_name.replace("'", ""))
    alias_set.add(ascii_name.replace("-", " "))
    alias_set.add(ascii_name.replace("-", " ").replace("'", ""))
    alias_set.update(extras)

    lower_ascii_name = ascii_name.lower()
    for prefix in (
        "al-",
        "al ",
        "an-",
        "an ",
        "ar-",
        "ar ",
        "as-",
        "as ",
        "ash-",
        "ash ",
        "at-",
        "at ",
        "az-",
        "az ",
        "ad-",
        "ad ",
        "adh-",
        "adh ",
    ):
        if lower_ascii_name.startswith(prefix):
            remainder = ascii_name[len(prefix) :].strip()
            if remainder:
                alias_set.add(remainder)
            break

    return tuple(sorted(alias_set))


QURAN_SURAH_DATA: tuple[QuranSurahData, ...] = (
    QuranSurahData(
        1,
        "al-Fātiḥah",
        _surah_aliases("al-Fātiḥah", "al-fatiha", "al-fatihah"),
    ),
    QuranSurahData(2, "al-Baqarah", _surah_aliases("al-Baqarah")),
    QuranSurahData(
        3,
        "Āl ʿImrān",
        _surah_aliases("Āl ʿImrān", "aal imran", "ali imran"),
    ),
    QuranSurahData(4, "an-Nisāʾ", _surah_aliases("an-Nisa", "an-nisaa")),
    QuranSurahData(5, "al-Māʾidah", _surah_aliases("al-Ma'idah", "al-maidah")),
    QuranSurahData(6, "al-Anʿām", _surah_aliases("al-An'am", "al-anaam")),
    QuranSurahData(7, "al-Aʿrāf", _surah_aliases("al-A'raf", "al-araf")),
    QuranSurahData(8, "al-Anfāl", _surah_aliases("al-Anfal")),
    QuranSurahData(9, "at-Tawbah", _surah_aliases("at-Tawbah", "at-taubah")),
    QuranSurahData(10, "Yūnus", _surah_aliases("Yunus")),
    QuranSurahData(11, "Hūd", _surah_aliases("Hud")),
    QuranSurahData(12, "Yūsuf", _surah_aliases("Yusuf")),
    QuranSurahData(13, "ar-Raʿd", _surah_aliases("ar-Ra'd", "ar-rad")),
    QuranSurahData(14, "Ibrāhīm", _surah_aliases("Ibrahim")),
    QuranSurahData(15, "al-Ḥijr", _surah_aliases("al-Hijr")),
    QuranSurahData(16, "an-Naḥl", _surah_aliases("an-Nahl")),
    QuranSurahData(17, "al-Isrāʾ", _surah_aliases("al-Isra", "bani israil")),
    QuranSurahData(18, "al-Kahf", _surah_aliases("al-Kahf")),
    QuranSurahData(19, "Maryam", _surah_aliases("Maryam")),
    QuranSurahData(20, "Ṭā Hā", _surah_aliases("Ta-Ha", "Taha")),
    QuranSurahData(21, "al-Anbiyāʾ", _surah_aliases("al-Anbiya")),
    QuranSurahData(22, "al-Ḥajj", _surah_aliases("al-Hajj")),
    QuranSurahData(23, "al-Muʾminūn", _surah_aliases("al-Mu'minun", "al-muminun")),
    QuranSurahData(24, "an-Nūr", _surah_aliases("an-Nur")),
    QuranSurahData(25, "al-Furqān", _surah_aliases("al-Furqan")),
    QuranSurahData(26, "ash-Shuʿarāʾ", _surah_aliases("ash-Shu'ara", "ash-shuara")),
    QuranSurahData(27, "an-Naml", _surah_aliases("an-Naml")),
    QuranSurahData(28, "al-Qaṣaṣ", _surah_aliases("al-Qasas")),
    QuranSurahData(29, "al-ʿAnkabūt", _surah_aliases("al-Ankabut")),
    QuranSurahData(30, "ar-Rūm", _surah_aliases("ar-Rum")),
    QuranSurahData(31, "Luqmān", _surah_aliases("Luqman")),
    QuranSurahData(32, "as-Sajdah", _surah_aliases("as-Sajdah")),
    QuranSurahData(33, "al-Aḥzāb", _surah_aliases("al-Ahzab")),
    QuranSurahData(34, "Sabaʾ", _surah_aliases("Saba", "Saba'")),
    QuranSurahData(35, "Fāṭir", _surah_aliases("Fatir")),
    QuranSurahData(36, "Yā Sīn", _surah_aliases("Ya-Sin", "Yasin")),
    QuranSurahData(37, "aṣ-Ṣāffāt", _surah_aliases("as-Saffat")),
    QuranSurahData(38, "Ṣād", _surah_aliases("Sad", "Saad")),
    QuranSurahData(39, "az-Zumar", _surah_aliases("az-Zumar")),
    QuranSurahData(40, "Ghāfir", _surah_aliases("Ghafir", "al-mu'min", "al-mumin")),
    QuranSurahData(41, "Fuṣṣilat", _surah_aliases("Fussilat")),
    QuranSurahData(42, "ash-Shūrā", _surah_aliases("ash-Shura", "ash-shuraa")),
    QuranSurahData(43, "az-Zukhruf", _surah_aliases("az-Zukhruf")),
    QuranSurahData(44, "ad-Dukhān", _surah_aliases("ad-Dukhan")),
    QuranSurahData(45, "al-Jāthiyah", _surah_aliases("al-Jathiyah")),
    QuranSurahData(46, "al-Aḥqāf", _surah_aliases("al-Ahqaf")),
    QuranSurahData(47, "Muḥammad", _surah_aliases("Muhammad")),
    QuranSurahData(48, "al-Fatḥ", _surah_aliases("al-Fath")),
    QuranSurahData(49, "al-Ḥujurāt", _surah_aliases("al-Hujurat")),
    QuranSurahData(50, "Qāf", _surah_aliases("Qaf")),
    QuranSurahData(51, "adh-Dhāriyāt", _surah_aliases("adh-Dhariyat", "az-zariyat")),
    QuranSurahData(52, "aṭ-Ṭūr", _surah_aliases("at-Tur")),
    QuranSurahData(53, "an-Najm", _surah_aliases("an-Najm")),
    QuranSurahData(54, "al-Qamar", _surah_aliases("al-Qamar")),
    QuranSurahData(55, "ar-Raḥmān", _surah_aliases("ar-Rahman")),
    QuranSurahData(56, "al-Wāqiʿah", _surah_aliases("al-Waqi'ah", "al-waqiah")),
    QuranSurahData(57, "al-Ḥadīd", _surah_aliases("al-Hadid")),
    QuranSurahData(58, "al-Mujādilah", _surah_aliases("al-Mujadilah")),
    QuranSurahData(59, "al-Ḥashr", _surah_aliases("al-Hashr")),
    QuranSurahData(60, "al-Mumtaḥanah", _surah_aliases("al-Mumtahanah")),
    QuranSurahData(61, "aṣ-Ṣaff", _surah_aliases("as-Saff")),
    QuranSurahData(62, "al-Jumuʿah", _surah_aliases("al-Jumu'ah", "al-jumuah")),
    QuranSurahData(63, "al-Munāfiqūn", _surah_aliases("al-Munafiqun")),
    QuranSurahData(64, "at-Taghābun", _surah_aliases("at-Taghabun")),
    QuranSurahData(65, "aṭ-Ṭalāq", _surah_aliases("at-Talaq")),
    QuranSurahData(66, "at-Taḥrīm", _surah_aliases("at-Tahrim")),
    QuranSurahData(67, "al-Mulk", _surah_aliases("al-Mulk")),
    QuranSurahData(68, "al-Qalam", _surah_aliases("al-Qalam")),
    QuranSurahData(69, "al-Ḥāqqah", _surah_aliases("al-Haqqah", "al-haaqqah")),
    QuranSurahData(70, "al-Maʿārij", _surah_aliases("al-Ma'arij", "al-maarij")),
    QuranSurahData(71, "Nūḥ", _surah_aliases("Nuh")),
    QuranSurahData(72, "al-Jinn", _surah_aliases("al-Jinn")),
    QuranSurahData(73, "al-Muzzammil", _surah_aliases("al-Muzzammil")),
    QuranSurahData(74, "al-Muddaththir", _surah_aliases("al-Muddaththir")),
    QuranSurahData(75, "al-Qiyāmah", _surah_aliases("al-Qiyamah")),
    QuranSurahData(76, "al-Insān", _surah_aliases("al-Insan", "ad-dahr")),
    QuranSurahData(77, "al-Mursalāt", _surah_aliases("al-Mursalat")),
    QuranSurahData(78, "an-Nabaʾ", _surah_aliases("an-Naba", "an-nabaa")),
    QuranSurahData(79, "an-Nāziʿāt", _surah_aliases("an-Nazi'at", "an-naziat")),
    QuranSurahData(80, "ʿAbasa", _surah_aliases("Abasa", "'Abasa")),
    QuranSurahData(81, "at-Takwīr", _surah_aliases("at-Takwir")),
    QuranSurahData(82, "al-Infiṭār", _surah_aliases("al-Infitar")),
    QuranSurahData(83, "al-Muṭaffifīn", _surah_aliases("al-Mutaffifin")),
    QuranSurahData(84, "al-Inshiqāq", _surah_aliases("al-Inshiqaq")),
    QuranSurahData(85, "al-Burūj", _surah_aliases("al-Buruj")),
    QuranSurahData(86, "aṭ-Ṭāriq", _surah_aliases("at-Tariq")),
    QuranSurahData(87, "al-Aʿlā", _surah_aliases("al-A'la", "al-ala")),
    QuranSurahData(88, "al-Ghāshiyah", _surah_aliases("al-Ghashiyah")),
    QuranSurahData(89, "al-Fajr", _surah_aliases("al-Fajr")),
    QuranSurahData(90, "al-Balad", _surah_aliases("al-Balad")),
    QuranSurahData(91, "ash-Shams", _surah_aliases("ash-Shams")),
    QuranSurahData(92, "al-Layl", _surah_aliases("al-Layl")),
    QuranSurahData(93, "aḍ-Ḍuḥā", _surah_aliases("ad-Duha")),
    QuranSurahData(94, "ash-Sharḥ", _surah_aliases("ash-Sharh", "al-inshirah")),
    QuranSurahData(95, "at-Tīn", _surah_aliases("at-Tin")),
    QuranSurahData(96, "al-ʿAlaq", _surah_aliases("al-Alaq")),
    QuranSurahData(97, "al-Qadr", _surah_aliases("al-Qadr")),
    QuranSurahData(98, "al-Bayyinah", _surah_aliases("al-Bayyinah")),
    QuranSurahData(99, "az-Zalzalah", _surah_aliases("az-Zalzalah")),
    QuranSurahData(100, "al-ʿĀdiyāt", _surah_aliases("al-Adiyat")),
    QuranSurahData(101, "al-Qāriʿah", _surah_aliases("al-Qari'ah", "al-qariah")),
    QuranSurahData(102, "at-Takāthur", _surah_aliases("at-Takathur")),
    QuranSurahData(103, "al-ʿAṣr", _surah_aliases("al-Asr", "al-'asr")),
    QuranSurahData(104, "al-Humazah", _surah_aliases("al-Humazah")),
    QuranSurahData(105, "al-Fīl", _surah_aliases("al-Fil")),
    QuranSurahData(106, "Quraysh", _surah_aliases("Quraysh", "Quraish")),
    QuranSurahData(107, "al-Māʿūn", _surah_aliases("al-Ma'un", "al-maun")),
    QuranSurahData(108, "al-Kawthar", _surah_aliases("al-Kawthar")),
    QuranSurahData(109, "al-Kāfirūn", _surah_aliases("al-Kafirun")),
    QuranSurahData(110, "an-Naṣr", _surah_aliases("an-Nasr")),
    QuranSurahData(111, "al-Masad", _surah_aliases("al-Masad", "al-Lahab")),
    QuranSurahData(112, "al-Ikhlāṣ", _surah_aliases("al-Ikhlas")),
    QuranSurahData(113, "al-Falaq", _surah_aliases("al-Falaq")),
    QuranSurahData(114, "an-Nās", _surah_aliases("an-Nas")),
)

QURAN_SURAH_BY_NUMBER: dict[int, QuranSurahData] = {
    surah.number: surah for surah in QURAN_SURAH_DATA
}
QURAN_SURAH_ALIAS_TO_NUMBER: dict[str, int] = {
    _normalize_alias(alias): surah.number
    for surah in QURAN_SURAH_DATA
    for alias in surah.aliases
}


def normalize_quran_input(text: str) -> str:
    return " ".join(str(text).replace("–", "-").split()).strip()


def _valid_surah_number(number: int) -> bool:
    return 1 <= number <= 114


def _valid_ayah_number(number: int) -> bool:
    return number >= 1


def _make_reference(
    start_surah: int,
    start_ayah: int | None,
    end_surah: int,
    end_ayah: int | None,
) -> QuranReference | None:
    if not (_valid_surah_number(start_surah) and _valid_surah_number(end_surah)):
        return None
    if end_surah < start_surah:
        return None
    if (start_ayah is None) != (end_ayah is None):
        return None
    if start_ayah is not None:
        assert end_ayah is not None
        if not _valid_ayah_number(start_ayah) or not _valid_ayah_number(end_ayah):
            return None
    if (
        start_surah == end_surah
        and start_ayah is not None
        and end_ayah is not None
        and end_ayah < start_ayah
    ):
        return None
    if end_surah > start_surah and start_ayah is not None and end_ayah is not None:
        return QuranReference(start_surah, start_ayah, end_surah, end_ayah)
    if end_surah > start_surah:
        return QuranReference(start_surah, None, end_surah, None)
    return QuranReference(start_surah, start_ayah, end_surah, end_ayah)


def _parse_numeric_reference(text: str) -> QuranReference | None:
    if match := SINGLE_SURAH_PATTERN.fullmatch(text):
        surah = int(match.group(1))
        return _make_reference(surah, None, surah, None)
    if match := SINGLE_SURAH_AYAH_PATTERN.fullmatch(text):
        surah = int(match.group(1))
        start_ayah = int(match.group(2))
        end_ayah = int(match.group(3) or start_ayah)
        if match.group(3) and end_ayah == start_ayah:
            return None
        return _make_reference(surah, start_ayah, surah, end_ayah)
    if match := WHOLE_SURAH_RANGE_PATTERN.fullmatch(text):
        start_surah = int(match.group(1))
        end_surah = int(match.group(2))
        return _make_reference(start_surah, None, end_surah, None)
    if match := CROSS_SURAH_AYAH_RANGE_PATTERN.fullmatch(text):
        start_surah = int(match.group(1))
        start_ayah = int(match.group(2))
        end_surah = int(match.group(3))
        end_ayah = int(match.group(4))
        return _make_reference(start_surah, start_ayah, end_surah, end_ayah)
    return None


def _match_named_surah(text: str) -> tuple[int, str] | None:
    normalized = normalize_quran_input(text)
    for alias, number in sorted(
        QURAN_SURAH_ALIAS_TO_NUMBER.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        pattern = rf"(?i)^{re.escape(alias)}(?=$|[\s:])"
        match = re.match(pattern, _normalize_alias(normalized))
        if match is None:
            continue

        consumed = len(normalized)
        for index in range(1, len(normalized) + 1):
            if _normalize_alias(normalized[:index]) == alias:
                consumed = index
                break
        return number, normalized[consumed:].strip()
    return None


def _parse_named_reference(text: str) -> QuranReference | None:
    matched = _match_named_surah(text)
    if matched is None:
        return None

    surah, remainder = matched
    if not remainder:
        return _make_reference(surah, None, surah, None)

    if remainder.startswith(":"):
        remainder = remainder[1:].strip()

    if match := re.fullmatch(r"(\d{1,3}):(\d{1,3})(?:-(\d{1,3}))?", remainder):
        named_surah = int(match.group(1))
        if named_surah != surah:
            return None
        start_ayah = int(match.group(2))
        end_ayah = int(match.group(3) or start_ayah)
        return _make_reference(surah, start_ayah, surah, end_ayah)

    if match := re.fullmatch(r"(\d{1,3})", remainder):
        ayah = int(match.group(1))
        return _make_reference(surah, ayah, surah, ayah)

    if match := re.fullmatch(r"(\d{1,3})-(\d{1,3})", remainder):
        start_ayah = int(match.group(1))
        end_ayah = int(match.group(2))
        return _make_reference(surah, start_ayah, surah, end_ayah)

    return None


def parse_quran_reference(passage: str) -> QuranReference | None:
    normalized = normalize_quran_input(passage)
    if not normalized:
        return None

    scripture_match = SCRIPTURE_PREFIX_PATTERN.match(normalized)
    if scripture_match is not None:
        remainder = normalized[scripture_match.end() :].strip()
        numeric = _parse_numeric_reference(remainder)
        if numeric is not None:
            return numeric
        return _parse_named_reference(remainder)

    sura_match = SURA_PREFIX_PATTERN.match(normalized)
    if sura_match is not None:
        return _parse_named_reference(normalized[sura_match.end() :].strip())

    return _parse_named_reference(normalized)


def quran_surah_display_name(surah: int) -> str:
    return QURAN_SURAH_BY_NUMBER[surah].display_name


def format_quran_machine_reference(reference: QuranReference) -> str:
    if reference.start_surah == reference.end_surah:
        if reference.start_ayah is None:
            return str(reference.start_surah)
        if reference.start_ayah == reference.end_ayah:
            return f"{reference.start_surah}:{reference.start_ayah}"
        return f"{reference.start_surah}:{reference.start_ayah}-{reference.end_ayah}"

    if reference.start_ayah is None:
        return f"{reference.start_surah}-{reference.end_surah}"
    return (
        f"{reference.start_surah}:{reference.start_ayah}"
        f"-{reference.end_surah}:{reference.end_ayah}"
    )


def quran_translation_label(version: str) -> str | None:
    canonical = resolve_version_code(version) or version.upper()
    if canonical == "UTHMANI":
        return None
    labels = {
        "ṢI": "Ṣaḥīḥ International",
        "QPICK": "Pickthall",
        "QYUSUF": "Yusuf Ali",
    }
    if canonical in labels:
        return labels[canonical]
    configured = get_version(canonical)
    if configured is None:
        return canonical
    return configured.name


def format_quran_reference(
    reference: QuranReference, version: str | None = None
) -> str:
    start_label = (
        f"{quran_surah_display_name(reference.start_surah)} ({reference.start_surah})"
    )
    if reference.start_surah == reference.end_surah:
        if reference.start_ayah is None:
            body = start_label
        elif reference.start_ayah == reference.end_ayah:
            body = f"{start_label}:{reference.start_ayah}"
        else:
            body = (
                f"{start_label}:{reference.start_ayah}"
                f"{QURAN_REFERENCE_SEPARATOR}{reference.end_ayah}"
            )
    else:
        end_label = (
            f"{quran_surah_display_name(reference.end_surah)} ({reference.end_surah})"
        )
        if reference.start_ayah is None:
            body = f"{start_label}{QURAN_REFERENCE_SEPARATOR}{end_label}"
        else:
            body = (
                f"{start_label}:{reference.start_ayah}"
                f"{QURAN_REFERENCE_SEPARATOR}"
                f"{end_label}:{reference.end_ayah}"
            )

    citation = f"{QURAN_SCRIPTURE_NAME}, {body}"
    translation = quran_translation_label(version) if version is not None else None
    if translation:
        return f"{citation} ({translation})"
    return citation
