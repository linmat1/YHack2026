import time

import numpy as np
import pandas as pd
import streamlit as st

from .charts import backtest_chart, blended_equity_chart, correlation_chart, ml_chart, price_chart
from .data import get_data_cached
from .features import add_horizon_features, build_feature_lab, prepare_modeling_frame
from .ml import walk_forward_random_forest
from .polymarket import render_polymarket_tab
from .strategy import (
    apply_strategy,
    build_watchlist_pulse,
    compute_stress_feed,
    run_backtest,
    summarize_signal,
    validate_inputs,
)
from .ui import inject_styles, initialize_state, metric_card, quick_ticker_buttons, render_header, sidebar_controls


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

    tabs = st.tabs(["Overview", "Charts", "Backtest", "Watchlist", "Quant Lab", "Prediction Markets", "Raw Data"])

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
                    st.plotly_chart(blended_equity_chart(blended), use_container_width=True)
            except Exception as exc:
                st.warning(f"ML layer could not be completed: {exc}")

    with tabs[5]:
        if controls["show_polymarket"]:
            render_polymarket_tab(controls["ticker"])
        else:
            st.info("Enable 'Show prediction markets' in the sidebar to load this section.")

    with tabs[6]:
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
