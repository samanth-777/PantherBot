import os
from dotenv import load_dotenv
import chromadb
from openai import OpenAI

load_dotenv()

client_oai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Use the same persistent Chroma DB
chroma = chromadb.PersistentClient(path="chroma_data")
collection = chroma.get_collection("uwm_courses")

def ask_courses(question: str, k: int = 3):
    # 1) Embed the question
    q_emb = client_oai.embeddings.create(
        model="text-embedding-3-small",
        input=question
    ).data[0].embedding

    # 2) Query Chroma
    results = collection.query(
        query_embeddings=[q_emb],
        n_results=k
    )
    return results

if __name__ == "__main__":
    question = "What are the prerequisites for INFOST 582?"
    res = ask_courses(question, k=3)

    print("🔎 Question:", question)
    for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
        print("\n---")
        print("Title:", meta.get("title"))
        print("URL:  ", meta.get("url"))
        print("Text:", doc[:400], "...")