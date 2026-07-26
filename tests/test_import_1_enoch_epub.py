import unittest

from tools.import_1_enoch_epub import extract_verses_from_html


class Import1EnochEpubTests(unittest.TestCase):
    def test_extract_verses_splits_inline_slash_verse_markers(self):
        html = """
        <html><body>
        <p class="indent">
        5:1 Contemplate all the trees; their leaves blossom green on them.
        </p>
        <p class="indent">
        Contemplate all these works, and understand that he who lives for all
        the ages made all these works. 2/ And his works take place from year to
        year.
        </p>
        <p class="indent">
        3 Observe how, in like manner, the sea and the rivers carry out their
        works.
        </p>
        </body></html>
        """

        verses = extract_verses_from_html(html)

        self.assertEqual(
            {
                5: {
                    1: (
                        "Contemplate all the trees; their leaves blossom green "
                        "on them. Contemplate all these works, and understand "
                        "that he who lives for all the ages made all these "
                        "works."
                    ),
                    2: "And his works take place from year to year.",
                    3: (
                        "Observe how, in like manner, the sea and the rivers carry out "
                        "their works."
                    ),
                }
            },
            verses,
        )

    def test_extract_verses_splits_multiple_inline_markers_in_one_paragraph(self):
        html = """
        <html><body>
        <p class="indent">
        7:3 They were devouring the labor of all the sons of men. 4/ And the
        giants began to kill men and to devour them. 5/ And they began to sin
        against the birds and beasts.
        </p>
        </body></html>
        """

        verses = extract_verses_from_html(html)

        self.assertEqual(
            {
                7: {
                    3: "They were devouring the labor of all the sons of men.",
                    4: "And the giants began to kill men and to devour them.",
                    5: "And they began to sin against the birds and beasts.",
                }
            },
            verses,
        )

    def test_extract_verses_splits_inline_chapter_transition_markers(self):
        html = """
        <html><body>
        <p class="indent">
        23:4 Then Reuel answered me. 24:1/ And he showed me mountains of fire
        that burned day and night.
        </p>
        </body></html>
        """

        verses = extract_verses_from_html(html)

        self.assertEqual(
            {
                23: {4: "Then Reuel answered me."},
                24: {
                    1: "And he showed me mountains of fire that burned day and night."
                },
            },
            verses,
        )


if __name__ == "__main__":
    unittest.main()
