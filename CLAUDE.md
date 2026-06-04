# CLAUDE.md — AWS SAA-C03 Study Bot

## 프로젝트 개요

AWS SAA-C03 시험 준비용 Discord 봇. OpenRouter LLM으로 문제를 생성하고 SQLite로 학습 기록을 관리한다.

## 기술 스택

- Python 3.11+, discord.py 2.x
- OpenRouter API — 무료 모델, 자동 폴백
- SQLite + aiosqlite
- boto3 mock 레이어
