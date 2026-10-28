import io
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pypdf import PdfReader

from app.config import Settings
from app.context import text_sections
from app.llm import LLM, ProviderError
from app.service import DocumentService
from app.store import Store

ROOT = Path(__file__).resolve().parent.parent


class Request(BaseModel):
    task: Literal["qa", "summary"] = "qa"
    question: str = Field(min_length=3, max_length=2000)
    document_ids: list[str] = Field(min_length=1, max_length=20)


def create_app(settings=None, llm=None):
    settings = settings or Settings.from_env()
    store = Store(settings.data_dir)
    service = DocumentService(store, llm or LLM(settings), settings)
    app = FastAPI(title="Lume · Assistente de documentos", version="0.1.0")
    app.state.store, app.state.service = store, service
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @app.get("/")
    def index():
        return FileResponse(ROOT / "static/index.html")

    @app.get("/api/status")
    def status():
        return {
            "mode": "live" if settings.api_key else "demo",
            "models": {
                "fast": settings.fast_model,
                "deep": settings.deep_model,
                "fallback": settings.fallback_model,
            },
            "input_budget": settings.input_budget,
            "output_budget": settings.output_budget,
            "context_window": settings.context_window,
        }

    @app.get("/api/documents")
    def documents():
        return store.documents()

    @app.post("/api/documents", status_code=201)
    async def upload(file: UploadFile = File(...)):
        name = Path((file.filename or "documento").replace("\\", "/")).name
        extension = Path(name).suffix.lower()
        if extension not in {".txt", ".md", ".pdf"}:
            raise HTTPException(415, "Envie um arquivo TXT, Markdown ou PDF com texto.")
        data = await file.read(2_000_001)
        await file.close()
        if len(data) > 2_000_000:
            raise HTTPException(413, "O limite por arquivo é de 2 MB.")
        try:
            if extension == ".pdf":
                reader = PdfReader(io.BytesIO(data))
                if reader.is_encrypted or len(reader.pages) > 300:
                    raise ValueError("PDF protegido ou com mais de 300 páginas.")
                pages = []
                for page in reader.pages:
                    pages.append(page.extract_text() or "")
                    if sum(map(len, pages)) > 500_000:
                        raise ValueError("PDF excede 500 mil caracteres extraídos.")
            else:
                pages = text_sections(data.decode("utf-8-sig"), extension == ".md")
        except Exception as exc:
            raise HTTPException(
                422,
                "Não foi possível ler o arquivo. Use UTF-8 ou PDF com texto, "
                "sem senha e até 300 páginas / 500 mil caracteres. PDFs escaneados exigem OCR.",
            ) from exc
        try:
            return store.add(name, pages)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/demo")
    def demo():
        return store.add(
            "Manual Aurora · exemplo fictício.md",
            text_sections((ROOT / "examples/manual-aurora.md").read_text(), True),
        )

    @app.delete("/api/documents/{doc_id}")
    def delete(doc_id: str):
        if not store.delete(doc_id):
            raise HTTPException(404, "Documento não encontrado.")
        return {"deleted": True}

    @app.post("/api/analyze")
    async def analyze(request: Request):
        if not request.question.strip():
            raise HTTPException(422, "Escreva uma pergunta ou objetivo.")
        try:
            return await service.run(
                request.task, request.question.strip(), list(dict.fromkeys(request.document_ids))
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except ProviderError as exc:
            raise HTTPException(502, str(exc)) from exc

    @app.get("/api/runs")
    def runs():
        return store.runs()

    return app


app = create_app()
