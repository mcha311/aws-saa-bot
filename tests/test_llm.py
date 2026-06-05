import json
import pytest
from unittest.mock import AsyncMock, patch


MOCK_QUIZ_JSON = json.dumps({
    "question": "Which EC2 instance type is optimized for memory-intensive workloads?",
    "options": {
        "A": "c5.xlarge",
        "B": "r5.xlarge",
        "C": "t3.medium",
        "D": "p3.2xlarge",
    },
    "answer": "B",
    "explanation": "R-series instances are memory optimized.",
})


@pytest.mark.asyncio
async def test_generate_quiz_parses_json():
    with patch("services.llm._call", new=AsyncMock(return_value=MOCK_QUIZ_JSON)):
        from services.llm import generate_quiz
        result = await generate_quiz("EC2")

    assert result["answer"] == "B"
    assert set(result["options"].keys()) == {"A", "B", "C", "D"}


@pytest.mark.asyncio
async def test_generate_quiz_strips_markdown_fence():
    fenced = f"```json\n{MOCK_QUIZ_JSON}\n```"
    with patch("services.llm._call", new=AsyncMock(return_value=fenced)):
        from services.llm import generate_quiz
        result = await generate_quiz("S3")

    assert result["answer"] == "B"


@pytest.mark.asyncio
async def test_generate_quiz_retries_on_bad_json():
    bad = "not json at all"
    good = MOCK_QUIZ_JSON
    call_count = 0

    async def side_effect(prompt):
        nonlocal call_count
        call_count += 1
        return bad if call_count == 1 else good

    with patch("services.llm._call", side_effect=side_effect):
        from services.llm import generate_quiz
        result = await generate_quiz("VPC")

    assert result["answer"] == "B"
    assert call_count == 2
