import unittest

from versions import (
    LanguageCode,
    ScriptureSystemId,
    Version,
    format_language_group,
    get_scripture_system,
    register_runtime_version,
    unregister_runtime_version,
)


class LanguageGroupTests(unittest.TestCase):
    def test_language_appears_only_while_it_has_a_version(self):
        label = format_language_group(LanguageCode.GEZ)
        version = Version.local(
            "Synthetic Geʿez Bible",
            "TESTGEZ",
            frozenset({"genesis"}),
        )

        system = get_scripture_system(ScriptureSystemId.BIBLE)
        self.assertNotIn(label, system.language_group_labels)
        self.assertIsNone(system.resolve_language_group(label))
        self.assertIsNone(system.get_versions_for_language(LanguageCode.GEZ))

        register_runtime_version(
            ScriptureSystemId.BIBLE,
            LanguageCode.GEZ,
            version,
        )
        try:
            system = get_scripture_system(ScriptureSystemId.BIBLE)
            self.assertIn(label, system.language_group_labels)
            self.assertEqual(LanguageCode.GEZ, system.resolve_language_group(label))
            self.assertEqual(
                ("Synthetic Geʿez Bible (TESTGEZ)",),
                system.get_versions_for_language(LanguageCode.GEZ),
            )
        finally:
            unregister_runtime_version(ScriptureSystemId.BIBLE, version.code)

        system = get_scripture_system(ScriptureSystemId.BIBLE)
        self.assertNotIn(label, system.language_group_labels)
        self.assertIsNone(system.resolve_language_group(label))
        self.assertIsNone(system.get_versions_for_language(LanguageCode.GEZ))
