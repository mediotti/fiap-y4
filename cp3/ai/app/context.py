"""Chunking com sobreposição, busca BM25 e orçamento explícito de contexto."""

import math
import re
import unicodedata
from collections import Counter

STOP = set(
    "a o as os de da do das dos em um uma para por com e ou que qual quais como no na nos nas ao se é são sobre meu minha documento documentos segundo".split()
)


def tokens(text: str) -> int:
    # Estimativa conservadora para prosa PT; não é o tokenizer exato do provedor.
    return math.ceil(len(text.encode("utf-8")) / 3)


def text_sections(text: str, markdown: bool = False) -> list[str]:
    return re.split(r"\n(?=## )", text) if markdown else [text]


def terms(text: str) -> list[str]:
    normalized = "".join(
        c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c)
    )
    return [w for w in re.findall(r"[a-z0-9]+", normalized) if w not in STOP and len(w) > 1]


def chunk_pages(pages: list[str], size=1800, overlap=180) -> list[dict]:
    chunks = []
    for page, text in enumerate(pages, 1):
        text = text.replace("\x00", "").strip()
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                boundary = text.rfind(" ", start + size // 2, end)
                if boundary > start:
                    end = boundary
            excerpt = text[start:end].strip()
            if excerpt:
                chunks.append(
                    {"page": page, "position": len(chunks) + 1, "text": excerpt, "tokens": tokens(excerpt)}
                )
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
    return chunks


def retrieve(chunks: list[dict], query: str, budget: int, limit=8) -> list[dict]:
    if not chunks:
        return []
    query_terms = set(terms(query))
    bags = [Counter(terms(c["text"])) for c in chunks]
    avg = sum(sum(b.values()) for b in bags) / len(bags) or 1
    df = Counter(t for bag in bags for t in bag)
    ranked = []
    for chunk, bag in zip(chunks, bags):
        score = 0
        length = sum(bag.values())
        for term in query_terms:
            freq = bag[term]
            if freq:
                idf = math.log(1 + (len(bags) - df[term] + 0.5) / (df[term] + 0.5))
                score += idf * freq * 2.5 / (freq + 1.5 * (0.25 + 0.75 * length / avg))
        if score > 0:
            ranked.append(({**chunk, "score": round(score, 3)}, score))
    selected, used = [], 0
    for chunk, _ in sorted(ranked, key=lambda item: item[1], reverse=True):
        cost = tokens(source_text(chunk))
        if used + cost <= budget:
            selected.append(chunk)
            used += cost
        if len(selected) == limit:
            break
    return selected


def source_text(chunk: dict) -> str:
    return f"[{chunk['id']}] {chunk['name']} | página/seção {chunk['page']}\n{chunk['text']}"


def pack(items: list[dict], budget: int) -> list[list[dict]]:
    batches, batch, used = [], [], 0
    for item in items:
        cost = tokens(source_text(item))
        if cost > budget:
            raise ValueError("Trecho excede o orçamento de contexto.")
        if batch and used + cost > budget:
            batches.append(batch)
            batch, used = [], 0
        batch.append(item)
        used += cost
    if batch:
        batches.append(batch)
    return batches
