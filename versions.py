import re
from collections import OrderedDict
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, TypedDict


class BookData(TypedDict):
    title: str
    slug: str
    aliases: tuple[str, ...]


type VersionLabel = str
type VersionCode = str
type LanguageGroup = str
type BookSlug = str
type VersionDataMap = OrderedDict[LanguageCode, list["Version"]]
type SefariaVersionConfig = str | dict[BookSlug, str]


class ScriptureSystemId(StrEnum):
    BIBLE = "bible"
    LDS = "lds"
    QURAN = "quran"


class LanguageCode(StrEnum):
    AMU = "AMU"
    AR = "AR"
    AWA = "AWA"
    BG = "BG"
    CCO = "CCO"
    CEB = "CEB"
    CHR = "CHR"
    CKW = "CKW"
    CS = "CS"
    CY = "CY"
    DA = "DA"
    DE = "DE"
    EN = "EN"
    ES = "ES"
    FA = "FA"
    FI = "FI"
    FR = "FR"
    GRC = "GRC"
    HE = "HE"
    HI = "HI"
    HIL = "HIL"
    HR = "HR"
    HT = "HT"
    HU = "HU"
    HWC = "HWC"
    IS = "IS"
    IT = "IT"
    JAC = "JAC"
    KEK = "KEK"
    LAD = "LAD"
    LA = "LA"
    MI = "MI"
    MK = "MK"
    MR = "MR"
    MVC = "MVC"
    MVJ = "MVJ"
    NDS = "NDS"
    NE = "NE"
    NGU = "NGU"
    NL = "NL"
    NO = "NO"
    OR = "OR"
    PA = "PA"
    PL = "PL"
    PPL = "PPL"
    PT = "PT"
    QU = "QU"
    QUT = "QUT"
    RO = "RO"
    RU = "RU"
    SK = "SK"
    SO = "SO"
    SQ = "SQ"
    SR = "SR"
    SV = "SV"
    SW = "SW"
    TA = "TA"
    TH = "TH"
    TL = "TL"
    TR = "TR"
    TWI = "TWI"
    UK = "UK"
    UR = "UR"
    USP = "USP"
    UZ = "UZ"
    VI = "VI"
    YI = "YI"
    ZH = "ZH"


class VersionSupportScope(StrEnum):
    BIBLE = "bible"
    NEW_TESTAMENT = "new_testament"
    OLD_TESTAMENT = "old_testament"
    TORAH = "torah"
    BOOK_OF_MORMON = "book_of_mormon"
    DOCTRINE_AND_COVENANTS = "doctrine_and_covenants"
    PEARL_OF_GREAT_PRICE = "pearl_of_great_price"
    QURAN = "quran"
    CUSTOM = "custom"


class VersionProvider(StrEnum):
    BIBLE_GATEWAY = "biblegateway"
    BIBLE_COM = "biblecom"
    SEFARIA = "sefaria"
    LDS = "lds"
    QURAN = "quran"


def _language_group(label: str, code: LanguageCode) -> LanguageGroup:
    return f"—{label} ({code})—"


LANGUAGE_NAMES: Final[dict[LanguageCode, str]] = {
    LanguageCode.AMU: "Amuzgo de Guerrero",
    LanguageCode.AR: "الْعَرَبِيَّة",
    LanguageCode.AWA: "अवधी",
    LanguageCode.BG: "Бъ́лгарски",
    LanguageCode.CCO: "Chinanteco de Comaltepec",
    LanguageCode.CEB: "Cebuano",
    LanguageCode.CHR: "ᏣᎳᎩ ᎦᏬᏂᎯᏍ",
    LanguageCode.CKW: "Cakchiquel Occidental",
    LanguageCode.CS: "Čeština",
    LanguageCode.CY: "Cymraeg",
    LanguageCode.DA: "Dansk",
    LanguageCode.DE: "Deutsch",
    LanguageCode.EN: "English",
    LanguageCode.ES: "Español",
    LanguageCode.FA: "فارسی",
    LanguageCode.FI: "Suomi",
    LanguageCode.FR: "Français",
    LanguageCode.GRC: "Ἀρχαίᾱ Ἑλληνική",
    LanguageCode.HE: "עִבְרִית",
    LanguageCode.HI: "हिन्दी",
    LanguageCode.HIL: "Ilonggo",
    LanguageCode.HR: "Hrvatski",
    LanguageCode.HT: "Kreyòl ayisyen",
    LanguageCode.HU: "Magyar",
    LanguageCode.HWC: "Hawai‘i Pidgin",
    LanguageCode.IS: "Íslenska",
    LanguageCode.IT: "Italiano",
    LanguageCode.JAC: "Jacalteco, Oriental",
    LanguageCode.KEK: "Kekchi",
    LanguageCode.LAD: "Ladino",
    LanguageCode.LA: "Latīna",
    LanguageCode.MI: "Māori",
    LanguageCode.MK: "Македонски",
    LanguageCode.MR: "मराठी",
    LanguageCode.MVC: "Mam, Central",
    LanguageCode.MVJ: "Mam, Todos Santos",
    LanguageCode.NDS: "Plautdietsch",
    LanguageCode.NE: "नेपाली",
    LanguageCode.NGU: "Náhuatl de Guerrero",
    LanguageCode.NL: "Nederlands",
    LanguageCode.NO: "Norsk",
    LanguageCode.OR: "ଓଡ଼ିଆ",
    LanguageCode.PA: "ਪੰਜਾਬੀ",
    LanguageCode.PL: "Polski",
    LanguageCode.PPL: "Nāwat",
    LanguageCode.PT: "Português",
    LanguageCode.QU: "Quichua",
    LanguageCode.QUT: "Quiché, Centro Occidental",
    LanguageCode.RO: "Română",
    LanguageCode.RU: "Ру́сский",
    LanguageCode.SK: "Slovenčina",
    LanguageCode.SO: "Somali",
    LanguageCode.SQ: "Shqip",
    LanguageCode.SR: "Српски",
    LanguageCode.SV: "Svenska",
    LanguageCode.SW: "Kiswahili",
    LanguageCode.TA: "தமிழ்",
    LanguageCode.TH: "ภาษาไทย",
    LanguageCode.TL: "Tagalog",
    LanguageCode.TR: "Türkçe",
    LanguageCode.TWI: "Twi",
    LanguageCode.UK: "Украї́нська",
    LanguageCode.UR: "اُرْدُو",
    LanguageCode.USP: "Uspanteco",
    LanguageCode.UZ: "Oʻzbek",
    LanguageCode.VI: "Tiếng Việt",
    LanguageCode.YI: "ייִדיש",
    LanguageCode.ZH: "中文",
}
LANGUAGE_GROUP_LABELS: Final[dict[LanguageCode, LanguageGroup]] = {
    code: _language_group(label, code) for code, label in LANGUAGE_NAMES.items()
}
LANGUAGE_GROUP_CODES: Final[dict[LanguageGroup, LanguageCode]] = {
    label: code for code, label in LANGUAGE_GROUP_LABELS.items()
}


