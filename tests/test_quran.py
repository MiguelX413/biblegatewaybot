import unittest

from quran import format_quran_machine_reference, quran_surah_display_name
from services.alquran_cloud import (
    ALQURAN_CLOUD_EDITION_IDS,
    build_quran_passage_url,
    format_quran_reference,
    parse_quran_reference,
    parse_surah_payload,
)
from state import EMPTY, InlinePassageResult

SURAH_ONE_PAYLOAD = {
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
    def test_parse_quran_reference_accepts_numeric_forms(self):
        reference = parse_quran_reference("Quran 2")
        assert reference is not None
        self.assertEqual(2, reference.start_surah)
        self.assertIsNone(reference.start_ayah)
        self.assertEqual(2, reference.end_surah)
        self.assertIsNone(reference.end_ayah)

        reference = parse_quran_reference("Qur'an 2:255")
        assert reference is not None
        self.assertEqual(
            (2, 255, 2, 255),
            (
                reference.start_surah,
                reference.start_ayah,
                reference.end_surah,
                reference.end_ayah,
            ),
        )

        reference = parse_quran_reference("Quran 2:255–257")
        assert reference is not None
        self.assertEqual(
            (2, 255, 2, 257),
            (
                reference.start_surah,
                reference.start_ayah,
                reference.end_surah,
                reference.end_ayah,
            ),
        )

    def test_parse_quran_reference_accepts_named_surah_forms(self):
        reference = parse_quran_reference("Al-Baqarah")
        assert reference is not None
        self.assertEqual(
            (2, None, 2, None),
            (
                reference.start_surah,
                reference.start_ayah,
                reference.end_surah,
                reference.end_ayah,
            ),
        )

        reference = parse_quran_reference("Al-Baqarah 255")
        assert reference is not None
        self.assertEqual(
            (2, 255, 2, 255),
            (
                reference.start_surah,
                reference.start_ayah,
                reference.end_surah,
                reference.end_ayah,
            ),
        )

        reference = parse_quran_reference("Al-Baqarah:255")
        assert reference is not None
        self.assertEqual(
            (2, 255, 2, 255),
            (
                reference.start_surah,
                reference.start_ayah,
                reference.end_surah,
                reference.end_ayah,
            ),
        )

        reference = parse_quran_reference("Surah Al-Baqarah 255")
        assert reference is not None
        self.assertEqual(
            (2, 255, 2, 255),
            (
                reference.start_surah,
                reference.start_ayah,
                reference.end_surah,
                reference.end_ayah,
            ),
        )

        reference = parse_quran_reference("Sura Al-Baqarah 255")
        assert reference is not None
        self.assertEqual(
            (2, 255, 2, 255),
            (
                reference.start_surah,
                reference.start_ayah,
                reference.end_surah,
                reference.end_ayah,
            ),
        )

    def test_parse_quran_reference_accepts_scripture_and_surah_name(self):
        reference = parse_quran_reference("Qur'an al-Baqarah 2:255")
        assert reference is not None
        self.assertEqual(
            (2, 255, 2, 255),
            (
                reference.start_surah,
                reference.start_ayah,
                reference.end_surah,
                reference.end_ayah,
            ),
        )

        reference = parse_quran_reference("Quran al-Baqarah 255")
        assert reference is not None
        self.assertEqual(
            (2, 255, 2, 255),
            (
                reference.start_surah,
                reference.start_ayah,
                reference.end_surah,
                reference.end_ayah,
            ),
        )

    def test_parse_quran_reference_accepts_cross_surah_ranges(self):
        reference = parse_quran_reference("Quran 1-2")
        assert reference is not None
        self.assertEqual(
            (1, None, 2, None),
            (
                reference.start_surah,
                reference.start_ayah,
                reference.end_surah,
                reference.end_ayah,
            ),
        )

        reference = parse_quran_reference("Quran 1:2-2:4")
        assert reference is not None
        self.assertEqual(
            (1, 2, 2, 4),
            (
                reference.start_surah,
                reference.start_ayah,
                reference.end_surah,
                reference.end_ayah,
            ),
        )

    def test_parse_quran_reference_keeps_named_surah_ranges_as_ayah_ranges(self):
        reference = parse_quran_reference("Al-Fatiha 1-3")
        assert reference is not None
        self.assertEqual(
            (1, 1, 1, 3),
            (
                reference.start_surah,
                reference.start_ayah,
                reference.end_surah,
                reference.end_ayah,
            ),
        )

    def test_parse_quran_reference_rejects_invalid_forms(self):
        for passage in (
            "Quran 0",
            "Quran 115",
            "Quran 2:0",
            "Quran 2:257-255",
            "Quran 2-1",
            "Quran 2:4-1:2",
            "Quran 1-2:4",
            "Quran 1:2-2",
            "Qur'an al-Baqarah 3:255",
            "Qur'an al-Fātiḥah 2:1",
            "Genesis 1:1",
        ):
            self.assertIsNone(parse_quran_reference(passage), passage)

    def test_format_quran_reference_uses_canonical_display(self):
        reference = parse_quran_reference("Quran 2")
        assert reference is not None
        self.assertEqual("Qurʾān, al-Baqarah (2)", format_quran_reference(reference))

        reference = parse_quran_reference("Quran 2:255")
        assert reference is not None
        self.assertEqual(
            "Qurʾān, al-Baqarah (2):255",
            format_quran_reference(reference),
        )
        self.assertEqual(
            "Qurʾān, al-Baqarah (2):255 (Ṣaḥīḥ International)",
            format_quran_reference(reference, "ṢI"),
        )
        self.assertEqual(
            "Qurʾān, al-Baqarah (2):255 (Pickthall)",
            format_quran_reference(reference, "QPICK"),
        )
        self.assertEqual(
            "Qurʾān, al-Baqarah (2):255 (Yusuf Ali)",
            format_quran_reference(reference, "QYUSUF"),
        )
        self.assertEqual(
            "Qurʾān, al-Baqarah (2):255",
            format_quran_reference(reference, "UTHMANI"),
        )

        reference = parse_quran_reference("Quran 2:255-257")
        assert reference is not None
        self.assertEqual(
            "Qurʾān, al-Baqarah (2):255–257",
            format_quran_reference(reference),
        )

        reference = parse_quran_reference("Quran 1-2")
        assert reference is not None
        self.assertEqual(
            "Qurʾān, al-Fātiḥah (1)–al-Baqarah (2)",
            format_quran_reference(reference),
        )

        reference = parse_quran_reference("Quran 1:2-2:4")
        assert reference is not None
        self.assertEqual(
            "Qurʾān, al-Fātiḥah (1):2–al-Baqarah (2):4",
            format_quran_reference(reference),
        )
        self.assertEqual(
            "Qurʾān, al-Fātiḥah (1):2–al-Baqarah (2):4 (Ṣaḥīḥ International)",
            format_quran_reference(reference, "ṢI"),
        )

    def test_machine_reference_and_urls_remain_compact(self):
        reference = parse_quran_reference("Quran 1:2-2:4")
        assert reference is not None
        self.assertEqual("1:2-2:4", format_quran_machine_reference(reference))
        self.assertEqual(
            "https://quran.com/1?startingVerse=2",
            build_quran_passage_url(reference, "ṢI"),
        )
        self.assertEqual("https://quran.com/1", build_quran_passage_url("Quran 1-2"))

    def test_parse_surah_payload_uses_reader_facing_header(self):
        reference = parse_quran_reference("Quran 1:1-3")
        assert reference is not None
        result = parse_surah_payload(
            SURAH_ONE_PAYLOAD,
            version="ṢI",
            reference=reference,
        )
        self.assertIsInstance(result, str)
        assert isinstance(result, str)
        self.assertIn("Qurʾān, al-Fātiḥah (1):1–3 (Ṣaḥīḥ International)", result)
        self.assertIn("¹ In the name of Allah.", result)
        self.assertIn("² All praise is due to Allah.", result)

    def test_parse_surah_payload_inline_uses_compact_result_id(self):
        reference = parse_quran_reference("Quran 1:1-3")
        assert reference is not None
        result = parse_surah_payload(
            SURAH_ONE_PAYLOAD,
            version="ṢI",
            reference=reference,
            inline_details=True,
        )
        self.assertIsInstance(result, InlinePassageResult)
        assert isinstance(result, InlinePassageResult)
        self.assertEqual("quran/1:1-3/ṢI", result.result_id)
        self.assertEqual(
            "Qurʾān, al-Fātiḥah (1):1–3 (Ṣaḥīḥ International)",
            result.title,
        )
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
        self.assertEqual("en.sahih", ALQURAN_CLOUD_EDITION_IDS["ṢI"])
        self.assertEqual("fa.ayati", ALQURAN_CLOUD_EDITION_IDS["QAYATI"])
        self.assertEqual("uz.sodik", ALQURAN_CLOUD_EDITION_IDS["QSODIK"])

    def test_surah_display_names_are_canonical(self):
        self.assertEqual("al-Fātiḥah", quran_surah_display_name(1))
        self.assertEqual("al-Baqarah", quran_surah_display_name(2))


if __name__ == "__main__":
    unittest.main()
