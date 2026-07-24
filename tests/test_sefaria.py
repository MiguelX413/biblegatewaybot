import unittest

from services.sefaria import parse_passage_payload
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
        self.assertIn("Genesis 1:1-2 (JPS)", result)
        self.assertIn("In the beginning God created the heaven and the earth.", result)

    def test_parse_passage_payload_inline(self):
        result = parse_passage_payload(
            PASSAGE_PAYLOAD, version="JPS", inline_details=True
        )
        self.assertIsInstance(result, InlinePassageResult)
        self.assertEqual("Genesis 1:1-2/JPS", result.result_id)

    def test_parse_passage_payload_empty(self):
        self.assertEqual(EMPTY, parse_passage_payload({"versions": []}, version="JPS"))


if __name__ == "__main__":
    unittest.main()
