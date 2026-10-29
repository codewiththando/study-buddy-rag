"""Pagewise public demo. Runs the pipeline directly (no separate API server)."""

import os
from pathlib import Path

import streamlit as st

# On Streamlit Cloud the key comes from the app's Secrets settings
try:
    if "GEMINI_API_KEY" in st.secrets:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass  # locally the key comes from your .env file

from app.qa import answer  # noqa: E402
from app.store import add_pdf, get_collection  # noqa: E402

SAMPLE_DIR = Path("sample")
MAX_QUESTIONS_PER_SESSION = 10

st.set_page_config(page_title="Pagewise", page_icon="📄")
st.title("📄 Pagewise")
st.caption("Ask questions about the sample document and get answers with page citations.")


@st.cache_resource(show_spinner="Indexing the sample document (first load only)...")
def ensure_index() -> int:
    """Index each sample PDF once, then return the number of stored chunks."""
    collection = get_collection()
    for pdf in sorted(SAMPLE_DIR.glob("*.pdf")):
        if not collection.get(where={"source": pdf.name}, limit=1)["ids"]:
            add_pdf(str(pdf))
    return get_collection().count()


def show_sources(sources: list[dict]) -> None:
    with st.expander("Sources"):
        for src in sources:
            st.markdown(f"**{src['source']}, page {src['page']}**")
            st.caption(src["text"])


chunk_count = ensure_index()
if chunk_count == 0:
    st.error("No sample document found. Add a PDF to the sample/ folder.")
    st.stop()

with st.sidebar:
    st.header("About")
    st.write(
        "Answers come only from the indexed sample document, "
        "and every answer cites its source pages."
    )
    st.caption(f"Indexed chunks: {chunk_count}")

if "history" not in st.session_state:
    st.session_state.history = []
if "asked" not in st.session_state:
    st.session_state.asked = 0

for message in st.session_state.history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            show_sources(message["sources"])

question = st.chat_input("Ask a question about the document")

if question:
    if st.session_state.asked >= MAX_QUESTIONS_PER_SESSION:
        st.warning("Demo limit reached for this session. Refresh the page to start again.")
    else:
        st.session_state.asked += 1
        st.session_state.history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Searching the document..."):
                try:
                    result = answer(question)
                    text, sources = result["answer"], result["sources"]
                except Exception:
                    text, sources = "Something went wrong. Please try again in a minute.", []
            st.markdown(text)
            if sources:
                show_sources(sources)

        st.session_state.history.append(
            {"role": "assistant", "content": text, "sources": sources}
        )