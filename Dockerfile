FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 1. системные зависимости
RUN sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    python3 \
    python3-pip \
    build-essential && \
    rm -rf /var/lib/apt/lists/*
# 2. установка uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY . .

RUN uv venv
RUN uv sync

CMD ["uv", "run", "gunicorn", "-b", "0.0.0.0:8000", "main:app"]
