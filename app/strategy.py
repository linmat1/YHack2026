from datetime import date

import numpy as np
import pandas as pd

from .data import get_data_cached
from .features import build_feature_lab


def validate_inputs(ticker: str, start_date: date, end_date: date) -> tuple[date, date]:
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("Please enter a ticker symbol.")
    if end_date > date.today():
        raise ValueError("End date cannot be in the future.")
    if start_date >= end_date:
        raise ValueError("Start date must be before end date.")
    return start_date, end_date


def apply_strategy(df: pd.DataFrame, strategy_name: str) -> tuple[pd.DataFrame, str]:
    signal_map = {
        "RSI": "RSI_Signal",
        "Trend": "Trend_Signal",
        "MACD": "MACD_Signal_Flag",
        "Breakout": "Breakout_Signal",
        "Ensemble": "EnsembleSignal",
    }
    signal_col = signal_map[strategy_name]
    out = df.copy()
    out["Signal"] = out[signal_col].fillna(0)
    return out, signal_col


def summarize_signal(strategy_df: pd.DataFrame, strategy_name: str) -> dict:
    non_zero = strategy_df[strategy_df["Signal"] != 0]
    last_signal = 0 if non_zero.empty else int(non_zero["Signal"].iloc[-1])
    current_rsi = float(strategy_df["RSI"].iloc[-1]) if pd.notna(strategy_df["RSI"].iloc[-1]) else np.nan

    if last_signal == 1:
        confidence = 0.0 if np.isnan(current_rsi) else max(0.0, min(100.0, (30 - current_rsi) / 30 * 100))
        return {
            "label": "BUY",
            "signal": last_signal,
            "confidence": confidence,
            "message": f"{strategy_name} has a bullish setup.",
            "css": "pill-buy",
        }
    if last_signal == -1:
        confidence = 0.0 if np.isnan(current_rsi) else max(0.0, min(100.0, (current_rsi - 70) / 30 * 100))
        return {
            "label": "SELL",
            "signal": last_signal,
            "confidence": confidence,
            "message": f"{strategy_name} has a bearish setup.",
            "css": "pill-sell",
        }
    return {
        "label": "WAIT",
        "signal": 0,
        "confidence": 0.0,
        "message": f"{strategy_name} is neutral right now.",
        "css": "pill-neutral",
    }


def run_backtest(feature_df: pd.DataFrame, signal_col: str, fee_bps: float) -> pd.DataFrame:
    bt = feature_df.copy()
    bt["SignalPosition"] = bt[signal_col].fillna(0).shift(1).fillna(0)
    bt["Turnover"] = bt["SignalPosition"].diff().abs().fillna(bt["SignalPosition"].abs())
    bt["StrategyReturn"] = bt["SignalPosition"] * bt["Return_1D"].fillna(0) - bt["Turnover"] * (fee_bps / 10000)
    bt["BuyHoldReturn"] = bt["Return_1D"].fillna(0)
    bt["StrategyEquity"] = (1 + bt["StrategyReturn"]).cumprod()
    bt["BuyHoldEquity"] = (1 + bt["BuyHoldReturn"]).cumprod()
    bt["StrategyDrawdown"] = bt["StrategyEquity"] / bt["StrategyEquity"].cummax() - 1
    return bt


def compute_stress_feed(feature_df: pd.DataFrame) -> pd.DataFrame:
    stress_events: list[tuple[pd.Timestamp, str, float]] = []
    median_vol = feature_df["Volatility_20D"].median()
    for idx, row in feature_df.dropna(subset=["Return_1D", "Volatility_20D", "RSI"]).iterrows():
        if abs(row["Return_1D"]) > 0.03:
            stress_events.append((idx, "Large daily move", row["Return_1D"]))
        if pd.notna(median_vol) and row["Volatility_20D"] > median_vol * 1.5:
            stress_events.append((idx, "Volatility spike", row["Volatility_20D"]))
        if row["Drawdown"] < -0.1:
            stress_events.append((idx, "Deep drawdown", row["Drawdown"]))
        if row["RSI"] < 30:
            stress_events.append((idx, "Oversold RSI", row["RSI"]))
        if row["RSI"] > 70:
            stress_events.append((idx, "Overbought RSI", row["RSI"]))
    return pd.DataFrame(stress_events, columns=["Date", "Event", "Value"]).drop_duplicates().tail(15)


def build_watchlist_pulse(
    watchlist: list[str],
    start_date: date,
    end_date: date,
    interval: str,
    data_mode: str,
    rsi_window: int,
    fast_window: int,
    slow_window: int,
    trend_window: int,
    long_trend_window: int,
    vol_window: int,
) -> pd.DataFrame:
    rows: list[dict] = []
    for symbol in watchlist:
        symbol_data, _ = get_data_cached(symbol, start_date, end_date, interval, data_mode)
        if symbol_data.empty:
            continue
        symbol_features = build_feature_lab(
            symbol_data,
            rsi_window,
            fast_window,
            slow_window,
            trend_window,
            long_trend_window,
            vol_window,
        )
        latest = symbol_features.iloc[-1]
        rows.append(
            {
                "Ticker": symbol,
                "Close": latest["Close"],
                "1D Return": latest["Return_1D"],
                "5D Return": latest["Return_5D"],
                "20D Return": latest["Return_20D"],
                "RSI": latest["RSI"],
                "20D Vol": latest["Volatility_20D"],
                "Drawdown": latest["Drawdown"],
                "Regime": latest["Regime"],
                "Ensemble Signal": latest["EnsembleSignal"],
                "Pulse Score": abs(latest["Return_5D"]) + abs(latest["MACD_Hist"]) + abs(latest["Drawdown"]),
            }
        )
    pulse = pd.DataFrame(rows)
    if pulse.empty:
        return pulse
    return pulse.sort_values("Pulse Score", ascending=False).reset_index(drop=True)
