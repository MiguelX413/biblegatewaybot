import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import Final, Literal, TypedDict


class BookData(TypedDict):
    title: str
    slug: str
    aliases: tuple[str, ...]


type VersionLabel = str
type VersionCode = str
type LanguageGroup = str
type LanguageCode = str
type BookSlug = str
type BookTitle = str
type ProviderName = str
type ScriptureSystemId = Literal["bible", "lds", "quran"]
type VersionDataMap = OrderedDict[LanguageCode, list[VersionLabel]]
type SefariaVersionConfig = str | dict[BookSlug, str]


def _language_group(label: str, code: LanguageCode) -> LanguageGroup:
    return f"—{label} ({code})—"


LANGUAGE_GROUP_LABELS: Final[dict[LanguageCode, LanguageGroup]] = {
    "AMU": _language_group("Amuzgo de Guerrero", "AMU"),
    "AR": _language_group("الْعَرَبِيَّة", "AR"),
    "AWA": _language_group("अवधी", "AWA"),
    "BG": _language_group("Бъ́лгарски", "BG"),
    "CCO": _language_group("Chinanteco de Comaltepec", "CCO"),
    "CEB": _language_group("Cebuano", "CEB"),
    "CHR": _language_group("ᏣᎳᎩ ᎦᏬᏂᎯᏍ", "CHR"),
    "CKW": _language_group("Cakchiquel Occidental", "CKW"),
    "CS": _language_group("Čeština", "CS"),
    "CY": _language_group("Cymraeg", "CY"),
    "DA": _language_group("Dansk", "DA"),
    "DE": _language_group("Deutsch", "DE"),
    "EN": _language_group("English", "EN"),
    "ES": _language_group("Español", "ES"),
    "FA": _language_group("فارسی", "FA"),
    "FI": _language_group("Suomi", "FI"),
    "FR": _language_group("Français", "FR"),
    "GRC": _language_group("Ἀρχαίᾱ Ἑλληνική", "GRC"),
    "HE": _language_group("עִבְרִית", "HE"),
    "HI": _language_group("हिन्दी", "HI"),
    "HIL": _language_group("Ilonggo", "HIL"),
    "HR": _language_group("Hrvatski", "HR"),
    "HT": _language_group("Kreyòl ayisyen", "HT"),
    "HU": _language_group("Magyar", "HU"),
    "HWC": _language_group("Hawai‘i Pidgin", "HWC"),
    "IS": _language_group("Íslenska", "IS"),
    "IT": _language_group("Italiano", "IT"),
    "JAC": _language_group("Jacalteco, Oriental", "JAC"),
    "KEK": _language_group("Kekchi", "KEK"),
    "LAD": _language_group("Ladino", "LAD"),
    "LA": _language_group("Latīna", "LA"),
    "MI": _language_group("Māori", "MI"),
    "MK": _language_group("Македонски", "MK"),
    "MR": _language_group("मराठी", "MR"),
    "MVC": _language_group("Mam, Central", "MVC"),
    "MVJ": _language_group("Mam, Todos Santos", "MVJ"),
    "NDS": _language_group("Plautdietsch", "NDS"),
    "NE": _language_group("नेपाली", "NE"),
    "NGU": _language_group("Náhuatl de Guerrero", "NGU"),
    "NL": _language_group("Nederlands", "NL"),
    "NO": _language_group("Norsk", "NO"),
    "OR": _language_group("ଓଡ଼ିଆ", "OR"),
    "PA": _language_group("ਪੰਜਾਬੀ", "PA"),
    "PL": _language_group("Polski", "PL"),
    "PPL": _language_group("Nāwat", "PPL"),
    "PT": _language_group("Português", "PT"),
    "QU": _language_group("Quichua", "QU"),
    "QUT": _language_group("Quiché, Centro Occidental", "QUT"),
    "RO": _language_group("Română", "RO"),
    "RU": _language_group("Ру́сский", "RU"),
    "SK": _language_group("Slovenčina", "SK"),
    "SO": _language_group("Somali", "SO"),
    "SQ": _language_group("Shqip", "SQ"),
    "SR": _language_group("Српски", "SR"),
    "SV": _language_group("Svenska", "SV"),
    "SW": _language_group("Kiswahili", "SW"),
    "TA": _language_group("தமிழ்", "TA"),
    "TH": _language_group("ภาษาไทย", "TH"),
    "TL": _language_group("Tagalog", "TL"),
    "TR": _language_group("Türkçe", "TR"),
    "TWI": _language_group("Twi", "TWI"),
    "UK": _language_group("Украї́нська", "UK"),
    "UR": _language_group("اُرْدُو", "UR"),
    "USP": _language_group("Uspanteco", "USP"),
    "UZ": _language_group("Oʻzbek", "UZ"),
    "VI": _language_group("Tiếng Việt", "VI"),
    "YI": _language_group("ייִדיש", "YI"),
    "ZH": _language_group("中文", "ZH"),
}
LANGUAGE_GROUP_CODES: Final[dict[LanguageGroup, LanguageCode]] = {
    label: code for code, label in LANGUAGE_GROUP_LABELS.items()
}


