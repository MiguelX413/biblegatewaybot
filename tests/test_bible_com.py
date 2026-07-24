import json
import unittest

from services.bible_com import (
    BIBLE_COM_VERSION_IDS,
    build_bible_com_passage_url,
    extract_chapter_content,
    parse_bible_com_reference,
    parse_chapter_content,
)


def build_page_html(content_html: str) -> str:
    payload = {
        "props": {
            "pageProps": {
                "chapterInfo": {"content": content_html},
                "versionData": {"id": BIBLE_COM_VERSION_IDS["TMA"]},
            }
        }
    }
    return (
        "<html><body>"
        '<script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(payload)}"
        "</script>"
        "</body></html>"
    )


CHAPTER_CONTENT_HTML = """
<div class="version vid1714 iso6393arb rtl" data-vid="1714" data-iso6393="arb">
  <div class="book bkMAT">
    <div class="chapter ch3" data-usfm="MAT.3">
      <div class="label">3</div>
      <div class="cl"><span class="heading">الفصل الثّالث</span></div>
      <div class="s"><span class="heading">دعوة النّبيّ يحيى</span></div>
      <div class="p">
        <span class="verse v1" data-usfm="MAT.3.1">
          <span class="label">1</span>
          <span class="content">النص الأول.</span>
          <span class="note f">
            <span class="label">#</span>
            <span class="body">حاشية يجب حذفها.</span>
          </span>
        </span>
        <span class="verse v2" data-usfm="MAT.3.2">
          <span class="label">2</span>
          <span class="content">النص الثاني.</span>
        </span>
      </div>
      <div class="s"><span class="heading">عنوان ثانٍ</span></div>
      <div class="p">
        <span class="verse v3" data-usfm="MAT.3.3">
          <span class="label">3</span>
          <span class="content">النص الثالث.</span>
        </span>
      </div>
    </div>
  </div>
</div>
"""

POETIC_CHAPTER_CONTENT_HTML = """
<div class="version vid1981 iso6393arb rtl" data-vid="1981" data-iso6393="arb">
  <div class="book bkGEN">
    <div class="chapter ch1" data-usfm="GEN.1">
      <div class="label">1</div>
      <div class="ms2">١. نشأة العالم والبشريّة</div>
      <div class="ms3">أ - خَلْق العالَم</div>
      <div class="s1">الرواية الأولى</div>
      <div class="q">1 في البدء خلق الله السماوات والأرض،</div>
      <div class="q">وكانت الأرض خاوِية.</div>
      <div class="q">2 وقال الله كلامًا آخر.</div>
    </div>
  </div>
</div>
"""


class BibleComParsingTests(unittest.TestCase):
    def test_parse_bible_com_reference(self):
        reference = parse_bible_com_reference("Matthew 3:1-2")
        assert reference is not None
        self.assertEqual("matthew", reference.book_slug)
        self.assertEqual("MAT", reference.book_usfm)
        self.assertEqual(3, reference.start_chapter)
        self.assertEqual(1, reference.start_verse)
        self.assertEqual(3, reference.end_chapter)
        self.assertEqual(2, reference.end_verse)

    def test_build_bible_com_passage_url(self):
        self.assertEqual(
            "https://bible.com/bible/1714/MAT.3.1-2",
            build_bible_com_passage_url("Matthew 3:1-2", "TMA"),
        )

    def test_extract_chapter_content(self):
        page_html = build_page_html(CHAPTER_CONTENT_HTML)
        self.assertEqual(CHAPTER_CONTENT_HTML, extract_chapter_content(page_html))

    def test_parse_chapter_content_chapter(self):
        blocks = parse_chapter_content(CHAPTER_CONTENT_HTML)
        self.assertEqual("الفصل الثّالث", blocks[0])
        self.assertEqual("دعوة النّبيّ يحيى", blocks[1])
        self.assertIn("¹ النص الأول.", blocks[2])
        self.assertIn("² النص الثاني.", blocks[2])
        self.assertEqual("عنوان ثانٍ", blocks[3])
        self.assertEqual("³ النص الثالث.", blocks[4])
        self.assertNotIn("حاشية", " ".join(blocks))

    def test_parse_chapter_content_filters_verses(self):
        blocks = parse_chapter_content(CHAPTER_CONTENT_HTML, start_verse=2, end_verse=3)
        self.assertEqual("الفصل الثّالث", blocks[0])
        self.assertEqual("دعوة النّبيّ يحيى", blocks[1])
        self.assertEqual("² النص الثاني.", blocks[2])
        self.assertEqual("عنوان ثانٍ", blocks[3])
        self.assertEqual("³ النص الثالث.", blocks[4])

    def test_parse_chapter_content_supports_embedded_verse_numbers(self):
        blocks = parse_chapter_content(POETIC_CHAPTER_CONTENT_HTML)
        self.assertEqual("١. نشأة العالم والبشريّة", blocks[0])
        self.assertEqual("أ - خَلْق العالَم", blocks[1])
        self.assertEqual("الرواية الأولى", blocks[2])
        self.assertEqual(
            "¹ في البدء خلق الله السماوات والأرض،\nوكانت الأرض خاوِية.",
            blocks[3],
        )
        self.assertEqual("² وقال الله كلامًا آخر.", blocks[4])


if __name__ == "__main__":
    unittest.main()
