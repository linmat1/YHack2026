import time
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error


st.set_page_config(
    page_title="Rentwise Quant Lab",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800&family=Barlow:wght@300;400;600;700&family=JetBrains+Mono:wght@300;400;500;600&display=swap');

        :root {
            --bg-base: #08090f;
            --bg-panel: #0f1018;
            --bg-panel-2: #141520;
            --accent: #d97706;
            --accent-bright: #f59e0b;
            --accent-sky: #38bdf8;
            --buy: #22c55e;
            --sell: #f43f5e;
            --text: #f0f4f8;
            --muted: #8892a4;
            --faint: #4a5568;
            --border: rgba(255,255,255,0.07);
            --border-amber: rgba(217,119,6,0.3);
        }

        html, body, .stApp {
            font-family: 'Barlow', sans-serif;
            color: var(--text);
        }

        .stApp {
            background:
                radial-gradient(ellipse at 15% 8%, rgba(217,119,6,0.08) 0%, transparent 48%),
                radial-gradient(ellipse at 85% 88%, rgba(56,189,248,0.05) 0%, transparent 48%),
                var(--bg-base);
        }

        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
        }

        /* HERO */
        .hero {
            padding: 1.8rem 2.2rem 1.5rem;
            border-radius: 2px;
            background: linear-gradient(135deg, #0f1018 0%, #13152a 100%);
            border: 1px solid var(--border-amber);
            border-left: 4px solid var(--accent-bright);
            margin-bottom: 1.4rem;
            position: relative;
            overflow: hidden;
        }

        .hero::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 1px;
            background: linear-gradient(90deg, var(--accent-bright) 0%, var(--accent-sky) 55%, transparent 100%);
        }

        .hero-eyebrow {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.68rem;
            color: var(--accent);
            letter-spacing: 0.2em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }

        .hero h1 {
            margin: 0;
            font-family: 'Barlow Condensed', sans-serif;
            font-weight: 800;
            font-size: 2.9rem;
            line-height: 1.0;
            color: var(--text);
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }

        .hero h1 .hl { color: var(--accent-bright); }

        .hero-meta {
            margin-top: 0.7rem;
            font-size: 0.86rem;
            color: var(--muted);
            display: flex;
            align-items: center;
            gap: 0.8rem;
            flex-wrap: wrap;
        }

        .live-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.18rem 0.6rem;
            background: rgba(34,197,94,0.1);
            border: 1px solid rgba(34,197,94,0.35);
            border-radius: 2px;
            color: #22c55e;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.16em;
        }

        .live-badge::before {
            content: '';
            width: 5px;
            height: 5px;
            background: #22c55e;
            border-radius: 50%;
            animation: blink-dot 2s ease-in-out infinite;
        }

        @keyframes blink-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.15; }
        }

        /* GLASS CARD */
        .glass-card {
            padding: 1.2rem 1.4rem;
            border-radius: 2px;
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-left: 3px solid var(--accent-sky);
            margin-bottom: 0.9rem;
        }

        /* METRIC CARD */
        .metric-card {
            padding: 1rem 1.2rem 1.1rem;
            border-radius: 2px;
            background: var(--bg-panel);
            border: 1px solid var(--border);
            border-top: 2px solid var(--accent-bright);
            min-height: 110px;
        }

        .metric-label {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.66rem;
            color: var(--faint);
            text-transform: uppercase;
            letter-spacing: 0.18em;
            margin-bottom: 0.35rem;
        }

        .metric-value {
            font-family: 'Barlow Condensed', sans-serif;
            font-weight: 700;
            font-size: 2.1rem;
            color: var(--text);
            line-height: 1.1;
            letter-spacing: -0.01em;
        }

        .metric-sub {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.71rem;
            color: var(--muted);
            margin-top: 0.35rem;
        }

        /* SIGNAL PILLS */
        .pill-buy, .pill-sell, .pill-neutral {
            display: inline-flex;
            align-items: center;
            padding: 0.38rem 0.9rem;
            border-radius: 2px;
            font-family: 'Barlow Condensed', sans-serif;
            font-weight: 700;
            font-size: 1rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }

        .pill-buy {
            background: rgba(34,197,94,0.1);
            color: #86efac;
            border: 1px solid rgba(34,197,94,0.32);
            border-left: 3px solid #22c55e;
        }

        .pill-sell {
            background: rgba(244,63,94,0.1);
            color: #fda4af;
            border: 1px solid rgba(244,63,94,0.32);
            border-left: 3px solid #f43f5e;
        }

        .pill-neutral {
            background: rgba(245,158,11,0.1);
            color: #fcd34d;
            border: 1px solid rgba(245,158,11,0.28);
            border-left: 3px solid var(--accent-bright);
        }

        /* TYPOGRAPHY */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Barlow Condensed', sans-serif !important;
            font-weight: 700 !important;
            letter-spacing: 0.03em !important;
            text-transform: uppercase !important;
            color: var(--text) !important;
        }

        p, label, span, div {
            color: inherit;
        }

        .stMarkdown, .stText, .stCaption {
            color: var(--text) !important;
        }

        [data-testid="stMetricLabel"] {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.7rem !important;
            color: var(--faint) !important;
            text-transform: uppercase !important;
            letter-spacing: 0.13em !important;
        }

        [data-testid="stMetricValue"] {
            font-family: 'Barlow Condensed', sans-serif !important;
            font-weight: 700 !important;
            font-size: 1.9rem !important;
            color: var(--text) !important;
        }

        /* TABS */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.15rem;
            background: var(--bg-panel);
            border-radius: 2px;
            padding: 0.25rem;
            border: 1px solid var(--border);
        }

        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border-radius: 2px;
            padding: 0.5rem 1rem;
            color: var(--muted) !important;
            font-family: 'Barlow', sans-serif;
            font-weight: 600;
            font-size: 0.8rem;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            border: none !important;
        }

        .stTabs [aria-selected="true"] {
            background: var(--accent-bright) !important;
            color: #07080f !important;
            border-bottom: none !important;
        }

        /* BUTTONS */
        .stButton > button {
            background: transparent !important;
            color: var(--text) !important;
            border: 1px solid var(--border-amber) !important;
            border-radius: 2px !important;
            font-family: 'Barlow', sans-serif !important;
            font-weight: 700 !important;
            font-size: 0.8rem !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            transition: all 0.14s ease !important;
            box-shadow: none !important;
        }

        .stButton > button:hover {
            background: var(--accent-bright) !important;
            color: #08090f !important;
            border-color: var(--accent-bright) !important;
        }

        .stButton > button p,
        .stButton > button span,
        .stButton > button div {
            color: inherit !important;
        }

        /* INPUTS */
        .stTextInput input,
        .stTextArea textarea,
        .stDateInput input,
        .stSelectbox [data-baseweb="select"] > div,
        .stNumberInput input {
            background: rgba(255,255,255,0.95) !important;
            color: #0d0e1a !important;
            border-radius: 2px !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.86rem !important;
        }

        .stTextInput label,
        .stTextArea label,
        .stDateInput label,
        .stSelectbox label,
        .stRadio label,
        .stSlider label,
        .stCheckbox label {
            color: #2a2e42 !important;
            font-family: 'Barlow', sans-serif !important;
            font-weight: 700 !important;
            font-size: 0.76rem !important;
            letter-spacing: 0.07em !important;
            text-transform: uppercase !important;
        }

        /* SIDEBAR */
        .stSidebar .stMarkdown,
        .stSidebar .stText,
        .stSidebar p,
        .stSidebar div,
        .stSidebar span {
            color: #1a1e30;
        }

        div[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f2f3fa 0%, #e8eaf5 100%);
        }

        div[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            padding-top: 0.5rem;
        }

        /* DATAFRAMES */
        [data-testid="stDataFrame"], [data-testid="stTable"] {
            background: var(--bg-panel);
            border-radius: 2px;
            border: 1px solid var(--border);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
        }

        /* SCROLLBAR */
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: var(--bg-base); }
        ::-webkit-scrollbar-thumb { background: rgba(217,119,6,0.45); border-radius: 2px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--accent-bright); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_state() -> None:
    defaults = {
        "ticker_input": "AAPL",
        "benchmark_input": "SPY",
        "watchlist_text": "AAPL,MSFT,NVDA,TSLA,SPY,QQQ",
        "start_date": date.today() - timedelta(days=365),
        "end_date": date.today(),
        "interval": "1d",
        "data_mode": "Auto",
        "strategy_choice": "Ensemble",
        "rsi_window": 14,
        "fast_window": 12,
        "slow_window": 26,
        "trend_window": 20,
        "long_trend_window": 50,
        "vol_window": 20,
        "fee_bps": 5,
        "run_app": True,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def quick_ticker_buttons() -> None:
    tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "SPY", "QQQ"]
    cols = st.columns(len(tickers))
    for col, symbol in zip(cols, tickers):
        if col.button(symbol, use_container_width=True):
            st.session_state["ticker_input"] = symbol
            st.session_state["run_app"] = True


