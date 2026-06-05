import json
import pytest


@pytest.mark.asyncio
async def test_init_and_user_crud():
    from services.db import init_db, get_or_create_user
    await init_db()

    uid = await get_or_create_user(123456789, "testuser")
    assert isinstance(uid, int)

    uid2 = await get_or_create_user(123456789, "testuser")
    assert uid == uid2  # idempotent


@pytest.mark.asyncio
async def test_quiz_attempt_and_wrong_note():
    from services.db import (
        init_db, get_or_create_user, save_question,
        save_attempt, upsert_wrong_note, get_user_stats,
    )

    await init_db()
    user_id = await get_or_create_user(999, "quizuser")

    qid = await save_question(
        domain="EC2",
        content="Which instance is cheapest?",
        options_json=json.dumps({"A": "t2", "B": "c5", "C": "r5", "D": "p3"}),
        answer="A",
        explanation="t2 is the cheapest.",
    )

    await save_attempt(user_id, qid, "B", False)
    await upsert_wrong_note(user_id, qid)

    stats = await get_user_stats(user_id)
    assert stats["total"] == 1
    assert stats["correct"] == 0
    assert stats["unmastered_wrong"] == 1


@pytest.mark.asyncio
async def test_mastery_flow():
    from services.db import (
        init_db, get_or_create_user, save_question,
        upsert_wrong_note, update_mastery,
    )

    await init_db()
    user_id = await get_or_create_user(777, "masteryuser")
    qid = await save_question(
        "S3", "q?", json.dumps({"A": "a", "B": "b", "C": "c", "D": "d"}), "A", "exp"
    )

    await upsert_wrong_note(user_id, qid)

    r1 = await update_mastery(user_id, qid, is_correct=True)
    assert r1["consecutive_correct"] == 1
    assert not r1["mastered"]

    r2 = await update_mastery(user_id, qid, is_correct=True)
    assert r2["consecutive_correct"] == 2
    assert r2["mastered"]
