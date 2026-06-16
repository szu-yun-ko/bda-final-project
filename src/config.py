from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(dotenv_path: str = ".env") -> None:
    path = Path(dotenv_path)
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    tdx_client_id: str
    tdx_client_secret: str
    tdx_base_url: str
    tdx_token_url: str


def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        tdx_client_id=os.getenv("TDX_CLIENT_ID", ""),
        tdx_client_secret=os.getenv("TDX_CLIENT_SECRET", ""),
        tdx_base_url=os.getenv("TDX_BASE_URL", "https://tdx.transportdata.tw/api/basic"),
        tdx_token_url=os.getenv(
            "TDX_TOKEN_URL",
            "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token",
        ),
    )
