import json
from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.config import Settings
from app.main import create_app


def client(tmp_path):
    return TestClient(create_app(Settings(data_dir=tmp_path)))


def upload(
    c,
    name="manual.txt",
    text="A bolsa mensal é de R$ 700,00. O prazo de inscrição termina em 15 de março de 2026.",
):
    return c.post("/api/documents", files={"file": (name, text.encode(), "text/plain")})


def test_upload_query_citations_metrics_and_delete(tmp_path):
    c = client(tmp_path)
    assert c.get("/").status_code == 200
    assert c.get("/api/status").json()["mode"] == "demo"
    doc_id = upload(c).json()["id"]
    result = c.post(
        "/api/analyze", json={"question": "Qual é o prazo de inscrição?", "document_ids": [doc_id]}
    )
    assert result.status_code == 200
    data = result.json()
    assert "15 de março" in data["answer"]
    assert data["sources"][0]["document_id"] == doc_id
    assert data["metrics"]["selected_chunks"] == 1
    assert data["metrics"]["cost_usd"] is None
    runs = c.get("/api/runs").json()
    assert len(runs) == 1
    assert "answer" not in json.dumps(runs)
    assert "700" not in json.dumps(runs)
    assert c.delete(f"/api/documents/{doc_id}").status_code == 200
    assert c.get("/api/documents").json() == []
    assert c.app.state.store.chunks([doc_id]) == []


def test_deduplication_persistence_and_filename_sanitizing(tmp_path):
    c = client(tmp_path)
    doc = upload(c, "../../manual.txt").json()
    duplicate = upload(c).json()
    assert duplicate["duplicate"]
    assert duplicate["id"] == doc["id"]
    fresh = client(tmp_path)
    assert fresh.get("/api/documents").json()[0]["name"] == "manual.txt"


def test_validation_and_missing_documents(tmp_path):
    c = client(tmp_path)
    assert upload(c, "code.exe").status_code == 415
    assert upload(c, text=" ").status_code == 422
    assert upload(c, text="a" * 2_000_001).status_code == 413
    assert c.post("/api/documents", files={"file": ("bad.txt", b"\xff\xff", "text/plain")}).status_code == 422
    assert (
        c.post("/api/documents", files={"file": ("bad.pdf", b"not-pdf", "application/pdf")}).status_code
        == 422
    )
    assert c.post("/api/analyze", json={"question": "Qual prazo?", "document_ids": []}).status_code == 422
    assert (
        c.post("/api/analyze", json={"question": "Qual prazo?", "document_ids": ["missing"]}).status_code
        == 422
    )


def test_blank_pdf_requires_text_and_encrypted_pdf_rejected(tmp_path):
    c = client(tmp_path)
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buffer = BytesIO()
    writer.write(buffer)
    assert c.post("/api/documents", files={"file": ("scan.pdf", buffer.getvalue())}).status_code == 422
    writer.encrypt("password")
    encrypted = BytesIO()
    writer.write(encrypted)
    assert c.post("/api/documents", files={"file": ("private.pdf", encrypted.getvalue())}).status_code == 422


def test_no_evidence_abstains_without_model_call(tmp_path):
    c = client(tmp_path)
    doc_id = upload(c).json()["id"]
    result = c.post("/api/analyze", json={"question": "Capital do Japão?", "document_ids": [doc_id]}).json()
    assert "Não encontrei" in result["answer"]
    assert result["sources"] == []
    assert result["metrics"]["calls"] == 0


def test_long_document_summary_covers_all_chunks_and_routes(tmp_path):
    c = client(tmp_path)
    doc_id = c.post("/api/demo").json()["id"]
    result = c.post(
        "/api/analyze",
        json={"task": "summary", "question": "Resuma critérios e prazos", "document_ids": [doc_id]},
    )
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["metrics"]["document_tokens_estimated"] > 6000
    assert data["metrics"]["selected_chunks"] == data["metrics"]["total_chunks"]
    assert len(data["sections"]) > 1
    trace = data["metrics"]["trace"]
    assert trace[0]["model"] != trace[-1]["model"]
    assert all(call["estimated_input_tokens"] <= 6000 for call in trace)
    assert data["sources"]


def test_summary_rejects_multiple_and_too_large_materials(tmp_path):
    c = client(tmp_path)
    first = upload(c).json()["id"]
    second = upload(c, text="Texto de outro documento de pesquisa com matrícula ativa e bolsa.").json()["id"]
    assert (
        c.post(
            "/api/analyze",
            json={"task": "summary", "question": "Resuma os materiais", "document_ids": [first, second]},
        ).status_code
        == 422
    )
    big = upload(c, text="material pesquisa " * 18000).json()["id"]
    assert (
        c.post(
            "/api/analyze", json={"task": "summary", "question": "Resuma os materiais", "document_ids": [big]}
        ).status_code
        == 422
    )
