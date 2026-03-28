"""Polymarket-augmented signal fusion layer.

Implements the architecture from yhack_prediction_market_dashboard_lab.ipynb:
  1. fetch_and_tag_markets  — pull Polymarket markets, tag direction/theme/quality
  2. aggregate_pm_features  — scalar sentiment summary from tagged markets
  3. simulate_pm_history    — synthetic daily prob series aligned to price data
  4. fuse_signals           — combine technical + PM into FinalConfidence / FinalAction
  5. build_scenarios        — sensitivity table under market stress scenarios
  6. run_backtest_variants  — TechOnly vs PM-filtered vs PM-sized equity curves
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import requests

# ── Keyword maps ──────────────────────────────────────────────────────────────

_SEARCH_TERMS: dict[str, list[str]] = {
    "BTC":     ["bitcoin", "btc", "crypto reserve", "bitcoin reserve", "bitcoin etf"],
    "BTC-USD": ["bitcoin", "btc", "crypto reserve", "bitcoin reserve", "bitcoin etf"],
    "ETH":     ["ethereum", "eth", "ether etf"],
    "ETH-USD": ["ethereum", "eth", "ether etf"],
    "SOL":     ["solana", "sol", "sol etf"],
    "SOL-USD": ["solana", "sol", "sol etf"],
    "TSLA":    ["tesla", "tsla", "elon", "cybertruck"],
    "AAPL":    ["apple", "aapl", "iphone"],
    "NVDA":    ["nvidia", "nvda", "ai chips", "jensen"],
    "SPY":     ["sp500", "s&p", "stock market", "recession"],
    "QQQ":     ["nasdaq", "qqq", "tech stocks"],
}

_BULLISH_KW = ["above", "hit", "reach", "approved", "bull", "all-time high", "new high",
               "reserve", "etf", "surge", "rally", "breakout"]
_BEARISH_KW = ["below", "ban", "collapse", "hack", "recession", "crash", "bear",
               "down", "drop", "slump", "bankruptcy"]

_THEME_KEYWORDS: dict[str, list[str]] = {
    "price":      ["above", "below", "hit", "reach", "$", "price"],
    "regulation": ["sec", "regulation", "ban", "approval", "approved", "reserve"],
    "macro":      ["fed", "rates", "recession", "inflation", "treasury"],
    "adoption":   ["etf", "fund", "treasury", "reserve", "adoption"],
    "risk":       ["hack", "collapse", "bankruptcy", "attack", "outage"],
}

GAMMA_URL = "https://gamma-api.polymarket.com"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _search_terms_for(ticker: str) -> list[str]:
    base = ticker.upper().split("-")[0]
    return _SEARCH_TERMS.get(ticker.upper(), _SEARCH_TERMS.get(base, [ticker.lower()]))


def _safe_normalize(s: pd.Series) -> pd.Series:
    filled = s.fillna(s.median() if s.notna().any() else 0.0)
    mx = filled.max()
    return (filled / mx) if mx > 0 else pd.Series(0.0, index=s.index)


def _infer_direction(text: str) -> str:
    t = text.lower()
    bull = sum(k in t for k in _BULLISH_KW)
    bear = sum(k in t for k in _BEARISH_KW)
    if bull > bear:
        return "bullish"
    if bear > bull:
        return "bearish"
    return "ambiguous"


def _infer_theme(text: str) -> str:
    t = text.lower()
    scores = {theme: sum(k in t for k in kws) for theme, kws in _THEME_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "other"


def _minmax(series: pd.Series) -> pd.Series:
    s = series.replace([np.inf, -np.inf], np.nan).ffill().bfill()
    if s.nunique(dropna=False) <= 1:
        return pd.Series(0.0, index=s.index)
    return (s - s.min()) / (s.max() - s.min())


# ── Polymarket fetch + tagging ────────────────────────────────────────────────

def fetch_and_tag_markets(ticker: str, limit: int = 60) -> pd.DataFrame:
    """Fetch Polymarket markets relevant to *ticker* and tag them with direction/theme/quality."""
    search_terms = _search_terms_for(ticker)
    per_term = max(limit // min(len(search_terms), 3), 20)

    all_rows: list[dict] = []
    for term in search_terms[:3]:
        try:
            resp = requests.get(
                f"{GAMMA_URL}/markets",
                params={"keyword": term, "active": "true", "closed": "false", "limit": per_term},
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                all_rows.extend(data)
        except Exception:
            continue

    if not all_rows:
        return pd.DataFrame()

    # Deduplicate
    seen: set[str] = set()
    unique = []
    for m in all_rows:
        cid = str(m.get("conditionId") or m.get("slug") or "")
        if cid and cid not in seen:
            seen.add(cid)
            unique.append(m)

    rows = []
    for m in unique:
        prices_raw = m.get("outcomePrices", "[]")
        try:
            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else (prices_raw or [])
        except Exception:
            prices = []
        yes_prob = float(prices[0]) if prices else 0.5

        try:
            end_dt = pd.to_datetime(m.get("endDate"), utc=True)
            days_left = max(0, (end_dt - pd.Timestamp.now(tz="UTC")).days)
        except Exception:
            days_left = 30

        question = str(m.get("question", ""))
        rows.append({
            "question":          question,
            "mid":               yes_prob,
            "spread":            float(m.get("spread") or 0.04),
            "liquidity":         float(m.get("liquidity") or 0),
            "volume":            float(m.get("volume") or 0),
            "days_to_resolution": days_left,
            "direction":         _infer_direction(question),
            "theme":             _infer_theme(question),
        })

    board = pd.DataFrame(rows)
    if board.empty:
        return board

    board["direction_sign"] = board["direction"].map({"bullish": 1, "bearish": -1, "ambiguous": 0})
    board["market_quality_score"] = (
        0.45 * _safe_normalize(board["liquidity"])
        + 0.35 * _safe_normalize(board["volume"])
        + 0.20 * (1 - _safe_normalize(board["spread"]))
    )
    return board.sort_values("market_quality_score", ascending=False).reset_index(drop=True)


def aggregate_pm_features(tagged: pd.DataFrame) -> dict:
    """Collapse tagged-markets DataFrame into a single scalar feature dict."""
    if tagged.empty:
        return {
            "pm_bullish_mean":                0.5,
            "pm_bearish_mean":                0.5,
            "pm_net_sentiment":               0.0,
            "pm_liquidity_weighted_sentiment": 0.0,
            "pm_avg_spread":                  0.04,
            "pm_total_liquidity":             0.0,
            "pm_total_volume":                0.0,
            "pm_dispersion":                  0.0,
            "pm_event_risk":                  0.0,
            "pm_market_quality":              0.5,
            "pm_conflict_score":              0.0,
            "pm_market_count":                0,
        }

    bullish = tagged[tagged["direction"] == "bullish"]
    bearish = tagged[tagged["direction"] == "bearish"]

    contrib = tagged["direction_sign"] * tagged["mid"].fillna(0)
    liq = tagged["liquidity"].fillna(1)
    weighted_sent = float(np.average(contrib, weights=liq) if liq.sum() > 0 else 0.0)

    near_term_max = tagged["days_to_resolution"].clip(lower=0).max()
    near_term = 1 - tagged["days_to_resolution"].clip(lower=0) / max(near_term_max, 1)

    return {
        "pm_bullish_mean":                float(bullish["mid"].mean()) if not bullish.empty else 0.5,
        "pm_bearish_mean":                float(bearish["mid"].mean()) if not bearish.empty else 0.5,
        "pm_net_sentiment":               float(contrib.mean()),
        "pm_liquidity_weighted_sentiment": weighted_sent,
        "pm_avg_spread":                  float(tagged["spread"].mean()),
        "pm_total_liquidity":             float(tagged["liquidity"].fillna(0).sum()),
        "pm_total_volume":                float(tagged["volume"].fillna(0).sum()),
        "pm_dispersion":                  float(tagged["mid"].fillna(0).std() or 0.0),
        "pm_event_risk":                  float(near_term.mean()),
        "pm_market_quality":              float(tagged["market_quality_score"].mean()),
        "pm_conflict_score":              float(abs(
            (bullish["mid"].mean() if not bullish.empty else 0.5) -
            (bearish["mid"].mean() if not bearish.empty else 0.5)
        )),
        "pm_market_count":                int(len(tagged)),
    }


# ── Simulate PM probability history ──────────────────────────────────────────

def simulate_pm_history(
    feature_df: pd.DataFrame,
    pm_agg: dict,
    resolution_days: int = 60,
) -> pd.DataFrame:
    """Generate a synthetic daily YES-probability series anchored to pm_agg snapshot."""
    n = len(feature_df)
    base_prob = float(np.clip(
        0.50 + 0.40 * (pm_agg.get("pm_liquidity_weighted_sentiment") or 0),
        0.05, 0.95,
    ))
    spread_anchor = float(pm_agg.get("pm_avg_spread") or 0.04)
    volume_anchor = max(float(pm_agg.get("pm_total_volume") or 250_000), 50_000)

    spot_driver    = feature_df["Return_1D"].fillna(0).rolling(3).sum().fillna(0)
    vol_driver     = feature_df["Volatility_20D"].fillna(feature_df["Volatility_20D"].median()).fillna(0)
    drawdown_driver = feature_df["Drawdown"].fillna(0)

    net_sign = np.sign(pm_agg.get("pm_net_sentiment") or 0)
    anchor_prob = float(np.clip(base_prob + 0.05 * net_sign, 0.05, 0.95))
    anchor_logit = np.log(anchor_prob / (1 - anchor_prob))

    latent = np.zeros(n)
    latent[0] = np.log(base_prob / (1 - base_prob))
    rng = np.random.default_rng(123)
    for i in range(1, n):
        latent[i] = (
            0.94 * latent[i - 1]
            + 0.03 * anchor_logit
            + 1.50 * float(spot_driver.iloc[i])
            - 0.45 * float(vol_driver.iloc[i])
            + 0.30 * float(drawdown_driver.iloc[i])
            + rng.normal(0, 0.08)
        )

    yes_mid = np.clip(1 / (1 + np.exp(-latent)), 0.03, 0.97)
    spread = np.clip(
        spread_anchor
        + 0.18 * vol_driver.rank(pct=True).fillna(0.5)
        + 0.02 * feature_df["Return_1D"].fillna(0).abs(),
        0.01, 0.20,
    )

    pm = pd.DataFrame(index=feature_df.index)
    pm["YES_Mid"]              = yes_mid
    pm["YES_Bid"]              = np.clip(yes_mid - spread / 2, 0.01, 0.99)
    pm["YES_Ask"]              = np.clip(yes_mid + spread / 2, 0.01, 0.99)
    pm["PM_Spread"]            = pm["YES_Ask"] - pm["YES_Bid"]
    pm["ProbMomentum_5D"]      = pm["YES_Mid"].diff(5)
    pm["ProbVol_10D"]          = pm["YES_Mid"].diff().rolling(10).std()
    pm["DaysToResolution"]     = np.linspace(resolution_days, 0, n).clip(min=0)
    pm["EventProximity"]       = 1 - pm["DaysToResolution"] / max(resolution_days, 1)
    pm["ProbSpotDivergence"]   = (
        pm["YES_Mid"].pct_change().replace([np.inf, -np.inf], np.nan)
        - feature_df["Return_1D"].fillna(0)
    )
    return pm


# ── Main fusion function ──────────────────────────────────────────────────────

def fuse_signals(
    feature_df: pd.DataFrame,
    pm_agg: dict,
    confidence_trade_threshold: float = 35.0,
    pm_confirmation_threshold: float = 0.05,
    avoid_threshold: float = 75.0,
) -> pd.DataFrame:
    """Return feature_df extended with risk scores, FinalConfidence, PositionSize, FinalAction."""
    fused = feature_df.copy()
    pm_history = simulate_pm_history(feature_df, pm_agg)
    fused = fused.join(pm_history)

    # Risk scores (0–100)
    fused["VolSpikeScore"]     = 100 * _minmax(fused["Volatility_20D"])
    fused["DrawdownScore"]     = 100 * _minmax(fused["Drawdown"].abs())
    fused["SpreadStressScore"] = 100 * _minmax(fused["PM_Spread"])
    fused["ProbWhipsawScore"]  = 100 * _minmax(fused["ProbVol_10D"].fillna(0))
    fused["EventRiskScore"]    = 100 * _minmax(fused["EventProximity"])
    fused["DivergenceScore"]   = 100 * _minmax(fused["ProbSpotDivergence"].abs().fillna(0))

    pm_sent      = float(pm_agg.get("pm_liquidity_weighted_sentiment") or 0)
    pm_quality   = float(pm_agg.get("pm_market_quality") or 0)
    pm_conflict  = float(pm_agg.get("pm_dispersion") or 0)

    fused["PMConfirmationScore"] = 100 * float(np.clip(0.5 + 0.5 * pm_sent, 0, 1))
    fused["PMQualityScore"]      = 100 * float(np.clip(pm_quality, 0, 1))
    fused["PMConflictPenalty"]   = 100 * float(np.clip(pm_conflict, 0, 1))

    fused["CautionScore"] = (
        0.24 * fused["VolSpikeScore"]
        + 0.18 * fused["DrawdownScore"]
        + 0.16 * fused["SpreadStressScore"]
        + 0.14 * fused["ProbWhipsawScore"]
        + 0.14 * fused["EventRiskScore"]
        + 0.14 * fused["DivergenceScore"]
    )

    fused["FinalConfidence"] = np.clip(
        0.55 * fused["TechnicalConfidence"]
        + 0.25 * fused["PMConfirmationScore"]
        + 0.10 * fused["PMQualityScore"]
        - 0.10 * fused["PMConflictPenalty"]
        - 0.25 * fused["CautionScore"],
        0, 100,
    )

    fused["RiskZone"] = pd.cut(
        fused["CautionScore"],
        bins=[-np.inf, 30, 55, avoid_threshold, np.inf],
        labels=["Tradeable", "Cautious", "High Risk", "Avoid"],
    ).astype(str)

    fused["PositionSize"] = np.select(
        [
            fused["FinalConfidence"] < confidence_trade_threshold,
            (fused["FinalConfidence"] >= confidence_trade_threshold) & (fused["FinalConfidence"] < 55),
            (fused["FinalConfidence"] >= 55) & (fused["FinalConfidence"] < 70),
            (fused["FinalConfidence"] >= 70) & (fused["FinalConfidence"] < 85),
            fused["FinalConfidence"] >= 85,
        ],
        [0.0, 0.25, 0.50, 0.75, 1.0],
        default=0.0,
    )
    fused.loc[fused["RiskZone"] == "Avoid", "PositionSize"] = 0.0

    fused["PMAgreement"] = np.select(
        [
            (fused["BaseDirection"] == "Long") & (pm_sent > pm_confirmation_threshold),
            (fused["BaseDirection"] == "Short") & (pm_sent < -pm_confirmation_threshold),
        ],
        [1, 1],
        default=0,
    )

    fused["FinalAction"] = np.select(
        [
            (fused["BaseDirection"] == "Long") & (fused["PositionSize"] > 0),
            (fused["BaseDirection"] == "Short") & (fused["PositionSize"] > 0),
        ],
        ["Long", "Short"],
        default="No Trade",
    )
    return fused


# ── Scenario analysis ─────────────────────────────────────────────────────────

def _scenario(
    latest: pd.Series,
    pm_agg: dict,
    sentiment_shift: float,
    spread_mult: float,
    event_risk_shift: float,
    confidence_trade_threshold: float = 35.0,
    avoid_threshold: float = 75.0,
) -> dict:
    pm_sent     = float(np.clip((pm_agg.get("pm_liquidity_weighted_sentiment") or 0) + sentiment_shift, -1, 1))
    pm_quality  = float(pm_agg.get("pm_market_quality") or 0)
    pm_conflict = float(pm_agg.get("pm_dispersion") or 0)

    adj_caution = float(np.clip(
        latest["CautionScore"] + 20 * (spread_mult - 1) + 20 * event_risk_shift,
        0, 100,
    ))
    confidence = float(np.clip(
        0.55 * latest["TechnicalConfidence"]
        + 25 * float(np.clip(0.5 + 0.5 * pm_sent, 0, 1))
        + 10 * pm_quality
        - 10 * pm_conflict
        - 0.25 * adj_caution,
        0, 100,
    ))

    if confidence < confidence_trade_threshold or adj_caution >= avoid_threshold:
        action, size = "No Trade", 0.0
    else:
        direction = str(latest.get("BaseDirection", "Flat"))
        action = direction if direction in {"Long", "Short"} else "No Trade"
        size = 0.25 if confidence < 55 else 0.50 if confidence < 70 else 0.75 if confidence < 85 else 1.0

    return {
        "FinalConfidence":  round(confidence, 1),
        "AdjustedCaution":  round(adj_caution, 1),
        "FinalAction":      action,
        "PositionSize":     size,
    }


def build_scenarios(latest: pd.Series, pm_agg: dict) -> list[dict]:
    kw: dict = {}
    return [
        {"Scenario": "Base",                     **_scenario(latest, pm_agg,  0.00, 1.0,  0.0, **kw)},
        {"Scenario": "PM sentiment +10%",         **_scenario(latest, pm_agg,  0.10, 1.0,  0.0, **kw)},
        {"Scenario": "PM sentiment −10%",         **_scenario(latest, pm_agg, -0.10, 1.0,  0.0, **kw)},
        {"Scenario": "Spreads widen ×1.6",        **_scenario(latest, pm_agg,  0.00, 1.6,  0.0, **kw)},
        {"Scenario": "Event risk +40%",           **_scenario(latest, pm_agg,  0.00, 1.0,  0.4, **kw)},
        {"Scenario": "Improved PM + lower risk",  **_scenario(latest, pm_agg,  0.12, 0.9, -0.2, **kw)},
    ]


# ── Backtest variants ─────────────────────────────────────────────────────────

def _dir_to_pos(d: str) -> float:
    return {"Long": 1.0, "Short": -1.0, "Flat": 0.0, "No Trade": 0.0}.get(d, 0.0)


def run_backtest_variants(fused_df: pd.DataFrame, fee_bps: float = 5.0) -> pd.DataFrame:
    bt = fused_df.copy()
    bt["BasePosition"] = bt["BaseDirection"].map(_dir_to_pos).fillna(0.0)
    r1d = bt["Return_1D"].fillna(0)

    for label, raw_signal in [
        ("TechOnly",    bt["BasePosition"]),
        ("PMFiltered",  np.where((bt["PMAgreement"] == 1) & (bt["FinalConfidence"] >= 35), bt["BasePosition"], 0.0)),
        ("PMSized",     bt["BasePosition"] * bt["PositionSize"]),
    ]:
        pos      = pd.Series(raw_signal, index=bt.index).shift(1).fillna(0)
        turnover = pos.diff().abs().fillna(pos.abs())
        ret      = pos * r1d - turnover * (fee_bps / 10_000)
        bt[f"{label}Position"] = pos
        bt[f"{label}Return"]   = ret
        bt[f"{label}Equity"]   = (1 + ret).cumprod()

    return bt


def summarize_backtest_variants(bt: pd.DataFrame) -> list[dict]:
    out = []
    for variant, ret_col, eq_col, pos_col in [
        ("Technical Only",       "TechOnlyReturn",   "TechOnlyEquity",   "TechOnlyPosition"),
        ("Technical + PM Filter","PMFilteredReturn",  "PMFilteredEquity", "PMFilteredPosition"),
        ("Technical + PM Sizing","PMSizedReturn",     "PMSizedEquity",    "PMSizedPosition"),
    ]:
        eq  = bt[eq_col]
        ret = bt[ret_col]
        dd  = eq / eq.cummax() - 1
        out.append({
            "variant":      variant,
            "total_return": float(eq.iloc[-1] - 1),
            "max_drawdown": float(dd.min()),
            "hit_rate":     float((ret > 0).mean()),
            "avg_exposure": float(bt[pos_col].abs().mean()),
        })
    return out
