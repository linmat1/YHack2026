import json
import time

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from .ui import metric_card

_TITLE_FONT = dict(family="Barlow Condensed, sans-serif", size=17, color="#f0f4f8")
_GRID = dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.09)")
_LEGEND = dict(bgcolor="rgba(15,16,24,0.85)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1)


@st.cache_data(show_spinner=False, ttl=300)
def fetch_polymarket_markets(keyword: str) -> tuple[list[dict], str]:
    try:
        resp = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={"keyword": keyword, "active": "true", "limit": 20},
            timeout=6,
        )
        data = resp.json()
        for market in data:
            raw = market.get("outcomePrices", "[]")
            try:
                market["outcomePrices"] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                market["outcomePrices"] = ["0.5", "0.5"]
        return data, "Polymarket Gamma API"
    except Exception:
        return [], "Unavailable"


@st.cache_data(show_spinner=False, ttl=300)
def fetch_polymarket_price_history(condition_id: str, lookback_days: int = 30) -> tuple[pd.DataFrame, str]:
    try:
        end_ts = int(time.time())
        start_ts = end_ts - lookback_days * 86400
        resp = requests.get(
            "https://clob.polymarket.com/prices-history",
            params={"market_id": condition_id, "startTs": start_ts, "endTs": end_ts, "fidelity": 60},
            timeout=6,
        )
        points = resp.json().get("history", [])
        df = pd.DataFrame(points)
        if df.empty or "t" not in df.columns:
            return pd.DataFrame(), "Unavailable"
        df.index = pd.to_datetime(df["t"], unit="s", utc=True)
        df = df.rename(columns={"p": "yes_prob"})[["yes_prob"]]
        return df, "Polymarket CLOB API"
    except Exception:
        return pd.DataFrame(), "Unavailable"


def polymarket_prob_chart(price_history: pd.DataFrame, question: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=price_history.index,
        y=price_history["yes_prob"],
        name="YES Probability",
        line=dict(color="#f59e0b", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(245,158,11,0.08)",
    ))
    title_text = question[:80] + ("..." if len(question) > 80 else "")
    fig.update_layout(
        paper_bgcolor="rgba(15,16,24,0)",
        plot_bgcolor="rgba(15,16,24,0.55)",
        font=dict(family="JetBrains Mono, monospace", color="#8892a4", size=10),
        height=360,
        margin=dict(l=20, r=20, t=44, b=20),
        title=dict(text=title_text, font=_TITLE_FONT),
        xaxis=_GRID,
        yaxis=dict(**_GRID, tickformat=".0%", range=[0, 1]),
        legend=_LEGEND,
    )
    fig.add_hline(y=0.5, line_color="#94a3b8", line_dash="dash", opacity=0.6)
    return fig


def render_polymarket_tab(ticker: str) -> None:
    markets, source = fetch_polymarket_markets(ticker)
    if not markets:
        st.info(
            f"No active prediction markets found for '{ticker}'. "
            "Polymarket may not have markets for this symbol, or the API is temporarily unavailable."
        )
        return

    rows = []
    for m in markets:
        try:
            yes_prob = float(m["outcomePrices"][0])
        except (IndexError, ValueError, TypeError):
            yes_prob = 0.5
        vol = float(m.get("volume", 0) or 0)
        try:
            end_dt = pd.to_datetime(m["endDate"], utc=True)
            days_left = max(0, (end_dt - pd.Timestamp.now(tz="UTC")).days)
        except Exception:
            days_left = 0
        rows.append({"market": m, "yes_prob": yes_prob, "vol": vol, "days_left": days_left})

    rows.sort(key=lambda r: r["vol"], reverse=True)

    card_rows = rows[:4]
    cols = st.columns(len(card_rows))
    for col, r in zip(cols, card_rows):
        q = r["market"].get("question", "")
        question_short = q[:40] + ("..." if len(q) > 40 else "")
        col.markdown(
            metric_card(question_short, f"{r['yes_prob']:.0%}", f"Vol ${r['vol']:,.0f} · {r['days_left']}d left"),
            unsafe_allow_html=True,
        )

    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("All Markets")
    table_df = pd.DataFrame([{
        "Question": r["market"].get("question", ""),
        "YES %": f"{r['yes_prob']:.1%}",
        "Volume ($)": f"{r['vol']:,.0f}",
        "Closes In": f"{r['days_left']}d",
    } for r in rows])
    st.dataframe(table_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    top = rows[0]["market"]
    hist_df, hist_source = fetch_polymarket_price_history(top.get("conditionId", ""))
    if hist_df.empty:
        st.info("Price history is not available for this market.")
    else:
        st.plotly_chart(polymarket_prob_chart(hist_df, top.get("question", "")), use_container_width=True)

    st.caption(f"Data: {source} · {hist_source} · Cached 5 min")
