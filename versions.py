import re
from collections import OrderedDict
from typing import Final, TypedDict


class BookData(TypedDict):
    title: str
    slug: str
    aliases: tuple[str, ...]


type VersionLabel = str
type VersionCode = str
type LanguageGroup = str
type BookSlug = str
type BookTitle = str
type ProviderName = str
type VersionDataMap = OrderedDict[LanguageGroup, list[VersionLabel]]


VERSION_DATA = OrderedDict(
    [
        (
            "—English (EN)—",
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
                "Book of Mormon (BOM)",
                "Doctrine and Covenants (DC)",
                "Pearl of Great Price (PGP)",
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
                "The Wisdom of Ben Sira, Cambridge University Press, 1899 "
                "(BENSIRA1899)",
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
            "—中文 (ZH)—",
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
        ("—Amuzgo de Guerrero (AMU)—", ["Amuzgo de Guerrero (AMU)"]),
        (
            "—الْعَرَبِيَّة (AR)—",
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
            "—अवधी (AWA)—",
            ["Awadhi Bible: Easy-to-Read Version (ERV-AWA)"],
        ),
        (
            "—Бъ́лгарски (BG)—",
            [
                "1940 Bulgarian Bible (BG1940)",
                "Bulgarian Bible (BULG)",
                "Bulgarian New Testament: Easy-to-Read Version (ERV-BG)",
                "Bulgarian Protestant Bible (BPB)",
            ],
        ),
        (
            "—Chinanteco de Comaltepec (CCO)—",
            ["Chinanteco de Comaltepec (CCO)"],
        ),
        ("—Cebuano (CEB)—", ["Ang Pulong Sa Dios (APSD-CEB)"]),
        (
            "—ᏣᎳᎩ ᎦᏬᏂᎯᏍ (CHR)—",
            ["Cherokee New Testament (CHR)"],
        ),
        ("—Cakchiquel Occidental (CKW)—", ["Cakchiquel Occidental (CKW)"]),
        (
            "—Čeština (CS)—",
            ["Bible 21 (B21)", "Slovo na cestu (SNC)"],
        ),
        ("—Cymraeg (CY)—", ["Beibl William Morgan (BWM)"]),
        (
            "—Dansk (DA)—",
            [
                "Bibelen på hverdagsdansk (BPH)",
                "Dette er Biblen på dansk (DN1933)",
            ],
        ),
        (
            "—Deutsch (DE)—",
            [
                "Hoffnung für Alle (HOF)",
                "Luther Bibel 1545 (LUTH1545)",
                "Neue Genfer Übersetzung (NGU-DE)",
                "Schlachter 1951 (SCH1951)",
                "Schlachter 2000 (SCH2000)",
            ],
        ),
        (
            "—Español (ES)—",
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
        ("—Suomi (FI)—", ["Raamattu 1933/38 (R1933)"]),
        (
            "—Français (FR)—",
            [
                "La Bible du Semeur (BDS)",
                "Louis Segond (LSG)",
                "Nouvelle Edition de Genève – NEG1979 (NEG1979)",
                "Segond 21 (SG21)",
            ],
        ),
        (
            "—Ἀρχαίᾱ Ἑλληνική (GRC)—",
            [
                "1550 Stephanus New Testament (TR1550)",
                "1881 Westcott-Hort New Testament (WHNU)",
                "1894 Scrivener New Testament (TR1894)",
                "SBL Greek New Testament (SBLGNT)",
            ],
        ),
        (
            "—עִבְרִית (HE)—",
            [
                "Habrit Hakhadasha/Haderekh (HHH)",
                "The Westminster Leningrad Codex (WLC)",
            ],
        ),
        (
            "—हिन्दी (HI)—",
            ["Hindi Bible: Easy-to-Read Version (ERV-HI)"],
        ),
        ("—Ilonggo (HIL)—", ["Ang Pulong Sang Dios (HLGN)"]),
        (
            "—Hrvatski (HR)—",
            [
                "Hrvatski Novi Zavjet – Rijeka 2001 (HNZ-RI)",
                "Knijga O Kristu (CRO)",
            ],
        ),
        ("—Kreyòl ayisyen (HT)—", ["Haitian Creole Version (HCV)"]),
        (
            "—Magyar (HU)—",
            [
                "Hungarian Károli (KAR)",
                "Hungarian Bible: Easy-to-Read Version (ERV-HU)",
                "Hungarian New Translation (NT-HU)",
            ],
        ),
        ("—Hawai‘i Pidgin (HWC)—", ["Hawai‘i Pidgin (HWP)"]),
        ("—Íslenska (IS)—", ["Icelandic Bible (ICELAND)"]),
        (
            "—Italiano (IT)—",
            [
                "La Bibbia della Gioia (BDG)",
                "Conferenza Episcopale Italiana (CEI)",
                "La Nuova Diodati (LND)",
                "Nuova Riveduta 1994 (NR1994)",
                "Nuova Riveduta 2006 (NR2006)",
            ],
        ),
        ("—Jacalteco, Oriental (JAC)—", ["Jacalteco, Oriental (JAC)"]),
        ("—Kekchi (KEK)—", ["Kekchi (KEK)"]),
        ("—Latīna (LA)—", ["Biblia Sacra Vulgata (VULGATE)"]),
        ("—Māori (MI)—", ["Maori Bible (MAORI)"]),
        (
            "—Македонски (MK)—",
            ["Macedonian New Testament (MNT)"],
        ),
        (
            "—मराठी (MR)—",
            ["Marathi Bible: Easy-to-Read Version (ERV-MR)"],
        ),
        ("—Mam, Central (MVC)—", ["Mam, Central (MVC)"]),
        (
            "—Mam, Todos Santos (MVJ)—",
            ["Mam de Todos Santos Chuchumatán (MVJ)"],
        ),
        ("—Plautdietsch (NDS)—", ["Reimer 2001 (REIMER)"]),
        (
            "—नेपाली (NE)—",
            ["Nepali Bible: Easy-to-Read Version (ERV-NE)"],
        ),
        ("—Náhuatl de Guerrero (NGU)—", ["Náhuatl de Guerrero (NGU)"]),
        ("—Nederlands (NL)—", ["Het Boek (HTB)"]),
        (
            "—Norsk (NO)—",
            ["Det Norsk Bibelselskap 1930 (DNB1930)", "En Levende Bok (LB)"],
        ),
        (
            "—ଓଡ଼ିଆ (OR)—",
            ["Oriya Bible: Easy-to-Read Version (ERV-OR)"],
        ),
        (
            "—ਪੰਜਾਬੀ (PA)—",
            ["Punjabi Bible: Easy-to-Read Version (ERV-PA)"],
        ),
        (
            "—Polski (PL)—",
            [
                "Nowe Przymierze (NP)",
                "Słowo Życia (SZ-PL)",
                "Updated Gdańsk Bible (UBG)",
            ],
        ),
        ("—Nāwat (PPL)—", ["Ne Bibliaj Tik Nawat (NBTN)"]),
        (
            "—Português (PT)—",
            [
                "Almeida Revista e Corrigida 2009 (ARC)",
                "Nova Traduҫão na Linguagem de Hoje 2000 (NTLH)",
                "Nova Versão Internacional (NVI-PT)",
                "O Livro (OL)",
                "Portuguese New Testament: Easy-to-Read Version (VFL)",
            ],
        ),
        ("—Quichua (QU)—", ["Mushuj Testamento Diospaj Shimi (MTDS)"]),
        (
            "—Quiché, Centro Occidental (QUT)—",
            ["Quiché, Centro Occidental (QUT)"],
        ),
        (
            "—Română (RO)—",
            [
                "Cornilescu 1924 - Revised 2010, 2014 (RMNN)",
                "Nouă Traducere În Limba Română (NTLR)",
            ],
        ),
        (
            "—Ру́сский (RU)—",
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
        ("—Slovenčina (SK)—", ["Nádej pre kazdého (NPK)"]),
        ("—Somali (SO)—", ["Somali Bible (SOM)"]),
        ("—Shqip (SQ)—", ["Albanian Bible (ALB)"]),
        (
            "—Српски (SR)—",
            ["Serbian New Testament: Easy-to-Read Version (ERV-SR)"],
        ),
        (
            "—Svenska (SV)—",
            [
                "Nya Levande Bibeln (SVL)",
                "Svenska 1917 (SV1917)",
                "Svenska Folkbibeln (SFB)",
                "Svenska Folkbibeln 2014 (SFB2014)",
            ],
        ),
        ("—Kiswahili (SW)—", ["Neno: Bibilia Takatifu (SNT)"]),
        (
            "—தமிழ் (TA)—",
            ["Tamil Bible: Easy-to-Read Version (ERV-TA)"],
        ),
        (
            "—ภาษาไทย (TH)—",
            [
                "Thai New Contemporary Bible (TNCV)",
                "Thai New Testament: Easy-to-Read Version (ERV-TH)",
            ],
        ),
        (
            "—Tagalog (TL)—",
            ["Ang Dating Biblia (1905) (ADB1905)", "Ang Salita ng Diyos (SND)"],
        ),
        ("—Twi (TWI)—", ["Nkwa Asem (NA-TWI)"]),
        (
            "—Украї́нська (UK)—",
            [
                "Ukrainian Bible (UKR)",
                "Ukrainian New Testament: Easy-to-Read Version (ERV-UK)",
            ],
        ),
        (
            "—اُرْدُو (UR)—",
            ["Urdu Bible: Easy-to-Read Version (ERV-UR)"],
        ),
        ("—Uspanteco (USP)—", ["Uspanteco (USP)"]),
        (
            "—Tiếng Việt (VI)—",
            [
                "1934 Vietnamese Bible (VIET)",
                "Bản Dịch 2011 (BD2011)",
                "Vietnamese Bible: Easy-to-Read Version (BPT)",
            ],
        ),
    ]
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
    version_data: VersionDataMap,
) -> dict[VersionLabel, VersionCode]:
    lookup: dict[VersionLabel, VersionCode] = {}
    seen_codes: set[VersionCode] = set()
    for labels in version_data.values():
        for label in labels:
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
    VERSION_DATA
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
SEFARIA_VERSION_TITLES: dict[str, str | dict[str, str]] = {
    "JPS": "The Holy Scriptures: A New Translation (JPS 1917)",
    "NJPS": "Tanakh: The Holy Scriptures, published by JPS",
    "KOREN": "The Koren Jerusalem Bible",
    "CTJPS": "The Contemporary Torah, Jewish Publication Society, 2006",
    "FOX": "The Five Books of Moses, by Everett Fox. New York, Schocken Books, 1995",
    "SCOMM": "Sefaria Community Translation",
    "BRENTON": "Brenton's Septuagint",
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
    "BENSIRA1899": "The Wisdom of Ben Sira, Cambridge University Press, 1899",
    "METSUDAH": "Metsudah Chumash, Metsudah Publications, 2009",
    "RJPS": "THE JPS TANAKH: Gender-Sensitive Edition",
}
VERSION_PROVIDERS.update({code: "sefaria" for code in SEFARIA_VERSION_TITLES})
for code in ("BOM", "DC", "PGP"):
    VERSION_PROVIDERS[code] = "lds"
for code in ("GNA2025", "GNADC25", "TMA", "TMA-C", "TKA"):
    VERSION_PROVIDERS[code] = "biblecom"
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
for code in ("JPS", "NJPS", "KOREN", "RJPS"):
    VERSION_SUPPORTED_BOOK_SLUGS[code] = frozenset(OLD_TESTAMENT_BOOK_SLUGS)
for code in ("CTJPS", "FOX", "METSUDAH"):
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

BOOKS: tuple[str, ...] = (
    PROTESTANT_CANON_BOOK_SLUGS
    + APOCRYPHA_BOOK_SLUGS
    + SEFARIA_EXTRA_BOOK_SLUGS
    + LDS_STANDARD_WORKS_BOOK_SLUGS
)
