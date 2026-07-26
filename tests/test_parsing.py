import unittest

from parsing import (
    TELEGRAM_MESSAGE_LIMIT,
    batch_parallel_passage_entities,
    build_passage_from_ref,
    canonicalize_reference,
    decode_linked_reference,
    extract_leading_book_name,
    find_requested_book,
    format_inline_passage_entities,
    format_parallel_passage_entities,
    format_passage_chunks,
    format_passage_entities,
    get_book_scripture_system,
    get_passage_scripture_system,
    get_version_provider,
    is_book_only_request,
    normalize_book_name,
    normalize_reference_lookup_key,
    other_version,
    parse_get_request,
    parse_reference_version_query,
    parse_version_selection,
    resolve_auto_version,
    supported_book_slugs,
    supported_versions_for_book_slug,
    version_supports_book_slug,
    version_supports_passage,
)
from versions import VERSION_CATALOG, ScriptureSystemId, get_version_system


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
            header_url="https://biblegateway.com/passage/?search=John%203:16&version=NIV",
        )
        self.assertEqual("John 3:16 NIV\nFor God so loved the world.", text)
        self.assertEqual(3, len(entities))
        self.assertEqual("bold", entities[0].type)
        self.assertEqual("text_link", entities[1].type)
        self.assertEqual(
            "https://biblegateway.com/passage/?search=John%203:16&version=NIV",
            entities[1].url,
        )
        self.assertEqual("expandable_blockquote", entities[2].type)

    def test_format_passage_chunks_splits_long_messages(self):
        paragraph = "x" * 3000
        chunks = format_passage_chunks(
            f"1 Nephi 1 LDSENG\n\n{paragraph}\n\n{paragraph}"
        )
        self.assertEqual(2, len(chunks))
        self.assertTrue(chunks[0][0].startswith("1 Nephi 1 LDSENG\n"))
        self.assertTrue(chunks[1][0].startswith("1 Nephi 1 LDSENG\n"))
        self.assertEqual("expandable_blockquote", chunks[0][1][-1].type)
        self.assertEqual("expandable_blockquote", chunks[1][1][-1].type)
        self.assertLessEqual(len(chunks[0][0]), TELEGRAM_MESSAGE_LIMIT)
        self.assertLessEqual(len(chunks[1][0]), TELEGRAM_MESSAGE_LIMIT)

    def test_format_passage_chunks_uses_each_chunks_verse_range_in_header(self):
        first_paragraph = f"¹ {'x' * 2500}"
        second_paragraph = f"² {'x' * 2500}"
        chunks = format_passage_chunks(
            f"John 3:1–2 NIV\n\n{first_paragraph}\n\n{second_paragraph}"
        )
        self.assertEqual(2, len(chunks))
        self.assertTrue(chunks[0][0].startswith("John 3:1–2 NIV\nJohn 3:1 NIV\n"))
        self.assertTrue(chunks[1][0].startswith("John 3:2 NIV\n"))

    def test_format_passage_chunks_recalculates_quran_header_within_one_surah(self):
        paragraph = f"¹ {'x' * 2500}"
        chunks = format_passage_chunks(
            "Qurʾān, al-Baqarah (2):255–257 (Saheeh International)\n\n"
            f"{paragraph}\n\n{paragraph}"
        )
        self.assertEqual(2, len(chunks))
        self.assertTrue(
            chunks[0][0].startswith(
                "Qurʾān, al-Baqarah (2):255–257 (Saheeh International)\n"
                "Qurʾān, al-Baqarah (2):1 (Saheeh International)\n"
            )
        )
        self.assertTrue(
            chunks[1][0].startswith("Qurʾān, al-Baqarah (2):1 (Saheeh International)\n")
        )

    def test_format_passage_chunks_recalculates_quran_header_across_surahs(self):
        first_paragraph = f"al-Fātiḥah (1)\n\n² {'x' * 2500}"
        second_paragraph = f"Āl ʿImrān (3)\n\n¹ {'x' * 2500}"
        chunks = format_passage_chunks(
            "Qurʾān, al-Fātiḥah (1):2–Āl ʿImrān (3):2 (Saheeh International)\n\n"
            f"{first_paragraph}\n\n{second_paragraph}"
        )
        self.assertEqual(2, len(chunks))
        self.assertTrue(
            chunks[0][0].startswith(
                "Qurʾān, al-Fātiḥah (1):2–Āl ʿImrān (3):2 (Saheeh International)\n"
                "Qurʾān, al-Fātiḥah (1):2 (Saheeh International)\n"
            )
        )
        self.assertTrue(
            chunks[1][0].startswith("Qurʾān, Āl ʿImrān (3):1 (Saheeh International)\n")
        )

    def test_format_passage_chunks_treats_a_chapter_number_as_verse_one(self):
        first_paragraph = f"3 {'x' * 2500} ² {'x' * 10}"
        second_paragraph = f"4 {'x' * 2500}"
        chunks = format_passage_chunks(
            f"John 3:1-4:1 NIV\n\n{first_paragraph}\n\n{second_paragraph}"
        )
        self.assertEqual(2, len(chunks))
        self.assertTrue(chunks[0][0].startswith("John 3:1-4:1 NIV\nJohn 3:1–2 NIV\n"))
        self.assertTrue(chunks[1][0].startswith("John 4:1 NIV\n"))

    def test_format_passage_chunks_recalculates_cross_chapter_bible_ranges(self):
        first_paragraph = f"¹ {'x' * 2500} ³⁴ {'x' * 10}"
        second_paragraph = f"2 {'x' * 10}\n¹ {'x' * 10} ¹² {'x' * 2500}"
        third_paragraph = f"3 {'x' * 10}\n¹ {'x' * 10} ⁴ {'x' * 2500}"
        chunks = format_passage_chunks(
            "John 1:2-3:4 NRSVue\n\n"
            f"{first_paragraph}\n\n{second_paragraph}\n\n{third_paragraph}"
        )
        self.assertEqual(3, len(chunks))
        self.assertTrue(
            chunks[0][0].startswith("John 1:2-3:4 NRSVue\nJohn 1:1–34 NRSVue\n")
        )
        self.assertTrue(chunks[1][0].startswith("John 2:1–12 NRSVue\n"))
        self.assertTrue(chunks[2][0].startswith("John 3:1–4 NRSVue\n"))

    def test_format_parallel_passage_entities_combines_small_responses(self):
        combined = format_parallel_passage_entities(
            [
                ("John 3:16 NIV\n\nFor God so loved the world.", "https://niv"),
                ("John 3:16 NRSVue\n\nFor God so loved the world.", "https://nrsvue"),
                ("John 3:16 WLC\n\nFor God so loved the world.", "https://wlc"),
            ]
        )
        assert combined is not None
        text, entities = combined
        self.assertEqual(
            "John 3:16 NIV\nFor God so loved the world.\n"
            "John 3:16 NRSVue\nFor God so loved the world.\n"
            "John 3:16 WLC\nFor God so loved the world.",
            text,
        )
        self.assertEqual(9, len(entities))
        self.assertEqual("bold", entities[0].type)
        self.assertEqual("text_link", entities[1].type)
        self.assertEqual("expandable_blockquote", entities[2].type)
        self.assertEqual("bold", entities[3].type)
        self.assertEqual("text_link", entities[4].type)
        self.assertEqual("expandable_blockquote", entities[5].type)
        self.assertEqual("bold", entities[6].type)
        self.assertEqual("text_link", entities[7].type)
        self.assertEqual("expandable_blockquote", entities[8].type)

    def test_format_parallel_passage_entities_rejects_oversized_messages(self):
        text = f"John 3 NIV\n\n{'x' * 3000}"
        self.assertIsNone(
            format_parallel_passage_entities([(text, None), (text, None)])
        )

    def test_batch_parallel_passage_entities_packs_whole_passages_greedily(self):
        small = "John 3:16 NIV\n\nFor God so loved the world."
        large = f"John 3 NIV\n\n{'x' * 3000}"
        batches = batch_parallel_passage_entities(
            [
                (small, "https://niv"),
                (small.replace("NIV", "NRSVue"), "https://nrsvue"),
                (small.replace("NIV", "WLC"), "https://wlc"),
                (large.replace("NIV", "KJV"), None),
                (large.replace("NIV", "NASB"), None),
            ]
        )
        self.assertEqual(2, len(batches))
        self.assertIn("John 3:16 NIV", batches[0][0])
        self.assertIn("John 3:16 NRSVue", batches[0][0])
        self.assertIn("John 3:16 WLC", batches[0][0])
        self.assertIn("John 3 KJV", batches[0][0])
        self.assertIn("John 3 NASB", batches[1][0])

    def test_format_inline_passage_entities_truncates_long_messages(self):
        paragraph = "x" * 3000
        text, entities = format_inline_passage_entities(
            f"1 Nephi 1 LDSENG\n\n{paragraph}\n\n{paragraph}"
        )
        self.assertTrue(text.startswith("1 Nephi 1 LDSENG\n"))
        self.assertIn("…continued; use /get for the full passage.", text)
        self.assertLessEqual(len(text), TELEGRAM_MESSAGE_LIMIT)
        self.assertEqual(2, len(entities))
        self.assertEqual("bold", entities[0].type)
        self.assertEqual("expandable_blockquote", entities[1].type)

    def test_parse_get_uses_default_version(self):
        version, passage, explicit = parse_get_request("/get John 3:16", "NIV")
        self.assertEqual(
            ((("NIV",),), "John 3:16", False), (version, passage, explicit)
        )

    def test_parse_get_uses_trailing_version(self):
        version, passage, explicit = parse_get_request("/get 1 cor 13:4-7 NLT", "NIV")
        self.assertEqual(
            ((("NLT",),), "1 cor 13:4-7", True), (version, passage, explicit)
        )

    def test_parse_get_accepts_mixed_case_display_version_code(self):
        version, passage, explicit = parse_get_request("/get Genesis 1 NRSVue", "NIV")
        self.assertEqual(
            ((("NRSVUE",),), "Genesis 1", True), (version, passage, explicit)
        )

    def test_parse_get_accepts_bible_com_version_aliases(self):
        version, passage, explicit = parse_get_request("/get Tobit 4:7 GNADC", "NIV")
        self.assertEqual(
            ((("GNADC25",),), "Tobit 4:7", True), (version, passage, explicit)
        )
        version, passage, explicit = parse_get_request("/get Matthew 3 TMA-C", "NIV")
        self.assertEqual(
            ((("TMA-C",),), "Matthew 3", True), (version, passage, explicit)
        )

    def test_parse_get_prompts_for_passage_when_only_version_is_given(self):
        version, passage, explicit = parse_get_request("/get NASB", "NIV")
        self.assertEqual(((("NASB",),), None, True), (version, passage, explicit))

    def test_parse_get_rejects_old_command_suffix_format(self):
        version, passage, explicit = parse_get_request("/getabc John 3:16", "NIV")
        self.assertEqual((None, None, False), (version, passage, explicit))

    def test_parse_get_treats_non_version_tail_as_part_of_reference(self):
        version, passage, explicit = parse_get_request("/get John 3:16 earth", "NIV")
        self.assertEqual(
            ((("NIV",),), "John 3:16 earth", False), (version, passage, explicit)
        )

    def test_parse_get_rejects_non_get_commands(self):
        version, passage, explicit = parse_get_request("/search John 3:16", "NIV")
        self.assertEqual((None, None, False), (version, passage, explicit))

    def test_parse_reference_version_query_uses_default_version(self):
        version, passage, explicit = parse_reference_version_query("John 3:16", "NIV")
        self.assertEqual(
            ((("NIV",),), "John 3:16", False), (version, passage, explicit)
        )

    def test_parse_reference_version_query_uses_trailing_version(self):
        version, passage, explicit = parse_reference_version_query(
            "Genesis 1:1 NJPS", "NIV"
        )
        self.assertEqual(
            ((("NJPS",),), "Genesis 1:1", True), (version, passage, explicit)
        )

    def test_parse_reference_version_query_accepts_bible_com_aliases(self):
        version, passage, explicit = parse_reference_version_query(
            "Matthew 3 TKʿ", "NIV"
        )
        self.assertEqual(((("TKA",),), "Matthew 3", True), (version, passage, explicit))

    def test_parse_version_selection_supports_fallbacks_and_parallels(self):
        self.assertEqual(
            (("NIV", "NRSVUE"), ("GNADC25",)),
            parse_version_selection("NIV,NRSVue&GNADC"),
        )
        self.assertEqual(
            (("NIV", "NRSVUE"), ("TMA", "GNADC25")),
            parse_version_selection("NIV,NRSVue&TMA,GNADC"),
        )
        self.assertIsNone(parse_version_selection("NIV,&NRSVUE"))

    def test_parse_get_accepts_version_selection(self):
        selection, passage, explicit = parse_get_request(
            "/get 1 Maccabees 1 NIV,NRSVue&GNADC", "NIV"
        )
        self.assertEqual((("NIV", "NRSVUE"), ("GNADC25",)), selection)
        self.assertEqual("1 Maccabees 1", passage)
        self.assertTrue(explicit)

    def test_parse_get_accepts_quran_version(self):
        selection, passage, explicit = parse_get_request("/get Quran 2:255 QSI", "NIV")
        self.assertEqual((("QSI",),), selection)
        self.assertEqual("Quran 2:255", passage)
        self.assertTrue(explicit)

    def test_parse_get_accepts_named_quran_surah_forms(self):
        selection, passage, explicit = parse_get_request(
            "/get Al-Baqarah 255 QSI", "NIV"
        )
        self.assertEqual((("QSI",),), selection)
        self.assertEqual("Al-Baqarah 255", passage)
        self.assertTrue(explicit)

        selection, passage, explicit = parse_get_request(
            "/get Qur'an al-Baqarah 2:255 QSI", "NIV"
        )
        self.assertEqual((("QSI",),), selection)
        self.assertEqual("Qur'an al-Baqarah 2:255", passage)
        self.assertTrue(explicit)

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
            ("jubilees", "Jubilees"),
            find_requested_book("Jubilees 1:1"),
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
        self.assertEqual(("quran", "Qurʾan"), find_requested_book("Quran 2:255"))
        self.assertEqual(("quran", "Qurʾan"), find_requested_book("Qur'an 2:255"))

    def test_scripture_systems_keep_bible_lds_and_quran_separate(self):
        self.assertEqual(ScriptureSystemId.BIBLE, get_book_scripture_system("genesis"))
        self.assertEqual(ScriptureSystemId.BIBLE, get_book_scripture_system("1enoch"))
        self.assertEqual(ScriptureSystemId.LDS, get_book_scripture_system("1nephi"))
        self.assertEqual(ScriptureSystemId.QURAN, get_book_scripture_system("quran"))
        self.assertEqual(
            ScriptureSystemId.BIBLE, get_passage_scripture_system("Genesis 1:1")
        )
        self.assertEqual(
            ScriptureSystemId.LDS, get_passage_scripture_system("1 Nephi 1:1")
        )
        self.assertEqual(
            ScriptureSystemId.QURAN, get_passage_scripture_system("Quran 2:255")
        )
        self.assertEqual(
            ScriptureSystemId.QURAN, get_passage_scripture_system("Al-Baqarah 255")
        )
        self.assertEqual(
            ScriptureSystemId.QURAN,
            get_passage_scripture_system("Qur'an al-Baqarah 2:255"),
        )
        self.assertEqual(ScriptureSystemId.BIBLE, get_version_system("NIV"))
        self.assertEqual(ScriptureSystemId.LDS, get_version_system("LDSENG"))
        self.assertEqual(ScriptureSystemId.QURAN, get_version_system("QSI"))
        self.assertNotIn(
            "BOM",
            VERSION_CATALOG.systems_by_id[ScriptureSystemId.BIBLE].version_labels,
        )
        self.assertIn(
            "English LDS scriptures (LDSENG)",
            VERSION_CATALOG.systems_by_id[ScriptureSystemId.LDS].version_labels,
        )
        self.assertIn(
            "Saheeh International (QSI)",
            VERSION_CATALOG.systems_by_id[ScriptureSystemId.QURAN].version_labels,
        )

    def test_is_book_only_request(self):
        self.assertTrue(is_book_only_request("John"))
        self.assertTrue(is_book_only_request("1 Maccabees"))
        self.assertTrue(is_book_only_request("Jubilees"))
        self.assertTrue(is_book_only_request("Quran"))
        self.assertFalse(is_book_only_request("John 3"))
        self.assertFalse(is_book_only_request("John 3:16"))
        self.assertFalse(is_book_only_request("1 Maccabees 1"))

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
        self.assertEqual("sefaria", get_version_provider("KOREN"))
        self.assertEqual("sefaria", get_version_provider("CTJPS"))
        self.assertEqual("sefaria", get_version_provider("FOX"))
        self.assertEqual("sefaria", get_version_provider("SCOMM"))
        self.assertEqual("sefaria", get_version_provider("BRENTON"))
        self.assertEqual("sefaria", get_version_provider("FERRARA"))
        self.assertEqual("sefaria", get_version_provider("BOYADJIAN1873"))
        self.assertEqual("sefaria", get_version_provider("NEUHAUSEN1914"))
        self.assertEqual("sefaria", get_version_provider("CHARLES"))
        self.assertEqual("sefaria", get_version_provider("FEUER"))
        self.assertEqual("sefaria", get_version_provider("NEUBAUER"))
        self.assertEqual("sefaria", get_version_provider("ARISTEAS"))
        self.assertEqual("sefaria", get_version_provider("OPENSID"))
        self.assertEqual("sefaria", get_version_provider("ESHEL"))
        self.assertEqual("sefaria", get_version_provider("METSUDAH"))
        self.assertEqual("sefaria", get_version_provider("RJPS"))
        self.assertEqual("sefaria", get_version_provider("YEHOYESH"))
        self.assertEqual("biblecom", get_version_provider("GNA2025"))
        self.assertEqual("biblecom", get_version_provider("GNADC25"))
        self.assertEqual("biblecom", get_version_provider("TMA"))
        self.assertEqual("biblecom", get_version_provider("TMA-C"))
        self.assertEqual("biblecom", get_version_provider("TKA"))
        self.assertEqual("lds", get_version_provider("LDSENG"))
        self.assertEqual("lds", get_version_provider("LDSESP"))
        self.assertIsNone(get_version_provider("BOM"))
        self.assertIsNone(get_version_provider("DC"))
        self.assertIsNone(get_version_provider("PGP"))
        self.assertEqual("quran", get_version_provider("QURAN"))
        self.assertEqual("quran", get_version_provider("QSI"))

    def test_supported_book_slugs_capture_scope_overrides(self):
        self.assertIn("genesis", supported_book_slugs("NIV"))
        self.assertNotIn("genesis", supported_book_slugs("DLNT"))
        self.assertIn("john", supported_book_slugs("DLNT"))
        self.assertIn("genesis", supported_book_slugs("WLC"))
        self.assertNotIn("matthew", supported_book_slugs("WLC"))
        self.assertIn("genesis", supported_book_slugs("JPS"))
        self.assertNotIn("matthew", supported_book_slugs("JPS"))
        self.assertIn("genesis", supported_book_slugs("NJPS"))
        self.assertIn("john", supported_book_slugs("TMA"))
        self.assertNotIn("tobit", supported_book_slugs("TMA"))
        self.assertIn("tobit", supported_book_slugs("GNA2025"))
        self.assertIn("tobit", supported_book_slugs("GNADC25"))
        self.assertIn("tobit", supported_book_slugs("TKA"))
        self.assertNotIn("matthew", supported_book_slugs("NJPS"))
        self.assertIn("genesis", supported_book_slugs("KOREN"))
        self.assertNotIn("matthew", supported_book_slugs("KOREN"))
        self.assertIn("genesis", supported_book_slugs("CTJPS"))
        self.assertNotIn("joshua", supported_book_slugs("CTJPS"))
        self.assertIn("genesis", supported_book_slugs("FOX"))
        self.assertNotIn("psalm", supported_book_slugs("FOX"))
        self.assertIn("1maccabees", supported_book_slugs("SCOMM"))
        self.assertIn("2maccabees", supported_book_slugs("SCOMM"))
        self.assertIn("jubilees", supported_book_slugs("SCOMM"))
        self.assertIn("sirach", supported_book_slugs("SCOMM"))
        self.assertIn("1maccabees", supported_book_slugs("BRENTON"))
        self.assertNotIn("2maccabees", supported_book_slugs("BRENTON"))
        self.assertIn("jubilees", supported_book_slugs("CHARLES"))
        self.assertIn(
            "testamentsofthetwelvepatriarchs", supported_book_slugs("CHARLES")
        )
        self.assertIn("megillatantiochus", supported_book_slugs("FEUER"))
        self.assertIn("tobit", supported_book_slugs("NEUBAUER"))
        self.assertIn("letterofaristeas", supported_book_slugs("ARISTEAS"))
        self.assertIn("megillatantiochus", supported_book_slugs("OPENSID"))
        self.assertIn("psalm154", supported_book_slugs("ESHEL"))
        self.assertIn("genesis", supported_book_slugs("METSUDAH"))
        self.assertNotIn("isaiah", supported_book_slugs("METSUDAH"))
        self.assertIn("genesis", supported_book_slugs("RJPS"))
        self.assertNotIn("matthew", supported_book_slugs("RJPS"))
        self.assertIn("1nephi", supported_book_slugs("LDSENG"))
        self.assertIn("doctrineandcovenants", supported_book_slugs("LDSENG"))
        self.assertIn("abraham", supported_book_slugs("LDSENG"))
        self.assertEqual(frozenset(), supported_book_slugs("BOM"))
        self.assertEqual(frozenset(), supported_book_slugs("DC"))
        self.assertEqual(frozenset(), supported_book_slugs("PGP"))
        self.assertIn("quran", supported_book_slugs("QURAN"))
        self.assertNotIn("john", supported_book_slugs("QURAN"))
        self.assertIn("3maccabees", supported_book_slugs("NRSVUE"))
        self.assertIn("4maccabees", supported_book_slugs("NRSVUE"))
        self.assertIn("3maccabees", supported_book_slugs("NRSVA"))
        self.assertIn("4maccabees", supported_book_slugs("RSV"))

    def test_version_supports_book_slug(self):
        self.assertTrue(version_supports_book_slug("NRSVUE", "1esdras"))
        self.assertTrue(version_supports_book_slug("NABRE", "tobit"))
        self.assertFalse(version_supports_book_slug("NABRE", "1esdras"))

    def test_supported_versions_for_book_slug(self):
        self.assertEqual(
            frozenset({"LDSENG", "LDSESP", "LDSPOR", "LDSFRA", "LDSDEU"}),
            supported_versions_for_book_slug("1nephi"),
        )
        self.assertEqual(
            frozenset({"LDSENG", "LDSESP", "LDSPOR", "LDSFRA", "LDSDEU"}),
            supported_versions_for_book_slug("doctrineandcovenants"),
        )
        self.assertEqual(
            frozenset({"LDSENG", "LDSESP", "LDSPOR", "LDSFRA", "LDSDEU"}),
            supported_versions_for_book_slug("abraham"),
        )
        self.assertEqual(
            frozenset({"SCOMM", "CHARLES"}),
            supported_versions_for_book_slug("jubilees"),
        )
        self.assertEqual(
            True,
            {"BRENTON", "SCOMM", "FEUER"}.issubset(
                supported_versions_for_book_slug("1maccabees")
            ),
        )
        self.assertEqual(
            True, {"SCOMM"}.issubset(supported_versions_for_book_slug("2maccabees"))
        )
        self.assertEqual(
            frozenset({"ARISTEAS"}),
            supported_versions_for_book_slug("letterofaristeas"),
        )
        self.assertEqual(
            True,
            {"OPENSID", "FEUER"}.issubset(
                supported_versions_for_book_slug("megillatantiochus")
            ),
        )
        self.assertEqual(
            frozenset({"ESHEL"}), supported_versions_for_book_slug("psalm154")
        )
        self.assertEqual(
            frozenset({"CHARLES"}),
            supported_versions_for_book_slug("testamentsofthetwelvepatriarchs"),
        )
        self.assertIn("NIV", supported_versions_for_book_slug("john"))
        self.assertEqual(
            frozenset(
                {
                    "UTHMANI",
                    "QSI",
                    "QPICK",
                    "QYUSUF",
                    "QAYATI",
                    "QFOOL",
                    "QSODIK",
                    "QJAL",
                    "QDIYANET",
                    "QKULIEV",
                }
            ),
            supported_versions_for_book_slug("quran"),
        )

    def test_resolve_auto_version_uses_lds_default_for_exclusive_books(self):
        self.assertEqual("LDSENG", resolve_auto_version("NIV", "1 Nephi 3:7"))
        self.assertEqual("LDSENG", resolve_auto_version("NIV", "D&C 1:1"))
        self.assertEqual("LDSENG", resolve_auto_version("NIV", "Abraham 3:22"))
        self.assertEqual("CHARLES", resolve_auto_version("NIV", "Jubilees 1:1"))
        self.assertEqual(
            "ARISTEAS", resolve_auto_version("NIV", "Letter of Aristeas 1:1")
        )
        self.assertEqual(
            "OPENSID", resolve_auto_version("NIV", "Megillat Antiochus 1:1")
        )
        self.assertEqual(
            "CHARLES",
            resolve_auto_version("NIV", "Testaments of the Twelve Patriarchs 1:1"),
        )
        self.assertEqual(
            "NIV",
            resolve_auto_version("NIV", "1 Nephi 3:7", explicit_version=True),
        )
        self.assertEqual("NIV", resolve_auto_version("NIV", "John 3:16"))

    def test_resolve_auto_version_prefers_nrsvue_before_sefaria_for_apocrypha(self):
        self.assertEqual("NRSVUE", resolve_auto_version("NIV", "1 Maccabees 1:1"))
        self.assertEqual("NRSVUE", resolve_auto_version("NIV", "2 Maccabees 1:1"))
        self.assertEqual("NRSVUE", resolve_auto_version("NIV", "Wisdom 3:5"))

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
            (True, "1 Nephi"), version_supports_passage("LDSENG", "1 Nephi 3:7")
        )
        self.assertEqual(
            (True, "Doctrine and Covenants"),
            version_supports_passage("LDSENG", "Doctrine and Covenants 1:1"),
        )
        self.assertEqual(
            (False, "John"), version_supports_passage("LDSENG", "John 3:16")
        )
        self.assertEqual(
            (True, "Abraham"), version_supports_passage("LDSENG", "Abraham 3:22")
        )
        self.assertEqual(
            (True, "1 Nephi"), version_supports_passage("LDSENG", "1 Nephi 3:7")
        )
        self.assertEqual(
            (True, "Jubilees"),
            version_supports_passage("SCOMM", "Jubilees 1:1"),
        )
        self.assertEqual(
            (True, "Jubilees"),
            version_supports_passage("CHARLES", "Jubilees 1:1"),
        )
        self.assertEqual(
            (False, "Genesis"), version_supports_passage("SCOMM", "Genesis 1:1")
        )
        self.assertEqual(
            (False, "Genesis"),
            version_supports_passage("CHARLES", "Genesis 1:1"),
        )
        self.assertEqual(
            (True, "1 Maccabees"),
            version_supports_passage("BRENTON", "1 Maccabees 1:1"),
        )
        self.assertEqual(
            (False, "2 Maccabees"),
            version_supports_passage("BRENTON", "2 Maccabees 1:1"),
        )
        self.assertEqual(
            (True, "2 Maccabees"),
            version_supports_passage("SCOMM", "2 Maccabees 1:1"),
        )
        self.assertEqual(
            (True, "Letter of Aristeas"),
            version_supports_passage("ARISTEAS", "Letter of Aristeas 1:1"),
        )
        self.assertEqual(
            (True, "Megillat Antiochus"),
            version_supports_passage("OPENSID", "Megillat Antiochus 1:1"),
        )
        self.assertEqual(
            (True, "Psalm 154"), version_supports_passage("ESHEL", "Psalm 154 1:1")
        )
        self.assertEqual(
            (False, "John"), version_supports_passage("LDSENG", "John 3:16")
        )
        self.assertEqual(
            (True, "Qurʾān"), version_supports_passage("QSI", "Quran 2:255")
        )
        self.assertEqual(
            (False, "Genesis"), version_supports_passage("QSI", "Genesis 1:1")
        )

    def test_decode_linked_reference_for_apocrypha(self):
        self.assertEqual(
            "1 Maccabees 2:1-5", decode_linked_reference("1maccabees2V1-5")
        )


if __name__ == "__main__":
    unittest.main()
