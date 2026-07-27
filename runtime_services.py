from telegram.ext import Application

from config import BotConfig, load_config
from parsing import clear_runtime_books
from services.bible_com import BibleComClient
from services.bible_gateway import BibleGatewayClient
from services.lds_scriptures import LdsScripturesClient
from services.local_bible import LocalBibleClient
from services.quran_client import create_quran_client
from services.quran_foundation import QuranFoundationClient
from services.sefaria import SefariaClient
from versions import (
    QURAN_FOUNDATION_RUNTIME_VERSIONS,
    ScriptureSystemId,
    clear_runtime_book_slugs,
    clear_runtime_versions,
    register_runtime_version,
    unregister_runtime_version,
)


def configure_runtime_services(application: Application, config: BotConfig) -> None:
    application.bot_data["config"] = config
    application.bot_data["bible_client"] = BibleGatewayClient()
    application.bot_data["bible_com_client"] = BibleComClient()
    application.bot_data["quran_client"] = create_quran_client(config)
    application.bot_data["lds_client"] = LdsScripturesClient()
    application.bot_data["sefaria_client"] = SefariaClient()
    application.bot_data["local_bible_client"] = LocalBibleClient()


async def initialize_quran_runtime_versions(application: Application) -> None:
    quran_client = application.bot_data.get("quran_client")
    if isinstance(quran_client, QuranFoundationClient):
        if await quran_client.initialize():
            for language_code, version in QURAN_FOUNDATION_RUNTIME_VERSIONS:
                register_runtime_version(
                    ScriptureSystemId.QURAN,
                    language_code,
                    version,
                )
            return
    for _, version in QURAN_FOUNDATION_RUNTIME_VERSIONS:
        unregister_runtime_version(ScriptureSystemId.QURAN, version.code)


async def initialize_runtime_services(application: Application) -> None:
    config = load_config()
    configure_runtime_services(application, config)
    await initialize_quran_runtime_versions(application)


async def close_http_client(application: Application) -> None:
    bible_client: BibleGatewayClient | None = application.bot_data.get("bible_client")
    bible_com_client: BibleComClient | None = application.bot_data.get(
        "bible_com_client"
    )
    quran_client = application.bot_data.get("quran_client")
    lds_client: LdsScripturesClient | None = application.bot_data.get("lds_client")
    sefaria_client: SefariaClient | None = application.bot_data.get("sefaria_client")
    local_bible_client: LocalBibleClient | None = application.bot_data.get(
        "local_bible_client"
    )
    if bible_client is not None:
        await bible_client.close()
    if bible_com_client is not None:
        await bible_com_client.close()
    if quran_client is not None:
        await quran_client.close()
    if lds_client is not None:
        await lds_client.close()
    if sefaria_client is not None:
        await sefaria_client.close()
    if local_bible_client is not None:
        await local_bible_client.close()


async def reload_runtime_services(application: Application) -> None:
    await close_http_client(application)
    clear_runtime_books()
    clear_runtime_book_slugs()
    clear_runtime_versions()
    config = load_config()
    configure_runtime_services(application, config)
    await initialize_quran_runtime_versions(application)
