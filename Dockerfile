
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

COPY bot.py ./

CMD ["uv", "run", "--frozen", "--no-sync", "python", "bot.py"]
