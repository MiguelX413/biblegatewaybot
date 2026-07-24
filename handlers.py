import logging

from scriptures import extract as extract_refs
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ChatAction, ParseMode
from telegram.ext import CallbackContext, ContextTypes, ConversationHandler

from config import BotConfig
from parsing import (
    build_bot_handle,
    build_passage_from_ref,
    canonicalize_reference,
    command_list,
    decode_linked_reference,
    ensure_text,
    format_passage_html,
    other_version,
    parse_get_request,
    version_supports_passage,
    get_version_provider,
)
from state import (
    BACK_TO_LANGUAGES,
    DEFAULT_VERSION,
    EMPTY,
    GET_PASSAGE_STATE,
    MAX_SEARCH_RESULTS,
    SEARCH_STATE,
    SETDEFAULT_LANGUAGE_STATE,
    SETDEFAULT_VERSION_STATE,
    USER_SEARCH_KEY,
    USER_STARTED_KEY,
    USER_VERSION_KEY,
    SearchState,
)
from versions import VERSION_DATA, VERSION_LOOKUP, VERSIONS


def get_try_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Try inline mode", switch_inline_query_current_chat="john 3:16 nlt"
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


def get_default_version(context: CallbackContext) -> str:
    return ensure_text(
        context.user_data.get(USER_VERSION_KEY) or DEFAULT_VERSION
    ).upper()


def set_default_version(context: CallbackContext, version: str) -> None:
    context.user_data[USER_VERSION_KEY] = version.upper()


def get_identity(update: Update) -> tuple[str, str, bool]:
    chat = update.effective_chat
    user = update.effective_user

    if chat and chat.type == "private":
        name = ensure_text(user.first_name) or "friend"
        return name, name, False

    group_name = ensure_text(chat.title) or "this group"
    sender_name = ensure_text(user.first_name) or group_name
    return sender_name, group_name, True


def is_group_chat(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.type != "private")


def replied_to_bot(update: Update) -> bool:
    message = update.effective_message
    if (
        not message
        or not message.reply_to_message
        or not message.reply_to_message.from_user
    ):
        return False
    return message.reply_to_message.from_user.username == update.get_bot().username


async def send_typing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )


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
    reply_markup: ReplyKeyboardRemove | None = None,
) -> None:
    supports_passage, requested_book = version_supports_passage(version, passage)
    if not supports_passage and requested_book:
        await update.effective_message.reply_text(
            f"Sorry {display_name}, {version} does not appear to include {requested_book}. "
            "Try a translation that includes that book.",
            reply_markup=reply_markup,
        )
        return

    await send_typing(update, context)
    response = await fetch_passage(context, passage, version)
    if response == EMPTY:
        await update.effective_message.reply_text(
            f"Sorry {display_name}, no results were found. Please try again.",
            reply_markup=reply_markup,
        )
        return
    if response is None:
        await update.effective_message.reply_text(
            f"Sorry {display_name}, I'm having some difficulty accessing the site. Please try again later.",
            reply_markup=reply_markup,
        )
        return
    await update.effective_message.reply_text(
        format_passage_html(str(response)),
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
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
    await send_typing(update, context)
    response = await fetch_search_results(context, term, start=start)
    if response == EMPTY:
        context.user_data.pop(USER_SEARCH_KEY, None)
        await update.effective_message.reply_text(
            f"Sorry {display_name}, no results were found. Please try again.",
            reply_markup=reply_markup,
        )
        return
    if response is None:
        await update.effective_message.reply_text(
            f"Sorry {display_name}, I'm having some difficulty accessing the site. Please try again later.",
            reply_markup=reply_markup,
        )
        return

    context.user_data[USER_SEARCH_KEY] = SearchState(term=term, start=start)
    await update.effective_message.reply_text(response, reply_markup=reply_markup)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sender_name, group_name, is_group = get_identity(update)
    is_new = not bool(context.user_data.get(USER_STARTED_KEY))
    context.user_data[USER_STARTED_KEY] = True

    greeting = (
        f"Hello, friends in {group_name}! Thanks for adding me in!"
        if is_group
        else f"Hello, {sender_name}! Welcome!"
    )
    await update.effective_message.reply_text(
        f"{greeting} This bot can fetch Bible passages from biblegateway.com.\n\n"
        f"To get started, enter one of the following commands:\n{command_list(context.application)}",
        reply_markup=get_try_inline_keyboard(),
    )

    if context.args == ["setdefault"]:
        await update.effective_message.reply_text(
            "Choose a language:", reply_markup=build_buttons(list(VERSION_DATA.keys()))
        )
        return SETDEFAULT_LANGUAGE_STATE

    if is_new:
        if is_group:
            new_alert = f'New group: "{group_name}" via user: {sender_name}'
        else:
            new_alert = f"New user: {sender_name}"
        await notify_admin(context, new_alert)
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    display_name, _, _ = get_identity(update)
    await update.effective_message.reply_text(
        f"Hi {display_name}! Please enter one of the following commands:\n{command_list(context.application)}",
        reply_markup=get_try_inline_keyboard(),
    )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        f"Current default version is {get_default_version(context)}. Use /setdefault to change it."
    )


