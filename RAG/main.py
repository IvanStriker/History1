"""
RAG service — FastAPI-сервис для поиска по векторному хранилищу карточек.

Endpoints:
  GET  /health                  — статус и список загруженных хранилищ
  POST /search                  — поиск top-k релевантных карточек
  POST /update_card             — добавить/обновить одну карточку в all_cards
  POST /build                   — собрать/пересобрать хранилище для scope

Переменные окружения:
  MISTRAL_API_KEY  — ключ Mistral AI (для эмбеддингов)
  DATA_DIR         — папка для сохранения FAISS-индексов (default: /data)
"""

import json
import logging
import os
import pickle
from pathlib import Path

import faiss
import httpx
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("rag")

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
EMBED_URL = "https://api.mistral.ai/v1/embeddings"
EMBED_MODEL = "mistral-embed"
EMBED_DIM = 1024
EMBED_BATCH = 16

app = FastAPI(title="RAG Service")

# stores: scope_name -> {"index": faiss.Index, "meta": list[dict]}
stores: dict[str, dict] = {}


# ── Утилиты хранилища ─────────────────────────────────────────────────────────

def _scope_files(scope: str):
    safe = scope.replace("/", "_").replace("..", "")
    return DATA_DIR / f"{safe}.faiss", DATA_DIR / f"{safe}_meta.pkl"


def _load_store(scope: str) -> bool:
    fi, fm = _scope_files(scope)
    if fi.exists() and fm.exists():
        try:
            index = faiss.read_index(str(fi))
            with open(fm, "rb") as f:
                meta = pickle.load(f)
            stores[scope] = {"index": index, "meta": meta}
            logger.info(f"Loaded store '{scope}': {index.ntotal} vectors")
            return True
        except Exception as e:
            logger.error(f"Failed to load store '{scope}': {e}")
    return False


def _save_store(scope: str):
    if scope not in stores:
        return
    fi, fm = _scope_files(scope)
    faiss.write_index(stores[scope]["index"], str(fi))
    with open(fm, "wb") as f:
        pickle.dump(stores[scope]["meta"], f)


# ── Эмбеддинги через Mistral API ─────────────────────────────────────────────

def _embed(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, EMBED_DIM), dtype="float32")
    if not MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY is not set")

    all_vecs: list[list[float]] = []
    with httpx.Client(timeout=30) as client:
        for i in range(0, len(texts), EMBED_BATCH):
            batch = texts[i : i + EMBED_BATCH]
            resp = client.post(
                EMBED_URL,
                headers={"Authorization": f"Bearer {MISTRAL_API_KEY}"},
                json={"model": EMBED_MODEL, "input": batch},
            )
            resp.raise_for_status()
            items = sorted(resp.json()["data"], key=lambda x: x["index"])
            all_vecs.extend(d["embedding"] for d in items)

    arr = np.array(all_vecs, dtype="float32")
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    arr /= np.maximum(norms, 1e-8)
    return arr


def _card_to_text(card: dict) -> str:
    parts = []
    if card.get("front_type", "text") == "text" and card.get("front_content"):
        parts.append(card["front_content"])
    if card.get("back_type", "text") == "text" and card.get("back_content"):
        parts.append(card["back_content"])
    if card.get("answer_text"):
        parts.append(card["answer_text"])
    return " | ".join(parts) or f"card_{card.get('id', 0)}"


def _build_index(cards: list[dict]) -> dict:
    if not cards:
        return {"index": faiss.IndexFlatIP(EMBED_DIM), "meta": []}
    texts = [_card_to_text(c) for c in cards]
    vecs = _embed(texts)
    index = faiss.IndexFlatIP(EMBED_DIM)
    index.add(vecs)
    return {"index": index, "meta": list(cards)}


# ── Жизненный цикл ───────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    _load_store("all_cards")
    for f in DATA_DIR.glob("category_*.faiss"):
        _load_store(f.stem)
    logger.info(f"RAG service started. Stores: {list(stores)}")


# ── Схемы ─────────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    scope: str = "all_cards"
    k: int = 5


class CardData(BaseModel):
    id: int
    front_type: str = "text"
    front_content: str = ""
    back_type: str = "text"
    back_content: str = ""
    answer_text: str = ""


class BuildRequest(BaseModel):
    scope: str
    cards: list[dict]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "ok": True,
        "stores": {k: stores[k]["index"].ntotal for k in stores},
    }


@app.post("/search")
def search(req: SearchRequest):
    if req.scope not in stores or stores[req.scope]["index"].ntotal == 0:
        return {"docs": []}
    store = stores[req.scope]
    try:
        vec = _embed([req.query])
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    k = min(req.k, store["index"].ntotal)
    _, indices = store["index"].search(vec, k)
    docs = [store["meta"][i] for i in indices[0] if 0 <= i < len(store["meta"])]
    return {"docs": docs}


@app.post("/update_card")
def update_card(card: CardData):
    card_dict = card.dict()
    try:
        meta = stores.get("all_cards", {}).get("meta", [])
        for i, m in enumerate(meta):
            if m.get("id") == card.id:
                meta[i] = card_dict
                stores["all_cards"] = _build_index(meta)
                _save_store("all_cards")
                return {"ok": True}
        meta.append(card_dict)
        stores["all_cards"] = _build_index(meta)
        _save_store("all_cards")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"ok": True}


@app.post("/build")
def build(req: BuildRequest):
    if not req.cards:
        raise HTTPException(status_code=400, detail="No cards provided")
    try:
        stores[req.scope] = _build_index(req.cards)
        _save_store(req.scope)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"ok": True, "scope": req.scope, "count": len(req.cards)}
