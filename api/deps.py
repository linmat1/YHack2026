"""Shared query parameter dependencies for FastAPI routers."""
from datetime import date
from typing import Annotated

from fastapi import Query

# Types only — defaults are set at each endpoint with `= value`
TickerQ = Annotated[str, Query(description="Ticker symbol, e.g. AAPL")]
StartQ = Annotated[date, Query(description="Start date (YYYY-MM-DD)")]
EndQ = Annotated[date, Query(description="End date (YYYY-MM-DD)")]
IntervalQ = Annotated[str, Query(description="yfinance interval, e.g. 1d, 1wk")]
DataModeQ = Annotated[str, Query(description="Auto | Live | Synthetic")]
RsiWindowQ = Annotated[int, Query(ge=5, le=30, description="RSI window")]
FastWindowQ = Annotated[int, Query(ge=5, le=20, description="MACD fast window")]
SlowWindowQ = Annotated[int, Query(ge=10, le=60, description="MACD slow window")]
TrendWindowQ = Annotated[int, Query(ge=10, le=40, description="Trend SMA window")]
LongTrendWindowQ = Annotated[int, Query(ge=20, le=120, description="Long trend SMA window")]
VolWindowQ = Annotated[int, Query(ge=5, le=40, description="Volatility window")]
FeeBpsQ = Annotated[int, Query(ge=0, le=100, description="Trading fee in basis points")]
StrategyQ = Annotated[str, Query(description="Strategy name")]
