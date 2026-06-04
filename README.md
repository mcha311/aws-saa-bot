# AWS SAA-C03 Study Bot

AWS Solutions Architect Associate (SAA-C03) 시험 준비를 위한 Discord 스터디 봇입니다.

## 기능

| 명령어 | 설명 |
|--------|------|
| `/quiz [domain]` | LLM이 생성한 SAA-C03 4지선다 문제 풀기 |
| `/review` | 오답 노트 복습 (2회 연속 정답 시 마스터) |
| `/explain <개념>` | AWS 개념 설명 (LLM) |
| `/stats` | 개인 학습 통계 (정답률, 도메인별, 스트릭) |
| `/leaderboard` | 서버 Top 5 랭킹 |
| `/reset` | 내 기록 초기화 (확인 버튼 포함) |

매일 오전 9시 KST에 오답 노트가 있는 유저에게 DM 알림 (`DAILY_REVIEW_ENABLED=true` 시).

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `DISCORD_TOKEN` | Discord Bot 토큰 | 필수 |
| `OPENROUTER_API_KEY` | OpenRouter API 키 | 필수 |
| `LLM_MODEL` | 기본 LLM 모델 | `google/gemma-4-31b-it:free` |
| `AWS_REAL_DEPLOY` | `true` 시 실제 AWS 호출 | `false` |
| `DAILY_REVIEW_ENABLED` | 매일 DM 알림 활성화 | `false` |
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

## 기술 스택

- **Discord:** discord.py 2.x (slash commands, app_commands, tasks.loop)
- **LLM:** OpenRouter API (free tier, 자동 모델 폴백)
- **DB:** SQLite + aiosqlite
- **AWS Mock:** boto3 import 유지 + `_MockClient` 패턴
- **CI:** GitHub Actions (lint → test → docker-build)
