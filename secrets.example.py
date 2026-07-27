"""Copy this file to secrets.py and replace placeholder values."""

# Required
TOKEN = "your-telegram-bot-token"

# Optional
# Telegram user ID allowed to run admin-only commands like /shutdown.
ADMIN_ID = "your-telegram-user-id"
BOTFAMILY_HASH = ""
OFFLINE_ONLY = "false"
# Qurʾān backend selector: "auto", "qf", or "alquran_cloud".
QURAN_BACKEND = "auto"
# Quran Foundation Content API client ID.
QF_CLIENT_ID = ""
# Quran Foundation Content API client secret. Keep server-side only.
QF_CLIENT_SECRET = ""
# Quran Foundation environment selector: use "production" or "prelive".
# This is not a full URL; code derives the correct auth/API base URLs from it.
QF_ENV = ""
