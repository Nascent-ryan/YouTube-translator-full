from __future__ import annotations

import os

import uvicorn

from .config import AppConfig
from .services.pot_provider import PotProviderProcess
from .web_app import create_app


def main() -> None:
    pot_provider = PotProviderProcess.start_if_available()
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
