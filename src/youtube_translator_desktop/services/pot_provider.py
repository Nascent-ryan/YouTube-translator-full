from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


@dataclass(slots=True)
class PotProviderProcess:
    process: subprocess.Popen[str]
    base_url: str

    @classmethod
    def start_if_available(cls) -> PotProviderProcess | None:
        script_path = cls._script_path()
        if not script_path.exists():
            return None

        node = shutil.which("node")
        if not node:
            raise RuntimeError("PO Token provider requires Node.js, but node was not found.")

        port = int(os.getenv("YTDLP_POT_PROVIDER_PORT", "4416"))
        base_url = f"http://127.0.0.1:{port}"
        process = subprocess.Popen(
            [node, str(script_path), "--port", str(port)],
            text=True,
            env=os.environ.copy(),
        )
        provider = cls(process=process, base_url=base_url)
        provider._wait_until_ready()
        os.environ["YTDLP_POT_PROVIDER_URL"] = base_url
        return provider

    @staticmethod
    def _script_path() -> Path:
        configured = os.getenv("YTDLP_POT_PROVIDER_SCRIPT", "").strip()
        if configured:
            return Path(configured).expanduser()

        version = os.getenv("BGUTIL_PROVIDER_VERSION", "1.3.2").strip() or "1.3.2"
        return Path.cwd() / ".render" / f"bgutil-ytdlp-pot-provider-{version}" / "server" / "build" / "main.js"

    def _wait_until_ready(self, timeout_seconds: float = 30.0) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("PO Token provider exited before becoming ready.")
            try:
                with urlopen(f"{self.base_url}/ping", timeout=2) as response:
                    if response.status == 200:
                        return
            except (OSError, URLError):
                time.sleep(0.5)
        self.stop()
        raise RuntimeError("PO Token provider did not become ready within 30 seconds.")

    def stop(self) -> None:
        if self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
