import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error


def walk_forward_random_forest(
    modeling_df: pd.DataFrame,
    feature_cols: list[str],
    train_ratio: float = 0.7,
    seeds: tuple[int, ...] = (7, 21, 42, 84, 126),
) -> tuple[pd.DataFrame, pd.DataFrame, float, pd.Series]:
    split_idx = max(int(len(modeling_df) * train_ratio), 50)
    train = modeling_df.iloc[:split_idx].copy()
    valid = modeling_df.iloc[split_idx:].copy()
    if valid.empty:
        raise ValueError("Validation split is empty. Expand the date range.")

    preds: list[np.ndarray] = []
    feature_importance_rows: list[pd.Series] = []
    for seed in seeds:
        model = RandomForestRegressor(
            n_estimators=250,
            max_depth=6,
            min_samples_leaf=5,
            random_state=seed,
            n_jobs=-1,
        )
        model.fit(train[feature_cols], train["TargetNextReturn"])
        preds.append(model.predict(valid[feature_cols]))
        feature_importance_rows.append(pd.Series(model.feature_importances_, index=feature_cols, name=f"seed_{seed}"))

    pred_matrix = np.vstack(preds)
    valid["PredictedNextReturn"] = pred_matrix.mean(axis=0)
    valid["PredictedSignal"] = np.select(
        [valid["PredictedNextReturn"] > 0.002, valid["PredictedNextReturn"] < -0.002],
        [1, -1],
        default=0,
    )
    valid["PredictionError"] = valid["TargetNextReturn"] - valid["PredictedNextReturn"]
    rmse = mean_squared_error(valid["TargetNextReturn"], valid["PredictedNextReturn"]) ** 0.5
    importance = pd.concat(feature_importance_rows, axis=1).mean(axis=1).sort_values(ascending=False)
    return train, valid, rmse, importance
