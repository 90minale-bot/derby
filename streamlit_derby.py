# streamlit_derby.py
import os
import pandas as pd
import plotly.express as px
import streamlit as st

from derby_model import calculate_derby_scores, add_bet_labels


DATA_FILE = "derby_horses.csv"


st.set_page_config(
    page_title="Derby Win Probability Model",
    page_icon="🏇",
    layout="wide"
)

st.title("🏇 Derby Win Probability + Value Model")


def create_sample_data():
    return pd.DataFrame([
        {
            "post": 1,
            "horse": "Example A",
            "odds": "+500",
            "trainer": "Trainer A",
            "jockey": "Jockey A",
            "speed_score": 85,
            "form_score": 82,
            "pace_score": 78,
            "stamina_score": 80,
            "post_score": 65,
            "trainer_jockey_score": 80,
        },
        {
            "post": 2,
            "horse": "Example B",
            "odds": "+1200",
            "trainer": "Trainer B",
            "jockey": "Jockey B",
            "speed_score": 76,
            "form_score": 78,
            "pace_score": 84,
            "stamina_score": 75,
            "post_score": 70,
            "trainer_jockey_score": 74,
        },
    ])


def load_data():
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        try:
            return pd.read_csv(DATA_FILE)
        except pd.errors.EmptyDataError:
            return create_sample_data()
        except Exception:
            return create_sample_data()

    return create_sample_data()


def save_data(df):
    df.to_csv(DATA_FILE, index=False)


def clean_input_df(df):
    df = df.copy()

    if "horse" not in df.columns:
        df["horse"] = "Unknown"

    if "odds" not in df.columns:
        df["odds"] = "+1000"

    if "post" not in df.columns:
        df["post"] = range(1, len(df) + 1)

    if "trainer" not in df.columns:
        df["trainer"] = ""

    if "jockey" not in df.columns:
        df["jockey"] = ""

    score_cols = [
        "speed_score",
        "form_score",
        "pace_score",
        "stamina_score",
        "post_score",
        "trainer_jockey_score",
    ]

    for col in score_cols:
        if col not in df.columns:
            df[col] = 50
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(50)

    df["post"] = pd.to_numeric(df["post"], errors="coerce").fillna(0).astype(int)

    return df


def rerank(df, sort_col="model_score"):
    df = df.copy()

    if sort_col in df.columns:
        df = df.sort_values(sort_col, ascending=False).reset_index(drop=True)

    df["rank"] = range(1, len(df) + 1)
    return df


def safe_weight_slider(label, default, remaining, key):
    remaining = round(max(remaining, 0.0), 2)

    if remaining <= 0:
        st.sidebar.metric(label, "0.00")
        return 0.0

    value = min(default, remaining)

    return st.sidebar.slider(
        label,
        min_value=0.0,
        max_value=remaining,
        value=value,
        step=0.01,
        key=key,
    )


# -----------------------------
# Sidebar weights
# -----------------------------
st.sidebar.header("Model Weights")
st.sidebar.caption("Weights are forced to add up to exactly 1.00.")

remaining = 1.0

speed_w = safe_weight_slider("Speed", 0.25, remaining, "speed_w")
remaining = round(remaining - speed_w, 2)

form_w = safe_weight_slider("Recent Form", 0.20, remaining, "form_w")
remaining = round(remaining - form_w, 2)

pace_w = safe_weight_slider("Pace Fit", 0.15, remaining, "pace_w")
remaining = round(remaining - pace_w, 2)

stamina_w = safe_weight_slider("Stamina / Distance", 0.15, remaining, "stamina_w")
remaining = round(remaining - stamina_w, 2)

post_w = safe_weight_slider("Post Position", 0.10, remaining, "post_w")
remaining = round(remaining - post_w, 2)

tj_w = safe_weight_slider("Trainer / Jockey", 0.10, remaining, "tj_w")
remaining = round(remaining - tj_w, 2)

odds_w = round(max(remaining, 0.0), 2)

st.sidebar.metric("Odds Value Weight", f"{odds_w:.2f}")

weights = {
    "speed_score": speed_w,
    "form_score": form_w,
    "pace_score": pace_w,
    "stamina_score": stamina_w,
    "post_score": post_w,
    "trainer_jockey_score": tj_w,
    "odds_value_score": odds_w,
}

total_weight = round(sum(weights.values()), 2)

if total_weight != 1.0:
    st.sidebar.warning(f"Total Weight = {total_weight:.2f}")
else:
    st.sidebar.success("Total Weight = 1.00")


with st.sidebar.expander("📘 Model Weight Definitions"):
    st.markdown("""
**Speed**  
Raw ability and race speed. Higher means the horse has stronger speed figures.

**Recent Form**  
How well the horse has performed recently.

**Pace Fit**  
How well the expected race shape matches the horse's running style.

**Stamina / Distance**  
Ability to handle the Derby distance.

**Post Position**  
How favorable the starting gate position is.

**Trainer / Jockey**  
Experience, quality, and confidence in the horse's connections.

**Odds Value**  
Automatically receives the remaining weight so the total always equals 1.00.
""")


# -----------------------------
# Load data and run model
# -----------------------------
df_input = clean_input_df(load_data())

