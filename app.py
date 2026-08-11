import streamlit as st
import pandas as pd
from pathlib import Path
from collections import Counter
import re
from urllib.parse import quote_plus

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
        st.error("`journal_rankings_final.csv` not found. Please place it in the repository root.")
        return pd.DataFrame()
    return pd.read_csv(path)

journal_db = load_journal_corpus()

# -----------------------------
# Sidebar
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

if not journal_db.empty:
    st.sidebar.success(f"Corpus loaded: **{len(journal_db)}** journals")
else:
    st.sidebar.error("Corpus not loaded")

# =========================================================
# Constants & Helpers
# =========================================================

DISCIPLINES = [
    "None / Prefer not to specify",
    "Sociology",
    "Political Science & International Relations",
    "Development Studies",
    "Anthropology",
    "Gender Studies",
    "Public Administration / Public Policy",
    "Education",
    "Communication",
    "Human Geography / Urban Studies",
    "Demography",
    "Social Policy",
    "Interdisciplinary / Other Social Science"
]

DISCIPLINE_MAP = {
    "None / Prefer not to specify": [],
    "Sociology": ["sociology", "political science"],
    "Political Science & International Relations": ["political science", "international relations"],
    "Development Studies": ["development"],
    "Anthropology": ["anthropology"],
    "Gender Studies": ["gender"],
    "Public Administration / Public Policy": ["public administration", "public policy", "policy"],
    "Education": ["education"],
    "Communication": ["communication"],
    "Human Geography / Urban Studies": ["geography", "urban", "planning"],
    "Demography": ["demography"],
    "Social Policy": ["social policy", "policy"],
    "Interdisciplinary / Other Social Science": []
}

VAGUE_TERMS = {
    "society", "social", "issues", "important", "various", "different",
    "things", "aspects", "factors", "areas", "system", "systems",
    "process", "processes", "problem", "problems", "situation",
    "context", "framework", "approach", "approaches", "study", "studies",
    "research", "analysis", "data", "information", "knowledge", "role",
    "impact", "effect", "effects", "relationship", "relationships"
}

METHOD_SIGNALS = {
    "qualitative", "quantitative", "ethnography", "ethnographic", "interview",
    "interviews", "survey", "surveys", "case study", "mixed methods",
    "content analysis", "discourse", "regression", "experiment", "experimental",
    "longitudinal", "cross-sectional", "focus group", "participant observation"
}

POPULATION_SIGNALS = {
    "youth", "young people", "women", "men", "students", "workers",
    "migrants", "immigrants", "refugees", "teachers", "children",
    "adolescents", "elderly", "citizens", "voters", "farmers",
    "employees", "parents", "households", "communities"
}

def extract_candidate_terms(text):
    text = text.lower()
    tokens = re.findall(r"[a-z][a-z\-]+(?:\s+[a-z][a-z\-]+){0,3}", text)
    candidates = []
    for t in tokens:
        t = t.strip()
        if len(t) < 4:
            continue
        if t in {"this study", "the study", "this paper", "the paper", "this article", "the article"}:
            continue
        candidates.append(t)
    counts = Counter(candidates)
    return [w for w, c in counts.most_common(25)]

def diagnose_abstract(abstract):
    abstract_lower = abstract.lower()
    candidates = extract_candidate_terms(abstract)

    vague_found = [t for t in candidates if t in VAGUE_TERMS or any(v in t.split() for v in VAGUE_TERMS)]
    method_found = [m for m in METHOD_SIGNALS if m in abstract_lower]
    population_found = [p for p in POPULATION_SIGNALS if p in abstract_lower]

    issues = []
    if len(vague_found) >= 3:
        issues.append("Many vague/generic terms detected (e.g. society, issues, factors, impact).")
    if not population_found:
        issues.append("No clear population / sample terms detected.")
    if not method_found:
        issues.append("No clear methodological signal detected.")
    if len(candidates) < 6:
        issues.append("Very few usable candidate keywords extracted.")
    if len(abstract.split()) < 80:
        issues.append("Abstract is quite short – keyword extraction may be limited.")
    if not issues:
        issues.append("No major structural problems detected. Keywords can still be sharpened.")

    return {
        "candidates": candidates,
        "vague": vague_found[:8],
        "methods": method_found,
        "population": population_found,
        "issues": issues
    }