@dataclass(frozen=True)
class Version:
    name: str
    abbreviation: str
    provider: VersionProvider
    aliases: tuple[str, ...] = ()
    sefaria_config: SefariaVersionConfig | None = None
    support_scope: VersionSupportScope = VersionSupportScope.BIBLE
    supported_book_slugs: frozenset[BookSlug] = frozenset()
    additional_supported_book_slugs: frozenset[BookSlug] = frozenset()

    @classmethod
    def gateway(
        cls,
        name: str,
        abbreviation: str,
        *,
        aliases: tuple[str, ...] = (),
        additional_supported_book_slugs: frozenset[BookSlug] = frozenset(),
    ) -> Version:
        return cls(
            name,
            abbreviation,
            VersionProvider.BIBLE_GATEWAY,
            aliases,
            None,
            VersionSupportScope.BIBLE,
            frozenset(),
            additional_supported_book_slugs,
        )

    @classmethod
    def gateway_nt(
        cls, name: str, abbreviation: str, *, aliases: tuple[str, ...] = ()
    ) -> Version:
        return cls(
            name,
            abbreviation,
            VersionProvider.BIBLE_GATEWAY,
            aliases,
            None,
            VersionSupportScope.NEW_TESTAMENT,
        )

    @classmethod
    def gateway_ot(
        cls, name: str, abbreviation: str, *, aliases: tuple[str, ...] = ()
    ) -> Version:
        return cls(
            name,
            abbreviation,
            VersionProvider.BIBLE_GATEWAY,
            aliases,
            None,
            VersionSupportScope.OLD_TESTAMENT,
        )

    @classmethod
    def gateway_torah(
        cls, name: str, abbreviation: str, *, aliases: tuple[str, ...] = ()
    ) -> Version:
        return cls(
            name,
            abbreviation,
            VersionProvider.BIBLE_GATEWAY,
            aliases,
            None,
            VersionSupportScope.TORAH,
        )

    @classmethod
    def quran(
        cls, name: str, abbreviation: str, *, aliases: tuple[str, ...] = ()
    ) -> Version:
        return cls(
            name,
            abbreviation,
            VersionProvider.QURAN,
            aliases,
            None,
            VersionSupportScope.QURAN,
        )

    @classmethod
    def book_of_mormon(
        cls, name: str, abbreviation: str, *, aliases: tuple[str, ...] = ()
    ) -> Version:
        return cls(
            name,
            abbreviation,
            VersionProvider.LDS,
            aliases,
            None,
            VersionSupportScope.BOOK_OF_MORMON,
        )

    @classmethod
    def doctrine_and_covenants(
        cls, name: str, abbreviation: str, *, aliases: tuple[str, ...] = ()
    ) -> Version:
        return cls(
            name,
            abbreviation,
            VersionProvider.LDS,
            aliases,
            None,
            VersionSupportScope.DOCTRINE_AND_COVENANTS,
        )

    @classmethod
    def pearl_of_great_price(
        cls, name: str, abbreviation: str, *, aliases: tuple[str, ...] = ()
    ) -> Version:
        return cls(
            name,
            abbreviation,
            VersionProvider.LDS,
            aliases,
            None,
            VersionSupportScope.PEARL_OF_GREAT_PRICE,
        )

    @classmethod
    def bible_com(
        cls,
        name: str,
        abbreviation: str,
        *,
        aliases: tuple[str, ...] = (),
        additional_supported_book_slugs: frozenset[BookSlug] = frozenset(),
    ) -> Version:
        return cls(
            name,
            abbreviation,
            VersionProvider.BIBLE_COM,
            aliases,
            None,
            VersionSupportScope.BIBLE,
            frozenset(),
            additional_supported_book_slugs,
        )

    @classmethod
    def sefaria(
        cls,
        name: str,
        abbreviation: str,
        supported_book_slugs: frozenset[BookSlug],
        *,
        aliases: tuple[str, ...] = (),
        sefaria_config: SefariaVersionConfig | None = None,
    ) -> Version:
        return cls(
            name,
            abbreviation,
            VersionProvider.SEFARIA,
            aliases,
            sefaria_config,
            VersionSupportScope.CUSTOM,
            supported_book_slugs,
        )

    @classmethod
    def custom(
        cls,
        name: str,
        abbreviation: str,
        supported_book_slugs: frozenset[BookSlug],
        *,
        aliases: tuple[str, ...] = (),
    ) -> Version:
        return cls(
            name,
            abbreviation,
            VersionProvider.BIBLE_GATEWAY,
            aliases,
            None,
            VersionSupportScope.CUSTOM,
            supported_book_slugs,
        )

    @property
    def code(self) -> str:
        return self.abbreviation

    @property
    def full_label(self) -> str:
        return f"{self.name} ({self.abbreviation})"


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
SUPPORT_BOOK_SLUGS_BY_SCOPE: Final[dict[VersionSupportScope, frozenset[BookSlug]]] = {
    VersionSupportScope.BIBLE: frozenset(PROTESTANT_CANON_BOOK_SLUGS),
    VersionSupportScope.NEW_TESTAMENT: frozenset(NEW_TESTAMENT_BOOK_SLUGS),
    VersionSupportScope.OLD_TESTAMENT: frozenset(OLD_TESTAMENT_BOOK_SLUGS),
    VersionSupportScope.TORAH: frozenset(TORAH_BOOK_SLUGS),
    VersionSupportScope.BOOK_OF_MORMON: frozenset(BOOK_OF_MORMON_BOOK_SLUGS),
    VersionSupportScope.DOCTRINE_AND_COVENANTS: frozenset(
        DOCTRINE_AND_COVENANTS_BOOK_SLUGS
    ),
    VersionSupportScope.PEARL_OF_GREAT_PRICE: frozenset(
        PEARL_OF_GREAT_PRICE_BOOK_SLUGS
    ),
    VersionSupportScope.QURAN: frozenset(QURAN_BOOK_SLUGS),
    VersionSupportScope.CUSTOM: frozenset(),
}

