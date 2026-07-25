import unittest

from services.lds_scriptures import (
    LDS_BOOK_BY_ALIAS,
    LdsReference,
    build_lds_passage_url,
    format_reference_title,
    parse_lds_reference,
    parse_passage_html,
)
from state import EMPTY, InlinePassageResult

SAMPLE_HTML = """
<html>
  <body>
    <header>
      <p class="chapter">Chapter 3</p>
      <p class="study-summary" id="study_summary1">
        Nephi retrieves the plates.
      </p>
    </header>
    <div class="body-block">
      <p class="verse" id="p6">
        <span class="verse-number">6 </span>
        Therefore I will go and do the things which the Lord hath commanded.
      </p>
      <p class="verse" id="p7">
        <span class="verse-number">7 </span>
        For I know that the Lord giveth no commandments unto the children of men,
        save he shall prepare a way for them.
      </p>
      <p class="verse" id="p8">
        <span class="iconPointer-OKie_" data-pointer-type="media"></span>
        <span class="verse-number">8 </span>
        And it came to pass that I said unto my father:
        <a class="study-note-ref" href="#note8_a"><sup class="marker">a</sup>more</a>
      </p>
    </div>
  </body>
</html>
"""


class LdsScripturesParsingTests(unittest.TestCase):
    def test_build_lds_passage_url_uses_public_host(self):
        self.assertEqual(
            "https://churchofjesuschrist.org/study/scriptures/bofm/1-ne/3"
            "?lang=eng&id=p7#p7",
            build_lds_passage_url("1 Nephi 3:7"),
        )

    def test_parse_reference_single_verse(self):
        reference = parse_lds_reference("1 Nephi 3:7")
        self.assertIsNotNone(reference)
        assert reference is not None
        self.assertEqual("1 Nephi", reference.book.title)
        self.assertEqual(
            (3, 7, 3, 7),
            (
                reference.start_chapter,
                reference.start_verse,
                reference.end_chapter,
                reference.end_verse,
            ),
        )

    def test_parse_reference_chapter_range(self):
        reference = parse_lds_reference("Alma 5-6")
        self.assertIsNotNone(reference)
        assert reference is not None
        self.assertEqual(
            (5, None, 6, None),
            (
                reference.start_chapter,
                reference.start_verse,
                reference.end_chapter,
                reference.end_verse,
            ),
        )

    def test_parse_reference_cross_chapter_range(self):
        reference = parse_lds_reference("3 Nephi 11:3-12:2")
        self.assertIsNotNone(reference)
        assert reference is not None
        self.assertEqual(
            (11, 3, 12, 2),
            (
                reference.start_chapter,
                reference.start_verse,
                reference.end_chapter,
                reference.end_verse,
            ),
        )

    def test_parse_reference_accepts_doctrine_and_covenants(self):
        reference = parse_lds_reference("Doctrine and Covenants 1:1-2")
        self.assertIsNotNone(reference)
        assert reference is not None
        self.assertEqual("Doctrine and Covenants", reference.book.title)
        self.assertEqual("DC", reference.book.version)

    def test_parse_reference_accepts_pearl_of_great_price_books(self):
        reference = parse_lds_reference("Joseph Smith-History 1:15-17")
        self.assertIsNotNone(reference)
        assert reference is not None
        self.assertEqual("Joseph Smith—History", reference.book.title)
        self.assertEqual("PGP", reference.book.version)

    def test_parse_reference_rejects_unknown_book(self):
        self.assertIsNone(parse_lds_reference("Heliocentrics 1:1"))

    def test_format_reference_title(self):
        book = LDS_BOOK_BY_ALIAS["1nephi"]
        self.assertEqual(
            "1 Nephi 3:7-8",
            format_reference_title(LdsReference(book, 3, 7, 3, 8)),
        )

    def test_parse_passage_html_filters_requested_verses(self):
        reference = LdsReference(LDS_BOOK_BY_ALIAS["1nephi"], 3, 7, 3, 8)
        result = parse_passage_html(SAMPLE_HTML, reference)
        self.assertIsInstance(result, str)
        assert isinstance(result, str)
        self.assertIn("1 Nephi 3:7-8 BOM", result)
        self.assertNotIn("6 Therefore", result)
        self.assertIn("⁷ For I know", result)
        self.assertIn("⁸ And it came to pass", result)
        self.assertNotIn("more", result)

    def test_parse_passage_html_inline(self):
        reference = LdsReference(LDS_BOOK_BY_ALIAS["1nephi"], 3, 7, 3, 7)
        result = parse_passage_html(SAMPLE_HTML, reference, inline_details=True)
        self.assertIsInstance(result, InlinePassageResult)
        assert isinstance(result, InlinePassageResult)
        self.assertEqual("1 Nephi 3:7 BOM", result.title)
        self.assertIn("⁷ For I know", result.passage)

    def test_parse_passage_html_returns_empty_when_no_match(self):
        reference = LdsReference(LDS_BOOK_BY_ALIAS["1nephi"], 3, 20, 3, 21)
        self.assertEqual(EMPTY, parse_passage_html(SAMPLE_HTML, reference))


if __name__ == "__main__":
    unittest.main()
