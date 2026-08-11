import streamlit as st
import pandas as pd
from pathlib import Path

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="Social Science Journal Finder",
    page_icon="📚",
    layout="wide"
)

st.title("Social Science Journal Finder")
st.markdown("**For Master’s and Early PhD students** · Core Social Sciences + Education")

# -----------------------------
# Load Journal Corpus
# -----------------------------
@st.cache_data
def load_journal_corpus():
    path = Path("journal_rankings_final.csv")
    if not path.exists():
        st.error("`journal_rankings_final.csv` not found. Please upload it to the repository.")
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df

journal_db = load_journal_corpus()

# -----------------------------
# Sidebar Navigation
# -----------------------------
section = st.sidebar.radio(
    "Module",
    [
        "1. Abstract Diagnosis",
        "2. Improvement Pathways",
        "3. Journal Finder",
        "4. Supervisor Review"
    ]
)

# -----------------------------
# Status check
# -----------------------------
if not journal_db.empty:
    st.sidebar.success(f"Corpus loaded: **{len(journal_db)}** journals")
else:
    st.sidebar.error("Corpus not loaded")

# -----------------------------
# Placeholder modules
# -----------------------------
if section == "1. Abstract Diagnosis":
    st.header("1. Abstract Diagnosis")
    st.info("This module will accept a naive abstract and diagnose keyword problems.")
    st.write("Coming in next step...")

elif section == "2. Improvement Pathways":
    st.header("2. Improvement Pathways")
    st.info("Four pathways to improve keywords will appear here.")
    st.write("Coming soon...")

elif section == "3. Journal Finder":
    st.header("3. Journal Finder")
    st.info("Journal recommendations based on improved keywords.")
    
    if not journal_db.empty:
        st.subheader("Current Corpus Preview")
        st.dataframe(
            journal_db[["Journal", "Category", "Source", "Quality_Level", "ABDC_Rank"]].head(20),
            use_container_width=True,
            hide_index=True
        )
        st.caption(f"Showing 20 of {len(journal_db)} journals")

elif section == "4. Supervisor Review":
    st.header("4. Supervisor Review")
    st.info("Supervisor feedback module will appear here.")
    st.write("Coming soon...")

st.markdown("---")
st.caption("Social Science Journal Finder · Corpus: Scopus Top 10% + ABDC 2025 relevant journals")