BIBLE_VERSION_DATA: Final[VersionDataMap] = OrderedDict(
    [
        (
            LanguageCode.EN,
            [
                Version.gateway("21st Century King James Version", "KJ21"),
                Version.gateway("American Standard Version", "ASV"),
                Version.gateway("Amplified Bible", "AMP"),
                Version.gateway("Amplified Bible, Classic Edition", "AMPC"),
                Version.gateway("BRG Bible", "BRG"),
                Version.gateway(
                    "Common English Bible",
                    "CEB",
                    additional_supported_book_slugs=CORE_DEUTEROCANON_BOOK_SLUGS,
                ),
                Version.gateway("Complete Jewish Bible", "CJB"),
                Version.gateway("Contemporary English Version", "CEV"),
                Version.gateway("Darby Translation", "DARBY"),
                Version.gateway_nt("Disciples’ Literal New Testament", "DLNT"),
                Version.gateway(
                    "Douay-Rheims 1899 American Edition",
                    "DRA",
                    additional_supported_book_slugs=CORE_DEUTEROCANON_BOOK_SLUGS,
                ),
                Version.gateway("Easy-to-Read Version", "ERV"),
                Version.gateway("English Standard Version", "ESV"),
                Version.gateway("English Standard Version Anglicised", "ESVUK"),
                Version.gateway("Expanded Bible", "EXB"),
                Version.gateway("1599 Geneva Bible", "GNV"),
                Version.gateway("GOD’S WORD Translation", "GW"),
                Version.gateway(
                    "Good News Translation",
                    "GNT",
                    additional_supported_book_slugs=CORE_DEUTEROCANON_BOOK_SLUGS,
                ),
                Version.gateway("Holman Christian Standard Bible", "HCSB"),
                Version.gateway("International Children’s Bible", "ICB"),
                Version.gateway("International Standard Version", "ISV"),
                Version.gateway_nt("J.B. Phillips New Testament", "PHILLIPS"),
                Version.gateway("Jubilee Bible 2000", "JUB"),
                Version.sefaria(
                    "JPS 1917",
                    "JPS",
                    frozenset(OLD_TESTAMENT_BOOK_SLUGS),
                    sefaria_config="The Holy Scriptures: A New Translation (JPS 1917)",
                ),
                Version.sefaria(
                    "JPS, 1985",
                    "NJPS",
                    frozenset(OLD_TESTAMENT_BOOK_SLUGS),
                    sefaria_config="Tanakh: The Holy Scriptures, published by JPS",
                ),
                Version.sefaria(
                    "The Koren Jerusalem Bible",
                    "KOREN",
                    frozenset(OLD_TESTAMENT_BOOK_SLUGS),
                    sefaria_config="The Koren Jerusalem Bible",
                ),
                Version.sefaria(
                    "The Contemporary Torah, JPS, 2006",
                    "CTJPS",
                    frozenset(TORAH_BOOK_SLUGS),
                    sefaria_config=(
                        "The Contemporary Torah, Jewish Publication Society, 2006"
                    ),
                ),
                Version.sefaria(
                    "The Five Books of Moses, by Everett Fox",
                    "FOX",
                    frozenset(TORAH_BOOK_SLUGS),
                    sefaria_config=(
                        "The Five Books of Moses, by Everett Fox. New York, "
                        "Schocken Books, 1995"
                    ),
                ),
                Version.sefaria(
                    "Sefaria Community Translation",
                    "SCOMM",
                    frozenset(
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
                    ),
                    sefaria_config="Sefaria Community Translation",
                ),
                Version.sefaria(
                    "Brenton's Septuagint",
                    "BRENTON",
                    frozenset({"1maccabees"}),
                    sefaria_config="Brenton's Septuagint",
                ),
                Version.sefaria(
                    "R. H. Charles Translation",
                    "CHARLES",
                    frozenset({"jubilees", "testamentsofthetwelvepatriarchs"}),
                    sefaria_config={
                        "jubilees": (
                            "The Book of Jubilees, trans. R. H. Charles. London [1917]"
                        ),
                        "testamentsofthetwelvepatriarchs": (
                            "Testaments of the Twelve Patriarchs, R. H. Charles,1908"
                        ),
                    },
                ),
                Version.sefaria(
                    "Rabbi Mike Feuer, Jerusalem Anthology",
                    "FEUER",
                    frozenset({"1maccabees", "megillatantiochus"}),
                    sefaria_config="Rabbi Mike Feuer, Jerusalem Anthology",
                ),
                Version.sefaria(
                    "The Book of Tobit, English translation by A. Neubauer, 1878",
                    "NEUBAUER",
                    frozenset({"tobit"}),
                    sefaria_config=(
                        "The Book of Tobit, English translation by A. Neubauer, 1878"
                    ),
                ),
                Version.sefaria(
                    "The Letter of Aristeas, The Clarendon Press, 1913",
                    "ARISTEAS",
                    frozenset({"letterofaristeas"}),
                    sefaria_config="The Letter of Aristeas, The Clarendon Press, 1913",
                ),
                Version.sefaria(
                    "the Open Siddur Project",
                    "OPENSID",
                    frozenset({"megillatantiochus"}),
                    sefaria_config="the Open Siddur Project",
                ),
                Version.sefaria(
                    "Translated by Hanan and Esther Eshel",
                    "ESHEL",
                    frozenset({"psalm154"}),
                    sefaria_config="Translated by Hanan and Esther Eshel",
                ),
                Version.sefaria(
                    "Metsudah Chumash, Metsudah Publications, 2009",
                    "METSUDAH",
                    frozenset(TORAH_BOOK_SLUGS),
                    sefaria_config="Metsudah Chumash, Metsudah Publications, 2009",
                ),
                Version.sefaria(
                    "Revised JPS, 2023",
                    "RJPS",
                    frozenset(OLD_TESTAMENT_BOOK_SLUGS),
                    sefaria_config="THE JPS TANAKH: Gender-Sensitive Edition",
                ),
                Version.gateway("King James Version", "KJV"),
                Version.gateway("Authorized (King James) Version", "AKJV"),
                Version.gateway("Lexham English Bible", "LEB"),
                Version.gateway("Living Bible", "TLB"),
                Version.gateway("The Message", "MSG"),
                Version.gateway("Modern English Version", "MEV"),
                Version.gateway_nt(
                    "Mounce Reverse-Interlinear New Testament", "MOUNCE"
                ),
                Version.gateway("Names of God Bible", "NOG"),
                Version.gateway(
                    "New American Bible (Revised Edition)",
                    "NABRE",
                    additional_supported_book_slugs=CORE_DEUTEROCANON_BOOK_SLUGS,
                ),
                Version.gateway("New American Standard Bible", "NASB"),
                Version.gateway("New Century Version", "NCV"),
                Version.gateway("New English Translation", "NET Bible"),
                Version.gateway("New International Reader's Version", "NIrV"),
                Version.gateway("New International Version", "NIV"),
                Version.gateway("New International Version - UK", "NIVUK"),
                Version.gateway("New King James Version", "NKJV"),
                Version.gateway("New Life Version", "NLV"),
                Version.gateway("New Living Translation", "NLT"),
                Version.gateway(
                    "New Revised Standard Version",
                    "NRSV",
                    additional_supported_book_slugs=EXTENDED_APOCRYPHA_BOOK_SLUGS,
                ),
                Version.gateway(
                    "New Revised Standard Version, Anglicised",
                    "NRSVA",
                    additional_supported_book_slugs=ORTHODOX_SUPPLEMENT_APOCRYPHA_BOOK_SLUGS,
                ),
                Version.gateway(
                    "New Revised Standard Version, Anglicised Catholic Edition",
                    "NRSVACE",
                    additional_supported_book_slugs=CORE_DEUTEROCANON_BOOK_SLUGS,
                ),
                Version.gateway(
                    "New Revised Standard Version Catholic Edition",
                    "NRSVCE",
                    additional_supported_book_slugs=CORE_DEUTEROCANON_BOOK_SLUGS,
                ),
                Version.gateway(
                    "New Revised Standard Version Updated Edition",
                    "NRSVue",
                    additional_supported_book_slugs=ORTHODOX_SUPPLEMENT_APOCRYPHA_BOOK_SLUGS,
                ),
                Version.gateway("Orthodox Jewish Bible", "OJB"),
                Version.gateway(
                    "Revised Standard Version",
                    "RSV",
                    additional_supported_book_slugs=ORTHODOX_SUPPLEMENT_APOCRYPHA_BOOK_SLUGS,
                ),
                Version.gateway(
                    "Revised Standard Version Catholic Edition",
                    "RSVCE",
                    additional_supported_book_slugs=CORE_DEUTEROCANON_BOOK_SLUGS,
                ),
                Version.gateway("The Voice", "VOICE"),
                Version.gateway("World English Bible", "WEB"),
                Version.gateway_nt("Worldwide English (New Testament)", "WE"),
                Version.gateway(
                    "Wycliffe Bible",
                    "WYC",
                    additional_supported_book_slugs=CORE_DEUTEROCANON_BOOK_SLUGS,
                ),
                Version.gateway("Young's Literal Translation", "YLT"),
            ],
        ),
        (
            LanguageCode.ZH,
            [
                Version.gateway("Chinese Contemporary Bible", "CCB"),
                Version.gateway(
                    "Chinese New Testament: Easy-to-Read Version", "ERV-ZH"
                ),
                Version.gateway("Chinese New Version (Simplified)", "CNVS"),
                Version.gateway("Chinese New Version (Traditional)", "CNVT"),
                Version.gateway("Chinese Standard Bible (Simplified)", "CSBS"),
                Version.gateway("Chinese Standard Bible (Traditional)", "CSBT"),
                Version.gateway("Chinese Union Version (Simplified)", "CUVS"),
                Version.gateway("Chinese Union Version (Traditional)", "CUV"),
                Version.gateway(
                    "Chinese Union Version Modern Punctuation (Simplified)", "CUVMPS"
                ),
                Version.gateway(
                    "Chinese Union Version Modern Punctuation (Traditional)", "CUVMPT"
                ),
            ],
        ),
        (
            LanguageCode.AMU,
            [Version.gateway("Amuzgo de Guerrero", "AMU")],
        ),
        (
            LanguageCode.AR,
            [
                Version.gateway("Arabic Bible: Easy-to-Read Version", "ERV-AR"),
                Version.gateway("Ketab El Hayat", "NAV"),
                Version.bible_com(
                    "الترجمة العربية المشتركة",
                    "GNA2025",
                    additional_supported_book_slugs=CORE_DEUTEROCANON_BOOK_SLUGS,
                ),
                Version.bible_com(
                    "2025 الترجمة العربية المشتركة",
                    "GNADC25",
                    aliases=("GNADC", "GNADC 25", "GNADC-25"),
                    additional_supported_book_slugs=CORE_DEUTEROCANON_BOOK_SLUGS,
                ),
                Version.bible_com("المعنى الصحيح لإنجيل المسيح", "TMA"),
                Version.bible_com(
                    "المعنى الصحيح لإنجيل المسيح - ترتيل",
                    "TMA-C",
                    aliases=("TMAC",),
                ),
                Version.bible_com(
                    "الترجمة الكاثوليكيّة (اليسوعيّة)",
                    "TKA",
                    aliases=("TKʿ", "ت.ك.ع"),
                    additional_supported_book_slugs=CORE_DEUTEROCANON_BOOK_SLUGS,
                ),
            ],
        ),
        (
            LanguageCode.AWA,
            [Version.gateway("Awadhi Bible: Easy-to-Read Version", "ERV-AWA")],
        ),
        (
            LanguageCode.BG,
            [
                Version.gateway("1940 Bulgarian Bible", "BG1940"),
                Version.gateway("Bulgarian Bible", "BULG"),
                Version.gateway(
                    "Bulgarian New Testament: Easy-to-Read Version", "ERV-BG"
                ),
                Version.gateway("Bulgarian Protestant Bible", "BPB"),
            ],
        ),
        (
            LanguageCode.CCO,
            [Version.gateway("Chinanteco de Comaltepec", "CCO")],
        ),
        (
            LanguageCode.CEB,
            [Version.gateway("Ang Pulong Sa Dios", "APSD-CEB")],
        ),
        (
            LanguageCode.CHR,
            [Version.gateway("Cherokee New Testament", "CHR")],
        ),
        (
            LanguageCode.CKW,
            [Version.gateway("Cakchiquel Occidental", "CKW")],
        ),
        (
            LanguageCode.CS,
            [
                Version.gateway("Bible 21", "B21"),
                Version.gateway("Slovo na cestu", "SNC"),
            ],
        ),
        (
            LanguageCode.CY,
            [Version.gateway("Beibl William Morgan", "BWM")],
        ),
        (
            LanguageCode.DA,
            [
                Version.gateway("Bibelen på hverdagsdansk", "BPH"),
                Version.gateway("Dette er Biblen på dansk", "DN1933"),
            ],
        ),
        (
            LanguageCode.DE,
            [
                Version.gateway("Hoffnung für Alle", "HOF"),
                Version.gateway("Luther Bibel 1545", "LUTH1545"),
                Version.gateway("Neue Genfer Übersetzung", "NGU-DE"),
                Version.gateway("Schlachter 1951", "SCH1951"),
                Version.gateway("Schlachter 2000", "SCH2000"),
            ],
        ),
        (
            LanguageCode.ES,
            [
                Version.gateway("La Biblia de las Américas", "LBLA"),
                Version.gateway("Dios Habla Hoy", "DHH"),
                Version.gateway("Jubilee Bible 2000 (Spanish)", "JBS"),
                Version.gateway("Nueva Biblia al Día", "NBD"),
                Version.gateway("Nueva Biblia Latinoamericana de Hoy", "NBLH"),
                Version.gateway("Nueva Traducción Viviente", "NTV"),
                Version.gateway("Nueva Versión Internacional", "NVI"),
                Version.gateway("Nueva Versión Internacional (Castilian)", "CST"),
                Version.gateway("Palabra de Dios para Todos", "PDT"),
                Version.gateway("La Palabra (España)", "BLP"),
                Version.gateway("La Palabra (Hispanoamérica)", "BLPH"),
                Version.gateway("Reina Valera Contemporánea", "RVC"),
                Version.gateway("Reina-Valera 1960", "RVR1960"),
                Version.gateway("Reina Valera 1977", "RVR1977"),
                Version.gateway("Reina-Valera 1995", "RVR1995"),
                Version.gateway("Reina-Valera Antigua", "RVA"),
                Version.gateway("Traducción en lenguaje actual", "TLA"),
            ],
        ),
        (
            LanguageCode.FI,
            [Version.gateway("Raamattu 1933/38", "R1933")],
        ),
        (
            LanguageCode.FR,
            [
                Version.gateway("La Bible du Semeur", "BDS"),
                Version.gateway("Louis Segond", "LSG"),
                Version.gateway("Nouvelle Edition de Genève – NEG1979", "NEG1979"),
                Version.gateway("Segond 21", "SG21"),
            ],
        ),
        (
            LanguageCode.GRC,
            [
                Version.gateway("1550 Stephanus New Testament", "TR1550"),
                Version.gateway("1881 Westcott-Hort New Testament", "WHNU"),
                Version.gateway("1894 Scrivener New Testament", "TR1894"),
                Version.gateway("SBL Greek New Testament", "SBLGNT"),
            ],
        ),
        (
            LanguageCode.HE,
            [
                Version.bible_com("Habrit Hakhadasha/Haderekh", "HHH"),
                Version.gateway_ot("The Westminster Leningrad Codex", "WLC"),
            ],
        ),
        (
            LanguageCode.HI,
            [Version.gateway("Hindi Bible: Easy-to-Read Version", "ERV-HI")],
        ),
        (
            LanguageCode.HIL,
            [Version.gateway("Ang Pulong Sang Dios", "HLGN")],
        ),
        (
            LanguageCode.HR,
            [
                Version.gateway("Hrvatski Novi Zavjet – Rijeka 2001", "HNZ-RI"),
                Version.gateway("Knijga O Kristu", "CRO"),
            ],
        ),
        (
            LanguageCode.HT,
            [Version.gateway("Haitian Creole Version", "HCV")],
        ),
        (
            LanguageCode.HU,
            [
                Version.gateway("Hungarian Károli", "KAR"),
                Version.gateway("Hungarian Bible: Easy-to-Read Version", "ERV-HU"),
                Version.gateway("Hungarian New Translation", "NT-HU"),
            ],
        ),
        (
            LanguageCode.HWC,
            [Version.gateway("Hawai‘i Pidgin", "HWP")],
        ),
        (
            LanguageCode.IS,
            [Version.gateway("Icelandic Bible", "ICELAND")],
        ),
        (
            LanguageCode.IT,
            [
                Version.gateway("La Bibbia della Gioia", "BDG"),
                Version.gateway("Conferenza Episcopale Italiana", "CEI"),
                Version.gateway("La Nuova Diodati", "LND"),
                Version.gateway("Nuova Riveduta 1994", "NR1994"),
                Version.gateway("Nuova Riveduta 2006", "NR2006"),
            ],
        ),
        (
            LanguageCode.LAD,
            [
                Version.sefaria(
                    "Biblia de Ferrara",
                    "FERRARA",
                    frozenset(TORAH_BOOK_SLUGS),
                    sefaria_config="ladino|Biblia de Ferrara [lad]",
                ),
                Version.sefaria(
                    "Trazladado en la lingua Espanyola, 1873",
                    "BOYADJIAN1873",
                    frozenset(TORAH_BOOK_SLUGS),
                    sefaria_config=(
                        "ladino|Trazladado en la lingua Espanyola, Estamperia "
                        "de A. H. Boyadjian, Konstantinopla 1873. "
                        "Transkrito por Yehuda Sidi, 2021 [lad]"
                    ),
                ),
            ],
        ),
        (
            LanguageCode.JAC,
            [Version.gateway("Jacalteco, Oriental", "JAC")],
        ),
        (
            LanguageCode.KEK,
            [Version.gateway("Kekchi", "KEK")],
        ),
        (
            LanguageCode.LA,
            [Version.gateway("Biblia Sacra Vulgata", "VULGATE")],
        ),
        (
            LanguageCode.MI,
            [Version.gateway("Maori Bible", "MAORI")],
        ),
        (
            LanguageCode.MK,
            [Version.gateway("Macedonian New Testament", "MNT")],
        ),
        (
            LanguageCode.MR,
            [Version.gateway("Marathi Bible: Easy-to-Read Version", "ERV-MR")],
        ),
        (
            LanguageCode.MVC,
            [Version.gateway("Mam, Central", "MVC")],
        ),
        (
            LanguageCode.MVJ,
            [Version.gateway("Mam de Todos Santos Chuchumatán", "MVJ")],
        ),
        (
            LanguageCode.NDS,
            [Version.gateway("Reimer 2001", "REIMER")],
        ),
        (
            LanguageCode.NE,
            [Version.gateway("Nepali Bible: Easy-to-Read Version", "ERV-NE")],
        ),
        (
            LanguageCode.NGU,
            [Version.gateway("Náhuatl de Guerrero", "NGU")],
        ),
        (
            LanguageCode.NL,
            [Version.gateway("Het Boek", "HTB")],
        ),
        (
            LanguageCode.NO,
            [
                Version.gateway("Det Norsk Bibelselskap 1930", "DNB1930"),
                Version.gateway("En Levende Bok", "LB"),
            ],
        ),
        (
            LanguageCode.OR,
            [Version.gateway("Oriya Bible: Easy-to-Read Version", "ERV-OR")],
        ),
        (
            LanguageCode.PA,
            [Version.gateway("Punjabi Bible: Easy-to-Read Version", "ERV-PA")],
        ),
        (
            LanguageCode.PL,
            [
                Version.gateway("Nowe Przymierze", "NP"),
                Version.gateway("Słowo Życia", "SZ-PL"),
                Version.gateway("Updated Gdańsk Bible", "UBG"),
            ],
        ),
        (
            LanguageCode.PPL,
            [Version.gateway("Ne Bibliaj Tik Nawat", "NBTN")],
        ),
        (
            LanguageCode.PT,
            [
                Version.gateway("Almeida Revista e Corrigida 2009", "ARC"),
                Version.gateway("Nova Traduҫão na Linguagem de Hoje 2000", "NTLH"),
                Version.gateway("Nova Versão Internacional", "NVI-PT"),
                Version.gateway("O Livro", "OL"),
                Version.gateway(
                    "Portuguese New Testament: Easy-to-Read Version", "VFL"
                ),
            ],
        ),
        (
            LanguageCode.QU,
            [Version.gateway("Mushuj Testamento Diospaj Shimi", "MTDS")],
        ),
        (
            LanguageCode.QUT,
            [Version.gateway("Quiché, Centro Occidental", "QUT")],
        ),
        (
            LanguageCode.RO,
            [
                Version.gateway("Cornilescu 1924 - Revised 2010, 2014", "RMNN"),
                Version.gateway("Nouă Traducere În Limba Română", "NTLR"),
            ],
        ),
        (
            LanguageCode.RU,
            [
                Version.gateway("New Russian Translation", "NRT"),
                Version.gateway("Священное Писание (Восточный Перевод)", "CARS"),
                Version.gateway(
                    "Священное Писание (Восточный перевод), версия для Таджикистана",
                    "CARST",
                ),
                Version.gateway(
                    "Священное Писание (Восточный перевод), версия с «Аллахом»", "CARSA"
                ),
                Version.gateway(
                    "Russian New Testament: Easy-to-Read Version", "ERV-RU"
                ),
                Version.gateway("Russian Synodal Version", "RUSV"),
            ],
        ),
        (
            LanguageCode.SK,
            [Version.gateway("Nádej pre kazdého", "NPK")],
        ),
        (
            LanguageCode.SO,
            [Version.gateway("Somali Bible", "SOM")],
        ),
        (
            LanguageCode.SQ,
            [Version.gateway("Albanian Bible", "ALB")],
        ),
        (
            LanguageCode.SR,
            [Version.gateway("Serbian New Testament: Easy-to-Read Version", "ERV-SR")],
        ),
        (
            LanguageCode.SV,
            [
                Version.gateway("Nya Levande Bibeln", "SVL"),
                Version.gateway("Svenska 1917", "SV1917"),
                Version.gateway("Svenska Folkbibeln", "SFB"),
                Version.gateway("Svenska Folkbibeln 2014", "SFB2014"),
            ],
        ),
        (
            LanguageCode.SW,
            [Version.gateway("Neno: Bibilia Takatifu", "SNT")],
        ),
        (
            LanguageCode.TA,
            [Version.gateway("Tamil Bible: Easy-to-Read Version", "ERV-TA")],
        ),
        (
            LanguageCode.TH,
            [
                Version.gateway("Thai New Contemporary Bible", "TNCV"),
                Version.gateway("Thai New Testament: Easy-to-Read Version", "ERV-TH"),
            ],
        ),
        (
            LanguageCode.TL,
            [
                Version.gateway("Ang Dating Biblia (1905)", "ADB1905"),
                Version.gateway("Ang Salita ng Diyos", "SND"),
            ],
        ),
        (
            LanguageCode.TWI,
            [Version.gateway("Nkwa Asem", "NA-TWI")],
        ),
        (
            LanguageCode.UK,
            [
                Version.gateway("Ukrainian Bible", "UKR"),
                Version.gateway(
                    "Ukrainian New Testament: Easy-to-Read Version", "ERV-UK"
                ),
            ],
        ),
        (
            LanguageCode.UR,
            [Version.gateway("Urdu Bible: Easy-to-Read Version", "ERV-UR")],
        ),
        (
            LanguageCode.USP,
            [Version.gateway("Uspanteco", "USP")],
        ),
        (
            LanguageCode.VI,
            [
                Version.gateway("1934 Vietnamese Bible", "VIET"),
                Version.gateway("Bản Dịch 2011", "BD2011"),
                Version.gateway("Vietnamese Bible: Easy-to-Read Version", "BPT"),
            ],
        ),
        (
            LanguageCode.YI,
            [
                Version.sefaria(
                    "Tanakh in Yiddish, 1914",
                    "NEUHAUSEN1914",
                    frozenset(TORAH_BOOK_SLUGS),
                    sefaria_config=(
                        "yiddish|Tanakh in Yiddish. Translated by "
                        "Ch. Neuhausen, A. Hyman Charlap; NY 1914 [yi]"
                    ),
                ),
                Version.sefaria(
                    "Yehoyesh's Yiddish Tanakh Translation",
                    "YEHOYESH",
                    frozenset(OLD_TESTAMENT_BOOK_SLUGS),
                    sefaria_config="yiddish|Yehoyesh's Yiddish Tanakh Translation [yi]",
                ),
            ],
        ),
    ]
)
LDS_VERSION_DATA: Final[VersionDataMap] = OrderedDict(
    [
        (
            LanguageCode.EN,
            [
                Version.book_of_mormon("Book of Mormon", "BOM"),
                Version.doctrine_and_covenants("Doctrine and Covenants", "DC"),
                Version.pearl_of_great_price("Pearl of Great Price", "PGP"),
            ],
        ),
    ]
)
QURAN_VERSION_DATA: Final[VersionDataMap] = OrderedDict(
    [
        (
            LanguageCode.AR,
            [Version.quran("Uthmani Arabic", "UTHMANI", aliases=("QURAN",))],
        ),
        (
            LanguageCode.EN,
            [
                Version.quran("Saheeh International", "QSI"),
                Version.quran("Marmaduke Pickthall", "QPICK"),
                Version.quran("Abdullah Yusuf Ali", "QYUSUF"),
            ],
        ),
        (
            LanguageCode.FA,
            [
                Version.quran("AbdolMohammad Ayati", "QAYATI"),
                Version.quran("Mohammad Mahdi Fooladvand", "QFOOL"),
            ],
        ),
        (
            LanguageCode.UZ,
            [Version.quran("Muhammad Sodik Muhammad Yusuf", "QSODIK")],
        ),
        (
            LanguageCode.UR,
            [Version.quran("Fateh Muhammad Jalandhry", "QJAL")],
        ),
        (
            LanguageCode.TR,
            [Version.quran("Diyanet İşleri", "QDIYANET")],
        ),
        (
            LanguageCode.RU,
            [Version.quran("Elmir Kuliev", "QKULIEV")],
        ),
    ]
)


