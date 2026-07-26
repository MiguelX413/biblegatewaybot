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


class LocalBibleTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_client_returns_exact_passage(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "NIV.json").write_text(
                json.dumps({"John 3:16": "For God so loved the world."}),
                encoding="utf-8",
            )
            client = LocalBibleClient(base_path)

            result = await client.get_passage("john 3:16", "NIV")

            self.assertEqual("John 3:16 NIV\n\nFor God so loved the world.", result)

    async def test_local_client_normalizes_abbreviated_lookup_keys(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "KJV.json").write_text(
                json.dumps({"1 Corinthians 13:4-7": "Love suffereth long."}),
                encoding="utf-8",
            )
            client = LocalBibleClient(base_path)

            result = await client.get_passage("1co13:4-7", "KJV")

            self.assertEqual("1 Corinthians 13:4–7 KJV\n\nLove suffereth long.", result)

    async def test_local_client_supports_inline_details(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "JPS.json").write_text(
                json.dumps(
                    {
                        "Genesis 1:1": {
                            "title": "Genesis 1:1",
                            "text": [
                                "In the beginning God created the heaven and the earth."
                            ],
                            "description": "Offline JPS sample",
                        }
                    }
                ),
                encoding="utf-8",
            )
            client = LocalBibleClient(base_path)

            result = await client.get_passage("gen 1:1", "JPS", inline_details=True)

            self.assertIsInstance(result, InlinePassageResult)
            assert isinstance(result, InlinePassageResult)
            self.assertEqual("Genesis 1:1/JPS", result.result_id)
            self.assertEqual("Offline JPS sample", result.description)

    async def test_local_client_returns_empty_for_missing_passage(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            client = LocalBibleClient(Path(tmp_dir))
            result = await client.get_passage("John 3:16", "NIV")
            self.assertEqual(EMPTY, result)

    async def test_local_client_composes_same_chapter_ranges_from_verse_entries(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "versions").mkdir()
            (base_path / "works").mkdir()
            (base_path / "versions" / "HERM.json").write_text(
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
            (base_path / "works" / "1enoch.herm.json").write_text(
                json.dumps(
                    {
                        "version_code": "HERM",
                        "title": "1 Enoch",
                        "slug": "1enoch",
                        "aliases": ["1 enoch", "1enoch", "first enoch", "enoch"],
                        "chapters": [
                            [
                                "The words of the blessing.",
                                "And he took up his discourse.",
                                "And concerning the chosen I speak now.",
                            ]
                        ],
                    }
                ),
                encoding="utf-8",
            )
            client = LocalBibleClient(base_path)

            result = await client.get_passage("1 Enoch 1:1-2", "HERM")

            self.assertEqual(
                "1 Enoch 1:1–2 HERM\n\n"
                "1 The words of the blessing.\n\n"
                "² And he took up his discourse.",
                result,
            )

    async def test_local_client_composes_chapter_requests_from_verse_entries(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "versions").mkdir()
            (base_path / "works").mkdir()
            (base_path / "versions" / "HERM.json").write_text(
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
            (base_path / "works" / "1enoch.herm.json").write_text(
                json.dumps(
                    {
                        "version_code": "HERM",
                        "title": "1 Enoch",
                        "slug": "1enoch",
                        "aliases": ["1 enoch", "1enoch", "first enoch", "enoch"],
                        "chapters": [
                            [
                                "The words of the blessing.",
                                "And he took up his discourse.",
                            ]
                        ],
                    }
                ),
                encoding="utf-8",
            )
            client = LocalBibleClient(base_path)

            result = await client.get_passage("1 Enoch 1", "HERM")

            self.assertEqual(
                "1 Enoch 1 HERM\n\n"
                "1 The words of the blessing.\n\n"
                "² And he took up his discourse.",
                result,
            )

    async def test_local_client_registers_metadata_driven_versions_and_books(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_path = Path(tmp_dir)
            (base_path / "versions").mkdir()
            (base_path / "works").mkdir()
            (base_path / "versions" / "HERM.json").write_text(
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
            (base_path / "works" / "1enoch.herm.json").write_text(
                json.dumps(
                    {
                        "version_code": "HERM",
                        "title": "1 Enoch",
                        "slug": "1enoch",
                        "aliases": [
                            "1 enoch",
                            "1enoch",
                            "first enoch",
                            "enoch",
                        ],
                        "source_url": "https://doi.org/10.2307/j.ctt22nm5vn",
                        "chapters": [["The words of the blessing."]],
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
            (base_path / "versions").mkdir()
            (base_path / "works").mkdir()
            (base_path / "versions" / "HERM.json").write_text(
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
            (base_path / "works" / "1enoch.herm.json").write_text(
                json.dumps(
                    {
                        "version_code": "HERM",
                        "title": "1 Enoch",
                        "slug": "1enoch",
                        "aliases": ["1 enoch", "enoch"],
                        "source_url": "https://doi.org/10.2307/j.ctt22nm5vn",
                        "chapters": [["The words of the blessing."]],
                    }
                ),
                encoding="utf-8",
            )
            (base_path / "works" / "jubilees.herm.json").write_text(
                json.dumps(
                    {
                        "version_code": "HERM",
                        "title": "Jubilees",
                        "slug": "jubilees",
                        "aliases": ["jubilees", "book of jubilees"],
                        "chapters": [["These are the words of the division."]],
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
            (base_path / "versions").mkdir()
            (base_path / "works").mkdir()
            (base_path / "versions" / "HERM.json").write_text(
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
            (base_path / "works" / "1enoch.herm.json").write_text(
                json.dumps(
                    {
                        "version_code": "HERM",
                        "title": "1 Enoch",
                        "slug": "1enoch",
                        "aliases": ["1 enoch", "1enoch", "first enoch", "enoch"],
                        "chapters": [
                            [
                                "The words of the blessing.",
                                "And he took up his discourse.",
                            ],
                            ["Another chapter begins.", "Its second verse follows."],
                        ],
                    }
                ),
                encoding="utf-8",
            )
            client = LocalBibleClient(base_path)

            result = await client.get_passage("1 Enoch 1:2-2:2", "HERM")

            self.assertEqual(
                "1 Enoch 1:2–2:2 HERM\n\n"
                "² And he took up his discourse.\n\n"
                "2 Another chapter begins.\n\n"
                "² Its second verse follows.",
                result,
            )


class LocalBibleFormattingTests(unittest.TestCase):
    def test_format_local_passage_entry_rejects_empty_entry(self):
        self.assertEqual(EMPTY, format_local_passage_entry("John 3:16", {}))

    def test_format_local_passage_entry_superscripts_leading_verse_numbers(self):
        result = format_local_passage_entry(
            "John 3:16-17",
            ["16 For God so loved the world.", "17 For God sent not his Son."],
            version="NIV",
        )
        expected = (
            "John 3:16–17 NIV\n\n"
            "¹⁶ For God so loved the world.\n\n"
            "¹⁷ For God sent not his Son."
        )
        self.assertEqual(
            expected,
            result,
        )


if __name__ == "__main__":
    unittest.main()
