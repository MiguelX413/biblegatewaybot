from collections import OrderedDict
from typing import TypedDict


class BookData(TypedDict):
    title: str
    slug: str
    aliases: tuple[str, ...]


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
            "—汉语 (ZH)—",
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
            "—العربية (AR)—",
            ["Arabic Bible: Easy-to-Read Version (ERV-AR)", "Ketab El Hayat (NAV)"],
        ),
        (
            "—अवधी (AWA)—",
            ["Awadhi Bible: Easy-to-Read Version (ERV-AWA)"],
        ),
        (
            "—Български (BG)—",
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
            "—Κοινη (GRC)—",
            [
                "1550 Stephanus New Testament (TR1550)",
                "1881 Westcott-Hort New Testament (WHNU)",
                "1894 Scrivener New Testament (TR1894)",
                "SBL Greek New Testament (SBLGNT)",
            ],
        ),
        (
            "—עברית (HE)—",
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
        ("—Latina (LA)—", ["Biblia Sacra Vulgata (VULGATE)"]),
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
        ("—Nawat (PPL)—", ["Ne Bibliaj Tik Nawat (NBTN)"]),
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
            "—Русский (RU)—",
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
            "—Українська (UK)—",
            [
                "Ukrainian Bible (UKR)",
                "Ukrainian New Testament: Easy-to-Read Version (ERV-UK)",
            ],
        ),
        (
            "—اردو (UR)—",
            ["Urdu Bible: Easy-to-Read Version (ERV-UR)"],
        ),
        ("—Uspanteco (USP)—", ["Uspanteco (USP)"]),
        (
            "—Tiêng Viêt (VI)—",
            [
                "1934 Vietnamese Bible (VIET)",
                "Bản Dịch 2011 (BD2011)",
                "Vietnamese Bible: Easy-to-Read Version (BPT)",
            ],
        ),
    ]
)
VERSION_LOOKUP = {
    "Hungarian Károli (KAR)": "KAR",
    "Maori Bible (MAORI)": "MAORI",
    "Russian Synodal Version (RUSV)": "RUSV",
    "La Biblia de las Américas (LBLA)": "LBLA",
    "Expanded Bible (EXB)": "EXB",
    "Book of Mormon (BOM)": "BOM",
    "Doctrine and Covenants (DC)": "DC",
    "Pearl of Great Price (PGP)": "PGP",
    "Nouvelle Edition de Genève – NEG1979 (NEG1979)": "NEG1979",
    "Chinese Standard Bible (Traditional) (CSBT)": "CSBT",
    "Mounce Reverse-Interlinear New Testament (MOUNCE)": "MOUNCE",
    "Chinese Union Version Modern Punctuation (Traditional) (CUVMPT)": "CUVMPT",
    "Mushuj Testamento Diospaj Shimi (MTDS)": "MTDS",
    "Urdu Bible: Easy-to-Read Version (ERV-UR)": "ERV-UR",
    "New Life Version (NLV)": "NLV",
    "New Russian Translation (NRT)": "NRT",
    "Uspanteco (USP)": "USP",
    "New American Standard Bible (NASB)": "NASB",
    "Young's Literal Translation (YLT)": "YLT",
    "Names of God Bible (NOG)": "NOG",
    "Chinese Union Version Modern Punctuation (Simplified) (CUVMPS)": "CUVMPS",
    "Wycliffe Bible (WYC)": "WYC",
    "English Standard Version Anglicised (ESVUK)": "ESVUK",
    "Reina Valera Contemporánea (RVC)": "RVC",
    "Knijga O Kristu (CRO)": "CRO",
    "Amplified Bible (AMP)": "AMP",
    "Worldwide English (New Testament) (WE)": "WE",
    "Dette er Biblen på dansk (DN1933)": "DN1933",
    "1550 Stephanus New Testament (TR1550)": "TR1550",
    "Conferenza Episcopale Italiana (CEI)": "CEI",
    "Bulgarian Bible (BULG)": "BULG",
    "Hindi Bible: Easy-to-Read Version (ERV-HI)": "ERV-HI",
    "BRG Bible (BRG)": "BRG",
    "Svenska Folkbibeln (SFB)": "SFB",
    "Nuova Riveduta 1994 (NR1994)": "NR1994",
    "Neno: Bibilia Takatifu (SNT)": "SNT",
    "Mam, Central (MVC)": "MVC",
    "Biblia Sacra Vulgata (VULGATE)": "VULGATE",
    "Mam de Todos Santos Chuchumatán (MVJ)": "MVJ",
    "Updated Gdańsk Bible (UBG)": "UBG",
    "Священное Писание (Восточный перевод), версия для Таджикистана (CARST)": "CARST",
    "Reina-Valera Antigua (RVA)": "RVA",
    "Revised Standard Version Catholic Edition (RSVCE)": "RSVCE",
    "Ang Dating Biblia (1905) (ADB1905)": "ADB1905",
    "Cherokee New Testament (CHR)": "CHR",
    "Vietnamese Bible: Easy-to-Read Version (BPT)": "BPT",
    "En Levende Bok (LB)": "LB",
    "Ukrainian Bible (UKR)": "UKR",
    "Schlachter 1951 (SCH1951)": "SCH1951",
    "Cakchiquel Occidental (CKW)": "CKW",
    "Revised Standard Version (RSV)": "RSV",
    "GOD’S WORD Translation (GW)": "GW",
    "Dios Habla Hoy (DHH)": "DHH",
    "Lexham English Bible (LEB)": "LEB",
    "Hrvatski Novi Zavjet – Rijeka 2001 (HNZ-RI)": "HNZ-RI",
    "La Palabra (España) (BLP)": "BLP",
    "Jacalteco, Oriental (JAC)": "JAC",
    "The Westminster Leningrad Codex (WLC)": "WLC",
    "Punjabi Bible: Easy-to-Read Version (ERV-PA)": "ERV-PA",
    "Nuova Riveduta 2006 (NR2006)": "NR2006",
    "Nepali Bible: Easy-to-Read Version (ERV-NE)": "ERV-NE",
    "Chinese Union Version (Simplified) (CUVS)": "CUVS",
    "Священное Писание (Восточный Перевод) (CARS)": "CARS",
    "Portuguese New Testament: Easy-to-Read Version (VFL)": "VFL",
    "Somali Bible (SOM)": "SOM",
    "Schlachter 2000 (SCH2000)": "SCH2000",
    "Traducción en lenguaje actual (TLA)": "TLA",
    "Thai New Testament: Easy-to-Read Version (ERV-TH)": "ERV-TH",
    "Complete Jewish Bible (CJB)": "CJB",
    "La Nuova Diodati (LND)": "LND",
    "Chinese New Testament: Easy-to-Read Version (ERV-ZH)": "ERV-ZH",
    "Ang Pulong Sa Dios (APSD-CEB)": "APSD-CEB",
    "Nueva Biblia al Día (NBD)": "NBD",
    "Nueva Biblia Latinoamericana de Hoy (NBLH)": "NBLH",
    "Contemporary English Version (CEV)": "CEV",
    "La Palabra (Hispanoamérica) (BLPH)": "BLPH",
    "New English Translation (NET Bible)": "NET",
    "New International Reader's Version (NIrV)": "NIRV",
    "New Revised Standard Version, Anglicised (NRSVA)": "NRSVA",
    "Svenska 1917 (SV1917)": "SV1917",
    "New International Version - UK (NIVUK)": "NIVUK",
    "1894 Scrivener New Testament (TR1894)": "TR1894",
    "The Voice (VOICE)": "VOICE",
    "Bulgarian New Testament: Easy-to-Read Version (ERV-BG)": "ERV-BG",
    "Reina Valera 1977 (RVR1977)": "RVR1977",
    "Russian New Testament: Easy-to-Read Version (ERV-RU)": "ERV-RU",
    "Chinese Standard Bible (Simplified) (CSBS)": "CSBS",
    "Nádej pre kazdého (NPK)": "NPK",
    "Священное Писание (Восточный перевод), версия с «Аллахом» (CARSA)": "CARSA",
    "Hawai‘i Pidgin (HWP)": "HWP",
    "Nkwa Asem (NA-TWI)": "NA-TWI",
    "Hungarian Bible: Easy-to-Read Version (ERV-HU)": "ERV-HU",
    "Reina-Valera 1960 (RVR1960)": "RVR1960",
    "Serbian New Testament: Easy-to-Read Version (ERV-SR)": "ERV-SR",
    "Bibelen på hverdagsdansk (BPH)": "BPH",
    "Nouă Traducere În Limba Română (NTLR)": "NTLR",
    "Awadhi Bible: Easy-to-Read Version (ERV-AWA)": "ERV-AWA",
    "English Standard Version (ESV)": "ESV",
    "Thai New Contemporary Bible (TNCV)": "TNCV",
    "Segond 21 (SG21)": "SG21",
    "King James Version (KJV)": "KJV",
    "JPS 1917 (JPS)": "JPS",
    "JPS, 1985 (NJPS)": "NJPS",
    "Revised JPS, 2023 (RJPS)": "RJPS",
    "International Standard Version (ISV)": "ISV",
    "Bible 21 (B21)": "B21",
    "Luther Bibel 1545 (LUTH1545)": "LUTH1545",
    "Reina-Valera 1995 (RVR1995)": "RVR1995",
    "Haitian Creole Version (HCV)": "HCV",
    "Palabra de Dios para Todos (PDT)": "PDT",
    "La Bible du Semeur (BDS)": "BDS",
    "Macedonian New Testament (MNT)": "MNT",
    "Bản Dịch 2011 (BD2011)": "BD2011",
    "La Bibbia della Gioia (BDG)": "BDG",
    "American Standard Version (ASV)": "ASV",
    "Raamattu 1933/38 (R1933)": "R1933",
    "1599 Geneva Bible (GNV)": "GNV",
    "World English Bible (WEB)": "WEB",
    "Easy-to-Read Version (ERV)": "ERV",
    "Amplified Bible, Classic Edition (AMPC)": "AMPC",
    "Beibl William Morgan (BWM)": "BWM",
    "New American Bible (Revised Edition) (NABRE)": "NABRE",
    "Nya Levande Bibeln (SVL)": "SVL",
    "Amuzgo de Guerrero (AMU)": "AMU",
    "Ang Pulong Sang Dios (HLGN)": "HLGN",
    "Modern English Version (MEV)": "MEV",
    "Hoffnung für Alle (HOF)": "HOF",
    "New Revised Standard Version, Anglicised Catholic Edition (NRSVACE)": "NRSVACE",
    "Neue Genfer Übersetzung (NGU-DE)": "NGU-DE",
    "Oriya Bible: Easy-to-Read Version (ERV-OR)": "ERV-OR",
    "1940 Bulgarian Bible (BG1940)": "BG1940",
    "Slovo na cestu (SNC)": "SNC",
    "New Revised Standard Version Catholic Edition (NRSVCE)": "NRSVCE",
    "New Revised Standard Version Updated Edition (NRSVue)": "NRSVUE",
    "Common English Bible (CEB)": "CEB",
    "Chinese Union Version (Traditional) (CUV)": "CUV",
    "New International Version (NIV)": "NIV",
    "New Century Version (NCV)": "NCV",
    "Quiché, Centro Occidental (QUT)": "QUT",
    "Svenska Folkbibeln 2014 (SFB2014)": "SFB2014",
    "Ketab El Hayat (NAV)": "NAV",
    "21st Century King James Version (KJ21)": "KJ21",
    "Kekchi (KEK)": "KEK",
    "Chinanteco de Comaltepec (CCO)": "CCO",
    "Reimer 2001 (REIMER)": "REIMER",
    "Marathi Bible: Easy-to-Read Version (ERV-MR)": "ERV-MR",
    "Louis Segond (LSG)": "LSG",
    "O Livro (OL)": "OL",
    "Holman Christian Standard Bible (HCSB)": "HCSB",
    "1934 Vietnamese Bible (VIET)": "VIET",
    "Albanian Bible (ALB)": "ALB",
    "The Message (MSG)": "MSG",
    "Hungarian New Translation (NT-HU)": "NT-HU",
    "Bulgarian Protestant Bible (BPB)": "BPB",
    "1881 Westcott-Hort New Testament (WHNU)": "WHNU",
    "Het Boek (HTB)": "HTB",
    "Ne Bibliaj Tik Nawat (NBTN)": "NBTN",
    "Arabic Bible: Easy-to-Read Version (ERV-AR)": "ERV-AR",
    "Almeida Revista e Corrigida 2009 (ARC)": "ARC",
    "Living Bible (TLB)": "TLB",
    "SBL Greek New Testament (SBLGNT)": "SBLGNT",
    "Orthodox Jewish Bible (OJB)": "OJB",
    "Det Norsk Bibelselskap 1930 (DNB1930)": "DNB1930",
    "New Living Translation (NLT)": "NLT",
    "International Children’s Bible (ICB)": "ICB",
    "Nowe Przymierze (NP)": "NP",
    "Náhuatl de Guerrero (NGU)": "NGU",
    "Nova Traduҫão na Linguagem de Hoje 2000 (NTLH)": "NTLH",
    "Chinese Contemporary Bible (CCB)": "CCB",
    "Jubilee Bible 2000 (Spanish) (JBS)": "JBS",
    "Icelandic Bible (ICELAND)": "ICELAND",
    "Nueva Versión Internacional (NVI)": "NVI",
    "Tamil Bible: Easy-to-Read Version (ERV-TA)": "ERV-TA",
    "Nova Versão Internacional (NVI-PT)": "NVI-PT",
    "J.B. Phillips New Testament (PHILLIPS)": "PHILLIPS",
    "Habrit Hakhadasha/Haderekh (HHH)": "HHH",
    "Darby Translation (DARBY)": "DARBY",
    "Ukrainian New Testament: Easy-to-Read Version (ERV-UK)": "ERV-UK",
    "Authorized (King James) Version (AKJV)": "AKJV",
    "Chinese New Version (Traditional) (CNVT)": "CNVT",
    "Cornilescu 1924 - Revised 2010, 2014 (RMNN)": "RMNN",
    "Słowo Życia (SZ-PL)": "SZ-PL",
    "Disciples’ Literal New Testament (DLNT)": "DLNT",
    "Ang Salita ng Diyos (SND)": "SND",
    "Good News Translation (GNT)": "GNT",
    "Nueva Traducción Viviente (NTV)": "NTV",
    "New Revised Standard Version (NRSV)": "NRSV",
    "Douay-Rheims 1899 American Edition (DRA)": "DRA",
    "Chinese New Version (Simplified) (CNVS)": "CNVS",
    "Jubilee Bible 2000 (JUB)": "JUB",
    "New King James Version (NKJV)": "NKJV",
    "Nueva Versión Internacional (Castilian) (CST)": "CST",
}
VERSIONS = tuple(VERSION_LOOKUP.values())
VERSION_DISPLAY_LABELS = {
    code: (
        label.rsplit("(", 1)[1][:-1] if label.endswith(")") and "(" in label else code
    )
    for label, code in VERSION_LOOKUP.items()
}


