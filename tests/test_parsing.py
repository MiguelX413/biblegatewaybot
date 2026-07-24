import unittest

from parsing import (
    build_passage_from_ref,
    canonicalize_reference,
    decode_linked_reference,
    extract_leading_book_name,
    find_requested_book,
    get_version_provider,
    normalize_book_name,
    normalize_reference_lookup_key,
    other_version,
    parse_get_request,
    supported_book_slugs,
    version_supports_book_slug,
    version_supports_passage,
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

    def test_canonicalize_reference(self):
        self.assertEqual("Wisdom 3:5-7", canonicalize_reference("wisdom 3 : 5 - 7"))
        self.assertEqual("1 Corinthians 13:4-7", canonicalize_reference("1co13:4 - 7"))
        self.assertEqual("1 Maccabees 2:1", canonicalize_reference("1 maccabees 2:1"))

    def test_normalize_book_name_handles_special_cases(self):
        self.assertEqual(
            ("revelation", "Revelation"),
            normalize_book_name("Revelation of Jesus Christ"),
        )
        self.assertEqual(
            ("songofsolomon", "Song of Solomon"), normalize_book_name("Song of Songs")
        )
        self.assertEqual(("psalm", "Psalm"), normalize_book_name("Psalms"))
        self.assertEqual(("1corinthians", "1 Corinthians"), normalize_book_name("1co"))
        self.assertEqual(("john", "John"), normalize_book_name("jn"))

    def test_extract_leading_book_name_handles_compact_forms(self):
        self.assertEqual("1co", extract_leading_book_name("1co13:4-7"))
        self.assertEqual("jn", extract_leading_book_name("jn3:16"))
        self.assertEqual(
            "Song of Songs", extract_leading_book_name("Song of Songs 1:1")
        )

    def test_find_requested_book(self):
        self.assertEqual(("john", "John"), find_requested_book("John 3:16"))
        self.assertEqual(("john", "John"), find_requested_book("jn 3:16"))
        self.assertEqual(
            ("1corinthians", "1 Corinthians"), find_requested_book("1co13:4-7")
        )
        self.assertEqual(("genesis", "Genesis"), find_requested_book("gen 1:1"))
        self.assertEqual(("tobit", "Tobit"), find_requested_book("Tobit 4:7"))
        self.assertEqual(
            ("wisdom", "Wisdom"), find_requested_book("Wisdom of Solomon 3:5-7")
        )
        self.assertEqual(
            ("songofsolomon", "Song of Solomon"),
            find_requested_book("Song of Songs 1:1"),
        )

    def test_normalize_reference_lookup_key(self):
        self.assertEqual("john 3:16", normalize_reference_lookup_key(" jn 3 : 16 "))
        self.assertEqual(
            "1 corinthians 13:4-7",
            normalize_reference_lookup_key("1co13:4 - 7"),
        )
        self.assertEqual(
            "song of solomon 1:1",
            normalize_reference_lookup_key("Song of Songs 1 : 1"),
        )

    def test_version_provider_defaults_to_biblegateway(self):
        self.assertEqual("biblegateway", get_version_provider("NIV"))
        self.assertEqual("sefaria", get_version_provider("JPS"))
        self.assertEqual("sefaria", get_version_provider("NJPS"))
        self.assertEqual("sefaria", get_version_provider("RJPS"))

    def test_supported_book_slugs_capture_scope_overrides(self):
        self.assertIn("genesis", supported_book_slugs("NIV"))
        self.assertNotIn("genesis", supported_book_slugs("DLNT"))
        self.assertIn("john", supported_book_slugs("DLNT"))
        self.assertIn("genesis", supported_book_slugs("WLC"))
        self.assertNotIn("matthew", supported_book_slugs("WLC"))
        self.assertIn("genesis", supported_book_slugs("JPS"))
        self.assertNotIn("matthew", supported_book_slugs("JPS"))
        self.assertIn("genesis", supported_book_slugs("NJPS"))
        self.assertNotIn("matthew", supported_book_slugs("NJPS"))
        self.assertIn("genesis", supported_book_slugs("RJPS"))
        self.assertNotIn("matthew", supported_book_slugs("RJPS"))

    def test_version_supports_book_slug(self):
        self.assertTrue(version_supports_book_slug("NRSVUE", "1esdras"))
        self.assertTrue(version_supports_book_slug("NABRE", "tobit"))
        self.assertFalse(version_supports_book_slug("NABRE", "1esdras"))

    def test_version_supports_passage(self):
        self.assertEqual((False, "John"), version_supports_passage("JPS", "John 3:16"))
        self.assertEqual((False, "John"), version_supports_passage("JPS", "jn3:16"))
        self.assertEqual(
            (True, "Genesis"), version_supports_passage("JPS", "Genesis 1:1")
        )
        self.assertEqual((True, "Genesis"), version_supports_passage("JPS", "gen 1:1"))
        self.assertEqual((False, "Tobit"), version_supports_passage("JPS", "Tobit 4:7"))
        self.assertEqual(
            (True, "Tobit"), version_supports_passage("NABRE", "Tobit 4:7")
        )

    def test_decode_linked_reference_for_apocrypha(self):
        self.assertEqual(
            "1 Maccabees 2:1-5", decode_linked_reference("1maccabees2V1-5")
        )


if __name__ == "__main__":
    unittest.main()
