from app.context import chunk_pages, pack, retrieve, text_sections, tokens


def make_chunks(text):
    return [{**c, "id": f"c{c['position']}", "name": "Manual"} for c in chunk_pages([text])]


def test_chunking_keeps_start_end_and_overlap():
    text = " ".join(f"palavra{i}" for i in range(2000))
    chunks = chunk_pages([text], size=600, overlap=80)
    assert chunks[0]["text"].startswith("palavra0")
    assert chunks[-1]["text"].endswith("palavra1999")
    assert all(len(c["text"]) <= 600 for c in chunks)
    assert chunks[0]["text"][-60:] in chunks[1]["text"]
    assert all(f"palavra{i}" in " ".join(c["text"] for c in chunks) for i in range(2000))


def test_retrieve_tail_of_long_document_and_respect_budget():
    text = "Projetos acadêmicos e leitura de materiais didáticos. " * 5000
    text += " O código exclusivo de conferência é JACARANDÁ-482."
    chunks = make_chunks(text)
    result = retrieve(chunks, "Qual é o código JACARANDÁ?", budget=1500)
    assert any("JACARANDÁ-482" in c["text"] for c in result)
    assert (
        sum(tokens(f"[{c['id']}] {c['name']} | página/seção {c['page']}\n{c['text']}") for c in result)
        <= 1500
    )
    assert tokens(text) > 6000
    assert len(result) < len(chunks)


def test_search_no_evidence_and_accents():
    chunks = make_chunks("A inscrição encerra em março. Solicite a bolsa no prazo publicado.")
    assert retrieve(chunks, "inscricao", 1500)
    assert retrieve(chunks, "astronomia extraterrestre", 1500) == []


def test_pack_never_drops_chunks():
    chunks = make_chunks("Pesquisa e metodologia. " * 3000)
    batches = pack(chunks, 1900)
    assert len(batches) > 1
    assert [c["id"] for b in batches for c in b] == [c["id"] for c in chunks]


def test_page_and_markdown_section_metadata():
    sections = text_sections(
        "# Título\nApresentação\n## Prazos\nPrazo: março.\n## Critérios\nCritério: matrícula.", True
    )
    chunks = chunk_pages(sections)
    assert len(sections) == 3
    assert chunks[-1]["page"] == 3
