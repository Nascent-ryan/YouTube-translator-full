from __future__ import annotations

import os

import uvicorn

from .config import AppConfig
from .web_app import create_app


def main() -> None:
    config = AppConfig.load()
    app = create_app(config)
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
