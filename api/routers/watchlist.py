from typing import Annotated

from fastapi import APIRouter, Query

from app.strategy import build_watchlist_pulse
from ..deps import (
    DataModeQ, EndQ, FastWindowQ, IntervalQ, LongTrendWindowQ,
    RsiWindowQ, SlowWindowQ, StartQ, TrendWindowQ, VolWindowQ,
)

router = APIRouter(tags=["watchlist"])


@router.get("/watchlist")
def get_watchlist(
    tickers: Annotated[str, Query(description="Comma-separated tickers, e.g. AAPL,MSFT,NVDA")] = "AAPL,MSFT,NVDA,TSLA,SPY,QQQ",
    start: StartQ = None,
    end: EndQ = None,
    interval: IntervalQ = "1d",
    data_mode: DataModeQ = "Auto",
    rsi_window: RsiWindowQ = 14,
    fast_window: FastWindowQ = 12,
    slow_window: SlowWindowQ = 26,
    trend_window: TrendWindowQ = 20,
    long_trend_window: LongTrendWindowQ = 50,
    vol_window: VolWindowQ = 20,
) -> dict:
    from datetime import date, timedelta
    if start is None:
        start = date.today() - timedelta(days=365)
    if end is None:
        end = date.today()

    watchlist = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    pulse = build_watchlist_pulse(watchlist, start, end, interval, data_mode,
                                  rsi_window, fast_window, slow_window,
                                  trend_window, long_trend_window, vol_window)
    if pulse.empty:
        return {"rows": []}

    pulse = pulse.fillna(0)
    return {"rows": pulse.to_dict(orient="records")}
