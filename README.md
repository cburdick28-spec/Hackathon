# StudyOS 🎓

AI-powered study companion — Supabase + Streamlit Cloud edition.

## Stack

| Layer | Tech |
|-------|------|
| UI | Streamlit |
| Auth + DB | Supabase (Postgres + GoTrue) |
| AI | BrewsterAI |
| PDF | PyPDF2 |
| OCR | Tesseract + pytesseract |

---

## Setup — 3 steps

### 1. Supabase

1. Create a free project at [supabase.com](https://supabase.com).
2. Open **SQL Editor → New query**, paste the contents of `schema.sql`, and run it.
3. Go to **Project Settings → API** and copy:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
4. Under **Authentication → Providers**, make sure **Email** is enabled.
   - For the hackathon you can disable "Confirm email" under **Auth → Email** settings
     so users can sign in immediately without a confirmation step.

### 2. Secrets

**Local dev** — create `.streamlit/secrets.toml` (already gitignored):

```toml
SUPABASE_URL      = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key"
BREWSTER_API_KEY  = "your-brewster-key"
```

**Streamlit Cloud** — go to your app → **Settings → Secrets** and paste the same key=value pairs.

### 3. Deploy to Streamlit Cloud

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select your repo, set **Main file path** to `app.py`.
4. Add your secrets (step 2).
5. Click **Deploy** — done.

Streamlit Cloud reads `requirements.txt` for Python packages and `packages.txt`
for system packages (Tesseract lives there).

---

## Local dev

```bash
pip install -r requirements.txt
# macOS: brew install tesseract
# Ubuntu: sudo apt install tesseract-ocr
streamlit run app.py
```

---

## File overview

```
app.py              Main Streamlit app (5 tabs)
db.py               Supabase client + all DB helpers
brewster_client.py  BrewsterAI HTTP wrapper
schema.sql          Run once in Supabase SQL Editor
requirements.txt    Python dependencies
packages.txt        System dependencies (Tesseract) for Streamlit Cloud
.streamlit/
  secrets.toml      Local secrets (gitignored)
```

---

## Supabase table overview

| Table | Purpose |
|-------|---------|
| `profiles` | Display names, linked to `auth.users` |
| `chat_messages` | Per-user, per-room chat history |
| `flashcard_decks` | Named decks per user |
| `flashcards` | Individual cards linked to a deck |
| `pdf_summaries` | Saved AI summaries from PDFs and images |

All tables have Row Level Security enabled — users can only access their own rows.
