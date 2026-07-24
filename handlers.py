import logging
from typing import Any

from scriptures import extract as extract_refs
from telegram import (
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InlineQueryResultsButton,
    InputTextMessageContent,
    Message,
    MessageEntity,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
    User,
)
from telegram.constants import ChatAction, MessageEntityType
from telegram.error import TelegramError
from telegram.ext import CallbackContext, ContextTypes, ConversationHandler

from config import BotConfig
from parsing import (
    build_bot_handle,
    build_passage_from_ref,
    canonicalize_reference,
    command_list,
    decode_linked_reference,
    ensure_text,
    find_requested_book,
    format_passage_chunks,
    format_passage_entities,
    get_passage_scripture_system,
    get_version_provider,
    is_book_only_request,
    other_version,
    parse_get_request,
    parse_reference_version_query,
    resolve_auto_version,
    version_supports_passage,
)
from services.bible_com import build_bible_com_passage_url
from services.bible_gateway import build_bible_gateway_passage_url
from services.lds_scriptures import build_lds_passage_url
from services.sefaria import build_sefaria_passage_url, resolve_sefaria_version_query
from state import (
    BACK_TO_COLLECTIONS,
    BACK_TO_LANGUAGES,
    CHOOSE_COLLECTION_PROMPT,
    CHOOSE_LANGUAGE_PROMPT,
    DEFAULT_VERSION_BY_SYSTEM,
    EMPTY,
    GET_PASSAGE_STATE,
    MAX_SEARCH_RESULTS,
    PENDING_GET_VERSION_EXPLICIT_KEY,
    PENDING_GET_VERSION_KEY,
    SEARCH_STATE,
    SELECT_VERSION_PROMPT,
    SETDEFAULT_COLLECTION_STATE,
    SETDEFAULT_LANGUAGE_STATE,
    SETDEFAULT_VERSION_STATE,
    USER_DEFAULT_VERSION_KEY_BY_SYSTEM,
    USER_SEARCH_KEY,
    USER_STARTED_KEY,
    InlinePassageResult,
    SearchState,
)
from versions import (
    BIBLE_VERSION_DATA,
    SCRIPTURE_SYSTEM_ORDER,
    SCRIPTURE_SYSTEMS,
    SEFARIA_VERSION_CONFIGS,
    VERSION_LOOKUP,
    ScriptureSystemId,
    format_version_full_label,
    format_version_inline_label,
    get_scripture_system,
    get_version_system,
    resolve_version_code,
)


def build_input_message_content(
    text: str, *, header_url: str | None = None
) -> InputTextMessageContent:
    message_text, entities = format_passage_entities(text, header_url=header_url)
    return InputTextMessageContent(message_text=message_text, entities=entities)


def build_passage_header_url(passage: str, version: str) -> str | None:
    provider = get_version_provider(version)
    if provider == "biblegateway":
        return build_bible_gateway_passage_url(passage, version)
    if provider == "biblecom":
        return build_bible_com_passage_url(passage, version)
    if provider == "sefaria":
        version_query = resolve_sefaria_version_query(
            passage, version, SEFARIA_VERSION_CONFIGS
        )
        return build_sefaria_passage_url(passage, version, version_query)
    if provider == "lds":
        return build_lds_passage_url(passage)
    return None


def build_welcome_message(
    greeting: str, application: Any
) -> tuple[str, list[MessageEntity]]:
    source_links = [
        ("BibleGateway", "https://biblegateway.com"),
        ("Bible.com", "https://bible.com"),
        ("Sefaria", "https://sefaria.org"),
        ("LDS scriptures", "https://churchofjesuschrist.org/study/scriptures"),
    ]
    sources_text = ", ".join(label for label, _ in source_links[:-1])
    sources_text += f", and {source_links[-1][0]}"
    welcome_command_list = command_list(application).replace("/search <keyword>\n", "")
    welcome_command_list = welcome_command_list.replace(
        "/search the greatest commandment\n", ""
    )
    message_text = (
        f"{greeting} This bot can fetch Bible passages from {sources_text}, "
        "and optional local offline files.\n\n"
        "To get started, enter one of the following commands:\n"
        f"{welcome_command_list}"
    )

    entities: list[MessageEntity] = []
    search_start = message_text.find("from ") + len("from ")
    for label, url in source_links:
        offset = message_text.find(label, search_start)
        if offset == -1:
            continue
        entities.append(
            MessageEntity(
                type=MessageEntityType.TEXT_LINK,
                offset=offset,
                length=len(label),
                url=url,
            )
        )
        search_start = offset + len(label)

    utf16_entities = MessageEntity.adjust_message_entities_to_utf_16(
        message_text, entities
    )
    return message_text, list(utf16_entities)