def validate_inputs(ticker: str, start_date: date, end_date: date) -> tuple[date, date]:
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("Please enter a ticker symbol.")
    if end_date > date.today():
        raise ValueError("End date cannot be in the future.")
    if start_date >= end_date:
        raise ValueError("Start date must be before end date.")
    return start_date, end_date


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
    source = "Synthetic"

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


def build_feature_lab(
    data: pd.DataFrame,
    rsi_window: int,
    fast_window: int,
    slow_window: int,
    trend_window: int,
    long_trend_window: int,
    vol_window: int,
) -> pd.DataFrame:
    df = data.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"] if "Volume" in df.columns else pd.Series(index=df.index, dtype=float)

    df["Return_1D"] = close.pct_change()
    df["Return_5D"] = close.pct_change(5)
    df["Return_20D"] = close.pct_change(20)
    df["LogReturn"] = np.log(close / close.shift(1))

    df["SMA_20"] = close.rolling(trend_window).mean()
    df["SMA_50"] = close.rolling(long_trend_window).mean()
    df["EMA_12"] = close.ewm(span=fast_window, adjust=False).mean()
    df["EMA_26"] = close.ewm(span=slow_window, adjust=False).mean()
    df["Momentum_20"] = close / close.shift(20) - 1

    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=rsi_window).mean()
    avg_loss = loss.rolling(window=rsi_window).mean().replace(0, 1e-10)
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    rolling_mean = close.rolling(trend_window).mean()
    rolling_std = close.rolling(trend_window).std()
    df["BB_Upper"] = rolling_mean + 2 * rolling_std
    df["BB_Lower"] = rolling_mean - 2 * rolling_std
    df["BB_Z"] = (close - rolling_mean) / rolling_std.replace(0, np.nan)
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / rolling_mean.replace(0, np.nan)

    true_range = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["ATR_14"] = true_range.rolling(14).mean()
    df["RangePct"] = (high - low) / close.replace(0, np.nan)
    df["Volatility_20D"] = df["LogReturn"].rolling(vol_window).std() * np.sqrt(252)
    df["Drawdown"] = close / close.cummax() - 1
    df["Volume_Z"] = (volume - volume.rolling(20).mean()) / volume.rolling(20).std().replace(0, np.nan)

    df["RSI_Signal"] = np.select([df["RSI"] < 30, df["RSI"] > 70], [1, -1], default=0)
    df["Trend_Signal"] = np.select([close > df["SMA_20"], close < df["SMA_20"]], [1, -1], default=0)
    df["MACD_Signal_Flag"] = np.select([df["MACD_Hist"] > 0, df["MACD_Hist"] < 0], [1, -1], default=0)
    df["Breakout_Signal"] = np.select([close > df["BB_Upper"], close < df["BB_Lower"]], [1, -1], default=0)

    df["EnsembleScore"] = (
        0.35 * df["RSI_Signal"]
        + 0.35 * df["Trend_Signal"]
        + 0.20 * df["MACD_Signal_Flag"]
        + 0.10 * df["Breakout_Signal"]
    )
    df["EnsembleSignal"] = np.select(
        [df["EnsembleScore"] >= 0.25, df["EnsembleScore"] <= -0.25],
        [1, -1],
        default=0,
    )

    vol_anchor = df["Volatility_20D"].expanding().median()
    df["Regime"] = np.select(
        [
            (close > df["SMA_50"]) & (df["Volatility_20D"] <= vol_anchor),
            (close > df["SMA_50"]) & (df["Volatility_20D"] > vol_anchor),
            (close <= df["SMA_50"]) & (df["Volatility_20D"] > vol_anchor),
        ],
        ["Trend Up", "High-Vol Uptrend", "High-Vol Drawdown"],
        default="Range / Weak Trend",
    )
    return df


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


