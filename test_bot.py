from pantherbot_engine import ask_pantherbot

if __name__ == "__main__":
    q = "What are the prerequisites for INFOST 582?"
    answer, docs, metas = ask_pantherbot(q)

    print("🧠 Answer:\n", answer)
    print("\n🔍 Retrieved documents:")
    for meta in metas:
        print("-", meta["title"], meta["url"])