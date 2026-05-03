import json
import re
from pathlib import Path

JSON = Path("data/questoes.json")

FONTES_MD = [
    Path("md_criticos_reprocessados"),
    Path("questoes_validadas_pdf"),
]

def extrair_item(nome):
    # Info normal
    m = re.search(r"Info\s+(\d+)\s+(STF|STJ)", nome, re.I)
    if m:
        return m.group(2).upper(), str(int(m.group(1)))

    # Edição Extra
    m = re.search(r"Ed\.?\s*Extra\s+(\d+)\s+STJ", nome, re.I)
    if m:
        return "STJ", str(int(m.group(1)))

    return None, None

def extrair_blocos(txt):
    if re.search(r"\n## Julgado\s+\d+", txt):
        return re.split(r"\n## Julgado\s+\d+", txt)[1:]
    if re.search(r"\n## Questão\s+\d+", txt):
        return re.split(r"\n## Questão\s+\d+", txt)[1:]
    return []

def extrair_ref_do_bloco(bloco):
    # 1) padrão explícito
    m = re.search(
        r"\*\*Referência:\*\*\s*(.*?)(?=\n\*\*|\n---|\n##|\Z)",
        bloco,
        re.S | re.I
    )
    if m:
        ref = " ".join(m.group(1).strip().split())
        if ref and ref not in ["Informativos STJ", "Informativos STF"]:
            return ref

    # 2) linha iniciada por STJ/STF
    m = re.search(r"((?:STJ|STF)\..*?(?:Info\s+\d+.*?|Tema\s+\d+.*?|julgado.*?|\)\.))", bloco, re.S | re.I)
    if m:
        ref = " ".join(m.group(1).strip().split())
        if ref and ref not in ["Informativos STJ", "Informativos STF"]:
            return ref

    return ""

def qnum(qid):
    m = re.search(r"q(\d+)$", qid or "")
    return int(m.group(1)) if m else None

mapa = {}

for pasta in FONTES_MD:
    if not pasta.exists():
        continue

    for md in sorted(pasta.glob("*.md")):
        tribunal, numero = extrair_item(md.name)
        if not tribunal or not numero:
            continue

        txt = md.read_text(encoding="utf-8", errors="ignore")
        blocos = extrair_blocos(txt)

        for i, bloco in enumerate(blocos, 1):
            ref = extrair_ref_do_bloco(bloco)
            if ref:
                mapa[(tribunal, numero, i)] = ref

print("Referências mapeadas:", len(mapa))

dados = json.loads(JSON.read_text(encoding="utf-8"))

corrigidas = 0
sem_match = []

for q in dados:
    if q.get("referencia") not in ["Informativos STJ", "Informativos STF"]:
        continue

    tribunal = q.get("tribunal")
    numero = str(int(q.get("informativo"))) if q.get("informativo") not in [None, ""] else ""
    n = qnum(q.get("id"))

    chave = (tribunal, numero, n)

    if chave in mapa:
        q["referencia"] = mapa[chave]
        corrigidas += 1
    else:
        sem_match.append((q.get("id"), chave))

JSON.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

print("Corrigidas:", corrigidas)
print("Sem match:", len(sem_match))

for item in sem_match[:20]:
    print("Sem match:", item)
