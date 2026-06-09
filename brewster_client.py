"""
BrewsterAI client for StudyOS.

Set BREWSTER_API_KEY (and optionally BREWSTER_API_URL) in
  .streamlit/secrets.toml  (local dev)
  Streamlit Cloud → App settings → Secrets  (production)

Expected API response shape:
  {
    "answer":     "<markdown reply>",
    "flashcards": [{"front": "...", "back": "..."}],
    "summary":    "<plain-text summary>"
  }
"""

from __future__ import annotations

import json
from typing import Any, Dict

import requests
import streamlit as st

BREWSTER_URL: str = st.secrets.get("BREWSTER_API_URL", "https://api.brewster.ai/v1/generate")
REQUEST_TIMEOUT = 30


def call_brewster(
    prompt: str,
    model: str = "brewster-medium",
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """
    Call the BrewsterAI API and return a normalised response dict.

    Raises:
        RuntimeError – BREWSTER_API_KEY not set in Streamlit secrets.
        requests.HTTPError – non-2xx response.
    """
    api_key: str = st.secrets.get("BREWSTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "BREWSTER_API_KEY is not set. "
            "Add it to .streamlit/secrets.toml or Streamlit Cloud secrets."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": 1024,
    }

    resp = requests.post(BREWSTER_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()

    try:
        data = resp.json()
    except ValueError:
        return {"answer": resp.text, "flashcards": [], "summary": ""}

    if not isinstance(data, dict):
        return {"answer": str(data), "flashcards": [], "summary": ""}

    answer = (
        data.get("answer")
        or data.get("text")
        or data.get("output")
        or data.get("response")
        or json.dumps(data)
    )

    raw_cards = data.get("flashcards") or []
    valid_cards = [
        fc for fc in raw_cards
        if isinstance(fc, dict) and fc.get("front") and fc.get("back")
    ]

    return {
        "answer": str(answer),
        "flashcards": valid_cards,
        "summary": str(data.get("summary") or data.get("abstract") or ""),
    }
