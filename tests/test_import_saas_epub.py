import unittest

from tools.import_saas_epub import (
    ExtractedBook,
    build_chapters,
    extract_book_from_html,
)


class ImportSaasEpubTests(unittest.TestCase):
    def test_extracts_prose_verses_from_inline_markers(self):
        html = """
        <html><body>
        <p class="sub1">Synthetic Section</p>
        <p class="chapter1">
          <span class="chbeg" id="Gen_vchap1-1">1</span>
          Synthetic first verse.
          <sup id="Gen_vchap1-2">2</sup>Synthetic second verse.
          <sup><a href="study.html#f1">†</a></sup>
        </p>
        <p class="rindent">
          <sup id="Gen_vchap1-3">3</sup>Synthetic third verse.
        </p>
        <p class="tx">Synthetic study note should not be imported.</p>
        </body></html>
        """

        extracted = extract_book_from_html((html,))

        self.assertEqual(
            {
                1: {
                    1: "Synthetic first verse.",
                    2: "Synthetic second verse.",
                    3: "Synthetic third verse.",
                }
            },
            extracted.verses,
        )
        self.assertEqual({1: {1: ["Synthetic Section"]}}, extracted.headers)

    def test_extracts_poetry_from_ol_verse_id_and_continuation_lines(self):
        html = """
        <html><body>
        <p class="psalm">Psalm 1</p>
        <ol class="olstyle" id="Ps_vchap1-1">
          <li><span class="chbeg">S</span>ample synthetic line,</li>
          <li>Synthetic continuation line.</li>
          <li><sup id="Ps_vchap1-2">2</sup>Synthetic second verse.</li>
        </ol>
        <p class="psalm">Psalm 2</p>
        <ol class="olstyle" id="Ps_vchap2-1">
          <li><span class="chbeg">W</span>hy synthetic opening?</li>
        </ol>
        </body></html>
        """

        extracted = extract_book_from_html((html,))

        self.assertEqual(
            {
                1: {
                    1: "Sample synthetic line, Synthetic continuation line.",
                    2: "Synthetic second verse.",
                },
                2: {1: "Why synthetic opening?"},
            },
            extracted.verses,
        )

    def test_builds_positional_chapter_arrays(self):
        chapters = build_chapters(
            ExtractedBook(
                verses={1: {1: "Synthetic verse."}},
                headers={1: {1: ["Synthetic heading"]}},
            )
        )

        self.assertEqual(
            [
                None,
                {
                    "headers": {"1": ["Synthetic heading"]},
                    "verses": [None, "Synthetic verse."],
                },
            ],
            chapters,
        )


if __name__ == "__main__":
    unittest.main()
