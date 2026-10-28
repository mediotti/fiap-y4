# Avaliação e evidências

## O que foi verificado

O relatório `evaluation-demo.json` contém seis cenários e 18 verificações de funcionamento: regra de roteamento, presença de evidência esperada nas fontes, orçamento de cada prompt, ausência de chamada sem correspondência lexical e processamento de todos os trechos no resumo. Os seis cenários passaram na execução registrada. O manual possui 45 trechos e cerca de 22.479 tokens estimados de conteúdo, acima do orçamento de entrada de 6.000 por chamada. O resumo processou 45/45 em cinco lotes parciais e uma síntese simulada.

Há 25 testes automatizados para chunking, metadados, orçamento, busca no fim de um arquivo extenso, upload, deduplicação, persistência, exclusão, erros de PDF, abstinência, roteamento, fallback, JSON inválido, citação inexistente, truncamento, erros de chave/saldo/permissão, síntese com múltiplos níveis e preservação de tentativas após falha. O transporte do OpenRouter usa `httpx.MockTransport` nos testes: são testes do contrato e tratamento de falhas, sem chamada real.

O smoke test de navegador registrou 11 fluxos no Chromium: exemplo, consulta, fontes, exportação, resumo, histórico, abstinência, upload, exclusão, configuração e visualização em celular. As capturas desktop e celular estão em `docs/`, e `browser-verification.json` registra os fluxos. Não houve erro JavaScript nem transbordamento horizontal a 390 pixels.

**Esses resultados não demonstram a qualidade de um LLM.** Sem chave e liberação de rede para o OpenRouter, a avaliação real não foi executada. A extração do modo demo pode ser repetitiva e não realiza comparação semântica. Ela demonstra o fluxo e as regras, com esse limite explícito.

## Executar avaliação real

1. Configure a chave no servidor e permita o domínio `openrouter.ai` no ambiente.
2. Confirme os três IDs, suporte a JSON, janelas e preços no catálogo atual.
3. Execute `python scripts/evaluate.py --live --output docs/evaluation-live.json`.
4. Registre data, modelos, configuração, uso e custo disponível. O comando faz chamadas cobradas.
5. Dois integrantes devem revisar independentemente as respostas e discutir divergências de avaliação.

Além dos cenários automáticos, use um documento próprio público ou autorizado. Inclua uma pergunta factual, uma comparação de perspectivas, um resumo e uma pergunta sem resposta no material. Repita uma pergunta com palavras diferentes para observar a sensibilidade lexical. Para comparar o roteador, faça uma segunda rodada trocando `MODEL_FAST` e `MODEL_DEEP`, mantendo as perguntas e os documentos, e compare os resultados sob a rubrica abaixo.

## Rubrica humana: 0 a 2 em cada dimensão

| Dimensão | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Fidelidade às fontes | Inventa ou contradiz | Tem imprecisão ou atribuição fraca | Afirmações verificáveis e atribuídas |
| Cobertura do objetivo | Não atende | Atende parcialmente | Cobre pontos essenciais e exceções |
| Perspectivas e contexto | Apaga ou confunde vozes | Distingue parcialmente | Preserva posições, condições e limites |
| Adequação ao público | Obscura ou inadequada | Compreensível com esforço | Português claro e útil para estudantes |
| Reconhecimento de limites | Certeza sem evidência | Ressalva genérica | Reconhece exatamente as lacunas |

Considere 8/10 uma meta inicial, sem aceitar nota zero em fidelidade. A meta é um critério proposto, ainda sem resultado real. Analise também latência, tokens, custo, número de fallbacks e se a rota econômica trouxe benefício sem perda material de qualidade. Uma rota marcada como correta pelo teste só confirma a regra, não a superioridade do modelo escolhido.

| Caso | Modelo real / tentativas | Nota /10 | Erros ou omissões | Decisão sobre a rota |
| --- | --- | --- | --- | --- |
| Prazo | A preencher após execução real | — | — | — |
| Valor | A preencher após execução real | — | — | — |
| Perspectivas | A preencher após execução real | — | — | — |
| Final do documento | A preencher após execução real | — | — | — |
| Sem evidência | Sem chamada, se não houver recuperação | — | — | — |
| Resumo integral | A preencher após execução real | — | — | — |

## Limites dos testes

O conjunto é pequeno, sintético e em português; não é benchmark geral. A coincidência textual nas fontes mede recuperação simples e não apoio semântico. A busca pode recuperar trechos sobre um assunto relacionado, mesmo quando o fato pedido está ausente. O prompt pede abstinência, mas só a revisão de respostas reais verifica seu cumprimento. PDF com texto complexo, tabelas e múltiplas colunas pode ser extraído em ordem inadequada. O smoke test não substitui teste de acessibilidade com pessoas ou tecnologias assistivas.
