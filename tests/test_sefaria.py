import unittest

from services.sefaria import (
    build_sefaria_passage_url,
    normalize_sefaria_passage_reference,
    parse_passage_payload,
    resolve_sefaria_version_query,
)
from state import EMPTY, InlinePassageResult
from versions import SEFARIA_VERSION_CONFIGS

PASSAGE_PAYLOAD = {
    "ref": "Genesis 1:1-2",
    "versions": [
        {
            "versionTitle": "The Holy Scriptures: A New Translation (JPS 1917)",
            "text": [
                "In the beginning God created the heaven and the earth.",
                "Now the earth was unformed and void.",
            ],
        }
    ],
}


class SefariaParsingTests(unittest.TestCase):
    def test_parse_passage_payload(self):
        result = parse_passage_payload(PASSAGE_PAYLOAD, version="JPS")
        self.assertIsInstance(result, str)
        assert isinstance(result, str)
        self.assertIn("Genesis 1:1-2 JPS", result)
        self.assertIn(
            "¹ In the beginning God created the heaven and the earth.", result
        )
        self.assertIn("² Now the earth was unformed and void.", result)

    def test_parse_passage_payload_inline(self):
        result = parse_passage_payload(
            PASSAGE_PAYLOAD, version="JPS", inline_details=True
        )
        self.assertIsInstance(result, InlinePassageResult)
        assert isinstance(result, InlinePassageResult)
        self.assertEqual("Genesis 1:1-2/JPS", result.result_id)

    def test_parse_passage_payload_empty(self):
        self.assertEqual(EMPTY, parse_passage_payload({"versions": []}, version="JPS"))

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
            "JPS",
            SEFARIA_VERSION_CONFIGS,
        )
        self.assertEqual(
            "https://sefaria.org/Genesis.1:1"
            "?lang=bi&ven=english%7CThe%20Holy%20Scriptures%3A%20A%20New%20Translation%20%28JPS%201917%29",
            build_sefaria_passage_url("Genesis 1:1", "JPS", version_query),
        )

    def test_build_sefaria_passage_url_includes_yiddish_version(self):
        version_query = resolve_sefaria_version_query(
            "Genesis 1:1",
            "YEHOYESH",
            SEFARIA_VERSION_CONFIGS,
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
