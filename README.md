[STRATEGY_DOCUMENTATION.md](https://github.com/user-attachments/files/26327574/STRATEGY_DOCUMENTATION.md)
# Yhack Strategy Documentation

## Overview

This project is an asset-first crypto trading research system that uses Polymarket as an information layer rather than as the traded instrument itself.

The core idea is:

- trade liquid crypto assets such as `BTC`, `ETH`, and `SOL`
- generate the base trade from market data
- use Polymarket to confirm, reduce, or veto that trade
- compare a plain technical strategy against a Polymarket-enhanced variant
- expose the results through both notebooks and a Streamlit dashboard

This repo currently contains two main user-facing artifacts:

- [yhack_prediction_market_dashboard_lab_iter_2.ipynb](/Users/sabyasachi/Library/CloudStorage/OneDrive-rbionline/golden jubilee application/mission 2025/final college selection/housing/ds_project/rentwise-project/Yhack/yhack_prediction_market_dashboard_lab_iter_2.ipynb)
- [yhack_strategy_studio_iter_2.py](/Users/sabyasachi/Library/CloudStorage/OneDrive-rbionline/golden jubilee application/mission 2025/final college selection/housing/ds_project/rentwise-project/Yhack/yhack_strategy_studio_iter_2.py)

The notebook is the research and export environment. The Streamlit app is the presentation and exploration layer.

## Problem Statement

The strategy does not directly buy or sell prediction contracts. Instead, it asks:

- can live and historical Polymarket context improve crypto trade selection?
- can Polymarket reduce false-positive entries?
- can Polymarket improve position sizing?
- can Polymarket identify high-risk or avoid zones before entry?

The system treats Polymarket as:

- a confidence layer
- a caution layer
- a position-sizing layer
- a hedge and scenario-analysis layer

## Project Structure

### Key files

- [yhack_prediction_market_dashboard_lab.ipynb](/Users/sabyasachi/Library/CloudStorage/OneDrive-rbionline/golden jubilee application/mission 2025/final college selection/housing/ds_project/rentwise-project/Yhack/yhack_prediction_market_dashboard_lab.ipynb)
- [yhack_prediction_market_dashboard_lab_iter_2.ipynb](/Users/sabyasachi/Library/CloudStorage/OneDrive-rbionline/golden jubilee application/mission 2025/final college selection/housing/ds_project/rentwise-project/Yhack/yhack_prediction_market_dashboard_lab_iter_2.ipynb)
- [yhack_strategy_studio_iter_2.py](/Users/sabyasachi/Library/CloudStorage/OneDrive-rbionline/golden jubilee application/mission 2025/final college selection/housing/ds_project/rentwise-project/Yhack/yhack_strategy_studio_iter_2.py)
- [polymarket_config.py](/Users/sabyasachi/Library/CloudStorage/OneDrive-rbionline/golden jubilee application/mission 2025/final college selection/housing/ds_project/rentwise-project/Yhack/polymarket_config.py)
- [data](/Users/sabyasachi/Library/CloudStorage/OneDrive-rbionline/golden jubilee application/mission 2025/final college selection/housing/ds_project/rentwise-project/Yhack/data)

### Supporting files

- local secret storage via `Yhack/.env`
- `.gitignore` excludes local secrets
- `.env.example` shows the expected config keys

## Data Sources

### Underlying market data

Live crypto candles come from Kraken.

Supported assets in the current dashboard:

- `BTC-USD`
- `ETH-USD`
- `SOL-USD`

Kraken is used instead of Yahoo to avoid the repeated upstream failures that were affecting crypto ticker lookup and startup time.

### Polymarket data

Polymarket is used through:

- Gamma API for market discovery
- CLOB API for live order-book state
- CLOB `prices-history` for historical token prices

Relevant config loading is handled by [polymarket_config.py](/Users/sabyasachi/Library/CloudStorage/OneDrive-rbionline/golden jubilee application/mission 2025/final college selection/housing/ds_project/rentwise-project/Yhack/polymarket_config.py).

The project supports safe local loading of:

- `POLYMARKET_GAMMA_HOST`
- `POLYMARKET_CLOB_HOST`
- `POLYMARKET_DATA_HOST`
- `POLYMARKET_API_KEY`
- `POLYMARKET_SECRET`
- `POLYMARKET_PASSPHRASE`

The current research flow is public-data-first. A private key is not required for the analytics workflow.

## Strategy Logic

## 1. Base Market Strategy

The trading engine is intentionally simple and mirrors the older crypto strategy notebook.

### Base signal

The control strategy is long-only and uses a rolling-mean rule:

- buy when `Close > rolling_mean`
- sell or exit when `Close < rolling_mean`

This is then tested in two forms:

- `Without PM`
- `With PM`

### Risk-managed execution model

The simulator uses a fixed starting capital and risk-based sizing.

Default strategy parameters copied from the earlier notebook:

- `initial_cash = 10,000`
- `risk_per_trade = 0.011630049699125568`
- `max_position = 0.07691911910746403`
- `stop_loss_pct = 0.00318888532686275`
- `target_pct = 0.009930545954923087`
- `slippage_pct = 0.0005`
- `fee_pct = 0.001`

### Position sizing formula

The position size is based on stop distance:

`risk_amount = cash * risk_per_trade`

`stop_distance = entry_price * stop_loss_pct`

`units = risk_amount / stop_distance`

The raw size is then capped by maximum allowed portfolio exposure:

`max_position_value = max_position * equity`

### Exit logic

The strategy checks exits in this order:

- stop-loss
- take-profit
- signal exit
- PM defensive exit for the PM-enhanced strategy

Round-trip trades are generated by compressing one or more `BUY` fills into the next full `SELL`.

## 2. Polymarket Integration

Polymarket does not generate the base trade. It modifies the trade decision quality.

### Market discovery

For each asset, the project:

- queries Gamma for active markets
- filters to relevant questions
- extracts token IDs
- fetches live best bid, best ask, midpoint, spread, volume, liquidity, and days to resolution

### Question tagging

Each market is tagged using rule-based keyword logic:

- bullish
- bearish
- ambiguous

Each market is also assigned a theme:

- price
- regulation
- macro
- adoption
- risk

The tagging system is transparent and inspectable. It is not LLM-based.

### Historical alignment

For selected markets, the notebook fetches historical CLOB token prices using `prices-history`.

Those token histories are:

- aligned to the underlying asset frequency
- resampled
- aggregated into hourly or daily asset-level Polymarket features

### Polymarket-derived features

Examples of features used:

- `pm_hist_mean_price`
- `pm_hist_net_sentiment`
- `pm_hist_liq_weighted_sentiment`
- `pm_hist_avg_spread`
- `pm_hist_dispersion`
- `pm_hist_total_liquidity`
- `pm_hist_total_volume`
- `pm_hist_price_momentum`
- `pm_hist_price_volatility`

These are combined with technical features to determine whether PM is:

- confirming the trade
- reducing size
- flagging elevated risk

## 3. Fusion Layer

The fusion layer combines technical state and PM state.

### Technical side

The feature lab computes:

- returns
- moving averages
- RSI
- MACD
- Bollinger statistics
- ATR
- volatility
- drawdown
- volume-normalized measures

These are collapsed into:

- `TechnicalScore`
- `TechnicalConfidence`

### PM side

The Polymarket aggregate contributes:

- confirmation score
- conflict penalty
- quality score
- event urgency
- spread stress

### Caution score

The system computes a composite caution score from:

- volatility spike
- drawdown pressure
- spread stress
- PM whipsaw or disagreement
- event risk
- price vs PM divergence

This drives a risk-zone label:

- `Tradeable`
- `Cautious`
- `High Risk`
- `Avoid`

### Final trade decision

The PM-enhanced strategy uses:

- `FinalAction`
- `FinalConfidence`
- `PositionSize`

The PM variant can:

- allow a trade at full size
- reduce the position
- block a trade entirely
- trigger a defensive early exit

## Notebook Architecture

The research notebook is organized as a pipeline.

### Core research sections

1. problem framing
2. config and inputs
3. underlying market data
4. Polymarket live pull
5. question tagging
6. Polymarket historical alignment and aggregation
7. signal fusion
8. decision dashboard
9. scenario analysis
10. baseline backtest comparison
11. old-style 10K trade simulator
12. iter-2 payoff explorer
13. iter-2 hedge and timing analysis
14. iter-2 portfolio and educational diagnostics
15. final CSV export cell

### Iteration 2 extensions

The iteration-2 notebook expands the project toward the original Yhack five-tab framing.

It adds:

- probability/horizon payoff explorer
- hedge lab
- earlier-vs-later resolution scenarios
- multi-asset portfolio aggregation
- educational contribution diagnostics

## Streamlit Dashboard Structure

The Streamlit app is a user-friendly front end for the same core research idea.

### Current tabs

- `Overview`
- `Trade Engine`
- `Market Board`
- `Payoff Studio`
- `Timing + Portfolio`
- `Education`

### Main user controls

- asset
- date range
- interval
- live vs synthetic data source
- Polymarket search override
- PM market count
- confidence thresholds
- caution threshold
- PM defensive exit threshold
- capital
- rolling window
- stop-loss
- target
- slippage
- fee
- hedge ratios
- portfolio weights

## Results and Output Tables

## 1. Trade simulation outputs

For both `Without PM` and `With PM`, the simulator produces:

- raw fill ledger
- round-trip P&L table
- equity curve
- summary metrics

### Round-trip output schema

Each round-trip row includes:

- `entry_time`
- `exit_time`
- `qty`
- `buy_cost_incl_fees`
- `sell_proceeds_after_fee`
- `realized_pnl`
- `exit_reason`
- `cum_equity`
- `cum_return_pct`

### Summary output schema

The strategy summary includes:

- strategy name
- final equity
- total return
- max drawdown
- number of round trips
- win rate
- stop exits
- target exits
- signal exits
- PM exits
- skipped PM entries

## 2. Market and PM outputs

The research outputs also include:

- raw market data
- technical feature table
- live Polymarket board
- tagged Polymarket board
- PM snapshot aggregate
- PM historical panel
- fused technical + PM table

## 3. Iteration-2 analytical outputs

The iteration-2 notebook produces:

- asset summary table across `BTC`, `ETH`, and `SOL`
- probability payoff grid
- hedge profile table
- resolution window table
- portfolio equity tables
- portfolio summary table
- educational contribution table

## Exported CSV Files

The final notebook cell exports CSVs to [data](/Users/sabyasachi/Library/CloudStorage/OneDrive-rbionline/golden jubilee application/mission 2025/final college selection/housing/ds_project/rentwise-project/Yhack/data).

Examples include:

- `market_data.csv`
- `feature_data.csv`
- `polymarket_board.csv`
- `tagged_polymarket.csv`
- `pm_historical_panel.csv`
- `fused_data.csv`
- `without_pm_roundtrip.csv`
- `with_pm_roundtrip.csv`
- `iter2_asset_summary.csv`
- `iter2_probability_payoff.csv`
- `iter2_hedge_profiles.csv`
- `iter2_resolution_table.csv`
- `iter2_portfolio_without_pm.csv`
- `iter2_portfolio_with_pm.csv`
- `iter2_portfolio_summary.csv`
- `iter2_education.csv`

Per-asset exports are also written for:

- `iter2_btc_*`
- `iter2_eth_*`
- `iter2_sol_*`

## How to Reproduce

## Notebook workflow

1. Open [yhack_prediction_market_dashboard_lab_iter_2.ipynb](/Users/sabyasachi/Library/CloudStorage/OneDrive-rbionline/golden jubilee application/mission 2025/final college selection/housing/ds_project/rentwise-project/Yhack/yhack_prediction_market_dashboard_lab_iter_2.ipynb).
2. Run the notebook from top to bottom.
3. Run the last export cell.
4. Inspect the generated CSVs in [data](/Users/sabyasachi/Library/CloudStorage/OneDrive-rbionline/golden jubilee application/mission 2025/final college selection/housing/ds_project/rentwise-project/Yhack/data).

## Streamlit workflow

From the repo root:

```bash
conda activate genAiEnv
python -m streamlit run Yhack/yhack_strategy_studio_iter_2.py --server.address 127.0.0.1 --server.port 8502
```

Important:

- do not mix the broken local `.venv` and the conda env
- use Kraken for crypto live data
- use the project `.env` for local Polymarket config

## Interpretation Guide

### What `Without PM` means

This is the control strategy:

- long-only
- rolling-mean entry/exit
- same risk model
- no PM filtering

### What `With PM` means

This is the PM-enhanced strategy:

- same core trade engine
- same capital and execution assumptions
- PM confirms or discounts entries
- PM changes position size
- PM can force defensive exit

### How to read improvements

The PM layer is valuable if it:

- improves final equity
- lowers drawdown
- reduces bad entries
- cuts size during poor regimes
- improves win rate without destroying exposure

## Known Limitations

- question tagging is keyword-based, not semantic
- public PM analytics do not capture every possible historical market attribute
- some PM features are stronger for high-coverage assets like BTC than for smaller assets
- hedge lab and payoff studio are research visualizations, not execution-grade derivatives pricing
- results depend on API availability, current live market coverage, and notebook runtime settings

## Recommended Next Improvements

- replace keyword tagging with stronger semantic relevance logic
- add historical spread and liquidity reconstruction where available
- improve per-market selection for PM aggregation
- test additional assets and alternative technical entry models
- add portfolio constraints and risk budgeting
- expose CSV export from the Streamlit app as well

## Repo Positioning

The strongest way to present this project is:

`A crypto trading research system that uses prediction-market intelligence to improve entry quality, position sizing, risk control, and scenario understanding.`

That framing is materially stronger than presenting it as a pure Polymarket dashboard or a pure technical trading notebook.
