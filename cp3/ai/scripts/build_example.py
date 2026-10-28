"""Recria o anexo sintético determinístico, sem dados pessoais."""

from pathlib import Path

path = Path(__file__).resolve().parents[1] / "examples/manual-aurora.md"
base = path.read_text().split("\n## Anexo — casos sintéticos")[0]
cases = [
    (
        "matrícula",
        "A pessoa apresentou comprovante com emissão há 12 dias e proposta com aceite da orientação.",
        "O comprovante atende ao prazo de emissão de até 30 dias. Os demais critérios precisam de avaliação própria.",
    ),
    (
        "renda",
        "A declaração informa renda familiar per capita equivalente a 1,5 salário mínimo.",
        "O valor declarado está dentro do limite de dois salários mínimos. A comissão deve conferir a documentação.",
    ),
    (
        "cuidado",
        "A pessoa divide a rotina entre aulas e cuidado de familiar, e propõe atividades assíncronas.",
        "A proposta pode ser discutida como adequação de horário. O objetivo de acompanhamento continua válido.",
    ),
    (
        "pagamento",
        "O registro de atividades de abril foi enviado dentro do prazo e validado pela orientação.",
        "A primeira parcela será processada em maio. O manual prevê pagamento até o quinto dia útil do mês seguinte.",
    ),
    (
        "recurso",
        "Uma candidatura aponta que a avaliação deixou de considerar o aceite enviado na inscrição.",
        "O recurso pode contestar erro de leitura. Deve indicar o critério e a evidência, dentro do prazo publicado.",
    ),
    (
        "acessibilidade",
        "A pessoa solicita transcrição de um encontro gravado para acompanhar a atividade.",
        "A equipe deve acolher a solicitação e planejar o formato acessível sem exposição pública da condição.",
    ),
    (
        "pesquisa",
        "A hipótese inicial não foi confirmada pelos dados e o relatório explica as limitações do método.",
        "Resultado negativo não impede conclusão. A avaliação deve considerar a participação e o registro dos resultados.",
    ),
    (
        "residência",
        "O comprovante de residência não está no nome da pessoa candidata, que envia declaração.",
        "A declaração pode substituir o comprovante. Não se deve exigir conta própria quando o manual admite alternativa.",
    ),
]
annex = "\n## Anexo — casos sintéticos\n\nOs 48 casos são exercícios de leitura, sem decisão real sobre pessoas.\n"
for i in range(1, 49):
    theme, situation, interpretation = cases[(i - 1) % len(cases)]
    annex += (
        f"\n### Registro AUR-{i:03d} · {theme}\n\n"
        f"Situação fictícia: {situation} O registro AUR-{i:03d} foi incluído no lote de treinamento "
        f"{(i - 1) // 8 + 1}, para comparação de decisões de leitura entre integrantes do grupo.\n\n"
        f"Leitura procedimental: {interpretation} Essa conclusão é limitada ao item descrito e não "
        "equivale à aprovação da candidatura. Quando faltarem documentos, a análise deve dizer o que "
        "precisa ser verificado, sem preencher lacunas com suposições.\n\n"
        "Ressalva de contexto: a forma de redigir uma solicitação pode refletir diferentes oportunidades "
        "de acesso à linguagem acadêmica. A equipe deve separar o conteúdo do pedido de impressões "
        "sobre estilo, evitando que vocabulário técnico se transforme em requisito informal. "
        "A justificativa da decisão deve ser curta, compreensível e ligada ao critério publicado.\n"
    )
annex += (
    "\n## Informação exclusiva do encerramento\n\n"
    "O código de conferência do último anexo é JACARANDÁ-482. Esse código identifica somente "
    "esta versão fictícia do material e não deve ser usado como credencial ou número de inscrição. "
    "A reunião final de avaliação do material de demonstração ocorrerá na Sala Ipê. "
    "Não há endereço físico informado para essa sala.\n"
)
path.write_text(base + annex)
print(f"Exemplo gerado: {len((base + annex).encode())} bytes")
