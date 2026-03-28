import numpy as np
import pandas as pd


def build_feature_lab(
    data: pd.DataFrame,
    rsi_window: int,
    fast_window: int,
    slow_window: int,
    trend_window: int,
    long_trend_window: int,
    vol_window: int,
) -> pd.DataFrame:
    df = data.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"] if "Volume" in df.columns else pd.Series(index=df.index, dtype=float)

    df["Return_1D"] = close.pct_change()
    df["Return_5D"] = close.pct_change(5)
    df["Return_20D"] = close.pct_change(20)
    df["LogReturn"] = np.log(close / close.shift(1))

    df["SMA_20"] = close.rolling(trend_window).mean()
    df["SMA_50"] = close.rolling(long_trend_window).mean()
    df["EMA_12"] = close.ewm(span=fast_window, adjust=False).mean()
    df["EMA_26"] = close.ewm(span=slow_window, adjust=False).mean()
    df["Momentum_20"] = close / close.shift(20) - 1

    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=rsi_window).mean()
    avg_loss = loss.rolling(window=rsi_window).mean().replace(0, 1e-10)
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    rolling_mean = close.rolling(trend_window).mean()
    rolling_std = close.rolling(trend_window).std()
    df["BB_Upper"] = rolling_mean + 2 * rolling_std
    df["BB_Lower"] = rolling_mean - 2 * rolling_std
    df["BB_Z"] = (close - rolling_mean) / rolling_std.replace(0, np.nan)
    df["BB_Width"] = (df["BB_Upper"] - df["BB_Lower"]) / rolling_mean.replace(0, np.nan)

    true_range = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["ATR_14"] = true_range.rolling(14).mean()
    df["RangePct"] = (high - low) / close.replace(0, np.nan)
    df["Volatility_20D"] = df["LogReturn"].rolling(vol_window).std() * np.sqrt(252)
    df["Drawdown"] = close / close.cummax() - 1
    df["Volume_Z"] = (volume - volume.rolling(20).mean()) / volume.rolling(20).std().replace(0, np.nan)

    df["RSI_Signal"] = np.select([df["RSI"] < 30, df["RSI"] > 70], [1, -1], default=0)
    df["Trend_Signal"] = np.select([close > df["SMA_20"], close < df["SMA_20"]], [1, -1], default=0)
    df["MACD_Signal_Flag"] = np.select([df["MACD_Hist"] > 0, df["MACD_Hist"] < 0], [1, -1], default=0)
    df["Breakout_Signal"] = np.select([close > df["BB_Upper"], close < df["BB_Lower"]], [1, -1], default=0)

    df["EnsembleScore"] = (
        0.35 * df["RSI_Signal"]
        + 0.35 * df["Trend_Signal"]
        + 0.20 * df["MACD_Signal_Flag"]
        + 0.10 * df["Breakout_Signal"]
    )
    df["EnsembleSignal"] = np.select(
        [df["EnsembleScore"] >= 0.25, df["EnsembleScore"] <= -0.25],
        [1, -1],
        default=0,
    )

    vol_anchor = df["Volatility_20D"].expanding().median()
    df["Regime"] = np.select(
        [
            (close > df["SMA_50"]) & (df["Volatility_20D"] <= vol_anchor),
            (close > df["SMA_50"]) & (df["Volatility_20D"] > vol_anchor),
            (close <= df["SMA_50"]) & (df["Volatility_20D"] > vol_anchor),
        ],
        ["Trend Up", "High-Vol Uptrend", "High-Vol Drawdown"],
        default="Range / Weak Trend",
    )
    return df


def add_horizon_features(feature_df: pd.DataFrame, horizons: tuple[int, ...] = (3, 5, 10, 20)) -> pd.DataFrame:
    df = feature_df.copy()
    for horizon in horizons:
        df[f"Return_{horizon}D"] = df["Close"].pct_change(horizon)
        df[f"RollingVol_{horizon}D"] = df["LogReturn"].rolling(horizon).std() * np.sqrt(252)
        df[f"Price_vs_SMA_{horizon}D"] = df["Close"] / df["Close"].rolling(horizon).mean() - 1
        df[f"HighLowRange_{horizon}D"] = (
            (df["High"].rolling(horizon).max() - df["Low"].rolling(horizon).min()) / df["Close"]
        ).replace([np.inf, -np.inf], np.nan)
        if "Volume" in df.columns:
            vol_roll = df["Volume"].rolling(horizon)
            df[f"VolumeShock_{horizon}D"] = (df["Volume"] - vol_roll.mean()) / vol_roll.std().replace(0, np.nan)

    df["RSI_x_Vol"] = df["RSI"] * df["Volatility_20D"]
    df["Momentum_x_Drawdown"] = df["Momentum_20"] * df["Drawdown"]
    df["MACD_x_BBWidth"] = df["MACD_Hist"] * df["BB_Width"]
    df["TrendGap_20_50"] = df["SMA_20"] / df["SMA_50"] - 1
    return df


def prepare_modeling_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    modeling = df.copy()
    modeling["TargetNextReturn"] = modeling["Close"].pct_change().shift(-1)
    candidate_cols = [
        "RSI",
        "MACD",
        "MACD_Hist",
        "BB_Z",
        "BB_Width",
        "ATR_14",
        "Volatility_20D",
        "Drawdown",
        "Momentum_20",
        "RangePct",
        "RSI_x_Vol",
        "Momentum_x_Drawdown",
        "MACD_x_BBWidth",
        "TrendGap_20_50",
    ]
    candidate_cols += [
        column
        for column in modeling.columns
        if column.startswith(("Return_", "RollingVol_", "Price_vs_SMA_", "HighLowRange_", "VolumeShock_"))
    ]
    candidate_cols = [column for column in candidate_cols if column in modeling.columns]
    modeling = modeling[candidate_cols + ["TargetNextReturn"]].replace([np.inf, -np.inf], np.nan).dropna()
    return modeling, candidate_cols
