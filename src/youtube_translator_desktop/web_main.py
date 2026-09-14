from __future__ import annotations

import os

import uvicorn

from .config import AppConfig
from .services.pot_provider import PotProviderProcess
from .web_app import create_app


def _pot_provider_enabled() -> bool:
    return os.getenv("ENABLE_YTDLP_POT_PROVIDER", "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    # Browser-assisted captions do not need the local PO-token sidecar. Keeping it
    # opt-in avoids adding up to 30 seconds to a Render cold start.
    pot_provider = PotProviderProcess.start_if_available() if _pot_provider_enabled() else None
    config = AppConfig.load()
    app = create_app(config)
    port = int(os.environ.get("PORT", "8000"))
    try:
        uvicorn.run(app, host="0.0.0.0", port=port)
    finally:
        if pot_provider:
            pot_provider.stop()


if __name__ == "__main__":
    main()