@dataclass(frozen=True)
class ScriptureSystem:
    """A separately configurable collection of sacred texts and versions."""

    id: ScriptureSystemId
    display_name: str
    version_data: VersionDataMap

    @property
    def versions(self) -> tuple[Version, ...]:
        return tuple(
            version for versions in self.version_data.values() for version in versions
        )

    @property
    def version_labels(self) -> tuple[VersionLabel, ...]:
        return tuple(version.full_label for version in self.versions)

    @property
    def language_group_labels(self) -> tuple[LanguageGroup, ...]:
        return tuple(format_language_group(language) for language in self.version_data)

    def resolve_language_group(self, label: str) -> LanguageCode | None:
        language = LANGUAGE_GROUP_CODES.get(label)
        if language in self.version_data:
            return language
        return None

    def get_versions_for_language(
        self, language: LanguageCode
    ) -> tuple[VersionLabel, ...] | None:
        versions = self.version_data.get(language)
        if versions is None:
            return None
        return tuple(version.full_label for version in versions)


def format_language_group(code: LanguageCode) -> LanguageGroup:
    return LANGUAGE_GROUP_LABELS[code]


@dataclass(frozen=True)
class VersionCatalog:
    systems: tuple[ScriptureSystem, ...]

    @property
    def system_ids(self) -> tuple[ScriptureSystemId, ...]:
        return tuple(system.id for system in self.systems)

    @property
    def systems_by_id(self) -> dict[ScriptureSystemId, ScriptureSystem]:
        return {system.id: system for system in self.systems}

    @property
    def all_versions(self) -> tuple[Version, ...]:
        return tuple(version for system in self.systems for version in system.versions)

    @property
    def version_lookup(self) -> dict[VersionLabel, VersionCode]:
        lookup: dict[VersionLabel, VersionCode] = {}
        seen_codes: set[VersionCode] = set()
        for version in self.all_versions:
            label = version.full_label
            code = _canonicalize_version_code(version.code)
            if label in lookup:
                raise ValueError(f"Duplicate version label: {label!r}")
            if code in seen_codes:
                raise ValueError(f"Duplicate version code: {code!r}")
            lookup[label] = code
            seen_codes.add(code)
        return lookup

    @property
    def version_display_labels(self) -> dict[VersionCode, VersionCode]:
        return {
            _canonicalize_version_code(version.code): version.code
            for version in self.all_versions
        }

    @property
    def version_full_labels(self) -> dict[VersionCode, VersionLabel]:
        return {
            _canonicalize_version_code(version.code): version.full_label
            for version in self.all_versions
        }

    @property
    def versions_by_code(self) -> dict[VersionCode, Version]:
        return {
            _canonicalize_version_code(version.code): version
            for version in self.all_versions
        }

    @property
    def versions_by_system(self) -> dict[ScriptureSystemId, frozenset[VersionCode]]:
        return {
            system.id: frozenset(
                _canonicalize_version_code(version.code) for version in system.versions
            )
            for system in self.systems
        }

    @property
    def version_systems(self) -> dict[VersionCode, ScriptureSystemId]:
        return {
            version: system_id
            for system_id, versions in self.versions_by_system.items()
            for version in versions
        }

    @property
    def version_providers(self) -> dict[str, VersionProvider]:
        return {
            _canonicalize_version_code(version.code): version.provider
            for version in self.all_versions
        }

    @property
    def version_code_aliases(self) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for version in self.all_versions:
            canonical_code = _canonicalize_version_code(version.code)
            for alias in version.aliases:
                aliases[alias.upper()] = canonical_code
        return aliases

    def resolve_version_code(self, token: str) -> str | None:
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


