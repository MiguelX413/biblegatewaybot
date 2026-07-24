import logging
import os
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
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from versions import BOOKS, VERSION_DATA, VERSION_LOOKUP, VERSIONS

EMPTY = "empty"
MAX_SEARCH_RESULTS = 5
STATE_VERSION = "version"
STATE_REPLY_TO = "reply_to"
STATE_STARTED = "started"
DEFAULT_VERSION = "NIV"
REQUEST_TIMEOUT_SECONDS = 10
PERSISTENCE_FILE = Path(__file__).with_name("bot-state.pkl")


def load_secret(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value

    try:
        import secrets as local_secrets
    except ImportError:
        return default

    return getattr(local_secrets, name, default)


TOKEN = load_secret("TOKEN")
ADMIN_ID = load_secret("ADMIN_ID")
BOTFAMILY_HASH = load_secret("BOTFAMILY_HASH")

if not TOKEN:
    raise RuntimeError(
        "Missing TOKEN. Set it in the environment or provide secrets.py."
    )


def build_bot_handle(application: Application) -> str:
    username = application.bot.username or "biblegatewaybot"
    return f"@{username}"


def bot_description(application: Application) -> str:
    return "This bot can fetch Bible passages from biblegateway.com."


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
        f"Inline mode:\n{bot_handle} john 3:16\n{bot_handle} 1co13 nasb"
    )


def get_welcome_text(application: Application, name: str, is_group: bool) -> str:
    if is_group:
        greeting = f"Hello, friends in {name}! Thanks for adding me in!"
    else:
        greeting = f"Hello, {name}! Welcome!"
    return (
        f"{greeting} {bot_description(application)}\n\n"
        f"To get started, enter one of the following commands:\n{command_list(application)}"
    )


def get_help_text(application: Application, name: str) -> str:
    return (
        f"Hi {name}! Please enter one of the following commands:\n"
        f"{command_list(application)}"
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


def ensure_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    return str(value)


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


def fetch_text(url: str) -> str | None:
    request = Request(url, headers={"User-Agent": "biblegatewaybot/1.0"})
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8", "ignore")
    except (HTTPError, URLError, TimeoutError) as exc:
        logging.warning("Error fetching %s: %s", url, exc)
        return None


def get_passage(
    passage: str, version: str = DEFAULT_VERSION, inline_details: bool = False
):
    search = quote(ensure_text(passage).lower().strip())
    url = "https://www.biblegateway.com/passage/?search={}&version={}&interface=print".format(
        search, version
    )
    html = fetch_text(url)
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
    qr_id = f"{title}/{version}"
    if osis_start != -1:
        osis_start += len('data-osis="')
        osis_end = html.find('"', osis_start)
        if osis_end != -1:
            qr_id = f"{html[osis_start:osis_end]}/{version}"

    content = " ".join(final_text.split())
    qr_description = f"{content[:150]}..." if len(content) > 153 else content
    return final_text, qr_id, header, qr_description


def get_search_results(text: str, start: int = 0) -> str | None:
    query = quote(ensure_text(text).lower().strip())
    url = f"http://biblehub.net/search.php?q={query}"
    html = fetch_text(url)
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


def other_version(current_version: str) -> str:
    return "NIV" if current_version == "NASB" else "NASB"


def build_buttons(menu: list[str]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[item] for item in menu],
        one_time_keyboard=True,
        resize_keyboard=True,
        selective=True,
    )


def get_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict[str, Any]:
    chat = update.effective_chat
    if chat and chat.type != "private":
        return context.chat_data
    return context.user_data


def get_version_from_state(state: dict[str, Any]) -> str:
    return ensure_text(state.get(STATE_VERSION) or DEFAULT_VERSION).upper()


def set_version_in_state(state: dict[str, Any], version: str) -> None:
    state[STATE_VERSION] = version.upper()


def get_reply_to(state: dict[str, Any]) -> str | None:
    reply_to = state.get(STATE_REPLY_TO)
    return ensure_text(reply_to) or None


