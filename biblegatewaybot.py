import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
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
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    InlineQueryHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from versions import BOOKS, VERSION_DATA, VERSION_LOOKUP, VERSIONS

DEFAULT_VERSION = "NIV"
EMPTY = "empty"
MAX_SEARCH_RESULTS = 5
REQUEST_TIMEOUT_SECONDS = 10
PERSISTENCE_FILE = Path(__file__).with_name("bot-state.pkl")

GET_PASSAGE_STATE, SEARCH_STATE, SETDEFAULT_LANGUAGE_STATE, SETDEFAULT_VERSION_STATE = (
    range(4)
)

USER_VERSION_KEY = "default_version"
USER_SEARCH_KEY = "last_search"
USER_STARTED_KEY = "started"

BACK_TO_LANGUAGES = "🔙 to language list"


@dataclass(frozen=True)
class BotConfig:
    token: str
    admin_id: int | None
    botfamily_hash: str | None


@dataclass(frozen=True)
class InlinePassageResult:
    passage: str
    result_id: str
    title: str
    description: str


@dataclass(frozen=True)
class SearchState:
    term: str
    start: int = 0


class BibleGatewayClient:
    def fetch_text(self, url: str) -> str | None:
        request = Request(url, headers={"User-Agent": "biblegatewaybot/1.0"})
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return response.read().decode("utf-8", "ignore")
        except (HTTPError, URLError, TimeoutError) as exc:
            logging.warning("Error fetching %s: %s", url, exc)
            return None

    def get_passage(
        self, passage: str, version: str = DEFAULT_VERSION, inline_details: bool = False
    ) -> str | InlinePassageResult | None:
        search = quote(ensure_text(passage).lower().strip())
        url = "https://www.biblegateway.com/passage/?search={}&version={}&interface=print".format(
            search, version
        )
        html = self.fetch_text(url)
        if html is None:
            return None

        start = html.find('<div class="passage-col')
        if start == -1:
            return EMPTY

        end = html.find("<!-- passage-box -->", start)
        passage_html = html[start:end]
        soup = BeautifulSoup(passage_html, "lxml")

        title_node = soup.select_one(".bcv")
        passage_soup = soup.select_one(".passage-text")
        if title_node is None or passage_soup is None:
            return EMPTY

        title = title_node.text.strip()
        header = f"{title} ({version})"

        for tag in passage_soup.select(
            ".passage-other-trans, .footnote, .footnotes, .crossreference, .crossrefs"
        ):
            tag.decompose()

        for tag in passage_soup.select("h1, h2, h3, h4, h5, h6"):
            tag["class"] = "bg-bot-passage-text"
            tag.string = tag.text.strip()

        for tag in passage_soup.select("p"):
            tag["class"] = "bg-bot-passage-text"

        for tag in passage_soup.select("br"):
            tag.replace_with("\n")

        for tag in passage_soup.select(".chapternum"):
            tag.string = f"{tag.text.strip()} "

        for tag in passage_soup.select(".versenum"):
            tag.string = to_sup(tag.text.strip())

        for tag in passage_soup.select(".text"):
            tag.string = tag.text.rstrip()

        blocks = [header]
        for tag in passage_soup(class_="bg-bot-passage-text"):
            text = " ".join(tag.text.split())
            if text:
                blocks.append(text)

        final_text = "\n\n".join(blocks).strip()
        if not final_text:
            return EMPTY

        if not inline_details:
            return final_text

        osis_start = html.find('data-osis="')
        result_id = f"{title}/{version}"
        if osis_start != -1:
            osis_start += len('data-osis="')
            osis_end = html.find('"', osis_start)
            if osis_end != -1:
                result_id = f"{html[osis_start:osis_end]}/{version}"

        content = " ".join(final_text.split())
        description = f"{content[:150]}..." if len(content) > 153 else content
        return InlinePassageResult(
            passage=final_text,
            result_id=result_id,
            title=header,
            description=description,
        )

    def get_search_results(self, text: str, start: int = 0) -> str | None:
        query = quote(ensure_text(text).lower().strip())
        url = f"http://biblehub.net/search.php?q={query}"
        html = self.fetch_text(url)
        if html is None:
            return None

        soup = BeautifulSoup(html, "lxml")
        headers = soup.select(".l")
        bodies = soup.select(".s")
        num_results = min(len(headers), len(bodies))

        if num_results == 0 or start >= num_results:
            return EMPTY

        lines = []
        end = min(num_results, start + MAX_SEARCH_RESULTS)
        for i in range(start, end):
            header = headers[i].text
            idx = header.find(":")
            idx += header[idx:].find(" ")
            title = header[:idx].strip()

            body_text = " ".join(bodies[i].text.split())
            cutoff = body_text.rfind("//biblehub.com")
            if cutoff != -1:
                body_text = body_text[:cutoff].strip()

            link = "/" + "".join(title.split()).lower().replace(":", "V")
            lines.append(f"🔹{title}\n{body_text}\n{link}")

        header_text = "Search results"
        if num_results > MAX_SEARCH_RESULTS:
            header_text += f" ({start + 1}-{end} of {num_results})"

        result = f"{header_text}\n\n" + "\n\n".join(lines)
        if start + MAX_SEARCH_RESULTS < num_results:
            result += "\n\nGet /more results"
        return result


def ensure_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    return str(value)


