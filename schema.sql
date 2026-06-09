-- ============================================================
-- StudyOS — Supabase schema
-- Run this in: Supabase Dashboard → SQL Editor → New query
-- ============================================================

-- ── Extensions ──────────────────────────────────────────────
create extension if not exists "uuid-ossp";

-- ── profiles ────────────────────────────────────────────────
create table if not exists profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  username    text not null,
  created_at  timestamptz default now()
);

alter table profiles enable row level security;

create policy "Users can read own profile"
  on profiles for select using (auth.uid() = id);

create policy "Users can upsert own profile"
  on profiles for insert with check (auth.uid() = id);

create policy "Users can update own profile"
  on profiles for update using (auth.uid() = id);

-- ── chat_messages ────────────────────────────────────────────
create table if not exists chat_messages (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  room        text not null default 'Room A',
  role        text not null check (role in ('user', 'assistant')),
  message     text not null,
  created_at  timestamptz default now()
);

create index if not exists chat_messages_user_room_idx on chat_messages (user_id, room, created_at);

alter table chat_messages enable row level security;

create policy "Users can read own messages"
  on chat_messages for select using (auth.uid() = user_id);

create policy "Users can insert own messages"
  on chat_messages for insert with check (auth.uid() = user_id);

create policy "Users can delete own messages"
  on chat_messages for delete using (auth.uid() = user_id);

-- ── flashcard_decks ──────────────────────────────────────────
create table if not exists flashcard_decks (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  name        text not null default 'Default',
  created_at  timestamptz default now(),
  unique (user_id, name)
);

alter table flashcard_decks enable row level security;

create policy "Users can read own decks"
  on flashcard_decks for select using (auth.uid() = user_id);

create policy "Users can insert own decks"
  on flashcard_decks for insert with check (auth.uid() = user_id);

create policy "Users can delete own decks"
  on flashcard_decks for delete using (auth.uid() = user_id);

-- ── flashcards ───────────────────────────────────────────────
create table if not exists flashcards (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  deck_id     uuid not null references flashcard_decks(id) on delete cascade,
  front       text not null,
  back        text not null,
  created_at  timestamptz default now()
);

create index if not exists flashcards_deck_idx on flashcards (deck_id, created_at);

alter table flashcards enable row level security;

create policy "Users can read own flashcards"
  on flashcards for select using (auth.uid() = user_id);

create policy "Users can insert own flashcards"
  on flashcards for insert with check (auth.uid() = user_id);

create policy "Users can delete own flashcards"
  on flashcards for delete using (auth.uid() = user_id);

-- ── pdf_summaries ────────────────────────────────────────────
create table if not exists pdf_summaries (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  filename        text not null,
  extracted_text  text,
  summary         text not null,
  created_at      timestamptz default now()
);

alter table pdf_summaries enable row level security;

create policy "Users can read own summaries"
  on pdf_summaries for select using (auth.uid() = user_id);

create policy "Users can insert own summaries"
  on pdf_summaries for insert with check (auth.uid() = user_id);

create policy "Users can delete own summaries"
  on pdf_summaries for delete using (auth.uid() = user_id);
