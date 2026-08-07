import hashlib
import logging
import re
import subprocess
import time
from collections.abc import Sequence
from functools import lru_cache
from typing import Any

from scriptures import extract as extract_refs
from telegram import (
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InlineQueryResultsButton,
    InputTextMessageContent,
    LinkPreviewOptions,
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
    VersionSelection,
    batch_parallel_passage_entities,
    build_bot_handle,
    build_passage_from_ref,
    canonicalize_reference,
    command_list,
    decode_linked_reference,
    ensure_text,
    find_requested_book,
    format_inline_parallel_passage_entities,
    format_passage_chunks,
    format_version_selection,
    get_passage_scripture_system,
    get_version_provider,
    is_book_only_request,
    other_version,
    parse_get_request,
    parse_reference_version_query,
    parse_version_selection,
    resolve_auto_version,
    version_supports_passage,
)
from quran import QuranReference
from services.alquran_cloud import build_quran_passage_url
from services.bible_com import build_bible_com_passage_url
from services.bible_gateway import build_bible_gateway_passage_url
from services.lds_scriptures import build_lds_passage_url
from services.local_bible import get_local_passage_url
from services.sefaria import build_sefaria_passage_url, resolve_sefaria_version_query
from state import (
    BACK_TO_COLLECTIONS,
    BACK_TO_LANGUAGES,
    CHAT_LINK_EMBEDS_ENABLED_KEY,
    CHAT_REQUEST_TIMESTAMPS_KEY,
    CHOOSE_COLLECTION_PROMPT,
    CHOOSE_LANGUAGE_PROMPT,
    DEFAULT_VERSION_BY_SYSTEM,
    EMPTY,
    GET_PASSAGE_STATE,
    MAX_SEARCH_RESULTS,
    PENDING_GET_VERSION_EXPLICIT_KEY,
    PENDING_GET_VERSION_KEY,
    PENDING_SETDEFAULT_SYSTEM_KEY,
    SEARCH_STATE,
    SELECT_VERSION_PROMPT,
    SETDEFAULT_COLLECTION_STATE,
    SETDEFAULT_LANGUAGE_STATE,
    SETDEFAULT_VERSION_STATE,
    USER_DEFAULT_VERSION_KEY_BY_SYSTEM,
    USER_INLINE_LINK_EMBEDS_ENABLED_KEY,
    USER_REQUEST_TIMESTAMPS_KEY,
    USER_SEARCH_KEY,
    USER_STARTED_KEY,
    InlinePassageResult,
    SearchState,
)
from versions import (
    VERSION_CATALOG,
    VERSION_LOOKUP,
    ScriptureSystemId,
    VersionProvider,
    format_version_full_label,
    get_scripture_system,
    get_sefaria_version_config,
    get_version_system,
)

MAX_PASSAGE_RESPONSE_MESSAGES = 4
REQUEST_THROTTLE_WINDOW_SECONDS = 10.0
REQUEST_THROTTLE_MIN_INTERVAL_SECONDS = 1.0
MAX_USER_REQUESTS_PER_WINDOW = 4
MAX_CHAT_REQUESTS_PER_WINDOW = 10
GITHUB_REMOTE_PATTERN = re.compile(
    r"^(?:git@github\.com:|https://github\.com/)(?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$"
)


def build_input_message_content(
    passages: Sequence[tuple[str, str | None]],
    *,
    link_preview_options: LinkPreviewOptions | None = None,
) -> InputTextMessageContent:
    message_text, entities = format_inline_parallel_passage_entities(passages)
    return InputTextMessageContent(
        message_text=message_text,
        entities=entities,
        link_preview_options=link_preview_options,
    )


