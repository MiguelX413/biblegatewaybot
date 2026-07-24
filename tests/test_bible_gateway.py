import unittest

from services.bible_gateway import parse_passage_html, parse_search_results_html
from state import EMPTY, InlinePassageResult

PASSAGE_HTML = """
<html>
  <body>
    <div class="passage-col">
      <span class="bcv">John 3:16</span>
      <div class="passage-text">
        <h3>For God So Loved the World</h3>
        <p><span class="chapternum">3</span><span class="versenum">16</span><span class="text">For God so loved the world</span><br/><span class="text">that he gave his one and only Son.</span></p>
        <div class="footnote">remove me</div>
      </div>
    </div>
    <!-- passage-box -->
    <div data-osis="John.3.16"></div>
  </body>
</html>
"""

SEARCH_HTML = """
<html>
  <body>
    <div class="l">John 3:16 Something</div>
    <div class="s">For God so loved the world //biblehub.com</div>
    <div class="l">Romans 8:28 Something</div>
    <div class="s">All things work together //biblehub.com</div>
  </body>
</html>
"""


class BibleGatewayParsingTests(unittest.TestCase):
    def test_parse_passage_html(self):
        result = parse_passage_html(PASSAGE_HTML, version="NIV")
        self.assertIsInstance(result, str)
        self.assertIn("John 3:16 (NIV)", result)
        self.assertIn("For God so loved the world", result)
        self.assertNotIn("remove me", result)

    def test_parse_passage_html_inline(self):
        result = parse_passage_html(PASSAGE_HTML, version="NIV", inline_details=True)
        self.assertIsInstance(result, InlinePassageResult)
        self.assertEqual("John.3.16/NIV", result.result_id)
        self.assertIn("John 3:16 (NIV)", result.passage)

    def test_parse_passage_html_missing_passage(self):
        self.assertEqual(EMPTY, parse_passage_html("<html></html>", version="NIV"))

    def test_parse_search_results_html(self):
        result = parse_search_results_html(SEARCH_HTML)
        self.assertIn("Search results", result)
        self.assertIn("🔹John 3:16", result)
        self.assertIn("/john3V16", result)
        self.assertNotIn("//biblehub.com", result)


if __name__ == "__main__":
    unittest.main()
