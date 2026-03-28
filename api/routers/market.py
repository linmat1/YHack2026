from fastapi import APIRouter, HTTPException

from app.data import get_data_cached
from app.features import build_feature_lab
from ..deps import (
    DataModeQ, EndQ, FastWindowQ, IntervalQ, LongTrendWindowQ,
    RsiWindowQ, SlowWindowQ, StartQ, TickerQ, TrendWindowQ, VolWindowQ,
)

router = APIRouter(tags=["market"])


@router.get("/data")
def get_market_data(
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
) -> dict:
    ticker = ticker.strip().upper()
    data, source = get_data_cached(ticker, start, end, interval, data_mode)
    if data.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    features = build_feature_lab(data, rsi_window, fast_window, slow_window, trend_window, long_trend_window, vol_window)
    features = features.reset_index()
    features["Date"] = features["Date"].astype(str)

    ohlcv_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
    feature_cols = ["Date", "RSI", "MACD", "MACD_Hist", "BB_Upper", "BB_Lower",
                    "Volatility_20D", "Drawdown", "SMA_20", "SMA_50", "Return_1D",
                    "Return_5D", "Return_20D", "Regime"]

    ohlcv = features[[c for c in ohlcv_cols if c in features.columns]].to_dict(orient="records")
    feat = features[[c for c in feature_cols if c in features.columns]].to_dict(orient="records")

    return {"ticker": ticker, "source": source, "ohlcv": ohlcv, "features": feat}
