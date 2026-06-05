import aiosqlite
import os
from datetime import date, timedelta
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "bot.db")
SCHEMA_PATH = Path(__file__).parent.parent / "models" / "schema.sql"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA_PATH.read_text())
        # safety net for existing DBs created before consecutive_correct was in schema.sql
        try:
            await db.execute(
                "ALTER TABLE wrong_notes ADD COLUMN"
                " consecutive_correct INTEGER NOT NULL DEFAULT 0"
            )
        except Exception:
            pass
        await db.commit()


# ── users ──────────────────────────────────────────────────────────────────────────

async def get_or_create_user(discord_id: int, username: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM users WHERE discord_id = ?", (discord_id,)
        ) as cur:
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


# ── questions ──────────────────────────────────────────────────────────────────

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


# ── attempts ───────────────────────────────────────────────────────────────────

async def save_attempt(
    user_id: int, question_id: int, selected: str, is_correct: bool
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO attempts (user_id, question_id, selected, is_correct)"
            " VALUES (?, ?, ?, ?)",
            (user_id, question_id, selected, int(is_correct)),
        )
        await db.commit()


# ── wrong_notes ────────────────────────────────────────────────────────────────

async def upsert_wrong_note(user_id: int, question_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO wrong_notes (user_id, question_id, wrong_count, last_wrong_at)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, question_id) DO UPDATE SET
                wrong_count          = wrong_count + 1,
                last_wrong_at        = CURRENT_TIMESTAMP,
                mastered             = 0,
                consecutive_correct  = 0
            """,
            (user_id, question_id),
        )
        await db.commit()


async def get_wrong_notes(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT wn.id            AS note_id,
                   wn.wrong_count,
                   wn.consecutive_correct,
                   q.id             AS question_id,
                   q.domain,
                   q.content        AS question,
                   q.options_json,
                   q.answer,
                   q.explanation
            FROM wrong_notes wn
            JOIN questions q ON q.id = wn.question_id
            WHERE wn.user_id = ? AND wn.mastered = 0
            ORDER BY wn.wrong_count DESC
            """,
            (user_id,),
        ) as cur:
            cols = [d[0] for d in cur.description]
            rows = await cur.fetchall()
    return [dict(zip(cols, row)) for row in rows]


async def update_mastery(
    user_id: int, question_id: int, is_correct: bool
) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        if is_correct:
            await db.execute(
                """
                UPDATE wrong_notes
                SET consecutive_correct = consecutive_correct + 1,
                    wrong_count         = 0
                WHERE user_id = ? AND question_id = ?
                """,
                (user_id, question_id),
            )
        else:
            await db.execute(
                """
                UPDATE wrong_notes
                SET consecutive_correct = 0,
                    wrong_count         = wrong_count + 1,
                    last_wrong_at       = CURRENT_TIMESTAMP
                WHERE user_id = ? AND question_id = ?
                """,
                (user_id, question_id),
            )

        async with db.execute(
            "SELECT consecutive_correct FROM wrong_notes"
            " WHERE user_id = ? AND question_id = ?",
            (user_id, question_id),
        ) as cur:
            row = await cur.fetchone()

        consecutive = row[0] if row else 0
        mastered = consecutive >= 2

        if mastered:
            await db.execute(
                "UPDATE wrong_notes SET mastered = 1"
                " WHERE user_id = ? AND question_id = ?",
                (user_id, question_id),
            )

        await db.commit()

    return {"mastered": mastered, "consecutive_correct": consecutive}


async def get_users_with_pending_review() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT DISTINCT u.id, u.discord_id, u.username
            FROM wrong_notes wn
            JOIN users u ON u.id = wn.user_id
            WHERE wn.mastered = 0
            """,
        ) as cur:
            rows = await cur.fetchall()
    return [{"id": r[0], "discord_id": r[1], "username": r[2]} for r in rows]


# ── stats ──────────────────────────────────────────────────────────────────────────

async def get_user_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*), COALESCE(SUM(is_correct), 0)"
            " FROM attempts WHERE user_id = ?",
            (user_id,),
        ) as cur:
            total, correct = await cur.fetchone()

        async with db.execute(
            """
            SELECT q.domain,
                   COUNT(*)                    AS total,
                   COALESCE(SUM(a.is_correct), 0) AS correct
            FROM attempts a
            JOIN questions q ON q.id = a.question_id
            WHERE a.user_id = ?
            GROUP BY q.domain
            ORDER BY total DESC
            """,
            (user_id,),
        ) as cur:
            domain_rows = await cur.fetchall()

        async with db.execute(
            "SELECT COUNT(*) FROM wrong_notes WHERE user_id = ? AND mastered = 0",
            (user_id,),
        ) as cur:
            (unmastered,) = await cur.fetchone()

        async with db.execute(
            "SELECT DISTINCT date(attempted_at) FROM attempts"
            " WHERE user_id = ? ORDER BY 1 DESC",
            (user_id,),
        ) as cur:
            date_rows = await cur.fetchall()

    # streak: consecutive days ending today or yesterday
    streak = 0
    if date_rows:
        today = date.today()
        dates = [date.fromisoformat(r[0]) for r in date_rows]
        if dates[0] >= today - timedelta(days=1):
            streak = 1
            for i in range(1, len(dates)):
                if dates[i - 1] - dates[i] == timedelta(days=1):
                    streak += 1
                else:
                    break

    return {
        "total": total,
        "correct": correct,
        "unmastered_wrong": unmastered,
        "streak": streak,
        "domain_stats": {
            domain: {"total": int(t), "correct": int(c)}
            for domain, t, c in domain_rows
        },
    }


async def get_leaderboard(
    discord_ids: list[int] | None = None, limit: int = 5
) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        if discord_ids:
            placeholders = ",".join("?" * len(discord_ids))
            query = f"""
                SELECT u.username, u.discord_id,
                       COUNT(*)                       AS total,
                       COALESCE(SUM(a.is_correct), 0) AS correct
                FROM attempts a
                JOIN users u ON u.id = a.user_id
                WHERE u.discord_id IN ({placeholders})
                GROUP BY a.user_id
                HAVING total >= 3
                ORDER BY CAST(correct AS REAL) / total DESC, total DESC
                LIMIT ?
            """
            params = [*discord_ids, limit]
        else:
            query = """
                SELECT u.username, u.discord_id,
                       COUNT(*)                       AS total,
                       COALESCE(SUM(a.is_correct), 0) AS correct
                FROM attempts a
                JOIN users u ON u.id = a.user_id
                GROUP BY a.user_id
                HAVING total >= 3
                ORDER BY CAST(correct AS REAL) / total DESC, total DESC
                LIMIT ?
            """
            params = [limit]

        async with db.execute(query, params) as cur:
            rows = await cur.fetchall()

    return [
        {"username": r[0], "discord_id": r[1], "total": r[2], "correct": r[3]}
        for r in rows
    ]


# ── admin ──────────────────────────────────────────────────────────────────────────

async def reset_user_stats(discord_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM users WHERE discord_id = ?", (discord_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return False
        user_id = row[0]
        await db.execute("DELETE FROM attempts    WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM wrong_notes WHERE user_id = ?", (user_id,))
        await db.commit()
        return True
