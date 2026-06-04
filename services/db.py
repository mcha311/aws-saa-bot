import aiosqlite
import os
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "bot.db")
SCHEMA_PATH = Path(__file__).parent.parent / "models" / "schema.sql"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA_PATH.read_text())
        await db.commit()


async def get_or_create_user(discord_id: int, username: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM users WHERE discord_id = ?", (discord_id,)) as cur:
            row = await cur.fetchone()
        if row:
            return row[0]
        cur = await db.execute(
            "INSERT INTO users (discord_id, username) VALUES (?, ?)",
            (discord_id, username),
        )
        await db.commit()
        return cur.lastrowid


async def get_all_users() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, discord_id, username FROM users") as cur:
            rows = await cur.fetchall()
    return [{"id": r[0], "discord_id": r[1], "username": r[2]} for r in rows]


async def save_question(
    domain: str, content: str, options_json: str, answer: str, explanation: str
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO questions (domain, content, options_json, answer, explanation)"
            " VALUES (?, ?, ?, ?, ?)",
            (domain, content, options_json, answer, explanation),
        )
        await db.commit()
        return cur.lastrowid


async def save_attempt(
    user_id: int, question_id: int, selected: str, is_correct: bool
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO attempts (user_id, question_id, selected, is_correct) VALUES (?, ?, ?, ?)",
            (user_id, question_id, selected, int(is_correct)),
        )
        await db.commit()


async def upsert_wrong_note(user_id: int, question_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO wrong_notes (user_id, question_id, wrong_count, last_wrong_at)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, question_id) DO UPDATE SET
                wrong_count   = wrong_count + 1,
                last_wrong_at = CURRENT_TIMESTAMP,
                mastered      = 0
            """,
            (user_id, question_id),
        )
        await db.commit()
