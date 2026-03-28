from fastapi import APIRouter, HTTPException

from app.data import get_data_cached
from app.features import add_horizon_features, build_feature_lab, prepare_modeling_frame
from app.ml import walk_forward_random_forest
from app.strategy import apply_strategy, run_backtest
import numpy as np
from ..deps import (
    DataModeQ, EndQ, FastWindowQ, FeeBpsQ, IntervalQ, LongTrendWindowQ,
    RsiWindowQ, SlowWindowQ, StartQ, StrategyQ, TickerQ, TrendWindowQ, VolWindowQ,
)

router = APIRouter(tags=["ml"])


@router.get("/ml")
def get_ml(
    ticker: TickerQ,
    start: StartQ,
    end: EndQ,
    interval: IntervalQ = "1d",
    data_mode: DataModeQ = "Auto",
    strategy: StrategyQ = "Ensemble",
    rsi_window: RsiWindowQ = 14,
    fast_window: FastWindowQ = 12,
    slow_window: SlowWindowQ = 26,
    trend_window: TrendWindowQ = 20,
    long_trend_window: LongTrendWindowQ = 50,
    vol_window: VolWindowQ = 20,
    fee_bps: FeeBpsQ = 5,
) -> dict:
    ticker = ticker.strip().upper()
    data, _ = get_data_cached(ticker, start, end, interval, data_mode)
    if data.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    features = build_feature_lab(data, rsi_window, fast_window, slow_window, trend_window, long_trend_window, vol_window)
    strategy_data, signal_col = apply_strategy(features, strategy)
    backtest = run_backtest(strategy_data, signal_col, fee_bps)
    enriched = add_horizon_features(strategy_data)

    modeling_df, feature_cols = prepare_modeling_frame(enriched)
    if len(modeling_df) < 100:
        raise HTTPException(status_code=422, detail="Not enough data for ML. Extend the date range.")

    _, wf_valid, rmse, importance = walk_forward_random_forest(modeling_df, feature_cols)

    # Build blended equity
    blended = backtest.join(wf_valid[["PredictedNextReturn", "PredictedSignal"]], how="left")
    blended["PredictedSignal"] = blended["PredictedSignal"].fillna(0)
    signal_mix = 0.65 * blended["SignalPosition"].fillna(0) + 0.35 * blended["PredictedSignal"]
    blended["BlendedSignal"] = np.select([signal_mix >= 0.25, signal_mix <= -0.25], [1, -1], default=0)
    blended["BlendedPosition"] = blended["BlendedSignal"].shift(1).fillna(0)
    blended["BlendedTurnover"] = blended["BlendedPosition"].diff().abs().fillna(blended["BlendedPosition"].abs())
    blended["BlendedReturn"] = blended["BlendedPosition"] * blended["Return_1D"].fillna(0) - blended["BlendedTurnover"] * 0.0005
    blended["BlendedEquity"] = (1 + blended["BlendedReturn"]).cumprod()

    # Serialize predictions
    pred_df = wf_valid[["TargetNextReturn", "PredictedNextReturn"]].reset_index()
    pred_df["Date"] = pred_df["Date"].astype(str)
    predictions = pred_df.to_dict(orient="records")

    # Serialize blended equity
    blend_df = blended[["StrategyEquity", "BlendedEquity"]].reset_index()
    blend_df["Date"] = blend_df["Date"].astype(str)
    blended_curve = blend_df.to_dict(orient="records")

    return {
        "rmse": float(rmse),
        "predictions": predictions,
        "feature_importance": [
            {"feature": k, "importance": float(v)}
            for k, v in importance.head(12).items()
        ],
        "blended_equity": blended_curve,
    }
