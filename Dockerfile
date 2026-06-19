FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./

RUN uv sync --no-dev --frozen

COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/
COPY agent_config.yaml ./agent_config.yaml

EXPOSE 8000

CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