def build_inline_result_id(result_ids: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for result_id in result_ids:
        encoded = result_id.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def get_git_version_details() -> tuple[str, str, str | None]:
    try:
        full_sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        short_sha_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        full_sha = full_sha_result.stdout.strip()
        short_sha = short_sha_result.stdout.strip()
    except OSError, subprocess.SubprocessError:
        return "unknown", "unknown", None

    if not full_sha or not short_sha:
        return "unknown", "unknown", None

    try:
        remote_result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
    except OSError, subprocess.SubprocessError:
        return short_sha, full_sha, None

    remote_url = remote_result.stdout.strip()
    match = GITHUB_REMOTE_PATTERN.match(remote_url)
    if match is None:
        return short_sha, full_sha, None
    owner = match.group("owner")
    repo = match.group("repo")
    return short_sha, full_sha, f"https://github.com/{owner}/{repo}/commit/{full_sha}"


def build_passage_header_url(passage: str, version: str) -> str | None:
    provider = get_version_provider(version)
    if provider is VersionProvider.BIBLE_GATEWAY:
        return build_bible_gateway_passage_url(passage, version)
    if provider is VersionProvider.BIBLE_COM:
        return build_bible_com_passage_url(passage, version)
    if provider is VersionProvider.QURAN:
        return build_quran_passage_url(passage, version)
    if provider is VersionProvider.SEFARIA:
        version_query = resolve_sefaria_version_query(
            passage, get_sefaria_version_config(version)
        )
        return build_sefaria_passage_url(passage, version, version_query)
    if provider is VersionProvider.LDS:
        return build_lds_passage_url(passage, version)
    if provider is VersionProvider.LOCAL:
        return get_local_passage_url(passage, version)
    return None


def build_welcome_message(
    greeting: str, application: Any
) -> tuple[str, list[MessageEntity]]:
    source_links = [
        ("BibleGateway", "https://biblegateway.com"),
        ("Bible.com", "https://bible.com"),
        ("Sefaria", "https://sefaria.org"),
        ("LDS scriptures", "https://churchofjesuschrist.org/study/scriptures"),
        ("AlQuran Cloud", "https://alquran.cloud"),
    ]
    sources_text = ", ".join(label for label, _ in source_links[:-1])
    sources_text += f", and {source_links[-1][0]}"
    welcome_command_list = command_list(
        application, include_admin_commands=False
    ).replace("/search <keyword>\n", "")
    welcome_command_list = welcome_command_list.replace(
        "/search the greatest commandment\n", ""
    )
    message_text = (
        f"{greeting} This bot can fetch scripture passages from {sources_text}, "
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


def require_chat_data(context: CallbackContext[Any, Any, Any, Any]) -> dict[Any, Any]:
    chat_data = context.chat_data
    assert chat_data is not None
    return chat_data


def get_link_preview_options(
    context: CallbackContext[Any, Any, Any, Any],
) -> LinkPreviewOptions:
    chat_data = require_chat_data(context)
    enabled = bool(chat_data.get(CHAT_LINK_EMBEDS_ENABLED_KEY, False))
    return LinkPreviewOptions(is_disabled=not enabled)


def get_inline_link_preview_options(
    context: CallbackContext[Any, Any, Any, Any], user_id: int
) -> LinkPreviewOptions:
    user_data = require_user_data(context)
    enabled = user_data.get(USER_INLINE_LINK_EMBEDS_ENABLED_KEY)
    if enabled is None:
        # A private chat uses its user's ID as its chat ID. Read the existing
        # chat-level setting once so DMs configured before inline support keep
        # their preference too.
        direct_message_data = context.application.chat_data.get(user_id, {})
        enabled = direct_message_data.get(CHAT_LINK_EMBEDS_ENABLED_KEY, False)
        user_data[USER_INLINE_LINK_EMBEDS_ENABLED_KEY] = enabled
    return LinkPreviewOptions(is_disabled=not enabled)


def build_inline_results_button(
    default_selection: VersionSelection,
) -> InlineQueryResultsButton:
    return InlineQueryResultsButton(
        text=f"Default versions: {format_version_selection(default_selection)}",
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


def _prune_request_timestamps(
    timestamps: list[float], *, now: float, window_seconds: float
) -> list[float]:
    return [timestamp for timestamp in timestamps if now - timestamp < window_seconds]


def get_request_throttle_retry_after(
    user_data: dict[Any, Any],
    chat_data: dict[Any, Any] | None,
    *,
    now: float,
) -> float | None:
    user_timestamps = _prune_request_timestamps(
        list(user_data.get(USER_REQUEST_TIMESTAMPS_KEY, ())),
        now=now,
        window_seconds=REQUEST_THROTTLE_WINDOW_SECONDS,
    )
    user_data[USER_REQUEST_TIMESTAMPS_KEY] = user_timestamps
    if user_timestamps:
        retry_after = REQUEST_THROTTLE_MIN_INTERVAL_SECONDS - (
            now - user_timestamps[-1]
        )
        if retry_after > 0:
            return retry_after
    if len(user_timestamps) >= MAX_USER_REQUESTS_PER_WINDOW:
        return REQUEST_THROTTLE_WINDOW_SECONDS - (now - user_timestamps[0])

    if chat_data is None:
        return None

    chat_timestamps = _prune_request_timestamps(
        list(chat_data.get(CHAT_REQUEST_TIMESTAMPS_KEY, ())),
        now=now,
        window_seconds=REQUEST_THROTTLE_WINDOW_SECONDS,
    )
    chat_data[CHAT_REQUEST_TIMESTAMPS_KEY] = chat_timestamps
    if len(chat_timestamps) >= MAX_CHAT_REQUESTS_PER_WINDOW:
        return REQUEST_THROTTLE_WINDOW_SECONDS - (now - chat_timestamps[0])
    return None


def record_request_timestamp(
    user_data: dict[Any, Any], chat_data: dict[Any, Any] | None, *, now: float
) -> None:
    user_timestamps = list(user_data.get(USER_REQUEST_TIMESTAMPS_KEY, ()))
    user_timestamps.append(now)
    user_data[USER_REQUEST_TIMESTAMPS_KEY] = user_timestamps

    if chat_data is None:
        return
    chat_timestamps = list(chat_data.get(CHAT_REQUEST_TIMESTAMPS_KEY, ()))
    chat_timestamps.append(now)
    chat_data[CHAT_REQUEST_TIMESTAMPS_KEY] = chat_timestamps


def is_admin_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    config: BotConfig = context.application.bot_data["config"]
    admin_ids = config.admin_ids
    if not admin_ids:
        return False
    user = update.effective_user
    return user is not None and user.id in admin_ids


async def enforce_request_throttle(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    silent: bool = False,
) -> bool:
    if is_admin_user(update, context):
        return True

    user_data = require_user_data(context)
    chat_data = context.chat_data
    now = time.monotonic()
    retry_after = get_request_throttle_retry_after(user_data, chat_data, now=now)
    if retry_after is not None:
        if not silent:
            message = require_message(update)
            await message.reply_text(
                "Too many requests too quickly. "
                f"Please wait about {max(1, round(retry_after))} seconds and try again."
            )
        return False

    record_request_timestamp(user_data, chat_data, now=now)
    return True


def count_passage_result_messages(
    passage_results: Sequence[tuple[str, str | None] | tuple[str, str | None, str]],
) -> int:
    normalized_results = [
        (result[0], result[1], result[2] if len(result) == 3 else "")
        for result in passage_results
    ]
    if len(passage_results) > 1:
        return len(
            batch_parallel_passage_entities(
                [
                    (response, header_url)
                    for response, header_url, _ in normalized_results
                ]
            )
        )
    return sum(
        len(format_passage_chunks(response, header_url=header_url))
        for response, header_url, _ in normalized_results
    )


def resolve_chunk_header_url(
    chunk_reference: str | QuranReference | None, version: str
) -> str | None:
    if chunk_reference is None:
        return None
    if get_version_provider(version) is VersionProvider.QURAN:
        return build_quran_passage_url(chunk_reference, version)
    if isinstance(chunk_reference, str):
        return build_passage_header_url(chunk_reference, version)
    return None


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


async def reply_choose_language(
    message: Message, scripture_system: ScriptureSystemId
) -> None:
    system = VERSION_CATALOG.systems_by_id[scripture_system]
    await message.reply_text(
        CHOOSE_LANGUAGE_PROMPT,
        reply_markup=build_buttons(
            list(system.language_group_labels) + [BACK_TO_COLLECTIONS]
        ),
    )


async def reply_choose_collection(message: Message) -> None:
    await message.reply_text(
        CHOOSE_COLLECTION_PROMPT,
        reply_markup=build_buttons(
            [
                VERSION_CATALOG.systems_by_id[system_id].display_name
                for system_id in VERSION_CATALOG.system_ids
            ]
        ),
    )


def get_user_default_version(
    context: CallbackContext, scripture_system: ScriptureSystemId
) -> VersionSelection:
    user_data = require_user_data(context)
    stored_default = user_data.get(
        USER_DEFAULT_VERSION_KEY_BY_SYSTEM[scripture_system],
        DEFAULT_VERSION_BY_SYSTEM[scripture_system],
    )
    if isinstance(stored_default, str):
        return ((stored_default.upper(),),)
    if isinstance(stored_default, tuple):
        return stored_default
    fallback_default = DEFAULT_VERSION_BY_SYSTEM[scripture_system]
    if isinstance(fallback_default, str):
        return ((fallback_default,),)
    return fallback_default


def get_bible_default_version(context: CallbackContext) -> VersionSelection:
    return get_user_default_version(context, ScriptureSystemId.BIBLE)


def get_lds_default_version(context: CallbackContext) -> VersionSelection:
    return get_user_default_version(context, ScriptureSystemId.LDS)


def get_quran_default_version(context: CallbackContext) -> VersionSelection:
    return get_user_default_version(context, ScriptureSystemId.QURAN)


def get_passage_default_version(
    context: CallbackContext, passage: str | None
) -> VersionSelection:
    scripture_system = (
        get_passage_scripture_system(passage or "") or ScriptureSystemId.BIBLE
    )
    return get_user_default_version(context, scripture_system)


def set_user_default_version(
    context: CallbackContext, selection: VersionSelection
) -> ScriptureSystemId:
    user_data = require_user_data(context)
    systems = {
        get_version_system(version)
        for candidates in selection
        for version in candidates
    }
    if len(systems) != 1 or None in systems:
        raise ValueError("Default versions must belong to one scripture system")
    scripture_system = systems.pop()
    assert scripture_system is not None
    user_data[USER_DEFAULT_VERSION_KEY_BY_SYSTEM[scripture_system]] = selection
    return scripture_system


def format_default_selection(selection: VersionSelection) -> str:
    return " & ".join(
        " → ".join(format_version_full_label(version) for version in candidates)
        for candidates in selection
    )


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
    if not config.admin_ids:
        return
    for admin_id in config.admin_ids:
        try:
            await context.bot.send_message(chat_id=admin_id, text=text)
        except Exception as exc:
            logging.warning("Failed to notify admin %s: %s", admin_id, exc)


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
    if provider is VersionProvider.SEFARIA:
        client = context.application.bot_data["sefaria_client"]
    elif provider is VersionProvider.BIBLE_COM:
        client = context.application.bot_data["bible_com_client"]
    elif provider is VersionProvider.QURAN:
        client = context.application.bot_data["quran_client"]
    elif provider is VersionProvider.LDS:
        client = context.application.bot_data["lds_client"]
    else:
        client = context.application.bot_data["bible_client"]
    return await client.get_passage(passage, version, inline_details=inline_details)


async def fetch_search_results(
    context: ContextTypes.DEFAULT_TYPE, term: str, start: int = 0
):
    client = context.application.bot_data["bible_client"]
    return await client.get_search_results(term, start=start)


def resolve_version_selection(
    selection: VersionSelection, passage: str, *, explicit_version: bool
) -> VersionSelection:
    if explicit_version:
        return selection
    return tuple(
        (
            (resolve_auto_version(candidates[0], passage),)
            if len(candidates) == 1
            else candidates
        )
        for candidates in selection
    )


async def fetch_version_group(
    context: ContextTypes.DEFAULT_TYPE,
    passage: str,
    candidates: tuple[str, ...],
    *,
    inline_details: bool = False,
) -> tuple[str, str | InlinePassageResult] | None:
    for version in candidates:
        supports_passage, _ = version_supports_passage(version, passage)
        if not supports_passage:
            continue
        response = await fetch_passage(
            context, passage, version, inline_details=inline_details
        )
        if response not in (None, EMPTY):
            return version, response
    return None


async def reply_with_passage_result(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    passage: str,
    selection: VersionSelection,
    display_name: str,
    *,
    explicit_version: bool = False,
    reply_markup: ReplyKeyboardRemove | None = None,
    silent_failures: bool = False,
) -> None:
    message = require_message(update)
    selection = resolve_version_selection(
        selection, passage, explicit_version=explicit_version
    )
    await send_typing(update, context)
    passage_results: list[tuple[str, str | None, str]] = []
    for candidates in selection:
        result = await fetch_version_group(context, passage, candidates)
        if result is None:
            continue
        version, response = result
        header_url = build_passage_header_url(passage, version)
        passage_results.append((str(response), header_url, version))

    if (
        passage_results
        and count_passage_result_messages(passage_results)
        > MAX_PASSAGE_RESPONSE_MESSAGES
    ):
        logging.info(
            "Refusing oversized passage request %r for user %s: exceeds %s messages",
            passage,
            require_user(update).id,
            MAX_PASSAGE_RESPONSE_MESSAGES,
        )
        await message.reply_text(
            f"Sorry {display_name}, that request is too large to send safely. "
            "Please narrow the range."
        )
        return

    if len(passage_results) > 1:
        combined_messages = batch_parallel_passage_entities(
            [(response, header_url) for response, header_url, _ in passage_results]
        )
        if combined_messages:
            for index, (message_text, entities) in enumerate(combined_messages):
                await message.reply_text(
                    message_text,
                    entities=entities,
                    reply_markup=reply_markup if index == 0 else None,
                    link_preview_options=get_link_preview_options(context),
                )
            return

    sent_response = False
    for response, header_url, version in passage_results:

        def chunk_header_url_resolver(
            chunk_reference: str | QuranReference | None,
        ) -> str | None:
            return resolve_chunk_header_url(chunk_reference, version)

        chunks = format_passage_chunks(
            response,
            header_url=header_url,
            chunk_header_url_resolver=chunk_header_url_resolver,
        )
        for index, (message_text, entities) in enumerate(chunks):
            await message.reply_text(
                message_text,
                entities=entities,
                reply_markup=reply_markup if not sent_response and index == 0 else None,
                link_preview_options=get_link_preview_options(context),
            )
        sent_response = True

    if sent_response or silent_failures:
        return
    await reply_no_results(message, display_name, reply_markup=reply_markup)


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
        link_preview_options=get_link_preview_options(context),
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
    command_text = command_list(
        context.application,
        include_admin_commands=is_admin_user(update, context),
    )
    await message.reply_text(
        f"Hi {display_name}! Please enter one of the following commands:\n"
        f"{command_text}",
        reply_markup=get_try_inline_keyboard(),
    )


async def version_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    message = require_message(update)
    short_sha, _, github_url = get_git_version_details()
    text = f"Version: {short_sha}"
    if github_url is None:
        await message.reply_text(text)
        return

    sha_offset = len("Version: ")
    entities = [
        MessageEntity(
            type=MessageEntityType.TEXT_LINK,
            offset=sha_offset,
            length=len(short_sha),
            url=github_url,
        ),
    ]
    utf16_entities = MessageEntity.adjust_message_entities_to_utf_16(text, entities)
    await message.reply_text(text, entities=list(utf16_entities))


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = require_message(update)
    preview_options = get_link_preview_options(context)
    link_embeds = "enabled" if not preview_options.is_disabled else "disabled"
    await message.reply_text(
        "Current defaults:\n"
        f"Bible: {format_default_selection(get_bible_default_version(context))}\n"
        "LDS scriptures: "
        f"{format_default_selection(get_lds_default_version(context))}\n"
        f"Qurʾan: {format_default_selection(get_quran_default_version(context))}\n\n"
        "Use /setdefault to change them.\n"
        f"Link embeds: {link_embeds} (/linkembeds off|on)"
    )


async def link_embeds_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = require_message(update)
    chat_data = require_chat_data(context)
    arguments = context.args or []
    argument = arguments[0].lower() if len(arguments) == 1 else ""

    if argument in {"on", "enable", "enabled"}:
        chat_data[CHAT_LINK_EMBEDS_ENABLED_KEY] = True
        if require_chat(update).type == "private":
            require_user_data(context)[USER_INLINE_LINK_EMBEDS_ENABLED_KEY] = True
        await message.reply_text("Link embeds are now enabled for this chat.")
        return
    if argument in {"off", "disable", "disabled"}:
        chat_data[CHAT_LINK_EMBEDS_ENABLED_KEY] = False
        if require_chat(update).type == "private":
            require_user_data(context)[USER_INLINE_LINK_EMBEDS_ENABLED_KEY] = False
        await message.reply_text("Link embeds are now disabled for this chat.")
        return

    enabled = bool(chat_data.get(CHAT_LINK_EMBEDS_ENABLED_KEY, False))
    status = "enabled" if enabled else "disabled"
    await message.reply_text(
        f"Link embeds are currently {status} for this chat.\n"
        "Use /linkembeds off or /linkembeds on."
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


async def shutdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = require_message(update)
    if not is_admin_user(update, context):
        await message.reply_text("Sorry, only the admin may shut me down.")
        return

    user = require_user(update)
    logging.info("Shutdown requested by admin user %s", user.id)
    await message.reply_text("Shutting down.")
    context.application.stop_running()


async def get_command_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = require_message(update)
    user_data = require_user_data(context)
    raw_text = ensure_text(message.text).strip()
    selection, passage, explicit_version = parse_get_request(
        raw_text, get_bible_default_version(context)
    )
    display_name, _, _ = get_identity(update)

    if selection is None:
        await message.reply_text(
            f"Sorry {display_name}, I couldn't find that version. "
            "Use /setdefault to view all available versions."
        )
        return ConversationHandler.END

    if passage:
        if not await enforce_request_throttle(update, context):
            return ConversationHandler.END
        if not explicit_version:
            selection = get_passage_default_version(context, passage)
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
            selection,
            display_name,
            explicit_version=explicit_version,
        )
        return ConversationHandler.END

    user_data[PENDING_GET_VERSION_KEY] = selection
    user_data[PENDING_GET_VERSION_EXPLICIT_KEY] = explicit_version
    await message.reply_text(
        "Which passage do you want to look up? Version selection: "
        f"{format_version_selection(selection)}\n\n"
        "Tip: For faster results, use:\n/get John 3:16\n"
        f"/get John 3:16 {other_version(selection[0][0])}"
    )
    return GET_PASSAGE_STATE


async def get_conversation_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    message = require_message(update)
    if not await enforce_request_throttle(update, context):
        return ConversationHandler.END
    user_data = require_user_data(context)
    selection = user_data.pop(PENDING_GET_VERSION_KEY, ())
    explicit_version = bool(user_data.pop(PENDING_GET_VERSION_EXPLICIT_KEY, False))
    display_name, _, _ = get_identity(update)
    passage = ensure_text(message.text).strip()
    if not isinstance(selection, tuple) or not selection:
        selection = get_bible_default_version(context)
    if not explicit_version:
        selection = get_passage_default_version(context, passage)
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
        selection,
        display_name,
        explicit_version=explicit_version,
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def search_command_entry(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    message = require_message(update)
    if not await enforce_request_throttle(update, context):
        return ConversationHandler.END
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
    if not await enforce_request_throttle(update, context):
        return ConversationHandler.END
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
    if not await enforce_request_throttle(update, context):
        return
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
        selection = parse_version_selection(parts[1].strip())
        if selection is None:
            await message.reply_text(
                f"Sorry {display_name}, I couldn't find that version. "
                "Use /setdefault to view all available versions.\n\n"
                "Current Bible default is "
                f"{format_default_selection(get_bible_default_version(context))}.\n"
                "Current LDS default is "
                f"{format_default_selection(get_lds_default_version(context))}.\n"
                "Current Qurʾan default is "
                f"{format_default_selection(get_quran_default_version(context))}."
            )
            return ConversationHandler.END
        try:
            scripture_system = set_user_default_version(context, selection)
        except ValueError:
            await message.reply_text(
                "Sorry, default versions must belong to the same scripture system."
            )
            return ConversationHandler.END
        await message.reply_text(
            "Success! "
            f"{get_scripture_system(scripture_system).display_name} default is now "
            f"{format_default_selection(selection)}."
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
    user_data = require_user_data(context)
    if raw_text == VERSION_CATALOG.systems_by_id[ScriptureSystemId.BIBLE].display_name:
        user_data[PENDING_SETDEFAULT_SYSTEM_KEY] = ScriptureSystemId.BIBLE
        await reply_choose_language(message, ScriptureSystemId.BIBLE)
        return SETDEFAULT_LANGUAGE_STATE
    if raw_text == VERSION_CATALOG.systems_by_id[ScriptureSystemId.LDS].display_name:
        user_data[PENDING_SETDEFAULT_SYSTEM_KEY] = ScriptureSystemId.LDS
        await reply_choose_language(message, ScriptureSystemId.LDS)
        return SETDEFAULT_LANGUAGE_STATE
    if raw_text == VERSION_CATALOG.systems_by_id[ScriptureSystemId.QURAN].display_name:
        user_data[PENDING_SETDEFAULT_SYSTEM_KEY] = ScriptureSystemId.QURAN
        await reply_choose_language(message, ScriptureSystemId.QURAN)
        return SETDEFAULT_LANGUAGE_STATE

    await reply_choose_collection(message)
    return SETDEFAULT_COLLECTION_STATE


async def setdefault_language_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    message = require_message(update)
    user_data = require_user_data(context)
    raw_text = ensure_text(message.text).strip()
    scripture_system = user_data.get(
        PENDING_SETDEFAULT_SYSTEM_KEY, ScriptureSystemId.BIBLE
    )
    if scripture_system not in VERSION_CATALOG.systems_by_id:
        scripture_system = ScriptureSystemId.BIBLE
    system = VERSION_CATALOG.systems_by_id[scripture_system]
    language_code = system.resolve_language_group(raw_text)
    if raw_text == BACK_TO_COLLECTIONS:
        user_data.pop(PENDING_SETDEFAULT_SYSTEM_KEY, None)
        await reply_choose_collection(message)
        return SETDEFAULT_COLLECTION_STATE
    versions = (
        system.get_versions_for_language(language_code)
        if language_code is not None
        else None
    )
    if versions is None:
        await reply_choose_language(message, scripture_system)
        return SETDEFAULT_LANGUAGE_STATE

    await message.reply_text(
        SELECT_VERSION_PROMPT,
        reply_markup=build_buttons(list(versions) + [BACK_TO_LANGUAGES]),
    )
    return SETDEFAULT_VERSION_STATE


async def setdefault_version_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    message = require_message(update)
    user_data = require_user_data(context)
    raw_text = ensure_text(message.text).strip()
    if raw_text == BACK_TO_COLLECTIONS:
        user_data.pop(PENDING_SETDEFAULT_SYSTEM_KEY, None)
        await reply_choose_collection(message)
        return SETDEFAULT_COLLECTION_STATE
    if raw_text == BACK_TO_LANGUAGES:
        scripture_system = user_data.get(
            PENDING_SETDEFAULT_SYSTEM_KEY, ScriptureSystemId.BIBLE
        )
        if scripture_system not in VERSION_CATALOG.systems_by_id:
            scripture_system = ScriptureSystemId.BIBLE
        await reply_choose_language(message, scripture_system)
        return SETDEFAULT_LANGUAGE_STATE

    if raw_text not in VERSION_LOOKUP:
        await message.reply_text(SELECT_VERSION_PROMPT)
        return SETDEFAULT_VERSION_STATE

    version = VERSION_LOOKUP[raw_text]
    selection = ((version,),)
    scripture_system = set_user_default_version(context, selection)
    await message.reply_text(
        "Success! "
        f"{get_scripture_system(scripture_system).display_name} default is now "
        f"{format_default_selection(selection)}.",
        reply_markup=ReplyKeyboardRemove(),
    )
    user_data.pop(PENDING_SETDEFAULT_SYSTEM_KEY, None)
    return ConversationHandler.END


async def cancel_conversation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    message = require_message(update)
    user_data = require_user_data(context)
    user_data.pop(PENDING_GET_VERSION_KEY, None)
    user_data.pop(PENDING_GET_VERSION_EXPLICIT_KEY, None)
    user_data.pop(PENDING_SETDEFAULT_SYSTEM_KEY, None)
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
    if not await enforce_request_throttle(update, context, silent=True):
        await inline_query.answer(
            [],
            cache_time=1,
            button=build_inline_results_button(default_version),
        )
        return

    words = query.split()
    selection = parse_version_selection(words[-1]) if len(words) > 1 else None
    if selection is not None:
        passage = " ".join(words[:-1])
        explicit_version = True
    else:
        passage = query
        selection = get_passage_default_version(context, passage)
        explicit_version = False

    selection = resolve_version_selection(
        selection, passage, explicit_version=explicit_version
    )
    inline_results: list[tuple[str, InlinePassageResult]] = []
    for candidates in selection:
        result = await fetch_version_group(
            context, passage, candidates, inline_details=True
        )
        if result is None:
            continue
        version, response = result
        assert isinstance(response, InlinePassageResult)
        inline_results.append((version, response))

    if not inline_results:
        await inline_query.answer(
            [],
            cache_time=0,
            button=build_inline_results_button(default_version),
        )
        return

    passage_text = "\n\n".join(result.passage for _, result in inline_results)
    titles = " & ".join(result.title for _, result in inline_results)
    description = " ".join(passage_text.split())
    inline_passages = [
        (
            result.passage,
            result.header_url or build_passage_header_url(passage, version),
        )
        for version, result in inline_results
    ]
    link_preview_options = get_inline_link_preview_options(
        context, inline_query.from_user.id
    )
    results = [
        InlineQueryResultArticle(
            id=build_inline_result_id(
                [result.result_id for _, result in inline_results]
            ),
            title=titles,
            description=(
                description[:150] + "..." if len(description) > 153 else description
            ),
            input_message_content=build_input_message_content(
                inline_passages,
                link_preview_options=link_preview_options,
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
    if not await enforce_request_throttle(update, context, silent=True):
        return
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
    if not await enforce_request_throttle(update, context, silent=True):
        return

    display_name, _, _ = get_identity(update)
    to_lookup = lowered.replace(bot_handle, "").replace("revelations", "revelation")
    selection, to_lookup, explicit_version = parse_reference_version_query(
        to_lookup, get_bible_default_version(context)
    )
    refs = extract_refs(to_lookup)
    if refs:
        passage = build_passage_from_ref(refs[0])
        if not explicit_version:
            selection = get_passage_default_version(context, passage)
        await reply_with_passage_result(
            update,
            context,
            passage,
            selection,
            display_name,
            explicit_version=explicit_version,
            reply_markup=ReplyKeyboardRemove(),
            silent_failures=True,
        )
        return

    canonical_passage = canonicalize_reference(to_lookup)
    if canonical_passage and find_requested_book(canonical_passage):
        if not explicit_version:
            selection = get_passage_default_version(context, canonical_passage)
        await reply_with_passage_result(
            update,
            context,
            canonical_passage,
            selection,
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
