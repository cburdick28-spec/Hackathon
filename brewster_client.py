"""
BrewsterAI client for StudyOS — powered by Anthropic Claude.

Set ANTHROPIC_API_KEY in:
  .streamlit/secrets.toml  (local dev)
  Streamlit Cloud → App settings → Secrets  (production)
"""

from __future__ import annotations

import json
from typing import Any, Dict

import anthropic
import streamlit as st

_MODEL_MAP = {
    "brewster-small":  "claude-haiku-4-5-20251001",
    "brewster-medium": "claude-sonnet-4-6",
    "brewster-large":  "claude-sonnet-4-6",
}

_SYSTEM = """\
You are StudyOS, a friendly AI study companion. Respond to the user and return a JSON object with exactly these three fields:

{
  "answer": "<your full markdown response to the user>",
  "flashcards": [{"front": "<question>", "back": "<answer>"}, ...],
  "summary": "<1-3 sentence plain-text summary of the key points>"
}

Rules:
- "answer": clear, educational markdown. For greetings or short questions, just answer naturally with an empty flashcards array.
- "flashcards": 3-6 cards when the input contains study material; empty array otherwise.
- "summary": brief plain-text distillation of key points; empty string for conversational turns.
- Return only valid JSON — nothing outside the JSON object.
"""


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
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if the model wraps output in ```json ... ```
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        data = json.loads(raw)
    except ValueError:
        return {"answer": raw, "flashcards": [], "summary": ""}

    valid_cards = [
        fc for fc in (data.get("flashcards") or [])
        if isinstance(fc, dict) and fc.get("front") and fc.get("back")
    ]

    return {
        "answer": str(data.get("answer") or raw),
        "flashcards": valid_cards,
        "summary": str(data.get("summary") or ""),
    }
