import json
import tempfile
import unittest
from pathlib import Path

from services.local_bible import LocalBibleClient, format_local_passage_entry
from state import EMPTY, InlinePassageResult


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

            self.assertEqual("1 Corinthians 13:4-7 KJV\n\nLove suffereth long.", result)

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
            "John 3:16-17 NIV\n\n"
            "¹⁶ For God so loved the world.\n\n"
            "¹⁷ For God sent not his Son."
        )
        self.assertEqual(
            expected,
            result,
        )


if __name__ == "__main__":
    unittest.main()
