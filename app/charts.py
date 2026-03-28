import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_CHART_FONT = dict(family="JetBrains Mono, monospace", color="#8892a4", size=10)
_TITLE_FONT = dict(family="Barlow Condensed, sans-serif", size=17, color="#f0f4f8")
_GRID = dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.09)")
_LEGEND = dict(bgcolor="rgba(15,16,24,0.85)", bordercolor="rgba(255,255,255,0.1)", borderwidth=1)
_BASE_LAYOUT = dict(
    paper_bgcolor="rgba(15,16,24,0)",
    plot_bgcolor="rgba(15,16,24,0.55)",
    font=_CHART_FONT,
    xaxis=_GRID,
    yaxis=_GRID,
)


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

    fig.update_layout(
        **_BASE_LAYOUT,
        height=900,
        margin=dict(l=20, r=20, t=70, b=20),
        legend=dict(
            **_LEGEND,
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
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
        **_BASE_LAYOUT,
        height=420,
        margin=dict(l=20, r=20, t=44, b=20),
        title=dict(text="Backtest Equity Curve", font=_TITLE_FONT),
        legend=_LEGEND,
    )
    return fig


def correlation_chart(correlation_series: pd.Series, ticker: str, benchmark: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=correlation_series.index, y=correlation_series, name="Rolling Correlation", line=dict(color="#f59e0b", width=3)))
    fig.add_hline(y=0, line_color="#94a3b8", line_dash="dash")
    fig.update_layout(
        **_BASE_LAYOUT,
        height=360,
        margin=dict(l=20, r=20, t=44, b=20),
        title=dict(text=f"20-Period Correlation: {ticker} vs {benchmark}", font=_TITLE_FONT),
    )
    return fig


def ml_chart(valid: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=valid.index, y=valid["TargetNextReturn"], name="Actual Next Return", line=dict(color="#38bdf8")))
    fig.add_trace(go.Scatter(x=valid.index, y=valid["PredictedNextReturn"], name="Predicted Next Return", line=dict(color="#f472b6")))
    fig.update_layout(
        **_BASE_LAYOUT,
        height=360,
        margin=dict(l=20, r=20, t=44, b=20),
        title=dict(text="Walk-Forward ML Forecast", font=_TITLE_FONT),
        legend=_LEGEND,
    )
    return fig


def blended_equity_chart(blended: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=blended.index, y=blended["StrategyEquity"], name="Rule-Based", line=dict(color="#38bdf8", width=3)))
    fig.add_trace(go.Scatter(x=blended.index, y=blended["BlendedEquity"], name="Blended", line=dict(color="#f472b6", width=3)))
    fig.update_layout(
        **_BASE_LAYOUT,
        height=360,
        margin=dict(l=20, r=20, t=44, b=20),
        title=dict(text="Rule-Based vs Blended Equity", font=_TITLE_FONT),
        legend=_LEGEND,
    )
    return fig
