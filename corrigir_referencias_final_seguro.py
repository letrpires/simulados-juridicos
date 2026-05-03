import json
import re
from pathlib import Path

JSON_PATH = Path("data/questoes.json")

FONTES = [
    Path("md_criticos_reprocessados"),
    Path("questoes_validadas_pdf"),
]

def tipo_questao(q):
    if q.get("categoria") == "Edição Extraordinária":
        return "extra"
    if q.get("categoria") == "Informativos":
        return "info"
    return "outros"

def referencia_ruim(ref):
    ref = str(ref or "").strip()

    if ref.startswith("Informativos "):
        return True

    if ref.startswith("STJ Edição Extraordinária"):
        return True

    return False

def extrair_info_md(nome):
    m = re.search(r"Ed\.?\s*Extra\s+(\d+)\s+STJ", nome, re.I)
    if m:
        return "extra", "STJ", str(int(m.group(1)))

    m = re.search(r"Info\s+(\d+)\s+(STF|STJ)", nome, re.I)
    if m:
        return "info", m.group(2).upper(), str(int(m.group(1)))

    return None, None, None

def dividir_blocos(txt):
    if "## Julgado" in txt:
        return re.split(r"\n## Julgado\s+\d+", txt)[1:]
    if "## Questão" in txt:
        return re.split(r"\n## Questão\s+\d+", txt)[1:]
    return []

def extrair_ref(bloco):
    m = re.search(r"\*\*Referência:\*\*\s*(.*?)(?=\n\*\*|\n---|\Z)", bloco, re.S)
    if m:
        ref = " ".join(m.group(1).strip().split())
        if ref:
            return ref

    m = re.search(r"(STJ\..*?\)|STF\..*?\))", bloco, re.S)
    if m:
        return " ".join(m.group(1).strip().split())

    return ""

def numero_q(id):
    m = re.search(r"q(\d+)$", str(id))
    return int(m.group(1)) if m else None

# MAPA
mapa = {}

for pasta in FONTES:
    if not pasta.exists():
        continue

    for md in pasta.glob("*.md"):
        tipo, tribunal, numero = extrair_info_md(md.name)
        if not tipo:
            continue

        txt = md.read_text(encoding="utf-8", errors="ignore")
        blocos = dividir_blocos(txt)

        for i, bloco in enumerate(blocos, 1):
            ref = extrair_ref(bloco)
            if ref:
                mapa[(tipo, tribunal, numero, i)] = ref

print("Mapeadas:", len(mapa))

dados = json.loads(JSON_PATH.read_text(encoding="utf-8"))

corrigidas = 0

for q in dados:

    tipo = tipo_questao(q)

    # 🔒 BLOQUEIO TOTAL PARA NÃO ESTRAGAR
    if tipo not in ["info", "extra"]:
        continue

    if not referencia_ruim(q.get("referencia")):
        continue

    tribunal = q.get("tribunal")
    numero = str(int(q.get("informativo"))) if q.get("informativo") else ""
    n = numero_q(q.get("id"))

    chave = (tipo, tribunal, numero, n)

    if chave in mapa:
        q["referencia"] = mapa[chave]
        corrigidas += 1

JSON_PATH.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

print("Corrigidas:", corrigidas)
