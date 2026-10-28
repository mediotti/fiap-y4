import asyncio

from app.config import Settings
from app.llm import Generated, ProviderError
from app.service import DocumentService
from app.store import Store


class RecordingLLM:
    def __init__(self):
        self.calls = []

    async def generate(self, task, question, sources, document_count=1):
        self.calls.append((task, [c["id"] for c in sources]))
        return Generated(
            answer="A matrícula ativa é exigida. " * 15,
            citation_ids=[c["id"] for c in sources],
            limitations=[],
        ), []


def test_multilevel_summary_keeps_provenance_from_every_original_chunk(tmp_path):
    settings = Settings(input_budget=3000, data_dir=tmp_path)
    store = Store(tmp_path)
    doc = store.add(
        "Material extenso", [f"Seção {i}. " + "A matrícula ativa é exigida. " * 58 for i in range(100)]
    )
    llm = RecordingLLM()
    result = asyncio.run(
        DocumentService(store, llm, settings).run("summary", "Resuma os critérios", [doc["id"]])
    )
    original_ids = {c["id"] for c in store.chunks([doc["id"]])}
    first_level_ids = {cid for task, ids in llm.calls for cid in ids if cid in original_ids}
    assert first_level_ids == original_ids
    assert any(any(cid.startswith("resumo-") for cid in ids) for task, ids in llm.calls if task == "map")
    assert {c["id"] for c in result["sources"]} == original_ids
    assert llm.calls[-1][0] == "synthesis"


def test_failure_in_later_stage_preserves_prior_attempts(tmp_path):
    class FailingLLM:
        def __init__(self):
            self.count = 0

        async def generate(self, task, question, sources, document_count=1):
            self.count += 1
            call = {"model": "test-model", "status": "ok" if self.count == 1 else "error"}
            if self.count > 1:
                raise ProviderError("Falha do provedor", [call])
            return Generated(
                answer="Resumo parcial.", citation_ids=[c["id"] for c in sources], limitations=[]
            ), [call]

    settings = Settings(data_dir=tmp_path)
    store = Store(tmp_path)
    doc = store.add("Documento", ["Informação relevante para o resumo do documento. " * 1000])
    try:
        asyncio.run(DocumentService(store, FailingLLM(), settings).run("summary", "Resuma tudo", [doc["id"]]))
    except ProviderError:
        pass
    else:
        raise AssertionError("Falha esperada")
    log = store.runs()[0]
    assert log["status"] == "error"
    assert [c["status"] for c in log["trace"]] == ["ok", "error"]
