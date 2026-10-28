"""Avaliação reproduzível; --live faz chamadas cobradas ao OpenRouter."""

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.context import text_sections  # noqa: E402
from app.llm import LLM  # noqa: E402
from app.service import DocumentService  # noqa: E402
from app.store import Store  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


async def evaluate(live=False):
    with tempfile.TemporaryDirectory(prefix="lume-eval-") as directory:
        settings = Settings.from_env() if live else Settings()
        if live and not settings.api_key:
            raise SystemExit("Defina OPENROUTER_API_KEY para a avaliação real.")
        settings.data_dir = Path(directory)
        store = Store(settings.data_dir)
        doc = store.add(
            "Manual Aurora", text_sections((ROOT / "examples/manual-aurora.md").read_text(), True)
        )
        service = DocumentService(store, LLM(settings), settings)
        cases = json.loads((ROOT / "examples/evaluation.json").read_text())
        rows = []
        for case in cases:
            result = await service.run(case["task"], case["question"], [doc["id"]])
            metrics = result["metrics"]
            expected = case["expected_model"]
            selected = metrics["trace"][-1]["model"] if metrics["trace"] else None
            expected_id = getattr(settings, f"{expected}_model") if expected else None
            evidence = "\n".join(c["text"] for c in result["sources"])
            rows.append(
                {
                    "case": case["id"],
                    "mode": metrics["mode"],
                    "route_correct": selected == expected_id,
                    "expected_evidence_in_sources": case["expected_source"] in evidence
                    if case["expected_source"]
                    else None,
                    "abstained_without_call": metrics["calls"] == 0 if expected is None else None,
                    "all_chunks_processed": metrics["selected_chunks"] == metrics["total_chunks"]
                    if case["task"] == "summary"
                    else None,
                    "prompts_within_budget": all(
                        c["estimated_input_tokens"] <= settings.input_budget for c in metrics["trace"]
                    ),
                    "answer": result["answer"],
                    "limitations": result["limitations"],
                    "metrics": metrics,
                }
            )
        return {
            "mode": "live" if live else "demo",
            "cases": rows,
            "note": "A extração local não avalia qualidade de LLM. Fonte recuperada não prova fidelidade "
            "semântica. Use a rubrica humana de docs/avaliacao.md para avaliar as respostas reais.",
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/evaluation-demo.json")
    args = parser.parse_args()
    report = asyncio.run(evaluate(args.live))
    if args.live and "demo" in args.output.name:
        args.output = ROOT / "docs/evaluation-live.json"
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    checks = [
        v
        for row in report["cases"]
        for k, v in row.items()
        if k
        in {
            "route_correct",
            "expected_evidence_in_sources",
            "abstained_without_call",
            "all_chunks_processed",
            "prompts_within_budget",
        }
        and v is not None
    ]
    print(f"{len(report['cases'])} cenários · {sum(checks)}/{len(checks)} verificações · {args.output}")
    if not all(checks):
        raise SystemExit(1)
