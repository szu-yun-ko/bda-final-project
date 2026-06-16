from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .config import Settings

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache" / "tdx"
CACHE_TTL_SEC = 4 * 60 * 60
ROW_KEYS = ("Stations", "LiveStatuses", "Connectors", "ChargingPoints", "Operators", "Sections", "LiveTraffics", "VDs", "VDLives")


def _unwrap_tdx_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ROW_KEYS:
            rows = data.get(key)
            if isinstance(rows, list):
                return [x for x in rows if isinstance(x, dict)]
    return []


class TdxClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._access_token: str | None = None

    def _cache_path(self, key: str) -> Path:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        digest = hashlib.md5(key.encode()).hexdigest()
        return CACHE_DIR / f"{digest}.json"

    def _read_cache(self, key: str, allow_stale: bool = False) -> Any | None:
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not allow_stale and time.time() - payload.get("ts", 0) > CACHE_TTL_SEC:
                return None
            return payload.get("data")
        except Exception:
            return None

    def _write_cache(self, key: str, data: Any) -> None:
        path = self._cache_path(key)
        path.write_text(json.dumps({"ts": time.time(), "data": data}, ensure_ascii=False), encoding="utf-8")

    def _post_form(self, url: str, payload: dict[str, str]) -> dict[str, Any]:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get_json(self, url: str, token: str) -> Any:
        cached = self._read_cache(url)
        if cached is not None:
            return cached
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                stale = self._read_cache(url, allow_stale=True)
                if stale is not None:
                    return stale
            raise
        self._write_cache(url, data)
        return data

    def get_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        if not self.settings.tdx_client_id or not self.settings.tdx_client_secret:
            raise ValueError("Missing TDX credentials. Set TDX_CLIENT_ID and TDX_CLIENT_SECRET.")

        token_data = self._post_form(
            self.settings.tdx_token_url,
            {
                "grant_type": "client_credentials",
                "client_id": self.settings.tdx_client_id,
                "client_secret": self.settings.tdx_client_secret,
            },
        )
        token = token_data.get("access_token")
        if not token:
            raise RuntimeError(f"TDX token response missing access_token: {token_data}")
        self._access_token = str(token)
        return self._access_token

    def fetch_city_station(self, city: str) -> list[dict[str, Any]]:
        token = self.get_access_token()
        url = f"{self.settings.tdx_base_url}/v1/EV/Station/City/{urllib.parse.quote(city)}?$format=JSON"
        return _unwrap_tdx_rows(self._get_json(url, token))

    def fetch_city_connector_live_status(self, city: str) -> list[dict[str, Any]]:
        token = self.get_access_token()
        url = (
            f"{self.settings.tdx_base_url}/v1/EV/ConnectorLiveStatus/City/"
            f"{urllib.parse.quote(city)}?$format=JSON"
        )
        return _unwrap_tdx_rows(self._get_json(url, token))

    def fetch_freeway_station(self) -> list[dict[str, Any]]:
        token = self.get_access_token()
        url = f"{self.settings.tdx_base_url}/v1/EV/Station/Freeway/ServiceArea?$format=JSON"
        return _unwrap_tdx_rows(self._get_json(url, token))

    def fetch_freeway_connector_live_status(self) -> list[dict[str, Any]]:
        token = self.get_access_token()
        url = f"{self.settings.tdx_base_url}/v1/EV/ConnectorLiveStatus/Freeway/ServiceArea?$format=JSON"
        return _unwrap_tdx_rows(self._get_json(url, token))

    def fetch_freeway_connector(self) -> list[dict[str, Any]]:
        token = self.get_access_token()
        url = f"{self.settings.tdx_base_url}/v1/EV/Connector/Freeway/ServiceArea?$format=JSON"
        return _unwrap_tdx_rows(self._get_json(url, token))

    def fetch_city_connector(self, city: str) -> list[dict[str, Any]]:
        token = self.get_access_token()
        url = f"{self.settings.tdx_base_url}/v1/EV/Connector/City/{urllib.parse.quote(city)}?$format=JSON"
        return _unwrap_tdx_rows(self._get_json(url, token))

    def fetch_city_traffic(self, city: str) -> list[dict[str, Any]]:
        return self.fetch_city_traffic_live(city)

    def fetch_city_traffic_sections(self, city: str) -> list[dict[str, Any]]:
        token = self.get_access_token()
        url = (
            f"{self.settings.tdx_base_url}/v2/Road/Traffic/Section/City/"
            f"{urllib.parse.quote(city)}?$format=JSON"
        )
        return _unwrap_tdx_rows(self._get_json(url, token))

    def fetch_city_traffic_live(self, city: str) -> list[dict[str, Any]]:
        token = self.get_access_token()
        url = (
            f"{self.settings.tdx_base_url}/v2/Road/Traffic/Live/City/"
            f"{urllib.parse.quote(city)}?$format=JSON"
        )
        return _unwrap_tdx_rows(self._get_json(url, token))

    def fetch_freeway_vd(self) -> list[dict[str, Any]]:
        token = self.get_access_token()
        url = f"{self.settings.tdx_base_url}/v2/Road/Traffic/VD/Freeway?$format=JSON"
        return _unwrap_tdx_rows(self._get_json(url, token))

    def fetch_freeway_vd_live(self) -> list[dict[str, Any]]:
        token = self.get_access_token()
        url = f"{self.settings.tdx_base_url}/v2/Road/Traffic/Live/VD/Freeway?$format=JSON"
        return _unwrap_tdx_rows(self._get_json(url, token))