def quick_clean(candidates, vague):
    cleaned = [c for c in candidates if c not in vague and not any(v in c.split() for v in VAGUE_TERMS)]
    return cleaned[:15]

def match_journals(keywords, discipline, mode="Conservative"):
    """Return journals ranked by Match %."""
    if journal_db.empty or not keywords:
        return pd.DataFrame()

    keywords = [k.strip() for k in keywords if k.strip()]
    total_kw = len(keywords)
    if total_kw == 0:
        return pd.DataFrame()

    kw_set = set(k.lower() for k in keywords)
    discipline_keys = DISCIPLINE_MAP.get(discipline, [])

    rows = []
    for _, row in journal_db.iterrows():
        journal = str(row.get("Journal", ""))
        category = str(row.get("Category", "")).lower()
        note = str(row.get("Note", "")).lower()
        text = f"{journal.lower()} {category} {note}"

        # Keyword matches
        matched = [k for k in kw_set if k in text or any(tok in text for tok in k.split())]
        match_count = len(matched)

        # Discipline bonus (small)
        discipline_bonus = 0
        if discipline_keys and any(dk in category or dk in text for dk in discipline_keys):
            discipline_bonus = 1

        if match_count == 0 and discipline_bonus == 0:
            continue

        # Match percentage (main ranking signal)
        match_pct = round((match_count / total_kw) * 100)

        # Optional small lift for discipline match (max +10)
        if discipline_bonus:
            match_pct = min(100, match_pct + 10)

        abdc = str(row.get("ABDC_Rank", "")).strip()
        source = str(row.get("Source", ""))
        quality = str(row.get("Quality_Level", ""))

        strength = 1
        if abdc in {"A", "A*"}:
            strength += 1
        if "Scopus" in source:
            strength += 1
        if discipline_bonus:
            strength += 1

        rows.append({
            "Journal": journal,
            "Category": row.get("Category", ""),
            "Match_%": match_pct,
            "Matched_Terms": ", ".join(matched[:6]) if matched else "—",
            "Quality_Level": quality,
            "ABDC_Rank": abdc if abdc else "—",
            "Source": source,
            "Strength": strength,
            "Note": row.get("Note", "")
        })

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)

    if mode == "Conservative":
        # Keep only reasonably strong matches
        result = result[result["Match_%"] >= 20]

    # Primary sort: Match % (descending)
    result = result.sort_values(["Match_%", "Strength"], ascending=False)
    return result.head(25)

# =========================================================
# MODULE 1: Abstract Diagnosis
# =========================================================
if section == "1. Abstract Diagnosis":
    st.header("1. Abstract Diagnosis")
    st.markdown("Select your discipline (optional) and paste a full abstract.")

    discipline = st.selectbox("Discipline", DISCIPLINES)

    abstract = st.text_area(
        "Paste your abstract here",
        height=220,
        placeholder="Paste the full abstract of your paper or proposal..."
    )

    if st.button("Analyse Abstract", type="primary"):
        if not abstract.strip():
            st.warning("Please paste an abstract first.")
        else:
            diagnosis = diagnose_abstract(abstract)
            st.session_state["abstract"] = abstract
            st.session_state["discipline"] = discipline
            st.session_state["diagnosis"] = diagnosis
            st.session_state["final_keywords"] = diagnosis["candidates"][:12]

            st.subheader("Diagnosis Report")
            st.markdown(f"**Discipline selected:** {discipline}")
            for issue in diagnosis["issues"]:
                st.markdown(f"- {issue}")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Candidate terms extracted**")
                st.write(", ".join(diagnosis["candidates"][:15]) if diagnosis["candidates"] else "—")
            with col2:
                st.markdown("**Vague / generic terms found**")
                st.write(", ".join(diagnosis["vague"]) if diagnosis["vague"] else "None detected")

            st.markdown("**Population signals**")
            st.write(", ".join(diagnosis["population"]) if diagnosis["population"] else "None clearly detected")
            st.markdown("**Method signals**")
            st.write(", ".join(diagnosis["methods"]) if diagnosis["methods"] else "None clearly detected")

            st.success("Diagnosis complete. Go to **Module 2** to improve the keywords.")

