# derby_model.py
import pandas as pd
import numpy as np


DEFAULT_WEIGHTS = {
    "speed_score": 0.25,
    "form_score": 0.20,
    "pace_score": 0.15,
    "stamina_score": 0.15,
    "post_score": 0.10,
    "trainer_jockey_score": 0.10,
    "odds_value_score": 0.05,
}


def american_odds_to_implied_prob(odds):
    """
    Converts American odds to implied probability.
    Examples:
    +500 -> 16.67%
    -150 -> 60.00%
    """
    try:
        odds = float(str(odds).replace("+", "").strip())

        if odds > 0:
            return 100 / (odds + 100)

        return abs(odds) / (abs(odds) + 100)

    except Exception:
        return np.nan


def normalize_series(series):
    """
    Converts values to a 0-100 scale.
    """
    series = pd.to_numeric(series, errors="coerce")

    min_val = series.min()
    max_val = series.max()

    if pd.isna(min_val) or pd.isna(max_val) or min_val == max_val:
        return pd.Series([50] * len(series), index=series.index)

    return ((series - min_val) / (max_val - min_val)) * 100


def calculate_derby_scores(df, weights=None):
    """
    Main scoring engine.

    Expected columns:
    horse
    odds
    speed_score
    form_score
    pace_score
    stamina_score
    post_score
    trainer_jockey_score
    """

    weights = weights or DEFAULT_WEIGHTS
    df = df.copy()

    required_cols = [
        "speed_score",
        "form_score",
        "pace_score",
        "stamina_score",
        "post_score",
        "trainer_jockey_score",
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = 50

        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(50)

    if "odds" in df.columns:
        df["implied_probability"] = df["odds"].apply(american_odds_to_implied_prob)
        df["implied_probability_pct"] = df["implied_probability"] * 100
    else:
        df["implied_probability"] = np.nan
        df["implied_probability_pct"] = np.nan

    # Lower implied probability means better payout.
    # This turns longer odds into a higher value score.
    if "implied_probability" in df.columns:
        df["odds_value_score"] = 100 - normalize_series(df["implied_probability"] * 100)
    else:
        df["odds_value_score"] = 50

    df["model_score"] = 0

    for col, weight in weights.items():
        if col not in df.columns:
            df[col] = 50

        df["model_score"] += df[col] * weight

    total_score = df["model_score"].sum()

    if total_score > 0:
        df["win_probability"] = df["model_score"] / total_score
    else:
        df["win_probability"] = 1 / len(df)

    df["win_probability_pct"] = df["win_probability"] * 100

    df["value_edge_pct"] = df["win_probability_pct"] - df["implied_probability_pct"]

    df["rank"] = df["model_score"].rank(
        ascending=False,
        method="first"
    ).astype(int)

    df = df.sort_values("model_score", ascending=False)

    return df


def classify_bet(row):
    """
    Simple betting-style label.
    """

    edge = row.get("value_edge_pct", 0)
    win_prob = row.get("win_probability_pct", 0)
    score = row.get("model_score", 0)

    if edge >= 5 and win_prob >= 8 and score >= 70:
        return "WIN VALUE"
    elif edge >= 3 and win_prob >= 6:
        return "EXACTA / WIN PLACE"
    elif edge >= 1 and win_prob >= 4:
        return "UNDERCARD VALUE"
    elif score >= 70:
        return "STRONG HORSE, BAD ODDS"
    else:
        return "PASS / WATCH"


def add_bet_labels(df):
    df = df.copy()
    df["bet_label"] = df.apply(classify_bet, axis=1)
    return df


def load_derby_csv(path="derby_horses.csv"):
    return pd.read_csv(path)


def save_ranked_derby_csv(df, path="derby_ranked_results.csv"):
    df.to_csv(path, index=False)


def run_derby_model(input_file="derby_horses.csv", output_file="derby_ranked_results.csv"):
    df = load_derby_csv(input_file)
    ranked = calculate_derby_scores(df)
    ranked = add_bet_labels(ranked)
    save_ranked_derby_csv(ranked, output_file)
    return ranked


if __name__ == "__main__":
    results = run_derby_model()
    print(results.to_string(index=False))