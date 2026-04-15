FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 1. системные зависимости
RUN apt update && apt install -y \
    curl \
    python3 \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. установка uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY . .

RUN uv venv
RUN uv sync

CMD ["uv", "run", "gunicorn", "-b", "0.0.0.0:8000", "main:app"]