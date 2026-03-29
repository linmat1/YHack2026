import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

try:
    from polymarket_config import get_polymarket_config, redacted_polymarket_config
except ModuleNotFoundError:
    from Yhack.polymarket_config import get_polymarket_config, redacted_polymarket_config

try:
    from py_clob_client.client import ClobClient
except Exception:
    ClobClient = None


st.set_page_config(
    page_title="Yhack Strategy Studio Iter 2",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


ASSET_MAP = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
}

ASSET_SEARCH_TERMS = {
    "BTC": ["bitcoin", "btc", "bitcoin etf", "bitcoin reserve", "crypto reserve"],
    "ETH": ["ethereum", "eth", "ether etf"],
    "SOL": ["solana", "sol", "sol etf"],
}

KRAKEN_PAIR_MAP = {
    "BTC-USD": "BTC/USD",
    "ETH-USD": "ETH/USD",
    "SOL-USD": "SOL/USD",
}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg-main: #f5f2ea;
            --bg-card: rgba(255, 255, 255, 0.72);
            --bg-card-strong: rgba(255, 255, 255, 0.9);
            --ink: #11243a;
            --muted: #5f7187;
            --gold: #f6b73c;
            --teal: #169b9d;
            --blue: #2c7be5;
            --coral: #f25f5c;
            --lime: #5fbf7f;
        }
        .stApp {
            background:
                radial-gradient(circle at 12% 12%, rgba(246, 183, 60, 0.22), transparent 26%),
                radial-gradient(circle at 90% 8%, rgba(44, 123, 229, 0.18), transparent 28%),
                radial-gradient(circle at 82% 88%, rgba(22, 155, 157, 0.16), transparent 22%),
                linear-gradient(180deg, #fcfaf6 0%, #f4efe6 38%, #eef3f7 100%);
            color: var(--ink);
        }
        .block-container {
            padding-top: 1.3rem;
            padding-bottom: 3rem;
        }
        .hero {
            padding: 1.5rem 1.7rem;
            border-radius: 24px;
            background:
                linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(255, 247, 229, 0.86)),
                linear-gradient(135deg, #f6b73c, #2c7be5);
            border: 1px solid rgba(17, 36, 58, 0.08);
            box-shadow: 0 24px 60px rgba(21, 36, 56, 0.12);
            margin-bottom: 1rem;
        }
        .hero h1 {
            margin: 0;
            font-size: 2.45rem;
            color: #11243a;
            letter-spacing: -0.03em;
        }
        .hero p {
            margin-top: 0.55rem;
            margin-bottom: 0;
            color: #44586f;
            font-size: 1.02rem;
            max-width: 72rem;
        }
        .hero-grid {
            display: grid;
            grid-template-columns: 1.4fr 1fr;
            gap: 1rem;
            align-items: start;
        }
        .workflow {
            padding: 0.95rem 1rem;
            border-radius: 18px;
            background: rgba(17, 36, 58, 0.06);
            border: 1px solid rgba(17, 36, 58, 0.08);
        }
        .workflow h3 {
            margin: 0 0 0.55rem 0;
            color: #11243a;
            font-size: 1rem;
        }
        .workflow p {
            margin: 0.2rem 0;
            font-size: 0.94rem;
            color: #42576f;
        }
        .glass-card {
            padding: 1rem 1.1rem;
            border-radius: 22px;
            background: var(--bg-card);
            backdrop-filter: blur(14px);
            border: 1px solid rgba(17, 36, 58, 0.08);
            box-shadow: 0 14px 34px rgba(21, 36, 56, 0.08);
            margin-bottom: 0.9rem;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.9rem;
            margin-bottom: 1rem;
        }
        .metric-card {
            padding: 0.95rem 1rem;
            border-radius: 18px;
            background: var(--bg-card-strong);
            border: 1px solid rgba(17, 36, 58, 0.08);
            box-shadow: 0 10px 24px rgba(21, 36, 56, 0.08);
        }
        .metric-label {
            color: var(--muted);
            font-size: 0.84rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .metric-value {
            margin-top: 0.22rem;
            color: var(--ink);
            font-weight: 800;
            font-size: 1.7rem;
        }
        .explain-box {
            padding: 0.95rem 1rem;
            border-radius: 16px;
            background: rgba(17, 36, 58, 0.05);
            border-left: 5px solid var(--gold);
            color: #274057;
            margin-bottom: 0.8rem;
        }
        .section-title {
            margin: 0.1rem 0 0.2rem 0;
            color: #11243a;
            font-size: 1.15rem;
            font-weight: 800;
        }
        .section-copy {
            margin: 0 0 0.4rem 0;
            color: #4a6077;
            font-size: 0.96rem;
        }
        .verdict-box {
            padding: 1rem 1.05rem;
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(255,255,255,0.94), rgba(232, 245, 255, 0.9));
            border: 1px solid rgba(44, 123, 229, 0.12);
            box-shadow: 0 12px 24px rgba(21,36,56,0.08);
            margin-bottom: 0.9rem;
        }
        .verdict-box h4 {
            margin: 0 0 0.35rem 0;
            color: #11243a;
            font-size: 1.04rem;
        }
        .verdict-box p {
            margin: 0.22rem 0;
            color: #41576e;
            font-size: 0.94rem;
        }
        .risk-pill {
            display: inline-block;
            padding: 0.35rem 0.72rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.9rem;
        }
        .risk-tradeable { background: rgba(95, 191, 127, 0.18); color: #2d7d46; }
        .risk-cautious { background: rgba(246, 183, 60, 0.18); color: #946100; }
        .risk-high { background: rgba(242, 95, 92, 0.18); color: #9c3532; }
        .risk-avoid { background: rgba(197, 59, 59, 0.18); color: #7a1515; }
        .small-note {
            color: var(--muted);
            font-size: 0.9rem;
        }
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.75);
            border: 1px solid rgba(17,36,58,0.08);
            padding: 0.7rem 0.8rem;
            border-radius: 16px;
            box-shadow: 0 8px 20px rgba(21,36,56,0.06);
        }
        div[data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(255,255,255,0.94), rgba(247,244,237,0.92));
            border-right: 1px solid rgba(17,36,58,0.08);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-grid">
                <div>
                    <h1>Yhack Strategy Studio</h1>
                    <p>
                        A glossy, explainable crypto strategy dashboard that compares plain technical trading against
                        Polymarket-enhanced sizing, filters, hedges, payoff curves, resolution windows, and portfolio outcomes.
                    </p>
                </div>
                <div class="workflow">
                    <h3>How to use this dashboard</h3>
                    <p>1. Pick an asset, backtest window, and trade settings in the sidebar.</p>
                    <p>2. Read the top verdict to see whether PM is increasing conviction or cutting risk.</p>
                    <p>3. Compare the plain trade engine against the PM-enhanced version.</p>
                    <p>4. Use payoff, hedge, and timing tabs to understand where the strategy works or fails.</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def safe_float(value, default=0.0) -> float:
    return default if pd.isna(value) else float(value)


def risk_css(zone: str) -> str:
    mapping = {
        "Tradeable": "risk-tradeable",
        "Cautious": "risk-cautious",
        "High Risk": "risk-high",
        "Avoid": "risk-avoid",
    }
    return mapping.get(str(zone), "risk-cautious")


def inject_card_metrics(metrics: list[tuple[str, str]]) -> None:
    cards = []
    for label, value in metrics:
        cards.append(
            (
                f'<div class="metric-card">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div>'
                f"</div>"
            )
        )
    st.markdown(f"<div class='metric-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)


def explain_text(text: str) -> None:
    st.markdown(f"<div class='explain-box'>{text}</div>", unsafe_allow_html=True)


def section_intro(title: str, text: str) -> None:
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='section-copy'>{text}</div>", unsafe_allow_html=True)


def render_verdict_box(bundle: dict) -> None:
    latest = bundle["strategy_df"].iloc[-1]
    without_pm = bundle["without_pm"]["summary"]
    with_pm = bundle["with_pm"]["summary"]
    delta = with_pm["Final Equity"] - without_pm["Final Equity"]
    direction = "improving" if delta >= 0 else "hurting"
    pm_markets = len(bundle["real_market_board"])
    st.markdown(
        f"""
        <div class="verdict-box">
            <h4>Current read for {bundle['asset_label']}</h4>
            <p><strong>Trade verdict:</strong> {latest['FinalAction']} with a size of {latest['PositionSize']:.2f}x and a risk zone of {latest['RiskZone']}.</p>
            <p><strong>PM effect:</strong> Polymarket is currently <strong>{direction}</strong> the strategy by {delta:,.2f} in ending equity versus the plain version over this backtest.</p>
            <p><strong>Context:</strong> {pm_markets} live PM markets were found, current YES probability is {latest['YES_Mid']:.3f}, and PM-adjusted confidence is {latest['FinalConfidence']:.1f}.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def generate_synthetic_data(ticker: str, start_date: date, end_date: date, interval: str) -> pd.DataFrame:
    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date)
    freq_map = {"1h": "h", "1d": "B", "1wk": "W-FRI", "1mo": "MS"}
    idx = pd.date_range(start_ts, end_ts, freq=freq_map.get(interval, "B"))
    if len(idx) < 120:
        idx = pd.date_range(start_ts, periods=260, freq="B")
    seed = sum(ord(ch) for ch in ticker) % (2**32 - 1)
    rng = np.random.default_rng(seed)
    drift = 0.00045 + (seed % 13) / 100000
    vol = 0.015 + (seed % 11) / 1000
    shocks = rng.normal(drift, vol, len(idx))
    close = 100 * np.exp(np.cumsum(shocks))
    open_ = np.concatenate([[close[0]], close[:-1]]) * (1 + rng.normal(0, 0.0025, len(idx)))
    high = np.maximum(open_, close) * (1 + rng.uniform(0.001, 0.016, len(idx)))
    low = np.minimum(open_, close) * (1 - rng.uniform(0.001, 0.016, len(idx)))
    volume = rng.integers(700_000, 4_500_000, len(idx))
    df = pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Adj Close": close, "Volume": volume}, index=idx)
    df.index.name = "Date"
    return df


def get_kraken_market_data(ticker: str, start_date: date, end_date: date, interval: str) -> pd.DataFrame:
    pair = KRAKEN_PAIR_MAP.get(ticker)
    interval_map = {"1h": 60, "1d": 1440}
    if pair is None or interval not in interval_map:
        return pd.DataFrame()
    params = {
        "pair": pair,
        "interval": interval_map[interval],
        "since": int(pd.Timestamp(start_date).tz_localize("UTC").timestamp()),
    }
    response = requests.get("https://api.kraken.com/0/public/OHLC", params=params, timeout=12)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise ValueError(f"Kraken OHLC error: {payload['error']}")
    result = payload.get("result", {})
    pair_key = next((key for key in result.keys() if key != "last"), None)
    rows = result.get(pair_key, []) if pair_key else []
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows, columns=["time", "Open", "High", "Low", "Close", "VWAP", "Volume", "Count"])
    frame["Date"] = pd.to_datetime(frame["time"], unit="s", utc=True).dt.tz_localize(None)
    for col in ["Open", "High", "Low", "Close", "VWAP", "Volume", "Count"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.set_index("Date").sort_index()
    frame = frame.loc[(frame.index >= pd.to_datetime(start_date)) & (frame.index < pd.to_datetime(end_date) + pd.Timedelta(days=1))]
    frame.index.name = "Date"
    return frame[["Open", "High", "Low", "Close", "Volume"]]


@st.cache_data(show_spinner=False, ttl=60 * 10)
def get_market_data(ticker: str, start_date: date, end_date: date, interval: str, data_mode: str) -> tuple[pd.DataFrame, str]:
    ticker = ticker.strip().upper()
    normalized_mode = data_mode.lower()
    source = "Synthetic Fallback"
    # CHANGED HERE: this dashboard is crypto-only, so live data should come from Kraken rather than Yahoo.
    if ticker in KRAKEN_PAIR_MAP and normalized_mode in {"kraken", "live", "auto"}:
        try:
            kraken = get_kraken_market_data(ticker, start_date, end_date, interval)
            if not kraken.empty:
                return kraken.sort_index(), "Kraken"
        except Exception:
            pass
    return generate_synthetic_data(ticker, start_date, end_date, interval).sort_index(), source


def build_feature_lab(data: pd.DataFrame) -> pd.DataFrame:
    df = data.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"] if "Volume" in df.columns else pd.Series(index=df.index, dtype=float)
    df["Return_1D"] = close.pct_change()
    df["LogReturn"] = np.log(close / close.shift(1))
    df["SMA_20"] = close.rolling(20).mean()
    df["SMA_50"] = close.rolling(50).mean()
    df["EMA_12"] = close.ewm(span=12, adjust=False).mean()
    df["EMA_26"] = close.ewm(span=26, adjust=False).mean()
    df["Momentum_20"] = close / close.shift(20) - 1
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean().replace(0, 1e-10)
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    rolling_mean = close.rolling(20).mean()
    rolling_std = close.rolling(20).std()
    df["BB_Upper"] = rolling_mean + 2 * rolling_std
    df["BB_Lower"] = rolling_mean - 2 * rolling_std
    df["Volatility_20D"] = df["LogReturn"].rolling(20).std() * np.sqrt(252)
    true_range = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    df["ATR_14"] = true_range.rolling(14).mean()
    df["Drawdown"] = close / close.cummax() - 1
    df["Volume_Z"] = (volume - volume.rolling(20).mean()) / volume.rolling(20).std().replace(0, np.nan)
    df["RSI_Signal"] = np.select([df["RSI"] < 30, df["RSI"] > 70], [1, -1], default=0)
    df["Trend_Signal"] = np.select([close > df["SMA_20"], close < df["SMA_20"]], [1, -1], default=0)
    df["MACD_Signal_Flag"] = np.select([df["MACD_Hist"] > 0, df["MACD_Hist"] < 0], [1, -1], default=0)
    df["Breakout_Signal"] = np.select([close > df["BB_Upper"], close < df["BB_Lower"]], [1, -1], default=0)
    df["TechnicalScore"] = (
        0.35 * df["Trend_Signal"]
        + 0.25 * df["MACD_Signal_Flag"]
        + 0.20 * df["RSI_Signal"]
        + 0.10 * df["Breakout_Signal"]
        + 0.10 * np.sign(df["Momentum_20"].fillna(0))
    )
    df["BaseDirection"] = np.where(df["TechnicalScore"] >= 0.25, "Long", np.where(df["TechnicalScore"] <= -0.25, "Short", "Flat"))
    df["TechnicalConfidence"] = 100 * np.clip(df["TechnicalScore"].abs(), 0, 1)
    return df


def compute_stress_feed(feature_data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    clean = feature_data.dropna(subset=["Return_1D", "Volatility_20D", "RSI"])
    for idx, row in clean.iterrows():
        if abs(row["Return_1D"]) > 0.03:
            rows.append((idx, "Large daily move", row["Return_1D"]))
        if row["Volatility_20D"] > clean["Volatility_20D"].median() * 1.5:
            rows.append((idx, "Volatility spike", row["Volatility_20D"]))
        if row["Drawdown"] < -0.10:
            rows.append((idx, "Deep drawdown", row["Drawdown"]))
        if row["RSI"] < 30:
            rows.append((idx, "Oversold RSI", row["RSI"]))
        if row["RSI"] > 70:
            rows.append((idx, "Overbought RSI", row["RSI"]))
    return pd.DataFrame(rows, columns=["Date", "Event", "Value"]).drop_duplicates().tail(15)


def parse_token_ids(raw_value):
    if raw_value is None or (isinstance(raw_value, float) and np.isnan(raw_value)):
        return []
    if isinstance(raw_value, list):
        return [str(x) for x in raw_value if str(x).strip()]
    if isinstance(raw_value, str):
        text = raw_value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(x) for x in parsed if str(x).strip()]
        except Exception:
            pass
        if "," in text:
            return [part.strip() for part in text.split(",") if part.strip()]
        return [text]
    return [str(raw_value)]


def safe_json_request(method: str, url: str, timeout: int = 20, **kwargs):
    response = requests.request(method, url, timeout=timeout, **kwargs)
    response.raise_for_status()
    return response.json()


@st.cache_data(show_spinner=False, ttl=60 * 5)
def fetch_gamma_markets(config: dict, limit: int = 50) -> pd.DataFrame:
    params = {"limit": limit, "active": "true", "closed": "false"}
    data = safe_json_request("GET", f"{config['gamma_host'].rstrip('/')}/markets", params=params, timeout=config["request_timeout"])
    if isinstance(data, dict):
        data = data.get("markets", data.get("data", []))
    return pd.DataFrame(data)


def filter_markets_for_asset(markets: pd.DataFrame, asset_label: str, override_search: str = "") -> pd.DataFrame:
    if markets.empty:
        return markets
    search_terms = ASSET_SEARCH_TERMS.get(asset_label, [asset_label.lower()])
    if override_search.strip():
        search_terms = [term.strip().lower() for term in override_search.split(",") if term.strip()]
    question = markets.get("question", pd.Series("", index=markets.index)).astype(str).str.lower()
    slug = markets.get("slug", pd.Series("", index=markets.index)).astype(str).str.lower()
    desc = markets.get("description", pd.Series("", index=markets.index)).astype(str).str.lower()
    mask = pd.Series(False, index=markets.index)
    for term in search_terms:
        term = term.lower()
        mask = mask | question.str.contains(term, na=False) | slug.str.contains(term, na=False) | desc.str.contains(term, na=False)
    return markets.loc[mask].copy().reset_index(drop=True)


def build_clob_client(config: dict):
    if ClobClient is None:
        return None
    try:
        return ClobClient(config["clob_host"])
    except Exception:
        return None


def normalize_book_levels(levels) -> list[dict]:
    out = []
    for level in levels or []:
        price = getattr(level, "price", None)
        size = getattr(level, "size", None)
        if isinstance(level, dict):
            price = level.get("price", price)
            size = level.get("size", size)
        if price is not None:
            out.append({"price": float(price), "size": float(size) if size is not None else np.nan})
    return out


def fetch_order_book_snapshot(token_id: str | None, config: dict, client=None) -> dict:
    if not token_id:
        return {"bids": [], "asks": [], "source": "no_token"}
    if client is not None:
        try:
            book = client.get_order_book(token_id)
            return {
                "bids": normalize_book_levels(getattr(book, "bids", [])),
                "asks": normalize_book_levels(getattr(book, "asks", [])),
                "source": "py_clob_client",
            }
        except Exception:
            pass
    host = config["clob_host"].rstrip("/")
    attempts = [
        ("GET", f"{host}/book", {"params": {"token_id": token_id}}),
        ("GET", f"{host}/book", {"params": {"asset_id": token_id}}),
        ("POST", f"{host}/books", {"json": {"token_ids": [token_id]}}),
    ]
    for method, url, kwargs in attempts:
        try:
            data = safe_json_request(method, url, timeout=config["request_timeout"], **kwargs)
            if isinstance(data, list):
                data = data[0] if data else {}
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                data = data["data"][0] if data["data"] else {}
            bids = normalize_book_levels(data.get("bids", []))
            asks = normalize_book_levels(data.get("asks", []))
            if bids or asks:
                return {"bids": bids, "asks": asks, "source": f"rest:{method}"}
        except Exception:
            continue
    return {"bids": [], "asks": [], "source": "unavailable"}


def top_price(levels: list[dict], side: str) -> float:
    if not levels:
        return np.nan
    prices = [level["price"] for level in levels if pd.notna(level["price"])]
    if not prices:
        return np.nan
    return max(prices) if side == "bid" else min(prices)


@st.cache_data(show_spinner=False, ttl=60 * 5)
def build_real_market_board(config: dict, asset_label: str, limit: int = 25, override_search: str = "") -> pd.DataFrame:
    markets = fetch_gamma_markets(config, limit=max(limit, 60))
    markets = filter_markets_for_asset(markets, asset_label, override_search=override_search)
    if markets.empty:
        return markets
    markets = markets.head(limit)
    client = build_clob_client(config)
    rows = []
    for _, row in markets.iterrows():
        token_ids = []
        for candidate_key in ["clobTokenIds", "tokenIds"]:
            if candidate_key in row.index:
                token_ids = parse_token_ids(row[candidate_key])
                if token_ids:
                    break
        yes_token = token_ids[0] if token_ids else None
        book = fetch_order_book_snapshot(yes_token, config, client)
        best_bid = top_price(book["bids"], "bid")
        best_ask = top_price(book["asks"], "ask")
        mid = (best_bid + best_ask) / 2 if pd.notna(best_bid) and pd.notna(best_ask) else best_bid if pd.notna(best_bid) else best_ask
        rows.append(
            {
                "market_id": row.get("conditionId", row.get("slug")),
                "slug": row.get("slug", ""),
                "question": row.get("question", row.get("title", "")),
                "yes_token_id": yes_token,
                "mid": mid,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": best_ask - best_bid if pd.notna(best_bid) and pd.notna(best_ask) else np.nan,
                "volume": pd.to_numeric(row.get("volume", row.get("volumeNum", np.nan)), errors="coerce"),
                "liquidity": pd.to_numeric(row.get("liquidity", row.get("liquidityNum", np.nan)), errors="coerce"),
                "end_date": row.get("endDate", row.get("resolutionDate")),
                "book_source": book["source"],
            }
        )
    board = pd.DataFrame(rows)
    if board.empty:
        return board
    board["event_date"] = pd.to_datetime(board["end_date"], errors="coerce", utc=True).dt.tz_localize(None)
    board["days_to_resolution"] = (board["event_date"] - pd.Timestamp.today().normalize()).dt.days
    return board.sort_values(["liquidity", "volume"], ascending=False, na_position="last").reset_index(drop=True)


def simulate_prediction_market(
    feature_df: pd.DataFrame,
    market_id: str,
    base_prob: float,
    subjective_prob: float,
    resolution_days: int,
    seed: int = 123,
    spread_anchor: float | None = None,
    volume_anchor: float | None = None,
) -> pd.DataFrame:
    df = feature_df.copy()
    rng = np.random.default_rng(seed)
    n = len(df)
    spot_driver = df["Return_1D"].fillna(0).rolling(3).sum().fillna(0)
    vol_driver = df["Volatility_20D"].fillna(df["Volatility_20D"].median()).fillna(0)
    rsi_driver = (df["RSI"].fillna(50) - 50) / 50
    drawdown_driver = df["Drawdown"].fillna(0)
    latent = np.zeros(n)
    base_prob = float(np.clip(base_prob, 0.03, 0.97))
    subjective_prob = float(np.clip(subjective_prob, 0.03, 0.97))
    latent[0] = np.log(base_prob / (1 - base_prob))
    anchor = np.log(subjective_prob / (1 - subjective_prob))
    for i in range(1, n):
        shock = rng.normal(0, 0.08)
        latent[i] = (
            0.94 * latent[i - 1]
            + 0.03 * anchor
            + 1.7 * spot_driver.iloc[i]
            - 0.50 * vol_driver.iloc[i]
            + 0.20 * rsi_driver.iloc[i]
            + 0.32 * drawdown_driver.iloc[i]
            + shock
        )
    yes_mid = np.clip(1 / (1 + np.exp(-latent)), 0.03, 0.97)
    spread_anchor = 0.04 if spread_anchor is None or pd.isna(spread_anchor) else spread_anchor
    volume_anchor = 250000 if volume_anchor is None or pd.isna(volume_anchor) else volume_anchor
    spread = np.clip(spread_anchor + 0.18 * vol_driver.rank(pct=True).fillna(0.5) + 0.03 * np.abs(df["Return_1D"].fillna(0)), 0.015, 0.22)
    volume = (volume_anchor * (1 + 4 * np.abs(spot_driver))).fillna(volume_anchor).astype(int)
    pm = pd.DataFrame(index=df.index)
    pm["PredictionMarket"] = market_id
    pm["YES_Mid"] = yes_mid
    pm["YES_Bid"] = np.clip(yes_mid - spread / 2, 0.01, 0.99)
    pm["YES_Ask"] = np.clip(yes_mid + spread / 2, 0.01, 0.99)
    pm["PM_Spread"] = pm["YES_Ask"] - pm["YES_Bid"]
    pm["PM_Volume"] = volume
    pm["SubjectiveProb"] = subjective_prob
    pm["ProbEdge"] = subjective_prob - pm["YES_Mid"]
    pm["ProbMomentum_5D"] = pm["YES_Mid"].diff(5)
    pm["ProbVol_10D"] = pm["YES_Mid"].diff().rolling(10).std()
    pm["DaysToResolution"] = np.linspace(resolution_days, 0, n).clip(min=0)
    pm["EventProximity"] = 1 - pm["DaysToResolution"] / max(resolution_days, 1)
    pm["VolumeShock"] = (pm["PM_Volume"] - pm["PM_Volume"].rolling(10).mean()) / pm["PM_Volume"].rolling(10).std()
    pm["SpreadShock"] = (pm["PM_Spread"] - pm["PM_Spread"].rolling(10).mean()) / pm["PM_Spread"].rolling(10).std()
    pm["ProbSpotDivergence"] = pm["YES_Mid"].pct_change().replace([np.inf, -np.inf], np.nan) - df["Return_1D"].fillna(0)
    return pm


def min_max_scale(series: pd.Series) -> pd.Series:
    series = series.replace([np.inf, -np.inf], np.nan).ffill().bfill()
    if series.nunique(dropna=False) <= 1:
        return pd.Series(0.0, index=series.index)
    return (series - series.min()) / (series.max() - series.min())


def build_strategy_frame(feature_df: pd.DataFrame, prediction_market: pd.DataFrame, caution_threshold: float, confidence_trade_threshold: float) -> pd.DataFrame:
    out = feature_df.join(prediction_market)
    out["VolSpikeScore"] = 100 * min_max_scale(out["Volatility_20D"])
    out["DrawdownScore"] = 100 * min_max_scale(out["Drawdown"].abs())
    out["SpreadStressScore"] = 100 * min_max_scale(out["PM_Spread"])
    out["ProbWhipsawScore"] = 100 * min_max_scale(out["ProbVol_10D"].fillna(0))
    out["VolumeShockScore"] = 100 * min_max_scale(out["VolumeShock"].abs().fillna(0))
    out["DivergenceScore"] = 100 * min_max_scale(out["ProbSpotDivergence"].abs().fillna(0))
    out["EventRiskScore"] = 100 * min_max_scale(out["EventProximity"])
    out["ModelDisagreementScore"] = 100 * min_max_scale((out["RSI_Signal"] - np.sign(out["TechnicalScore"].fillna(0))).abs())
    out["CautionScore"] = (
        0.22 * out["VolSpikeScore"]
        + 0.16 * out["DrawdownScore"]
        + 0.14 * out["SpreadStressScore"]
        + 0.14 * out["ProbWhipsawScore"]
        + 0.10 * out["VolumeShockScore"]
        + 0.10 * out["DivergenceScore"]
        + 0.08 * out["EventRiskScore"]
        + 0.06 * out["ModelDisagreementScore"]
    )
    out["RiskZone"] = pd.cut(out["CautionScore"], bins=[-np.inf, 30, 55, caution_threshold, np.inf], labels=["Tradeable", "Cautious", "High Risk", "Avoid"])
    out["PMConfirmationScore"] = np.clip(
        50
        + 70 * out["ProbEdge"].fillna(0)
        + 25 * (out["YES_Mid"].fillna(0.5) - 0.5)
        + 15 * out["ProbMomentum_5D"].fillna(0),
        0,
        100,
    )
    out["PMQualityScore"] = np.clip(100 - 180 * out["PM_Spread"].fillna(out["PM_Spread"].median()).fillna(0.04), 0, 100)
    out["PMConflictPenalty"] = 100 * min_max_scale(out["ProbSpotDivergence"].abs().fillna(0))
    out["FinalConfidence"] = np.clip(
        0.55 * out["TechnicalConfidence"]
        + 0.25 * out["PMConfirmationScore"]
        + 0.10 * out["PMQualityScore"]
        - 0.10 * out["PMConflictPenalty"]
        - 0.25 * out["CautionScore"],
        0,
        100,
    )
    out["PositionSize"] = np.select(
        [
            out["FinalConfidence"] < confidence_trade_threshold,
            (out["FinalConfidence"] >= confidence_trade_threshold) & (out["FinalConfidence"] < 55),
            (out["FinalConfidence"] >= 55) & (out["FinalConfidence"] < 70),
            (out["FinalConfidence"] >= 70) & (out["FinalConfidence"] < 85),
            out["FinalConfidence"] >= 85,
        ],
        [0.0, 0.25, 0.50, 0.75, 1.0],
        default=0.0,
    )
    out.loc[out["RiskZone"].astype(str) == "Avoid", "PositionSize"] = 0.0
    out["FinalAction"] = np.where(
        (out["BaseDirection"] == "Long") & (out["PositionSize"] > 0) & (out["FinalConfidence"] >= confidence_trade_threshold),
        "Long",
        "No Trade",
    )
    return out


def position_size_units(cash: float, entry_price: float, stop_loss_pct: float, risk_per_trade: float) -> float:
    risk_amount = cash * risk_per_trade
    stop_distance = entry_price * stop_loss_pct
    if stop_distance <= 0:
        return 0.0
    return risk_amount / stop_distance


def build_roundtrip_table(trades_df: pd.DataFrame, initial_cash: float) -> pd.DataFrame:
    roundtrips = []
    open_cost = 0.0
    open_qty = 0.0
    entry_time = None
    for _, trade in trades_df.iterrows():
        if trade["side"] == "BUY":
            if open_qty == 0:
                entry_time = trade["timestamp"]
            open_cost += trade["notional"] + trade["fee"]
            open_qty += trade["qty"]
        else:
            proceeds = trade["notional"] - trade["fee"]
            pnl = proceeds - open_cost
            roundtrips.append(
                {
                    "entry_time": entry_time,
                    "exit_time": trade["timestamp"],
                    "qty": open_qty,
                    "buy_cost_incl_fees": open_cost,
                    "sell_proceeds_after_fee": proceeds,
                    "realized_pnl": pnl,
                    "exit_reason": trade.get("reason", "SELL"),
                }
            )
            open_cost = 0.0
            open_qty = 0.0
            entry_time = None
    expected_cols = [
        "entry_time",
        "exit_time",
        "qty",
        "buy_cost_incl_fees",
        "sell_proceeds_after_fee",
        "realized_pnl",
        "exit_reason",
        "cum_equity",
        "cum_return_pct",
    ]
    roundtrip_df = pd.DataFrame(roundtrips)
    if roundtrip_df.empty:
        return pd.DataFrame(columns=expected_cols)
    roundtrip_df["cum_equity"] = initial_cash + roundtrip_df["realized_pnl"].cumsum()
    roundtrip_df["cum_return_pct"] = ((roundtrip_df["cum_equity"] - initial_cash) / initial_cash) * 100
    return roundtrip_df[expected_cols]


def run_trade_simulation(
    strategy_df: pd.DataFrame,
    initial_cash: float,
    rolling_window: int,
    stop_loss_pct: float,
    target_pct: float,
    risk_per_trade: float,
    max_position: float,
    slippage_pct: float,
    fee_pct: float,
    confidence_trade_threshold: float,
    pm_exit_confidence: float,
    use_pm: bool = False,
    label: str = "Without PM",
) -> dict:
    df = strategy_df.copy().sort_index()
    df["rolling_mean"] = df["Close"].rolling(rolling_window).mean()
    df["signal"] = np.where(df["Close"] > df["rolling_mean"], 1, np.where(df["Close"] < df["rolling_mean"], -1, 0))
    cash = float(initial_cash)
    position = 0.0
    avg_entry = None
    trades = []
    equity_curve = []
    skipped_pm_entries = 0
    for ts, row in df.iterrows():
        if pd.isna(row["rolling_mean"]):
            continue
        price = float(row["Close"])
        bar_high = float(row["High"]) if pd.notna(row["High"]) else price
        bar_low = float(row["Low"]) if pd.notna(row["Low"]) else price
        sig = int(row["signal"])
        equity_now = cash + position * price
        equity_curve.append((ts, equity_now))
        size = position_size_units(cash, price, stop_loss_pct, risk_per_trade)
        max_position_value = max_position * equity_now
        desired_position_value = (position + size) * price
        if abs(desired_position_value) > max_position_value:
            target_position_units = (np.sign(desired_position_value) * max_position_value / price) if price > 0 else 0.0
            size = target_position_units - position
        pm_multiplier = 1.0
        pm_entry_ok = True
        pm_exit = False
        if use_pm:
            pm_multiplier = np.clip(safe_float(row.get("PositionSize", 0.0), 0.0), 0.0, 1.0)
            pm_confidence = safe_float(row.get("FinalConfidence", 0.0), 0.0)
            pm_sentiment = safe_float(row.get("ProbEdge", 0.0), 0.0)
            pm_risk_zone = str(row.get("RiskZone", "Tradeable"))
            pm_entry_ok = (
                row.get("FinalAction", "No Trade") == "Long"
                and pm_confidence >= confidence_trade_threshold
                and pm_multiplier > 0
                and pm_risk_zone != "Avoid"
            )
            size *= pm_multiplier
            if position > 0 and (pm_confidence < pm_exit_confidence or pm_risk_zone == "Avoid" or pm_sentiment < -0.03):
                pm_exit = True
        stop_hit = False
        target_hit = False
        if position > 0 and avg_entry is not None:
            stop_price = avg_entry * (1 - stop_loss_pct)
            target_price = avg_entry * (1 + target_pct)
            if bar_low <= stop_price:
                stop_hit = True
            elif bar_high >= target_price:
                target_hit = True
        if sig == 1 and size > 0 and (pm_entry_ok if use_pm else True):
            fill = price * (1 + slippage_pct)
            max_affordable_qty = cash / (fill * (1 + fee_pct)) if fill > 0 else 0.0
            size = min(size, max_affordable_qty)
            if size > 0:
                notional = fill * size
                fee = fee_pct * notional
                cash -= (notional + fee)
                old_pos = position
                position += size
                avg_entry = fill if old_pos == 0 else ((avg_entry * old_pos + fill * size) / (old_pos + size))
                trades.append(
                    {
                        "timestamp": ts,
                        "side": "BUY",
                        "reason": "SIGNAL",
                        "fill_price": fill,
                        "qty": size,
                        "notional": notional,
                        "fee": fee,
                        "cash_after": cash,
                        "position_after": position,
                    }
                )
        elif sig == 1 and use_pm and not pm_entry_ok:
            skipped_pm_entries += 1
        elif position > 0 and (sig == -1 or stop_hit or target_hit or (use_pm and pm_exit)):
            fill = price * (1 - slippage_pct)
            qty = position
            notional = fill * qty
            fee = fee_pct * notional
            cash += (notional - fee)
            exit_reason = "STOP" if stop_hit else ("TARGET" if target_hit else ("PM_EXIT" if use_pm and pm_exit else "SIGNAL"))
            position = 0.0
            avg_entry = None
            trades.append(
                {
                    "timestamp": ts,
                    "side": "SELL",
                    "reason": exit_reason,
                    "fill_price": fill,
                    "qty": qty,
                    "notional": notional,
                    "fee": fee,
                    "cash_after": cash,
                    "position_after": position,
                }
            )
    if not df.empty:
        last_ts = df.index[-1]
        equity_curve.append((last_ts, cash + position * float(df["Close"].iloc[-1])))
    trades_df = pd.DataFrame(trades).sort_values("timestamp").reset_index(drop=True) if trades else pd.DataFrame(columns=["timestamp"])
    roundtrip_df = build_roundtrip_table(trades_df, initial_cash)
    equity_df = pd.DataFrame(equity_curve, columns=["timestamp", "equity"]).drop_duplicates(subset=["timestamp"], keep="last") if equity_curve else pd.DataFrame(columns=["timestamp", "equity"])
    final_equity = float(equity_df["equity"].iloc[-1]) if not equity_df.empty else float(initial_cash)
    max_drawdown = float((equity_df["equity"] / equity_df["equity"].cummax() - 1).min()) if not equity_df.empty else 0.0
    win_rate = float((roundtrip_df["realized_pnl"] > 0).mean()) if not roundtrip_df.empty else np.nan
    summary = {
        "Strategy": label,
        "Final Equity": final_equity,
        "Total Return %": ((final_equity - initial_cash) / initial_cash) * 100,
        "Max Drawdown %": max_drawdown * 100,
        "Round Trips": int(len(roundtrip_df)),
        "Win Rate %": win_rate * 100 if pd.notna(win_rate) else np.nan,
        "Stops": int((roundtrip_df["exit_reason"] == "STOP").sum()) if not roundtrip_df.empty else 0,
        "Targets": int((roundtrip_df["exit_reason"] == "TARGET").sum()) if not roundtrip_df.empty else 0,
        "Signal Exits": int((roundtrip_df["exit_reason"] == "SIGNAL").sum()) if not roundtrip_df.empty else 0,
        "PM Exits": int((roundtrip_df["exit_reason"] == "PM_EXIT").sum()) if (use_pm and not roundtrip_df.empty) else 0,
        "Skipped PM Entries": skipped_pm_entries,
    }
    return {"trades_df": trades_df, "roundtrip_df": roundtrip_df, "equity_df": equity_df, "summary": summary}


def mark_to_market_pnl(entry_yes_price: float, exit_yes_price: float, contracts: int, side: str = "YES") -> float:
    if side.upper() == "YES":
        return contracts * (exit_yes_price - entry_yes_price)
    return contracts * ((1 - exit_yes_price) - (1 - entry_yes_price))


def make_price_chart(strategy_df: pd.DataFrame, asset_label: str) -> go.Figure:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.46, 0.28, 0.26])
    fig.add_trace(go.Scatter(x=strategy_df.index, y=strategy_df["Close"], name=f"{asset_label} close", line=dict(color="#1f7a8c", width=3)), row=1, col=1)
    fig.add_trace(go.Scatter(x=strategy_df.index, y=strategy_df["rolling_mean"], name="Rolling mean", line=dict(color="#f6b73c", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=strategy_df.index, y=strategy_df["YES_Mid"], name="PM YES mid", line=dict(color="#d1495b", width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=strategy_df.index, y=strategy_df["FinalConfidence"], name="Final confidence", line=dict(color="#2c7be5", width=3)), row=3, col=1)
    fig.add_trace(go.Scatter(x=strategy_df.index, y=strategy_df["CautionScore"], name="Caution score", line=dict(color="#5f0f40", width=2)), row=3, col=1)
    fig.add_hline(y=35, row=3, col=1, line_dash="dash", line_color="#946100")
    fig.update_layout(template="plotly_white", height=820, margin=dict(l=16, r=16, t=32, b=16))
    fig.update_xaxes(rangeslider_visible=False)
    return fig


def make_equity_chart(without_pm: dict, with_pm: dict) -> go.Figure:
    fig = go.Figure()
    if not without_pm["equity_df"].empty:
        fig.add_trace(go.Scatter(x=without_pm["equity_df"]["timestamp"], y=without_pm["equity_df"]["equity"], name="Without PM", line=dict(color="#6c757d", width=3)))
    if not with_pm["equity_df"].empty:
        fig.add_trace(go.Scatter(x=with_pm["equity_df"]["timestamp"], y=with_pm["equity_df"]["equity"], name="With PM", line=dict(color="#169b9d", width=4)))
    fig.update_layout(template="plotly_white", height=420, margin=dict(l=16, r=16, t=40, b=16), title="10K equity curve comparison")
    return fig


def make_payoff_chart(payoff_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for horizon, subset in payoff_df.groupby("HorizonDays"):
        fig.add_trace(go.Scatter(x=subset["FuturePMProbability"], y=subset["WithoutPM_PnL"], name=f"Without PM {horizon}d", line=dict(width=2)))
        fig.add_trace(go.Scatter(x=subset["FuturePMProbability"], y=subset["WithPM_PnL"], name=f"With PM {horizon}d", line=dict(width=3, dash="dash")))
    fig.add_hline(y=0, line_color="#8795a1", line_dash="dash")
    fig.update_layout(template="plotly_white", height=460, margin=dict(l=16, r=16, t=40, b=16), title="P&L across probability outcomes and holding windows")
    return fig


def make_hedge_chart(hedge_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    palette = {
        "Spot Only": "#2c7be5",
        "Perp Hedge": "#169b9d",
        "Option Floor Proxy": "#f6b73c",
        "PM Overlay Hedge": "#d1495b",
    }
    for col in ["Spot Only", "Perp Hedge", "Option Floor Proxy", "PM Overlay Hedge"]:
        fig.add_trace(go.Scatter(x=hedge_df["AssetReturn"], y=hedge_df[col], name=col, line=dict(width=3, color=palette[col])))
    fig.add_hline(y=0, line_color="#8795a1", line_dash="dash")
    fig.add_vline(x=0, line_color="#d0d7de", line_dash="dash")
    fig.update_layout(template="plotly_white", height=460, margin=dict(l=16, r=16, t=40, b=16), title="Hedge lab: compare unhedged and hedged structures")
    return fig


def make_timing_chart(timing_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=timing_df["ResolutionWindowDays"], y=timing_df["AdjustedConfidence"], mode="lines+markers", name="Adjusted confidence", line=dict(color="#2c7be5", width=3)))
    fig.add_trace(go.Scatter(x=timing_df["ResolutionWindowDays"], y=timing_df["WithPM_ExpectedPnL"], mode="lines+markers", name="With PM expected P&L", line=dict(color="#d1495b", width=3)))
    fig.update_layout(template="plotly_white", height=420, margin=dict(l=16, r=16, t=40, b=16), title="Earlier vs later event resolution")
    return fig


def make_portfolio_chart(portfolio_without_pm: pd.DataFrame, portfolio_with_pm: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not portfolio_without_pm.empty:
        fig.add_trace(go.Scatter(x=portfolio_without_pm.index, y=portfolio_without_pm["PortfolioEquity"], name="Without PM portfolio", line=dict(color="#6c757d", width=3)))
    if not portfolio_with_pm.empty:
        fig.add_trace(go.Scatter(x=portfolio_with_pm.index, y=portfolio_with_pm["PortfolioEquity"], name="With PM portfolio", line=dict(color="#169b9d", width=4)))
    fig.update_layout(template="plotly_white", height=420, margin=dict(l=16, r=16, t=40, b=16), title="Portfolio equity across BTC, ETH, and SOL")
    return fig


def make_waterfall_chart(education_df: pd.DataFrame, asset_label: str) -> go.Figure:
    frame = education_df.iloc[:-2].copy()
    fig = go.Figure(go.Bar(
        x=frame["Value"],
        y=frame["Component"],
        orientation="h",
        marker_color=["#2a9d8f", "#2c7be5", "#98c1d9", "#f4a261", "#d1495b"],
    ))
    fig.add_vline(x=0, line_color="#8795a1")
    fig.update_layout(template="plotly_white", height=400, margin=dict(l=16, r=16, t=40, b=16), title=f"{asset_label}: why the PM-enhanced trade was sized this way")
    return fig


def build_probability_payoff_grid(strategy_df: pd.DataFrame, initial_cash: float, risk_per_trade: float, stop_loss_pct: float, max_position: float, horizons: list[int], probability_grid: np.ndarray) -> pd.DataFrame:
    latest = strategy_df.iloc[-1]
    current_price = float(latest["Close"])
    current_prob = safe_float(latest.get("YES_Mid", 0.5), 0.5)
    pm_delta = strategy_df["YES_Mid"].diff().replace([np.inf, -np.inf], np.nan)
    asset_ret = strategy_df["Return_1D"].replace([np.inf, -np.inf], np.nan)
    if pm_delta.notna().sum() > 5 and pm_delta.var(skipna=True) and pm_delta.var(skipna=True) > 0:
        beta = asset_ret.cov(pm_delta) / pm_delta.var(skipna=True)
    else:
        beta = 0.0
    base_units = position_size_units(initial_cash, current_price, stop_loss_pct, risk_per_trade)
    cap_units = (max_position * initial_cash) / current_price if current_price > 0 else 0.0
    base_units = min(base_units, cap_units)
    pm_units = base_units * np.clip(safe_float(latest.get("PositionSize", 0.0), 0.0), 0.0, 1.0)
    rows = []
    for horizon in horizons:
        scale = np.sqrt(max(horizon, 1)) / np.sqrt(30)
        for prob in probability_grid:
            implied_return = beta * (prob - current_prob) * scale
            without_pm_pnl = base_units * current_price * implied_return - (0.001 * current_price * base_units * 2)
            with_pm_pnl = pm_units * current_price * implied_return - (0.001 * current_price * pm_units * 2)
            rows.append({
                "HorizonDays": horizon,
                "FuturePMProbability": prob,
                "WithoutPM_PnL": without_pm_pnl,
                "WithPM_PnL": with_pm_pnl,
            })
    return pd.DataFrame(rows)


def build_hedge_profiles(strategy_df: pd.DataFrame, initial_cash: float, risk_per_trade: float, stop_loss_pct: float, max_position: float, return_grid: np.ndarray, perp_hedge_ratio: float, option_floor: float, option_premium_pct: float, pm_contract_cost: float) -> pd.DataFrame:
    latest = strategy_df.iloc[-1]
    current_price = float(latest["Close"])
    current_prob = safe_float(latest.get("YES_Mid", 0.5), 0.5)
    base_units = position_size_units(initial_cash, current_price, stop_loss_pct, risk_per_trade)
    cap_units = (max_position * initial_cash) / current_price if current_price > 0 else 0.0
    base_units = min(base_units, cap_units)
    pm_units = base_units * np.clip(safe_float(latest.get("PositionSize", 0.0), 0.0), 0.0, 1.0)
    rows = []
    for asset_return in return_grid:
        spot = base_units * current_price * asset_return
        perp = spot - (perp_hedge_ratio * base_units * current_price * asset_return)
        option = (base_units * current_price * max(asset_return, option_floor)) - (option_premium_pct * base_units * current_price)
        bearish_event = 1.0 if asset_return <= -0.05 else max(0.0, min(1.0, current_prob - asset_return))
        pm_overlay = spot + (pm_units * current_price * max(0.0, bearish_event - pm_contract_cost))
        rows.append({
            "AssetReturn": asset_return,
            "Spot Only": spot,
            "Perp Hedge": perp,
            "Option Floor Proxy": option,
            "PM Overlay Hedge": pm_overlay,
        })
    return pd.DataFrame(rows)


def build_resolution_window_table(strategy_df: pd.DataFrame, windows: list[int], confidence_trade_threshold: float) -> pd.DataFrame:
    latest = strategy_df.iloc[-1]
    current_price = float(latest["Close"])
    current_prob = safe_float(latest.get("YES_Mid", 0.5), 0.5)
    pm_delta = strategy_df["YES_Mid"].diff().replace([np.inf, -np.inf], np.nan)
    asset_ret = strategy_df["Return_1D"].replace([np.inf, -np.inf], np.nan)
    if pm_delta.notna().sum() > 5 and pm_delta.var(skipna=True) and pm_delta.var(skipna=True) > 0:
        beta = asset_ret.cov(pm_delta) / pm_delta.var(skipna=True)
    else:
        beta = 0.0
    base_units = position_size_units(10_000.0, current_price, 0.003, 0.01)
    pm_units = base_units * np.clip(safe_float(latest.get("PositionSize", 0.0), 0.0), 0.0, 1.0)
    rows = []
    for window in windows:
        scale = np.sqrt(max(window, 1)) / np.sqrt(30)
        adjusted_confidence = np.clip(latest["FinalConfidence"] - (window / max(windows)) * 8 + latest["ProbEdge"] * 18, 0, 100)
        expected_return = beta * (current_prob - 0.5) * scale
        rows.append({
            "ResolutionWindowDays": window,
            "AdjustedConfidence": adjusted_confidence,
            "ImpliedAssetReturn": expected_return,
            "WithoutPM_ExpectedPnL": base_units * current_price * expected_return,
            "WithPM_ExpectedPnL": pm_units * current_price * expected_return,
            "SuggestedSizeMultiplier": 0.0 if adjusted_confidence < confidence_trade_threshold else np.clip(pm_units / base_units if base_units > 0 else 0.0, 0.0, 1.0),
        })
    return pd.DataFrame(rows)


def build_asset_bundle(
    asset_label: str,
    ticker: str,
    start_date: date,
    end_date: date,
    interval: str,
    data_mode: str,
    config: dict,
    override_search: str,
    polymarket_limit: int,
    subjective_prob_buffer: float,
    caution_threshold: float,
    confidence_trade_threshold: float,
    sim_params: dict,
) -> dict:
    market_data, source = get_market_data(ticker, start_date, end_date, interval, data_mode)
    feature_data = build_feature_lab(market_data)
    board = build_real_market_board(config, asset_label, limit=polymarket_limit, override_search=override_search)
    if not board.empty:
        selected = board.iloc[0]
        entry_price = float(selected["best_ask"] if pd.notna(selected["best_ask"]) else selected["mid"])
        subjective_prob = float(np.clip(safe_float(selected["mid"], entry_price) + subjective_prob_buffer, 0.03, 0.97))
        resolution_days = max(int(selected["days_to_resolution"]) if pd.notna(selected["days_to_resolution"]) else 45, 1)
        prediction_market = simulate_prediction_market(
            feature_data,
            market_id=str(selected["slug"]),
            base_prob=safe_float(selected["mid"], entry_price),
            subjective_prob=subjective_prob,
            resolution_days=resolution_days,
            spread_anchor=safe_float(selected["spread"], 0.04),
            volume_anchor=safe_float(selected["volume"], 250000),
            seed=123 + sum(ord(ch) for ch in asset_label),
        )
        selected_market = selected
    else:
        entry_price = 0.44
        subjective_prob = float(np.clip(entry_price + subjective_prob_buffer, 0.03, 0.97))
        prediction_market = simulate_prediction_market(
            feature_data,
            market_id=f"{asset_label.lower()}_modeled_market",
            base_prob=entry_price,
            subjective_prob=subjective_prob,
            resolution_days=45,
            seed=123 + sum(ord(ch) for ch in asset_label),
        )
        selected_market = None
    strategy_df = build_strategy_frame(feature_data, prediction_market, caution_threshold, confidence_trade_threshold)
    rolling_window = min(sim_params["rolling_window"], max(5, len(strategy_df) - 1))
    strategy_df["rolling_mean"] = strategy_df["Close"].rolling(rolling_window).mean()
    strategy_df["signal"] = np.where(strategy_df["Close"] > strategy_df["rolling_mean"], 1, np.where(strategy_df["Close"] < strategy_df["rolling_mean"], -1, 0))
    sim_runtime = {key: value for key, value in sim_params.items() if key != "pm_exit_confidence"}
    without_pm = run_trade_simulation(
        strategy_df,
        use_pm=False,
        label=f"{asset_label} Without PM",
        confidence_trade_threshold=confidence_trade_threshold,
        pm_exit_confidence=sim_params["pm_exit_confidence"],
        **sim_runtime,
    )
    with_pm = run_trade_simulation(
        strategy_df,
        use_pm=True,
        label=f"{asset_label} With PM",
        confidence_trade_threshold=confidence_trade_threshold,
        pm_exit_confidence=sim_params["pm_exit_confidence"],
        **sim_runtime,
    )
    return {
        "asset_label": asset_label,
        "ticker": ticker,
        "market_source": source,
        "market_data": market_data,
        "feature_data": feature_data,
        "real_market_board": board,
        "selected_market": selected_market,
        "strategy_df": strategy_df,
        "without_pm": without_pm,
        "with_pm": with_pm,
    }


def build_portfolio_equity(asset_results: dict, weights: dict[str, float], variant_key: str) -> pd.DataFrame:
    aligned = []
    for label, bundle in asset_results.items():
        equity_df = bundle[variant_key]["equity_df"].copy()
        if equity_df.empty:
            continue
        equity_df = equity_df.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
        equity_df["timestamp"] = pd.to_datetime(equity_df["timestamp"])
        series = equity_df.set_index("timestamp")["equity"].resample("D").last().ffill()
        aligned.append(((series / 10000.0) * weights.get(label, 0.0)).rename(label))
    if not aligned:
        return pd.DataFrame(columns=["PortfolioEquity"])
    portfolio = pd.concat(aligned, axis=1).ffill()
    portfolio["PortfolioEquity"] = portfolio.sum(axis=1) * 10000.0
    return portfolio


def render_overview(bundle: dict) -> None:
    strategy_df = bundle["strategy_df"]
    latest = strategy_df.iloc[-1]
    section_intro(
        "What this tab tells you",
        "Start here to understand the latest state of the strategy. This tab answers three questions: what the market is doing, what Polymarket is implying, and whether the trade should be taken, reduced, or avoided.",
    )
    inject_card_metrics(
        [
            ("Asset", bundle["ticker"]),
            ("Market Source", bundle["market_source"]),
            ("Risk Zone", str(latest["RiskZone"])),
            ("Final Confidence", f"{latest['FinalConfidence']:.1f}"),
        ]
    )
    st.markdown(f"<div class='risk-pill {risk_css(str(latest['RiskZone']))}'>{latest['RiskZone']}</div>", unsafe_allow_html=True)
    render_verdict_box(bundle)
    explain_text(
        "The baseline strategy only looks at price relative to the rolling mean. "
        "The PM-enhanced strategy uses the same entry engine, then asks whether Polymarket is confirming the idea, reducing size, or vetoing it."
    )
    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Latest decision card")
        decision = pd.Series(
            {
                "Close": latest["Close"],
                "Rolling Mean": latest["rolling_mean"],
                "Technical Score": latest["TechnicalScore"],
                "YES Mid": latest["YES_Mid"],
                "Probability Edge": latest["ProbEdge"],
                "Caution Score": latest["CautionScore"],
                "Final Confidence": latest["FinalConfidence"],
                "Position Size": latest["PositionSize"],
                "Final Action": latest["FinalAction"],
            }
        )
        st.dataframe(decision.to_frame("Value"), use_container_width=True)
        stress = compute_stress_feed(bundle["feature_data"])
        if not stress.empty:
            st.caption("Recent stress feed")
            st.dataframe(stress, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.plotly_chart(make_price_chart(strategy_df, bundle["asset_label"]), use_container_width=True)


def render_trade_engine(bundle: dict) -> None:
    without_pm = bundle["without_pm"]
    with_pm = bundle["with_pm"]
    summary = pd.DataFrame([without_pm["summary"], with_pm["summary"]])
    section_intro(
        "How to read the trade engine",
        "Both engines trade with the same old-notebook mechanics: 10K capital, risk-based sizing, stop-loss, target, slippage, and fees. The PM version changes only the decision quality layer: it filters entries, cuts size, and exits defensively when PM deteriorates.",
    )
    explain_text(
        "Both engines start with the same 10K capital and the same stop, target, fee, and slippage assumptions. "
        "The only difference is that the PM version uses Polymarket to filter entries, cut position size, and trigger defensive exits."
    )
    latest_without = without_pm["summary"]
    latest_with = with_pm["summary"]
    inject_card_metrics(
        [
            ("Without PM return", f"{latest_without['Total Return %']:.2f}%"),
            ("With PM return", f"{latest_with['Total Return %']:.2f}%"),
            ("PM skipped entries", f"{latest_with['Skipped PM Entries']}"),
            ("With PM win rate", f"{latest_with['Win Rate %']:.1f}%"),
        ]
    )
    st.dataframe(summary, use_container_width=True)
    st.plotly_chart(make_equity_chart(without_pm, with_pm), use_container_width=True)
    tab_a, tab_b, tab_c = st.tabs(["Without PM", "With PM", "Raw Fills"])
    with tab_a:
        st.subheader("Round-trip P&L (Without PM)")
        st.dataframe(without_pm["roundtrip_df"], use_container_width=True)
    with tab_b:
        st.subheader("Round-trip P&L (With PM)")
        st.dataframe(with_pm["roundtrip_df"], use_container_width=True)
    with tab_c:
        fills = pd.concat([without_pm["trades_df"].assign(strategy="Without PM"), with_pm["trades_df"].assign(strategy="With PM")], ignore_index=True)
        st.dataframe(fills, use_container_width=True)


def render_market_board(bundle: dict) -> None:
    board = bundle["real_market_board"]
    section_intro(
        "What this market board means",
        "This board is the live PM context layer. It does not create trades by itself. Instead, it tells the strategy whether the market looks liquid, tight, event-heavy, or contradictory.",
    )
    explain_text(
        "This is the live Polymarket board that feeds the strategy studio. "
        "If live book prices are available, the dashboard uses them; otherwise it falls back to modeled probability dynamics."
    )
    if board.empty:
        st.warning("No live Polymarket markets were found for the selected asset and search terms.")
        return
    selected = bundle["selected_market"]
    if selected is not None:
        inject_card_metrics(
            [
                ("Selected market", str(selected["slug"])),
                ("YES mid", f"{safe_float(selected['mid'], 0.0):.3f}"),
                ("Spread", f"{safe_float(selected['spread'], 0.0):.4f}"),
                ("Days to resolution", f"{int(safe_float(selected['days_to_resolution'], 0.0))}"),
            ]
        )
    display_cols = ["slug", "question", "mid", "best_bid", "best_ask", "spread", "liquidity", "volume", "days_to_resolution", "book_source"]
    st.dataframe(board[display_cols], use_container_width=True)


def render_payoff_and_hedge(bundle: dict, sim_params: dict, probability_grid: np.ndarray, horizons: list[int], hedge_params: dict) -> None:
    strategy_df = bundle["strategy_df"]
    section_intro(
        "How to read the payoff studio",
        "The payoff chart converts PM probability shifts into expected asset P&L using the observed relationship between PM moves and asset returns. The hedge lab then shows how different structures can smooth or reshape that payoff.",
    )
    payoff_df = build_probability_payoff_grid(
        strategy_df,
        initial_cash=sim_params["initial_cash"],
        risk_per_trade=sim_params["risk_per_trade"],
        stop_loss_pct=sim_params["stop_loss_pct"],
        max_position=sim_params["max_position"],
        horizons=horizons,
        probability_grid=probability_grid,
    )
    hedge_df = build_hedge_profiles(
        strategy_df,
        initial_cash=sim_params["initial_cash"],
        risk_per_trade=sim_params["risk_per_trade"],
        stop_loss_pct=sim_params["stop_loss_pct"],
        max_position=sim_params["max_position"],
        return_grid=np.linspace(-0.20, 0.20, 81),
        perp_hedge_ratio=hedge_params["perp_hedge_ratio"],
        option_floor=hedge_params["option_floor"],
        option_premium_pct=hedge_params["option_premium_pct"],
        pm_contract_cost=hedge_params["pm_contract_cost"],
    )
    left, right = st.columns(2)
    with left:
        explain_text(
            "This payoff view answers: if the market's implied YES probability moves from today's level to a future level over different holding windows, "
            "how does the plain strategy compare with the PM-sized version?"
        )
        st.plotly_chart(make_payoff_chart(payoff_df), use_container_width=True)
    with right:
        explain_text(
            "This hedge lab shows four structures: plain spot exposure, a perp-style partial hedge, an option-floor proxy, and a PM overlay hedge. "
            "It is not execution-ready options pricing; it is a visual risk-translation tool."
        )
        st.plotly_chart(make_hedge_chart(hedge_df), use_container_width=True)
    st.dataframe(payoff_df.head(18), use_container_width=True)


def render_timing_and_portfolio(bundle: dict, confidence_trade_threshold: float, asset_results: dict, weights: dict[str, float]) -> None:
    section_intro(
        "Timing and portfolio logic",
        "This tab asks two questions. First: what happens if the event resolves sooner or later than expected? Second: if you spread the same framework across BTC, ETH, and SOL, does PM improve the whole basket or just one asset?",
    )
    timing_df = build_resolution_window_table(bundle["strategy_df"], [3, 7, 14, 30, 60], confidence_trade_threshold)
    portfolio_without_pm = build_portfolio_equity(asset_results, weights, "without_pm")
    portfolio_with_pm = build_portfolio_equity(asset_results, weights, "with_pm")
    left, right = st.columns(2)
    with left:
        explain_text(
            "Earlier vs later event resolution matters because confidence decays, carry changes, and PM confirmation can weaken before a thesis is resolved."
        )
        st.plotly_chart(make_timing_chart(timing_df), use_container_width=True)
        st.dataframe(timing_df, use_container_width=True)
    with right:
        explain_text(
            "The portfolio view runs the same engine across BTC, ETH, and SOL, then combines them with your chosen weights to show how PM changes aggregate equity."
        )
        st.plotly_chart(make_portfolio_chart(portfolio_without_pm, portfolio_with_pm), use_container_width=True)
        portfolio_summary = pd.DataFrame(
            [
                {
                    "Variant": "Without PM Portfolio",
                    "Final Equity": portfolio_without_pm["PortfolioEquity"].iloc[-1] if not portfolio_without_pm.empty else np.nan,
                    "Total Return %": ((portfolio_without_pm["PortfolioEquity"].iloc[-1] - 10000.0) / 10000.0) * 100 if not portfolio_without_pm.empty else np.nan,
                },
                {
                    "Variant": "With PM Portfolio",
                    "Final Equity": portfolio_with_pm["PortfolioEquity"].iloc[-1] if not portfolio_with_pm.empty else np.nan,
                    "Total Return %": ((portfolio_with_pm["PortfolioEquity"].iloc[-1] - 10000.0) / 10000.0) * 100 if not portfolio_with_pm.empty else np.nan,
                },
            ]
        )
        st.dataframe(portfolio_summary, use_container_width=True)


def render_education(bundle: dict) -> None:
    latest = bundle["strategy_df"].iloc[-1]
    section_intro(
        "Why the dashboard made this call",
        "This is the teaching tab. Use it to explain the trade to someone else: which parts of the model increased conviction, which parts reduced it, and why the final size is not simply the same as the technical signal.",
    )
    education_df = pd.DataFrame(
        [
            {"Component": "Technical confidence contribution", "Value": 0.55 * latest["TechnicalConfidence"]},
            {"Component": "PM confirmation contribution", "Value": 0.25 * latest["PMConfirmationScore"]},
            {"Component": "PM quality contribution", "Value": 0.10 * latest["PMQualityScore"]},
            {"Component": "PM conflict penalty", "Value": -0.10 * latest["PMConflictPenalty"]},
            {"Component": "Caution penalty", "Value": -0.25 * latest["CautionScore"]},
            {"Component": "Final confidence", "Value": latest["FinalConfidence"]},
            {"Component": "Position size", "Value": latest["PositionSize"]},
        ]
    )
    explain_text(
        "Read this tab like a teaching screen. Positive bars push confidence up, negative bars push it down. "
        "A trade can still be directionally correct but structurally poor if caution penalties dominate."
    )
    left, right = st.columns([1.1, 0.9])
    with left:
        st.dataframe(education_df, use_container_width=True)
        glossary = pd.DataFrame(
            [
                {"Concept": "Rolling mean signal", "Explanation": "The old strategy buys when price is above the rolling mean and exits when it falls below."},
                {"Concept": "Position size", "Explanation": "Fraction of the base risk-based trade size that PM allows after confidence and caution are applied."},
                {"Concept": "Caution score", "Explanation": "Composite penalty built from volatility, drawdown, PM spread, divergence, and event timing."},
                {"Concept": "PM confirmation", "Explanation": "How strongly Polymarket agrees with the asset trade, based on probability edge and momentum."},
                {"Concept": "PM exit", "Explanation": "An early defensive exit used only in the PM strategy when confidence collapses or risk turns structurally bad."},
            ]
        )
        st.dataframe(glossary, use_container_width=True)
    with right:
        st.plotly_chart(make_waterfall_chart(education_df, bundle["asset_label"]), use_container_width=True)


def main() -> None:
    inject_styles()
    render_header()

    env_path = Path.cwd() / "Yhack" / ".env"
    if not env_path.exists():
        env_path = Path.cwd() / ".env"
    config = get_polymarket_config(env_path)

    with st.sidebar:
        st.subheader("Strategy Controls")
        asset_label = st.selectbox("Asset", list(ASSET_MAP.keys()), index=0)
        ticker = ASSET_MAP[asset_label]
        default_start = date.today() - timedelta(days=730)
        start_date = st.date_input("Backtest start", value=default_start)
        end_date = st.date_input("Backtest end", value=date.today())
        interval = st.selectbox("Interval", ["1d", "1h"], index=0)
        data_mode = st.selectbox("Underlying source", ["Kraken", "Synthetic"], index=0)
        override_search = st.text_input("Polymarket search override", value="")
        polymarket_limit = st.slider("Live PM market count", 5, 40, 15)
        subjective_prob_buffer = st.slider("Subjective PM edge buffer", 0.0, 0.20, 0.05, 0.01)
        caution_threshold = st.slider("Avoid threshold", 55, 90, 75)
        confidence_trade_threshold = st.slider("Trade confidence threshold", 20, 70, 35)
        pm_exit_confidence = st.slider("PM defensive exit threshold", 5, 50, 25)

        st.markdown("---")
        st.subheader("Trade Engine")
        initial_cash = st.number_input("Initial capital", value=10000.0, step=1000.0)
        rolling_window = st.slider("Rolling window", 10, 120, 70)
        risk_per_trade = st.slider("Risk per trade", 0.001, 0.03, 0.01163, 0.0005, format="%.4f")
        max_position = st.slider("Max position share of equity", 0.02, 0.30, 0.07692, 0.005, format="%.4f")
        stop_loss_pct = st.slider("Stop-loss %", 0.002, 0.03, 0.00319, 0.0005, format="%.4f")
        target_pct = st.slider("Target %", 0.002, 0.03, 0.00993, 0.0005, format="%.4f")
        slippage_pct = st.slider("Slippage %", 0.0000, 0.0050, 0.0005, 0.0001, format="%.4f")
        fee_pct = st.slider("Fee %", 0.0000, 0.0050, 0.0010, 0.0001, format="%.4f")

        st.markdown("---")
        st.subheader("Hedge Lab")
        perp_hedge_ratio = st.slider("Perp hedge ratio", 0.0, 1.0, 0.50, 0.05)
        option_floor = st.slider("Option floor return", -0.20, 0.0, -0.08, 0.01)
        option_premium_pct = st.slider("Option premium %", 0.0, 0.05, 0.01, 0.005)
        pm_contract_cost = st.slider("PM hedge contract cost", 0.0, 0.25, 0.08, 0.01)

        st.markdown("---")
        st.subheader("Portfolio Weights")
        w_btc = st.slider("BTC weight", 0.0, 1.0, 0.50, 0.05)
        w_eth = st.slider("ETH weight", 0.0, 1.0, 0.30, 0.05)
        w_sol = st.slider("SOL weight", 0.0, 1.0, 0.20, 0.05)
        weight_sum = max(w_btc + w_eth + w_sol, 1e-9)
        portfolio_weights = {"BTC": w_btc / weight_sum, "ETH": w_eth / weight_sum, "SOL": w_sol / weight_sum}

        st.markdown("---")
        st.caption("Safe Polymarket config status")
        st.json(redacted_polymarket_config(env_path))

    if start_date >= end_date:
        st.error("Start date must be before end date.")
        st.stop()

    sim_params = {
        "initial_cash": float(initial_cash),
        "rolling_window": int(rolling_window),
        "stop_loss_pct": float(stop_loss_pct),
        "target_pct": float(target_pct),
        "risk_per_trade": float(risk_per_trade),
        "max_position": float(max_position),
        "slippage_pct": float(slippage_pct),
        "fee_pct": float(fee_pct),
        "pm_exit_confidence": float(pm_exit_confidence),
    }
    hedge_params = {
        "perp_hedge_ratio": float(perp_hedge_ratio),
        "option_floor": float(option_floor),
        "option_premium_pct": float(option_premium_pct),
        "pm_contract_cost": float(pm_contract_cost),
    }

    bundle = build_asset_bundle(
        asset_label=asset_label,
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        interval=interval,
        data_mode=data_mode,
        config=config,
        override_search=override_search,
        polymarket_limit=polymarket_limit,
        subjective_prob_buffer=subjective_prob_buffer,
        caution_threshold=float(caution_threshold),
        confidence_trade_threshold=float(confidence_trade_threshold),
        sim_params=sim_params,
    )

    asset_results = {}
    for label, asset_ticker in ASSET_MAP.items():
        search_override = override_search if label == asset_label else ""
        asset_results[label] = build_asset_bundle(
            asset_label=label,
            ticker=asset_ticker,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            data_mode=data_mode,
            config=config,
            override_search=search_override,
            polymarket_limit=min(polymarket_limit, 12),
            subjective_prob_buffer=subjective_prob_buffer,
            caution_threshold=float(caution_threshold),
            confidence_trade_threshold=float(confidence_trade_threshold),
            sim_params=sim_params,
        )

    latest = bundle["strategy_df"].iloc[-1]
    inject_card_metrics(
        [
            ("Ticker", ticker),
            ("Live PM markets", str(len(bundle["real_market_board"]))),
            ("Latest action", str(latest["FinalAction"])),
            ("Position size", f"{latest['PositionSize']:.2f}x"),
        ]
    )

    tabs = st.tabs(["Overview", "Trade Engine", "Market Board", "Payoff Studio", "Timing + Portfolio", "Education"])
    with tabs[0]:
        render_overview(bundle)
    with tabs[1]:
        render_trade_engine(bundle)
    with tabs[2]:
        render_market_board(bundle)
    with tabs[3]:
        render_payoff_and_hedge(bundle, sim_params, np.round(np.linspace(0.10, 0.90, 17), 2), [3, 7, 14, 30], hedge_params)
    with tabs[4]:
        render_timing_and_portfolio(bundle, float(confidence_trade_threshold), asset_results, portfolio_weights)
    with tabs[5]:
        render_education(bundle)


if __name__ == "__main__":
    main()