BIBLE_VERSION_DATA: Final[VersionDataMap] = OrderedDict(
    [
        (
            "EN",
            [
                "21st Century King James Version (KJ21)",
                "American Standard Version (ASV)",
                "Amplified Bible (AMP)",
                "Amplified Bible, Classic Edition (AMPC)",
                "BRG Bible (BRG)",
                "Common English Bible (CEB)",
                "Complete Jewish Bible (CJB)",
                "Contemporary English Version (CEV)",
                "Darby Translation (DARBY)",
                "Disciples’ Literal New Testament (DLNT)",
                "Douay-Rheims 1899 American Edition (DRA)",
                "Easy-to-Read Version (ERV)",
                "English Standard Version (ESV)",
                "English Standard Version Anglicised (ESVUK)",
                "Expanded Bible (EXB)",
                "1599 Geneva Bible (GNV)",
                "GOD’S WORD Translation (GW)",
                "Good News Translation (GNT)",
                "Holman Christian Standard Bible (HCSB)",
                "International Children’s Bible (ICB)",
                "International Standard Version (ISV)",
                "J.B. Phillips New Testament (PHILLIPS)",
                "Jubilee Bible 2000 (JUB)",
                "JPS 1917 (JPS)",
                "JPS, 1985 (NJPS)",
                "The Koren Jerusalem Bible (KOREN)",
                "The Contemporary Torah, JPS, 2006 (CTJPS)",
                "The Five Books of Moses, by Everett Fox (FOX)",
                "Sefaria Community Translation (SCOMM)",
                "Brenton's Septuagint (BRENTON)",
                "R. H. Charles Translation (CHARLES)",
                "Rabbi Mike Feuer, Jerusalem Anthology (FEUER)",
                "The Book of Tobit, English translation by A. Neubauer, 1878 "
                "(NEUBAUER)",
                "The Letter of Aristeas, The Clarendon Press, 1913 (ARISTEAS)",
                "the Open Siddur Project (OPENSID)",
                "Translated by Hanan and Esther Eshel (ESHEL)",
                "Metsudah Chumash, Metsudah Publications, 2009 (METSUDAH)",
                "Revised JPS, 2023 (RJPS)",
                "King James Version (KJV)",
                "Authorized (King James) Version (AKJV)",
                "Lexham English Bible (LEB)",
                "Living Bible (TLB)",
                "The Message (MSG)",
                "Modern English Version (MEV)",
                "Mounce Reverse-Interlinear New Testament (MOUNCE)",
                "Names of God Bible (NOG)",
                "New American Bible (Revised Edition) (NABRE)",
                "New American Standard Bible (NASB)",
                "New Century Version (NCV)",
                "New English Translation (NET Bible)",
                "New International Reader's Version (NIrV)",
                "New International Version (NIV)",
                "New International Version - UK (NIVUK)",
                "New King James Version (NKJV)",
                "New Life Version (NLV)",
                "New Living Translation (NLT)",
                "New Revised Standard Version (NRSV)",
                "New Revised Standard Version, Anglicised (NRSVA)",
                "New Revised Standard Version, Anglicised Catholic Edition (NRSVACE)",
                "New Revised Standard Version Catholic Edition (NRSVCE)",
                "New Revised Standard Version Updated Edition (NRSVue)",
                "Orthodox Jewish Bible (OJB)",
                "Revised Standard Version (RSV)",
                "Revised Standard Version Catholic Edition (RSVCE)",
                "The Voice (VOICE)",
                "World English Bible (WEB)",
                "Worldwide English (New Testament) (WE)",
                "Wycliffe Bible (WYC)",
                "Young's Literal Translation (YLT)",
            ],
        ),
        (
            "ZH",
            [
                "Chinese Contemporary Bible (CCB)",
                "Chinese New Testament: Easy-to-Read Version (ERV-ZH)",
                "Chinese New Version (Simplified) (CNVS)",
                "Chinese New Version (Traditional) (CNVT)",
                "Chinese Standard Bible (Simplified) (CSBS)",
                "Chinese Standard Bible (Traditional) (CSBT)",
                "Chinese Union Version (Simplified) (CUVS)",
                "Chinese Union Version (Traditional) (CUV)",
                "Chinese Union Version Modern Punctuation (Simplified) (CUVMPS)",
                "Chinese Union Version Modern Punctuation (Traditional) (CUVMPT)",
            ],
        ),
        ("AMU", ["Amuzgo de Guerrero (AMU)"]),
        (
            "AR",
            [
                "Arabic Bible: Easy-to-Read Version (ERV-AR)",
                "Ketab El Hayat (NAV)",
                "الترجمة العربية المشتركة (GNA2025)",
                "2025 الترجمة العربية المشتركة (GNADC25)",
                "المعنى الصحيح لإنجيل المسيح (TMA)",
                "المعنى الصحيح لإنجيل المسيح - ترتيل (TMA-C)",
                "الترجمة الكاثوليكيّة (اليسوعيّة) (TKA)",
            ],
        ),
        (
            "AWA",
            ["Awadhi Bible: Easy-to-Read Version (ERV-AWA)"],
        ),
        (
            "BG",
            [
                "1940 Bulgarian Bible (BG1940)",
                "Bulgarian Bible (BULG)",
                "Bulgarian New Testament: Easy-to-Read Version (ERV-BG)",
                "Bulgarian Protestant Bible (BPB)",
            ],
        ),
        ("CCO", ["Chinanteco de Comaltepec (CCO)"]),
        ("CEB", ["Ang Pulong Sa Dios (APSD-CEB)"]),
        (
            "CHR",
            ["Cherokee New Testament (CHR)"],
        ),
        ("CKW", ["Cakchiquel Occidental (CKW)"]),
        (
            "CS",
            ["Bible 21 (B21)", "Slovo na cestu (SNC)"],
        ),
        ("CY", ["Beibl William Morgan (BWM)"]),
        (
            "DA",
            [
                "Bibelen på hverdagsdansk (BPH)",
                "Dette er Biblen på dansk (DN1933)",
            ],
        ),
        (
            "DE",
            [
                "Hoffnung für Alle (HOF)",
                "Luther Bibel 1545 (LUTH1545)",
                "Neue Genfer Übersetzung (NGU-DE)",
                "Schlachter 1951 (SCH1951)",
                "Schlachter 2000 (SCH2000)",
            ],
        ),
        (
            "ES",
            [
                "La Biblia de las Américas (LBLA)",
                "Dios Habla Hoy (DHH)",
                "Jubilee Bible 2000 (Spanish) (JBS)",
                "Nueva Biblia al Día (NBD)",
                "Nueva Biblia Latinoamericana de Hoy (NBLH)",
                "Nueva Traducción Viviente (NTV)",
                "Nueva Versión Internacional (NVI)",
                "Nueva Versión Internacional (Castilian) (CST)",
                "Palabra de Dios para Todos (PDT)",
                "La Palabra (España) (BLP)",
                "La Palabra (Hispanoamérica) (BLPH)",
                "Reina Valera Contemporánea (RVC)",
                "Reina-Valera 1960 (RVR1960)",
                "Reina Valera 1977 (RVR1977)",
                "Reina-Valera 1995 (RVR1995)",
                "Reina-Valera Antigua (RVA)",
                "Traducción en lenguaje actual (TLA)",
            ],
        ),
        ("FI", ["Raamattu 1933/38 (R1933)"]),
        (
            "FR",
            [
                "La Bible du Semeur (BDS)",
                "Louis Segond (LSG)",
                "Nouvelle Edition de Genève – NEG1979 (NEG1979)",
                "Segond 21 (SG21)",
            ],
        ),
        (
            "GRC",
            [
                "1550 Stephanus New Testament (TR1550)",
                "1881 Westcott-Hort New Testament (WHNU)",
                "1894 Scrivener New Testament (TR1894)",
                "SBL Greek New Testament (SBLGNT)",
            ],
        ),
        (
            "HE",
            [
                "Habrit Hakhadasha/Haderekh (HHH)",
                "The Westminster Leningrad Codex (WLC)",
            ],
        ),
        ("HI", ["Hindi Bible: Easy-to-Read Version (ERV-HI)"]),
        ("HIL", ["Ang Pulong Sang Dios (HLGN)"]),
        (
            "HR",
            [
                "Hrvatski Novi Zavjet – Rijeka 2001 (HNZ-RI)",
                "Knijga O Kristu (CRO)",
            ],
        ),
        ("HT", ["Haitian Creole Version (HCV)"]),
        (
            "HU",
            [
                "Hungarian Károli (KAR)",
                "Hungarian Bible: Easy-to-Read Version (ERV-HU)",
                "Hungarian New Translation (NT-HU)",
            ],
        ),
        ("HWC", ["Hawai‘i Pidgin (HWP)"]),
        ("IS", ["Icelandic Bible (ICELAND)"]),
        (
            "IT",
            [
                "La Bibbia della Gioia (BDG)",
                "Conferenza Episcopale Italiana (CEI)",
                "La Nuova Diodati (LND)",
                "Nuova Riveduta 1994 (NR1994)",
                "Nuova Riveduta 2006 (NR2006)",
            ],
        ),
        (
            "LAD",
            [
                "Biblia de Ferrara (FERRARA)",
                "Trazladado en la lingua Espanyola, 1873 (BOYADJIAN1873)",
            ],
        ),
        ("JAC", ["Jacalteco, Oriental (JAC)"]),
        ("KEK", ["Kekchi (KEK)"]),
        ("LA", ["Biblia Sacra Vulgata (VULGATE)"]),
        ("MI", ["Maori Bible (MAORI)"]),
        (
            "MK",
            ["Macedonian New Testament (MNT)"],
        ),
        ("MR", ["Marathi Bible: Easy-to-Read Version (ERV-MR)"]),
        ("MVC", ["Mam, Central (MVC)"]),
        (
            "MVJ",
            ["Mam de Todos Santos Chuchumatán (MVJ)"],
        ),
        ("NDS", ["Reimer 2001 (REIMER)"]),
        ("NE", ["Nepali Bible: Easy-to-Read Version (ERV-NE)"]),
        ("NGU", ["Náhuatl de Guerrero (NGU)"]),
        ("NL", ["Het Boek (HTB)"]),
        (
            "NO",
            ["Det Norsk Bibelselskap 1930 (DNB1930)", "En Levende Bok (LB)"],
        ),
        ("OR", ["Oriya Bible: Easy-to-Read Version (ERV-OR)"]),
        ("PA", ["Punjabi Bible: Easy-to-Read Version (ERV-PA)"]),
        (
            "PL",
            [
                "Nowe Przymierze (NP)",
                "Słowo Życia (SZ-PL)",
                "Updated Gdańsk Bible (UBG)",
            ],
        ),
        ("PPL", ["Ne Bibliaj Tik Nawat (NBTN)"]),
        (
            "PT",
            [
                "Almeida Revista e Corrigida 2009 (ARC)",
                "Nova Traduҫão na Linguagem de Hoje 2000 (NTLH)",
                "Nova Versão Internacional (NVI-PT)",
                "O Livro (OL)",
                "Portuguese New Testament: Easy-to-Read Version (VFL)",
            ],
        ),
        ("QU", ["Mushuj Testamento Diospaj Shimi (MTDS)"]),
        (
            "QUT",
            ["Quiché, Centro Occidental (QUT)"],
        ),
        (
            "RO",
            [
                "Cornilescu 1924 - Revised 2010, 2014 (RMNN)",
                "Nouă Traducere În Limba Română (NTLR)",
            ],
        ),
        (
            "RU",
            [
                "New Russian Translation (NRT)",
                "Священное Писание (Восточный Перевод) (CARS)",
                "Священное Писание (Восточный перевод), версия для "
                "Таджикистана (CARST)",
                "Священное Писание (Восточный перевод), версия с «Аллахом» (CARSA)",
                "Russian New Testament: Easy-to-Read Version (ERV-RU)",
                "Russian Synodal Version (RUSV)",
            ],
        ),
        ("SK", ["Nádej pre kazdého (NPK)"]),
        ("SO", ["Somali Bible (SOM)"]),
        ("SQ", ["Albanian Bible (ALB)"]),
        (
            "SR",
            ["Serbian New Testament: Easy-to-Read Version (ERV-SR)"],
        ),
        (
            "SV",
            [
                "Nya Levande Bibeln (SVL)",
                "Svenska 1917 (SV1917)",
                "Svenska Folkbibeln (SFB)",
                "Svenska Folkbibeln 2014 (SFB2014)",
            ],
        ),
        ("SW", ["Neno: Bibilia Takatifu (SNT)"]),
        ("TA", ["Tamil Bible: Easy-to-Read Version (ERV-TA)"]),
        (
            "TH",
            [
                "Thai New Contemporary Bible (TNCV)",
                "Thai New Testament: Easy-to-Read Version (ERV-TH)",
            ],
        ),
        (
            "TL",
            ["Ang Dating Biblia (1905) (ADB1905)", "Ang Salita ng Diyos (SND)"],
        ),
        ("TWI", ["Nkwa Asem (NA-TWI)"]),
        (
            "UK",
            [
                "Ukrainian Bible (UKR)",
                "Ukrainian New Testament: Easy-to-Read Version (ERV-UK)",
            ],
        ),
        ("UR", ["Urdu Bible: Easy-to-Read Version (ERV-UR)"]),
        ("USP", ["Uspanteco (USP)"]),
        (
            "VI",
            [
                "1934 Vietnamese Bible (VIET)",
                "Bản Dịch 2011 (BD2011)",
                "Vietnamese Bible: Easy-to-Read Version (BPT)",
            ],
        ),
        (
            "YI",
            [
                "Tanakh in Yiddish, 1914 (NEUHAUSEN1914)",
                "Yehoyesh's Yiddish Tanakh Translation (YEHOYESH)",
            ],
        ),
    ]
)
LDS_VERSION_LABELS: Final[tuple[VersionLabel, ...]] = (
    "Book of Mormon (BOM)",
    "Doctrine and Covenants (DC)",
    "Pearl of Great Price (PGP)",
)
QURAN_VERSION_DATA: Final[VersionDataMap] = OrderedDict(
    [
        ("AR", ["Uthmani Arabic (QURAN)"]),
        (
            "EN",
            [
                "Saheeh International (QSI)",
                "Marmaduke Pickthall (QPICK)",
                "Abdullah Yusuf Ali (QYUSUF)",
            ],
        ),
        (
            "FA",
            [
                "AbdolMohammad Ayati (QAYATI)",
                "Mohammad Mahdi Fooladvand (QFOOL)",
            ],
        ),
        ("UZ", ["Muhammad Sodik Muhammad Yusuf (QSODIK)"]),
        ("UR", ["Fateh Muhammad Jalandhry (QJAL)"]),
        ("TR", ["Diyanet İşleri (QDIYANET)"]),
        ("RU", ["Elmir Kuliev (QKULIEV)"]),
    ]
)


