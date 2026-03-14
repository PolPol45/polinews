-- data_model_mvp.sql

CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  created_at TIMESTAMP NOT NULL,
  reputation_score INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS feed_items_raw (
  raw_id TEXT PRIMARY KEY,
  feed_id TEXT NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  title TEXT,
  snippet TEXT,
  source_name TEXT,
  source_url TEXT,
  published_at TIMESTAMP,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stories (
  story_id TEXT PRIMARY KEY,
  topic_slug TEXT NOT NULL,
  headline TEXT NOT NULL,
  summary TEXT NOT NULL,
  published_at TIMESTAMP NOT NULL,
  source_count INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS story_sources (
  story_source_id TEXT PRIMARY KEY,
  story_id TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  publisher_domain TEXT NOT NULL,
  FOREIGN KEY (story_id) REFERENCES stories(story_id)
);

CREATE TABLE IF NOT EXISTS quizzes (
  quiz_id TEXT PRIMARY KEY,
  story_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  question_pool_size INTEGER NOT NULL,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (story_id) REFERENCES stories(story_id)
);

CREATE TABLE IF NOT EXISTS attempts (
  attempt_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  story_id TEXT NOT NULL,
  quiz_id TEXT NOT NULL,
  elapsed_seconds INTEGER NOT NULL,
  score INTEGER NOT NULL,
  passed BOOLEAN NOT NULL,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  FOREIGN KEY (story_id) REFERENCES stories(story_id),
  FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id)
);

CREATE TABLE IF NOT EXISTS comments (
  comment_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  story_id TEXT NOT NULL,
  text TEXT NOT NULL,
  quality_status TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  FOREIGN KEY (story_id) REFERENCES stories(story_id)
);

CREATE TABLE IF NOT EXISTS rewards_ledger (
  entry_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  story_id TEXT,
  delta_credits INTEGER NOT NULL,
  reason TEXT NOT NULL,
  revocation_status TEXT NOT NULL DEFAULT 'none',
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS fraud_signals (
  signal_id TEXT PRIMARY KEY,
  user_id TEXT,
  story_id TEXT,
  signal_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  FOREIGN KEY (story_id) REFERENCES stories(story_id)
);

CREATE INDEX IF NOT EXISTS idx_attempts_user_story ON attempts(user_id, story_id);
CREATE INDEX IF NOT EXISTS idx_ledger_user_created ON rewards_ledger(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_fraud_status_severity ON fraud_signals(status, severity);