def add_horizon_features(feature_df: pd.DataFrame, horizons: tuple[int, ...] = (3, 5, 10, 20)) -> pd.DataFrame:
    df = feature_df.copy()
    for horizon in horizons:
        df[f"Return_{horizon}D"] = df["Close"].pct_change(horizon)
        df[f"RollingVol_{horizon}D"] = df["LogReturn"].rolling(horizon).std() * np.sqrt(252)
        df[f"Price_vs_SMA_{horizon}D"] = df["Close"] / df["Close"].rolling(horizon).mean() - 1
        df[f"HighLowRange_{horizon}D"] = (
            (df["High"].rolling(horizon).max() - df["Low"].rolling(horizon).min()) / df["Close"]
        ).replace([np.inf, -np.inf], np.nan)
        if "Volume" in df.columns:
            vol_roll = df["Volume"].rolling(horizon)
            df[f"VolumeShock_{horizon}D"] = (df["Volume"] - vol_roll.mean()) / vol_roll.std().replace(0, np.nan)

    df["RSI_x_Vol"] = df["RSI"] * df["Volatility_20D"]
    df["Momentum_x_Drawdown"] = df["Momentum_20"] * df["Drawdown"]
    df["MACD_x_BBWidth"] = df["MACD_Hist"] * df["BB_Width"]
    df["TrendGap_20_50"] = df["SMA_20"] / df["SMA_50"] - 1
    return df


