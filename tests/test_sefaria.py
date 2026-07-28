import unittest

from services.sefaria import (
    build_sefaria_passage_url,
    normalize_sefaria_passage_reference,
    parse_passage_payload,
    parse_v1_he_passage_payload,
    parse_v1_text_passage_payload,
    resolve_sefaria_version_query,
)
from state import EMPTY, InlinePassageResult
from versions import get_sefaria_version_config

PASSAGE_PAYLOAD = {
    "ref": "Genesis 1:1-2",
    "versions": [
        {
            "versionTitle": "The Holy Scriptures: A New Translation (JPS 1917)",
            "text": [
                "Synthetic Sefaria passage.",
                "Second synthetic Sefaria passage.",
            ],
        }
    ],
}

V1_HE_PASSAGE_PAYLOAD = {
    "ref": "Genesis 1:1-2",
    "heVersionTitle": (
        "Tanakh in Yiddish. Translated by Ch. Neuhausen, A. Hyman Charlap; NY 1914 [yi]"
    ),
    "he": [
        "סינטעטישער ערשטער זאַץ.",
        "סינטעטישער צווייטער זאַץ.",
    ],
}

V1_TEXT_PASSAGE_PAYLOAD = {
    "ref": "Genesis 1:1-2",
    "versionTitle": "Biblia de Ferrara [lad]",
    "text": [
        "Fraza sintetika primera.",
        "Fraza sintetika segunda.",
    ],
}


class SefariaParsingTests(unittest.TestCase):
    def test_parse_passage_payload(self):
        result = parse_passage_payload(PASSAGE_PAYLOAD, version="JPS")
        self.assertIsInstance(result, str)
        assert isinstance(result, str)
        self.assertIn("Genesis 1:1–2 JPS", result)
        self.assertIn("¹ Synthetic Sefaria passage.", result)
        self.assertIn("² Second synthetic Sefaria passage.", result)

    def test_parse_passage_payload_inline(self):
        result = parse_passage_payload(
            PASSAGE_PAYLOAD, version="JPS", inline_details=True
        )
        self.assertIsInstance(result, InlinePassageResult)
        assert isinstance(result, InlinePassageResult)
        self.assertEqual("Genesis 1:1-2/JPS", result.result_id)

    def test_parse_passage_payload_empty(self):
        self.assertEqual(EMPTY, parse_passage_payload({"versions": []}, version="JPS"))

    def test_parse_v1_he_passage_payload(self):
        result = parse_v1_he_passage_payload(
            V1_HE_PASSAGE_PAYLOAD, version="NEUHAUSEN1914"
        )
        self.assertIsInstance(result, str)
        assert isinstance(result, str)
        self.assertIn("Genesis 1:1–2 NEUHAUSEN1914", result)
        self.assertIn("¹ סינטעטישער ערשטער זאַץ.", result)
        self.assertIn("² סינטעטישער צווייטער זאַץ.", result)

    def test_parse_v1_text_passage_payload(self):
        result = parse_v1_text_passage_payload(
            V1_TEXT_PASSAGE_PAYLOAD, version="FERRARA"
        )
        self.assertIsInstance(result, str)
        assert isinstance(result, str)
        self.assertIn("Genesis 1:1–2 FERRARA", result)
        self.assertIn("¹ Fraza sintetika primera.", result)
        self.assertIn("² Fraza sintetika segunda.", result)

    def test_normalize_sefaria_passage_reference_for_apocrypha(self):
        self.assertEqual(
            "The Book of Maccabees I 1:1",
            normalize_sefaria_passage_reference("1 Maccabees 1:1", "BRENTON"),
        )
        self.assertEqual(
            "The Book of Maccabees II 1:1",
            normalize_sefaria_passage_reference("2 Maccabees 1:1", "SCOMM"),
        )
        self.assertEqual(
            "Ben Sira 1:1",
            normalize_sefaria_passage_reference("Sirach 1:1", "SCOMM"),
        )
        self.assertEqual(
            "Letter of Aristeas 1:1",
            normalize_sefaria_passage_reference("Letter of Aristeas 1:1", "ARISTEAS"),
        )

    def test_build_sefaria_passage_url_includes_specific_version(self):
        version_query = resolve_sefaria_version_query(
            "Genesis 1:1",
            get_sefaria_version_config("JPS"),
        )
        self.assertEqual(
            "https://sefaria.org/Genesis.1:1"
            "?lang=bi&ven=english%7CThe%20Holy%20Scriptures%3A%20A%20New%20Translation%20%28JPS%201917%29",
            build_sefaria_passage_url("Genesis 1:1", "JPS", version_query),
        )

    def test_build_sefaria_passage_url_includes_yiddish_version(self):
        version_query = resolve_sefaria_version_query(
            "Genesis 1:1",
            get_sefaria_version_config("YEHOYESH"),
        )
        self.assertEqual(
            "yiddish|Yehoyesh's Yiddish Tanakh Translation [yi]",
            version_query,
        )
        self.assertEqual(
            "https://sefaria.org/Genesis.1:1"
            "?lang=bi&ven=yiddish%7CYehoyesh%27s%20Yiddish%20Tanakh%20Translation%20%5Byi%5D",
            build_sefaria_passage_url("Genesis 1:1", "YEHOYESH", version_query),
        )


if __name__ == "__main__":
    unittest.main()
