import os
import json
from typing import Dict, Any

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BREWSTER_API_KEY")
BREWSTER_URL = os.getenv("BREWSTER_API_URL", "https://api.brewster.ai/v1/generate")


def call_brewster(prompt: str, model: str = "brewster-medium", temperature: float = 0.2) -> Dict[str, Any]:
    """
    Minimal BrewsterAI client.

    Reads BREWSTER_API_KEY from environment (or .env). Sends a JSON payload and
    expects a JSON response with keys 'answer', 'flashcards', and 'summary' if
    the backend supports that. Raises RuntimeError when API key is missing.

    This file is intentionally simple — adjust to match the real BrewsterAI API.
    """
    if not API_KEY:
        raise RuntimeError("BREWSTER_API_KEY not set. Set it in your environment or .env file.")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": temperature,
        # Add other fields your API requires (max_tokens, stop, etc.)
    }

    resp = requests.post(BREWSTER_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()

    data = resp.json()

    # Normalize response into the expected structure
    if isinstance(data, dict):
        return {
            "answer": data.get("answer") or data.get("text") or json.dumps(data),
            "flashcards": data.get("flashcards") or [],
            "summary": data.get("summary") or "",
        }

    return {"answer": str(data), "flashcards": [], "summary": ""}
