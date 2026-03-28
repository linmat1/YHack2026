from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional


DEFAULT_ENV_PATH = Path(__file__).resolve().parent / ".env"


def load_local_env(env_path: Optional[Path] = None, override: bool = False) -> Path:
    path = Path(env_path or DEFAULT_ENV_PATH)
    if not path.exists():
        return path

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = value
    return path


def get_polymarket_config(env_path: Optional[Path] = None) -> Dict[str, object]:
    path = load_local_env(env_path)
    cfg: Dict[str, object] = {
        "env_path": str(path),
        "gamma_host": os.getenv("POLYMARKET_GAMMA_HOST", "https://gamma-api.polymarket.com"),
        "clob_host": os.getenv("POLYMARKET_CLOB_HOST", "https://clob.polymarket.com"),
        "data_host": os.getenv("POLYMARKET_DATA_HOST", "https://data-api.polymarket.com"),
        "private_key": os.getenv("POLYMARKET_PRIVATE_KEY", ""),
        "proxy_address": os.getenv("POLYMARKET_PROXY_ADDRESS", ""),
        "api_key": os.getenv("POLYMARKET_API_KEY", ""),
        "secret": os.getenv("POLYMARKET_SECRET", ""),
        "passphrase": os.getenv("POLYMARKET_PASSPHRASE", ""),
        "signature_type": int(os.getenv("POLYMARKET_SIGNATURE_TYPE", "0")),
        "request_timeout": int(os.getenv("POLYMARKET_REQUEST_TIMEOUT", "20")),
        "chain_id": int(os.getenv("POLYMARKET_CHAIN_ID", "137")),
    }
    return cfg


def redacted_polymarket_config(env_path: Optional[Path] = None) -> Dict[str, object]:
    cfg = get_polymarket_config(env_path)
    return {
        "env_path": cfg["env_path"],
        "gamma_host": cfg["gamma_host"],
        "clob_host": cfg["clob_host"],
        "data_host": cfg["data_host"],
        "request_timeout": cfg["request_timeout"],
        "chain_id": cfg["chain_id"],
        "has_private_key": bool(cfg["private_key"]),
        "has_proxy_address": bool(cfg["proxy_address"]),
        "has_api_key": bool(cfg["api_key"]),
        "has_secret": bool(cfg["secret"]),
        "has_passphrase": bool(cfg["passphrase"]),
    }
