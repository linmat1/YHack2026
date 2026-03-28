from fastapi import APIRouter, HTTPException

from app.data import get_data_cached
from app.features import build_feature_lab
from app.strategy import apply_strategy, run_backtest
from ..deps import (
    DataModeQ, EndQ, FastWindowQ, FeeBpsQ, IntervalQ, LongTrendWindowQ,
    RsiWindowQ, SlowWindowQ, StartQ, StrategyQ, TickerQ, TrendWindowQ, VolWindowQ,
)

router = APIRouter(tags=["backtest"])


@router.get("/backtest")
def get_backtest(
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
    fee_bps: FeeBpsQ = 5,
) -> dict:
    ticker = ticker.strip().upper()
    data, _ = get_data_cached(ticker, start, end, interval, data_mode)
    if data.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    features = build_feature_lab(data, rsi_window, fast_window, slow_window, trend_window, long_trend_window, vol_window)
    strategy_data, signal_col = apply_strategy(features, strategy)
    bt = run_backtest(strategy_data, signal_col, fee_bps)

    df = bt.reset_index()
    df["Date"] = df["Date"].astype(str)
    equity_curve = df[["Date", "StrategyEquity", "BuyHoldEquity", "StrategyDrawdown"]].to_dict(orient="records")

    return {
        "metrics": {
            "strategy_return": float(bt["StrategyEquity"].iloc[-1] - 1),
            "buyhold_return": float(bt["BuyHoldEquity"].iloc[-1] - 1),
            "max_drawdown": float(bt["StrategyDrawdown"].min()),
            "hit_rate": float((bt["StrategyReturn"] > 0).mean()),
            "days_in_market": int((bt["SignalPosition"] != 0).sum()),
            "signal_changes": int(bt["Turnover"].sum()),
        },
        "equity_curve": equity_curve,
    }
