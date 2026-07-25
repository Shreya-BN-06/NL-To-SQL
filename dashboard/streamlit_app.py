"""
NL-to-SQL Failure Audit — Streamlit Dashboard
================================================
Run with: streamlit run streamlit_app.py
Requires: pip install streamlit pandas
"""

import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="NL-to-SQL Trust Audit", layout="wide", page_icon="🔎")

# -------------------- CUSTOM STYLING --------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=IBM+Plex+Mono:wght@500&display=swap');

.stApp {
    background-color: #faf8f3;
    color: #1c232b;
}

h1 { font-family: 'Fraunces', serif !important; font-weight: 700 !important; color: #1c232b !important; }
h2, h3 { font-family: 'Fraunces', serif !important; font-weight: 600 !important; color: #1c232b !important; }

[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #ddd6c9;
    border-radius: 10px;
    padding: 16px 18px 10px 18px;
}
[data-testid="stMetricLabel"] {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #6b7178 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Fraunces', serif !important;
    color: #2f8f86 !important;
}

.stCaption, [data-testid="stCaptionContainer"] {
    font-size: 14.5px !important;
    color: #6b7178 !important;
}

hr { border-color: #ddd6c9 !important; }

[data-testid="stDataFrame"] { border: 1px solid #ddd6c9; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# -------------------- DATA --------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "..", "results", "final_combined_comparison.xlsx")
df = pd.read_excel(DATA_PATH)

tier_names = {
    1: "Unambiguous",
    2: "Metric-ambiguous",
    3: "Business-context",
    4: "Time-window",
    5: "Complex joins",
}
df["tier_name"] = df["tier"].map(tier_names)

baseline_match = df["baseline_status"] == "MATCH"
final_match = df["final_status"].isin(["MATCH", "FIXED"])

baseline_pct = round(baseline_match.mean() * 100, 1)
final_pct = round(final_match.mean() * 100, 1)

# -------------------- HEADER --------------------

st.markdown(
    "<div style='font-family:IBM Plex Mono, monospace; font-size:12.5px; letter-spacing:0.12em; "
    "text-transform:uppercase; color:#2f8f86; margin-bottom:6px;'>NL-to-SQL Failure Audit &middot; Northwind Dataset</div>",
    unsafe_allow_html=True,
)
st.title("Where natural language quietly gets your data wrong")
st.caption("20 business questions, run through an LLM-powered SQL pipeline — with and without a business-term glossary.")

col1, col2, col3 = st.columns(3)
col1.metric("📊 Baseline accuracy", f"{baseline_pct}%")
col2.metric("✅ With glossary", f"{final_pct}%", delta=f"+{round(final_pct - baseline_pct,1)} pts")
col3.metric("🛠️ Fully resolved failures", "8 / 9")

st.divider()

# -------------------- TIER BREAKDOWN --------------------

st.subheader("📈 Accuracy by question type")

tier_summary = df.groupby("tier_name").apply(
    lambda g: pd.Series({
        "Baseline %": round((g["baseline_status"] == "MATCH").mean() * 100, 1),
        "With Glossary %": round(g["final_status"].isin(["MATCH", "FIXED"]).mean() * 100, 1),
    })
).reindex(["Unambiguous", "Metric-ambiguous", "Business-context", "Time-window", "Complex joins"])

st.bar_chart(tier_summary)

st.divider()

# -------------------- FAILURE TAXONOMY --------------------

st.subheader("🔍 Failure taxonomy (baseline)")

taxonomy = df[df["error_category"] != ""]["error_category"].value_counts().reset_index()
taxonomy.columns = ["Error Category", "Count"]
st.dataframe(taxonomy, use_container_width=True, hide_index=True)

st.divider()

# -------------------- FULL COMPARISON TABLE --------------------

st.subheader("📋 Full question-by-question comparison")

status_filter = st.multiselect(
    "Filter by final status",
    options=df["final_status"].unique().tolist(),
    default=df["final_status"].unique().tolist(),
)

filtered = df[df["final_status"].isin(status_filter)]

display_cols = ["master_question_id", "tier_name", "question", "baseline_result",
                 "baseline_status", "glossary_result", "final_status", "error_category"]

def style_status(val):
    colors = {
        "MATCH": "background-color: rgba(47,143,134,0.15); color: #1f6b64; font-weight: 600;",
        "FIXED": "background-color: rgba(47,143,134,0.15); color: #1f6b64; font-weight: 600;",
        "MISMATCH": "background-color: rgba(163,74,80,0.15); color: #8f3a3f; font-weight: 600;",
        "IMPROVED (defensible variant)": "background-color: rgba(185,122,46,0.15); color: #8a5a1f; font-weight: 600;",
    }
    return colors.get(val, "")

styled = filtered[display_cols].style.map(style_status, subset=["baseline_status", "final_status"])

st.dataframe(styled, use_container_width=True, hide_index=True)

st.divider()

# -------------------- METHODOLOGY NOTE --------------------

st.subheader("⚖️ On the 95%, not 100%")
st.write(
    "8 of 9 previously-failing questions produced exact matches once given a glossary. "
    "The 9th (shipping route efficiency) produced a methodologically valid but differently-scoped "
    "answer — not a wrong one. This is reported as an improved variant, not rounded up to a clean match, "
    "since overstating precision would repeat the exact failure mode this project investigates."
)
