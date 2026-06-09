"""
StudyOS — AI-powered study companion
Supabase edition  |  Streamlit app
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st

# ── page config (must be first Streamlit call) ────────────────────────────────

st.set_page_config(
    page_title="StudyOS",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── optional deps ─────────────────────────────────────────────────────────────

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

from db import (
    sign_in, sign_up, sign_out, restore_session,
    get_profile,
    save_message, load_messages, clear_messages,
    get_or_create_deck, save_flashcards, load_flashcards,
    load_decks, delete_flashcard, delete_deck,
    save_pdf_summary, load_pdf_summaries,
)

# ── global CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.flip-inner {
    padding: 1.8rem 1.5rem;
    border-radius: 12px;
    border: 1px solid rgba(128,128,128,0.25);
    background: var(--secondary-background-color);
    min-height: 110px;
}
.card-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    opacity: 0.4;
    margin-bottom: 0.5rem;
}
.card-text { font-size: 1.1rem; line-height: 1.55; }
.pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    background: rgba(99,102,241,0.12);
    color: #6366f1;
    font-size: 0.76rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ── session state defaults ────────────────────────────────────────────────────

DEFAULTS: Dict[str, Any] = {
    # auth
    "user": None,
    "access_token": None,
    "refresh_token": None,
    # ui state
    "room": "Room A",
    "model": "brewster-medium",
    "temperature": 0.2,
    # flashcard ui
    "fc_deck_id": None,
    "fc_deck_name": "Default",
    "fc_cards": [],
    "fc_index": 0,
    "fc_show_back": False,
    # scratch buffers
    "last_user_message": "",
    "ocr_text": "",
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── AI backend ────────────────────────────────────────────────────────────────

def ask_ai(prompt: str) -> Dict[str, Any]:
    """Call BrewsterAI or fall back to a demo response."""
    try:
        from brewster_client import call_brewster
        return call_brewster(
            prompt,
            model=st.session_state.model,
            temperature=st.session_state.temperature,
        )
    except RuntimeError as e:
        st.warning(f"BrewsterAI not configured: {e}. Running in demo mode.")
    except Exception as e:
        st.error(f"BrewsterAI error: {e}")

    sentences = [s.strip() for s in prompt.replace("\n", " ").split(".") if len(s.strip()) > 20]
    answer = (
        f"**Demo mode** — Here's a study response.\n\n"
        f"_{sentences[0] if sentences else prompt[:120]}_\n\n"
        "Set `BREWSTER_API_KEY` in your Streamlit secrets for real AI responses."
    )
    flashcards = [
        {"front": f"What does this mean? — {s[:80]}", "back": f"Explanation: {s[:160]}"}
        for s in sentences[:4]
    ]
    summary = " ".join(sentences[:3]) + ("…" if len(sentences) > 3 else "")
    return {"answer": answer, "flashcards": flashcards, "summary": summary or prompt[:200]}

# ── PDF / OCR helpers ─────────────────────────────────────────────────────────

def extract_image_text(uploaded_file) -> str:
    if not OCR_AVAILABLE:
        st.error("Install Pillow + pytesseract and the system Tesseract binary.")
        return ""
    try:
        return pytesseract.image_to_string(Image.open(uploaded_file)).strip()
    except Exception as e:
        st.error(f"OCR failed: {e}")
        return ""

# ── Auth helpers ──────────────────────────────────────────────────────────────

def current_user() -> Optional[dict]:
    return st.session_state.get("user")


def require_auth() -> bool:
    """Return True if the user is logged in, else render the auth wall."""
    user = current_user()

    # Try to restore from stored tokens on first load
    if not user and st.session_state.get("access_token"):
        user = restore_session(
            st.session_state.access_token,
            st.session_state.refresh_token or "",
        )
        if user:
            st.session_state.user = user

    return user is not None


def render_auth_wall():
    """Render the login / sign-up form when the user is not authenticated."""
    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("## 🎓 StudyOS")
        st.markdown("Your AI-powered study companion. Sign in to get started.")
        st.divider()

        mode = st.radio("", ["Sign in", "Create account"], horizontal=True, label_visibility="collapsed")

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if mode == "Create account":
            username = st.text_input("Display name")
            if st.button("Create account", type="primary", use_container_width=True):
                if not email or not password or not username:
                    st.warning("All fields are required.")
                    return
                try:
                    res = sign_up(email, password, username)
                    if res.user:
                        st.success("Account created! You can sign in now.")
                    else:
                        st.error("Sign-up failed. Try a different email.")
                except Exception as e:
                    st.error(f"Sign-up error: {e}")
        else:
            if st.button("Sign in", type="primary", use_container_width=True):
                if not email or not password:
                    st.warning("Email and password required.")
                    return
                try:
                    res = sign_in(email, password)
                    if res.user and res.session:
                        st.session_state.user = res.user
                        st.session_state.access_token = res.session.access_token
                        st.session_state.refresh_token = res.session.refresh_token
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")
                except Exception as e:
                    st.error(f"Sign-in error: {e}")

# ── Flashcard helpers ─────────────────────────────────────────────────────────

def ensure_deck(user_id: str) -> str:
    """Make sure a deck exists in DB and is cached in session state."""
    if not st.session_state.fc_deck_id:
        deck_id = get_or_create_deck(user_id, st.session_state.fc_deck_name)
        st.session_state.fc_deck_id = deck_id
        st.session_state.fc_cards = load_flashcards(user_id, deck_id)
    return st.session_state.fc_deck_id


def add_cards_to_deck(user_id: str, cards: List[dict]) -> None:
    """Save new cards to DB and append to local cache."""
    deck_id = ensure_deck(user_id)
    save_flashcards(user_id, deck_id, cards)
    # Reload from DB to get server-assigned IDs
    st.session_state.fc_cards = load_flashcards(user_id, deck_id)


def render_flashcard_ui(user_id: str):
    cards = st.session_state.fc_cards
    if not cards:
        st.info("No flashcards yet. Generate some from the AI Assistant or PDF Summary tabs.")
        return

    idx = st.session_state.fc_index
    total = len(cards)
    idx = max(0, min(idx, total - 1))   # clamp after deletions
    st.session_state.fc_index = idx
    card = cards[idx]

    st.markdown(f'<span class="pill">Card {idx + 1} of {total}</span>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col_f, col_b = st.columns(2)
    with col_f:
        st.markdown(
            f'<div class="flip-inner"><div class="card-label">Question</div>'
            f'<div class="card-text">{card["front"]}</div></div>',
            unsafe_allow_html=True,
        )
    with col_b:
        if st.session_state.fc_show_back:
            st.markdown(
                f'<div class="flip-inner"><div class="card-label">Answer</div>'
                f'<div class="card-text">{card["back"]}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="flip-inner" style="display:flex;align-items:center;'
                'justify-content:center;"><div class="card-label" style="margin:0">'
                'Tap reveal to show answer</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3, _, c4 = st.columns([1, 1.5, 1, 2, 1.5])
    with c1:
        if st.button("← Prev", use_container_width=True, disabled=(idx == 0)):
            st.session_state.fc_index -= 1
            st.session_state.fc_show_back = False
            st.rerun()
    with c2:
        label = "Hide answer" if st.session_state.fc_show_back else "Reveal answer"
        if st.button(label, use_container_width=True):
            st.session_state.fc_show_back = not st.session_state.fc_show_back
            st.rerun()
    with c3:
        if st.button("Next →", use_container_width=True, disabled=(idx == total - 1)):
            st.session_state.fc_index += 1
            st.session_state.fc_show_back = False
            st.rerun()
    with c4:
        if st.button("🗑 Delete", use_container_width=True):
            delete_flashcard(card["id"], user_id)
            st.session_state.fc_cards.pop(idx)
            st.session_state.fc_index = max(0, idx - 1)
            st.session_state.fc_show_back = False
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if not require_auth():
    render_auth_wall()
    st.stop()

user = current_user()
user_id: str = user.id
try:
    profile = get_profile(user_id) or {}
    username: str = profile.get("username") or user.email.split("@")[0]
except Exception:
    profile = {}
    username: str = user.email.split("@")[0]

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"## 🎓 StudyOS")
    st.markdown(f"👋 **{username}**")
    st.divider()

    st.session_state.room = st.selectbox(
        "Study room",
        ["Room A", "Room B", "Personal", "Exam Prep"],
        index=["Room A", "Room B", "Personal", "Exam Prep"].index(st.session_state.room),
    )

    st.divider()
    st.markdown("#### Model settings")
    st.session_state.model = st.selectbox(
        "Model",
        ["brewster-small", "brewster-medium", "brewster-large"],
        index=["brewster-small", "brewster-medium", "brewster-large"].index(st.session_state.model),
    )
    st.session_state.temperature = st.slider("Response Variation", 0.0, 1.0, st.session_state.temperature, step=0.05)

    st.divider()

    # Deck selector
    st.markdown("#### Flashcard deck")
    decks = load_decks(user_id)
    deck_names = [d["name"] for d in decks] + ["+ New deck"]
    current_deck_idx = next(
        (i for i, d in enumerate(decks) if d["name"] == st.session_state.fc_deck_name), 0
    )
    chosen = st.selectbox("Active deck", deck_names, index=current_deck_idx)

    if chosen == "+ New deck":
        new_name = st.text_input("New deck name", key="new_deck_input")
        if st.button("Create deck") and new_name.strip():
            st.session_state.fc_deck_name = new_name.strip()
            st.session_state.fc_deck_id = None
            st.session_state.fc_cards = []
            st.session_state.fc_index = 0
            ensure_deck(user_id)
            st.rerun()
    elif chosen != st.session_state.fc_deck_name:
        # Switch deck
        matched = next((d for d in decks if d["name"] == chosen), None)
        if matched:
            st.session_state.fc_deck_name = matched["name"]
            st.session_state.fc_deck_id = matched["id"]
            st.session_state.fc_cards = load_flashcards(user_id, matched["id"])
            st.session_state.fc_index = 0
            st.session_state.fc_show_back = False
            st.rerun()

    st.metric("Cards in deck", len(st.session_state.fc_cards))

    if st.session_state.fc_deck_id and st.button("🗑 Delete this deck", type="secondary"):
        delete_deck(st.session_state.fc_deck_id, user_id)
        st.session_state.fc_deck_id = None
        st.session_state.fc_cards = []
        st.session_state.fc_index = 0
        st.session_state.fc_deck_name = "Default"
        st.rerun()

    st.divider()
    if st.button("Sign out"):
        sign_out()
        st.rerun()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_chat, tab_cards, tab_ocr, tab_history = st.tabs([
    "💬 AI Study Assistant",
    "🃏 Flashcards",
    "🖼 Image Notes",
    "📚 Past Summaries",
])

# ╔══════════════════════════════╗
# ║   Tab 1 — AI Study Assistant ║
# ╚══════════════════════════════╝

with tab_chat:
    st.markdown(f"### Good to see you, {username} 👋")

    room = st.session_state.room

    # Load chat from Supabase on first render for this room
    cache_key = f"chat_loaded_{room}"
    if not st.session_state.get(cache_key):
        db_msgs = load_messages(user_id, room)
        st.session_state[f"chat_{room}"] = db_msgs
        st.session_state[cache_key] = True

    chat_key = f"chat_{room}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    # Render history
    for msg in st.session_state[chat_key]:
        avatar = "🙂" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["message"])

    # Quick actions
    qa_cols = st.columns(4)
    quick_actions = {
        "📝 Summarize": "Summarize the following in clear bullet points:\n\n",
        "🔍 Explain": "Explain this concept simply, as if I'm a student:\n\n",
        "🃏 Make flashcards": "Generate 5 flashcards (Q&A pairs) from this text:\n\n",
        "❓ Quiz me": "Give me 3 multiple-choice questions based on this text:\n\n",
    }
    triggered_prefix = None
    for col, (label, prefix) in zip(qa_cols, quick_actions.items()):
        if col.button(label, use_container_width=True):
            triggered_prefix = prefix

    user_input = st.chat_input("Ask a question or paste notes to study…")

    if triggered_prefix:
        context = st.session_state.last_user_message
        if not context:
            st.warning("Type a message first or upload a PDF so I have content to work with.")
        else:
            user_input = triggered_prefix + context

    if user_input:
        st.session_state.last_user_message = user_input
        st.session_state[chat_key].append({"role": "user", "message": user_input})
        save_message(user_id, room, "user", user_input)

        with st.chat_message("user", avatar="🙂"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking…"):
                resp = ask_ai(user_input)
            answer = resp.get("answer", "")
            st.markdown(answer)
            st.session_state[chat_key].append({"role": "assistant", "message": answer})
            save_message(user_id, room, "assistant", answer)

            new_cards = resp.get("flashcards", [])
            if new_cards:
                add_cards_to_deck(user_id, new_cards)
                st.success(f"✅ Added {len(new_cards)} flashcard(s) to **{st.session_state.fc_deck_name}**.")

        st.rerun()

    if st.session_state[chat_key]:
        if st.button("Clear chat history", type="secondary"):
            clear_messages(user_id, room)
            st.session_state[chat_key] = []
            st.session_state[cache_key] = True
            st.rerun()

# ╔══════════════════════╗
# ║   Tab 3 — Flashcards ║
# ╚══════════════════════╝

with tab_cards:
    # Ensure the deck is loaded
    ensure_deck(user_id)
    st.markdown(f"### Deck: {st.session_state.fc_deck_name}")
    render_flashcard_ui(user_id)

    st.divider()
    with st.expander("➕ Add a card manually"):
        front = st.text_input("Question / front", key="manual_front")
        back = st.text_area("Answer / back", key="manual_back", height=100)
        if st.button("Add card"):
            if front.strip() and back.strip():
                add_cards_to_deck(user_id, [{"front": front.strip(), "back": back.strip()}])
                st.success("Card added!")
                st.rerun()
            else:
                st.warning("Both fields are required.")

# ╔═══════════════════════╗
# ║   Tab 4 — Image Notes ║
# ╚═══════════════════════╝

with tab_ocr:
    st.markdown("### Upload an image of your notes")

    if not OCR_AVAILABLE:
        st.warning(
            "OCR requires `Pillow`, `pytesseract`, and the system `tesseract` binary. "
            "Add them to your requirements and packages.txt (see README)."
        )

    uploaded_img = st.file_uploader(
        "Choose an image (PNG, JPG, WEBP)", type=["png", "jpg", "jpeg", "webp"], key="img_uploader"
    )

    if uploaded_img:
        st.image(uploaded_img, caption="Uploaded image", use_column_width=True)

        if OCR_AVAILABLE:
            with st.spinner("Running OCR…"):
                ocr_text = extract_image_text(uploaded_img)
                st.session_state.ocr_text = ocr_text

            if ocr_text:
                st.success(f"OCR extracted ~{len(ocr_text.split())} words")
                with st.expander("Extracted text"):
                    st.text(ocr_text)

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("✨ Summarize notes", use_container_width=True, type="primary"):
                        with st.spinner("Summarizing…"):
                            resp = ask_ai(f"Summarize these handwritten notes:\n\n{ocr_text}")
                        summary_text = resp.get("summary") or resp.get("answer", "")
                        st.markdown("#### Summary")
                        st.markdown(summary_text)
                        save_pdf_summary(user_id, uploaded_img.name, ocr_text, summary_text)
                        st.caption("✅ Summary saved to your history.")
                        if resp.get("flashcards"):
                            add_cards_to_deck(user_id, resp["flashcards"])
                with col_b:
                    if st.button("🃏 Flashcards from notes", use_container_width=True):
                        with st.spinner("Generating flashcards…"):
                            resp = ask_ai(f"Generate 6 flashcards from these notes:\n\n{ocr_text}")
                        new_cards = resp.get("flashcards", [])
                        if new_cards:
                            add_cards_to_deck(user_id, new_cards)
                            st.success(f"Added {len(new_cards)} flashcards.")
            else:
                st.warning("No text detected. Try a clearer or higher-resolution image.")

# ╔══════════════════════════╗
# ║   Tab 5 — Past Summaries ║
# ╚══════════════════════════╝

with tab_history:
    st.markdown("### Your saved summaries")
    summaries = load_pdf_summaries(user_id)

    if not summaries:
        st.info("No summaries yet. Summarize a PDF or image to see them here.")
    else:
        for s in summaries:
            with st.expander(f"📄 {s['filename']}  —  {s['created_at'][:10]}"):
                st.markdown(s["summary"])
