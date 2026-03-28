from datetime import date

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


def generate_synthetic_data(ticker: str, start_date: date, end_date: date, interval: str) -> pd.DataFrame:
    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)
    freq_map = {
        "1h": "H",
        "1d": "B",
        "1wk": "W-FRI",
        "1mo": "MS",
        "1y": "YS",
    }
    freq = freq_map.get(interval, "B")
    idx = pd.date_range(start_ts, end_ts, freq=freq)
    if len(idx) < 90:
        idx = pd.date_range(start_ts, periods=160, freq="B")

    seed = sum(ord(ch) for ch in ticker) % (2**32 - 1)
    rng = np.random.default_rng(seed)
    drift = 0.0004 + (seed % 17) / 100000
    vol = 0.012 + (seed % 11) / 1000
    shocks = rng.normal(loc=drift, scale=vol, size=len(idx))
    close = 100 * np.exp(np.cumsum(shocks))
    open_ = np.concatenate([[close[0]], close[:-1]]) * (1 + rng.normal(0, 0.0025, len(idx)))
    high = np.maximum(open_, close) * (1 + rng.uniform(0.001, 0.015, len(idx)))
    low = np.minimum(open_, close) * (1 - rng.uniform(0.001, 0.015, len(idx)))
    volume = rng.integers(800_000, 5_000_000, len(idx))

    synthetic = pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Adj Close": close,
            "Volume": volume,
        },
        index=idx,
    )
    synthetic.index.name = "Date"
    return synthetic


@st.cache_data(show_spinner=False)
def get_data_cached(
    ticker: str,
    start_date: date,
    end_date: date,
    interval: str,
    data_mode: str,
) -> tuple[pd.DataFrame, str]:
    ticker = ticker.strip().upper()
    normalized_mode = data_mode.lower()
    data = pd.DataFrame()

    if normalized_mode in {"auto", "live"}:
        try:
            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                interval=interval,
                progress=False,
                auto_adjust=False,
                threads=False,
                timeout=4,
            )
        except Exception:
            data = pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    required_cols = {"Open", "High", "Low", "Close"}
    if not data.empty and required_cols.issubset(set(data.columns)):
        source = "Yahoo Finance"
    else:
        data = generate_synthetic_data(ticker, start_date, end_date, interval)
        source = "Synthetic Fallback"

    return data.sort_index(), source
