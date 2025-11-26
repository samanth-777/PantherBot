# PantherBot 

PantherBot is an AI-powered chatbot that helps UWM students instantly find course information such as prerequisites, credits, descriptions, and catalog links.  
It uses Retrieval-Augmented Generation (RAG) with a local vector database (ChromaDB) plus an OpenAI model, and exposes a simple chat interface built in Streamlit.

---

## Features

- Ask natural-language questions about UWM courses  
- Look up course descriptions, credits, and prerequisites  
- Direct catalog URL for each course (when available)  
- Small-talk support so the bot behaves more like a real assistant  
- Hybrid logic:
  - Direct CSV lookup when a specific course code is mentioned (e.g., `INFOST 790`)
  - Semantic search over the course catalog using embeddings + GPT

---

## Tech Stack

- **Python 3.9+**
- **Streamlit** – chat UI  
- **ChromaDB** – local vector database for course embeddings  
- **OpenAI API** – `text-embedding-3-small` for embeddings and `gpt-3.5-turbo` for answers  
- **pandas** – CSV loading and preprocessing  
- **python-dotenv** – loading `OPENAI_API_KEY` from `.env`

---

## Project Structure

```text
PantherBot/
├── app.py                 # Streamlit front-end (chat UI)
├── pantherbot_engine.py   # Core logic: lookup, RAG, smalltalk
├── build_index.py         # One-time script to index the course catalog into Chroma
├── test_query.py          # Simple CLI test for the RAG retrieval
├── test_bot.py            # Simple CLI test for the bot logic (no UI)
├── data/
│   └── course_catalog_template.csv   # UWM course catalog data (filled by me)
├── chroma_data/           # Local vector store created by build_index.py
├── requirements.txt       # Python dependencies
└── .gitignore             # Ignores .venv, .env, etc.
