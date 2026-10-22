"""Embed chunks into a local Chroma database and search them by meaning."""

import sys
from pathlib import Path

import chromadb

from app.ingest import ingest_pdf

DB_PATH = "chroma_db"          # folder created in the repo root (gitignored)
COLLECTION_NAME = "notes"
BATCH_SIZE = 100


def get_collection():
    """Open (or create) the persistent collection.

    Chroma's default embedding model (all-MiniLM-L6-v2) runs locally.
    It downloads once (~80 MB) the first time you add or search.
    """
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME)


def add_pdf(pdf_path: str) -> int:
    """Chunk a PDF and store every chunk. Re-running on the same PDF is safe."""
    chunks = ingest_pdf(pdf_path)
    if not chunks:
        print("No text found in this PDF (it may be scanned images).")
        return 0

    collection = get_collection()
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        collection.upsert(  # upsert = update if the id already exists
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[{"page": c["page"], "source": c["source"]} for c in batch],
        )
        print(f"  stored {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)}")
    return len(chunks)


def search(question: str, k: int = 4) -> list[dict]:
    """Return the k chunks most similar in meaning to the question."""
    collection = get_collection()
    result = collection.query(query_texts=[question], n_results=k)

    hits = []
    for text, meta, dist in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        hits.append(
            {
                "text": text,
                "page": meta["page"],
                "source": meta["source"],
                "distance": dist,  # lower = more similar
            }
        )
    return hits


if __name__ == "__main__":
    usage = (
        "Usage:\n"
        "  python -m app.store add data/your-file.pdf\n"
        '  python -m app.store search "your question"'
    )
    if len(sys.argv) != 3 or sys.argv[1] not in ("add", "search"):
        sys.exit(usage)

    command, argument = sys.argv[1], sys.argv[2]

    if command == "add":
        count = add_pdf(argument)
        print(f"Done. {count} chunks from {Path(argument).name} are in '{DB_PATH}'.")
    else:
        for rank, hit in enumerate(search(argument), start=1):
            print(f"\n#{rank}  {hit['source']}, page {hit['page']}  (distance {hit['distance']:.3f})")
            print(hit["text"][:300] + ("..." if len(hit["text"]) > 300 else ""))