import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BotConfig:
    token: str
    admin_id: int | None
    botfamily_hash: str | None
    offline_bibles_path: Path | None
    offline_only: bool


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
    offline_bibles_path_value = load_secret("OFFLINE_BIBLES_PATH")
    offline_bibles_path = (
        Path(offline_bibles_path_value).expanduser()
        if offline_bibles_path_value
        else None
    )
    offline_only = load_secret("OFFLINE_ONLY", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return BotConfig(
        token=token,
        admin_id=admin_id,
        botfamily_hash=load_secret("BOTFAMILY_HASH"),
        offline_bibles_path=offline_bibles_path,
        offline_only=offline_only,
    )
