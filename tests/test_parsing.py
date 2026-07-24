import unittest

from parsing import (
    TELEGRAM_MESSAGE_LIMIT,
    build_passage_from_ref,
    canonicalize_reference,
    decode_linked_reference,
    extract_leading_book_name,
    find_requested_book,
    format_inline_passage_entities,
    format_passage_chunks,
    format_passage_entities,
    get_version_provider,
    normalize_book_name,
    normalize_reference_lookup_key,
    other_version,
    parse_get_request,
    resolve_auto_version,
    supported_book_slugs,
    supported_versions_for_book_slug,
    version_supports_book_slug,
    version_supports_passage,
)


class ParsingTests(unittest.TestCase):
    def test_format_passage_entities_uses_expandable_blockquote(self):
        text, entities = format_passage_entities(
            "John 3:16 NIV\n\nFor God so loved the world."
        )
        self.assertEqual("John 3:16 NIV\nFor God so loved the world.", text)
        self.assertEqual(2, len(entities))
        self.assertEqual("bold", entities[0].type)
        self.assertEqual(0, entities[0].offset)
        self.assertEqual(len("John 3:16 NIV"), entities[0].length)
        self.assertEqual("expandable_blockquote", entities[1].type)
        self.assertEqual(len("John 3:16 NIV\n"), entities[1].offset)
        self.assertEqual(len("For God so loved the world."), entities[1].length)

    def test_format_passage_entities_can_link_header(self):
        text, entities = format_passage_entities(
            "John 3:16 NIV\n\nFor God so loved the world.",
            header_url="https://www.biblegateway.com/passage/?search=John%203%3A16&version=NIV",
        )
        self.assertEqual("John 3:16 NIV\nFor God so loved the world.", text)
        self.assertEqual(3, len(entities))
        self.assertEqual("bold", entities[0].type)
        self.assertEqual("text_link", entities[1].type)
        self.assertEqual(
            "https://www.biblegateway.com/passage/?search=John%203%3A16&version=NIV",
            entities[1].url,
        )
        self.assertEqual("expandable_blockquote", entities[2].type)

    def test_format_passage_chunks_splits_long_messages(self):
        paragraph = "x" * 3000
        chunks = format_passage_chunks(f"1 Nephi 1 BOM\n\n{paragraph}\n\n{paragraph}")
        self.assertEqual(2, len(chunks))
        self.assertTrue(chunks[0][0].startswith("1 Nephi 1 BOM\n"))
        self.assertEqual("expandable_blockquote", chunks[0][1][-1].type)
        self.assertEqual("expandable_blockquote", chunks[1][1][0].type)
        self.assertLessEqual(len(chunks[0][0]), TELEGRAM_MESSAGE_LIMIT)
        self.assertLessEqual(len(chunks[1][0]), TELEGRAM_MESSAGE_LIMIT)

    def test_format_inline_passage_entities_truncates_long_messages(self):
        paragraph = "x" * 3000
        text, entities = format_inline_passage_entities(
            f"1 Nephi 1 BOM\n\n{paragraph}\n\n{paragraph}"
        )
        self.assertTrue(text.startswith("1 Nephi 1 BOM\n"))
        self.assertIn("…continued; use /get for the full passage.", text)
        self.assertLessEqual(len(text), TELEGRAM_MESSAGE_LIMIT)
        self.assertEqual(2, len(entities))
        self.assertEqual("bold", entities[0].type)
        self.assertEqual("expandable_blockquote", entities[1].type)

    def test_parse_get_uses_default_version(self):
        version, passage, explicit = parse_get_request("/get John 3:16", "NIV")
        self.assertEqual(("NIV", "John 3:16", False), (version, passage, explicit))

    def test_parse_get_uses_trailing_version(self):
        version, passage, explicit = parse_get_request("/get 1 cor 13:4-7 NLT", "NIV")
        self.assertEqual(("NLT", "1 cor 13:4-7", True), (version, passage, explicit))

    def test_parse_get_prompts_for_passage_when_only_version_is_given(self):
        version, passage, explicit = parse_get_request("/get NASB", "NIV")
        self.assertEqual(("NASB", None, True), (version, passage, explicit))

    def test_parse_get_rejects_old_command_suffix_format(self):
        version, passage, explicit = parse_get_request("/getabc John 3:16", "NIV")
        self.assertEqual((None, None, False), (version, passage, explicit))

    def test_parse_get_treats_non_version_tail_as_part_of_reference(self):
        version, passage, explicit = parse_get_request("/get John 3:16 earth", "NIV")
        self.assertEqual(
            ("NIV", "John 3:16 earth", False), (version, passage, explicit)
        )

    def test_parse_get_rejects_non_get_commands(self):
        version, passage, explicit = parse_get_request("/search John 3:16", "NIV")
        self.assertEqual((None, None, False), (version, passage, explicit))

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
        self.assertEqual(("1nephi", "1 Nephi"), find_requested_book("1 Nephi 3:7"))
        self.assertEqual(
            ("doctrineandcovenants", "Doctrine and Covenants"),
            find_requested_book("D&C 1:1"),
        )
        self.assertEqual(("abraham", "Abraham"), find_requested_book("Abraham 3:22"))
        self.assertEqual(
            ("josephsmithhistory", "Joseph Smith—History"),
            find_requested_book("Joseph Smith-History 1:15"),
        )
        self.assertEqual(
            ("wordsofmormon", "Words of Mormon"),
            find_requested_book("Words of Mormon 1:1"),
        )
        self.assertEqual(("genesis", "Genesis"), find_requested_book("gen 1:1"))
        self.assertEqual(("tobit", "Tobit"), find_requested_book("Tobit 4:7"))
        self.assertEqual(
            ("3maccabees", "3 Maccabees"), find_requested_book("3 Maccabees 1:1")
        )
        self.assertEqual(
            ("4maccabees", "4 Maccabees"), find_requested_book("4 Maccabees 1:1")
        )
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
        self.assertEqual("lds", get_version_provider("BOM"))
        self.assertEqual("lds", get_version_provider("DC"))
        self.assertEqual("lds", get_version_provider("PGP"))

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
        self.assertIn("1nephi", supported_book_slugs("BOM"))
        self.assertNotIn("genesis", supported_book_slugs("BOM"))
        self.assertIn("doctrineandcovenants", supported_book_slugs("DC"))
        self.assertNotIn("1nephi", supported_book_slugs("DC"))
        self.assertIn("abraham", supported_book_slugs("PGP"))
        self.assertNotIn("john", supported_book_slugs("PGP"))
        self.assertIn("3maccabees", supported_book_slugs("NRSVUE"))
        self.assertIn("4maccabees", supported_book_slugs("NRSVUE"))
        self.assertIn("3maccabees", supported_book_slugs("NRSVA"))
        self.assertIn("4maccabees", supported_book_slugs("RSV"))

    def test_version_supports_book_slug(self):
        self.assertTrue(version_supports_book_slug("NRSVUE", "1esdras"))
        self.assertTrue(version_supports_book_slug("NABRE", "tobit"))
        self.assertFalse(version_supports_book_slug("NABRE", "1esdras"))

    def test_supported_versions_for_book_slug(self):
        self.assertEqual(frozenset({"BOM"}), supported_versions_for_book_slug("1nephi"))
        self.assertEqual(
            frozenset({"DC"}), supported_versions_for_book_slug("doctrineandcovenants")
        )
        self.assertEqual(
            frozenset({"PGP"}), supported_versions_for_book_slug("abraham")
        )
        self.assertIn("NIV", supported_versions_for_book_slug("john"))

    def test_resolve_auto_version_uses_bom_for_exclusive_books(self):
        self.assertEqual("BOM", resolve_auto_version("NIV", "1 Nephi 3:7"))
        self.assertEqual("DC", resolve_auto_version("NIV", "D&C 1:1"))
        self.assertEqual("PGP", resolve_auto_version("NIV", "Abraham 3:22"))
        self.assertEqual(
            "NIV",
            resolve_auto_version("NIV", "1 Nephi 3:7", explicit_version=True),
        )
        self.assertEqual("NIV", resolve_auto_version("NIV", "John 3:16"))

    def test_resolve_auto_version_falls_back_to_nrsvue_for_missing_apocrypha(self):
        self.assertEqual("NRSVUE", resolve_auto_version("NIV", "1 Esdras 1:1"))
        self.assertEqual("NRSVUE", resolve_auto_version("KJV", "Wisdom 3:5"))
        self.assertEqual("NRSVUE", resolve_auto_version("NIV", "3 Maccabees 1:1"))
        self.assertEqual("NRSVUE", resolve_auto_version("NIV", "4 Maccabees 1:1"))
        self.assertEqual("NABRE", resolve_auto_version("NABRE", "Tobit 4:7"))
        self.assertEqual(
            "NIV",
            resolve_auto_version("NIV", "1 Esdras 1:1", explicit_version=True),
        )

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
        self.assertEqual(
            (True, "1 Nephi"), version_supports_passage("BOM", "1 Nephi 3:7")
        )
        self.assertEqual(
            (True, "Doctrine and Covenants"),
            version_supports_passage("DC", "Doctrine and Covenants 1:1"),
        )
        self.assertEqual((False, "John"), version_supports_passage("DC", "John 3:16"))
        self.assertEqual(
            (True, "Abraham"), version_supports_passage("PGP", "Abraham 3:22")
        )
        self.assertEqual((False, "John"), version_supports_passage("BOM", "John 3:16"))

    def test_decode_linked_reference_for_apocrypha(self):
        self.assertEqual(
            "1 Maccabees 2:1-5", decode_linked_reference("1maccabees2V1-5")
        )


if __name__ == "__main__":
    unittest.main()