def prepare_modeling_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    modeling = df.copy()
    modeling["TargetNextReturn"] = modeling["Close"].pct_change().shift(-1)
    candidate_cols = [
        "RSI",
        "MACD",
        "MACD_Hist",
        "BB_Z",
        "BB_Width",
        "ATR_14",
        "Volatility_20D",
        "Drawdown",
        "Momentum_20",
        "RangePct",
        "RSI_x_Vol",
        "Momentum_x_Drawdown",
        "MACD_x_BBWidth",
        "TrendGap_20_50",
    ]
    candidate_cols += [
        column
        for column in modeling.columns
        if column.startswith(("Return_", "RollingVol_", "Price_vs_SMA_", "HighLowRange_", "VolumeShock_"))
    ]
    candidate_cols = [column for column in candidate_cols if column in modeling.columns]
    modeling = modeling[candidate_cols + ["TargetNextReturn"]].replace([np.inf, -np.inf], np.nan).dropna()
    return modeling, candidate_cols


def walk_forward_random_forest(
    modeling_df: pd.DataFrame,
    feature_cols: list[str],
    train_ratio: float = 0.7,
    seeds: tuple[int, ...] = (7, 21, 42, 84, 126),
) -> tuple[pd.DataFrame, pd.DataFrame, float, pd.Series]:
    split_idx = max(int(len(modeling_df) * train_ratio), 50)
    train = modeling_df.iloc[:split_idx].copy()
    valid = modeling_df.iloc[split_idx:].copy()
    if valid.empty:
        raise ValueError("Validation split is empty. Expand the date range.")

    preds: list[np.ndarray] = []
    feature_importance_rows: list[pd.Series] = []
    for seed in seeds:
        model = RandomForestRegressor(
            n_estimators=250,
            max_depth=6,
            min_samples_leaf=5,
            random_state=seed,
            n_jobs=-1,
        )
        model.fit(train[feature_cols], train["TargetNextReturn"])
        preds.append(model.predict(valid[feature_cols]))
        feature_importance_rows.append(pd.Series(model.feature_importances_, index=feature_cols, name=f"seed_{seed}"))

    pred_matrix = np.vstack(preds)
    valid["PredictedNextReturn"] = pred_matrix.mean(axis=0)
    valid["PredictedSignal"] = np.select(
        [valid["PredictedNextReturn"] > 0.002, valid["PredictedNextReturn"] < -0.002],
        [1, -1],
        default=0,
    )
    valid["PredictionError"] = valid["TargetNextReturn"] - valid["PredictedNextReturn"]
    rmse = mean_squared_error(valid["TargetNextReturn"], valid["PredictedNextReturn"]) ** 0.5
    importance = pd.concat(feature_importance_rows, axis=1).mean(axis=1).sort_values(ascending=False)
    return train, valid, rmse, importance


def price_chart(strategy_df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.5, 0.24, 0.26],
        subplot_titles=(f"{ticker} Price + Signals", "RSI / MACD", "Volatility / Drawdown"),
    )

    fig.add_trace(
        go.Candlestick(
            x=strategy_df.index,
            open=strategy_df["Open"],
            high=strategy_df["High"],
            low=strategy_df["Low"],
            close=strategy_df["Close"],
            name="Price",
        ),
        row=1,
        col=1,
    )
    buy_mask = strategy_df["Signal"] == 1
    sell_mask = strategy_df["Signal"] == -1
    fig.add_trace(
        go.Scatter(
            x=strategy_df.index[buy_mask],
            y=strategy_df.loc[buy_mask, "Close"],
            mode="markers",
            name="Buy",
            marker=dict(symbol="triangle-up", size=11, color="#22c55e"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=strategy_df.index[sell_mask],
            y=strategy_df.loc[sell_mask, "Close"],
            mode="markers",
            name="Sell",
            marker=dict(symbol="triangle-down", size=11, color="#ef4444"),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(go.Scatter(x=strategy_df.index, y=strategy_df["RSI"], name="RSI", line=dict(color="#c084fc")), row=2, col=1)
    fig.add_trace(go.Scatter(x=strategy_df.index, y=strategy_df["MACD_Hist"], name="MACD Hist", line=dict(color="#38bdf8")), row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#60a5fa", row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#f87171", row=2, col=1)

    fig.add_trace(
        go.Scatter(x=strategy_df.index, y=strategy_df["Volatility_20D"], name="20D Volatility", line=dict(color="#f59e0b")),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=strategy_df.index, y=strategy_df["Drawdown"], name="Drawdown", line=dict(color="#94a3b8")),
        row=3,
        col=1,
    )

    _chart_base = dict(
        paper_bgcolor="rgba(15,16,24,0)",
        plot_bgcolor="rgba(15,16,24,0.55)",
        font=dict(family="JetBrains Mono, monospace", color="#8892a4", size=10),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.09)", zerolinecolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.09)", zerolinecolor="rgba(255,255,255,0.05)"),
    )
    fig.update_layout(
        **_chart_base,
        height=900,
        margin=dict(l=20, r=20, t=70, b=20),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            bgcolor="rgba(15,16,24,0.85)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1,
            font=dict(family="JetBrains Mono, monospace", size=11),
        ),
    )
    fig.update_xaxes(rangeslider_visible=False)
    return fig


