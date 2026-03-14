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
  created_at TIMESTAMP NOT NULL,
  status TEXT NOT NULL DEFAULT 'not_publishable',
  publishability_reason TEXT,
  keypoints_generated_at TIMESTAMP,
  quiz_status TEXT,
  quiz_unavailable_reason TEXT,
  quiz_pool_version INTEGER,
  quiz_updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS story_sources (
  story_source_id TEXT PRIMARY KEY,
  story_id TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  canonical_url TEXT,
  publisher_domain TEXT NOT NULL,
  FOREIGN KEY (story_id) REFERENCES stories(story_id)
);

CREATE TABLE IF NOT EXISTS story_key_points (
  key_point_id TEXT PRIMARY KEY,
  story_id TEXT NOT NULL,
  position INTEGER NOT NULL,
  text TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  UNIQUE (story_id, position),
  FOREIGN KEY (story_id) REFERENCES stories(story_id)
);

CREATE TABLE IF NOT EXISTS dedup_registry (
  dedup_key TEXT PRIMARY KEY,
  story_id TEXT NOT NULL,
  raw_id TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS quizzes (
  quiz_id TEXT PRIMARY KEY,
  story_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  question_pool_size INTEGER NOT NULL,
  pool_signature TEXT,
  generator_version TEXT,
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
CREATE INDEX IF NOT EXISTS idx_story_key_points_story_position ON story_key_points(story_id, position);

-- v0.2 data monetization layer

CREATE TABLE IF NOT EXISTS quiz_questions (
  question_id TEXT PRIMARY KEY,
  quiz_id TEXT NOT NULL,
  question_text TEXT NOT NULL,
  task_type TEXT NOT NULL DEFAULT 'comprehension',
  options_json TEXT,
  correct_option_id TEXT,
  annotation_campaign_id TEXT,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id)
);

CREATE TABLE IF NOT EXISTS reading_sessions (
  session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  story_id TEXT NOT NULL,
  topic_slug TEXT NOT NULL,
  started_at TIMESTAMP NOT NULL,
  scroll_depth INTEGER,
  active_seconds INTEGER,
  total_seconds INTEGER,
  device_type TEXT,
  locale TEXT,
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  FOREIGN KEY (story_id) REFERENCES stories(story_id)
);

CREATE TABLE IF NOT EXISTS quiz_qa_pairs (
  pair_id TEXT PRIMARY KEY,
  story_id TEXT NOT NULL,
  quiz_id TEXT NOT NULL,
  question_id TEXT NOT NULL,
  question_text TEXT NOT NULL,
  correct_answer TEXT NOT NULL,
  distractor_a TEXT NOT NULL,
  distractor_b TEXT NOT NULL,
  topic_slug TEXT NOT NULL,
  difficulty INTEGER,
  avg_human_score FLOAT,
  attempt_count INTEGER DEFAULT 0,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (story_id) REFERENCES stories(story_id),
  FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id),
  FOREIGN KEY (question_id) REFERENCES quiz_questions(question_id)
);

CREATE TABLE IF NOT EXISTS comprehension_events (
  event_id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL,
  session_id TEXT,
  question_id TEXT NOT NULL,
  chosen_option_id TEXT NOT NULL,
  is_correct BOOLEAN NOT NULL,
  elapsed_ms INTEGER NOT NULL,
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (attempt_id) REFERENCES attempts(attempt_id),
  FOREIGN KEY (session_id) REFERENCES reading_sessions(session_id),
  FOREIGN KEY (question_id) REFERENCES quiz_questions(question_id)
);

CREATE TABLE IF NOT EXISTS annotation_tasks (
  task_id TEXT PRIMARY KEY,
  campaign_id TEXT NOT NULL,
  question_id TEXT NOT NULL,
  task_type TEXT NOT NULL,
  buyer_org TEXT,
  payout_per_label NUMERIC(10, 4),
  min_labels INTEGER DEFAULT 5,
  status TEXT DEFAULT 'active',
  created_at TIMESTAMP NOT NULL,
  FOREIGN KEY (question_id) REFERENCES quiz_questions(question_id)
);

CREATE TABLE IF NOT EXISTS story_analytics (
  analytics_id TEXT PRIMARY KEY,
  story_id TEXT NOT NULL,
  date DATE NOT NULL,
  box_viewed INTEGER DEFAULT 0,
  quiz_started INTEGER DEFAULT 0,
  quiz_passed INTEGER DEFAULT 0,
  comment_submitted INTEGER DEFAULT 0,
  comment_accepted INTEGER DEFAULT 0,
  avg_active_seconds FLOAT,
  avg_scroll_depth FLOAT,
  comprehension_score FLOAT,
  engagement_score FLOAT,
  UNIQUE (story_id, date),
  FOREIGN KEY (story_id) REFERENCES stories(story_id)
);

CREATE TABLE IF NOT EXISTS topic_interest_weekly (
  week_start DATE NOT NULL,
  topic_slug TEXT NOT NULL,
  locale TEXT NOT NULL,
  attempt_rate FLOAT,
  comprehension_score FLOAT,
  avg_read_seconds FLOAT,
  unique_readers INTEGER,
  PRIMARY KEY (week_start, topic_slug, locale)
);

CREATE INDEX IF NOT EXISTS idx_reading_sessions_story ON reading_sessions(story_id, started_at);
CREATE INDEX IF NOT EXISTS idx_qa_pairs_topic ON quiz_qa_pairs(topic_slug, created_at);
CREATE INDEX IF NOT EXISTS idx_story_analytics_date ON story_analytics(date, story_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_story_version ON quizzes(story_id, version DESC);
