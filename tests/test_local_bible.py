import json
import tempfile
import unittest
from pathlib import Path

from handlers import build_passage_header_url
from parsing import (
    get_version_provider,
    resolve_auto_version,
    supported_book_slugs,
    supported_versions_for_book_slug,
)
from services.local_bible import LocalBibleClient, format_local_passage_entry
from state import EMPTY, InlinePassageResult
from versions import ScriptureSystemId, get_version_system


def structured_chapter(
    *verses: str | None,
    headers: dict[str, list[str]] | None = None,
    source_url: str | None = None,
) -> dict[str, object]:
    chapter: dict[str, object] = {
        "verses": [None, *verses],
        "headers": headers or {},
    }
    if source_url is not None:
        chapter["source_url"] = source_url
    return chapter


class LocalBibleTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_client_returns_exact_passage(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "LONIV" / "books").mkdir(parents=True)
            (base_path / "LONIV" / "version.json").write_text(
                json.dumps(
                    {
                        "code": "LONIV",
                        "name": "New International Version",
                        "language": "EN",
                        "system": "bible",
                        "aliases": [],
                    }
                ),
                encoding="utf-8",
            )
            (base_path / "LONIV" / "books" / "john.json").write_text(
                json.dumps(
                    {
                        "title": "John",
                        "slug": "john",
                        "aliases": ["john", "jn"],
                        "passages": {"John 3:16": "Synthetic local passage."},
                    }
                ),
                encoding="utf-8",
            )
            client = LocalBibleClient(base_path)

            result = await client.get_passage("john 3:16", "LONIV")

            self.assertEqual("John 3:16 LONIV\n\nSynthetic local passage.", result)

    async def test_local_client_normalizes_abbreviated_lookup_keys(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "LOKJV" / "books").mkdir(parents=True)
            (base_path / "LOKJV" / "version.json").write_text(
                json.dumps(
                    {
                        "code": "LOKJV",
                        "name": "King James Version",
                        "language": "EN",
                        "system": "bible",
                        "aliases": [],
                    }
                ),
                encoding="utf-8",
            )
            (base_path / "LOKJV" / "books" / "1corinthians.json").write_text(
                json.dumps(
                    {
                        "title": "1 Corinthians",
                        "slug": "1corinthians",
                        "aliases": ["1 corinthians", "1co"],
                        "passages": {"1 Corinthians 13:4-7": "Love suffereth long."},
                    }
                ),
                encoding="utf-8",
            )
            client = LocalBibleClient(base_path)

            result = await client.get_passage("1co13:4-7", "LOKJV")

            self.assertEqual(
                "1 Corinthians 13:4–7 LOKJV\n\nLove suffereth long.", result
            )

    async def test_local_client_supports_inline_details(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "LOJPS" / "books").mkdir(parents=True)
            (base_path / "LOJPS" / "version.json").write_text(
                json.dumps(
                    {
                        "code": "LOJPS",
                        "name": "Jewish Publication Society",
                        "language": "EN",
                        "system": "bible",
                        "aliases": [],
                    }
                ),
                encoding="utf-8",
            )
            (base_path / "LOJPS" / "books" / "genesis.json").write_text(
                json.dumps(
                    {
                        "title": "Genesis",
                        "slug": "genesis",
                        "aliases": ["genesis", "gen"],
                        "passages": {
                            "Genesis 1:1": {
                                "title": "Genesis 1:1",
                                "text": ["Synthetic Genesis sample."],
                                "description": "Offline JPS sample",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            client = LocalBibleClient(base_path)

            result = await client.get_passage("gen 1:1", "LOJPS", inline_details=True)

            self.assertIsInstance(result, InlinePassageResult)
            assert isinstance(result, InlinePassageResult)
            self.assertEqual("Genesis 1:1/LOJPS", result.result_id)
            self.assertEqual("Offline JPS sample", result.description)

    async def test_local_client_returns_empty_for_missing_passage(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = LocalBibleClient(Path(tmp_dir))
            result = await client.get_passage("John 3:16", "NIV")
            self.assertEqual(EMPTY, result)

    async def test_local_client_composes_same_chapter_ranges_from_verse_entries(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "HERM" / "books").mkdir(parents=True)
            (base_path / "HERM" / "version.json").write_text(
                json.dumps(
                    {
                        "code": "HERM",
                        "name": "Hermeneia",
                        "language": "EN",
                        "system": "bible",
                        "aliases": [],
                    }
                ),
                encoding="utf-8",
            )
            (base_path / "HERM" / "books" / "1enoch.json").write_text(
                json.dumps(
                    {
                        "title": "1 Enoch",
                        "slug": "1enoch",
                        "aliases": ["1 enoch", "1enoch", "first enoch", "enoch"],
                        "chapters": [
                            None,
                            structured_chapter(
                                "Synthetic first verse.",
                                "Synthetic second verse.",
                                "Synthetic third verse.",
                            ),
                        ],
                    }
                ),
                encoding="utf-8",
            )
            client = LocalBibleClient(base_path)

            result = await client.get_passage("1 Enoch 1:1-2", "HERM")

            self.assertEqual(
                "1 Enoch 1:1–2 HERM\n\n"
                "1 Synthetic first verse.\n"
                "² Synthetic second verse.",
                result,
            )

    async def test_local_client_composes_chapter_requests_from_verse_entries(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "HERM" / "books").mkdir(parents=True)
            (base_path / "HERM" / "version.json").write_text(
                json.dumps(
                    {
                        "code": "HERM",
                        "name": "Hermeneia",
                        "language": "EN",
                        "system": "bible",
                        "aliases": [],
                    }
                ),
                encoding="utf-8",
            )
            (base_path / "HERM" / "books" / "1enoch.json").write_text(
                json.dumps(
                    {
                        "title": "1 Enoch",
                        "slug": "1enoch",
                        "aliases": ["1 enoch", "1enoch", "first enoch", "enoch"],
                        "chapters": [
                            None,
                            structured_chapter(
                                "Synthetic first verse.",
                                "Synthetic second verse.",
                            ),
                        ],
                    }
                ),
                encoding="utf-8",
            )
            client = LocalBibleClient(base_path)

            result = await client.get_passage("1 Enoch 1", "HERM")

            self.assertEqual(
                "1 Enoch 1 HERM\n\n1 Synthetic first verse.\n² Synthetic second verse.",
                result,
            )

    async def test_local_client_registers_metadata_driven_versions_and_books(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "HERM" / "books").mkdir(parents=True)
            (base_path / "HERM" / "version.json").write_text(
                json.dumps(
                    {
                        "code": "HERM",
                        "name": "Hermeneia",
                        "language": "EN",
                        "system": "bible",
                        "aliases": ["H1E"],
                    }
                ),
                encoding="utf-8",
            )
            (base_path / "HERM" / "books" / "1enoch.json").write_text(
                json.dumps(
                    {
                        "title": "1 Enoch",
                        "slug": "1enoch",
                        "aliases": [
                            "1 enoch",
                            "1enoch",
                            "first enoch",
                            "enoch",
                        ],
                        "source_url": "https://doi.org/10.2307/j.ctt22nm5vn",
                        "chapters": [
                            None,
                            structured_chapter("Synthetic first verse."),
                        ],
                    }
                ),
                encoding="utf-8",
            )

            LocalBibleClient(base_path)

            self.assertEqual(ScriptureSystemId.BIBLE, get_version_system("HERM"))
            self.assertEqual("local", get_version_provider("HERM"))
            self.assertIn("1enoch", supported_book_slugs("HERM"))
            self.assertEqual(
                frozenset({"HERM"}),
                supported_versions_for_book_slug("1enoch"),
            )
            self.assertEqual("HERM", resolve_auto_version("NIV", "Enoch 1:1"))
            self.assertEqual(
                "https://doi.org/10.2307/j.ctt22nm5vn",
                build_passage_header_url("Enoch 1:1", "HERM"),
            )

    async def test_local_client_merges_multiple_files_for_one_version_family(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "HERM" / "books").mkdir(parents=True)
            (base_path / "HERM" / "version.json").write_text(
                json.dumps(
                    {
                        "code": "HERM",
                        "name": "Hermeneia",
                        "language": "EN",
                        "system": "bible",
                        "aliases": [],
                    }
                ),
                encoding="utf-8",
            )
            (base_path / "HERM" / "books" / "1enoch.json").write_text(
                json.dumps(
                    {
                        "title": "1 Enoch",
                        "slug": "1enoch",
                        "aliases": ["1 enoch", "enoch"],
                        "source_url": "https://doi.org/10.2307/j.ctt22nm5vn",
                        "chapters": [
                            None,
                            structured_chapter("Synthetic first verse."),
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (base_path / "HERM" / "books" / "jubilees.json").write_text(
                json.dumps(
                    {
                        "title": "Jubilees",
                        "slug": "jubilees",
                        "aliases": ["jubilees", "book of jubilees"],
                        "chapters": [
                            None,
                            structured_chapter("These are the words of the division."),
                        ],
                    }
                ),
                encoding="utf-8",
            )

            client = LocalBibleClient(base_path)

            self.assertEqual(
                "Jubilees 1:1 HERM\n\n1 These are the words of the division.",
                await client.get_passage("Jubilees 1:1", "HERM"),
            )
            self.assertIn("1enoch", supported_book_slugs("HERM"))
            self.assertIn("jubilees", supported_book_slugs("HERM"))

    async def test_local_client_marks_new_chapters_with_plain_chapter_numbers(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "HERM" / "books").mkdir(parents=True)
            (base_path / "HERM" / "version.json").write_text(
                json.dumps(
                    {
                        "code": "HERM",
                        "name": "Hermeneia",
                        "language": "EN",
                        "system": "bible",
                        "aliases": [],
                    }
                ),
                encoding="utf-8",
            )
            (base_path / "HERM" / "books" / "1enoch.json").write_text(
                json.dumps(
                    {
                        "title": "1 Enoch",
                        "slug": "1enoch",
                        "aliases": ["1 enoch", "1enoch", "first enoch", "enoch"],
                        "chapters": [
                            None,
                            structured_chapter(
                                "Synthetic first verse.",
                                "Synthetic second verse.",
                            ),
                            structured_chapter(
                                "Another chapter begins.",
                                "Its second verse follows.",
                            ),
                        ],
                    }
                ),
                encoding="utf-8",
            )
            client = LocalBibleClient(base_path)

            result = await client.get_passage("1 Enoch 1:2-2:2", "HERM")

            self.assertEqual(
                "1 Enoch 1:2–2:2 HERM\n\n"
                "² Synthetic second verse.\n"
                "2 Another chapter begins.\n"
                "² Its second verse follows.",
                result,
            )

    async def test_local_client_supports_structured_headers_and_prefaces(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "HERM" / "books").mkdir(parents=True)
            (base_path / "HERM" / "version.json").write_text(
                json.dumps(
                    {
                        "code": "HERM",
                        "name": "Hermeneia",
                        "language": "EN",
                        "system": "bible",
                        "aliases": [],
                    }
                ),
                encoding="utf-8",
            )
            (base_path / "HERM" / "books" / "1enoch.json").write_text(
                json.dumps(
                    {
                        "title": "1 Enoch",
                        "slug": "1enoch",
                        "aliases": ["1 enoch", "1enoch", "first enoch", "enoch"],
                        "chapters": [
                            {"verses": ["General preface"], "headers": {}},
                            {
                                "verses": [
                                    "Chapter preface",
                                    "Synthetic first verse.",
                                ],
                                "headers": {"1": ["Primary Section"]},
                                "source_url": "https://example.com/1enoch/ch1",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            client = LocalBibleClient(base_path)

            result = await client.get_passage("1 Enoch 1:1", "HERM")

            self.assertEqual(
                "1 Enoch 1:1 HERM\n\n"
                "General preface\n\n"
                "Chapter preface\n\n"
                "Primary Section\n\n"
                "1 Synthetic first verse.",
                result,
            )
            self.assertEqual(
                "https://example.com/1enoch/ch1",
                build_passage_header_url("1 Enoch 1:1", "HERM"),
            )


class LocalBibleFormattingTests(unittest.TestCase):
    def test_format_local_passage_entry_rejects_empty_entry(self):
        self.assertEqual(EMPTY, format_local_passage_entry("John 3:16", {}))

    def test_format_local_passage_entry_superscripts_leading_verse_numbers(self):
        result = format_local_passage_entry(
            "John 3:16-17",
            ["16 Synthetic sixteenth verse.", "17 Synthetic seventeenth verse."],
            version="NIV",
        )
        expected = (
            "John 3:16–17 NIV\n\n"
            "¹⁶ Synthetic sixteenth verse.\n"
            "¹⁷ Synthetic seventeenth verse."
        )
        self.assertEqual(
            expected,
            result,
        )

    def test_format_local_passage_entry_cleans_hermeneia_epub_artifacts(self):
        result = format_local_passage_entry(
            "1 Enoch 93:1",
            {
                "chapter": 93,
                "verse": 1,
                "text": (
                    "After this Enoch took up his discourse , saying he "
                    "\u00adunderstood."
                ),
            },
            version="HERM",
        )

        self.assertEqual(
            "1 Enoch 93:1 HERM\n\n"
            "93 After this Enoch took up his discourse, saying he understood.",
            result,
        )


if __name__ == "__main__":
    unittest.main()
