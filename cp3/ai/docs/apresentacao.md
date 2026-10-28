# Lume — apresentação de 5 a 7 minutos

## Slide 1 · Problema e público · 40 segundos

**Como encontrar uma resposta verificável quando a informação está espalhada em um documento extenso?**

Lume apoia estudantes e grupos acadêmicos na leitura de manuais e relatórios. Permite consultar, resumir e conferir fontes. A proposta é apoiar leitura crítica, mantendo a responsabilidade humana pela interpretação.

Mostrar a tela inicial e identificar a biblioteca, os modos de análise e o aviso de demonstração/OpenRouter.

## Slide 2 · MVP em uso · 1 minuto

Adicionar o Manual Aurora, material inteiramente fictício. Perguntar **Qual é o prazo para solicitar uma bolsa?** Abrir uma fonte para conferir **15 de março de 2026, às 18h**. Mostrar que trechos relevantes, e não todo o manual, entraram na consulta.

Em modo real, mostrar nome, motivo e uso do modelo econômico. Em modo demo, explicar explicitamente que a resposta é extração local e a escolha de modelo foi simulada.

## Slide 3 · Contexto longo · 1 minuto

O exemplo tem aproximadamente 22 mil tokens estimados de conteúdo, com entrada limitada a 6 mil por chamada. A consulta usa chunking com sobreposição e seleção BM25. Perguntar pelo **código exclusivo de conferência do último anexo** e conferir **JACARANDÁ-482**.

Abrir **Resumir documento** e mostrar resumos parciais e síntese. Todos os 45 trechos entram em lotes; o sistema comprime novamente quando a soma dos resumos ainda não cabe na entrada.

## Slide 4 · Prompts e roteamento · 1 minuto

Perguntar **Compare as perspectivas da coordenação e dos estudantes sobre a carga horária**. Mostrar a mudança para a rota de análise.

Explicar a regra: factual → econômico; análise/múltiplos documentos → maior capacidade; resumo parcial → econômico; síntese → maior capacidade. Falhas transitórias ou saída inválida têm uma tentativa de fallback. A aplicação escolhe o modelo explicitamente.

O prompt define papel, público, idioma, limites de evidência e exemplos. A saída JSON é validada, e citações inventadas acionam fallback. Citação válida ainda exige conferência humana do conteúdo.

## Slide 5 · Resultados e limites · 1 minuto

Mostrar os relatórios: 25 testes automatizados, seis cenários com 18 verificações locais e 11 fluxos no navegador. Todos os trechos do exemplo foram incluídos no resumo. A busca alcançou a informação exclusiva do fim do arquivo.

Mostrar uma pergunta sem correspondência e explicar a economia de uma chamada. Demonstrar que sinônimos podem exigir reformulação. Não há OCR nem memória entre perguntas.

**Antes da apresentação final:** executar a rodada real do OpenRouter e preencher a rubrica. Não apresentar resultados simulados como medida de qualidade de LLM. Se a rodada ainda não foi feita, declarar a pendência e mostrar os testes de contrato como tal.

## Slide 6 · Contexto de circulação e equipe · 1 minuto

O manual inclui coordenação e estudantes para discutir como perspectivas mudam os sentidos do texto. O resumo deve preservar essas vozes, condições e exceções. Modelos podem omitir informações; as fontes permitem revisar o recorte.

O MVP é local e usa dados sintéticos. O modo real envia trechos ao provedor externo. Encerrar com o papel de cada integrante, usando o registro de contribuições reais. Indicar próximos passos sustentados pelos testes: avaliação com usuários, melhoria da recuperação e autenticação se houver hospedagem compartilhada.

## Preparação da demonstração

- Rodar o servidor, abrir a interface e confirmar o modo ativo.
- Importar o exemplo e deixar apenas ele selecionado para o resumo.
- Conferir rede, saldo e IDs dos modelos antes de apresentar o modo real.
- Preparar os relatórios locais para demonstrar contexto e fallback sem depender da rede.
- Preencher a avaliação de LLM e os nomes/contribuições do grupo antes da entrega.
