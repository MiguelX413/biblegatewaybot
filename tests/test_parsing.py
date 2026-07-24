import unittest

from parsing import (
    build_passage_from_ref,
    decode_linked_reference,
    other_version,
    parse_apocrypha_reference,
    parse_get_request,
    passage_uses_apocrypha,
    supported_apocrypha_books,
    version_supports_apocrypha_book,
    version_supports_apocrypha,
)


class ParsingTests(unittest.TestCase):
    def test_parse_get_uses_default_version(self):
        version, passage = parse_get_request("/get John 3:16", "NIV")
        self.assertEqual(("NIV", "John 3:16"), (version, passage))

    def test_parse_get_uses_command_suffix_version(self):
        version, passage = parse_get_request("/getnlt 1 cor 13:4-7", "NIV")
        self.assertEqual(("NLT", "1 cor 13:4-7"), (version, passage))

    def test_parse_get_uses_leading_passage_version(self):
        version, passage = parse_get_request("/get NASB John 3:16", "NIV")
        self.assertEqual(("NASB", "John 3:16"), (version, passage))

    def test_parse_get_rejects_invalid_version(self):
        version, passage = parse_get_request("/getabc John 3:16", "NIV")
        self.assertEqual((None, None), (version, passage))

    def test_build_passage_from_ref_normalizes_revelation_name(self):
        passage = build_passage_from_ref(("Revelation of Jesus Christ", 1, 1, 1, 3))
        self.assertEqual("Revelation 1:1-1:3", passage)

    def test_other_version_flips_nasb(self):
        self.assertEqual("NIV", other_version("NASB"))
        self.assertEqual("NASB", other_version("NIV"))

    def test_parse_apocrypha_reference(self):
        self.assertEqual("Wisdom 3:5-7", parse_apocrypha_reference("wisdom 3:5-7"))
        self.assertEqual(
            "1 Maccabees 2:1", parse_apocrypha_reference("1 maccabees 2:1")
        )

    def test_passage_uses_apocrypha(self):
        self.assertTrue(passage_uses_apocrypha("Tobit 4:7"))
        self.assertFalse(passage_uses_apocrypha("John 3:16"))

    def test_version_supports_apocrypha(self):
        self.assertTrue(version_supports_apocrypha("NRSVUE"))
        self.assertFalse(version_supports_apocrypha("NIV"))

    def test_version_supports_specific_apocrypha_book(self):
        self.assertTrue(version_supports_apocrypha_book("NABRE", "Tobit"))
        self.assertFalse(version_supports_apocrypha_book("NABRE", "1 Esdras"))
        self.assertTrue(version_supports_apocrypha_book("NRSVUE", "1 Esdras"))

    def test_supported_apocrypha_books_are_conservative(self):
        self.assertNotIn("1 Esdras", supported_apocrypha_books("NABRE"))
        self.assertIn("1 Esdras", supported_apocrypha_books("NRSVUE"))

    def test_decode_linked_reference_for_apocrypha(self):
        self.assertEqual(
            "1 Maccabees 2:1-5", decode_linked_reference("1maccabees2V1-5")
        )


if __name__ == "__main__":
    unittest.main()