def require_message(update: Update) -> Message:
    message = update.effective_message
    assert message is not None
    return message


def require_chat(update: Update) -> Chat:
    chat = update.effective_chat
    assert chat is not None
    return chat


def require_user(update: Update) -> User:
    user = update.effective_user
    assert user is not None
    return user


def require_user_data(context: CallbackContext[Any, Any, Any, Any]) -> dict[Any, Any]:
    user_data = context.user_data
    assert user_data is not None
    return user_data


def build_inline_results_button(default_version: str) -> InlineQueryResultsButton:
    return InlineQueryResultsButton(
        text=f"Default version: {format_version_inline_label(default_version)}",
        start_parameter="setdefault",
    )


def get_try_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Try inline mode", switch_inline_query_current_chat="John 3:16 NLT"
                )
            ]
        ]
    )


def build_buttons(menu: list[str]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[item] for item in menu],
        one_time_keyboard=True,
        resize_keyboard=True,
        selective=True,
    )


async def reply_no_results(
    message: Message,
    display_name: str,
    *,
    reply_markup: ReplyKeyboardRemove | None = None,
) -> None:
    await message.reply_text(
        f"Sorry {display_name}, no results were found. Please try again.",
        reply_markup=reply_markup,
    )


async def reply_service_unavailable(
    message: Message,
    display_name: str,
    *,
    reply_markup: ReplyKeyboardRemove | None = None,
) -> None:
    await message.reply_text(
        f"Sorry {display_name}, I'm having some difficulty accessing "
        "the site. Please try again later.",
        reply_markup=reply_markup,
    )


async def reply_choose_language(message: Message) -> None:
    await message.reply_text(
        CHOOSE_LANGUAGE_PROMPT,
        reply_markup=build_buttons(
            list(BIBLE_VERSION_DATA.keys()) + [BACK_TO_COLLECTIONS]
        ),
    )


async def reply_choose_collection(message: Message) -> None:
    await message.reply_text(
        CHOOSE_COLLECTION_PROMPT,
        reply_markup=build_buttons(
            [
                SCRIPTURE_SYSTEMS[system_id].display_name
                for system_id in SCRIPTURE_SYSTEM_ORDER
            ]
        ),
    )


async def reply_choose_lds_version(message: Message) -> None:
    await message.reply_text(
        SELECT_VERSION_PROMPT,
        reply_markup=build_buttons(
            list(SCRIPTURE_SYSTEMS["lds"].version_labels) + [BACK_TO_COLLECTIONS]
        ),
    )


def get_user_default_version(
    context: CallbackContext, scripture_system: ScriptureSystemId
) -> str:
    user_data = require_user_data(context)
    return ensure_text(
        user_data.get(USER_DEFAULT_VERSION_KEY_BY_SYSTEM[scripture_system])
        or DEFAULT_VERSION_BY_SYSTEM[scripture_system]
    ).upper()


def get_bible_default_version(context: CallbackContext) -> str:
    return get_user_default_version(context, "bible")


def get_lds_default_version(context: CallbackContext) -> str:
    return get_user_default_version(context, "lds")


def get_passage_default_version(context: CallbackContext, passage: str | None) -> str:
    scripture_system = get_passage_scripture_system(passage or "") or "bible"
    return get_user_default_version(context, scripture_system)


def set_user_default_version(context: CallbackContext, version: str) -> None:
    user_data = require_user_data(context)
    normalized = version.upper()
    scripture_system = get_version_system(normalized)
    if scripture_system is None:
        message = "Version does not belong to a configured scripture system"
        raise ValueError(f"{message}: {version}")
    user_data[USER_DEFAULT_VERSION_KEY_BY_SYSTEM[scripture_system]] = normalized


