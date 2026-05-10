#!/usr/bin/env python3
"""
build_store.py — Заполняет векторное хранилище RAG данными из БД.

Запускать после первого деплоя или при необходимости пересобрать индекс.

Переменные окружения:
  DATABASE_URL  — строка подключения к PostgreSQL
  RAG_URL       — URL RAG-сервиса (default: http://rag:8001)
"""

import json
import os
import sys
import urllib.request
import urllib.error


def _post(base_url: str, path: str, data: dict) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} on {path}: {e.read().decode()}", file=sys.stderr)
        return {}


def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    rag_url = os.environ.get("RAG_URL", "http://rag:8001")

    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # ── Все карточки ─────────────────────────────────────────────────────────
    cur.execute(
        "SELECT id, front_type, front_content, back_type, back_content, answer_text FROM cards"
    )
    rows = cur.fetchall()

    def row_to_card(r):
        return {
            "id": r[0],
            "front_type": r[1],
            "front_content": r[2] if r[1] == "text" else "",
            "back_type": r[3],
            "back_content": r[4] if r[3] == "text" else "",
            "answer_text": r[5] or "",
        }

    all_cards = [row_to_card(r) for r in rows]
    print(f"Found {len(all_cards)} cards total")

    result = _post(rag_url, "/build", {"scope": "all_cards", "cards": all_cards})
    print(f"all_cards store: {result}")

    # ── Подборки ──────────────────────────────────────────────────────────────
    cur.execute("SELECT id, name FROM categories")
    categories = cur.fetchall()

    for cat_id, cat_name in categories:
        cur.execute(
            """
            SELECT c.id, c.front_type, c.front_content, c.back_type, c.back_content, c.answer_text
            FROM cards c
            JOIN category_cards cc ON c.id = cc.card_id
            WHERE cc.category_id = %s
            """,
            (cat_id,),
        )
        cat_cards = [row_to_card(r) for r in cur.fetchall()]
        if cat_cards:
            result = _post(rag_url, "/build", {"scope": f"category_{cat_id}", "cards": cat_cards})
            print(f"category_{cat_id} ({cat_name!r}): {result}")

    conn.close()
    print("Done!")


if __name__ == "__main__":
    main()
