import unittest

from services.sefaria import normalize_sefaria_passage_reference, parse_passage_payload
from state import EMPTY, InlinePassageResult

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


if __name__ == "__main__":
    unittest.main()
