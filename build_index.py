import os
import pandas as pd
from dotenv import load_dotenv
import chromadb
from openai import OpenAI

# 1) Load API key from .env
load_dotenv()
client_oai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2) Init Chroma (persistent on disk)
chroma = chromadb.PersistentClient(path="chroma_data")

collection = chroma.get_or_create_collection(
    name="uwm_courses",
    metadata={"hnsw:space": "cosine"}
)

# 3) Load your course catalog CSV
csv_path = "data/course_catalog_template.csv"
df = pd.read_csv(csv_path)

def row_to_doc(row: pd.Series):
    code = str(row.get("course_code", "")).strip()
    title = str(row.get("course_title", "")).strip()
    desc = str(row.get("description", "")).strip()
    credits = str(row.get("credits", "")).strip()
    prereq = str(row.get("prerequisites", "")).strip()
    url = str(row.get("source_url", "")).strip()

    display_title = f"{code}: {title}" if code else title

    parts = [display_title]
    if desc:
        parts.append(desc)
    if credits:
        parts.append(f"Credits: {credits}.")
    if prereq:
        parts.append(f"Prerequisites: {prereq}")
    text = " ".join(parts).strip()

    return display_title, text, url

ids, docs, metas, embs = [], [], [], []

for i, row in df.iterrows():
    title, text, url = row_to_doc(row)
    if not text:
        continue  # skip empty rows

    # 4) Make embedding for this course
    emb = client_oai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    ).data[0].embedding

    doc_id = f"course::{row.get('course_code', i)}"

    ids.append(doc_id)
    docs.append(text)
    metas.append({"title": title, "url": url})
    embs.append(emb)

# 5) Store everything in Chroma
collection.upsert(
    ids=ids,
    documents=docs,
    metadatas=metas,
    embeddings=embs
)

print(f"✅ Indexed {len(ids)} courses into Chroma.")