def format_version_label(version: str) -> str:
    return VERSION_DISPLAY_LABELS.get(version.upper(), version)


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
        "aliases": ("sirach", "ecclesiasticus", "sir"),
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
    "TLA": CORE_DEUTEROCANON_BOOK_SLUGS,
    "WYC": CORE_DEUTEROCANON_BOOK_SLUGS,
}
VERSION_PROVIDERS: dict[str, str] = {code: "biblegateway" for code in VERSIONS}
SEFARIA_VERSION_TITLES: dict[str, str] = {
    "JPS": "The Holy Scriptures: A New Translation (JPS 1917)",
    "NJPS": "Tanakh: The Holy Scriptures, published by JPS",
    "RJPS": "THE JPS TANAKH: Gender-Sensitive Edition",
}
VERSION_PROVIDERS.update({code: "sefaria" for code in SEFARIA_VERSION_TITLES})
for code in ("BOM", "DC", "PGP"):
    VERSION_PROVIDERS[code] = "lds"
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
for code in ("JPS", "NJPS", "RJPS"):
    VERSION_SUPPORTED_BOOK_SLUGS[code] = frozenset(OLD_TESTAMENT_BOOK_SLUGS)
VERSION_SUPPORTED_BOOK_SLUGS["BOM"] = frozenset(BOOK_OF_MORMON_BOOK_SLUGS)
VERSION_SUPPORTED_BOOK_SLUGS["DC"] = frozenset(DOCTRINE_AND_COVENANTS_BOOK_SLUGS)
VERSION_SUPPORTED_BOOK_SLUGS["PGP"] = frozenset(PEARL_OF_GREAT_PRICE_BOOK_SLUGS)

BOOKS: tuple[str, ...] = (
    PROTESTANT_CANON_BOOK_SLUGS + APOCRYPHA_BOOK_SLUGS + LDS_STANDARD_WORKS_BOOK_SLUGS
)
