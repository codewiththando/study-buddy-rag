# study-buddy-rag
Study assistant that answers questions from your lecture notes and past papers, with page-level citations. Built with Python, FastAPI, Chroma, and an LLM API.
# Pagewise

Ask questions about your course notes and get answers with page-level citations.

Pagewise lets you upload PDFs (lecture notes, textbooks, past papers), then
answers questions using only what's in those documents. Every answer points to
the page it came from, so you can verify it instead of trusting it blindly.

**Live demo:** [link coming soon]

## Features
- PDF upload and automatic chunking
- Semantic search over your notes using embeddings
- Answers grounded in your documents, with page citations
- Evaluation set measuring retrieval accuracy

## Tech stack
Python · FastAPI · ChromaDB · [LLM provider] · Streamlit/React