VERSION_CATALOG: Final[VersionCatalog] = VersionCatalog(
    systems=(
        ScriptureSystem(
            id=ScriptureSystemId.BIBLE,
            display_name="Bible",
            version_data=BIBLE_VERSION_DATA,
        ),
        ScriptureSystem(
            id=ScriptureSystemId.LDS,
            display_name="LDS scriptures",
            version_data=LDS_VERSION_DATA,
        ),
        ScriptureSystem(
            id=ScriptureSystemId.QURAN,
            display_name="Qurʾan",
            version_data=QURAN_VERSION_DATA,
        ),
    )
)


def get_scripture_system(system_id: ScriptureSystemId) -> ScriptureSystem:
    return VERSION_CATALOG.systems_by_id[system_id]


ALL_VERSIONS: Final[tuple[Version, ...]] = VERSION_CATALOG.all_versions


def _supported_book_slugs_for_version(version: Version) -> frozenset[BookSlug]:
    if version.support_scope is VersionSupportScope.CUSTOM:
        return version.supported_book_slugs
    return (
        SUPPORT_BOOK_SLUGS_BY_SCOPE[version.support_scope]
        | version.additional_supported_book_slugs
    )


def _canonicalize_version_code(code: VersionCode) -> VersionCode:
    return code.upper()


