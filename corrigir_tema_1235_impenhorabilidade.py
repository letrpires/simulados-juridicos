import json
from pathlib import Path

ARQ = Path("data/questoes.json")

dados = json.loads(ARQ.read_text(encoding="utf-8"))

corrigidas = 0

nova_justificativa = """
O artigo 833, inciso X, do CPC estabelece a impenhorabilidade de valores inferiores a 40 salários mínimos em aplicações financeiras. À época do julgamento do AgInt no AREsp 2.220.880-RS, a 1ª Turma do STJ entendia que essa impenhorabilidade possuía natureza de ordem pública, podendo ser reconhecida de ofício pelo magistrado, independentemente de manifestação da parte executada, cabendo ao credor demonstrar eventual abuso, má-fé ou fraude.

Contudo, esse entendimento foi posteriormente superado pela Corte Especial do STJ no julgamento do Tema Repetitivo 1235. Fixou-se a tese de que a impenhorabilidade de quantia inferior a 40 salários mínimos (art. 833, X, do CPC) não constitui matéria de ordem pública e não pode ser reconhecida de ofício pelo juiz, devendo ser alegada pelo executado no primeiro momento em que lhe couber falar nos autos, em embargos à execução ou impugnação ao cumprimento de sentença, sob pena de preclusão.

Assim, atualmente, é incorreto afirmar que o magistrado pode determinar de ofício a liberação dos valores constritos com fundamento automático na impenhorabilidade prevista no art. 833, X, do CPC.

STJ. 1ª Turma. AgInt no AREsp 2.220.880-RS, Rel. Min. Paulo Sérgio Domingues, julgado em 26/2/2024 (Info 811).

STJ. Corte Especial. REsps 2.061.973-PR e 2.066.882-RS, Rel. Min. Nancy Andrighi, julgado em 2/10/2024 (Tema Repetitivo 1235) (Info 828).
""".strip()

for q in dados:
    enunciado = q.get("enunciado", "")

    if (
        q.get("categoria") == "Informativos"
        and str(q.get("informativo")) == "811"
        and q.get("tribunal") == "STJ"
        and "impenhorabilidade presumida de valores inferiores a 40 salários mínimos" in enunciado
    ):
        q["respostaCorreta"] = "E"
        q["explicacao"] = nova_justificativa
        corrigidas += 1

    # INFO 807 - DIREITO DE RESPOSTA
    if (
        q.get("categoria") == "Informativos"
        and str(q.get("informativo")) == "807"
        and q.get("tribunal") == "STJ"
        and "direito de resposta previsto na antiga Lei de Imprensa" in enunciado
    ):

        q["respostaCorreta"] = "C"

        q["explicacao"] = """
O caso concreto envolvia uma ação proposta com o único pedido de direito de resposta, vinculado a suposta injúria e calúnia em editorial jornalístico e fundamentado nos dispositivos da antiga Lei de Imprensa (Lei nº 5.250/67).

O STJ entende que o direito de resposta previsto na antiga Lei de Imprensa possuía natureza de sanção penal, submetendo-se às normas do Código de Processo Penal e devendo a ação ser processada no Juízo Criminal. Logo, a competência para apreciá-lo – caso ainda não tenha sido julgado – é de um dos órgãos julgadores com competência criminal (5ª ou 6ª Turmas).

STJ. Corte Especial. CC 195.616-DF, Rel. Min. Antonio Carlos Ferreira, julgado em 21/2/2024 (Info 807).
""".strip()

        corrigidas += 1

ARQ.write_text(
    json.dumps(dados, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"✅ Questões corrigidas: {corrigidas}")
