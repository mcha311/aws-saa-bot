import json
import logging
import os
import re

import aiohttp

log = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

_FALLBACK_MODELS = [
    os.getenv("LLM_MODEL", "google/gemma-4-31b-it:free"),
    "openai/gpt-oss-20b:free",
    "google/gemma-4-31b-it:free",
    "openai/gpt-oss-120b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.2-3b-instruct:free",
]
_MODELS: list[str] = list(dict.fromkeys(_FALLBACK_MODELS))

_QUIZ_PROMPT = """\
You are an AWS Solutions Architect Associate (SAA-C03) exam question generator.

Generate ONE multiple-choice exam question about the AWS topic: {domain}

Return ONLY a valid JSON object — no markdown fences, no text outside the JSON.
Schema:
{{
  "question": "<question text>",
  "options": {{"A": "<option A>", "B": "<option B>", "C": "<option C>", "D": "<option D>"}},
  "answer": "<one letter: A|B|C|D>",
  "explanation": "<why the answer is correct and why the others are wrong>"
}}

Quality rules:
- Realistic SAA-C03 exam style, scenario-based preferred
- Exactly ONE correct answer
- All four options must be plausible AWS services or configurations
- Explanation must reference AWS official documentation concepts
"""

_EXPLAIN_PROMPT = """\
You are an AWS Solutions Architect study assistant helping someone prepare for SAA-C03.

Explain this AWS concept clearly and concisely:
Concept: {concept}

Structure your answer as:
1. What it is (1-2 sentences)
2. Key features / characteristics (3-5 bullet points)
3. Common SAA-C03 exam scenarios / use cases
4. Limits, gotchas, or tricky points to remember

Keep the total response under 420 words. Use plain text — no markdown headings.
"""


def _extract_json(raw: str) -> str:
    raw = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", raw)
    if match:
        return match.group(1).strip()
    if raw.startswith("`") and raw.endswith("`"):
        return raw.strip("`").strip()
    return raw


class _RateLimited(Exception):
    pass


async def _call_model(prompt: str, model: str, api_key: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/aws-saa-bot",
        "X-Title": "AWS SAA Study Bot",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            if resp.status == 429:
                raise _RateLimited(model)
            if not resp.ok:
                body = await resp.text()
                raise RuntimeError(f"OpenRouter {resp.status} ({model}): {body[:200]}")
            data = await resp.json()
    return data["choices"][0]["message"]["content"]


async def _call(prompt: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    last_err: Exception | None = None
    for model in _MODELS:
        try:
            log.debug("Trying model: %s", model)
            return await _call_model(prompt, model, api_key)
        except _RateLimited:
            log.warning("Rate-limited on %s, trying next model...", model)
            last_err = Exception(f"{model} rate-limited")
        except Exception as exc:
            log.warning("Error with %s: %s", model, exc)
            last_err = exc
    raise RuntimeError(f"모든 모델이 응답하지 않습니다: {last_err}")


async def generate_quiz(domain: str) -> dict:
    last_err: Exception | None = None
    for _ in range(2):
        try:
            raw = await _call(_QUIZ_PROMPT.format(domain=domain))
            parsed = json.loads(_extract_json(raw))
            for key in ("question", "options", "answer", "explanation"):
                if key not in parsed:
                    raise KeyError(f"Missing key: {key}")
            if parsed["answer"] not in ("A", "B", "C", "D"):
                raise ValueError(f"Invalid answer: {parsed['answer']}")
            return parsed
        except Exception as exc:
            last_err = exc
    raise ValueError(f"문제 생성 실패: {last_err}")


async def explain_concept(concept: str) -> str:
    return await _call(_EXPLAIN_PROMPT.format(concept=concept))
