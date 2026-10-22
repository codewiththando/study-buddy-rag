"""Turn a PDF into chunks that remember which page they came from."""

import sys
from pathlib import Path

from pypdf import PdfReader

CHUNK_SIZE = 700   # target characters per chunk
OVERLAP = 100      # characters shared between neighbouring chunks


def split_text(text: str, size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    """Split text into overlapping chunks, preferring to break at whitespace."""
    text = " ".join(text.split())  # collapse newlines and repeated spaces
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # back up to the last space so we don't cut a word in half
            space = text.rfind(" ", start, end)
            if space > start + size // 2:
                end = space
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)  # step back for overlap, always move forward
    return chunks


def ingest_pdf(path: str | Path) -> list[dict]:
    """Read a PDF and return a list of {id, text, page, source} chunks."""
    path = Path(path)
    reader = PdfReader(path)
    chunks = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        for i, piece in enumerate(split_text(text)):
            chunks.append(
                {
                    "id": f"{path.stem}-p{page_number}-c{i}",
                    "text": piece,
                    "page": page_number,
                    "source": path.name,
                }
            )
    return chunks


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m app.ingest data/your-file.pdf")

    result = ingest_pdf(sys.argv[1])
    pages = {c["page"] for c in result}
    print(f"Chunks: {len(result)} | Pages with text: {len(pages)}")
    if result:
        first = result[0]
        print(f"\nFirst chunk (page {first['page']}, id {first['id']}):\n")
        print(first["text"])
    else:
        print("No text found. The PDF may be scanned images (needs OCR).")
