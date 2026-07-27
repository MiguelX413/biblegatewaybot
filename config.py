import os
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class BotConfig:
    token: str
    admin_ids: frozenset[int]
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


def _parse_admin_ids(raw_value: object) -> frozenset[int]:
    if raw_value is None:
        return frozenset()
    if isinstance(raw_value, str):
        return frozenset(
            int(value.strip()) for value in raw_value.split(",") if value.strip()
        )
    if isinstance(raw_value, Iterable):
        normalized: set[int] = set()
        for value in raw_value:
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    continue
                normalized.add(int(stripped))
                continue
            normalized.add(int(value))
        return frozenset(normalized)
    raise TypeError("ADMIN_IDS must be a comma-separated string or an iterable of IDs.")


def load_config() -> BotConfig:
    token = load_secret("TOKEN")
    if not token:
        raise RuntimeError(
            "Missing TOKEN. Set it in the environment or provide secrets.py."
        )

    admin_ids = _parse_admin_ids(load_secret("ADMIN_IDS"))
    offline_only = (load_secret("OFFLINE_ONLY", "") or "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return BotConfig(
        token=token,
        admin_ids=admin_ids,
        botfamily_hash=load_secret("BOTFAMILY_HASH"),
        offline_only=offline_only,
        quran_backend=load_secret("QURAN_BACKEND"),
        qf_client_id=load_secret("QF_CLIENT_ID"),
        qf_client_secret=load_secret("QF_CLIENT_SECRET"),
        qf_env=load_secret("QF_ENV"),
    )
