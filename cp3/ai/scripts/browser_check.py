"""Smoke test com Playwright/Chromium instalados, contra um servidor de teste local.

Uso: python scripts/browser_check.py http://127.0.0.1:8000
Não remove documentos preexistentes. Cria e remove apenas um arquivo próprio.
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base_url)
    expect(page.locator("#mode-badge")).to_contain_text("Demonstração")
    page.locator("#demo-button").click()
    expect(page.locator("#selection-label")).to_contain_text("selecionado")
    # Limita seleção ao exemplo, sem tocar no conteúdo de outros documentos.
    for item in page.locator(".document-item").all():
        if "Manual Aurora" not in item.inner_text():
            item.locator("input").uncheck()
    page.locator("#submit-button").click()
    expect(page.locator("#result")).to_be_visible()
    expect(page.locator(".answer-body")).to_contain_text("15 de março")
    page.locator(".source-button").first.click()
    expect(page.locator("#source-dialog")).to_be_visible()
    expect(page.locator("#source-text")).not_to_be_empty()
    page.locator("#close-source").click()
    with page.expect_download() as download:
        page.get_by_role("button", name="Exportar").click()
    assert download.value.suggested_filename == "lume-analise.md"
    page.locator("#result summary").first.click()
    expect(page.locator(".trace-item").first).to_contain_text("simulado")
    page.screenshot(path=str(ROOT / "docs/lume-consulta.png"), full_page=True)
    page.locator("#tab-summary").click()
    page.locator("#question").fill("Resuma critérios, prazos e perspectivas para estudantes.")
    page.locator("#submit-button").click()
    expect(page.locator("#result")).to_be_visible(timeout=15000)
    expect(page.locator("#result")).to_contain_text("Resumos parciais")
    page.locator("#history-button").click()
    expect(page.locator("#history")).to_be_visible()
    expect(page.locator(".history-row").first).to_contain_text("Resumo")
    page.locator("#close-history").click()
    page.locator("#tab-qa").click()
    page.locator("#question").fill("Astronomia extraterrestre em Saturno?")
    page.locator("#submit-button").click()
    expect(page.locator("#result")).to_contain_text("Não encontrei")
    # Upload e exclusão de um documento próprio pelo navegador.
    page.locator("#upload").set_input_files(
        {
            "name": "teste-interface.txt",
            "mimeType": "text/plain",
            "buffer": b"O documento exclusivo do teste possui prazo de 7 dias.",
        }
    )
    own = page.locator(".document-item").filter(has_text="teste-interface.txt")
    expect(own).to_be_visible()
    own.get_by_role("button", name="Remover").click()
    expect(own).to_have_count(0)
    page.locator("#settings-button").click()
    expect(page.locator("#settings-dialog")).to_be_visible()
    page.locator("#close-settings").click()
    page.set_viewport_size({"width": 390, "height": 844})
    page.reload()
    expect(page.locator("#mode-badge")).to_contain_text("Demonstração")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Overflow horizontal"
    page.screenshot(path=str(ROOT / "docs/lume-mobile.png"), full_page=True)
    assert not errors, errors
    browser.close()

report = {
    "status": "passed",
    "browser": "Chromium",
    "viewports": ["1440x1100", "390x844"],
    "flows": [
        "example",
        "qa",
        "sources",
        "export",
        "summary",
        "history",
        "abstention",
        "upload",
        "delete",
        "settings",
        "mobile",
    ],
    "console_errors": errors,
}
(ROOT / "docs/browser-verification.json").write_text(json.dumps(report, indent=2))
print("11 fluxos verificados no Chromium; desktop e celular, sem erros JavaScript.")
