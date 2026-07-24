from dataclasses import dataclass
from pathlib import Path

DEFAULT_BIBLE_VERSION = "NIV"
DEFAULT_LDS_VERSION = "BOM"
DEFAULT_VERSION_BY_SYSTEM = {
    "bible": DEFAULT_BIBLE_VERSION,
    "lds": DEFAULT_LDS_VERSION,
}
EMPTY = "empty"
MAX_SEARCH_RESULTS = 5
REQUEST_TIMEOUT_SECONDS = 10
PERSISTENCE_FILE = Path(__file__).with_name("scripturebot-state.pkl")

(
    GET_PASSAGE_STATE,
    SEARCH_STATE,
    SETDEFAULT_COLLECTION_STATE,
    SETDEFAULT_LANGUAGE_STATE,
    SETDEFAULT_VERSION_STATE,
) = range(5)

USER_DEFAULT_VERSION_KEY_BY_SYSTEM = {
    "bible": "default_bible_version",
    "lds": "default_lds_version",
}
USER_SEARCH_KEY = "last_search"
USER_STARTED_KEY = "started"
PENDING_GET_VERSION_KEY = "pending_get_version"
PENDING_GET_VERSION_EXPLICIT_KEY = "pending_get_version_explicit"

BACK_TO_COLLECTIONS = "🔙 to scripture collections"
BACK_TO_LANGUAGES = "🔙 to language list"
CHOOSE_COLLECTION_PROMPT = "Choose a scripture collection:"
CHOOSE_LANGUAGE_PROMPT = "Choose a language:"
SELECT_VERSION_PROMPT = "Select a version:"


@dataclass(frozen=True)
class InlinePassageResult:
    passage: str
    result_id: str
    title: str
    description: str
    header_url: str | None = None


@dataclass(frozen=True)
class SearchState:
    term: str
    start: int = 0