def set_reply_to(state: dict[str, Any], value: str | None) -> None:
    if value:
        state[STATE_REPLY_TO] = value[:1500]
    else:
        state.pop(STATE_REPLY_TO, None)


def mark_started(state: dict[str, Any]) -> bool:
    is_new = not bool(state.get(STATE_STARTED))
    state[STATE_STARTED] = True
    return is_new


def normalize_command_word(word: str) -> str:
    command = ensure_text(word).strip()
    if "@" in command:
        command = command.split("@", 1)[0]
    return command.lower()


def extract_message_identity(update: Update) -> tuple[str, str, bool]:
    chat = update.effective_chat
    user = update.effective_user

    if chat and chat.type == "private":
        name = ensure_text(user.first_name) or "friend"
        return name, name, False

    group_name = ensure_text(chat.title) or "this group"
    sender_name = ensure_text(user.first_name) or group_name
    return sender_name, group_name, True


def replied_to_bot(update: Update, application: Application) -> bool:
    message = update.effective_message
    if (
        not message
        or not message.reply_to_message
        or not message.reply_to_message.from_user
    ):
        return False
    bot_username = application.bot.username
    return message.reply_to_message.from_user.username == bot_username


async def notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    if not ADMIN_ID:
        return
    try:
        await context.bot.send_message(chat_id=int(ADMIN_ID), text=text)
    except Exception as exc:
        logging.warning("Failed to notify admin: %s", exc)


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: dict[str, Any],
    raw_text: str,
) -> None:
    sender_name, group_name, is_group = extract_message_identity(update)
    is_new = mark_started(state)
    set_reply_to(state, None)

    welcome_name = group_name if is_group else sender_name
    await update.effective_message.reply_text(
        get_welcome_text(context.application, welcome_name, is_group),
        reply_markup=get_try_inline_keyboard(),
    )

    normalized = raw_text.strip().lower()
    if normalized == "/start setdefault":
        set_reply_to(state, "setdefault")
        await update.effective_message.reply_text(
            "Choose a language:", reply_markup=build_buttons(list(VERSION_DATA.keys()))
        )

    if is_new:
        if is_group:
            new_alert = f'New group: "{group_name}" via user: {sender_name}'
        elif normalized == "/start setdefault":
            new_alert = f"New user via inline: {sender_name}"
        else:
            new_alert = f"New user: {sender_name}"
        await notify_admin(context, new_alert)


async def handle_get_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: dict[str, Any],
    raw_text: str,
    display_name: str,
) -> None:
    text = raw_text.strip()
    words = text.split()
    first_word = normalize_command_word(words[0])
    version = (
        first_word[4:].upper() if len(first_word) > 4 else get_version_from_state(state)
    )

    if version not in VERSIONS:
        await update.effective_message.reply_text(
            f"Sorry {display_name}, I couldn't find that version. Use /setdefault to view all available versions."
        )
        return

    passage = text[len(words[0]) :].strip()
    if not passage:
        set_reply_to(state, first_word[1:])
        await update.effective_message.reply_text(
            "Which Bible passage do you want to lookup? Version: {}\n\n"
            "Tip: For faster results, use:\n/get John 3:16\n/get{} John 3:16".format(
                version, other_version(version)
            )
        )
        return

    first_passage_word = passage.split()[0].upper()
    if (
        len(first_word) == 4
        and first_passage_word in VERSIONS
        and passage[len(first_passage_word) :].strip()
    ):
        version = first_passage_word
        passage = passage[len(first_passage_word) :].strip()

    set_reply_to(state, None)
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )
    response = get_passage(passage, version)
    if response == EMPTY:
        await update.effective_message.reply_text(
            f"Sorry {display_name}, no results were found. Please try again."
        )
        return
    if response is None:
        await update.effective_message.reply_text(
            f"Sorry {display_name}, I'm having some difficulty accessing the site. Please try again later."
        )
        return

    await update.effective_message.reply_text(response)


async def handle_search_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: dict[str, Any],
    search_term: str,
    display_name: str,
    *,
    hide_keyboard: bool = False,
    start: int = 0,
) -> None:
    set_reply_to(state, f"search{start} {search_term}")
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )
    response = get_search_results(search_term, start)

    reply_markup = ReplyKeyboardRemove() if hide_keyboard else None
    if response == EMPTY:
        set_reply_to(state, None)
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

    await update.effective_message.reply_text(response, reply_markup=reply_markup)


