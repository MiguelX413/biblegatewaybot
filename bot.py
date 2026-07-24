import logging

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    InlineQueryHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from config import load_config
from handlers import (
    botfamily_verification_command,
    cancel_conversation,
    error_handler,
    get_command_entry,
    get_conversation_message,
    handle_inline_query,
    handle_new_members,
    help_command,
    linked_passage_handler,
    more_command,
    quick_lookup_handler,
    search_command_entry,
    search_conversation_message,
    setdefault_entry,
    setdefault_language_message,
    setdefault_version_message,
    settings_command,
    start,
    start_setdefault_entry,
)
from services.bible_com import BibleComClient
from services.bible_gateway import BibleGatewayClient
from services.lds_scriptures import LdsScripturesClient
from services.local_bible import LocalBibleClient
from services.sefaria import SefariaClient
from state import (
    GET_PASSAGE_STATE,
    PERSISTENCE_FILE,
    SEARCH_STATE,
    SETDEFAULT_LANGUAGE_STATE,
    SETDEFAULT_VERSION_STATE,
)
from versions import BOOKS, SEFARIA_VERSION_TITLES


def configure_runtime_services(application: Application, config) -> None:
    application.bot_data["config"] = config
    application.bot_data["bible_client"] = BibleGatewayClient()
    application.bot_data["bible_com_client"] = BibleComClient()
    application.bot_data["lds_client"] = LdsScripturesClient()
    application.bot_data["sefaria_client"] = SefariaClient(SEFARIA_VERSION_TITLES)
    application.bot_data["local_bible_client"] = (
        LocalBibleClient(config.offline_bibles_path)
        if config.offline_bibles_path
        else None
    )


async def initialize_runtime_services(application: Application) -> None:
    config = load_config()
    configure_runtime_services(application, config)


async def close_http_client(application: Application) -> None:
    bible_client: BibleGatewayClient | None = application.bot_data.get("bible_client")
    bible_com_client: BibleComClient | None = application.bot_data.get(
        "bible_com_client"
    )
    lds_client: LdsScripturesClient | None = application.bot_data.get("lds_client")
    sefaria_client: SefariaClient | None = application.bot_data.get("sefaria_client")
    local_bible_client: LocalBibleClient | None = application.bot_data.get(
        "local_bible_client"
    )
    if bible_client is not None:
        await bible_client.close()
    if bible_com_client is not None:
        await bible_com_client.close()
    if lds_client is not None:
        await lds_client.close()
    if sefaria_client is not None:
        await sefaria_client.close()
    if local_bible_client is not None:
        await local_bible_client.close()


def build_application() -> Application:
    config = load_config()
    persistence = PicklePersistence(filepath=str(PERSISTENCE_FILE))
    application = (
        ApplicationBuilder()
        .token(config.token)
        .persistence(persistence)
        .post_init(initialize_runtime_services)
        .post_shutdown(close_http_client)
        .build()
    )
    configure_runtime_services(application, config)

    get_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^/get(@\w+)?(\s|$)"), get_command_entry)
        ],
        states={
            GET_PASSAGE_STATE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, get_conversation_message
                )
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        name="get_conversation",
        persistent=True,
    )

    search_conversation = ConversationHandler(
        entry_points=[CommandHandler("search", search_command_entry)],
        states={
            SEARCH_STATE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, search_conversation_message
                )
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        name="search_conversation",
        persistent=True,
    )

    setdefault_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("setdefault", setdefault_entry),
            MessageHandler(
                filters.Regex(r"^/start setdefault$"), start_setdefault_entry
            ),
        ],
        states={
            SETDEFAULT_LANGUAGE_STATE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, setdefault_language_message
                )
            ],
            SETDEFAULT_VERSION_STATE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, setdefault_version_message
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        name="setdefault_conversation",
        persistent=True,
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("more", more_command))
    application.add_handler(
        CommandHandler("botfamily_verification_code", botfamily_verification_command)
    )
    application.add_handler(get_conversation)
    application.add_handler(search_conversation)
    application.add_handler(setdefault_conversation)
    application.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members)
    )
    application.add_handler(InlineQueryHandler(handle_inline_query))
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^/(" + "|".join(BOOKS) + r")"), linked_passage_handler
        )
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, quick_lookup_handler)
    )
    application.add_error_handler(error_handler)
    return application


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.info("Starting scripturebot via python-telegram-bot polling")
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    return 0
