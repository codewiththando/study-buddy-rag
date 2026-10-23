"""FastAPI app exposing the notes assistant over HTTP."""

import shutil
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.qa import answer
from app.store import add_pdf

app = FastAPI(title="Pagewise", description="Ask questions about your notes, with page citations.")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


class Question(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
def upload(file: UploadFile = File(...)):
    """Save a PDF and add its chunks to the vector store."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    destination = DATA_DIR / Path(file.filename).name  # .name strips any folder parts
    with destination.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    chunk_count = add_pdf(str(destination))
    if chunk_count == 0:
        raise HTTPException(
            status_code=422,
            detail="No text found in this PDF. It may be scanned images.",
        )
    return {"filename": destination.name, "chunks": chunk_count}


@app.post("/ask")
def ask(body: Question):
    """Answer a question from the stored notes, with sources."""
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    result = answer(body.question)
    return {
        "answer": result["answer"],
        "sources": [
            {"source": h["source"], "page": h["page"], "text": h["text"]}
            for h in result["sources"]
        ],
    }