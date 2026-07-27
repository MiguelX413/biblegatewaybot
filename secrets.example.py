"""Copy this file to secrets.py and replace placeholder values."""

# Required
TOKEN = "your-telegram-bot-token"

# Optional
# Telegram user IDs allowed to run admin-only commands like /shutdown and /reload.
# In secrets.py, you may use a Python collection like {123456789, 987654321}.
# Environment variables should still use a comma-separated string.
ADMIN_IDS = {123456789, 987654321}
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
