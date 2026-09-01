FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY fixtures ./fixtures

RUN pip install --no-cache-dir ".[api]" \
    && useradd --system --uid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin brief \
    && mkdir -p /data/traces \
    && chown -R brief:brief /data

ENV BRIEF_MEMORY_PATH=/data/memory.sqlite \
    BRIEF_TRACE_DIR=/data/traces \
    BRIEF_API_HOST=0.0.0.0 \
    BRIEF_API_PORT=8000 \
    PYTHONUNBUFFERED=1

VOLUME ["/data"]
EXPOSE 8000
USER brief

CMD ["uvicorn", "workspace_brief.api:app", "--host", "0.0.0.0", "--port", "8000"]
