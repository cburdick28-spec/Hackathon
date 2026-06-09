import io
import json
from typing import List, Dict

import streamlit as st

# Optional: import PyPDF2 when available
try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None


# ----------------------
# Helper AI / PDF funcs
# ----------------------

def ask_ai(prompt: str) -> Dict:
    """
    Calls the BrewsterAI client if available, otherwise falls back to a mocked response.
    Returns the normalized structure: {"answer": str, "flashcards": [...], "summary": str}
    """
    try:
        from brewster_client import call_brewster
    except Exception:
        call_brewster = None

    model = st.session_state.get("model", "brewster-medium")
    temperature = st.session_state.get("temperature", 0.2)

    if call_brewster:
        try:
            return call_brewster(prompt, model=model, temperature=temperature)
        except Exception as e:
            st.error(f"Brewster API error: {e}")

    # Fallback mocked response for local development
    answer = f"AI response to: {prompt}"
    sentences = [s.strip() for s in prompt.split('.') if s.strip()]
    flashcards = []
    for i, s in enumerate(sentences[:4]):
        flashcards.append({"front": f"Q: {s[:60]}", "back": f"A: Explain {s[:120]}"})

    summary = (" ".join(sentences[:3]) + "...") if sentences else "No content to summarize."

    return {"answer": answer, "flashcards": flashcards, "summary": summary}


def extract_pdf_text(uploaded_file) -> str:
    """
    Extract text from a PDF uploaded_file (Streamlit UploadedFile).
    Uses PyPDF2 if available.
    """
    if PdfReader is None:
        st.warning("PyPDF2 not installed. Install with `pip install PyPDF2` to enable PDF extraction.")
        return ""

    try:
        # PdfReader accepts a file-like object
        reader = PdfReader(uploaded_file)
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                texts.append("")
        return "\n\n".join(texts)
    except Exception:
        try:
            # fallback: read bytes and use BytesIO
            data = uploaded_file.read()
            reader = PdfReader(io.BytesIO(data))
            texts = [p.extract_text() or "" for p in reader.pages]
            return "\n\n".join(texts)
        except Exception as e:
            st.error(f"Failed to extract PDF text: {e}")
            return ""


# ----------------------
# Flashcards renderer
# ----------------------

def render_flashcards(flashcards: List[Dict]):
    if not flashcards:
        st.info("No flashcards available. Generate some from the AI assistant or PDF tab.")
        return

    if "flashcard_index" not in st.session_state:
        st.session_state.flashcard_index = 0

    idx = st.session_state.flashcard_index
    total = len(flashcards)

    card = flashcards[idx]

    cols = st.columns(2)
    with cols[0]:
        st.markdown("**Front**")
        st.write(card.get("front", ""))
    with cols[1]:
        st.markdown("**Back**")
        st.write(card.get("back", ""))

    nav_cols = st.columns([1, 1, 1])
    if nav_cols[0].button("Previous"):
        st.session_state.flashcard_index = max(0, idx - 1)
    if nav_cols[2].button("Next"):
        st.session_state.flashcard_index = min(total - 1, idx + 1)

    st.caption(f"Card {idx+1} / {total}")


# ----------------------
# App initialization
# ----------------------

st.set_page_config(page_title="Study Assistant MVP", layout="wide")

# initialize session_state keys
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of {role: 'user'|'assistant', 'message': str}
if "flashcards" not in st.session_state:
    st.session_state.flashcards = []
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "last_user_message" not in st.session_state:
    st.session_state.last_user_message = ""

# Sidebar
with st.sidebar:
    st.title("Study Room")
    username = st.text_input("Username", value=st.session_state.get("username", "Student"))
    st.session_state.username = username

    room = st.selectbox("Study room (local)", options=["Room A", "Room B", "Personal"])
    st.session_state.room = room

    st.markdown("---")
    st.markdown("### Model settings")
    model_name = st.selectbox("Model", options=["brewster-small", "brewster-medium", "brewster-large"])
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2)

    st.session_state.model = model_name
    st.session_state.temperature = temperature

# Main layout with tabs
tabs = st.tabs(["AI Study Assistant", "PDF Summary", "Flashcards"])

# ----------------------
# AI Study Assistant tab
# ----------------------
with tabs[0]:
    st.header("AI Study Assistant")

    # render chat history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.chat_message("user", avatar="🙂").write(msg["message"])
        else:
            st.chat_message("assistant", avatar="🤖").write(msg["message"])

    # chat input
    user_input = st.chat_input("Ask a question or paste text to work from")

    # quick actions
    qa_cols = st.columns(4)
    actions = ["Summarize", "Explain", "Flashcards", "Quiz Me"]
    pressed_action = None
    for c, a in zip(qa_cols, actions):
        if c.button(a):
            pressed_action = a

    # handle normal chat submission
    if user_input:
        st.session_state.chat_history.append({"role": "user", "message": user_input})
        st.session_state.last_user_message = user_input

        with st.spinner("Querying AI..."):
            resp = ask_ai(user_input)

        st.session_state.chat_history.append({"role": "assistant", "message": resp.get("answer", "")})

        # store flashcards if provided
        if resp.get("flashcards"):
            st.session_state.flashcards.extend(resp.get("flashcards"))

        st.experimental_rerun()

    # handle quick-action buttons
    if pressed_action:
        prompt = pressed_action + ": " + (st.session_state.last_user_message or "Please summarize the last message.")
        st.session_state.chat_history.append({"role": "user", "message": prompt})
        with st.spinner(f"Performing {pressed_action}..."):
            resp = ask_ai(prompt)
        st.session_state.chat_history.append({"role": "assistant", "message": resp.get("answer", "")})
        if resp.get("flashcards"):
            st.session_state.flashcards.extend(resp.get("flashcards"))
        st.experimental_rerun()


# ----------------------
# PDF Summary tab
# ----------------------
with tabs[1]:
    st.header("PDF Summary")
    uploaded = st.file_uploader("Upload a PDF", type=["pdf"])
    if uploaded:
        st.info("Extracting text from PDF...")
        text = extract_pdf_text(uploaded)
        st.session_state.pdf_text = text

        if text:
            st.subheader("Extracted text (preview)")
            st.text_area("pdf_preview", value=text[:2000], height=300)

            if st.button("Summarize PDF with AI"):
                with st.spinner("Summarizing..."):
                    resp = ask_ai(text)
                st.subheader("Summary")
                st.write(resp.get("summary", ""))
                if resp.get("flashcards"):
                    st.session_state.flashcards.extend(resp.get("flashcards"))
                    st.success(f"Saved {len(resp.get('flashcards'))} flashcards to session.")


# ----------------------
# Flashcards tab
# ----------------------
with tabs[2]:
    st.header("Flashcards")
    render_flashcards(st.session_state.flashcards)

    if st.session_state.flashcards:
        if st.button("Clear flashcards"):
            st.session_state.flashcards = []
            st.session_state.flashcard_index = 0
            st.experimental_rerun()


# Footer / usage hint
st.write("\n---\nBuilt as an MVP. Replace ask_ai() with a BrewsterAI client and install PyPDF2 for PDF extraction.")
