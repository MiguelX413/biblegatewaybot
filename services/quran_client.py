from config import BotConfig
from services.alquran_cloud import AlQuranCloudClient
from services.quran_foundation import QuranFoundationClient


def create_quran_client(config: BotConfig):
    backend = (config.quran_backend or "auto").strip().casefold()
    has_qf_credentials = bool(config.qf_client_id and config.qf_client_secret)

    if backend == "alquran_cloud":
        return AlQuranCloudClient()

    if backend == "qf":
        if not has_qf_credentials:
            raise RuntimeError(
                "QURAN_BACKEND=qf requires QF_CLIENT_ID and QF_CLIENT_SECRET."
            )
        return QuranFoundationClient(
            client_id=config.qf_client_id or "",
            client_secret=config.qf_client_secret or "",
            env=config.qf_env,
        )

    if has_qf_credentials:
        return QuranFoundationClient(
            client_id=config.qf_client_id or "",
            client_secret=config.qf_client_secret or "",
            env=config.qf_env,
            fallback_client=AlQuranCloudClient(),
        )
    return AlQuranCloudClient()