async def botfamily_verification_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    config: BotConfig = context.application.bot_data["config"]
    if config.botfamily_hash:
        await update.effective_message.reply_text(config.botfamily_hash)
        await notify_admin(context, "Botfamily verified!")
    else:
        await update.effective_message.reply_text("BOTFAMILY_HASH is not configured.")


async def get_command_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw_text = ensure_text(update.effective_message.text).strip()
    version, passage = parse_get_request(raw_text, get_default_version(context))
    display_name, _, _ = get_identity(update)

    if version is None:
        await update.effective_message.reply_text(
            f"Sorry {display_name}, I couldn't find that version. Use /setdefault to view all available versions."
        )
        return ConversationHandler.END

    if passage:
        await reply_with_passage_result(update, context, passage, version, display_name)
        return ConversationHandler.END

    context.user_data["pending_get_version"] = version
    await update.effective_message.reply_text(
        "Which Bible passage do you want to lookup? Version: {}\n\n"
        "Tip: For faster results, use:\n/get John 3:16\n/get{} John 3:16".format(
            version, other_version(version)
        )
    )
    return GET_PASSAGE_STATE


async def get_conversation_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    version = ensure_text(
        context.user_data.pop("pending_get_version", get_default_version(context))
    )
    display_name, _, _ = get_identity(update)
    await reply_with_passage_result(
        update,
        context,
        ensure_text(update.effective_message.text).strip(),
        version,
        display_name,
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def search_command_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    raw_text = ensure_text(update.effective_message.text).strip()
    parts = raw_text.split(maxsplit=1)
    if len(parts) == 1:
        await update.effective_message.reply_text(
            "Please enter what you wish to search for.\n\n"
            'Tip: For faster results, use:\n/search make disciples\n/search "love is patient"'
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
    display_name, _, _ = get_identity(update)
    await reply_with_search_results(
        update,
        context,
        ensure_text(update.effective_message.text).strip(),
        display_name,
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def more_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    display_name, _, _ = get_identity(update)
    search_state = context.user_data.get(USER_SEARCH_KEY)
    if not isinstance(search_state, SearchState):
        await update.effective_message.reply_text(
            f"Sorry {display_name}, no results were found. Please try again."
        )
        return
    await reply_with_search_results(
        update,
        context,
        search_state.term,
        display_name,
        start=search_state.start + MAX_SEARCH_RESULTS,
    )


async def setdefault_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw_text = ensure_text(update.effective_message.text).strip()
    parts = raw_text.split(maxsplit=1)
    display_name, _, _ = get_identity(update)

    if len(parts) > 1:
        version = parts[1].strip().upper()
        if version not in VERSIONS:
            await update.effective_message.reply_text(
                "Sorry {}, I couldn't find that version. Use /setdefault to view all available versions.\n\n"
                "Current default is {}.".format(
                    display_name, get_default_version(context)
                )
            )
            return ConversationHandler.END
        set_default_version(context, version)
        await update.effective_message.reply_text(
            f"Success! Default version is now {version}."
        )
        return ConversationHandler.END

    await update.effective_message.reply_text(
        "Choose a language:", reply_markup=build_buttons(list(VERSION_DATA.keys()))
    )
    return SETDEFAULT_LANGUAGE_STATE


async def start_setdefault_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.effective_message.reply_text(
        "Choose a language:", reply_markup=build_buttons(list(VERSION_DATA.keys()))
    )
    return SETDEFAULT_LANGUAGE_STATE


async def setdefault_language_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    raw_text = ensure_text(update.effective_message.text).strip()
    if raw_text not in VERSION_DATA:
        await update.effective_message.reply_text(
            "Choose a language:", reply_markup=build_buttons(list(VERSION_DATA.keys()))
        )
        return SETDEFAULT_LANGUAGE_STATE

    await update.effective_message.reply_text(
        "Select a version:",
        reply_markup=build_buttons(VERSION_DATA[raw_text] + [BACK_TO_LANGUAGES]),
    )
    return SETDEFAULT_VERSION_STATE


async def setdefault_version_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    raw_text = ensure_text(update.effective_message.text).strip()
    if raw_text == BACK_TO_LANGUAGES:
        await update.effective_message.reply_text(
            "Choose a language:", reply_markup=build_buttons(list(VERSION_DATA.keys()))
        )
        return SETDEFAULT_LANGUAGE_STATE

    if raw_text not in VERSION_LOOKUP:
        await update.effective_message.reply_text("Select a version:")
        return SETDEFAULT_VERSION_STATE

    version = VERSION_LOOKUP[raw_text]
    set_default_version(context, version)
    await update.effective_message.reply_text(
        f"Success! Default version is now {version}.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def cancel_conversation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data.pop("pending_get_version", None)
    await update.effective_message.reply_text(
        "Cancelled.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def handle_inline_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    inline_query = update.inline_query
    if inline_query is None:
        return

    query = ensure_text(inline_query.query).strip()
    default_version = get_default_version(context)
    if not query:
        await inline_query.answer(
            [],
            cache_time=0,
            switch_pm_text=f"Default version: {default_version}",
            switch_pm_parameter="setdefault",
        )
        return

    words = query.split()
    if len(words) > 1 and words[-1].upper() in VERSIONS:
        passage = " ".join(words[:-1])
        version = words[-1].upper()
    else:
        passage = query
        version = default_version

    supports_passage, _ = version_supports_passage(version, passage)
    if not supports_passage:
        await inline_query.answer(
            [],
            cache_time=0,
            switch_pm_text=f"Default version: {default_version}",
            switch_pm_parameter="setdefault",
        )
        return

    response = await fetch_passage(context, passage, version, inline_details=True)
    if response in (None, EMPTY):
        await inline_query.answer(
            [],
            cache_time=0,
            switch_pm_text=f"Default version: {default_version}",
            switch_pm_parameter="setdefault",
        )
        return

    inline_result = response
    assert isinstance(inline_result, InlinePassageResult)
    results = [
        InlineQueryResultArticle(
            id=inline_result.result_id,
            title=inline_result.title,
            description=inline_result.description,
            input_message_content=InputTextMessageContent(
                format_passage_html(inline_result.passage),
                parse_mode=ParseMode.HTML,
            ),
        )
    ]
    await inline_query.answer(
        results,
        cache_time=0,
        switch_pm_text=f"Default version: {default_version}",
        switch_pm_parameter="setdefault",
    )


async def handle_new_members(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.effective_message
    if not message or not message.new_chat_members:
        return

    bot_username = context.application.bot.username
    for member in message.new_chat_members:
        if member.username == bot_username:
            await start(update, context)
            return


async def linked_passage_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    raw_text = ensure_text(update.effective_message.text).strip()
    display_name, _, _ = get_identity(update)
    reference = raw_text[1:]
    bot_handle = build_bot_handle(context.application)
    if reference.endswith(bot_handle):
        reference = reference[: -len(bot_handle)]
    passage = decode_linked_reference(reference)
    await reply_with_passage_result(
        update, context, passage, get_default_version(context), display_name
    )


async def quick_lookup_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    raw_text = ensure_text(update.effective_message.text).strip()
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
    refs = extract_refs(to_lookup)
    if refs:
        passage = build_passage_from_ref(refs[0])
        await reply_with_passage_result(
            update,
            context,
            passage,
            get_default_version(context),
            display_name,
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    canonical_passage = canonicalize_reference(to_lookup)
    if canonical_passage and find_requested_book(canonical_passage):
        await reply_with_passage_result(
            update,
            context,
            canonical_passage,
            get_default_version(context),
            display_name,
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await update.effective_message.reply_text(
        f"Sorry {display_name}, I couldn't understand that. Please enter one of the following commands:\n"
        f"{command_list(context.application)}",
        reply_markup=get_try_inline_keyboard(),
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.exception(
        "Unhandled error while processing update %s", update, exc_info=context.error
    )
