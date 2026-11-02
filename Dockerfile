FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.10.0 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project
COPY src/ ./src/
COPY data/synthetic/ ./data/synthetic/
RUN uv sync --no-dev && useradd -u 10001 -m app && mkdir -p runtime && chown -R app:app /app/runtime
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live',timeout=2)"
CMD [".venv/bin/uvicorn", "certflow.api:app", "--host", "0.0.0.0", "--port", "8000"]