@dataclass(frozen=True)
class ScriptureSystem:
    """A separately configurable collection of sacred texts."""

    id: ScriptureSystemId
    display_name: str
    version_labels: tuple[VersionLabel, ...]
    version_data: VersionDataMap | None = None


def _version_labels_from_data(version_data: VersionDataMap) -> tuple[VersionLabel, ...]:
    return tuple(
        label for group_labels in version_data.values() for label in group_labels
    )


def format_language_group(code: LanguageCode) -> LanguageGroup:
    return LANGUAGE_GROUP_LABELS[code]


def resolve_language_group(label: str) -> LanguageCode | None:
    return LANGUAGE_GROUP_CODES.get(label)


SCRIPTURE_SYSTEMS: Final[dict[ScriptureSystemId, ScriptureSystem]] = {
    "bible": ScriptureSystem(
        id="bible",
        display_name="Bible",
        version_labels=_version_labels_from_data(BIBLE_VERSION_DATA),
        version_data=BIBLE_VERSION_DATA,
    ),
    "lds": ScriptureSystem(
        id="lds",
        display_name="LDS scriptures",
        version_labels=LDS_VERSION_LABELS,
    ),
    "quran": ScriptureSystem(
        id="quran",
        display_name="Qurʾan",
        version_labels=_version_labels_from_data(QURAN_VERSION_DATA),
        version_data=QURAN_VERSION_DATA,
    ),
}
SCRIPTURE_SYSTEM_ORDER: Final[tuple[ScriptureSystemId, ...]] = (
    "bible",
    "lds",
    "quran",
)


