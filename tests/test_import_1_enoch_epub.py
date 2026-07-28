import unittest

from tools.import_1_enoch_epub import (
    build_chapters,
    extract_text_from_html,
    source_url_for_chapter,
)


class Import1EnochEpubTests(unittest.TestCase):
    def test_extract_verses_splits_inline_slash_verse_markers(self):
        html = """
        <html><body>
        <p class="indent">
        5:1 Synthetic opening sentence for verse one.
        </p>
        <p class="indent">
        Synthetic continuation of verse one. 2/ Synthetic text for verse two.
        </p>
        <p class="indent">
        3 Synthetic text for verse three.
        </p>
        </body></html>
        """

        verses = extract_text_from_html(html).verses

        self.assertEqual(
            {
                5: {
                    1: (
                        "Synthetic opening sentence for verse one. "
                        "Synthetic continuation of verse one."
                    ),
                    2: "Synthetic text for verse two.",
                    3: "Synthetic text for verse three.",
                }
            },
            verses,
        )

    def test_extract_verses_splits_multiple_inline_markers_in_one_paragraph(self):
        html = """
        <html><body>
        <p class="indent">
        7:3 Synthetic text for verse three. 4/ Synthetic text for verse four.
        5/ Synthetic text for verse five.
        </p>
        </body></html>
        """

        verses = extract_text_from_html(html).verses

        self.assertEqual(
            {
                7: {
                    3: "Synthetic text for verse three.",
                    4: "Synthetic text for verse four.",
                    5: "Synthetic text for verse five.",
                }
            },
            verses,
        )

    def test_extract_verses_splits_inline_chapter_transition_markers(self):
        html = """
        <html><body>
        <p class="indent">
        23:4 Synthetic text in chapter twenty-three.
        24:1/ Synthetic text in chapter twenty-four.
        </p>
        </body></html>
        """

        verses = extract_text_from_html(html).verses

        self.assertEqual(
            {
                23: {4: "Synthetic text in chapter twenty-three."},
                24: {1: "Synthetic text in chapter twenty-four."},
            },
            verses,
        )

    def test_extract_text_ignores_chapter_91_omission_marker(self):
        html = """
        <html><body>
        <p class="indent">91:10 Synthetic text for verse ten,</p>
        <p class="indent">with a second line in the same verse.</p>
        <p class="indent">11–17 . . . . . . . . . . . . . . .</p>
        <p class="indent">18 Synthetic text for verse eighteen,</p>
        <p class="indent">with another line in the same verse.</p>
        </body></html>
        """

        verses = extract_text_from_html(html).verses

        self.assertEqual(
            {
                91: {
                    10: (
                        "Synthetic text for verse ten, "
                        "with a second line in the same verse."
                    ),
                    18: (
                        "Synthetic text for verse eighteen, "
                        "with another line in the same verse."
                    ),
                }
            },
            verses,
        )

    def test_extract_text_attaches_ordered_headings_to_the_next_verse(self):
        html = """
        <html><body>
        <h2 class="chapter-title">Primary Section</h2>
        <h2><em>First Subsection</em></h2>
        <p class="nonindent">1:1 Synthetic text for verse one.</p>
        <h2><em>Second Subsection</em></h2>
        <p class="nonindent">2 Synthetic text for verse two.</p>
        </body></html>
        """

        extracted = extract_text_from_html(html)

        self.assertEqual(
            {
                1: {
                    1: ["Primary Section", "First Subsection"],
                    2: ["Second Subsection"],
                }
            },
            extracted.headers,
        )

    def test_build_chapters_reserves_zero_positions(self):
        chapters = build_chapters(
            {1: {1: "Synthetic text for verse one."}},
            {1: {1: ["Primary Heading"]}},
        )

        self.assertEqual(
            [
                None,
                {
                    "headers": {"1": ["Primary Heading"]},
                    "source_url": "https://doi.org/10.2307/j.ctt22nm5vn.6",
                    "verses": [None, "Synthetic text for verse one."],
                },
            ],
            chapters,
        )

    def test_chapter_source_urls_cover_each_enoch_section(self):
        expected_urls = {
            1: "https://doi.org/10.2307/j.ctt22nm5vn.6",
            36: "https://doi.org/10.2307/j.ctt22nm5vn.6",
            37: "https://doi.org/10.2307/j.ctt22nm5vn.7",
            71: "https://doi.org/10.2307/j.ctt22nm5vn.7",
            72: "https://doi.org/10.2307/j.ctt22nm5vn.8",
            82: "https://doi.org/10.2307/j.ctt22nm5vn.8",
            83: "https://doi.org/10.2307/j.ctt22nm5vn.9",
            90: "https://doi.org/10.2307/j.ctt22nm5vn.9",
            91: "https://doi.org/10.2307/j.ctt22nm5vn.10",
            92: "https://doi.org/10.2307/j.ctt22nm5vn.11",
            105: "https://doi.org/10.2307/j.ctt22nm5vn.11",
            106: "https://doi.org/10.2307/j.ctt22nm5vn.12",
            107: "https://doi.org/10.2307/j.ctt22nm5vn.12",
            108: "https://doi.org/10.2307/j.ctt22nm5vn.13",
        }

        for chapter, expected_url in expected_urls.items():
            with self.subTest(chapter=chapter):
                self.assertEqual(expected_url, source_url_for_chapter(chapter))


if __name__ == "__main__":
    unittest.main()
