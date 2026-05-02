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


# -----------------------------
# Sample + Load
# -----------------------------
def create_sample_data():
    return pd.DataFrame([
        {"post": 1, "horse": "Example A", "odds": "+500", "trainer": "A", "jockey": "A",
         "speed_score": 85, "form_score": 82, "pace_score": 78, "stamina_score": 80,
         "post_score": 65, "trainer_jockey_score": 80},
        {"post": 2, "horse": "Example B", "odds": "+1200", "trainer": "B", "jockey": "B",
         "speed_score": 76, "form_score": 78, "pace_score": 84, "stamina_score": 75,
         "post_score": 70, "trainer_jockey_score": 74},
    ])


def load_data():
    if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 0:
        try:
            return pd.read_csv(DATA_FILE)
        except:
            return create_sample_data()
    return create_sample_data()


def save_data(df):
    df.to_csv(DATA_FILE, index=False)


def clean(df):
    df = df.copy()

    cols = ["speed_score","form_score","pace_score","stamina_score","post_score","trainer_jockey_score"]
    for c in cols:
        if c not in df:
            df[c] = 50
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(50)

    if "post" not in df:
        df["post"] = range(1, len(df)+1)

    return df


# -----------------------------
# Sidebar weights
# -----------------------------
st.sidebar.header("Model Weights")

speed = st.sidebar.slider("Speed",0.0,1.0,0.25,0.05)
form = st.sidebar.slider("Recent Form",0.0,1.0,0.20,0.05)
pace = st.sidebar.slider("Pace Fit",0.0,1.0,0.15,0.05)
stamina = st.sidebar.slider("Stamina",0.0,1.0,0.15,0.05)
post = st.sidebar.slider("Post Position",0.0,1.0,0.10,0.05)
tj = st.sidebar.slider("Trainer/Jockey",0.0,1.0,0.10,0.05)
odds = st.sidebar.slider("Odds Value",0.0,1.0,0.05,0.05)

raw = {
    "speed_score": speed,
    "form_score": form,
    "pace_score": pace,
    "stamina_score": stamina,
    "post_score": post,
    "trainer_jockey_score": tj,
    "odds_value_score": odds
}

total = sum(raw.values())
weights = {k:v/total for k,v in raw.items()}


# -----------------------------
# Weight definitions
# -----------------------------
with st.sidebar.expander("📘 What these mean"):
    st.markdown("""
**Speed**  
Raw ability — fastest horses win more often.

**Recent Form**  
How the horse has performed lately.

**Pace Fit**  
Does race shape match this horse's style?

**Stamina**  
Can it handle the Derby distance (1¼ miles)?

**Post Position**  
Inside = risk, outside = distance. Middle often best.

**Trainer/Jockey**  
Experience matters in big races.

**Odds Value**  
Rewards longer odds vs favorites.
""")


# -----------------------------
# Load + run model
# -----------------------------
df = clean(load_data())

ranked = calculate_derby_scores(df, weights)
ranked = add_bet_labels(ranked)
ranked = ranked.sort_values("model_score", ascending=False).reset_index(drop=True)
ranked["rank"] = range(1, len(ranked)+1)


# -----------------------------
# TOP: SUMMARY
# -----------------------------
st.subheader("📊 Model Summary")

top = ranked.iloc[0]
best_val = ranked.sort_values("value_edge_pct", ascending=False).iloc[0]

c1,c2,c3,c4 = st.columns(4)

c1.metric("Top Horse", top["horse"])
c2.metric("Top Score", round(top["model_score"],1))
c3.metric("Win %", f"{top['win_probability_pct']:.1f}%")
c4.metric("Best Value", best_val["horse"])


# -----------------------------
# MIDDLE: RESULTS
# -----------------------------
st.subheader("🏆 Ranked Results")

st.dataframe(
    ranked[[
        "rank","post","horse","odds",
        "model_score","win_probability_pct",
        "value_edge_pct","bet_label"
    ]],
    use_container_width=True,
    height=400
)


# -----------------------------
# Charts
# -----------------------------
fig = px.bar(
    ranked.sort_values("model_score"),
    x="model_score",
    y="horse",
    orientation="h",
    title="Model Score"
)

st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# BOTTOM: DATA INPUT
# -----------------------------
st.subheader("✏️ Edit Horse Data")

edited = st.data_editor(df, num_rows="dynamic", use_container_width=True)

col1,col2 = st.columns(2)

with col1:
    if st.button("💾 Save"):
        save_data(edited)
        st.success("Saved")
        st.rerun()

with col2:
    if st.button("🔄 Recalculate"):
        st.rerun()


# -----------------------------
# Help
# -----------------------------
with st.expander("How to use this model"):
    st.markdown("""
- Adjust weights → model updates instantly  
- Focus on:
  - Top Score → best horse
  - Value Edge → best bet  
- Ideal play:
  - High score + positive value edge
""")