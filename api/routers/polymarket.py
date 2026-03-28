import json
import time
from typing import Annotated

import pandas as pd
import requests
from fastapi import APIRouter, Query

router = APIRouter(tags=["polymarket"])


def _fetch_markets(keyword: str) -> tuple[list[dict], str]:
    try:
        resp = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={"keyword": keyword, "active": "true", "limit": 20},
            timeout=6,
        )
        data = resp.json()
        for market in data:
            raw = market.get("outcomePrices", "[]")
            try:
                market["outcomePrices"] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                market["outcomePrices"] = ["0.5", "0.5"]
        return data, "Polymarket Gamma API"
    except Exception:
        return [], "Unavailable"


def _fetch_price_history(condition_id: str, lookback_days: int = 30) -> tuple[list[dict], str]:
    try:
        end_ts = int(time.time())
        start_ts = end_ts - lookback_days * 86400
        resp = requests.get(
            "https://clob.polymarket.com/prices-history",
            params={"market_id": condition_id, "startTs": start_ts, "endTs": end_ts, "fidelity": 60},
            timeout=6,
        )
        points = resp.json().get("history", [])
        return points, "Polymarket CLOB API"
    except Exception:
        return [], "Unavailable"


@router.get("/polymarket/markets")
def get_polymarket_markets(
    keyword: Annotated[str, Query(description="Search keyword, e.g. a ticker like AAPL")] = "AAPL",
) -> dict:
    markets, source = _fetch_markets(keyword)

    rows = []
    for m in markets:
        try:
            yes_prob = float(m["outcomePrices"][0])
        except (IndexError, ValueError, TypeError):
            yes_prob = 0.5
        vol = float(m.get("volume", 0) or 0)
        try:
            end_dt = pd.to_datetime(m["endDate"], utc=True)
            days_left = max(0, (end_dt - pd.Timestamp.now(tz="UTC")).days)
        except Exception:
            days_left = 0
        rows.append({
            "question": m.get("question", ""),
            "conditionId": m.get("conditionId", ""),
            "yes_prob": yes_prob,
            "volume": vol,
            "days_left": days_left,
        })

    rows.sort(key=lambda r: r["volume"], reverse=True)
    return {"source": source, "markets": rows}


@router.get("/polymarket/history")
def get_polymarket_history(
    condition_id: Annotated[str, Query(description="Polymarket condition ID")],
    lookback_days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> dict:
    points, source = _fetch_price_history(condition_id, lookback_days)
    history = [{"t": p["t"], "yes_prob": float(p.get("p", 0.5))} for p in points if "t" in p]
    return {"source": source, "history": history}
