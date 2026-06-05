# AWS SAA-C03 스터디 봇

> **🤖 바이브 코딩 프로젝트**
> 이 프로젝트는 코드를 한 줄도 직접 작성하지 않고, Claude와의 대화만으로 완성했습니다.

AWS Solutions Architect Associate(SAA-C03) 시험 준비용 Discord 봇.
LLM이 문제를 실시간 생성하고, 오답 노트와 마스터리 시스템으로 반복 학습을 돕습니다.

---

## 바이브 코딩이란?

> *"내가 원하는 걸 말하면 AI가 코드를 쓴다."​*

코드 작성을 AI에게 맡기고, 개발자는 **무엇을 만들지**에만 집중하는 개발 방식입니다.
이 프로젝트는 Claude Code와의 대화만으로 설계부터 배포까지 전 과정을 완성했습니다.

### 만들어진 것들

| 항목 | 내용 |
|------|------|
| Discord 슬래시 커맨드 6개 | `/quiz` `/explain` `/review` `/stats` `/leaderboard` `/reset` |
| LLM 문제 생성 | OpenRouter API + 5개 모델 자동 폴백 |
| 오답 노트 + 마스터리 | 2회 연속 정답 시 마스터 처리 |
| SQLite DB 레이어 | 유저/문제/응답/오답노트 CRUD |
| AWS Mock 레이어 | 실 배포 전 boto3 mock으로 로컈 검증 |
| CI 파이프라인 | GitHub Actions (lint → test → docker build) |
| CD 파이프라인 | Docker Hub push → EC2 SSH 배포 (변수로 on/off) |
| Docker 멀티스테이지 빌드 | 운영 이미지 최소화 |
| 테스트 코드 | pytest-asyncio, DB/LLM mock 테스트 6개 |

---

## 기능

| 명령어 | 설명 |
|--------|------|
| `/quiz [domain]` | LLM이 생성한 SAA-C03 4지선다 문제 풀기 |
| `/explain <개념>` | AWS 개념 즉시 설명 |
| `/review` | 오답 노트 복습 (2회 연속 정답 → 마스터) |
| `/stats` | 내 학습 통계 (정답률, 도메인별, 스트릭) |
| `/leaderboard` | 서버 Top 5 랜킹 |
| `/reset` | 내 기록 초기화 |

`DAILY_REVIEW_ENABLED=true` 설정 시 매일 오전 9시 KST에 오답 노트 DM 알림을 발송합니다.

---

## 아키텍처

```
Discord Client
      │
      ▼
  discord.py Bot (bot.py)
      │
      ├── cogs/quiz.py        ← /quiz, /explain
      ├── cogs/review.py      ← /review  (오답 노트)
      ├── cogs/stats.py       ← /stats, /leaderboard
      ├── cogs/admin.py       ← /reset
      └── cogs/scheduler.py   ← 매일 09:00 KST DM 알림
              │
              ├── services/llm.py        ← OpenRouter API (폴백 모델 자동 전환)
              ├── services/db.py         ← SQLite / aiosqlite CRUD
              └── services/aws_mock.py   ← boto3 mock (AWS_REAL_DEPLOY=false)
                      │
                      ├── [mock]  bot.db (SQLite)
                      └── [real]  DynamoDB / S3  (AWS_REAL_DEPLOY=true)
```

---

## 기술 스택

- **Discord:** discord.py 2.x — slash commands, Embed+View, tasks.loop
- **LLM:** OpenRouter API — 무료 모델, 5단계 자동 폴백
- **DB:** SQLite + aiosqlite — 커넥션 풀 없이 컨텔스트 매니저 패턴
- **AWS:** boto3 — `AWS_REAL_DEPLOY=false` 시 MockClient 자동 적용
- **CI/CD:** GitHub Actions — lint / test / docker-build / EC2 배포

---

## 실행

### 로컈

```bash
git clone https://github.com/mcha311/aws-saa-bot
cd aws-saa-bot

cp .env.example .env
# .env 에 DISCORD_TOKEN, OPENROUTER_API_KEY 입력

pip install -r requirements.txt
python bot.py
```

### Docker

```bash
docker build -t aws-saa-bot .
docker run --env-file .env \
  -v $(pwd)/data:/app/data \
  aws-saa-bot
```

---

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DISCORD_TOKEN` | 필수 | Discord Bot 토큰 |
| `OPENROUTER_API_KEY` | 필수 | OpenRouter API 키 |
| `LLM_MODEL` | `google/gemma-4-31b-it:free` | 1순위 LLM 모델 |
| `AWS_REAL_DEPLOY` | `false` | true 시 실제 boto3 호출 |
| `DAILY_REVIEW_ENABLED` | `false` | 매일 DM 알림 |
| `DB_PATH` | `bot.db` | SQLite 파일 경로 |

---

## 테스트

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

LLM 호출은 `unittest.mock.patch`로 mocking되어 API 키 없이 실행됩니다.

---

## CD 배포 활성화

이 레포는 CD 워크플로우가 포함되어 있지만 기본값은 비활성화 상태입니다.
실제 배포 시 GitHub 레포 **Settings → Variables → Actions** 에서 아래를 추가하세요:

| 종류 | 이름 | 값 |
|------|------|-----|
| Variable | `CD_ENABLED` | `true` |
| Secret | `DOCKERHUB_USERNAME` | Docker Hub ID |
| Secret | `DOCKERHUB_TOKEN` | Docker Hub Access Token |
| Secret | `EC2_HOST` | EC2 퍼블릭 IP |
| Secret | `EC2_USER` | `ec2-user` / `ubuntu` |
| Secret | `EC2_SSH_KEY` | PEM 키 내용 |

---

## 사용 가이드

봇 사용 방법은 [USER_GUIDE.md](USER_GUIDE.md)를 참고하세요.