# =========================================================
# MODULE 2: Improvement Pathways
# =========================================================
elif section == "2. Improvement Pathways":
    st.header("2. Improvement Pathways")

    if "diagnosis" not in st.session_state:
        st.warning("Please run **Module 1 – Abstract Diagnosis** first.")
    else:
        diagnosis = st.session_state["diagnosis"]
        discipline = st.session_state.get("discipline", "None / Prefer not to specify")
        st.markdown(f"**Discipline:** {discipline}")
        st.markdown("**Original candidate terms:**")
        st.code(", ".join(diagnosis["candidates"][:15]))

        pathway = st.radio(
            "Choose an improvement pathway",
            [
                "A. Quick Clean",
                "B. Keep strongest terms only",
                "C. Structured (SPIDER-style)",
                "D. Free-text expansion ready"
            ]
        )

        if pathway.startswith("A"):
            cleaned = quick_clean(diagnosis["candidates"], diagnosis["vague"])
            st.subheader("Pathway A – Quick Clean")
            st.write("Vague and generic terms removed.")
            st.code(", ".join(cleaned))
            if st.button("Use these keywords"):
                st.session_state["final_keywords"] = cleaned
                st.session_state["pathway_used"] = "Quick Clean"
                st.success("Keywords saved. Proceed to Module 3.")

        elif pathway.startswith("B"):
            strongest = diagnosis["candidates"][:10]
            st.subheader("Pathway B – Strongest terms")
            st.code(", ".join(strongest))
            if st.button("Use these keywords"):
                st.session_state["final_keywords"] = strongest
                st.session_state["pathway_used"] = "Strongest terms"
                st.success("Keywords saved. Proceed to Module 3.")

        elif pathway.startswith("C"):
            st.subheader("Pathway C – Structured (SPIDER-style)")
            st.markdown("Re-organise your terms into simple SPIDER components:")
            s = st.text_input("S – Sample / Population", ", ".join(diagnosis["population"][:5]))
            p = st.text_input("P – Phenomenon of Interest", ", ".join(diagnosis["candidates"][:5]))
            d = st.text_input("D – Design / Method", ", ".join(diagnosis["methods"][:3]))
            e = st.text_input("E – Evaluation / Outcome", "")
            r = st.text_input("R – Research type", "")
            structured = []
            for part in [s, p, d, e, r]:
                structured.extend([x.strip() for x in part.split(",") if x.strip()])
            structured = list(dict.fromkeys(structured))
            st.code(", ".join(structured))
            if st.button("Use structured keywords"):
                st.session_state["final_keywords"] = structured
                st.session_state["pathway_used"] = "SPIDER-style"
                st.success("Keywords saved. Proceed to Module 3.")

        elif pathway.startswith("D"):
            terms = diagnosis["candidates"][:12]
            st.subheader("Pathway D – Free-text expansion")
            st.markdown("Ready-to-use search strings:")
            gs = " AND ".join([f'"{t}"' for t in terms[:8]])
            st.markdown("**Google Scholar**")
            st.code(gs)
            st.markdown(f"[Open in Google Scholar](https://scholar.google.com/scholar?q={quote_plus(gs)})")
            st.markdown("**JSTOR**")
            st.markdown(f"[Open in JSTOR](https://www.jstor.org/action/doBasicSearch?Query={quote_plus(' AND '.join(terms[:6]))})")
            if st.button("Use these terms for journal matching"):
                st.session_state["final_keywords"] = terms
                st.session_state["pathway_used"] = "Free-text expansion"
                st.success("Keywords saved. Proceed to Module 3.")

