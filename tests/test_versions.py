import unittest

from versions import (
    LanguageCode,
    ScriptureSystemId,
    Version,
    format_language_group,
    get_scripture_system,
    get_version,
    register_runtime_version,
    resolve_version_code,
    unregister_runtime_version,
)


class LanguageGroupTests(unittest.TestCase):
    def test_tafsir_rasag_is_judeo_arabic_torah(self):
        system = get_scripture_system(ScriptureSystemId.BIBLE)
        label = format_language_group(LanguageCode.JRB)

        self.assertIn(label, system.language_group_labels)
        self.assertEqual(
            ("Tafsir Rasag (RASAG)",),
            system.get_versions_for_language(LanguageCode.JRB),
        )
        self.assertEqual("RASAG", resolve_version_code("Tafsir Rasag"))
        self.assertEqual("RASAG", resolve_version_code("Saadia Gaon"))

        version = get_version("RASAG")
        self.assertIsNotNone(version)
        assert version is not None
        self.assertEqual(
            frozenset({"genesis", "exodus", "leviticus", "numbers", "deuteronomy"}),
            version.supported_book_slugs,
        )

    def test_targum_onqelos_is_jewish_babylonian_aramaic_torah(self):
        system = get_scripture_system(ScriptureSystemId.BIBLE)
        label = format_language_group(LanguageCode.TMR)

        self.assertIn(label, system.language_group_labels)
        self.assertEqual(
            ("Targum Onqelos, vocalized according to the Yemenite Taj (ONQELOS)",),
            system.get_versions_for_language(LanguageCode.TMR),
        )
        self.assertEqual("ONQELOS", resolve_version_code("ONQ"))
        self.assertEqual("ONQELOS", resolve_version_code("ONKELOS"))
        self.assertEqual("ONQELOS", resolve_version_code("Targum Onkelos"))
        self.assertEqual("ONQELOS", resolve_version_code("Targum Onqelos"))

        version = get_version("ONKELOS")
        self.assertIsNotNone(version)
        assert version is not None
        self.assertEqual("ONQELOS", version.code)
        self.assertEqual(
            frozenset({"genesis", "exodus", "leviticus", "numbers", "deuteronomy"}),
            version.supported_book_slugs,
        )

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
