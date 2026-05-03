import json
import re
from pathlib import Path

JSON_PATH = Path("data/questoes.json")
PASTA_Q = Path("questoes_validadas_pdf")
PASTA_REF = Path("md_criticos_reprocessados")

NUMEROS = [14, 15, 16, 17, 18, 19, 20, 21]

dados = json.loads(JSON_PATH.read_text(encoding="utf-8"))
ids = {q["id"] for q in dados}

def campo(bloco, nome):
    m = re.search(
        rf"\*\*{nome}:\*\*\s*(.*?)(?=\n\*\*|\n---|\n## Questão|\Z)",
        bloco,
        re.S | re.I
    )
    return m.group(1).strip() if m else ""

def refs_do_md(num):
    md = PASTA_REF / f"Ed. Extra {num} STJ_limpo_estruturado.md"
    txt = md.read_text(encoding="utf-8", errors="ignore")
    blocos = re.split(r"\n## Julgado\s+\d+", txt)[1:]
    refs = []
    for bloco in blocos:
        ref = campo(bloco, "Referência")
        refs.append(" ".join(ref.split()))
    return refs

def questoes_do_md(num):
    md = PASTA_Q / f"Ed. Extra {num} STJ_questoes.md"
    txt = md.read_text(encoding="utf-8", errors="ignore")
    return re.split(r"\n## Questão\s+\d+", txt)[1:]

adicionadas = 0
puladas = []

for num in NUMEROS:
    questoes = questoes_do_md(num)
    refs = refs_do_md(num)

    print(f"Ed. Extra {num}: questões={len(questoes)} | refs={len(refs)}")

    if len(questoes) != len(refs):
        puladas.append((num, len(questoes), len(refs)))
        continue

    for i, bloco in enumerate(questoes, 1):
        qid = f"stj-2024-extra-{num}-q{i:03d}"
        if qid in ids:
            continue

        gab = campo(bloco, "Gabarito").upper()
        resp = "C" if "CERTO" in gab or gab == "C" else "E"

        dados.append({
            "id": qid,
            "categoria": "Edição Extraordinária",
            "modulo": "STJ Edição Extraordinária 2024",
            "tribunal": "STJ",
            "informativo": num,
            "tipo": "edicao_extraordinaria",
            "fonte": f"Ed. Extra {num} STJ",
            "disciplina": "",
            "tema": "",
            "enunciado": campo(bloco, "Enunciado"),
            "respostaCorreta": resp,
            "explicacao": campo(bloco, "Justificativa"),
            "referencia": refs[i-1],
        })

        ids.add(qid)
        adicionadas += 1

JSON_PATH.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

print("\nAdicionadas:", adicionadas)
print("Puladas por divergência:", puladas)
print("Total final:", len(dados))