def get_scripture_system(system_id: ScriptureSystemId) -> ScriptureSystem:
    return SCRIPTURE_SYSTEMS[system_id]


ALL_VERSION_LABELS: Final[tuple[VersionLabel, ...]] = tuple(
    label
    for system_id in SCRIPTURE_SYSTEM_ORDER
    for label in SCRIPTURE_SYSTEMS[system_id].version_labels
)
VERSION_CODE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\(([^()]+)\)$")


def _extract_version_code_label(label: VersionLabel) -> VersionCode:
    match = VERSION_CODE_PATTERN.search(label)
    if match is None:
        raise ValueError(f"Version label is missing a trailing code: {label!r}")
    return match.group(1)


def _canonicalize_version_code(code: VersionCode) -> VersionCode:
    return code.upper()


def _build_version_lookup(
    version_labels: tuple[VersionLabel, ...],
) -> dict[VersionLabel, VersionCode]:
    lookup: dict[VersionLabel, VersionCode] = {}
    seen_codes: set[VersionCode] = set()
    for label in version_labels:
        code = _canonicalize_version_code(_extract_version_code_label(label))
        if label in lookup:
            raise ValueError(f"Duplicate version label: {label!r}")
        if code in seen_codes:
            raise ValueError(f"Duplicate version code: {code!r}")
        lookup[label] = code
        seen_codes.add(code)
    return lookup


def _build_version_display_labels(
    version_lookup: dict[VersionLabel, VersionCode],
) -> dict[VersionCode, VersionCode]:
    return {
        code: _extract_version_code_label(label)
        for label, code in version_lookup.items()
    }


def _build_version_full_labels(
    version_lookup: dict[VersionLabel, VersionCode],
) -> dict[VersionCode, VersionLabel]:
    return {code: label for label, code in version_lookup.items()}


VERSION_LOOKUP: Final[dict[VersionLabel, VersionCode]] = _build_version_lookup(
    ALL_VERSION_LABELS
)
VERSIONS: Final[tuple[VersionCode, ...]] = tuple(VERSION_LOOKUP.values())
VERSIONS_SET: Final[frozenset[VersionCode]] = frozenset(VERSIONS)
VERSION_DISPLAY_LABELS: Final[dict[VersionCode, VersionCode]] = (
    _build_version_display_labels(VERSION_LOOKUP)
)
VERSION_FULL_LABELS: Final[dict[VersionCode, VersionLabel]] = (
    _build_version_full_labels(VERSION_LOOKUP)
)
VERSION_CODE_ALIASES: Final[dict[str, VersionCode]] = {
    "GNADC": "GNADC25",
    "GNADC25": "GNADC25",
    "GNADC 25": "GNADC25",
    "GNADC-25": "GNADC25",
    "TMA-C": "TMA-C",
    "TMAC": "TMA-C",
    "TKA": "TKA",
    "TKʿ": "TKA",
    "ت.ك.ع": "TKA",
}
VERSIONS_BY_SYSTEM: Final[dict[ScriptureSystemId, frozenset[VersionCode]]] = {
    system_id: frozenset(
        _canonicalize_version_code(_extract_version_code_label(label))
        for label in system.version_labels
    )
    for system_id, system in SCRIPTURE_SYSTEMS.items()
}
VERSION_SYSTEMS: Final[dict[VersionCode, ScriptureSystemId]] = {
    version: system_id
    for system_id, versions in VERSIONS_BY_SYSTEM.items()
    for version in versions
}


