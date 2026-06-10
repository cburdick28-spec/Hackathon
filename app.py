"""
StudyOS — AI-powered study companion
Supabase edition  |  Streamlit app
"""

from __future__ import annotations

import io
import time
from typing import Any, Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components

# ── page config (must be first Streamlit call) ────────────────────────────────

st.set_page_config(
    page_title="StudyOS",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── optional deps ─────────────────────────────────────────────────────────────

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

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
/* ── Sidebar ──────────────────────────────────────────────────── */
section[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(160deg, #1e1b4b 0%, #312e81 60%, #4c1d95 100%);
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] div { color: #e0e7ff; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #fff !important; }
section[data-testid="stSidebar"] hr { border-color: rgba(165,180,252,0.2); }
section[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 10px 14px;
    border: 1px solid rgba(165,180,252,0.15);
}
section[data-testid="stSidebar"] [data-testid="stMetricValue"] { color: #a5b4fc !important; }

/* ── Tabs ─────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    border-bottom: 2px solid rgba(99,102,241,0.15);
    padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px 10px 0 0;
    padding: 10px 18px;
    font-weight: 600;
    font-size: 0.88rem;
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: rgba(99,102,241,0.08) !important;
    border-bottom: 3px solid #6366f1 !important;
    color: #6366f1 !important;
}

/* ── Buttons ──────────────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    border: none;
    border-radius: 10px;
    color: #fff;
    font-weight: 600;
    box-shadow: 0 2px 8px rgba(99,102,241,0.35);
    transition: all 0.2s;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(99,102,241,0.45);
}
.stButton > button[kind="secondary"] {
    border-radius: 10px;
    border: 1.5px solid rgba(99,102,241,0.3);
    color: #6366f1;
    font-weight: 500;
    transition: all 0.2s;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(99,102,241,0.06);
    border-color: #6366f1;
}
.stButton > button:not([kind]) {
    border-radius: 10px;
    font-weight: 500;
    transition: all 0.2s;
}

/* ── Inputs ───────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 10px;
    border: 1.5px solid rgba(99,102,241,0.2) !important;
    transition: border-color 0.2s;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.1) !important;
}

/* ── Expanders ────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid rgba(99,102,241,0.15) !important;
    border-radius: 12px !important;
    overflow: hidden;
}

/* ── Flashcards ───────────────────────────────────────────────── */
.flip-inner {
    padding: 1.8rem 1.5rem;
    border-radius: 14px;
    border: 1px solid rgba(99,102,241,0.18);
    background: linear-gradient(135deg, rgba(99,102,241,0.04) 0%, rgba(139,92,246,0.04) 100%);
    min-height: 120px;
    box-shadow: 0 2px 12px rgba(99,102,241,0.08);
}
.card-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #8b5cf6;
    opacity: 0.7;
    margin-bottom: 0.5rem;
}
.card-text { font-size: 1.1rem; line-height: 1.6; }

/* ── Pill / badges ────────────────────────────────────────────── */
.pill {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 999px;
    background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.12));
    color: #6366f1;
    font-size: 0.76rem;
    font-weight: 700;
    border: 1px solid rgba(99,102,241,0.2);
}
.room-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 12px;
    border-radius: 999px;
    background: rgba(99,102,241,0.08);
    color: #8b5cf6;
    font-size: 0.8rem;
    font-weight: 600;
    border: 1px solid rgba(139,92,246,0.2);
}

/* ── Section headers ──────────────────────────────────────────── */
.tab-header {
    font-size: 1.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.1rem;
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
    "ocr_filename": "",
    # timer
    "timer_duration": 5,
    "timer_end": None,
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
    except Exception:
        pass

    sentences = [s.strip() for s in prompt.replace("\n", " ").split(".") if len(s.strip()) > 20]
    answer = (
        "Hey! I'm StudyOS, your AI study companion. "
        "I'm not fully connected yet — paste in your notes or study material and I'll help you summarize, "
        "make flashcards, and quiz you once the AI backend is live."
    )
    flashcards = [
        {"front": f"Key idea: {s[:80]}", "back": s[:160]}
        for s in sentences[:4]
    ]
    summary = " ".join(sentences[:3]) + ("…" if len(sentences) > 3 else "")
    return {"answer": answer, "flashcards": flashcards, "summary": summary or prompt[:200]}

# ── PDF / OCR helpers ─────────────────────────────────────────────────────────

def extract_pdf_text(uploaded_file) -> str:
    if PdfReader is None:
        st.error("PyPDF2 not installed.")
        return ""
    try:
        reader = PdfReader(io.BytesIO(uploaded_file.read()))
        return "\n\n".join(p.extract_text() or "" for p in reader.pages).strip()
    except Exception as e:
        st.error(f"PDF extraction failed: {e}")
        return ""


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
    st.markdown('<p style="font-size:1.5rem;font-weight:900;color:#a5b4fc;margin-bottom:0">🎓 StudyOS</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:#c7d2fe;margin-top:2px">👋 &nbsp;<b>{username}</b></p>', unsafe_allow_html=True)
    st.divider()

    st.markdown("#### Study timer")
    st.session_state.timer_duration = st.radio(
        "", [5, 10, 15], horizontal=True,
        format_func=lambda x: f"{x} min",
        index=[5, 10, 15].index(st.session_state.timer_duration),
        label_visibility="collapsed",
    )
    _tc1, _tc2 = st.columns(2)
    with _tc1:
        if st.button("Start", use_container_width=True, type="primary", key="timer_start"):
            st.session_state.timer_end = time.time() + st.session_state.timer_duration * 60
    with _tc2:
        if st.button("Stop", use_container_width=True, key="timer_stop"):
            st.session_state.timer_end = None

    if st.session_state.timer_end:
        _remaining = max(0, int(st.session_state.timer_end - time.time()))
        if _remaining > 0:
            _m, _s = divmod(_remaining, 60)
            st.markdown(
                f’<p style="text-align:center;font-size:1.6rem;font-weight:900;’
                f’color:#a5b4fc;font-family:monospace;margin:4px 0">’
                f’{_m:02d}:{_s:02d}</p>’,
                unsafe_allow_html=True,
            )
        else:
            st.success("Time’s up!")
            st.session_state.timer_end = None

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

# ── Timer banner (main area) ──────────────────────────────────────────────────

if st.session_state.timer_end:
    _rem = max(0, int(st.session_state.timer_end - time.time()))
    if _rem > 0:
        components.html(
            f"""
            <div style="text-align:center;font-size:2.6rem;font-weight:900;
                        font-family:monospace;color:#6366f1;
                        padding:6px 0 2px 0;line-height:1">
                <span id="sos-timer">--:--</span>
            </div>
            <div style="text-align:center;font-size:0.78rem;color:#9ca3af;
                        letter-spacing:0.08em;text-transform:uppercase">
                Study timer
            </div>
            <script>
            (function(){{
                var end = Date.now() + {_rem} * 1000;
                function tick(){{
                    var r = Math.max(0, end - Date.now());
                    var m = Math.floor(r / 60000);
                    var s = Math.floor((r % 60000) / 1000);
                    var el = document.getElementById('sos-timer');
                    if (el) el.innerText = String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
                    if (r > 0) setTimeout(tick, 500);
                    else if (el) el.innerText = "Time’s up!";
                }}
                tick();
            }})();
            </script>
            """,
            height=70,
        )

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_chat, tab_cards, tab_ocr, tab_history = st.tabs([
    "AI Study Assistant",
    "Flashcards",
    "Image Notes",
    "Past Summaries",
])

# ╔══════════════════════════════╗
# ║   Tab 1 — AI Study Assistant ║
# ╚══════════════════════════════╝

with tab_chat:
    _head_col, _clear_col = st.columns([5, 1])
    with _head_col:
        st.markdown(f'<div class="tab-header">Good to see you, {username}</div>', unsafe_allow_html=True)
        st.markdown(f'<span class="room-badge">📍 {st.session_state.room}</span>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
    with _clear_col:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑 Clear chat", type="secondary", use_container_width=True):
            room = st.session_state.room
            clear_messages(user_id, room)
            st.session_state[f"chat_{room}"] = []
            st.session_state[f"chat_loaded_{room}"] = True
            st.rerun()

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
        try:
            save_message(user_id, room, "user", user_input)
        except Exception:
            pass

        with st.chat_message("user", avatar="🙂"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking…"):
                resp = ask_ai(user_input)
            answer = resp.get("answer", "")
            st.markdown(answer)
            st.session_state[chat_key].append({"role": "assistant", "message": answer})
            try:
                save_message(user_id, room, "assistant", answer)
            except Exception:
                pass

            new_cards = resp.get("flashcards", [])
            if new_cards:
                add_cards_to_deck(user_id, new_cards)
                st.success(f"✅ Added {len(new_cards)} flashcard(s) to **{st.session_state.fc_deck_name}**.")

        st.rerun()


# ╔══════════════════════╗
# ║   Tab 3 — Flashcards ║
# ╚══════════════════════╝

with tab_cards:
    ensure_deck(user_id)
    st.markdown(f'<div class="tab-header">{st.session_state.fc_deck_name}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
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
    st.markdown('<div class="tab-header">Notes Transcriber</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload an image or PDF of your notes",
        type=["png", "jpg", "jpeg", "webp", "pdf"],
        key="notes_uploader",
    )

    if uploaded_file:
        is_pdf = uploaded_file.name.lower().endswith(".pdf")

        # Only re-extract when a new file is uploaded — prevents stream exhaustion on reruns
        if uploaded_file.name != st.session_state.ocr_filename:
            if is_pdf:
                with st.spinner("Reading PDF…"):
                    st.session_state.ocr_text = extract_pdf_text(uploaded_file)
            else:
                if OCR_AVAILABLE:
                    with st.spinner("Running OCR…"):
                        st.session_state.ocr_text = extract_image_text(uploaded_file)
                else:
                    st.session_state.ocr_text = ""
            st.session_state.ocr_filename = uploaded_file.name

        extracted_text = st.session_state.ocr_text

        if not is_pdf:
            st.image(uploaded_file, caption="Uploaded image", use_column_width=True)
            if not OCR_AVAILABLE:
                st.warning("OCR is not available in this environment.")

        if extracted_text:
            st.success(f"Extracted ~{len(extracted_text.split()):,} words from **{uploaded_file.name}**")
            with st.expander("Preview text"):
                st.text(extracted_text[:2000] + ("…" if len(extracted_text) > 2000 else ""))
        else:
            st.warning(
                "Could not extract text. "
                + ("The PDF may be scanned — try uploading an image instead." if is_pdf
                   else "Try a clearer or higher-resolution image.")
            )

        extracted_text = st.session_state.get("ocr_text", "")
        if extracted_text:
            st.markdown("<br>", unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Summarize", use_container_width=True, type="primary"):
                    with st.spinner("Summarizing…"):
                        resp = ask_ai(f"Summarize these notes:\n\n{extracted_text[:4000]}")
                    summary_text = resp.get("summary") or resp.get("answer", "")
                    st.markdown("#### Summary")
                    st.markdown(summary_text)
                    try:
                        save_pdf_summary(user_id, uploaded_file.name, extracted_text, summary_text)
                        st.caption("Summary saved to your history.")
                    except Exception:
                        st.caption("Could not save summary — it's still shown above.")
                    if resp.get("flashcards"):
                        add_cards_to_deck(user_id, resp["flashcards"])
            with col_b:
                if st.button("Make flashcards", use_container_width=True):
                    with st.spinner("Generating flashcards…"):
                        resp = ask_ai(f"Generate 6 flashcards from these notes:\n\n{extracted_text[:4000]}")
                    new_cards = resp.get("flashcards", [])
                    if new_cards:
                        before = len(st.session_state.fc_cards)
                        add_cards_to_deck(user_id, new_cards)
                        added = len(st.session_state.fc_cards) - before
                        if added > 0:
                            st.success(f"Added {added} flashcard(s) to **{st.session_state.fc_deck_name}**.")
                        else:
                            st.warning("Cards could not be saved. Check that you are signed in and try again.")
                    else:
                        st.info("No flashcards returned — try again.")

# ╔══════════════════════════╗
# ║   Tab 5 — Past Summaries ║
# ╚══════════════════════════╝

with tab_history:
    st.markdown('<div class="tab-header">Past Summaries</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    summaries = load_pdf_summaries(user_id)

    if not summaries:
        st.info("No summaries yet. Summarize a PDF or image to see them here.")
    else:
        for s in summaries:
            with st.expander(f"📄 {s['filename']}  —  {s['created_at'][:10]}"):
                st.markdown(s["summary"])
