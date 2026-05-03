import json
import re
from pathlib import Path

JSON_PATH = Path("data/questoes.json")

FONTES = [
    Path("md_criticos_reprocessados"),
    Path("questoes_validadas_pdf"),
]

REFERENCIAS_GENERICAS = {
    "Informativos STJ",
    "Informativos STF",
    "Informativos STJ 2024",
    "Informativos STJ 2025",
    "Informativos STJ 2026",
    "Informativos STF 2024",
    "Informativos STF 2025",
    "Informativos STF 2026",
    "STJ Edição Extraordinária 2024",
    "STJ Edição Extraordinária 2025",
    "STJ Edição Extraordinária 2026",
    "Edição Extraordinária",
}

def normalizar_ref(ref):
    return " ".join(str(ref or "").strip().split())

def tipo_arquivo(nome):
    m = re.search(r"Ed\.?\s*Extra\s+(\d+)\s+STJ", nome, re.I)
    if m:
        return "extra", "STJ", str(int(m.group(1)))

    m = re.search(r"Info\s+(\d+)\s+(STF|STJ)", nome, re.I)
    if m:
        return "info", m.group(2).upper(), str(int(m.group(1)))

    return None, None, None

def dividir_blocos(txt):
    if re.search(r"\n## Julgado\s+\d+", txt):
        return re.split(r"\n## Julgado\s+\d+", txt)[1:]

    if re.search(r"\n## Questão\s+\d+", txt):
        return re.split(r"\n## Questão\s+\d+", txt)[1:]

    return []

def extrair_ref(bloco):
    # 1. Campo explícito
    m = re.search(
        r"\*\*Referência:\*\*\s*(.*?)(?=\n\*\*|\n---|\n##|\Z)",
        bloco,
        re.S | re.I
    )
    if m:
        ref = normalizar_ref(m.group(1))
        if ref and ref not in REFERENCIAS_GENERICAS:
            return ref

    # 2. Linha ou trecho começando por STJ/STF
    m = re.search(
        r"((?:STJ|STF)\..*?(?:\(Info\s+\d+.*?\)|\(Tema\s+\d+.*?\)|julgado.*?\)|DJe.*?|\.))",
        bloco,
        re.S | re.I
    )
    if m:
        ref = normalizar_ref(m.group(1))
        if ref and ref not in REFERENCIAS_GENERICAS:
            return ref

    return ""

def numero_questao(qid):
    m = re.search(r"q(\d+)$", str(qid or ""))
    return int(m.group(1)) if m else None

def dados_questao(q):
    qid = str(q.get("id") or "").lower()
    tribunal = q.get("tribunal")

    # Edição Extra pelo ID
    m = re.search(r"extra-(\d+)-q(\d+)$", qid)
    if m:
        return "extra", "STJ", str(int(m.group(1))), int(m.group(2))

    # Informativo pelo ID
    m = re.search(r"informativo-(\d+)-q(\d+)$", qid)
    if m:
        return "info", tribunal, str(int(m.group(1))), int(m.group(2))

    # Fallback por campos
    tipo = "extra" if q.get("tipo") == "edicao_extraordinaria" or q.get("categoria") == "Edição Extraordinária" else "info"
    numero = str(int(q.get("informativo"))) if q.get("informativo") not in [None, ""] else ""
    return tipo, tribunal, numero, numero_questao(q.get("id"))

def referencia_ruim(ref):
    ref = normalizar_ref(ref)
    if not ref:
        return True
    if ref in REFERENCIAS_GENERICAS:
        return True
    if ref.startswith("Informativos "):
        return True
    if ref.startswith("STJ Edição Extraordinária"):
        return True
    if ref.startswith("STF Edição Extraordinária"):
        return True
    return False

# Monta mapa: (tipo, tribunal, numero, q) -> referência real
mapa = {}

for pasta in FONTES:
    if not pasta.exists():
        continue

    for md in sorted(pasta.glob("*.md")):
        tipo, tribunal, numero = tipo_arquivo(md.name)
        if not tipo:
            continue

        txt = md.read_text(encoding="utf-8", errors="ignore")
        blocos = dividir_blocos(txt)

        for i, bloco in enumerate(blocos, 1):
            ref = extrair_ref(bloco)
            if ref:
                mapa[(tipo, tribunal, numero, i)] = ref

print("Referências reais mapeadas:", len(mapa))

dados = json.loads(JSON_PATH.read_text(encoding="utf-8"))

corrigidas = 0
sem_match = []

for q in dados:
    if not referencia_ruim(q.get("referencia")):
        continue

    chave = dados_questao(q)

    if chave in mapa:
        q["referencia"] = mapa[chave]
        corrigidas += 1
    else:
        sem_match.append((q.get("id"), chave, q.get("referencia")))

JSON_PATH.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

print("Corrigidas:", corrigidas)
print("Sem match:", len(sem_match))

for item in sem_match[:30]:
    print("Sem match:", item)