def format_version_label(version: str) -> str:
    return VERSION_DISPLAY_LABELS.get(version.upper(), version)


def format_version_full_label(version: str) -> str:
    return VERSION_FULL_LABELS.get(version.upper(), version)


def format_version_inline_label(version: str) -> str:
    code = format_version_label(version)
    full_label = format_version_full_label(version)
    suffix = f" ({code})"
    if full_label.endswith(suffix):
        return f"{code}: {full_label[: -len(suffix)]}"
    return code


def resolve_version_code(token: str) -> str | None:
    raw = token.strip()
    if not raw:
        return None

    uppercase = raw.upper()
    if uppercase in VERSIONS_SET:
        return uppercase
    if uppercase in VERSION_CODE_ALIASES:
        return VERSION_CODE_ALIASES[uppercase]

    normalized = re.sub(r"[^0-9A-Z]+", "", uppercase)
    if normalized in VERSIONS_SET:
        return normalized
    return VERSION_CODE_ALIASES.get(normalized)


def get_version_system(version: str) -> ScriptureSystemId | None:
    normalized = resolve_version_code(version) or version.upper()
    if normalized == "BENSIRA1899":
        return "bible"
    return VERSION_SYSTEMS.get(normalized)


PROTESTANT_CANON_BOOK_SLUGS = (
    "genesis",
    "exodus",
    "leviticus",
    "numbers",
    "deuteronomy",
    "joshua",
    "judges",
    "ruth",
    "1samuel",
    "2samuel",
    "1kings",
    "2kings",
    "1chronicles",
    "2chronicles",
    "ezra",
    "nehemiah",
    "esther",
    "job",
    "psalm",
    "proverbs",
    "ecclesiastes",
    "songofsolomon",
    "isaiah",
    "jeremiah",
    "lamentations",
    "ezekiel",
    "daniel",
    "hosea",
    "joel",
    "amos",
    "obadiah",
    "jonah",
    "micah",
    "nahum",
    "habakkuk",
    "zephaniah",
    "haggai",
    "zechariah",
    "malachi",
    "matthew",
    "mark",
    "luke",
    "john",
    "acts",
    "romans",
    "1corinthians",
    "2corinthians",
    "galatians",
    "ephesians",
    "philippians",
    "colossians",
    "1thessalonians",
    "2thessalonians",
    "1timothy",
    "2timothy",
    "titus",
    "philemon",
    "hebrews",
    "james",
    "1peter",
    "2peter",
    "1john",
    "2john",
    "3john",
    "jude",
    "revelation",
)
OLD_TESTAMENT_BOOK_SLUGS = PROTESTANT_CANON_BOOK_SLUGS[:39]
TORAH_BOOK_SLUGS = PROTESTANT_CANON_BOOK_SLUGS[:5]
NEW_TESTAMENT_BOOK_SLUGS = PROTESTANT_CANON_BOOK_SLUGS[39:]

APOCRYPHA_BOOK_DATA: tuple[BookData, ...] = (
    {"title": "Tobit", "slug": "tobit", "aliases": ("tobit", "tob")},
    {"title": "Judith", "slug": "judith", "aliases": ("judith", "jdt")},
    {
        "title": "Additions to Esther",
        "slug": "additionstoesther",
        "aliases": ("additions to esther", "greek esther"),
    },
    {
        "title": "Wisdom",
        "slug": "wisdom",
        "aliases": ("wisdom", "wisdom of solomon", "wis"),
    },
    {
        "title": "Sirach",
        "slug": "sirach",
        "aliases": (
            "sirach",
            "ecclesiasticus",
            "sir",
            "ben sira",
            "wisdom of ben sira",
        ),
    },
    {"title": "Baruch", "slug": "baruch", "aliases": ("baruch", "bar")},
    {
        "title": "Letter of Jeremiah",
        "slug": "letterofjeremiah",
        "aliases": ("letter of jeremiah", "epistle of jeremiah"),
    },
    {
        "title": "Prayer of Azariah",
        "slug": "prayerofazariah",
        "aliases": ("prayer of azariah",),
    },
    {"title": "Susanna", "slug": "susanna", "aliases": ("susanna",)},
    {
        "title": "Bel and the Dragon",
        "slug": "belandthedragon",
        "aliases": ("bel and the dragon",),
    },
    {
        "title": "Prayer of Manasseh",
        "slug": "prayerofmanasseh",
        "aliases": ("prayer of manasseh",),
    },
    {"title": "1 Esdras", "slug": "1esdras", "aliases": ("1 esdras", "1esdras")},
    {"title": "2 Esdras", "slug": "2esdras", "aliases": ("2 esdras", "2esdras")},
    {
        "title": "1 Maccabees",
        "slug": "1maccabees",
        "aliases": ("1 maccabees", "1maccabees", "i maccabees"),
    },
    {
        "title": "2 Maccabees",
        "slug": "2maccabees",
        "aliases": ("2 maccabees", "2maccabees", "ii maccabees"),
    },
    {
        "title": "3 Maccabees",
        "slug": "3maccabees",
        "aliases": ("3 maccabees", "3maccabees", "iii maccabees"),
    },
    {
        "title": "4 Maccabees",
        "slug": "4maccabees",
        "aliases": ("4 maccabees", "4maccabees", "iv maccabees"),
    },
    {"title": "Psalm 151", "slug": "psalm151", "aliases": ("psalm 151", "ps151")},
)

