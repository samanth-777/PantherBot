import os
import re
import pandas as pd
from dotenv import load_dotenv
import chromadb
from openai import OpenAI

# ----------------------------
# API key + environment setup
# ----------------------------

# Load from .env when running locally
load_dotenv()

# Try to get API key from environment
API_KEY = os.getenv("OPENAI_API_KEY")

# If running on Streamlit Cloud, also check st.secrets
try:
    import streamlit as st  # this will work on Streamlit Cloud and locally if installed
    if not API_KEY:
        API_KEY = st.secrets.get("OPENAI_API_KEY")
except Exception:
    # If streamlit is not available (e.g., running build_index), just ignore
    pass

if not API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is not set. "
        "Set it in a .env file (locally) or in Streamlit secrets (on the cloud)."
    )

# Initialize OpenAI client
client_oai = OpenAI(api_key=API_KEY)

# Initialize Chroma (persistent DB)
chroma = chromadb.PersistentClient(path="chroma_data")
collection = chroma.get_collection("uwm_courses")

COURSE_CODE_PATTERN = re.compile(r"[A-Za-z]{3,7}\s*[-]?\s*\d{3}")

# ----------------------------
# Config / Data loading
# ----------------------------

COURSE_CSV_PATH_OPTIONS = [
    "data/course_catalog_template.csv",
    "course_catalog_template.csv",
]

COURSES_DF = None
for path in COURSE_CSV_PATH_OPTIONS:
    if os.path.exists(path):
        COURSES_DF = pd.read_csv(path)
        print(f"Loaded courses from: {path}")
        break

if COURSES_DF is None:
    print("⚠️ Could not find course_catalog_template.csv in expected locations.")
else:
    COURSES_DF["__code_norm__"] = (
        COURSES_DF["course_code"]
        .astype(str)
        .str.upper()
        .str.replace(" ", "", regex=False)
        .str.replace("-", "", regex=False)
    )


# ----------------------------
# Course lookup helpers
# ----------------------------

def extract_course_code_from_question(question: str):
    """Extract a course code like 'INFOST 790' / 'infost-790'."""
    m = COURSE_CODE_PATTERN.search(question)
    if not m:
        return None
    raw = m.group(0)
    return re.sub(r"[\s\-]", "", raw.upper())


def find_course_row_from_question(question: str):
    """
    Try to find a course row whose course_code appears in the question.
    Matching is case-insensitive and ignores spaces and hyphens.
    """
    if COURSES_DF is None:
        return None

    norm = extract_course_code_from_question(question)
    if not norm:
        return None

    for _, row in COURSES_DF.iterrows():
        code_norm = str(row.get("__code_norm__", "")).strip()
        if code_norm == norm:
            return row

    return None


def format_course_answer(row: pd.Series) -> str:
    """
    Turn a course row into a nice Markdown answer string.
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

    if code or title:
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


# ----------------------------
# Small-talk / chit-chat handling
# ----------------------------

def handle_smalltalk(question: str):
    """
    Handle greetings, thanks, and simple conversational stuff
    so the bot feels more like ChatGPT and doesn't say the
    'cannot find course' line for 'hi'.
    """
    q = question.strip().lower()

    # greetings
    greetings = ["hi", "hello", "hey", "yo", "hiya", "sup"]
    if any(q == g or q.startswith(g + " ") for g in greetings):
        return (
            "Hello! 👋 I'm PantherBot, your UWM course assistant. "
            "Ask me about courses, prerequisites, credits, or degree requirements."
        )

    if "good morning" in q:
        return (
            "Good morning! ☀️ How can I help you with UWM courses today?"
        )
    if "good afternoon" in q:
        return (
            "Good afternoon! 😄 What course information are you looking for?"
        )
    if "good evening" in q:
        return (
            "Good evening! 🌙 Need help with any UWM course details?"
        )

    # thanks
    if "thank" in q:
        return "You’re welcome! 😊 Let me know if you want to look up another course."

    # who are you / what is this
    if "who are you" in q or "what are you" in q or "pantherbot" in q:
        return (
            "I’m PantherBot, a UWM course assistant chatbot. I can help you find "
            "information about courses, prerequisites, credits, and program requirements."
        )

    # bye
    if q in ["bye", "goodbye", "see you", "see ya"]:
        return "Bye! 👋 Good luck with your classes at UWM!"

    return None  # not smalltalk


# ----------------------------
# Chroma / RAG helpers
# ----------------------------

def retrieve_context(question: str, k: int = 3):
    """Retrieve top-k relevant course chunks from Chroma."""
    q_emb = client_oai.embeddings.create(
        model="text-embedding-3-small",
        input=question
    ).data[0].embedding

    results = collection.query(
        query_embeddings=[q_emb],
        n_results=k
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    return docs, metas


def generate_answer(question: str, docs, metas):
    """Create a grounded answer using GPT, with a defensive fallback."""
    if not docs:
        return "I cannot find this information in the UWM course catalog."

    context_blocks = []
    for doc, meta in zip(docs, metas):
        title = meta.get("title", "Unknown course")
        url = meta.get("url", "")
        context_blocks.append(f"{title} (Source: {url}):\n{doc}")

    context_text = "\n\n".join(context_blocks)

    prompt = f"""
You are PantherBot, the official UWM course information assistant.

Use ONLY the context below to answer the question.
If the answer is not found in the context, say exactly:
"I cannot find this information in the UWM course catalog."

Context:
{context_text}

Question: {question}

Answer with clear details. When possible, include the source URL in parentheses like (Source: <URL>).
"""

    response = client_oai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    return response.choices[0].message.content


# ----------------------------
# Main entry point
# ----------------------------

def ask_pantherbot(question: str):
    """
    Main function used by app.py.
    0) Handle greetings / smalltalk.
    1) Try direct course-code lookup using the CSV.
    2) If that fails, fall back to the embedding-based Chroma search + GPT.
    """
    # 0) Small talk first
    smalltalk_reply = handle_smalltalk(question)
    if smalltalk_reply is not None:
        return smalltalk_reply, [], []

    # 1) Direct course code handling (e.g., 'INFOST 790')
    row = find_course_row_from_question(question)
    if row is not None:
        answer = format_course_answer(row)
        metas = [{
            "title": f"{row.get('course_code', '')} – {row.get('course_title', '')}",
            "url": row.get("source_url", "")
        }]
        return answer, [], metas

    # 2) Fallback: semantic search with Chroma + GPT
    docs, metas = retrieve_context(question)
    answer = generate_answer(question, docs, metas)
    return answer, docs, metas