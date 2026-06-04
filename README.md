# AWS SAA-C03 Study Bot

AWS Solutions Architect Associate (SAA-C03) 시험 준비를 위한 Discord 스터디 봇입니다.

## 기능 (Stage 1)

| 명령어 | 설명 |
|--------|------|
| `/quiz [domain]` | LLM이 생성한 SAA-C03 4지선다 문제 풀기 |
| `/explain <개념>` | AWS 개념 설명 (LLM) |

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `DISCORD_TOKEN` | Discord Bot 토큰 | 필수 |
| `OPENROUTER_API_KEY` | OpenRouter API 키 | 필수 |
| `LLM_MODEL` | 기본 LLM 모델 | `google/gemma-4-31b-it:free` |
| `AWS_REAL_DEPLOY` | `true` 시 실제 AWS 호출 | `false` |
| `DB_PATH` | SQLite 파일 경로 | `bot.db` |

## 실행

```bash
cp .env.example .env
pip install -r requirements.txt
python bot.py
```

## 테스트

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```
