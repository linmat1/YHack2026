import json
from typing import Annotated

import pandas as pd
import requests
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(tags=["polymarket"])

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
TIMEOUT = 8


def _parse_json_field(raw, default=None):
    """Gamma encodes list fields as JSON strings inside JSON."""
    if default is None:
        default = []
    try:
        return json.loads(raw) if isinstance(raw, str) else (raw or default)
    except (json.JSONDecodeError, TypeError):
        return default


def _days_left(end_date_str) -> int:
    try:
        end_dt = pd.to_datetime(end_date_str, utc=True)
        return max(0, (end_dt - pd.Timestamp.now(tz="UTC")).days)
    except Exception:
        return 0


def _is_resolved(prices: list) -> bool:
    """Markets where one outcome is at 0% or 100% are resolved/about to resolve."""
    if not prices:
        return False
    try:
        floats = [float(p) for p in prices]
        return any(p >= 0.99 or p <= 0.01 for p in floats)
    except (ValueError, TypeError):
        return False


def _build_market_row(m: dict) -> dict:
    prices = _parse_json_field(m.get("outcomePrices", "[]"))
    token_ids = _parse_json_field(m.get("clobTokenIds", "[]"))
    outcomes = _parse_json_field(m.get("outcomes", '["Yes","No"]'))

    yes_prob = float(prices[0]) if prices else 0.5
    no_prob = float(prices[1]) if len(prices) > 1 else 1 - yes_prob

    return {
        "question": m.get("question", ""),
        "conditionId": m.get("conditionId", ""),
        "slug": m.get("slug", ""),
        "tokenId": str(token_ids[0]) if token_ids else "",
        "noTokenId": str(token_ids[1]) if len(token_ids) > 1 else "",
        "outcomes": outcomes,
        "yes_prob": yes_prob,
        "no_prob": no_prob,
        "volume": float(m.get("volume") or 0),
        "volume24hr": float(m.get("volume24hr") or 0),
        "liquidity": float(m.get("liquidity") or 0),
        "lastTradePrice": float(m.get("lastTradePrice") or yes_prob),
        "bestBid": float(m.get("bestBid") or 0),
        "bestAsk": float(m.get("bestAsk") or 0),
        "spread": float(m.get("spread") or 0),
        "days_left": _days_left(m.get("endDate")),
        "endDate": (m.get("endDate") or "")[:10],
        "category": m.get("category", ""),
        "acceptingOrders": bool(m.get("acceptingOrders", False)),
    }


@router.get("/polymarket/markets")
def get_polymarket_markets(
    keyword: Annotated[str, Query(description="Search keyword")] = "",
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> dict:
    """
    Fetch active, non-resolved Polymarket markets sorted by 24h volume.
    Filters out: closed markets, resolved markets (price at 0% or 100%),
    and markets not accepting orders.
    """
    params: dict = {
        "active": "true",
        "closed": "false",
        "limit": min(limit * 3, 100),  # over-fetch to allow filtering
        "order": "volume24hr",
        "ascending": "false",
    }
    if keyword.strip():
        params["keyword"] = keyword.strip()

    try:
        resp = requests.get(f"{GAMMA}/markets", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        raw_markets = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gamma API error: {e}")

    markets = []
    for m in raw_markets:
        # Skip truly closed markets
        if m.get("closed") or not m.get("active"):
            continue

        prices = _parse_json_field(m.get("outcomePrices", "[]"))

        # Skip resolved markets (100%/0% outcomes)
        if _is_resolved(prices):
            continue

        row = _build_market_row(m)

        # Skip markets with no meaningful data
        if not row["tokenId"] or row["volume24hr"] == 0 and row["volume"] < 100:
            continue

        markets.append(row)
        if len(markets) >= limit:
            break

    return {"source": "Polymarket Gamma API", "markets": markets, "count": len(markets)}


@router.get("/polymarket/trending")
def get_polymarket_trending() -> dict:
    """
    Fetch the most active prediction markets right now (by 24h volume).
    No keyword filter — returns top markets across all categories.
    """
    try:
        resp = requests.get(
            f"{GAMMA}/markets",
            params={
                "active": "true",
                "closed": "false",
                "limit": 80,
                "order": "volume24hr",
                "ascending": "false",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        raw_markets = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gamma API error: {e}")

    markets = []
    for m in raw_markets:
        if m.get("closed") or not m.get("active"):
            continue
        prices = _parse_json_field(m.get("outcomePrices", "[]"))
        if _is_resolved(prices):
            continue
        row = _build_market_row(m)
        if not row["tokenId"]:
            continue
        markets.append(row)
        if len(markets) >= 30:
            break

    return {"source": "Polymarket Gamma API", "markets": markets, "count": len(markets)}


@router.get("/polymarket/history")
def get_polymarket_history(
    token_id: Annotated[str, Query(description="YES outcome token ID")],
    interval: Annotated[str, Query(description="max|1m|1w|1d|6h|1h")] = "1w",
) -> dict:
    """Get price (probability) history using the YES token ID."""
    if not token_id:
        raise HTTPException(status_code=400, detail="token_id is required")
    if interval not in {"max", "all", "1m", "1w", "1d", "6h", "1h"}:
        interval = "1w"

    try:
        resp = requests.get(
            f"{CLOB}/prices-history",
            params={"market": token_id, "interval": interval, "fidelity": 60},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CLOB API error: {e}")

    history = [
        {"t": int(p["t"]), "yes_prob": float(p.get("p", 0.5))}
        for p in data.get("history", [])
        if "t" in p
    ]
    return {"source": "Polymarket CLOB API", "history": history}


@router.get("/polymarket/price")
def get_polymarket_price(
    token_id: Annotated[str, Query(description="Token ID")],
) -> dict:
    """Get live midpoint price (probability) for a token."""
    try:
        resp = requests.get(f"{CLOB}/midpoint", params={"token_id": token_id}, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        # API returns {"mid": "0.755"} — field is "mid" not "mid_price"
        prob = float(data.get("mid", data.get("mid_price", 0.5)))
        return {"token_id": token_id, "yes_prob": prob, "source": "Polymarket CLOB API"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CLOB API error: {e}")


@router.get("/polymarket/orderbook")
def get_polymarket_orderbook(
    token_id: Annotated[str, Query(description="Token ID")],
) -> dict:
    """Get current order book top levels for a token."""
    try:
        resp = requests.get(f"{CLOB}/book", params={"token_id": token_id}, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return {
            "token_id": token_id,
            "bids": data.get("bids", [])[:6],
            "asks": data.get("asks", [])[:6],
            "last_trade_price": data.get("last_trade_price"),
            "timestamp": data.get("timestamp"),
            "source": "Polymarket CLOB API",
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CLOB API error: {e}")
