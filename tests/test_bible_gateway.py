import unittest

from services.bible_gateway import (
    build_bible_gateway_passage_url,
    normalize_block_text,
    parse_passage_html,
    parse_search_results_html,
)
from state import EMPTY, InlinePassageResult

PASSAGE_HTML = """
<html>
  <body>
    <div class="passage-col">
      <span class="bcv">John 3:16</span>
      <div class="passage-text">
        <h3>Synthetic Section Heading</h3>
        <p>
          <span class="chapternum">3</span><span class="versenum">16</span>
          <span class="text">Synthetic passage opening</span>
          <br/><span class="text">and synthetic continuation.</span>
        </p>
        <div class="footnote">remove me</div>
      </div>
    </div>
    <!-- passage-box -->
    <div data-osis="John.3.16"></div>
  </body>
</html>
"""

POETRY_HTML = """
<html>
  <body>
    <div class="passage-col">
      <span class="bcv">Psalm 23:1-2</span>
      <div class="passage-text">
        <p>
          <span class="chapternum">23</span><span class="versenum">1</span>
          <span class="text">Synthetic poetic opening;</span>
          <br/><span class="text">synthetic poetic continuation.</span>
        </p>
        <p>
          <span class="versenum">2</span>
          <span class="text">Second synthetic poetic opening:</span>
          <br/><span class="text">second synthetic poetic continuation.</span>
        </p>
      </div>
    </div>
  </body>
</html>
"""

SEARCH_HTML = """
<html>
  <body>
    <div class="l">John 3:16 Something</div>
    <div class="s">Synthetic search snippet //biblehub.com</div>
    <div class="l">Romans 8:28 Something</div>
    <div class="s">Second synthetic search snippet //biblehub.com</div>
  </body>
</html>
"""


class BibleGatewayParsingTests(unittest.TestCase):
    def test_build_bible_gateway_passage_url_uses_public_host(self):
        self.assertEqual(
            "https://biblegateway.com/passage/?search=John%203:16&version=NIV",
            build_bible_gateway_passage_url("John 3:16", "NIV"),
        )

    def test_normalize_block_text_preserves_intentional_line_breaks(self):
        self.assertEqual(
            "Line one\nLine two",
            normalize_block_text(" Line   one \n\n  Line   two "),
        )

    def test_parse_passage_html(self):
        result = parse_passage_html(PASSAGE_HTML, version="NIV")
        self.assertIsInstance(result, str)
        assert isinstance(result, str)
        self.assertIn("John 3:16 NIV", result)
        self.assertIn("Synthetic passage opening", result)
        self.assertNotIn("remove me", result)

    def test_parse_passage_html_preserves_poetry_line_breaks(self):
        result = parse_passage_html(POETRY_HTML, version="KJV")
        self.assertIsInstance(result, str)
        assert isinstance(result, str)
        self.assertIn("Psalm 23:1–2 KJV", result)
        self.assertIn(
            "Synthetic poetic opening;\nsynthetic poetic continuation.", result
        )
        self.assertIn(
            "Second synthetic poetic opening:\nsecond synthetic poetic continuation.",
            result,
        )

    def test_parse_passage_html_inline(self):
        result = parse_passage_html(PASSAGE_HTML, version="NIV", inline_details=True)
        self.assertIsInstance(result, InlinePassageResult)
        assert isinstance(result, InlinePassageResult)
        self.assertEqual("John.3.16/NIV", result.result_id)
        self.assertIn("John 3:16 NIV", result.passage)

    def test_parse_passage_html_missing_passage(self):
        self.assertEqual(EMPTY, parse_passage_html("<html></html>", version="NIV"))

    def test_parse_passage_html_without_passage_box_marker(self):
        result = parse_passage_html(POETRY_HTML, version="KJV")
        assert isinstance(result, str)
        self.assertIn("Psalm 23:1–2 KJV", result)

    def test_parse_search_results_html(self):
        result = parse_search_results_html(SEARCH_HTML)
        self.assertIn("Search results", result)
        self.assertIn("🔹John 3:16", result)
        self.assertIn("/john3V16", result)
        self.assertNotIn("//biblehub.com", result)


if __name__ == "__main__":
    unittest.main()
