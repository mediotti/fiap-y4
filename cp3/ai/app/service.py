import time

from app.context import pack, retrieve, tokens
from app.llm import Generated, ProviderError, estimate_messages, messages_for


class DocumentService:
    def __init__(self, store, llm, settings):
        self.store, self.llm, self.settings = store, llm, settings

    async def run(self, task, question, ids):
        started = time.perf_counter()
        chunks = self.store.chunks(ids)
        if not chunks:
            raise ValueError("Selecione ao menos um documento disponível.")
        existing = {c["document_id"] for c in chunks}
        if set(ids) != existing:
            raise ValueError("Um documento selecionado não existe mais. Atualize a biblioteca.")
        trace, sections, used = [], [], []
        # Reserva para instruções, objetivo, IDs e envelope JSON.
        overhead = estimate_messages(messages_for("qa", question, [])) + 400
        budget = self.settings.input_budget - overhead
        if budget < 900:
            raise ValueError("O objetivo é extenso demais para o orçamento disponível.")
        total_tokens = sum(c["tokens"] for c in chunks)
        try:
            if task == "qa":
                used = retrieve(chunks, question, budget)
                # Confere o prompt real serializado, incluindo o overhead de cada trecho.
                while (
                    used
                    and estimate_messages(messages_for("qa", question, used)) > self.settings.input_budget
                ):
                    used.pop()
                if not used:
                    result = Generated(
                        answer="Não encontrei trechos relacionados à pergunta nos documentos selecionados.",
                        citation_ids=[],
                        limitations=[
                            "A busca é lexical: tente palavras presentes no material.",
                            "Ausência de evidência recuperada não demonstra ausência do fato.",
                        ],
                    )
                else:
                    result, calls = await self.llm.generate("qa", question, used, len(ids))
                    trace.extend(calls)
                source_ids = set(result.citation_ids)
            else:
                if len(ids) != 1:
                    raise ValueError("Para resumir, selecione exatamente um documento.")
                if len(chunks) > 120:
                    raise ValueError(
                        "O resumo aceita até 120 trechos por execução. Divida o documento em partes."
                    )
                used = chunks
                current, provenance = [], {}
                for index, batch in enumerate(pack(chunks, budget)):
                    partial, calls = await self.llm.generate("map", question, batch)
                    trace.extend(calls)
                    sid = f"resumo-{index + 1}"
                    cited = set(partial.citation_ids)
                    provenance[sid] = cited
                    current.append(
                        {"id": sid, "name": "Resumo parcial", "page": index + 1, "text": partial.answer}
                    )
                    sections.append(
                        {
                            "title": f"Parte {index + 1}",
                            "answer": partial.answer,
                            "citation_ids": partial.citation_ids,
                        }
                    )
                # Redução hierárquica: nenhum lote inicial é descartado para caber na síntese.
                level = 0
                while len(pack(current, budget)) > 1:
                    level += 1
                    if level > 8:
                        raise ProviderError("A síntese não convergiu dentro do limite de etapas.", trace)
                    reduced = []
                    for index, batch in enumerate(pack(current, budget)):
                        partial, calls = await self.llm.generate("map", question, batch)
                        trace.extend(calls)
                        sid = f"nivel-{level}-{index}"
                        provenance[sid] = set().union(*(provenance[c] for c in partial.citation_ids))
                        reduced.append(
                            {
                                "id": sid,
                                "name": "Resumo intermediário",
                                "page": index + 1,
                                "text": partial.answer,
                            }
                        )
                    if sum(tokens(c["text"]) for c in reduced) >= sum(tokens(c["text"]) for c in current):
                        raise ProviderError(
                            "Os resumos não reduziram o contexto. Reduza o orçamento de saída.", trace
                        )
                    current = reduced
                result, calls = await self.llm.generate("synthesis", question, current)
                trace.extend(calls)
                source_ids = set().union(*(provenance[c] for c in result.citation_ids))
            sources = [c for c in used if c["id"] in source_ids]
            metrics = {
                "task": task,
                "mode": "live" if self.settings.api_key else "demo",
                "documents": len(ids),
                "total_chunks": len(chunks),
                "selected_chunks": len(used),
                "document_tokens_estimated": total_tokens,
                "selected_tokens_estimated": sum(c["tokens"] for c in used),
                "calls": len(trace),
                "trace": trace,
                "input_tokens": sum(c["input_tokens"] or 0 for c in trace)
                if trace and all(c["input_tokens"] is not None for c in trace)
                else None,
                "output_tokens": sum(c["output_tokens"] or 0 for c in trace)
                if trace and all(c["output_tokens"] is not None for c in trace)
                else None,
                "cost_usd": sum(c["cost_usd"] for c in trace)
                if trace and all(isinstance(c["cost_usd"], (int, float)) for c in trace)
                else None,
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "status": "ok",
            }
            self.store.log(metrics)
            warnings = list(result.limitations)
            if not sources:
                warnings.append(
                    "O modelo não indicou fontes; a resposta não deve ser tratada como fundamentada."
                )
            return {
                "answer": result.answer,
                "limitations": warnings,
                "sources": sources,
                "sections": sections,
                "metrics": metrics,
            }
        except ProviderError as exc:
            # Preserva tentativas anteriores em falhas de etapas posteriores.
            attempts = trace + [a for a in exc.attempts if a not in trace]
            self.store.log(
                {
                    "task": task,
                    "mode": "live" if self.settings.api_key else "demo",
                    "status": "error",
                    "trace": attempts,
                    "calls": len(attempts),
                    "latency_ms": round((time.perf_counter() - started) * 1000),
                }
            )
            raise
