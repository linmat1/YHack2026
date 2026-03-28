# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
streamlit run trading_simulator.py
```

Install dependencies (no `requirements.txt` exists):

```bash
pip install streamlit plotly yfinance pandas numpy scikit-learn
```

## Architecture

The entire application lives in a single file: `trading_simulator.py` (1,078 lines). There is also `trading_simulator_experiments.ipynb` for testing individual components in isolation.

### Execution Flow (`main()`)

`main()` orchestrates the full pipeline on every Streamlit re-run:

1. `inject_styles()` / `initialize_state()` / `render_header()` — setup
2. `sidebar_controls()` → returns a `controls` dict (ticker, dates, strategy, indicator params, feature toggles)
3. `get_data_cached()` → raw OHLCV `DataFrame`
4. `build_feature_lab()` → `feature_data` with 25+ indicators
5. `apply_strategy()` → `(strategy_data, signal_col)` — adds `Signal` column (1=buy, −1=sell, 0=hold)
6. `run_backtest()` → `backtest` DataFrame with equity curves and drawdown
7. Six `st.tabs` render the dashboard using the above outputs

### Data Pipeline

- **`get_data_cached()`** — fetches OHLCV from Yahoo Finance via `yfinance`; falls back to synthetic data (geometric Brownian motion) on failure. Decorated with `@st.cache_data` keyed on ticker+dates+interval+mode.
- **`build_feature_lab()`** — computes SMA, EMA, RSI, MACD, Bollinger Bands, ATR, volatility, drawdown, and regime flags from raw OHLCV.

### Trading Strategies (`apply_strategy()`)

Five rule-based strategies selected via sidebar; all produce a `Signal` column on the DataFrame:
- **RSI** — RSI < 30 = buy, RSI > 70 = sell
- **Trend** — price vs SMA-20 crossover
- **MACD** — MACD histogram sign changes
- **Breakout** — Bollinger Band breakouts
- **Ensemble** — weighted blend (35% RSI + 35% Trend + 20% MACD + 10% Breakout)

### Backtesting (`run_backtest()`)

Simulates strategy execution with position sizing, configurable trading fees (bps), equity curve tracking, drawdown calculation, and comparison to a buy-and-hold benchmark.

### ML Layer (`walk_forward_random_forest()`)

Walk-forward Random Forest (250 trees, depth 6, 5 ensemble seeds). Trains on the first 70% of data, validates on the remaining 30%. In the Quant Lab tab, ML signals are blended 35%/65% with rule-based signals: `signal_mix = 0.65 * rule_signal + 0.35 * ml_signal`.

### Dashboard (6 Tabs)

| Tab | Content |
|-----|---------|
| Overview | Market snapshot, stress event feed, strategy report card |
| Charts | Price+signals, RSI/MACD, volatility/drawdown |
| Backtest | Equity curves, return/risk metrics, hit rates |
| Watchlist | Pulse scan across multiple tickers |
| Quant Lab | ML forecasts, horizon scorecard, blended strategy equity curve |
| Raw Data | Raw OHLCV table and computed feature table |

### Sidebar Controls

Returned as a single `controls` dict from `sidebar_controls()`. Key fields: `ticker`, `start_date`, `end_date`, `interval`, `data_mode` (Auto/Live/Synthetic), `strategy_choice`, indicator windows (`rsi_window`, `fast_window`, `slow_window`, `trend_window`, `long_trend_window`, `vol_window`), `fee_bps`, `watchlist`, `benchmark`, and boolean toggles `show_ml`, `show_watchlist`, `show_correlation`, `show_raw`.

### Session State

`initialize_state()` seeds `st.session_state` with default ticker (`AAPL`) and date range (1 year). Quick-ticker buttons in `quick_ticker_buttons()` mutate `st.session_state.ticker` to trigger re-runs.