VERSION_LOOKUP: Final[dict[VersionLabel, VersionCode]] = VERSION_CATALOG.version_lookup
VERSIONS: Final[tuple[VersionCode, ...]] = tuple(VERSION_LOOKUP.values())
VERSIONS_SET: Final[frozenset[VersionCode]] = frozenset(VERSIONS)
VERSION_DISPLAY_LABELS: Final[dict[VersionCode, VersionCode]] = (
    VERSION_CATALOG.version_display_labels
)
VERSION_FULL_LABELS: Final[dict[VersionCode, VersionLabel]] = (
    VERSION_CATALOG.version_full_labels
)
VERSIONS_BY_CODE: Final[dict[VersionCode, Version]] = VERSION_CATALOG.versions_by_code
VERSION_CODE_ALIASES: Final[dict[str, VersionCode]] = (
    VERSION_CATALOG.version_code_aliases
)
VERSIONS_BY_SYSTEM: Final[dict[ScriptureSystemId, frozenset[VersionCode]]] = (
    VERSION_CATALOG.versions_by_system
)
VERSION_SYSTEMS: Final[dict[VersionCode, ScriptureSystemId]] = (
    VERSION_CATALOG.version_systems
)


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
    return VERSION_CATALOG.resolve_version_code(token)


def get_version_system(version: str) -> ScriptureSystemId | None:
    normalized = resolve_version_code(version) or version.upper()
    return VERSION_SYSTEMS.get(normalized)


def get_version(version: str) -> Version | None:
    normalized = resolve_version_code(version) or version.upper()
    return VERSIONS_BY_CODE.get(normalized)


def get_sefaria_version_config(version: str) -> SefariaVersionConfig | None:
    configured = get_version(version)
    if configured is None:
        return None
    return configured.sefaria_config


VERSION_PROVIDERS: dict[str, VersionProvider] = VERSION_CATALOG.version_providers
VERSION_SUPPORTED_BOOK_SLUGS: dict[str, frozenset[str]] = {
    _canonicalize_version_code(version.code): _supported_book_slugs_for_version(version)
    for version in ALL_VERSIONS
}

BOOKS: tuple[str, ...] = (
    PROTESTANT_CANON_BOOK_SLUGS
    + APOCRYPHA_BOOK_SLUGS
    + SEFARIA_EXTRA_BOOK_SLUGS
    + LDS_STANDARD_WORKS_BOOK_SLUGS
    + QURAN_BOOK_SLUGS
)