BOOK_OF_MORMON_BOOK_DATA: tuple[BookData, ...] = (
    {
        "title": "1 Nephi",
        "slug": "1nephi",
        "aliases": ("1 nephi", "1 ne", "1nephi", "1ne"),
    },
    {
        "title": "2 Nephi",
        "slug": "2nephi",
        "aliases": ("2 nephi", "2 ne", "2nephi", "2ne"),
    },
    {"title": "Jacob", "slug": "jacob", "aliases": ("jacob", "jac")},
    {"title": "Enos", "slug": "enos", "aliases": ("enos",)},
    {"title": "Jarom", "slug": "jarom", "aliases": ("jarom",)},
    {"title": "Omni", "slug": "omni", "aliases": ("omni",)},
    {
        "title": "Words of Mormon",
        "slug": "wordsofmormon",
        "aliases": ("words of mormon", "wordsofmormon", "w of m", "wom"),
    },
    {"title": "Mosiah", "slug": "mosiah", "aliases": ("mosiah", "mos")},
    {"title": "Alma", "slug": "alma", "aliases": ("alma",)},
    {"title": "Helaman", "slug": "helaman", "aliases": ("helaman", "hel")},
    {
        "title": "3 Nephi",
        "slug": "3nephi",
        "aliases": ("3 nephi", "3 ne", "3nephi", "3ne"),
    },
    {
        "title": "4 Nephi",
        "slug": "4nephi",
        "aliases": ("4 nephi", "4 ne", "4nephi", "4ne"),
    },
    {"title": "Mormon", "slug": "mormon", "aliases": ("mormon", "morm")},
    {"title": "Ether", "slug": "ether", "aliases": ("ether", "eth")},
    {"title": "Moroni", "slug": "moroni", "aliases": ("moroni", "moro", "mor")},
)
BOOK_OF_MORMON_BOOK_SLUGS: tuple[str, ...] = tuple(
    book["slug"] for book in BOOK_OF_MORMON_BOOK_DATA
)
SEFARIA_EXTRA_BOOK_DATA: tuple[BookData, ...] = (
    {
        "title": "Jubilees",
        "slug": "jubilees",
        "aliases": ("book of jubilees", "jubilees"),
    },
    {
        "title": "Letter of Aristeas",
        "slug": "letterofaristeas",
        "aliases": ("letter of aristeas", "aristeas"),
    },
    {
        "title": "Megillat Antiochus",
        "slug": "megillatantiochus",
        "aliases": ("megillat antiochus", "megillatantiochus"),
    },
    {"title": "Psalm 154", "slug": "psalm154", "aliases": ("psalm 154", "ps154")},
    {
        "title": "Testaments of the Twelve Patriarchs",
        "slug": "testamentsofthetwelvepatriarchs",
        "aliases": (
            "testaments of the twelve patriarchs",
            "testament of the twelve patriarchs",
        ),
    },
)
SEFARIA_EXTRA_BOOK_SLUGS: tuple[str, ...] = tuple(
    book["slug"] for book in SEFARIA_EXTRA_BOOK_DATA
)
DOCTRINE_AND_COVENANTS_BOOK_DATA: tuple[BookData, ...] = (
    {
        "title": "Doctrine and Covenants",
        "slug": "doctrineandcovenants",
        "aliases": (
            "doctrine and covenants",
            "doctrine & covenants",
            "d and c",
            "d&c",
            "dc",
        ),
    },
)
DOCTRINE_AND_COVENANTS_BOOK_SLUGS: tuple[str, ...] = tuple(
    book["slug"] for book in DOCTRINE_AND_COVENANTS_BOOK_DATA
)
PEARL_OF_GREAT_PRICE_BOOK_DATA: tuple[BookData, ...] = (
    {"title": "Moses", "slug": "moses", "aliases": ("moses",)},
    {"title": "Abraham", "slug": "abraham", "aliases": ("abraham", "abr")},
    {
        "title": "Joseph Smith—Matthew",
        "slug": "josephsmithmatthew",
        "aliases": (
            "joseph smith matthew",
            "joseph smith—matthew",
            "joseph smith-matthew",
            "jsm",
            "js-m",
        ),
    },
    {
        "title": "Joseph Smith—History",
        "slug": "josephsmithhistory",
        "aliases": (
            "joseph smith history",
            "joseph smith—history",
            "joseph smith-history",
            "jsh",
            "js-h",
        ),
    },
    {
        "title": "Articles of Faith",
        "slug": "articlesoffaith",
        "aliases": ("articles of faith", "a of f", "aof", "a-of-f"),
    },
)
PEARL_OF_GREAT_PRICE_BOOK_SLUGS: tuple[str, ...] = tuple(
    book["slug"] for book in PEARL_OF_GREAT_PRICE_BOOK_DATA
)
QURAN_BOOK_DATA: tuple[BookData, ...] = (
    {
        "title": "Qurʾan",
        "slug": "quran",
        "aliases": (
            "quran",
            "qur'an",
            "qur’an",
            "qurʾan",
            "al quran",
            "al-quran",
            "koran",
        ),
    },
)
QURAN_BOOK_SLUGS: tuple[str, ...] = tuple(book["slug"] for book in QURAN_BOOK_DATA)
LDS_STANDARD_WORKS_BOOK_DATA: tuple[BookData, ...] = (
    BOOK_OF_MORMON_BOOK_DATA
    + DOCTRINE_AND_COVENANTS_BOOK_DATA
    + PEARL_OF_GREAT_PRICE_BOOK_DATA
)
LDS_STANDARD_WORKS_BOOK_SLUGS: tuple[str, ...] = tuple(
    book["slug"] for book in LDS_STANDARD_WORKS_BOOK_DATA
)

