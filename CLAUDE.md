# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

The project has two distinct implementations:

1. **Legacy monolith** — `trading_simulator.py` (single-file Streamlit app, ~1,078 lines)
2. **Current multi-tier app** — three separate services that work together:
   - `app/` — modularized Streamlit frontend (refactor of the monolith)
   - `api/` — FastAPI backend serving REST endpoints
   - `frontend/` — Next.js frontend that consumes the FastAPI backend

## Running the Services

### Legacy Streamlit (monolith)
```bash
streamlit run trading_simulator.py
```

### Current multi-tier stack

**FastAPI backend** (runs on port 8000):
```bash
uvicorn api.main:app --reload
```

**Streamlit modular app** (uses `app/` package):
```bash
streamlit run -c "from app.main import main; main()"
```

**Next.js frontend** (runs on port 3000, connects to FastAPI):
```bash
cd frontend && npm run dev
```

Set `NEXT_PUBLIC_API_URL` to override the API base (default: `http://localhost:8000/api`).

### Install dependencies
```bash
pip install streamlit plotly yfinance pandas numpy scikit-learn fastapi uvicorn requests
cd frontend && npm install
```

## `api/` — FastAPI Backend

Entry point: `api/main.py`. Mounts all routers under `/api` prefix with CORS open to localhost:3000/3001.

| Router | Endpoint prefix | Source module |
|--------|----------------|---------------|
| market | `/api/data` | `app/data.py` + `app/features.py` |
| strategy | `/api/strategy` | `app/strategy.py` |
| backtest | `/api/backtest` | `app/strategy.py` |
| watchlist | `/api/watchlist` | `app/strategy.py` |
| ml | `/api/ml` | `app/ml.py` |
| polymarket | `/api/polymarket/*` | `app/polymarket.py` |

Shared query parameter types are defined in `api/deps.py` as `Annotated` aliases (e.g. `TickerQ`, `RsiWindowQ`) and reused across routers.

## `app/` — Streamlit Modular App

Refactored version of `trading_simulator.py` split into focused modules. `app/main.py:main()` orchestrates the same pipeline as the monolith:

1. `ui.py` — `inject_styles()`, `initialize_state()`, `render_header()`, `sidebar_controls()` → `controls` dict
2. `data.py` — `get_data_cached()` → raw OHLCV DataFrame (Yahoo Finance + GBM fallback)
3. `features.py` — `build_feature_lab()` → 25+ indicators; `add_horizon_features()`, `prepare_modeling_frame()`
4. `strategy.py` — `apply_strategy()` → Signal column (1=buy, −1=sell, 0=hold); `run_backtest()`, `build_watchlist_pulse()`, `compute_stress_feed()`
5. `ml.py` — `walk_forward_random_forest()` — 250-tree RF, 5 seeds, 70/30 walk-forward split
6. `charts.py` — Plotly figure builders: `price_chart`, `backtest_chart`, `ml_chart`, `blended_equity_chart`, `correlation_chart`
7. `polymarket.py` — Polymarket Gamma API integration (cached 300s); renders prediction market tab

The five trading strategies (RSI, Trend, MACD, Breakout, Ensemble) and their signal logic live entirely in `app/strategy.py`.

## `frontend/` — Next.js App

Single-page dashboard at `frontend/app/page.tsx`. State management is plain React (`useState`/`useEffect`) — no external state library.

**Key files:**
- `lib/api.ts` — typed `api` object wrapping all fetch calls; reads `NEXT_PUBLIC_API_URL`
- `lib/types.ts` — TypeScript interfaces mirroring all API response shapes
- `lib/extractTicker.ts` — heuristic to extract a stock ticker from a Polymarket question string
- `components/tabs/` — `ChartsTab`, `BacktestTab`, `WatchlistTab`, `QuantLabTab`, `PredictionMarketsTab`
- `components/charts/` — Recharts-based chart components (`PriceChart`, `EquityChart`, `RSIMACDChart`, `PolymarketChart`)
- `components/ui/` — shadcn/ui primitives (badge, button, card, select, table, tabs)

**Data flow:** On load, the page fetches trending Polymarket markets. Selecting a market auto-extracts a ticker via `extractTicker()`, which triggers parallel fetches of `/api/data`, `/api/strategy`, and `/api/backtest`. The Quant Lab tab lazily triggers `/api/ml` only when first activated.

> **Note:** `frontend/AGENTS.md` warns that this Next.js version may have breaking API changes from standard training data. Check `node_modules/next/dist/docs/` before writing Next.js-specific code.
