FROM python:3.12-slim

# Устанавливаем системные зависимости для WeasyPrint (Pango, GLib, HarfBuzz) и шрифты с кириллицей
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libharfbuzz-subset0 \
    libglib2.0-0 \
    libfontconfig1 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Копируем оба файла зависимостей (если uv.lock есть, сборка будет быстрее и воспроизводимее)
COPY pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-dev --no-cache || uv sync --no-dev --no-cache

COPY ./app /app/app

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
