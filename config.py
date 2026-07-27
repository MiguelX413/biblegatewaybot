import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BotConfig:
    token: str
    admin_id: int | None
    botfamily_hash: str | None
    offline_only: bool
    quran_backend: str | None
    qf_client_id: str | None
    qf_client_secret: str | None
    qf_env: str | None


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
    offline_only = (load_secret("OFFLINE_ONLY", "") or "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return BotConfig(
        token=token,
        admin_id=admin_id,
        botfamily_hash=load_secret("BOTFAMILY_HASH"),
        offline_only=offline_only,
        quran_backend=load_secret("QURAN_BACKEND"),
        qf_client_id=load_secret("QF_CLIENT_ID"),
        qf_client_secret=load_secret("QF_CLIENT_SECRET"),
        qf_env=load_secret("QF_ENV"),
    )
