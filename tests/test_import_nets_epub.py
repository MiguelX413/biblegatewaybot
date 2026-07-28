import unittest

from tools.import_nets_epub import (
    ExtractedWork,
    WorkSpec,
    build_chapters,
    extract_work_from_html,
)


class ImportNetsEpubTests(unittest.TestCase):
    def test_extracts_chapters_and_inline_verse_markers(self):
        html = """
        <html><body>
        <p class="noindent"><strong>1</strong> Synthetic verse one.
        <sup>2</sup> Synthetic verse two.</p>
        <p class="indent">3 Synthetic verse three.</p>
        <p class="noindent"><strong>2</strong> Synthetic next chapter.</p>
        </body></html>
        """
        spec = WorkSpec("Sample", "sample", ("sample",), ("sample.html",))

        extracted = extract_work_from_html((html,), spec)

        self.assertEqual(
            {
                1: {
                    1: "Synthetic verse one.",
                    2: "Synthetic verse two.",
                    3: "Synthetic verse three.",
                },
                2: {1: "Synthetic next chapter."},
            },
            extracted.verses,
        )

    def test_detects_plain_number_chapter_transition(self):
        html = """
        <html><body>
        <p><strong>1</strong> Synthetic verse one.</p>
        <p>2 Synthetic verse two.</p>
        <p>3 Synthetic verse three.</p>
        <p>2 Synthetic next chapter.</p>
        </body></html>
        """
        spec = WorkSpec("Sample", "sample", ("sample",), ("sample.html",))

        extracted = extract_work_from_html((html,), spec)

        self.assertEqual(
            {
                1: {
                    1: "Synthetic verse one.",
                    2: "Synthetic verse two.",
                    3: "Synthetic verse three.",
                },
                2: {1: "Synthetic next chapter."},
            },
            extracted.verses,
        )

    def test_extracts_single_chapter_work(self):
        html = """
        <html><body>
        <h2>Sample Work</h2>
        <p><sup>1</sup> Synthetic verse one.</p>
        <p><sup>2</sup> Synthetic verse two.</p>
        </body></html>
        """
        spec = WorkSpec(
            "Sample", "sample", ("sample",), ("sample.html",), single_chapter=True
        )

        extracted = extract_work_from_html((html,), spec)

        self.assertEqual(
            {1: {1: "Synthetic verse one.", 2: "Synthetic verse two."}},
            extracted.verses,
        )

    def test_extracts_psalm_headings_as_chapters(self):
        html = """
        <html><body>
        <p class="center"><strong>Psalm 1(1)</strong></p>
        <p><sup>1</sup> Synthetic first psalm.</p>
        <p class="center"><strong>Psalm 2(2)</strong></p>
        <p><sup>1</sup> Synthetic second psalm.</p>
        </body></html>
        """
        spec = WorkSpec(
            "Psalms",
            "psalm",
            ("psalm",),
            ("sample.html",),
            psalm_headings=True,
        )

        extracted = extract_work_from_html((html,), spec)

        self.assertEqual(
            {1: {1: "Synthetic first psalm."}, 2: {1: "Synthetic second psalm."}},
            extracted.verses,
        )

    def test_extracts_combined_psalms_heading(self):
        html = """
        <html><body>
        <p class="center"><strong>psalms 39(40)–40(41)</strong></p>
        <p><sup>1</sup> Synthetic psalm text.</p>
        <p class="center"><strong>Psalm 40(41)</strong></p>
        <p><sup>1</sup> Synthetic next psalm.</p>
        </body></html>
        """
        spec = WorkSpec(
            "Psalms",
            "psalm",
            ("psalm",),
            ("sample.html",),
            psalm_headings=True,
        )

        extracted = extract_work_from_html((html,), spec)

        self.assertEqual(
            {39: {1: "Synthetic psalm text."}, 40: {1: "Synthetic next psalm."}},
            extracted.verses,
        )

    def test_selects_work_between_cross_file_anchors(self):
        first_html = """
        <html><body>
        <h3><a id="sample-start"/>Sample</h3>
            <p><strong>1</strong> Synthetic first verse.
            <sup>2</sup> Synthetic second verse.
            <sup>3</sup> Synthetic third verse.</p>
        </body></html>
        """
        second_html = """
        <html><body>
        <p>2 Synthetic second chapter.</p>
        <h3><a id="sample-end"/>Next Work</h3>
        <p><strong>1</strong> Unrelated text.</p>
        </body></html>
        """
        spec = WorkSpec(
            "Sample",
            "sample",
            ("sample",),
            ("first.html", "second.html"),
            start_anchor="sample-start",
            end_anchor="sample-end",
        )

        extracted = extract_work_from_html((first_html, second_html), spec)

        self.assertEqual(
            {
                1: {
                    1: "Synthetic first verse.",
                    2: "Synthetic second verse.",
                    3: "Synthetic third verse.",
                },
                2: {1: "Synthetic second chapter."},
            },
            extracted.verses,
        )

    def test_selects_parallel_table_column(self):
        html = """
        <html><body><table>
        <tr>
          <td><p><strong>1</strong> Synthetic left text.</p></td>
          <td><p><strong>1</strong> Synthetic right text.</p></td>
        </tr>
        </table></body></html>
        """
        left = WorkSpec("Left", "left", ("left",), ("sample.html",), table_column=0)
        right = WorkSpec("Right", "right", ("right",), ("sample.html",), table_column=1)

        self.assertEqual(
            {1: {1: "Synthetic left text."}},
            extract_work_from_html((html,), left).verses,
        )
        self.assertEqual(
            {1: {1: "Synthetic right text."}},
            extract_work_from_html((html,), right).verses,
        )

    def test_plain_leading_verse_can_precede_superscript_markers(self):
        html = """
        <html><body><table><tr>
          <td><p>1 Synthetic first verse.
          <sup>2</sup> Synthetic second verse.</p></td>
          <td><p>Other column.</p></td>
        </tr></table></body></html>
        """
        spec = WorkSpec(
            "Sample",
            "sample",
            ("sample",),
            ("sample.html",),
            single_chapter=True,
            table_column=0,
        )

        extracted = extract_work_from_html((html,), spec)

        self.assertEqual(
            {
                1: {
                    1: "Synthetic first verse.",
                    2: "Synthetic second verse.",
                }
            },
            extracted.verses,
        )

    def test_builds_positional_chapter_arrays(self):
        chapters = build_chapters(
            ExtractedWork(
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
