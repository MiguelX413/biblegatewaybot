import unittest

from parsing import build_passage_from_ref, other_version, parse_get_request


class ParsingTests(unittest.TestCase):
    def test_parse_get_uses_default_version(self):
        version, passage = parse_get_request("/get John 3:16", "NIV")
        self.assertEqual(("NIV", "John 3:16"), (version, passage))

    def test_parse_get_uses_command_suffix_version(self):
        version, passage = parse_get_request("/getnlt 1 cor 13:4-7", "NIV")
        self.assertEqual(("NLT", "1 cor 13:4-7"), (version, passage))

    def test_parse_get_uses_leading_passage_version(self):
        version, passage = parse_get_request("/get NASB John 3:16", "NIV")
        self.assertEqual(("NASB", "John 3:16"), (version, passage))

    def test_parse_get_rejects_invalid_version(self):
        version, passage = parse_get_request("/getabc John 3:16", "NIV")
        self.assertEqual((None, None), (version, passage))

    def test_build_passage_from_ref_normalizes_revelation_name(self):
        passage = build_passage_from_ref(("Revelation of Jesus Christ", 1, 1, 1, 3))
        self.assertEqual("Revelation 1:1-1:3", passage)

    def test_other_version_flips_nasb(self):
        self.assertEqual("NIV", other_version("NASB"))
        self.assertEqual("NASB", other_version("NIV"))


if __name__ == "__main__":
    unittest.main()
