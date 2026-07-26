import unittest

from services.alquran_cloud import (
    ALQURAN_CLOUD_EDITION_IDS,
    build_quran_passage_url,
    format_quran_reference,
    parse_quran_reference,
    parse_surah_payload,
)
from state import EMPTY, InlinePassageResult

SURAH_PAYLOAD = {
    "code": 200,
    "status": "OK",
    "data": {
        "number": 1,
        "ayahs": [
            {"numberInSurah": 1, "text": "In the name of Allah."},
            {"numberInSurah": 2, "text": "All praise is due to Allah."},
            {
                "numberInSurah": 3,
                "text": "The Entirely Merciful, the Especially Merciful.",
            },
        ],
    },
}


class QuranParsingTests(unittest.TestCase):
    def test_parse_quran_reference_verse_range(self):
        reference = parse_quran_reference("Quran 2:255-257")
        assert reference is not None
        self.assertEqual(2, reference.surah)
        self.assertEqual(255, reference.start_ayah)
        self.assertEqual(257, reference.end_ayah)

    def test_parse_quran_reference_surah_only(self):
        reference = parse_quran_reference("Qur'an 1")
        assert reference is not None
        self.assertEqual(1, reference.surah)
        self.assertIsNone(reference.start_ayah)
        self.assertIsNone(reference.end_ayah)

    def test_parse_quran_reference_rejects_invalid_ranges(self):
        self.assertIsNone(parse_quran_reference("Quran 0:1"))
        self.assertIsNone(parse_quran_reference("Quran 2:257-255"))
        self.assertIsNone(parse_quran_reference("Genesis 1:1"))

    def test_format_quran_reference(self):
        reference = parse_quran_reference("Quran 2:255-257")
        assert reference is not None
        self.assertEqual("Qurʾan 2:255-257", format_quran_reference(reference))

    def test_build_quran_passage_url(self):
        self.assertEqual(
            "https://quran.com/2?startingVerse=255",
            build_quran_passage_url("Quran 2:255", "QSI"),
        )
        self.assertEqual("https://quran.com/1", build_quran_passage_url("Quran 1"))

    def test_parse_surah_payload(self):
        reference = parse_quran_reference("Quran 1:1-3")
        assert reference is not None
        result = parse_surah_payload(SURAH_PAYLOAD, version="QSI", reference=reference)
        self.assertIsInstance(result, str)
        assert isinstance(result, str)
        self.assertIn("Qurʾan 1:1-3 QSI", result)
        self.assertIn("¹ In the name of Allah.", result)
        self.assertIn("² All praise is due to Allah.", result)

    def test_parse_surah_payload_inline(self):
        reference = parse_quran_reference("Quran 1:1-3")
        assert reference is not None
        result = parse_surah_payload(
            SURAH_PAYLOAD,
            version="QSI",
            reference=reference,
            inline_details=True,
        )
        self.assertIsInstance(result, InlinePassageResult)
        assert isinstance(result, InlinePassageResult)
        self.assertEqual("quran/Qurʾan 1:1-3/QSI", result.result_id)
        self.assertEqual("https://quran.com/1?startingVerse=1", result.header_url)

    def test_parse_surah_payload_empty(self):
        reference = parse_quran_reference("Quran 1:1")
        assert reference is not None
        self.assertEqual(
            EMPTY,
            parse_surah_payload(
                {"status": "OK", "data": {"ayahs": []}},
                reference=reference,
            ),
        )

    def test_known_edition_ids(self):
        self.assertEqual("quran-uthmani", ALQURAN_CLOUD_EDITION_IDS["UTHMANI"])
        self.assertEqual("en.sahih", ALQURAN_CLOUD_EDITION_IDS["QSI"])
        self.assertEqual("fa.ayati", ALQURAN_CLOUD_EDITION_IDS["QAYATI"])
        self.assertEqual("uz.sodik", ALQURAN_CLOUD_EDITION_IDS["QSODIK"])


if __name__ == "__main__":
    unittest.main()