async def handle_setdefault(
    update: Update,
    state: dict[str, Any],
    raw_text: str,
    display_name: str,
) -> None:
    parts = raw_text.split(maxsplit=1)
    if len(parts) == 1:
        set_reply_to(state, "setdefault")
        await update.effective_message.reply_text(
            "Choose a language:", reply_markup=build_buttons(list(VERSION_DATA.keys()))
        )
        return

    version = parts[1].strip().upper()
    if version not in VERSIONS:
        await update.effective_message.reply_text(
            "Sorry {}, I couldn't find that version. Use /setdefault to view all available versions.\n\n"
            "Current default is {}.".format(display_name, get_version_from_state(state))
        )
        return

    set_version_in_state(state, version)
    set_reply_to(state, None)
    await update.effective_message.reply_text(
        f"Success! Default version is now {version}."
    )


def build_passage_from_ref(ref: tuple[Any, Any, Any, Any, Any]) -> str:
    book = ref[0]
    if book == "Revelation of Jesus Christ":
        book = "Revelation"
    return f"{book} {ref[1]}:{ref[2]}-{ref[3]}:{ref[4]}"


async def route_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.text:
        return

    raw_text = ensure_text(message.text).strip()
    if not raw_text:
        return

    state = get_state(update, context)
    display_name, group_name, is_group = extract_message_identity(update)
    bot_handle = build_bot_handle(context.application)
    lowered = raw_text.lower()

    if raw_text == "/botfamily_verification_code":
        if BOTFAMILY_HASH:
            await message.reply_text(BOTFAMILY_HASH)
            await notify_admin(context, "Botfamily verified!")
        else:
            await message.reply_text("BOTFAMILY_HASH is not configured.")
        return

    if lowered == "/start" or lowered == "/start setdefault":
        await start_command(update, context, state, lowered)
        return

    if raw_text in VERSION_DATA:
        buttons = build_buttons(VERSION_DATA[raw_text] + ["🔙 to language list"])
        await message.reply_text("Select a version:", reply_markup=buttons)
        return

    if raw_text == "🔙 to language list":
        set_reply_to(state, "setdefault")
        await message.reply_text(
            "Choose a language:", reply_markup=build_buttons(list(VERSION_DATA.keys()))
        )
        return

    if raw_text in VERSION_LOOKUP:
        version = VERSION_LOOKUP[raw_text]
        set_version_in_state(state, version)
        set_reply_to(state, None)
        await message.reply_text(
            f"Success! Default version is now {version}.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    first_word = raw_text.split()[0]
    normalized_command = normalize_command_word(first_word)

    if normalized_command == "/help":
        set_reply_to(state, None)
        await message.reply_text(
            get_help_text(context.application, display_name),
            reply_markup=get_try_inline_keyboard(),
        )
        return

    if normalized_command == "/settings":
        set_reply_to(state, None)
        await message.reply_text(
            f"Current default version is {get_version_from_state(state)}. Use /setdefault to change it."
        )
        return

    if normalized_command == "/setdefault":
        await handle_setdefault(update, state, raw_text, display_name)
        return

    if normalized_command == "/search":
        if len(raw_text.split(maxsplit=1)) == 1:
            set_reply_to(state, "search")
            await message.reply_text(
                "Please enter what you wish to search for.\n\n"
                'Tip: For faster results, use:\n/search make disciples\n/search "love is patient"'
            )
            return

        search_term = raw_text.split(maxsplit=1)[1].strip().lower()
        await handle_search_request(update, context, state, search_term, display_name)
        return

    if normalized_command.startswith("/get"):
        await handle_get_request(update, context, state, raw_text, display_name)
        return

    if normalized_command == "/more":
        reply_to = get_reply_to(state)
        if reply_to and reply_to.startswith("search") and len(reply_to) > 6:
            idx = reply_to.find(" ")
            old_start = int(reply_to[6:idx])
            search_term = reply_to[idx + 1 :]
            new_start = old_start + MAX_SEARCH_RESULTS
            await handle_search_request(
                update,
                context,
                state,
                search_term,
                display_name,
                start=new_start,
            )
        return

    if raw_text.startswith("/") and raw_text[1:].lower().startswith(BOOKS):
        passage = raw_text[1:].replace("V", ":")
        if passage.endswith(bot_handle):
            passage = passage[: -len(bot_handle)]

        set_reply_to(state, None)
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.TYPING
        )
        response = get_passage(passage, get_version_from_state(state))
        if response == EMPTY:
            await message.reply_text(
                f"Sorry {display_name}, no results were found. Please try again."
            )
            logging.info("Invalid link: %s", raw_text)
            return
        if response is None:
            await message.reply_text(
                f"Sorry {display_name}, I'm having some difficulty accessing the site. Please try again later."
            )
            return

        await message.reply_text(response)
        return

    reply_to = get_reply_to(state)
    if reply_to == "search":
        await handle_search_request(
            update, context, state, raw_text, display_name, hide_keyboard=True
        )
        return

    if reply_to and reply_to.startswith("get"):
        version = reply_to[3:].upper() or get_version_from_state(state)
        set_reply_to(state, None)
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.TYPING
        )
        response = get_passage(raw_text, version)
        if response == EMPTY:
            await message.reply_text(
                f"Sorry {display_name}, no results were found. Please try again.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return
        if response is None:
            await message.reply_text(
                f"Sorry {display_name}, I'm having some difficulty accessing the site. Please try again later.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        await message.reply_text(response, reply_markup=ReplyKeyboardRemove())
        return

    if (
        is_group
        and bot_handle.lower() not in lowered
        and not replied_to_bot(update, context.application)
    ):
        logging.info("Ignoring non-directed group message")
        return

    to_lookup = lowered.replace(bot_handle.lower(), "").replace(
        "revelations", "revelation"
    )
    refs = extract_refs(to_lookup)
    if refs:
        passage = build_passage_from_ref(refs[0])
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.TYPING
        )
        response = get_passage(passage, get_version_from_state(state))
        if response and response != EMPTY:
            await message.reply_text(response, reply_markup=ReplyKeyboardRemove())
            return
        if response == EMPTY:
            logging.warning("Invalid quick lookup: %s", raw_text)

    set_reply_to(state, None)
    await message.reply_text(
        "Sorry {}, I couldn't understand that. Please enter one of the following commands:\n{}".format(
            display_name, command_list(context.application)
        ),
        reply_markup=get_try_inline_keyboard(),
    )


async def handle_inline_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    inline_query = update.inline_query
    if inline_query is None:
        return

    query = ensure_text(inline_query.query).strip()
    default_version = ensure_text(
        context.user_data.get(STATE_VERSION) or DEFAULT_VERSION
    ).upper()

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
        response = get_passage(passage, version=version, inline_details=True)
    else:
        response = get_passage(query, version=default_version, inline_details=True)

    if response in (None, EMPTY):
        await inline_query.answer(
            [],
            cache_time=0,
            switch_pm_text=f"Default version: {default_version}",
            switch_pm_parameter="setdefault",
        )
        return

    passage, qr_id, qr_title, qr_description = response
    results = [
        InlineQueryResultArticle(
            id=qr_id,
            title=qr_title,
            description=qr_description,
            input_message_content=InputTextMessageContent(passage),
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
            state = get_state(update, context)
            await start_command(update, context, state, "/start")
            return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.exception(
        "Unhandled error while processing update %s", update, exc_info=context.error
    )


def build_application() -> Application:
    persistence = PicklePersistence(filepath=str(PERSISTENCE_FILE))
    app = ApplicationBuilder().token(TOKEN).persistence(persistence).build()
    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members)
    )
    app.add_handler(InlineQueryHandler(handle_inline_query))
    app.add_handler(MessageHandler(filters.TEXT, route_message))
    app.add_error_handler(error_handler)
    return app


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.info("Starting biblegatewaybot via python-telegram-bot polling")
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
