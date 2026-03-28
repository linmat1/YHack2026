from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.data import get_data_cached
from app.features import build_feature_lab
from app.fusion import (
    aggregate_pm_features,
    build_scenarios,
    fetch_and_tag_markets,
    fuse_signals,
    run_backtest_variants,
    summarize_backtest_variants,
)
from ..deps import (
    DataModeQ, EndQ, FastWindowQ, FeeBpsQ, IntervalQ, LongTrendWindowQ,
    RsiWindowQ, SlowWindowQ, StartQ, TickerQ, TrendWindowQ, VolWindowQ,
)

router = APIRouter(tags=["fusion"])

_SERIES_COLS = [
    "Date", "Close", "TechnicalScore", "TechnicalConfidence", "BaseDirection",
    "YES_Mid", "PM_Spread", "CautionScore", "FinalConfidence",
    "RiskZone", "PositionSize", "FinalAction", "PMAgreement",
]
_EQUITY_COLS = ["Date", "TechOnlyEquity", "PMFilteredEquity", "PMSizedEquity"]


@router.get("/fusion")
def get_fusion(
    ticker: TickerQ,
    start: StartQ,
    end: EndQ,
    interval: IntervalQ = "1d",
    data_mode: DataModeQ = "Auto",
    rsi_window: RsiWindowQ = 14,
    fast_window: FastWindowQ = 12,
    slow_window: SlowWindowQ = 26,
    trend_window: TrendWindowQ = 20,
    long_trend_window: LongTrendWindowQ = 50,
    vol_window: VolWindowQ = 20,
    fee_bps: FeeBpsQ = 5,
    keyword: Annotated[str, Query(description="Polymarket search keyword (defaults to ticker)")] = "",
) -> dict:
    ticker = ticker.strip().upper()
    data, source = get_data_cached(ticker, start, end, interval, data_mode)
    if data.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    features = build_feature_lab(
        data, rsi_window, fast_window, slow_window,
        trend_window, long_trend_window, vol_window,
    )

    pm_keyword = keyword.strip() or ticker
    tagged = fetch_and_tag_markets(pm_keyword)
    pm_agg = aggregate_pm_features(tagged)

    fused = fuse_signals(features, pm_agg)
    bt    = run_backtest_variants(fused, fee_bps)
    bt_summary = summarize_backtest_variants(bt)

    # Time series
    ts_df = fused.reset_index()
    ts_df["Date"] = ts_df["Date"].astype(str)
    time_series = ts_df[[c for c in _SERIES_COLS if c in ts_df.columns]].to_dict(orient="records")

    # Equity curves
    bt_df = bt.reset_index()
    bt_df["Date"] = bt_df["Date"].astype(str)
    equity_curves = bt_df[[c for c in _EQUITY_COLS if c in bt_df.columns]].to_dict(orient="records")

    # Latest decision row
    latest = fused.iloc[-1]
    decision = {
        "ticker":               ticker,
        "base_direction":       str(latest.get("BaseDirection", "Flat")),
        "technical_score":      round(float(latest.get("TechnicalScore", 0)), 3),
        "technical_confidence": round(float(latest.get("TechnicalConfidence", 0)), 1),
        "caution_score":        round(float(latest.get("CautionScore", 0)), 1),
        "risk_zone":            str(latest.get("RiskZone", "Unknown")),
        "final_confidence":     round(float(latest.get("FinalConfidence", 0)), 1),
        "position_size":        float(latest.get("PositionSize", 0)),
        "final_action":         str(latest.get("FinalAction", "No Trade")),
        "pm_agreement":         bool(latest.get("PMAgreement", 0)),
        "yes_mid":              round(float(latest.get("YES_Mid", 0.5)), 3),
    }

    # Top tagged markets
    tagged_markets: list[dict] = []
    if not tagged.empty:
        for _, row in tagged.head(10).iterrows():
            tagged_markets.append({
                "question":          str(row.get("question", "")),
                "direction":         str(row.get("direction", "")),
                "theme":             str(row.get("theme", "")),
                "mid":               round(float(row.get("mid", 0.5)), 3),
                "days_to_resolution": int(row.get("days_to_resolution", 0)),
            })

    return {
        "ticker":           ticker,
        "source":           source,
        "decision":         decision,
        "pm_aggregate":     pm_agg,
        "time_series":      time_series,
        "equity_curves":    equity_curves,
        "backtest_variants": bt_summary,
        "tagged_markets":   tagged_markets,
    }


@router.get("/fusion/scenarios")
def get_fusion_scenarios(
    ticker: TickerQ,
    start: StartQ,
    end: EndQ,
    interval: IntervalQ = "1d",
    data_mode: DataModeQ = "Auto",
    rsi_window: RsiWindowQ = 14,
    fast_window: FastWindowQ = 12,
    slow_window: SlowWindowQ = 26,
    trend_window: TrendWindowQ = 20,
    long_trend_window: LongTrendWindowQ = 50,
    vol_window: VolWindowQ = 20,
    keyword: Annotated[str, Query(description="Polymarket search keyword")] = "",
) -> dict:
    ticker = ticker.strip().upper()
    data, _ = get_data_cached(ticker, start, end, interval, data_mode)
    if data.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    features = build_feature_lab(
        data, rsi_window, fast_window, slow_window,
        trend_window, long_trend_window, vol_window,
    )
    pm_keyword = keyword.strip() or ticker
    tagged     = fetch_and_tag_markets(pm_keyword)
    pm_agg     = aggregate_pm_features(tagged)
    fused      = fuse_signals(features, pm_agg)
    latest     = fused.iloc[-1]

    return {"ticker": ticker, "scenarios": build_scenarios(latest, pm_agg)}
