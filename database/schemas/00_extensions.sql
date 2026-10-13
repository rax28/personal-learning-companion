
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  google_sub TEXT UNIQUE,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT,
  display_name TEXT NOT NULL DEFAULT 'Learner',
  avatar_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS oauth_tokens (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,
  access_token TEXT,
  refresh_token TEXT,
  expires_at TIMESTAMPTZ,
  scope TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS goals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  mode TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_goals_user ON goals(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS conversations (
  id TEXT NOT NULL,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  mode TEXT NOT NULL DEFAULT 'education',
  topic TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(user_id, id)
);

CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  conversation_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('user','assistant')),
  content TEXT NOT NULL,
  topic TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY(user_id, conversation_id) REFERENCES conversations(user_id,id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_messages_user_conversation ON messages(user_id, conversation_id, created_at);

CREATE TABLE IF NOT EXISTS topics (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  mode TEXT NOT NULL,
  UNIQUE(user_id, name, mode)
);
CREATE TABLE IF NOT EXISTS concepts (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  topic_id BIGINT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  parent_id BIGINT,
  UNIQUE(user_id, topic_id, name),
  UNIQUE(user_id, id),
  FOREIGN KEY(user_id, parent_id)
    REFERENCES concepts(user_id, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_concepts_user_topic ON concepts(user_id, topic_id);

CREATE TABLE IF NOT EXISTS learning_evidence (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  conversation_id TEXT NOT NULL,
  concept_id BIGINT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
  message TEXT NOT NULL,
  type TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY(user_id, conversation_id) REFERENCES conversations(user_id,id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_evidence_user_conversation ON learning_evidence(user_id, conversation_id, created_at DESC);

CREATE TABLE IF NOT EXISTS mastery (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  concept_id BIGINT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
  understanding REAL NOT NULL DEFAULT 0,
  attempts INT NOT NULL DEFAULT 0,
  correct INT NOT NULL DEFAULT 0,
  last_seen TIMESTAMPTZ,
  PRIMARY KEY(user_id, concept_id)
);

CREATE TABLE IF NOT EXISTS connections (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  from_concept_id BIGINT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
  to_concept_id BIGINT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
  relationship TEXT NOT NULL,
  UNIQUE(user_id, from_concept_id, to_concept_id, relationship)
);

CREATE TABLE IF NOT EXISTS conversation_state (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  conversation_id TEXT NOT NULL,
  mode TEXT NOT NULL,
  topic TEXT,
  stage TEXT NOT NULL DEFAULT 'explain',
  difficulty TEXT NOT NULL DEFAULT 'easy',
  waiting_for_answer BOOLEAN NOT NULL DEFAULT false,
  pending_question TEXT,
  pending_answer TEXT,
  style_level INT NOT NULL DEFAULT 0,
  current_gap TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(user_id, conversation_id)
);

CREATE TABLE IF NOT EXISTS learner_profile (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL DEFAULT 'Learner',
  grade_level TEXT,
  goals JSONB NOT NULL DEFAULT '[]',
  preferences JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mastery_history (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  concept_id BIGINT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
  conversation_id TEXT NOT NULL,
  previous_mastery REAL NOT NULL,
  new_mastery REAL NOT NULL,
  delta REAL NOT NULL,
  signal TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY(user_id, conversation_id) REFERENCES conversations(user_id,id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS source_cache (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  source_id TEXT NOT NULL,
  label TEXT NOT NULL,
  source_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  original_bytes BIGINT NOT NULL,
  compressed_bytes BIGINT NOT NULL,
  chunks JSONB NOT NULL,
  PRIMARY KEY(user_id, source_id)
);

CREATE INDEX IF NOT EXISTS idx_source_cache_user ON source_cache(user_id, created_at DESC);
