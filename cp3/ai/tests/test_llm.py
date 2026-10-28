import asyncio
import json

import httpx
import pytest

from app.config import Settings
from app.llm import LLM, ProviderError, route

SOURCES = [{"id": "c1", "name": "Manual", "page": 1, "text": "O prazo é 15 de março."}]


def completion(answer="O prazo é 15 de março.", ids=None):
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "answer": answer,
                            "citation_ids": ids if ids is not None else ["c1"],
                            "limitations": [],
                        }
                    )
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 30, "cost": 0.0001},
    }


def test_route_changes_by_task_complexity_and_documents():
    settings = Settings()
    assert route(settings, "qa", "Qual é o prazo?").model == settings.fast_model
    assert route(settings, "qa", "Compare as perspectivas").model == settings.deep_model
    assert route(settings, "qa", "Qual é o prazo?", 2).model == settings.deep_model
    assert route(settings, "map", "Resuma").model == settings.fast_model
    assert route(settings, "synthesis", "Resuma").model == settings.deep_model


@pytest.mark.parametrize("failure", ["server", "invalid_json", "bad_citation", "truncated"])
def test_fallback_and_trace(failure):
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            if failure == "server":
                return httpx.Response(503)
            payload = completion(ids=["inventada"]) if failure == "bad_citation" else completion()
            if failure == "invalid_json":
                payload["choices"][0]["message"]["content"] = "não é JSON"
            if failure == "truncated":
                payload["choices"][0]["finish_reason"] = "length"
            return httpx.Response(200, json=payload)
        return httpx.Response(200, json=completion())

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await LLM(Settings(api_key="test-key"), client).generate("qa", "Qual prazo?", SOURCES)

    result, trace = asyncio.run(run())
    assert result.citation_ids == ["c1"]
    assert len(calls) == 2
    assert calls[0]["model"] != calls[1]["model"]
    assert [t["status"] for t in trace] == ["error", "ok"]
    assert trace[1]["input_tokens"] == 100
    assert "test-key" not in json.dumps(trace)


@pytest.mark.parametrize("status", [401, 402, 403])
def test_auth_or_billing_error_does_not_retry_or_simulate(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="secret-provider-error")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await LLM(Settings(api_key="test-key"), client).generate("qa", "Qual prazo?", SOURCES)

    with pytest.raises(ProviderError) as exc:
        asyncio.run(run())
    assert len(calls) == 1
    assert "secret-provider-error" not in str(exc.value)


def test_demo_is_marked_and_does_not_make_network_calls():
    def handler(request):
        raise AssertionError("Demo não deve chamar o provedor")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await LLM(Settings(), client).generate("qa", "Qual prazo?", SOURCES)

    result, trace = asyncio.run(run())
    assert "15 de março" in result.answer
    assert trace[0]["mode"] == "demo"
    assert trace[0]["cost_usd"] is None


def test_budget_blocks_before_network_call():
    async def run():
        sources = [{**SOURCES[0], "text": "texto " * 10000}]
        await LLM(Settings(api_key="test")).generate("qa", "Qual prazo?", sources)

    with pytest.raises(ProviderError, match="orçamento"):
        asyncio.run(run())


def test_configuration_rejects_window_overflow():
    with pytest.raises(ValueError, match="janela"):
        Settings(context_window=7000)