def load_secret(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    try:
        import secrets as local_secrets
    except ImportError:
        return default
    return getattr(local_secrets, name, default)


def load_config() -> BotConfig:
    token = load_secret("TOKEN")
    if not token:
        raise RuntimeError(
            "Missing TOKEN. Set it in the environment or provide secrets.py."
        )

    admin_id_value = load_secret("ADMIN_ID")
    admin_id = int(admin_id_value) if admin_id_value else None
    return BotConfig(
        token=token,
        admin_id=admin_id,
        botfamily_hash=load_secret("BOTFAMILY_HASH"),
    )


def to_sup(text: str) -> str:
    sups = {
        "0": "\u2070",
        "1": "\xb9",
        "2": "\xb2",
        "3": "\xb3",
        "4": "\u2074",
        "5": "\u2075",
        "6": "\u2076",
        "7": "\u2077",
        "8": "\u2078",
        "9": "\u2079",
        "-": "\u207b",
    }
    return "".join(sups.get(char, char) for char in text)


def build_bot_handle(application: Application) -> str:
    username = application.bot.username or "biblegatewaybot"
    return f"@{username}"


def command_list(application: Application) -> str:
    bot_handle = build_bot_handle(application)
    return (
        "/get <reference>\n"
        "/get<version> <reference>\n"
        "/search <keyword>\n"
        "/setdefault <version>\n\n"
        "Examples:\n"
        "/get John 3:16\n"
        "/getNLT 1 cor 13:4-7\n"
        "/search the greatest commandment\n"
        "/setdefault NASB\n\n"
        f"Inline mode:\n{bot_handle} john 3:16\n"
        f"{bot_handle} 1co13 nasb"
    )


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


def replied_to_bot(update: Update, application: Application) -> bool:
    message = update.effective_message
    if (
        not message
        or not message.reply_to_message
        or not message.reply_to_message.from_user
    ):
        return False
    return message.reply_to_message.from_user.username == application.bot.username


def build_passage_from_ref(ref: tuple[Any, Any, Any, Any, Any]) -> str:
    book = ref[0]
    if book == "Revelation of Jesus Christ":
        book = "Revelation"
    return f"{book} {ref[1]}:{ref[2]}-{ref[3]}:{ref[4]}"


def parse_get_request(text: str, default_version: str) -> tuple[str | None, str | None]:
    words = text.split()
    if not words:
        return None, None

    first_word = words[0]
    normalized = first_word.split("@", 1)[0].lower()
    version = normalized[4:].upper() if len(normalized) > 4 else default_version
    if version not in VERSIONS:
        return None, None

    passage = text[len(first_word) :].strip()
    if not passage:
        return version, None

    first_passage_word = passage.split()[0].upper()
    if (
        len(normalized) == 4
        and first_passage_word in VERSIONS
        and passage[len(first_passage_word) :].strip()
    ):
        version = first_passage_word
        passage = passage[len(first_passage_word) :].strip()

    return version, passage


def other_version(current_version: str) -> str:
    return "NIV" if current_version == "NASB" else "NASB"


async def send_typing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )


async def fetch_passage_async(
    context: ContextTypes.DEFAULT_TYPE,
    passage: str,
    version: str,
    *,
    inline_details: bool = False,
) -> str | InlinePassageResult | None:
    client: BibleGatewayClient = context.application.bot_data["bible_client"]
    return await asyncio.to_thread(client.get_passage, passage, version, inline_details)


async def fetch_search_results_async(
    context: ContextTypes.DEFAULT_TYPE, term: str, start: int = 0
) -> str | None:
    client: BibleGatewayClient = context.application.bot_data["bible_client"]
    return await asyncio.to_thread(client.get_search_results, term, start)


async def notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    config: BotConfig = context.application.bot_data["config"]
    if not config.admin_id:
        return
    try:
        await context.bot.send_message(chat_id=config.admin_id, text=text)
    except Exception as exc:
        logging.warning("Failed to notify admin: %s", exc)


async def reply_with_passage_result(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    passage: str,
    version: str,
    display_name: str,
    *,
    reply_markup: ReplyKeyboardRemove | None = None,
) -> None:
    await send_typing(update, context)
    response = await fetch_passage_async(context, passage, version)
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
    await update.effective_message.reply_text(str(response), reply_markup=reply_markup)


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
    response = await fetch_search_results_async(context, term, start)
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

    response = await fetch_passage_async(context, passage, version, inline_details=True)
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
            input_message_content=InputTextMessageContent(inline_result.passage),
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
    passage = raw_text[1:].replace("V", ":")
    bot_handle = build_bot_handle(context.application)
    if passage.endswith(bot_handle):
        passage = passage[: -len(bot_handle)]
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
        and not replied_to_bot(update, context.application)
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

    await update.effective_message.reply_text(
        f"Sorry {display_name}, I couldn't understand that. Please enter one of the following commands:\n"
        f"{command_list(context.application)}",
        reply_markup=get_try_inline_keyboard(),
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.exception(
        "Unhandled error while processing update %s", update, exc_info=context.error
    )


def build_application(config: BotConfig) -> Application:
    persistence = PicklePersistence(filepath=str(PERSISTENCE_FILE))
    application = (
        ApplicationBuilder().token(config.token).persistence(persistence).build()
    )
    application.bot_data["config"] = config
    application.bot_data["bible_client"] = BibleGatewayClient()

    get_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(r"^/get(\w+)?(@\w+)?(\s|$)"), get_command_entry
            )
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
    config = load_config()
    logging.info("Starting biblegatewaybot via python-telegram-bot polling")
    application = build_application(config)
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
