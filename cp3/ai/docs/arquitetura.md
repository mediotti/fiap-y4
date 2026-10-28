# Decisões técnicas

## Fluxo e módulos

`main.py` expõe a API e serve a interface. `store.py` persiste em SQLite, com conexão curta por operação, chaves estrangeiras e exclusão em cascata. `context.py` organiza trechos e recupera contexto. `llm.py` contém prompts, regra de roteamento, transporte OpenRouter e validação de respostas. `service.py` coordena consulta e resumo e registra métricas. A chave não é devolvida por nenhum endpoint.

## Documentos e contexto longo

Uploads aceitam TXT UTF-8, Markdown e PDF com texto extraível. Páginas de PDF são preservadas; títulos de nível 2 em Markdown delimitam seções; TXT corresponde a uma seção. Trechos têm até 1.800 caracteres e sobreposição de 180, preferindo cortar entre palavras. Os metadados incluem documento, página/seção, posição e ID estável enquanto o documento existir. Duplicação usa SHA-256 do texto extraído, mesmo quando o nome do arquivo muda.

**Consulta:** normalização de acentos, remoção de palavras frequentes e BM25 (`k1=1,5`, `b=0,75`). Os melhores trechos entram até o limite de oito e o orçamento de contexto. A seleção é revalidada contra o prompt serializado. Nenhum trecho com pontuação zero é enviado. Se não houver correspondência lexical, há resposta local de insuficiência, sem custo de LLM. Isso favorece perguntas com termos do material, mas pode perder sinônimos e inferências. Não há busca semântica, OCR, reranker ou memória conversacional; cada pergunta precisa ser autossuficiente.

**Resumo:** exatamente um documento, até 120 trechos. Todos entram em lotes; cada lote produz um resumo parcial com fontes. Quando os resumos ainda excedem o orçamento, novos níveis de compressão são gerados até caber na síntese. Nenhum lote é descartado só para caber. Há limite de oito níveis e verificação de progresso da redução. As referências dos intermediários são mapeadas recursivamente para os trechos originais. A cobertura de processamento não garante preservação de todo fato: a compressão pode perder detalhes, e a interface mantém fontes e resumos parciais para revisão.

## Tokens e custo

A estimativa é `ceil(bytes UTF-8 / 3)`, adequada como aproximação conservadora para prosa em português, **sem garantia para todo tokenizer ou conteúdo**. Cada mensagem tem margem adicional de envelope. O padrão reserva 6.000 tokens estimados de entrada, 1.000 de saída e 512 de margem dentro de uma janela declarada de 16.384. O resumo parcial pede no máximo 450 tokens de saída. Um prompt acima do orçamento é rejeitado antes da chamada. A soma de entrada, saída e margem é validada na configuração.

O limite é conservador e compartilhado entre todos os modelos, incluindo fallback. Ao trocar modelos, ajuste `MODEL_CONTEXT_WINDOW` para a menor janela utilizada. Os limites reais do catálogo do provedor devem ser confirmados pelo grupo. O backend envia `max_tokens`; uma resposta truncada é considerada inválida. Estimativas não substituem o uso real retornado por `usage`.

Entrada, saída e custo real são exibidos apenas quando informados pelo provedor. Dado ausente aparece como indisponível, nunca como custo zero. Não há estimativa financeira baseada em preços fixos nem limite de gasto acumulado. O total do resumo é a soma de todas as chamadas e pode superar bastante o custo de uma consulta. Falhas já processadas pelo provedor também podem ter custo; chamadas sem `usage` tornam o total indisponível.

## Roteamento

| Condição explícita | Destino inicial | Motivo |
| --- | --- | --- |
| Pergunta factual, até 45 termos úteis, um documento | `MODEL_FAST` | Priorizar custo e latência esperados |
| Analisar, comparar, contrastar, justificar, relacionar ou criticar | `MODEL_DEEP` | Maior capacidade esperada de integração |
| Pergunta com mais de 45 termos úteis ou múltiplos documentos | `MODEL_DEEP` | Maior complexidade do contexto |
| Resumo parcial e redução intermediária | `MODEL_FAST` | Compressão de lotes pequenos |
| Síntese global | `MODEL_DEEP` | Relacionar partes e preservar ressalvas |
| Falha de transporte/HTTP, JSON inválido, citação inexistente ou truncamento | `MODEL_FALLBACK` | Uma tentativa adicional em modelo distinto |

Os padrões iniciais são Gemini 2.5 Flash, Claude Sonnet 4.5 e GPT-4.1 mini, respectivamente. São hipóteses de custo/capacidade, sem comparação empírica de qualidade realizada. IDs são configuráveis e precisam de conferência no catálogo atual. A regra usa palavras normalizadas e não representa um classificador semântico; reformulações podem mudar a decisão. Usar dois nomes iguais na configuração remove a distinção prática, por isso o grupo deve manter `FAST` e `DEEP` diferentes.

Não há roteamento automático como decisão principal. Cada chamada envia um único ID de modelo escolhido pela aplicação. Fallback da aplicação tem no máximo uma tentativa adicional, e modelos repetidos são deduplicados. Erros 401, 402 e 403 interrompem a operação para corrigir chave, saldo ou acesso; não são convertidos silenciosamente em demonstração. Toda tentativa tem modelo, motivo, modo, status, latência e uso disponível registrados.

## Prompts e saídas

O prompt define papel de assistente acadêmico, público, idioma, uso exclusivo das fontes, reconhecimento de ausência e preservação de divergências. Dois exemplos demonstram uma resposta sustentada e outra sem evidência. Pergunta, objetivo e fontes são dados JSON na mensagem do usuário; instruções fixas ficam na mensagem de sistema. As fontes são explicitamente tratadas como conteúdo não confiável. Isso reduz ambiguidades de instrução, mas não garante imunidade a prompt injection.

A saída deve obedecer a `{answer, citation_ids, limitations}`, validada com Pydantic em modo estrito. IDs fora do lote são rejeitados e acionam fallback. IDs válidos não provam apoio semântico às afirmações: essa etapa depende da leitura crítica. Quando a resposta não indica fontes, a interface mostra uma ressalva adicional. O frontend renderiza todo texto de documentos e respostas com `textContent`, sem executar HTML do modelo.

## Operação e limitações

O transporte usa `httpx`, timeout de conexão de 10 segundos e de operação de rede de 60 segundos. Resumos são sequenciais para reduzir picos de chamadas. Não há streaming, fila durável, retomada de resumo interrompido nem cancelamento de chamadas pelo navegador. Uma tentativa HTTP pode falhar após iniciar geração e ainda consumir créditos. A interface mantém indicação de processamento em tarefas longas.

O histórico registra apenas métricas e escolhas, sem conteúdo de perguntas ou respostas. Excluir documentos não exclui métricas históricas. O MVP é monousuário/local: autenticação, auditoria por usuário, quotas financeiras, extração isolada de PDFs e política institucional de retenção são trabalhos futuros para hospedagem compartilhada.