APOCRYPHA_BOOK_SLUGS: tuple[str, ...] = tuple(
    book["slug"] for book in APOCRYPHA_BOOK_DATA
)
NONCANON_BOOK_SLUGS: frozenset[str] = frozenset(
    APOCRYPHA_BOOK_SLUGS + SEFARIA_EXTRA_BOOK_SLUGS
)
APOCRYPHA_TITLE_TO_SLUG: dict[str, str] = {
    book["title"]: book["slug"] for book in APOCRYPHA_BOOK_DATA
}
CORE_DEUTEROCANON_BOOK_TITLES: frozenset[str] = frozenset(
    {
        "Tobit",
        "Judith",
        "Additions to Esther",
        "Wisdom",
        "Sirach",
        "Baruch",
        "Letter of Jeremiah",
        "Prayer of Azariah",
        "Susanna",
        "Bel and the Dragon",
        "1 Maccabees",
        "2 Maccabees",
    }
)
EXTENDED_APOCRYPHA_BOOK_TITLES: frozenset[str] = frozenset(
    CORE_DEUTEROCANON_BOOK_TITLES
    | {
        "1 Esdras",
        "2 Esdras",
        "Prayer of Manasseh",
        "Psalm 151",
    }
)
ORTHODOX_SUPPLEMENT_APOCRYPHA_BOOK_TITLES: frozenset[str] = frozenset(
    EXTENDED_APOCRYPHA_BOOK_TITLES | {"3 Maccabees", "4 Maccabees"}
)
VERSION_SUPPORTED_APOCRYPHA_BOOKS: dict[str, frozenset[str]] = {
    "CEB": CORE_DEUTEROCANON_BOOK_TITLES,
    "DHH": CORE_DEUTEROCANON_BOOK_TITLES,
    "DRA": CORE_DEUTEROCANON_BOOK_TITLES,
    "GNT": CORE_DEUTEROCANON_BOOK_TITLES,
    "NABRE": CORE_DEUTEROCANON_BOOK_TITLES,
    "NCB": CORE_DEUTEROCANON_BOOK_TITLES,
    "NRSV": EXTENDED_APOCRYPHA_BOOK_TITLES,
    "NRSVA": ORTHODOX_SUPPLEMENT_APOCRYPHA_BOOK_TITLES,
    "NRSVACE": CORE_DEUTEROCANON_BOOK_TITLES,
    "NRSVCE": CORE_DEUTEROCANON_BOOK_TITLES,
    "NRSVUE": ORTHODOX_SUPPLEMENT_APOCRYPHA_BOOK_TITLES,
    "RSV": ORTHODOX_SUPPLEMENT_APOCRYPHA_BOOK_TITLES,
    "RSVCE": CORE_DEUTEROCANON_BOOK_TITLES,
    "TLA": CORE_DEUTEROCANON_BOOK_TITLES,
    "WYC": CORE_DEUTEROCANON_BOOK_TITLES,
}
EXTENDED_APOCRYPHA_BOOK_SLUGS: frozenset[str] = frozenset(
    APOCRYPHA_TITLE_TO_SLUG[title] for title in EXTENDED_APOCRYPHA_BOOK_TITLES
)
ORTHODOX_SUPPLEMENT_APOCRYPHA_BOOK_SLUGS: frozenset[str] = frozenset(
    APOCRYPHA_TITLE_TO_SLUG[title]
    for title in ORTHODOX_SUPPLEMENT_APOCRYPHA_BOOK_TITLES
)
CORE_DEUTEROCANON_BOOK_SLUGS: frozenset[str] = frozenset(
    APOCRYPHA_TITLE_TO_SLUG[title] for title in CORE_DEUTEROCANON_BOOK_TITLES
)
VERSION_ADDITIONAL_BOOK_SLUGS: dict[str, frozenset[str]] = {
    "CEB": CORE_DEUTEROCANON_BOOK_SLUGS,
    "DHH": CORE_DEUTEROCANON_BOOK_SLUGS,
    "DRA": CORE_DEUTEROCANON_BOOK_SLUGS,
    "GNA2025": CORE_DEUTEROCANON_BOOK_SLUGS,
    "GNADC25": CORE_DEUTEROCANON_BOOK_SLUGS,
    "GNT": CORE_DEUTEROCANON_BOOK_SLUGS,
    "NABRE": CORE_DEUTEROCANON_BOOK_SLUGS,
    "NCB": CORE_DEUTEROCANON_BOOK_SLUGS,
    "NRSV": EXTENDED_APOCRYPHA_BOOK_SLUGS,
    "NRSVA": ORTHODOX_SUPPLEMENT_APOCRYPHA_BOOK_SLUGS,
    "NRSVACE": CORE_DEUTEROCANON_BOOK_SLUGS,
    "NRSVCE": CORE_DEUTEROCANON_BOOK_SLUGS,
    "NRSVUE": ORTHODOX_SUPPLEMENT_APOCRYPHA_BOOK_SLUGS,
    "RSV": ORTHODOX_SUPPLEMENT_APOCRYPHA_BOOK_SLUGS,
    "RSVCE": CORE_DEUTEROCANON_BOOK_SLUGS,
    "TKA": CORE_DEUTEROCANON_BOOK_SLUGS,
    "TLA": CORE_DEUTEROCANON_BOOK_SLUGS,
    "WYC": CORE_DEUTEROCANON_BOOK_SLUGS,
}
VERSION_PROVIDERS: dict[str, str] = {code: "biblegateway" for code in VERSIONS}
SEFARIA_VERSION_CONFIGS: dict[str, SefariaVersionConfig] = {
    "JPS": "The Holy Scriptures: A New Translation (JPS 1917)",
    "NJPS": "Tanakh: The Holy Scriptures, published by JPS",
    "KOREN": "The Koren Jerusalem Bible",
    "CTJPS": "The Contemporary Torah, Jewish Publication Society, 2006",
    "FOX": "The Five Books of Moses, by Everett Fox. New York, Schocken Books, 1995",
    "SCOMM": "Sefaria Community Translation",
    "BRENTON": "Brenton's Septuagint",
    "FERRARA": "ladino|Biblia de Ferrara [lad]",
    "BOYADJIAN1873": (
        "ladino|Trazladado en la lingua Espanyola, Estamperia de A. H. "
        "Boyadjian, Konstantinopla 1873. Transkrito por Yehuda Sidi, 2021 [lad]"
    ),
    "NEUHAUSEN1914": (
        "yiddish|Tanakh in Yiddish. Translated by Ch. Neuhausen, "
        "A. Hyman Charlap; NY 1914 [yi]"
    ),
    "YEHOYESH": "yiddish|Yehoyesh's Yiddish Tanakh Translation [yi]",
    "CHARLES": {
        "jubilees": "The Book of Jubilees, trans. R. H. Charles. London [1917]",
        "testamentsofthetwelvepatriarchs": (
            "Testaments of the Twelve Patriarchs, R. H. Charles,1908"
        ),
    },
    "FEUER": "Rabbi Mike Feuer, Jerusalem Anthology",
    "NEUBAUER": "The Book of Tobit, English translation by A. Neubauer, 1878",
    "ARISTEAS": "The Letter of Aristeas, The Clarendon Press, 1913",
    "OPENSID": "the Open Siddur Project",
    "ESHEL": "Translated by Hanan and Esther Eshel",
    # Hidden for now: exact retrieval is currently broken, so keep the config
    # around without advertising it in BIBLE_VERSION_DATA.
    "BENSIRA1899": "The Wisdom of Ben Sira, Cambridge University Press, 1899",
    "METSUDAH": "Metsudah Chumash, Metsudah Publications, 2009",
    "RJPS": "THE JPS TANAKH: Gender-Sensitive Edition",
}
VERSION_PROVIDERS.update({code: "sefaria" for code in SEFARIA_VERSION_CONFIGS})
for code in ("BOM", "DC", "PGP"):
    VERSION_PROVIDERS[code] = "lds"