def get_identity(update: Update) -> tuple[str, str, bool]:
    chat = require_chat(update)
    user = require_user(update)

    if chat and chat.type == "private":
        name = ensure_text(user.first_name) or "friend"
        return name, name, False

    group_name = ensure_text(chat.title) or "this group"
    sender_name = ensure_text(user.first_name) or group_name
    return sender_name, group_name, True


def is_group_chat(update: Update) -> bool:
    chat = require_chat(update)
    return bool(chat and chat.type != "private")


def replied_to_bot(update: Update) -> bool:
    message = require_message(update)
    if (
        not message
        or not message.reply_to_message
        or not message.reply_to_message.from_user
    ):
        return False
    return message.reply_to_message.from_user.username == update.get_bot().username


async def send_typing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = require_chat(update)
    try:
        await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
    except TelegramError as exc:
        logging.warning("Failed to send typing action for chat %s: %s", chat.id, exc)


async def notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    config: BotConfig = context.application.bot_data["config"]
    if not config.admin_id:
        return
    try:
        await context.bot.send_message(chat_id=config.admin_id, text=text)
    except Exception as exc:
        logging.warning("Failed to notify admin: %s", exc)


async def fetch_passage(
    context: ContextTypes.DEFAULT_TYPE,
    passage: str,
    version: str,
    *,
    inline_details: bool = False,
):
    local_client = context.application.bot_data.get("local_bible_client")
    config: BotConfig = context.application.bot_data["config"]
    if local_client is not None:
        local_response = await local_client.get_passage(
            passage, version, inline_details=inline_details
        )
        if local_response != EMPTY:
            return local_response
        if config.offline_only or local_response is None:
            return local_response

    provider = get_version_provider(version)
    if provider == "sefaria":
        client = context.application.bot_data["sefaria_client"]
    elif provider == "biblecom":
        client = context.application.bot_data["bible_com_client"]
    elif provider == "lds":
        client = context.application.bot_data["lds_client"]
    else:
        client = context.application.bot_data["bible_client"]
    return await client.get_passage(passage, version, inline_details=inline_details)


async def fetch_search_results(
    context: ContextTypes.DEFAULT_TYPE, term: str, start: int = 0
):
    client = context.application.bot_data["bible_client"]
    return await client.get_search_results(term, start=start)


async def reply_with_passage_result(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    passage: str,
    version: str,
    display_name: str,
    *,
    explicit_version: bool = False,
    reply_markup: ReplyKeyboardRemove | None = None,
    silent_failures: bool = False,
) -> None:
    message = require_message(update)
    version = resolve_auto_version(version, passage, explicit_version=explicit_version)
    header_url = build_passage_header_url(passage, version)
    supports_passage, requested_book = version_supports_passage(version, passage)
    if not supports_passage and requested_book:
        if silent_failures:
            return
        await message.reply_text(
            f"Sorry {display_name}, {version} does not appear to include "
            f"{requested_book}. "
            "Try a translation that includes that book.",
            reply_markup=reply_markup,
        )
        return

    await send_typing(update, context)
    response = await fetch_passage(context, passage, version)
    if response == EMPTY:
        if silent_failures:
            return
        await reply_no_results(message, display_name, reply_markup=reply_markup)
        return
    if response is None:
        if silent_failures:
            return
        await reply_service_unavailable(
            message, display_name, reply_markup=reply_markup
        )
        return
    chunks = format_passage_chunks(str(response), header_url=header_url)
    for index, (message_text, entities) in enumerate(chunks):
        await message.reply_text(
            message_text,
            entities=entities,
            reply_markup=reply_markup if index == 0 else None,
        )