def backtest_chart(backtest: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=backtest.index, y=backtest["StrategyEquity"], name="Strategy Equity", line=dict(color="#22c55e", width=3)))
    fig.add_trace(go.Scatter(x=backtest.index, y=backtest["BuyHoldEquity"], name="Buy & Hold", line=dict(color="#38bdf8", width=2)))
    fig.update_layout(
        paper_bgcolor="rgba(15,16,24,0)", plot_bgcolor="rgba(15,16,24,0.55)",
        font=dict(family="JetBrains Mono, monospace", color="#8892a4", size=10),
        height=420, margin=dict(l=20, r=20, t=44, b=20),
        title=dict(text="Backtest Equity Curve", font=dict(family="Barlow Condensed, sans-serif", size=17, color="#f0f4f8")),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.09)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.09)"),
        legend=dict(bgcolor="rgba(15,16,24,0.85)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1),
    )
    return fig


def correlation_chart(correlation_series: pd.Series, ticker: str, benchmark: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=correlation_series.index, y=correlation_series, name="Rolling Correlation", line=dict(color="#f59e0b", width=3)))
    fig.add_hline(y=0, line_color="#94a3b8", line_dash="dash")
    fig.update_layout(
        paper_bgcolor="rgba(15,16,24,0)", plot_bgcolor="rgba(15,16,24,0.55)",
        font=dict(family="JetBrains Mono, monospace", color="#8892a4", size=10),
        height=360, margin=dict(l=20, r=20, t=44, b=20),
        title=dict(text=f"20-Period Correlation: {ticker} vs {benchmark}", font=dict(family="Barlow Condensed, sans-serif", size=17, color="#f0f4f8")),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.09)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.09)"),
    )
    return fig


def ml_chart(valid: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=valid.index, y=valid["TargetNextReturn"], name="Actual Next Return", line=dict(color="#38bdf8")))
    fig.add_trace(go.Scatter(x=valid.index, y=valid["PredictedNextReturn"], name="Predicted Next Return", line=dict(color="#f472b6")))
    fig.update_layout(
        paper_bgcolor="rgba(15,16,24,0)", plot_bgcolor="rgba(15,16,24,0.55)",
        font=dict(family="JetBrains Mono, monospace", color="#8892a4", size=10),
        height=360, margin=dict(l=20, r=20, t=44, b=20),
        title=dict(text="Walk-Forward ML Forecast", font=dict(family="Barlow Condensed, sans-serif", size=17, color="#f0f4f8")),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.09)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.09)"),
        legend=dict(bgcolor="rgba(15,16,24,0.85)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1),
    )
    return fig


