import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from app.context import chunk_pages, tokens


class Store:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "lume.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, name TEXT, digest TEXT UNIQUE, tokens INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY, document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
                    page INTEGER, position INTEGER, text TEXT, tokens INTEGER);
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP, payload TEXT);
            """)

    @contextmanager
    def connect(self):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            yield db

    def add(self, name: str, pages: list[str]) -> dict:
        text = "\n".join(pages)
        if len(text.strip()) < 30:
            raise ValueError("O documento precisa conter ao menos 30 caracteres de texto extraível.")
        if len(text) > 500_000:
            raise ValueError("O documento excede 500 mil caracteres extraídos.")
        digest = hashlib.sha256(text.encode()).hexdigest()
        with self.connect() as db:
            existing = db.execute("SELECT id FROM documents WHERE digest=?", (digest,)).fetchone()
            if existing:
                return {"id": existing["id"], "duplicate": True}
            if db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] >= 20:
                raise ValueError("Limite de 20 documentos. Remova um material para continuar.")
            doc_id = uuid.uuid4().hex[:12]
            db.execute(
                "INSERT INTO documents(id,name,digest,tokens) VALUES (?,?,?,?)",
                (doc_id, name[:120], digest, tokens(text)),
            )
            for c in chunk_pages(pages):
                db.execute(
                    "INSERT INTO chunks VALUES (?,?,?,?,?,?)",
                    (f"{doc_id}-{c['position']}", doc_id, c["page"], c["position"], c["text"], c["tokens"]),
                )
        return {"id": doc_id, "duplicate": False}

    def documents(self):
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute("""
                SELECT d.id,d.name,d.tokens,d.created_at,COUNT(c.id) AS chunks
                FROM documents d LEFT JOIN chunks c ON c.document_id=d.id
                GROUP BY d.id ORDER BY d.created_at,d.id
            """)
            ]

    def chunks(self, ids: list[str]):
        if not ids:
            return []
        with self.connect() as db:
            return [
                dict(r)
                for r in db.execute(
                    f"""
                SELECT c.*,d.name FROM chunks c JOIN documents d ON d.id=c.document_id
                WHERE d.id IN ({",".join("?" for _ in ids)}) ORDER BY d.created_at,d.id,c.position
            """,
                    ids,
                )
            ]

    def delete(self, doc_id):
        with self.connect() as db:
            return db.execute("DELETE FROM documents WHERE id=?", (doc_id,)).rowcount > 0

    def log(self, result):
        # Apenas métricas; perguntas, respostas e textos não vão para o histórico.
        with self.connect() as db:
            db.execute("INSERT INTO runs(payload) VALUES (?)", (json.dumps(result, ensure_ascii=False),))

    def runs(self):
        with self.connect() as db:
            return [
                {"id": r["id"], "created_at": r["created_at"], **json.loads(r["payload"])}
                for r in db.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 30")
            ]