try:
    ranked = calculate_derby_scores(df_input, weights=weights)
    ranked = add_bet_labels(ranked)
    ranked = rerank(ranked, "model_score")
except Exception as e:
    st.error(f"Model calculation failed: {e}")
    st.stop()


# -----------------------------
# TOP: Model Summary
# -----------------------------
st.subheader("📊 Model Summary")

if ranked.empty:
    st.warning("No horse data available.")
    st.stop()

top = ranked.iloc[0]
best_value = ranked.sort_values("value_edge_pct", ascending=False).iloc[0]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Top Horse", top.get("horse", "N/A"))

with col2:
    st.metric("Top Model Score", round(top.get("model_score", 0), 1))

with col3:
    st.metric("Top Win Probability", f"{top.get('win_probability_pct', 0):.1f}%")

with col4:
    st.metric("Best Value Horse", best_value.get("horse", "N/A"))

st.markdown("""
**How to read this:**  
The top horse is the model's highest-rated horse. The best value horse is where the model's win probability exceeds the market's implied odds probability the most.
""")


# -----------------------------
# Ranked Results
# -----------------------------
st.divider()
st.subheader("🏆 Ranked Derby Results")

sort_options = [
    "model_score",
    "win_probability_pct",
    "value_edge_pct",
    "speed_score",
    "form_score",
    "pace_score",
    "stamina_score",
    "post_score",
    "trainer_jockey_score",
    "odds_value_score",
]

sort_options = [c for c in sort_options if c in ranked.columns]

sort_choice = st.selectbox(
    "Sort results by",
    sort_options,
    index=0
)

ranked_display = rerank(ranked, sort_choice)

display_cols = [
    "rank",
    "post",
    "horse",
    "odds",
    "model_score",
    "win_probability_pct",
    "implied_probability_pct",
    "value_edge_pct",
    "bet_label",
    "speed_score",
    "form_score",
    "pace_score",
    "stamina_score",
    "post_score",
    "trainer_jockey_score",
    "odds_value_score",
    "trainer",
    "jockey",
]

existing_cols = [c for c in display_cols if c in ranked_display.columns]

st.dataframe(
    ranked_display[existing_cols],
    use_container_width=True,
    height=500
)


# -----------------------------
# Visuals
# -----------------------------
st.divider()
st.subheader("📈 Visuals")

chart_df = ranked_display.copy()

if not chart_df.empty and "horse" in chart_df.columns:
    fig_score = px.bar(
        chart_df.sort_values(sort_choice, ascending=True),
        x=sort_choice,
        y="horse",
        orientation="h",
        title=f"{sort_choice} by Horse",
        text=sort_choice,
    )

    st.plotly_chart(fig_score, use_container_width=True)

    if "value_edge_pct" in chart_df.columns:
        fig_value = px.bar(
            chart_df.sort_values("value_edge_pct", ascending=True),
            x="value_edge_pct",
            y="horse",
            orientation="h",
            title="Value Edge: Model Win Probability minus Implied Odds Probability",
            text="value_edge_pct",
        )

        st.plotly_chart(fig_value, use_container_width=True)


# -----------------------------
# Data Input
# -----------------------------
st.divider()
st.subheader("✏️ Horse Input Data")

st.markdown("""
Edit the horse data below. Scores should be on a **0–100 scale**.  
American odds can be entered like `+500`, `+1200`, or `-150`.
""")

edited_df = st.data_editor(
    df_input,
    use_container_width=True,
    num_rows="dynamic",
    height=400,
    key="horse_editor",
)

col_save, col_recalc, col_reset = st.columns(3)

with col_save:
    if st.button("💾 Save derby_horses.csv"):
        save_data(edited_df)
        st.success("Saved derby_horses.csv")
        st.rerun()

with col_recalc:
    if st.button("🔄 Recalculate"):
        st.rerun()

with col_reset:
    if st.button("🧹 Reset to sample data"):
        sample = create_sample_data()
        save_data(sample)
        st.rerun()


# -----------------------------
# Export
# -----------------------------
st.divider()
st.subheader("⬇️ Export Results")

csv = ranked_display.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Ranked Derby Results",
    data=csv,
    file_name="derby_ranked_results.csv",
    mime="text/csv",
)


with st.expander("How this model works"):
    st.markdown("""
### Core idea

The model creates a weighted score for each horse using:

- Speed
- Recent form
- Pace fit
- Stamina / distance fit
- Post position
- Trainer / jockey
- Odds value

### Weight total

The weights are forced to add up to exactly **1.00**.

The **Odds Value** weight automatically receives whatever weight remains after the other sliders.

### Win probability

The model converts each horse's score into a share of the total field score.

### Implied probability

American odds are converted into implied probability.

Example:

`+500` means an implied probability of about `16.7%`.

### Value edge

`value_edge_pct = model win probability - implied odds probability`

Positive value edge means your model likes the horse more than the betting market does.

### Bet labels

- **WIN VALUE** = strong model + good odds edge
- **EXACTA / WIN PLACE** = playable value
- **UNDERCARD VALUE** = smaller edge
- **STRONG HORSE, BAD ODDS** = good horse, but odds may be too short
- **PASS / WATCH** = not enough value
""")