def metric_card(label: str, value: str, sub: str) -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>
    """


def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-eyebrow">quantitative research terminal &middot; v2.4</div>
            <h1>Rentwise <span class="hl">Quant Lab</span></h1>
            <div class="hero-meta">
                <span class="live-badge">LIVE</span>
                Rule-based strategies &middot; Walk-forward ML &middot; Multi-asset backtesting &middot; Watchlist pulse
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_controls() -> dict:
    with st.sidebar:
        st.markdown("## Control Deck\n---")
        st.text_input("Primary ticker", key="ticker_input")
        st.text_input("Benchmark", key="benchmark_input")
        st.text_area("Watchlist", key="watchlist_text", height=80)
        st.date_input("Start date", key="start_date")
        st.date_input("End date", key="end_date")
        st.selectbox("Interval", ["1h", "1d", "1wk", "1mo", "1y"], key="interval")
        st.selectbox("Data source", ["Auto", "Live", "Synthetic"], key="data_mode")
        st.radio("Strategy", ["RSI", "Trend", "MACD", "Breakout", "Ensemble"], key="strategy_choice", horizontal=False)

        st.markdown("### Indicator Tuning")
        st.slider("RSI window", 5, 30, key="rsi_window")
        st.slider("Fast EMA", 5, 20, key="fast_window")
        st.slider("Slow EMA", 10, 60, key="slow_window")
        st.slider("Trend SMA", 10, 40, key="trend_window")
        st.slider("Long trend SMA", 20, 120, key="long_trend_window")
        st.slider("Volatility window", 5, 40, key="vol_window")
        st.slider("Trading fee (bps)", 0, 25, key="fee_bps")

        show_raw = st.checkbox("Show raw market data", value=False)
        show_ml = st.checkbox("Run ML forecast layer", value=True)
        show_watchlist = st.checkbox("Run watchlist pulse scan", value=True)
        show_correlation = st.checkbox("Run benchmark correlation", value=True)

        control_cols = st.columns(2)
        if control_cols[0].button("Run", use_container_width=True):
            st.session_state["run_app"] = True
        if control_cols[1].button("Reset Presets", use_container_width=True):
            for key in [
                "ticker_input",
                "benchmark_input",
                "watchlist_text",
                "start_date",
                "end_date",
                "interval",
                "data_mode",
                "strategy_choice",
                "rsi_window",
                "fast_window",
                "slow_window",
                "trend_window",
                "long_trend_window",
                "vol_window",
                "fee_bps",
            ]:
                st.session_state.pop(key, None)
            initialize_state()
            st.session_state["run_app"] = True

    return {
        "ticker": st.session_state["ticker_input"].strip().upper(),
        "benchmark": st.session_state["benchmark_input"].strip().upper(),
        "watchlist": [item.strip().upper() for item in st.session_state["watchlist_text"].split(",") if item.strip()],
        "start_date": st.session_state["start_date"],
        "end_date": st.session_state["end_date"],
        "interval": st.session_state["interval"],
        "data_mode": st.session_state["data_mode"],
        "strategy_choice": st.session_state["strategy_choice"],
        "rsi_window": st.session_state["rsi_window"],
        "fast_window": st.session_state["fast_window"],
        "slow_window": st.session_state["slow_window"],
        "trend_window": st.session_state["trend_window"],
        "long_trend_window": st.session_state["long_trend_window"],
        "vol_window": st.session_state["vol_window"],
        "fee_bps": st.session_state["fee_bps"],
        "show_raw": show_raw,
        "show_ml": show_ml,
        "show_watchlist": show_watchlist,
        "show_correlation": show_correlation,
    }


def main() -> None:
    inject_styles()
    initialize_state()
    render_header()
    quick_ticker_buttons()
    controls = sidebar_controls()

    try:
        start_dt, end_dt = validate_inputs(controls["ticker"], controls["start_date"], controls["end_date"])
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    with st.spinner("Loading market data and building the trading lab..."):
        time.sleep(0.4)
        data, source = get_data_cached(
            controls["ticker"],
            start_dt,
            end_dt,
            controls["interval"],
            controls["data_mode"],
        )
        if data.empty:
            st.error("No data could be prepared for this ticker.")
            st.stop()

        feature_data = build_feature_lab(
            data,
            controls["rsi_window"],
            controls["fast_window"],
            controls["slow_window"],
            controls["trend_window"],
            controls["long_trend_window"],
            controls["vol_window"],
        )
        strategy_data, signal_col = apply_strategy(feature_data, controls["strategy_choice"])
        signal_summary = summarize_signal(strategy_data, controls["strategy_choice"])
        backtest = run_backtest(strategy_data, signal_col, controls["fee_bps"])

    snapshot = pd.Series(
        {
            "Last Close": strategy_data["Close"].iloc[-1],
            "1D Return": strategy_data["Return_1D"].iloc[-1],
            "5D Return": strategy_data["Return_5D"].iloc[-1],
            "20D Return": strategy_data["Return_20D"].iloc[-1],
            "RSI": strategy_data["RSI"].iloc[-1],
            "20D Volatility": strategy_data["Volatility_20D"].iloc[-1],
            "Drawdown": strategy_data["Drawdown"].iloc[-1],
            "Current Regime": strategy_data["Regime"].iloc[-1],
        }
    )

    top_cols = st.columns(4)
    top_cols[0].markdown(metric_card("Ticker", controls["ticker"], f"Source: {source}"), unsafe_allow_html=True)
    top_cols[1].markdown(metric_card("Signal", signal_summary["label"], signal_summary["message"]), unsafe_allow_html=True)
    top_cols[2].markdown(
        metric_card("Confidence", f"{signal_summary['confidence']:.1f}%", f"Strategy: {controls['strategy_choice']}"),
        unsafe_allow_html=True,
    )
    top_cols[3].markdown(
        metric_card(
            "Backtest Return",
            f"{(backtest['StrategyEquity'].iloc[-1] - 1):+.2%}",
            f"Buy & Hold: {(backtest['BuyHoldEquity'].iloc[-1] - 1):+.2%}",
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="{signal_summary["css"]}">{signal_summary["label"]}</div>',
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["Overview", "Charts", "Backtest", "Watchlist", "Quant Lab", "Raw Data"])

    with tabs[0]:
        left, right = st.columns([1.1, 0.9])
        with left:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("Market Snapshot")
            st.dataframe(snapshot.to_frame("Value"), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            stress_feed = compute_stress_feed(strategy_data)
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("Stress Feed")
            if stress_feed.empty:
                st.info("No major stress events were detected in the selected period.")
            else:
                st.dataframe(stress_feed, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with right:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("Strategy Report Card")
            report_card = pd.Series(
                {
                    "Signal Column": signal_col,
                    "Total Buy Signals": int((strategy_data["Signal"] == 1).sum()),
                    "Total Sell Signals": int((strategy_data["Signal"] == -1).sum()),
                    "Current RSI": round(float(strategy_data["RSI"].iloc[-1]), 2) if pd.notna(strategy_data["RSI"].iloc[-1]) else np.nan,
                    "Current MACD Hist": round(float(strategy_data["MACD_Hist"].iloc[-1]), 5) if pd.notna(strategy_data["MACD_Hist"].iloc[-1]) else np.nan,
                    "Current Regime": strategy_data["Regime"].iloc[-1],
                }
            )
            st.dataframe(report_card.to_frame("Value"), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("Action Notes")
            st.write(signal_summary["message"])
            st.write(
                "Use the watchlist and backtest tabs to compare whether the current setup is isolated to one ticker "
                "or supported across the broader tech and ETF basket."
            )
            st.markdown("</div>", unsafe_allow_html=True)

    with tabs[1]:
        st.plotly_chart(price_chart(strategy_data, controls["ticker"]), use_container_width=True)

    with tabs[2]:
        bt_cols = st.columns(3)
        bt_cols[0].metric("Strategy Total Return", f"{(backtest['StrategyEquity'].iloc[-1] - 1):+.2%}")
        bt_cols[1].metric("Buy & Hold Return", f"{(backtest['BuyHoldEquity'].iloc[-1] - 1):+.2%}")
        bt_cols[2].metric("Max Drawdown", f"{backtest['StrategyDrawdown'].min():+.2%}")
        st.plotly_chart(backtest_chart(backtest), use_container_width=True)
        st.dataframe(
            pd.DataFrame(
                {
                    "Strategy Return": [backtest["StrategyEquity"].iloc[-1] - 1],
                    "Buy & Hold": [backtest["BuyHoldEquity"].iloc[-1] - 1],
                    "Daily Hit Rate": [(backtest["StrategyReturn"] > 0).mean()],
                    "Days in Market": [(backtest["SignalPosition"] != 0).sum()],
                    "Signal Changes": [int(backtest["Turnover"].sum())],
                }
            ),
            use_container_width=True,
        )

    with tabs[3]:
        if controls["show_watchlist"] and controls["watchlist"]:
            pulse_table = build_watchlist_pulse(
                controls["watchlist"],
                start_dt,
                end_dt,
                controls["interval"],
                controls["data_mode"],
                controls["rsi_window"],
                controls["fast_window"],
                controls["slow_window"],
                controls["trend_window"],
                controls["long_trend_window"],
                controls["vol_window"],
            )
            if pulse_table.empty:
                st.warning("Watchlist pulse table is empty.")
            else:
                st.dataframe(pulse_table, use_container_width=True)
        else:
            st.info("Enable the watchlist scan in the sidebar to run this section.")

        if controls["show_correlation"] and controls["benchmark"]:
            benchmark_data, _ = get_data_cached(
                controls["benchmark"],
                start_dt,
                end_dt,
                controls["interval"],
                controls["data_mode"],
            )
            benchmark_returns = benchmark_data["Close"].pct_change().rename(controls["benchmark"])
            ticker_returns = strategy_data["Close"].pct_change().rename(controls["ticker"])
            corr_frame = pd.concat([ticker_returns, benchmark_returns], axis=1).dropna()
            if not corr_frame.empty:
                rolling_corr = corr_frame[controls["ticker"]].rolling(20).corr(corr_frame[controls["benchmark"]]).dropna()
                st.plotly_chart(correlation_chart(rolling_corr, controls["ticker"], controls["benchmark"]), use_container_width=True)
                if not rolling_corr.empty:
                    st.metric("Latest Rolling Correlation", f"{rolling_corr.iloc[-1]:+.3f}")

    with tabs[4]:
        enriched_feature_data = add_horizon_features(strategy_data)
        horizon_scorecard = pd.DataFrame(
            {
                "Feature": [
                    column
                    for column in enriched_feature_data.columns
                    if column.startswith(("Return_", "RollingVol_", "Price_vs_SMA_"))
                ]
            }
        )
        if not horizon_scorecard.empty:
            horizon_scorecard["LatestValue"] = horizon_scorecard["Feature"].map(lambda column: enriched_feature_data[column].iloc[-1])
            horizon_scorecard["AbsLatestValue"] = horizon_scorecard["LatestValue"].abs()
            horizon_scorecard = horizon_scorecard.sort_values("AbsLatestValue", ascending=False).head(15)
            st.subheader("Horizon Scorecard")
            st.dataframe(horizon_scorecard[["Feature", "LatestValue"]], use_container_width=True)

        if controls["show_ml"]:
            try:
                modeling_df, modeling_features = prepare_modeling_frame(enriched_feature_data)
                if len(modeling_df) < 100:
                    st.info("Not enough clean rows for the ML forecast layer. Extend the date range.")
                else:
                    _, wf_valid, wf_rmse, wf_importance = walk_forward_random_forest(modeling_df, modeling_features)
                    st.metric("Walk-Forward RMSE", f"{wf_rmse:.6f}")
                    st.plotly_chart(ml_chart(wf_valid), use_container_width=True)
                    st.subheader("Top Feature Importances")
                    st.dataframe(wf_importance.head(12).to_frame("Mean Importance"), use_container_width=True)

                    blended = backtest.join(wf_valid[["PredictedNextReturn", "PredictedSignal"]], how="left")
                    blended["PredictedSignal"] = blended["PredictedSignal"].fillna(0)
                    signal_mix = 0.65 * blended["SignalPosition"].fillna(0) + 0.35 * blended["PredictedSignal"]
                    blended["BlendedSignal"] = np.select([signal_mix >= 0.25, signal_mix <= -0.25], [1, -1], default=0)
                    blended["BlendedPosition"] = blended["BlendedSignal"].shift(1).fillna(0)
                    blended["BlendedTurnover"] = blended["BlendedPosition"].diff().abs().fillna(blended["BlendedPosition"].abs())
                    blended["BlendedReturn"] = blended["BlendedPosition"] * blended["Return_1D"].fillna(0) - blended["BlendedTurnover"] * 0.0005
                    blended["BlendedEquity"] = (1 + blended["BlendedReturn"]).cumprod()

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=blended.index, y=blended["StrategyEquity"], name="Rule-Based", line=dict(color="#38bdf8", width=3)))
                    fig.add_trace(go.Scatter(x=blended.index, y=blended["BlendedEquity"], name="Blended", line=dict(color="#f472b6", width=3)))
                    fig.update_layout(
                        paper_bgcolor="rgba(15,16,24,0)", plot_bgcolor="rgba(15,16,24,0.55)",
                        font=dict(family="JetBrains Mono, monospace", color="#8892a4", size=10),
                        height=360, margin=dict(l=20, r=20, t=44, b=20),
                        title=dict(text="Rule-Based vs Blended Equity", font=dict(family="Barlow Condensed, sans-serif", size=17, color="#f0f4f8")),
                        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.09)"),
                        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.09)"),
                        legend=dict(bgcolor="rgba(15,16,24,0.85)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1),
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:
                st.warning(f"ML layer could not be completed: {exc}")

    with tabs[5]:
        if controls["show_raw"]:
            st.subheader("Raw Market Data")
            st.dataframe(data.tail(200), use_container_width=True)
        st.subheader("Feature Table")
        display_cols = [
            "Close",
            "RSI",
            "MACD",
            "MACD_Hist",
            "Volatility_20D",
            "Drawdown",
            "Regime",
            "Signal",
        ]
        st.dataframe(strategy_data[display_cols].tail(120), use_container_width=True)


if __name__ == "__main__":
    main()