# =========================================================
# MODULE 3: Journal Finder
# =========================================================
elif section == "3. Journal Finder":
    st.header("3. Journal Finder")

    keywords = st.session_state.get("final_keywords", [])
    discipline = st.session_state.get("discipline", "None / Prefer not to specify")

    if not keywords:
        st.warning("No keywords available. Please complete Module 1 and Module 2 first.")
    else:
        st.markdown(f"**Discipline:** {discipline}")
        st.markdown("**Current keywords:**")
        st.code(", ".join(keywords))

        mode = st.radio("Recommendation mode", ["Conservative", "Exploratory"], horizontal=True)
        st.caption("Conservative shows only journals with Match % ≥ 20. Exploratory shows a broader list.")

        if st.button("Find Journals", type="primary"):
            results = match_journals(keywords, discipline, mode=mode)
            st.session_state["recommended_journals"] = results

            if results.empty:
                st.warning("No strong matches found. Try different keywords or switch to Exploratory mode.")
            else:
                st.subheader(f"Recommended Journals (ranked by Match %)")
                st.dataframe(
                    results[["Journal", "Category", "Match_%", "Matched_Terms", "Quality_Level", "ABDC_Rank"]],
                    use_container_width=True,
                    hide_index=True
                )
                st.download_button(
                    "Download shortlist (CSV)",
                    results.to_csv(index=False),
                    "journal_shortlist.csv",
                    "text/csv"
                )

# =========================================================
# MODULE 4: Supervisor Review
# =========================================================
elif section == "4. Supervisor Review":
    st.header("4. Supervisor Review")

    if "abstract" not in st.session_state:
        st.info("No student session loaded yet. The student should first run Modules 1–3.")
    else:
        st.subheader("Student Snapshot")
        st.markdown(f"**Discipline:** {st.session_state.get('discipline', '—')}")
        st.markdown("**Abstract (excerpt)**")
        st.write(st.session_state["abstract"][:500] + ("..." if len(st.session_state["abstract"]) > 500 else ""))

        diag = st.session_state.get("diagnosis", {})
        st.markdown("**Diagnosis issues**")
        for issue in diag.get("issues", []):
            st.markdown(f"- {issue}")

        st.markdown("**Pathway used:** " + st.session_state.get("pathway_used", "—"))
        st.markdown("**Final keywords:** " + ", ".join(st.session_state.get("final_keywords", [])))

        recs = st.session_state.get("recommended_journals", pd.DataFrame())
        if not isinstance(recs, pd.DataFrame):
            recs = pd.DataFrame()

        if not recs.empty:
            st.markdown("**Recommended journals (ranked by Match %)**")
            st.dataframe(
                recs[["Journal", "Category", "Match_%", "Matched_Terms", "Quality_Level", "ABDC_Rank"]].head(15),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No journal recommendations available yet.")

        st.subheader("Supervisor Feedback")
        kw_quality = st.selectbox("Keyword quality after improvement", ["Strong", "Adequate", "Needs work"])
        shortlist_quality = st.selectbox(
            "Journal shortlist assessment",
            ["Suitable", "Too ambitious", "Too narrow", "Missing important journals"]
        )
        intellectual_fit = st.selectbox("Intellectual fit", ["Strong", "Acceptable", "Weak"])
        confidence = st.selectbox("Confidence in the tool’s matching", ["High", "Medium", "Low"])
        next_steps = st.text_area("Suggested next steps")
        comments = st.text_area("Additional comments")

        if st.button("Generate Feedback Summary"):
            summary = f"""
SUPERVISOR FEEDBACK SUMMARY
---------------------------
Discipline: {st.session_state.get('discipline', '—')}
Keyword quality: {kw_quality}
Journal shortlist: {shortlist_quality}
Intellectual fit: {intellectual_fit}
Confidence in matching: {confidence}

Suggested next steps:
{next_steps}

Comments:
{comments}
"""
            st.code(summary)
            st.download_button("Download feedback", summary, "supervisor_feedback.txt")

st.markdown("---")
st.caption("Social Science Journal Finder · Corpus: Scopus Top 10% (Core Social Sciences + Education) + ABDC 2025 relevant journals")