import os
import re
import pandas as pd
import streamlit as st
from PIL import Image

from pantherbot_engine import ask_pantherbot  # fallback for general questions


# ---------------------------------------------------------
# Setup
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(page_title="PantherBot – UWM Course Assistant", page_icon="🐾")


# ---------------------------------------------------------
# Display UWM Logo
# ---------------------------------------------------------

LOGO_PATH = os.path.join(BASE_DIR, "data", "uwm_logo.png")

if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=260)   # Adjust width if needed


# ---------------------------------------------------------
# Load CSV (Absolute Paths)
# ---------------------------------------------------------

CSV_PATH_OPTIONS = [
    os.path.join(BASE_DIR, "data", "course_catalog_template.csv"),
    os.path.join(BASE_DIR, "course_catalog_template.csv"),
]

COURSES_DF = None
csv_loaded_from = None

for path in CSV_PATH_OPTIONS:
    if os.path.exists(path):
        try:
            COURSES_DF = pd.read_csv(path)
            csv_loaded_from = path
            break
        except Exception as e:
            print(f"Error loading {path}: {e}")


# ---------------------------------------------------------
# Build Course Code Map for Fast Lookup
# ---------------------------------------------------------

CODE_MAP = {}
COURSE_CODE_PATTERN = re.compile(r"[A-Za-z]{3,7}\s*[-]?\s*\d{3}")

if COURSES_DF is not None and "course_code" in COURSES_DF.columns:
    for idx, row in COURSES_DF.iterrows():
        raw = str(row.get("course_code", "")).strip()
        if not raw:
            continue
        # Normalize: INFOST 790 → INFOST790
        norm = re.sub(r"[\s\-]", "", raw.upper())
        CODE_MAP[norm] = row


def extract_course_code_from_question(question: str):
    """
    Extract something like 'INFOST 790' or 'infost-790' from the user's question.
    Returns normalized form like 'INFOST790'.
    """
    m = COURSE_CODE_PATTERN.search(question)
    if not m:
        return None
    raw = m.group(0)
    return re.sub(r"[\s\-]", "", raw.upper())


def find_course_row_from_question(question: str):
    """
    Use regex extraction + CODE_MAP lookup.
    """
    if not CODE_MAP:
        return None

    norm = extract_course_code_from_question(question)
    if not norm:
        return None

    return CODE_MAP.get(norm)


# ---------------------------------------------------------
# Formatting for Display
# ---------------------------------------------------------

def format_course_answer(row: pd.Series) -> str:
    """
    Turn a course row into a clean Markdown answer.
    """
    code = str(row.get("course_code", "")).strip()
    title = str(row.get("course_title", "")).strip()
    desc = str(row.get("description", "")).strip()
    credits = str(row.get("credits", "")).strip()
    prereq = str(row.get("prerequisites", "")).strip()
    url = str(row.get("source_url", "")).strip()
    req_msist = str(row.get("Required Courses for MSIST", "")).strip()
    req_mscs = str(row.get("Required Courses for MSCS", "")).strip()

    lines = []

    lines.append(f"**{code}: {title}**")

    if credits:
        lines.append(f"**Credits:** {credits}")

    if desc:
        lines.append(desc)

    if prereq:
        lines.append(f"**Prerequisites:** {prereq}")

    if req_msist:
        lines.append(f"**Required for MSIST:** {req_msist}")

    if req_mscs:
        lines.append(f"**Required for MSCS:** {req_mscs}")

    if url:
        lines.append(f"(Source: {url})")

    return "\n\n".join(lines)


# ---------------------------------------------------------
# UI Header
# ---------------------------------------------------------

st.title("PantherBot – UWM Course Assistant")
st.write("Ask me about UWM courses, prerequisites, credits, and more.")


# ---------------------------------------------------------
# Chat Logic
# ---------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Show prior messages
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input box
user_question = st.chat_input("Ask about a course, e.g., 'INFOST 790'")

if user_question:

    # Display user message
    st.session_state["messages"].append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    answer_text = None
    metas = []

    # 1) Direct CSV Lookup First (exact, reliable)
    row = find_course_row_from_question(user_question)

    if row is not None:
        answer_text = format_course_answer(row)
        metas = [{
            "title": f"{row.get('course_code', '')} – {row.get('course_title', '')}",
            "url": row.get("source_url", "")
        }]
    else:
        # 2) If no course code detected, fallback to RAG engine
        answer_text, docs, metas = ask_pantherbot(user_question)

    # Display assistant answer
    with st.chat_message("assistant"):
        st.markdown(answer_text)

        if metas:
            with st.expander("Sources"):
                for m in metas:
                    title = m.get("title", "Source")
                    url = m.get("url", "")
                    if url:
                        st.markdown(f"- **{title}** — {url}")
                    else:
                        st.markdown(f"- **{title}**")

    st.session_state["messages"].append({"role": "assistant", "content": answer_text})