for code in ("GNA2025", "GNADC25", "TMA", "TMA-C", "TKA"):
    VERSION_PROVIDERS[code] = "biblecom"
for code in (
    "QURAN",
    "QSI",
    "QPICK",
    "QYUSUF",
    "QAYATI",
    "QFOOL",
    "QSODIK",
    "QJAL",
    "QDIYANET",
    "QKULIEV",
):
    VERSION_PROVIDERS[code] = "quran"
VERSION_SUPPORTED_BOOK_SLUGS: dict[str, frozenset[str]] = {
    code: frozenset(PROTESTANT_CANON_BOOK_SLUGS) for code in VERSIONS
}
for code, additional_book_slugs in VERSION_ADDITIONAL_BOOK_SLUGS.items():
    VERSION_SUPPORTED_BOOK_SLUGS[code] = (
        frozenset(PROTESTANT_CANON_BOOK_SLUGS) | additional_book_slugs
    )

# Known scope overrides for current BibleGateway versions that are not full Bible
# editions.
for code in ("DLNT", "MOUNCE", "PHILLIPS", "WE"):
    VERSION_SUPPORTED_BOOK_SLUGS[code] = frozenset(NEW_TESTAMENT_BOOK_SLUGS)
VERSION_SUPPORTED_BOOK_SLUGS["HHH"] = frozenset(NEW_TESTAMENT_BOOK_SLUGS)
VERSION_SUPPORTED_BOOK_SLUGS["WLC"] = frozenset(OLD_TESTAMENT_BOOK_SLUGS)
for code in ("JPS", "NJPS", "KOREN", "RJPS", "YEHOYESH"):
    VERSION_SUPPORTED_BOOK_SLUGS[code] = frozenset(OLD_TESTAMENT_BOOK_SLUGS)
for code in ("CTJPS", "FOX", "METSUDAH", "FERRARA", "BOYADJIAN1873", "NEUHAUSEN1914"):
    VERSION_SUPPORTED_BOOK_SLUGS[code] = frozenset(TORAH_BOOK_SLUGS)
VERSION_SUPPORTED_BOOK_SLUGS["SCOMM"] = frozenset(
    {
        "sirach",
        "wisdom",
        "judith",
        "susanna",
        "prayerofmanasseh",
        "psalm151",
        "1maccabees",
        "2maccabees",
        "jubilees",
    }
)
VERSION_SUPPORTED_BOOK_SLUGS["BRENTON"] = frozenset({"1maccabees"})
VERSION_SUPPORTED_BOOK_SLUGS["CHARLES"] = frozenset(
    {"jubilees", "testamentsofthetwelvepatriarchs"}
)
VERSION_SUPPORTED_BOOK_SLUGS["FEUER"] = frozenset({"1maccabees", "megillatantiochus"})
VERSION_SUPPORTED_BOOK_SLUGS["NEUBAUER"] = frozenset({"tobit"})
VERSION_SUPPORTED_BOOK_SLUGS["ARISTEAS"] = frozenset({"letterofaristeas"})
VERSION_SUPPORTED_BOOK_SLUGS["OPENSID"] = frozenset({"megillatantiochus"})
VERSION_SUPPORTED_BOOK_SLUGS["ESHEL"] = frozenset({"psalm154"})
VERSION_SUPPORTED_BOOK_SLUGS["BENSIRA1899"] = frozenset({"sirach"})
VERSION_SUPPORTED_BOOK_SLUGS["BOM"] = frozenset(BOOK_OF_MORMON_BOOK_SLUGS)
VERSION_SUPPORTED_BOOK_SLUGS["DC"] = frozenset(DOCTRINE_AND_COVENANTS_BOOK_SLUGS)
VERSION_SUPPORTED_BOOK_SLUGS["PGP"] = frozenset(PEARL_OF_GREAT_PRICE_BOOK_SLUGS)
for code in (
    "QURAN",
    "QSI",
    "QPICK",
    "QYUSUF",
    "QAYATI",
    "QFOOL",
    "QSODIK",
    "QJAL",
    "QDIYANET",
    "QKULIEV",
):
    VERSION_SUPPORTED_BOOK_SLUGS[code] = frozenset(QURAN_BOOK_SLUGS)

BOOKS: tuple[str, ...] = (
    PROTESTANT_CANON_BOOK_SLUGS
    + APOCRYPHA_BOOK_SLUGS
    + SEFARIA_EXTRA_BOOK_SLUGS
    + LDS_STANDARD_WORKS_BOOK_SLUGS
    + QURAN_BOOK_SLUGS
)
