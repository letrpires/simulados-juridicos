import json
import re
from pathlib import Path

JSON = Path("data/questoes.json")

FONTES = [
    Path("md_criticos_reprocessados"),
    Path("questoes_validadas_pdf"),
]

def tipo(q):
    if q.get("categoria") == "Informativos":
        return "info"
    if q.get("categoria") == "Edição Extraordinária":
        return "extra"
    if q.get("categoria") == "Repercussão Geral":
        return "rg"
    if q.get("categoria") == "Repetitivos":
        return "rep"
    return "outros"

def ruim(ref):
    ref = str(ref or "")
    return (
        ref.startswith("Informativos ")
        or ref.startswith("STJ Edição Extraordinária")
        or ref.startswith("RG ")
        or ref.startswith("RG –")
        or ref.startswith("Repetitivo")
    )

def extrair_ref(bloco):
    m = re.search(r"\*\*Referência:\*\*\s*(.*?)(?=\n|\Z)", bloco, re.S)
    if m:
        return " ".join(m.group(1).split())

    m = re.search(r"(STF\..*?\)|STJ\..*?\))", bloco, re.S)
    if m:
        return " ".join(m.group(1).split())

    return ""

def dividir(txt):
    if "## Julgado" in txt:
        return re.split(r"\n## Julgado\s+\d+", txt)[1:]
    if "## Questão" in txt:
        return re.split(r"\n## Questão\s+\d+", txt)[1:]
    return []

def numero_q(id):
    m = re.search(r"q(\d+)$", str(id))
    return int(m.group(1)) if m else None

def chave_md(nome):
    m = re.search(r"Ed\.?\s*Extra\s+(\d+)\s+STJ", nome, re.I)
    if m:
        return "extra", "STJ", str(int(m.group(1)))

    m = re.search(r"Info\s+(\d+)\s+(STF|STJ)", nome, re.I)
    if m:
        return "info", m.group(2), str(int(m.group(1)))

    return None

# mapa geral
mapa = {}

for pasta in FONTES:
    if not pasta.exists():
        continue

    for md in pasta.glob("*.md"):
        base = chave_md(md.name)
        if not base:
            continue

        txt = md.read_text(encoding="utf-8", errors="ignore")
        blocos = dividir(txt)

        for i, bloco in enumerate(blocos, 1):
            ref = extrair_ref(bloco)
            if ref:
                mapa[(*base, i)] = ref

print("Mapeadas:", len(mapa))

dados = json.loads(JSON.read_text())

corrigidas = 0

for q in dados:

    t = tipo(q)

    # 🔒 NÃO MEXER EM SÚMULAS
    if t == "outros":
        continue

    if not ruim(q.get("referencia")):
        continue

    tribunal = q.get("tribunal")
    numero = str(int(q.get("informativo"))) if q.get("informativo") else ""
    n = numero_q(q.get("id"))

    chave = (t, tribunal, numero, n)

    # fallback: tentar como info/extra
    alt1 = ("info", tribunal, numero, n)
    alt2 = ("extra", tribunal, numero, n)

    if chave in mapa:
        q["referencia"] = mapa[chave]
        corrigidas += 1
    elif alt1 in mapa:
        q["referencia"] = mapa[alt1]
        corrigidas += 1
    elif alt2 in mapa:
        q["referencia"] = mapa[alt2]
        corrigidas += 1

JSON.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

print("Corrigidas:", corrigidas)
