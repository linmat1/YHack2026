# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
streamlit run trading_simulator.py
```

The app launches an interactive web UI ("Rentwise Quant Lab") in the browser.

## Architecture

The entire application lives in a single file: `trading_simulator.py` (~1,078 lines). There is also `trading_simulator_experiments.ipynb` for testing individual components in isolation.

### Data Pipeline

1. **`get_data_cached()`** — fetches OHLCV data from Yahoo Finance via `yfinance`; falls back to synthetic data (geometric Brownian motion) if the fetch fails
2. **`build_feature_lab()`** — computes 25+ technical indicators on top of the raw price data (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, volatility, drawdown, regime flags)

### Trading Strategies (`apply_strategy()`)

Five rule-based strategies, selected via the sidebar:
- **RSI** — RSI < 30 = buy, RSI > 70 = sell
- **Trend** — price vs SMA-20 crossover
- **MACD** — MACD histogram sign changes
- **Breakout** — Bollinger Band breakouts
- **Ensemble** — weighted blend (35% RSI + 35% Trend + 20% MACD + 10% Breakout)

### Backtesting (`run_backtest()`)

Simulates strategy execution with position sizing, configurable trading fees (bps), equity curve tracking, drawdown calculation, and comparison to a buy-and-hold benchmark.

### ML Layer (`walk_forward_random_forest()`)

Walk-forward Random Forest (250 trees, depth 6, 5 ensemble seeds). Trains on the first 70% of data, validates on the remaining 30%. Predicts next-day returns from the feature set; ML signals can be blended with rule-based signals in the **Quant Lab** tab.

### Dashboard (6 Tabs)

| Tab | Content |
|-----|---------|
| Overview | Market snapshot, stress event feed, strategy report card |
| Charts | Price+signals, RSI/MACD, volatility/drawdown |
| Backtest | Equity curves, return/risk metrics, hit rates |
| Watchlist | Pulse scan across multiple tickers |
| Quant Lab | ML forecasts and blended strategies |
| Raw Data | Market data table and computed features |

### Sidebar Controls

Ticker, date range, data source (Auto/Live/Synthetic), strategy selection, indicator parameter tuning, watchlist tickers, benchmark (default: SPY), and feature toggles (ML, watchlist, correlation).

## Dependencies

No `requirements.txt` exists. Required packages: `streamlit`, `plotly`, `yfinance`, `pandas`, `numpy`, `scikit-learn`.
