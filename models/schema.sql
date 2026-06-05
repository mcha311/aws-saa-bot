CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id  INTEGER UNIQUE NOT NULL,
    username    TEXT    NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    domain       TEXT NOT NULL,
    content      TEXT NOT NULL,
    options_json TEXT NOT NULL,
    answer       TEXT NOT NULL,
    explanation  TEXT NOT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attempts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    question_id  INTEGER NOT NULL REFERENCES questions(id),
    selected     TEXT    NOT NULL,
    is_correct   INTEGER NOT NULL,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wrong_notes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    question_id         INTEGER NOT NULL REFERENCES questions(id),
    wrong_count         INTEGER NOT NULL DEFAULT 1,
    last_wrong_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mastered            INTEGER NOT NULL DEFAULT 0,
    consecutive_correct INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, question_id)
);
