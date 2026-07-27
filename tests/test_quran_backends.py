import unittest

from config import BotConfig
from services.quran_client import create_quran_client
from services.quran_common import clean_quran_translation_text
from services.quran_foundation import _resolve_qf_env


class QuranBackendTests(unittest.TestCase):
    def test_clean_quran_translation_text_strips_html_and_footnotes(self):
        self.assertEqual(
            "In the name of Allah, the Entirely Merciful, the Especially Merciful.",
            clean_quran_translation_text(
                'In the name of Allah,<sup foot_note="1">1</sup> '
                "<em>the Entirely Merciful</em>, the Especially Merciful."
            ),
        )

    def test_resolve_qf_env_accepts_short_names_and_urls(self):
        self.assertEqual("prelive", _resolve_qf_env("prelive"))
        self.assertEqual("production", _resolve_qf_env("production"))
        self.assertEqual(
            "prelive", _resolve_qf_env("https://prelive-oauth2.quran.foundation")
        )
        self.assertEqual(
            "production", _resolve_qf_env("https://oauth2.quran.foundation")
        )

    def test_create_quran_client_uses_alquran_cloud_without_qf_credentials(self):
        config = BotConfig(
            token="token",
            admin_id=None,
            botfamily_hash=None,
            offline_only=False,
            quran_backend="auto",
            qf_client_id=None,
            qf_client_secret=None,
            qf_env=None,
        )
        client = create_quran_client(config)
        self.assertEqual("AlQuranCloudClient", type(client).__name__)

    def test_create_quran_client_prefers_qf_with_credentials(self):
        config = BotConfig(
            token="token",
            admin_id=None,
            botfamily_hash=None,
            offline_only=False,
            quran_backend="auto",
            qf_client_id="client-id",
            qf_client_secret="client-secret",
            qf_env="prelive",
        )
        client = create_quran_client(config)
        self.assertEqual("QuranFoundationClient", type(client).__name__)


if __name__ == "__main__":
    unittest.main()
