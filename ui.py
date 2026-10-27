"""Streamlit front end for Pagewise. Talks to the FastAPI backend."""

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Pagewise", page_icon="📄")
st.title("📄 Pagewise")
st.caption("Ask questions about your notes and get answers with page citations.")

if "history" not in st.session_state:
    st.session_state.history = []  # list of {"role", "content", "sources"}


def api_error(response: requests.Response) -> str:
    """Pull a readable message out of a failed API response."""
    try:
        return response.json().get("detail", response.text)
    except ValueError:
        return response.text


# ---------- Sidebar: upload ----------
with st.sidebar:
    st.header("Your notes")
    uploaded = st.file_uploader("Upload a PDF", type="pdf")

    if uploaded and st.button("Add to library"):
        with st.spinner("Reading and indexing..."):
            try:
                response = requests.post(
                    f"{API_URL}/upload",
                    files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                    timeout=300,
                )
                if response.ok:
                    data = response.json()
                    st.success(f"Added {data['filename']} ({data['chunks']} chunks)")
                else:
                    st.error(api_error(response))
            except requests.exceptions.ConnectionError:
                st.error("Can't reach the API. Is uvicorn running?")

    if st.button("Clear chat"):
        st.session_state.history = []
        st.rerun()

# ---------- Chat history ----------
for message in st.session_state.history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                for src in message["sources"]:
                    st.markdown(f"**{src['source']}, page {src['page']}**")
                    st.caption(src["text"])

# ---------- New question ----------
question = st.chat_input("Ask a question about your notes")

if question:
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching your notes..."):
            try:
                response = requests.post(
                    f"{API_URL}/ask", json={"question": question}, timeout=120
                )
                if response.ok:
                    data = response.json()
                    answer, sources = data["answer"], data["sources"]
                else:
                    answer, sources = f"Error: {api_error(response)}", []
            except requests.exceptions.ConnectionError:
                answer, sources = "Can't reach the API. Is uvicorn running?", []

        st.markdown(answer)
        if sources:
            with st.expander("Sources"):
                for src in sources:
                    st.markdown(f"**{src['source']}, page {src['page']}**")
                    st.caption(src["text"])

    st.session_state.history.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )