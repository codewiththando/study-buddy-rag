"""Embed chunks into a local Chroma database and search them.

Three search modes: "semantic" (embeddings), "keyword" (BM25), "hybrid" (both, merged).
"""

import re
import sys
from pathlib import Path

import chromadb
from rank_bm25 import BM25Okapi

from app.ingest import ingest_pdf

DB_PATH = "chroma_db"          # folder created in the repo root (gitignored)
COLLECTION_NAME = "notes"
BATCH_SIZE = 100
CANDIDATES = 20                # results each method contributes before merging
RRF_K = 60                     # standard constant for reciprocal rank fusion

STOPWORDS = set(
    "a an the is are was were be of in on at to for and or what how why when "
    "does do did it its this that with as by from can".split()
)

_bm25_cache = {"count": None, "bm25": None, "chunks": None}


def get_collection():
    """Open (or create) the persistent collection."""
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


def tokenize(text: str) -> list[str]:
    """Lowercase words with common filler words removed."""
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]


def _keyword_index(collection):
    """Build (and cache) a BM25 index over every stored chunk."""
    count = collection.count()
    if _bm25_cache["count"] != count:
        data = collection.get(include=["documents", "metadatas"])
        chunks = [
            {"id": i, "text": d, "page": m["page"], "source": m["source"]}
            for i, d, m in zip(data["ids"], data["documents"], data["metadatas"])
        ]
        _bm25_cache["count"] = count
        _bm25_cache["chunks"] = chunks
        _bm25_cache["bm25"] = BM25Okapi([tokenize(c["text"]) for c in chunks])
    return _bm25_cache["bm25"], _bm25_cache["chunks"]


def semantic_search(question: str, k: int = 4) -> list[dict]:
    """Chunks closest in meaning to the question (embedding search)."""
    collection = get_collection()
    result = collection.query(query_texts=[question], n_results=k)
    hits = []
    for id_, text, meta, dist in zip(
        result["ids"][0], result["documents"][0],
        result["metadatas"][0], result["distances"][0],
    ):
        hits.append(
            {"id": id_, "text": text, "page": meta["page"],
             "source": meta["source"], "distance": dist}  # lower = more similar
        )
    return hits


def keyword_search(question: str, k: int = 4) -> list[dict]:
    """Chunks that best match the question's exact words (BM25)."""
    collection = get_collection()
    if collection.count() == 0:
        return []
    bm25, chunks = _keyword_index(collection)
    scores = bm25.get_scores(tokenize(question))
    top = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    return [dict(chunks[i], distance=float("nan")) for i in top if scores[i] > 0]


def hybrid_search(question: str, k: int = 4) -> list[dict]:
    """Merge semantic and keyword rankings with reciprocal rank fusion."""
    semantic = semantic_search(question, CANDIDATES)
    keyword = keyword_search(question, CANDIDATES)
    distances = {h["id"]: h["distance"] for h in semantic}

    fused = {}
    for ranking in (semantic, keyword):
        for rank, hit in enumerate(ranking, start=1):
            entry = fused.setdefault(hit["id"], {**hit, "score": 0.0})
            entry["score"] += 1.0 / (RRF_K + rank)

    for id_, entry in fused.items():
        entry["distance"] = distances.get(id_, float("nan"))

    ranked = sorted(fused.values(), key=lambda h: h["score"], reverse=True)
    return ranked[:k]


def search(question: str, k: int = 4, mode: str = "hybrid") -> list[dict]:
    """Search the stored notes. mode: "hybrid" (default), "semantic", or "keyword"."""
    if mode == "semantic":
        return semantic_search(question, k)
    if mode == "keyword":
        return keyword_search(question, k)
    return hybrid_search(question, k)


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