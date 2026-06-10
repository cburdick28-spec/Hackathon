"""
BrewsterAI client for StudyOS — powered by Anthropic Claude.

Set ANTHROPIC_API_KEY in:
  .streamlit/secrets.toml  (local dev)
  Streamlit Cloud → App settings → Secrets  (production)
"""

from __future__ import annotations

from typing import Any, Dict

import anthropic
import streamlit as st

_MODEL_MAP = {
    "brewster-small":  "claude-haiku-4-5-20251001",
    "brewster-medium": "claude-sonnet-4-6",
    "brewster-large":  "claude-sonnet-4-6",
}

_SYSTEM = (
    "You are StudyOS, a friendly AI study companion. "
    "Always respond using the study_response tool. "
    "If the user explicitly asks to create or generate flashcards, you MUST populate the flashcards array — never leave it empty. "
    "For greetings or simple conversational messages, return an empty flashcards array and empty summary. "
    "For study material or any explicit flashcard request, generate 4-6 flashcards and a short summary."
)

_TOOL = {
    "name": "study_response",
    "description": "Return a structured study response to the user.",
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "Full markdown response shown in chat.",
            },
            "flashcards": {
                "type": "array",
                "description": "Study flashcards. Empty array for conversational turns.",
                "items": {
                    "type": "object",
                    "properties": {
                        "front": {"type": "string"},
                        "back":  {"type": "string"},
                    },
                    "required": ["front", "back"],
                },
            },
            "summary": {
                "type": "string",
                "description": "1-3 sentence plain-text summary. Empty for conversational turns.",
            },
        },
        "required": ["answer", "flashcards", "summary"],
    },
}


def call_brewster(
    prompt: str,
    model: str = "brewster-medium",
    temperature: float = 0.2,
) -> Dict[str, Any]:
    api_key: str = st.secrets.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in Streamlit secrets.")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=_MODEL_MAP.get(model, "claude-haiku-4-5-20251001"),
        max_tokens=1024,
        temperature=temperature,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "study_response"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in message.content:
        if block.type == "tool_use" and block.name == "study_response":
            data = block.input
            valid_cards = [
                fc for fc in (data.get("flashcards") or [])
                if isinstance(fc, dict) and fc.get("front") and fc.get("back")
            ]
            return {
                "answer":     str(data.get("answer") or ""),
                "flashcards": valid_cards,
                "summary":    str(data.get("summary") or ""),
            }

    # Fallback: return any text content if tool call is missing
    for block in message.content:
        if hasattr(block, "text"):
            return {"answer": block.text, "flashcards": [], "summary": ""}

    return {"answer": "", "flashcards": [], "summary": ""}
