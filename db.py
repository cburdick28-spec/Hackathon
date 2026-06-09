"""
db.py — Supabase client + all database helpers for StudyOS.

Tables expected in your Supabase project (see schema.sql for the full DDL):
  profiles        (id uuid PK → auth.users, username text, created_at)
  chat_messages   (id uuid PK, user_id uuid FK, room text, role text, message text, created_at)
  flashcard_decks (id uuid PK, user_id uuid FK, name text, created_at)
  flashcards      (id uuid PK, deck_id uuid FK, user_id uuid FK, front text, back text, created_at)
  pdf_summaries   (id uuid PK, user_id uuid FK, filename text, extracted_text text, summary text, created_at)

Row-Level Security must be enabled on every table with policies that restrict
reads/writes to rows where user_id = auth.uid().
"""

from __future__ import annotations

import streamlit as st
from supabase import create_client, Client
from typing import Optional


# ── Client singleton (cached per Streamlit session) ──────────────────────────

@st.cache_resource
def get_supabase() -> Client:
    """Return a single Supabase client reused across reruns."""
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)


# ── Auth helpers ──────────────────────────────────────────────────────────────

def sign_up(email: str, password: str, username: str = "") -> dict:
    """Register a new user. Passes username as metadata for the DB trigger."""
    client = get_supabase()
    res = client.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"username": username}},
    })
    return res


def sign_in(email: str, password: str) -> dict:
    """Sign in with email + password. Returns session/user dict."""
    client = get_supabase()
    res = client.auth.sign_in_with_password({"email": email, "password": password})
    return res


def sign_out() -> None:
    client = get_supabase()
    client.auth.sign_out()
    # Clear local session state
    for key in ("user", "access_token"):
        st.session_state.pop(key, None)


def restore_session(access_token: str, refresh_token: str) -> Optional[dict]:
    """Re-hydrate a session from stored tokens (survives page refresh)."""
    try:
        client = get_supabase()
        res = client.auth.set_session(access_token, refresh_token)
        return res.user
    except Exception:
        return None


# ── Profile helpers ───────────────────────────────────────────────────────────

def upsert_profile(user_id: str, username: str) -> None:
    client = get_supabase()
    client.table("profiles").upsert(
        {"id": user_id, "username": username},
        on_conflict="id",
    ).execute()


def get_profile(user_id: str) -> Optional[dict]:
    try:
        client = get_supabase()
        res = (
            client.table("profiles")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return res.data if res else None
    except Exception:
        return None


# ── Chat helpers ──────────────────────────────────────────────────────────────

def save_message(user_id: str, room: str, role: str, message: str) -> None:
    client = get_supabase()
    client.table("chat_messages").insert(
        {"user_id": user_id, "room": room, "role": role, "message": message}
    ).execute()


def load_messages(user_id: str, room: str, limit: int = 100) -> list[dict]:
    client = get_supabase()
    res = (
        client.table("chat_messages")
        .select("role, message, created_at")
        .eq("user_id", user_id)
        .eq("room", room)
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    return res.data or []


def clear_messages(user_id: str, room: str) -> None:
    client = get_supabase()
    client.table("chat_messages").delete().eq("user_id", user_id).eq("room", room).execute()


# ── Flashcard helpers ─────────────────────────────────────────────────────────

def get_or_create_deck(user_id: str, name: str) -> str:
    """Return the deck id for *name*, creating it if it doesn't exist."""
    client = get_supabase()
    try:
        res = (
            client.table("flashcard_decks")
            .select("id")
            .eq("user_id", user_id)
            .eq("name", name)
            .maybe_single()
            .execute()
        )
        if res and res.data:
            return res.data["id"]
    except Exception:
        pass
    ins = (
        client.table("flashcard_decks")
        .insert({"user_id": user_id, "name": name})
        .execute()
    )
    return ins.data[0]["id"]


def save_flashcards(user_id: str, deck_id: str, cards: list[dict]) -> None:
    """Bulk-insert a list of {"front": ..., "back": ...} dicts."""
    if not cards:
        return
    client = get_supabase()
    rows = [
        {"user_id": user_id, "deck_id": deck_id, "front": c["front"], "back": c["back"]}
        for c in cards
        if c.get("front") and c.get("back")
    ]
    if rows:
        client.table("flashcards").insert(rows).execute()


def load_flashcards(user_id: str, deck_id: str) -> list[dict]:
    client = get_supabase()
    res = (
        client.table("flashcards")
        .select("id, front, back, created_at")
        .eq("user_id", user_id)
        .eq("deck_id", deck_id)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []


def load_decks(user_id: str) -> list[dict]:
    client = get_supabase()
    res = (
        client.table("flashcard_decks")
        .select("id, name, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []


def delete_flashcard(card_id: str, user_id: str) -> None:
    client = get_supabase()
    client.table("flashcards").delete().eq("id", card_id).eq("user_id", user_id).execute()


def delete_deck(deck_id: str, user_id: str) -> None:
    client = get_supabase()
    client.table("flashcards").delete().eq("deck_id", deck_id).execute()
    client.table("flashcard_decks").delete().eq("id", deck_id).eq("user_id", user_id).execute()


# ── PDF summary helpers ───────────────────────────────────────────────────────

def save_pdf_summary(
    user_id: str, filename: str, extracted_text: str, summary: str
) -> None:
    client = get_supabase()
    client.table("pdf_summaries").insert(
        {
            "user_id": user_id,
            "filename": filename,
            "extracted_text": extracted_text[:50_000],   # guard against huge docs
            "summary": summary,
        }
    ).execute()


def load_pdf_summaries(user_id: str, limit: int = 20) -> list[dict]:
    client = get_supabase()
    res = (
        client.table("pdf_summaries")
        .select("id, filename, summary, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []
