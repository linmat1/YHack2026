from datetime import date, timedelta

import streamlit as st


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


def quick_ticker_buttons() -> None:
    tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "SPY", "QQQ"]
    cols = st.columns(len(tickers))
    for col, symbol in zip(cols, tickers):
        if col.button(symbol, use_container_width=True):
            st.session_state["ticker_input"] = symbol
            st.session_state["run_app"] = True


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
        show_polymarket = st.checkbox("Show prediction markets", value=True)

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
        "show_polymarket": show_polymarket,
    }
