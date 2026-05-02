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

st.markdown("""
Upload or edit your Derby horse data, adjust the model weights, then rank the field by
model score, estimated win probability, implied odds probability, and value edge.
""")


def create_sample_data():
    return pd.DataFrame([
        {
            "post": 1,
            "horse": "Example Horse A",
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
            "horse": "Example Horse B",
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
        {
            "post": 3,
            "horse": "Example Horse C",
            "odds": "+2500",
            "trainer": "Trainer C",
            "jockey": "Jockey C",
            "speed_score": 70,
            "form_score": 72,
            "pace_score": 80,
            "stamina_score": 68,
            "post_score": 75,
            "trainer_jockey_score": 70,
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


# -----------------------------
# Sidebar data
# -----------------------------
st.sidebar.header("Data")

uploaded_file = st.sidebar.file_uploader(
    "Upload derby_horses.csv",
    type=["csv"]
)

if uploaded_file is not None:
    try:
        df_input = pd.read_csv(uploaded_file)
        st.sidebar.success("Uploaded CSV loaded.")
    except pd.errors.EmptyDataError:
        st.sidebar.error("Uploaded CSV was empty. Using sample data instead.")
        df_input = create_sample_data()
    except Exception as e:
        st.sidebar.error(f"Could not read uploaded CSV: {e}")
        df_input = create_sample_data()
else:
    df_input = load_data()


# -----------------------------
# Sidebar model weights
# -----------------------------
st.sidebar.markdown("---")
st.sidebar.header("Model Weights")

speed_w = st.sidebar.slider("Speed", 0.0, 1.0, 0.25, 0.05)
form_w = st.sidebar.slider("Recent Form", 0.0, 1.0, 0.20, 0.05)
pace_w = st.sidebar.slider("Pace Fit", 0.0, 1.0, 0.15, 0.05)
stamina_w = st.sidebar.slider("Stamina / Distance", 0.0, 1.0, 0.15, 0.05)
post_w = st.sidebar.slider("Post Position", 0.0, 1.0, 0.10, 0.05)
tj_w = st.sidebar.slider("Trainer / Jockey", 0.0, 1.0, 0.10, 0.05)
odds_w = st.sidebar.slider("Odds Value", 0.0, 1.0, 0.05, 0.05)

raw_weights = {
    "speed_score": speed_w,
    "form_score": form_w,
    "pace_score": pace_w,
    "stamina_score": stamina_w,
    "post_score": post_w,
    "trainer_jockey_score": tj_w,
    "odds_value_score": odds_w,
}

weight_total = sum(raw_weights.values())

if weight_total == 0:
    st.sidebar.error("At least one model weight must be greater than 0.")
    st.stop()

weights = {k: v / weight_total for k, v in raw_weights.items()}

st.sidebar.caption(f"Normalized total weight: {sum(weights.values()):.2f}")


# -----------------------------
# Input data editor
# -----------------------------
st.subheader("1️⃣ Horse Input Data")

st.markdown("""
Edit the table below. Scores should be on a **0–100 scale**.  
American odds can be entered like `+500`, `+1200`, or `-150`.
""")

df_input = clean_input_df(df_input)

edited_df = st.data_editor(
    df_input,
    use_container_width=True,
    num_rows="dynamic",
    height=350,
    key="horse_editor"
)

col_save, col_reload, col_reset = st.columns([1, 1, 1])

with col_save:
    if st.button("💾 Save derby_horses.csv"):
        save_data(edited_df)
        st.success("Saved derby_horses.csv")

with col_reload:
    if st.button("🔄 Recalculate"):
        st.rerun()

with col_reset:
    if st.button("🧹 Reset to sample data"):
        sample = create_sample_data()
        save_data(sample)
        st.rerun()


# -----------------------------
# Run model every rerun
# -----------------------------
ranked = calculate_derby_scores(edited_df, weights=weights)
ranked = add_bet_labels(ranked)
ranked = rerank(ranked, "model_score")


# -----------------------------
# Metrics
# -----------------------------
st.divider()
st.subheader("2️⃣ Model Summary")

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


# -----------------------------
# Results table
# -----------------------------
st.divider()
st.subheader("3️⃣ Ranked Derby Results")

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
    height=550
)


# -----------------------------
# Charts
# -----------------------------
st.divider()
st.subheader("4️⃣ Visuals")

chart_df = ranked_display.copy()

if "horse" in chart_df.columns:
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
# Export
# -----------------------------
st.divider()
st.subheader("5️⃣ Export Results")

csv = ranked_display.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download Ranked Derby Results",
    data=csv,
    file_name="derby_ranked_results.csv",
    mime="text/csv"
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

### Weight sliders

When you move the weight sliders, the model recalculates automatically.

The app normalizes the weights so they always add up to 1.00.

### Win Probability

The model converts each horse's score into a share of the total field score.

### Implied Probability

American odds are converted into implied probability.

Example:

`+500` means an implied probability of about `16.7%`.

### Value Edge

`value_edge_pct = model win probability - implied odds probability`

Positive value edge means your model likes the horse more than the betting market does.

### Bet Labels

- **WIN VALUE** = strong model + good odds edge
- **EXACTA / WIN PLACE** = playable value
- **UNDERCARD VALUE** = smaller edge
- **STRONG HORSE, BAD ODDS** = good horse, but odds may be too short
- **PASS / WATCH** = not enough value
""")