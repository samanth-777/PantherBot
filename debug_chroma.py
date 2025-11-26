import chromadb
chroma = chromadb.PersistentClient(path="chroma_data")
collection = chroma.get_collection("uwm_courses")

print("Total items:", collection.count())

# Try to get INFOST 582 specifically
try:
    item = collection.get(ids=["course::INFOST 582"])
    print("Found INFOST 582:", item)
except Exception as e:
    print("Error getting INFOST 582:", e)

# List first 5 ids to see format
print("Sample IDs:", collection.get(limit=5)["ids"])
