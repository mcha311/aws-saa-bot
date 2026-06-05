# ── Stage 1: dependency builder ────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: runtime ─────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# copy application source
COPY . .

# SQLite DB lives in /app/data — mount this directory for persistence.
# e.g. docker run -v $(pwd)/data:/app/data aws-saa-bot
RUN mkdir -p /app/data
ENV DB_PATH=/app/data/bot.db
VOLUME ["/app/data"]

ENTRYPOINT ["python", "bot.py"]