async def reply_with_search_results(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    term: str,
    display_name: str,
    *,
    start: int = 0,
    reply_markup: ReplyKeyboardRemove | None = None,
) -> None:
    message = require_message(update)
    user_data = require_user_data(context)
    await send_typing(update, context)
    response = await fetch_search_results(context, term, start=start)
    if response == EMPTY:
        user_data.pop(USER_SEARCH_KEY, None)
        await reply_no_results(message, display_name, reply_markup=reply_markup)
        return
    if response is None:
        await reply_service_unavailable(
            message, display_name, reply_markup=reply_markup
        )
        return

    user_data[USER_SEARCH_KEY] = SearchState(term=term, start=start)
    await message.reply_text(response, reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = require_message(update)
    user_data = require_user_data(context)
    sender_name, group_name, is_group = get_identity(update)
    is_new = not bool(user_data.get(USER_STARTED_KEY))
    user_data[USER_STARTED_KEY] = True

    greeting = (
        f"Hello, friends in {group_name}! Thanks for adding me in!"
        if is_group
        else f"Hello, {sender_name}! Welcome!"
    )
    welcome_text, welcome_entities = build_welcome_message(
        greeting, context.application
    )
    await message.reply_text(
        welcome_text,
        entities=welcome_entities,
        reply_markup=get_try_inline_keyboard(),
    )

    if context.args == ["setdefault"]:
        await reply_choose_collection(message)
        return SETDEFAULT_COLLECTION_STATE

    if is_new:
        if is_group:
            new_alert = f'New group: "{group_name}" via user: {sender_name}'
        else:
            new_alert = f"New user: {sender_name}"
        await notify_admin(context, new_alert)
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = require_message(update)
    display_name, _, _ = get_identity(update)
    await message.reply_text(
        f"Hi {display_name}! Please enter one of the following commands:\n"
        f"{command_list(context.application)}",
        reply_markup=get_try_inline_keyboard(),
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = require_message(update)
    await message.reply_text(
        "Current defaults:\n"
        f"Bible: {format_version_full_label(get_bible_default_version(context))}\n"
        "LDS scriptures: "
        f"{format_version_full_label(get_lds_default_version(context))}\n\n"
        "Use /setdefault to change them."
    )


async def botfamily_verification_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = require_message(update)
    config: BotConfig = context.application.bot_data["config"]
    if config.botfamily_hash:
        await message.reply_text(config.botfamily_hash)
        await notify_admin(context, "Botfamily verified!")
    else:
        await message.reply_text("BOTFAMILY_HASH is not configured.")


async def get_command_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = require_message(update)
    user_data = require_user_data(context)
    raw_text = ensure_text(message.text).strip()
    version, passage, explicit_version = parse_get_request(
        raw_text, get_bible_default_version(context)
    )
    display_name, _, _ = get_identity(update)

    if version is None:
        await message.reply_text(
            f"Sorry {display_name}, I couldn't find that version. "
            "Use /setdefault to view all available versions."
        )
        return ConversationHandler.END

    if passage:
        if not explicit_version:
            version = get_passage_default_version(context, passage)
        if is_book_only_request(passage):
            await message.reply_text(
                f"Sorry {display_name}, please specify at least a chapter. "
                "Whole-book requests are not supported."
            )
            return ConversationHandler.END
        await reply_with_passage_result(
            update,
            context,
            passage,
            version,
            display_name,
            explicit_version=explicit_version,
        )
        return ConversationHandler.END

    user_data[PENDING_GET_VERSION_KEY] = version
    user_data[PENDING_GET_VERSION_EXPLICIT_KEY] = explicit_version
    await message.reply_text(
        f"Which Bible passage do you want to lookup? Version: {version}\n\n"
        "Tip: For faster results, use:\n/get John 3:16\n"
        f"/get John 3:16 {other_version(version)}"
    )
    return GET_PASSAGE_STATE


async def get_conversation_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    message = require_message(update)
    user_data = require_user_data(context)
    version = ensure_text(user_data.pop(PENDING_GET_VERSION_KEY, ""))
    explicit_version = bool(user_data.pop(PENDING_GET_VERSION_EXPLICIT_KEY, False))
    display_name, _, _ = get_identity(update)
    passage = ensure_text(message.text).strip()
    if not explicit_version:
        version = get_passage_default_version(context, passage)
    if is_book_only_request(passage):
        await message.reply_text(
            f"Sorry {display_name}, please specify at least a chapter. "
            "Whole-book requests are not supported.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END
    await reply_with_passage_result(
        update,
        context,
        passage,
        version,
        display_name,
        explicit_version=explicit_version,
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def search_command_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    message = require_message(update)
    raw_text = ensure_text(message.text).strip()
    parts = raw_text.split(maxsplit=1)
    if len(parts) == 1:
        await message.reply_text(
            "Please enter what you wish to search for.\n\n"
            "Tip: For faster results, use:\n/search make disciples\n"
            '/search "love is patient"'
        )
        return SEARCH_STATE

    display_name, _, _ = get_identity(update)
    await reply_with_search_results(
        update, context, parts[1].strip().lower(), display_name
    )
    return ConversationHandler.END


async def search_conversation_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    message = require_message(update)
    display_name, _, _ = get_identity(update)
    await reply_with_search_results(
        update,
        context,
        ensure_text(message.text).strip(),
        display_name,
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def more_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = require_message(update)
    user_data = require_user_data(context)
    display_name, _, _ = get_identity(update)
    search_state = user_data.get(USER_SEARCH_KEY)
    if not isinstance(search_state, SearchState):
        await reply_no_results(message, display_name)
        return
    await reply_with_search_results(
        update,
        context,
        search_state.term,
        display_name,
        start=search_state.start + MAX_SEARCH_RESULTS,
    )


async def setdefault_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = require_message(update)
    raw_text = ensure_text(message.text).strip()
    parts = raw_text.split(maxsplit=1)
    display_name, _, _ = get_identity(update)

    if len(parts) > 1:
        version = resolve_version_code(parts[1].strip())
        if version is None:
            await message.reply_text(
                f"Sorry {display_name}, I couldn't find that version. "
                "Use /setdefault to view all available versions.\n\n"
                f"Current Bible default is {get_bible_default_version(context)}.\n"
                f"Current LDS default is {get_lds_default_version(context)}."
            )
            return ConversationHandler.END
        set_user_default_version(context, version)
        scripture_system = get_version_system(version) or "bible"
        await message.reply_text(
            "Success! "
            f"{get_scripture_system(scripture_system).display_name} default is now "
            f"{format_version_full_label(version)}."
        )
        return ConversationHandler.END

    await reply_choose_collection(message)
    return SETDEFAULT_COLLECTION_STATE


async def start_setdefault_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    message = require_message(update)
    await reply_choose_collection(message)
    return SETDEFAULT_COLLECTION_STATE


async def setdefault_collection_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    message = require_message(update)
    raw_text = ensure_text(message.text).strip()
    if raw_text == SCRIPTURE_SYSTEMS["bible"].display_name:
        await reply_choose_language(message)
        return SETDEFAULT_LANGUAGE_STATE
    if raw_text == SCRIPTURE_SYSTEMS["lds"].display_name:
        await reply_choose_lds_version(message)
        return SETDEFAULT_VERSION_STATE

    await reply_choose_collection(message)
    return SETDEFAULT_COLLECTION_STATE


async def setdefault_language_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    message = require_message(update)
    raw_text = ensure_text(message.text).strip()
    if raw_text == BACK_TO_COLLECTIONS:
        await reply_choose_collection(message)
        return SETDEFAULT_COLLECTION_STATE
    if raw_text not in BIBLE_VERSION_DATA:
        await reply_choose_language(message)
        return SETDEFAULT_LANGUAGE_STATE

    await message.reply_text(
        SELECT_VERSION_PROMPT,
        reply_markup=build_buttons(BIBLE_VERSION_DATA[raw_text] + [BACK_TO_LANGUAGES]),
    )
    return SETDEFAULT_VERSION_STATE


async def setdefault_version_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    message = require_message(update)
    raw_text = ensure_text(message.text).strip()
    if raw_text == BACK_TO_COLLECTIONS:
        await reply_choose_collection(message)
        return SETDEFAULT_COLLECTION_STATE
    if raw_text == BACK_TO_LANGUAGES:
        await reply_choose_language(message)
        return SETDEFAULT_LANGUAGE_STATE

    if raw_text not in VERSION_LOOKUP:
        await message.reply_text(SELECT_VERSION_PROMPT)
        return SETDEFAULT_VERSION_STATE

    version = VERSION_LOOKUP[raw_text]
    set_user_default_version(context, version)
    scripture_system = get_version_system(version)
    assert scripture_system is not None
    await message.reply_text(
        "Success! "
        f"{get_scripture_system(scripture_system).display_name} default is now "
        f"{format_version_full_label(version)}.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel_conversation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    message = require_message(update)
    user_data = require_user_data(context)
    user_data.pop(PENDING_GET_VERSION_KEY, None)
    user_data.pop(PENDING_GET_VERSION_EXPLICIT_KEY, None)
    await message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def handle_inline_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    inline_query = update.inline_query
    if inline_query is None:
        return

    query = ensure_text(inline_query.query).strip()
    default_version = get_bible_default_version(context)
    if not query:
        await inline_query.answer(
            [],
            cache_time=0,
            button=build_inline_results_button(default_version),
        )
        return

    words = query.split()
    resolved_version = resolve_version_code(words[-1]) if len(words) > 1 else None
    if resolved_version is not None:
        passage = " ".join(words[:-1])
        version = resolved_version
        explicit_version = True
    else:
        passage = query
        version = get_passage_default_version(context, passage)
        explicit_version = False

    version = resolve_auto_version(version, passage, explicit_version=explicit_version)

    supports_passage, _ = version_supports_passage(version, passage)
    if not supports_passage:
        await inline_query.answer(
            [],
            cache_time=0,
            button=build_inline_results_button(default_version),
        )
        return

    response = await fetch_passage(context, passage, version, inline_details=True)
    if response in (None, EMPTY):
        await inline_query.answer(
            [],
            cache_time=0,
            button=build_inline_results_button(default_version),
        )
        return

    inline_result = response
    assert isinstance(inline_result, InlinePassageResult)
    header_url = inline_result.header_url or build_passage_header_url(passage, version)
    results = [
        InlineQueryResultArticle(
            id=inline_result.result_id,
            title=inline_result.title,
            description=inline_result.description,
            input_message_content=build_input_message_content(
                inline_result.passage, header_url=header_url
            ),
        )
    ]
    await inline_query.answer(
        results,
        cache_time=0,
        button=build_inline_results_button(default_version),
    )


async def handle_new_members(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = require_message(update)
    if not message.new_chat_members:
        return

    bot_username = context.application.bot.username
    for member in message.new_chat_members:
        if member.username == bot_username:
            await start(update, context)
            return


async def linked_passage_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = require_message(update)
    raw_text = ensure_text(message.text).strip()
    display_name, _, _ = get_identity(update)
    reference = raw_text[1:]
    bot_handle = build_bot_handle(context.application)
    if reference.endswith(bot_handle):
        reference = reference[: -len(bot_handle)]
    passage = decode_linked_reference(reference)
    await reply_with_passage_result(
        update,
        context,
        passage,
        get_passage_default_version(context, passage),
        display_name,
        explicit_version=False,
    )


async def quick_lookup_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = require_message(update)
    raw_text = ensure_text(message.text).strip()
    lowered = raw_text.lower()
    bot_handle = build_bot_handle(context.application).lower()

    if (
        is_group_chat(update)
        and bot_handle not in lowered
        and not replied_to_bot(update)
    ):
        logging.info("Ignoring non-directed group message")
        return

    display_name, _, _ = get_identity(update)
    to_lookup = lowered.replace(bot_handle, "").replace("revelations", "revelation")
    version, to_lookup, explicit_version = parse_reference_version_query(
        to_lookup, get_bible_default_version(context)
    )
    refs = extract_refs(to_lookup)
    if refs:
        passage = build_passage_from_ref(refs[0])
        if not explicit_version:
            version = get_passage_default_version(context, passage)
        await reply_with_passage_result(
            update,
            context,
            passage,
            version,
            display_name,
            explicit_version=explicit_version,
            reply_markup=ReplyKeyboardRemove(),
            silent_failures=True,
        )
        return

    canonical_passage = canonicalize_reference(to_lookup)
    if canonical_passage and find_requested_book(canonical_passage):
        if not explicit_version:
            version = get_passage_default_version(context, canonical_passage)
        await reply_with_passage_result(
            update,
            context,
            canonical_passage,
            version,
            display_name,
            explicit_version=explicit_version,
            reply_markup=ReplyKeyboardRemove(),
            silent_failures=True,
        )
        return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.exception(
        "Unhandled error while processing update %s", update, exc_info=context.error
    )
