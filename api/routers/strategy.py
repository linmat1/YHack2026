from fastapi import APIRouter, HTTPException

from app.data import get_data_cached
from app.features import build_feature_lab
from app.strategy import apply_strategy, summarize_signal
from ..deps import (
    DataModeQ, EndQ, FastWindowQ, IntervalQ, LongTrendWindowQ,
    RsiWindowQ, SlowWindowQ, StartQ, StrategyQ, TickerQ, TrendWindowQ, VolWindowQ,
)

router = APIRouter(tags=["strategy"])


@router.get("/strategy")
def get_strategy(
    ticker: TickerQ,
    start: StartQ,
    end: EndQ,
    interval: IntervalQ = "1d",
    data_mode: DataModeQ = "Auto",
    strategy: StrategyQ = "Ensemble",
    rsi_window: RsiWindowQ = 14,
    fast_window: FastWindowQ = 12,
    slow_window: SlowWindowQ = 26,
    trend_window: TrendWindowQ = 20,
    long_trend_window: LongTrendWindowQ = 50,
    vol_window: VolWindowQ = 20,
) -> dict:
    ticker = ticker.strip().upper()
    data, source = get_data_cached(ticker, start, end, interval, data_mode)
    if data.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    features = build_feature_lab(data, rsi_window, fast_window, slow_window, trend_window, long_trend_window, vol_window)
    strategy_data, signal_col = apply_strategy(features, strategy)
    summary = summarize_signal(strategy_data, strategy)

    df = strategy_data.reset_index()
    df["Date"] = df["Date"].astype(str)
    signals = df[["Date", "Close", "Signal"]].to_dict(orient="records")

    return {
        "ticker": ticker,
        "source": source,
        "signal_col": signal_col,
        "signals": signals,
        "summary": summary,
    }
