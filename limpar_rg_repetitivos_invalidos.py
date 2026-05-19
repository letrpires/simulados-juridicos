import json
import re
from pathlib import Path
from datetime import datetime

JSON = Path("data/questoes.json")

RG_MD = Path("rg_temas.md")
REP_MD = Path("repetitivos_temas.md")

if not JSON.exists():
    raise SystemExit("❌ Não achei data/questoes.json")

if not RG_MD.exists():
    raise SystemExit("❌ Não achei rg_temas.md")

if not REP_MD.exists():
    raise SystemExit("❌ Não achei repetitivos_temas.md")

dados = json.loads(JSON.read_text(encoding="utf-8"))

backup_dir = Path("data/backups")
backup_dir.mkdir(parents=True, exist_ok=True)

backup = backup_dir / f'questoes_backup_antes_limpeza_rg_repetitivos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

backup.write_text(
    json.dumps(dados, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print(f"✅ Backup criado: {backup}")

# =========================================================
# 1. LER BASES OFICIAIS
# =========================================================

rg_txt = RG_MD.read_text(encoding="utf-8", errors="ignore")
rep_txt = REP_MD.read_text(encoding="utf-8", errors="ignore")

temas_rg_oficiais = {
    int(x)
    for x in re.findall(
        r"Tema(?:\s+RG|\s+de\s+Repercuss[aã]o\s+Geral)?\s+(\d+)",
        rg_txt,
        flags=re.I
    )
}

temas_rep_oficiais = {
    int(x)
    for x in re.findall(
        r"Tema(?:\s+Repetitivo)?\s+(\d+)",
        rep_txt,
        flags=re.I
    )
}

print(f"Temas oficiais RG: {len(temas_rg_oficiais)}")
print(f"Temas oficiais Repetitivos STJ: {len(temas_rep_oficiais)}")

# =========================================================
# 2. PADRÕES DE QUESTÕES-LIXO / PLACEHOLDERS
# =========================================================

PADROES_LIXO = [
    r"aguarda julgamento",
    r"aguardando julgamento",
    r"mérito ainda não julgado",
    r"merito ainda nao julgado",
    r"não sendo possível extrair",
    r"nao sendo possivel extrair",
    r"não é possível extrair",
    r"nao e possivel extrair",
    r"não possui tese",
    r"nao possui tese",
    r"sem tese firmada",
    r"sem tese definida",
    r"sem entendimento firmado",
    r"não há tese",
    r"nao ha tese",
    r"tema pendente",
    r"pendente de julgamento",
    r"aguardando a publicação do acórdão",
    r"aguardando publicacao do acordao",
    r"não foi fixada tese",
    r"nao foi fixada tese",
]

def normalizar(txt):
    txt = str(txt).lower()
    return (
        txt.replace("ã", "a")
           .replace("á", "a")
           .replace("à", "a")
           .replace("â", "a")
           .replace("é", "e")
           .replace("ê", "e")
           .replace("í", "i")
           .replace("ó", "o")
           .replace("ô", "o")
           .replace("ú", "u")
           .replace("ç", "c")
    )

def eh_lixo(q):
    texto = normalizar(" ".join([
        str(q.get("enunciado", "")),
        str(q.get("explicacao", "")),
        str(q.get("justificativa", "")),
        str(q.get("referencia", "")),
        str(q.get("tema", "")),
        str(q.get("fonte", "")),
    ]))

    for padrao in PADROES_LIXO:
        if re.search(normalizar(padrao), texto):
            return True

    return False

def extrair_tema(q):
    texto = " ".join([
        str(q.get("referencia", "")),
        str(q.get("fonte", "")),
        str(q.get("tema", "")),
        str(q.get("modulo", "")),
        str(q.get("enunciado", "")),
    ])

    m = re.search(
        r"Tema(?:\s+Repetitivo|\s+RG|\s+de\s+Repercuss[aã]o\s+Geral)?\s+(\d+)",
        texto,
        flags=re.I
    )

    if m:
        return int(m.group(1))

    m = re.search(
        r"(?:tema|rg|rep|repetitivo)[-_]?(\d{1,4})",
        str(q.get("id", "")),
        flags=re.I
    )

    if m:
        return int(m.group(1))

    return None

# =========================================================
# 3. LIMPEZA COM TRAVA ABSOLUTA POR CATEGORIA
# =========================================================

novos = []

removidos_lixo = []
removidos_sem_base = []

mantidos_rg_rep = 0
intocados_outras_categorias = 0

for q in dados:

    categoria = str(q.get("categoria", "")).strip()

    # NÃO mexe em Informativos, Súmulas etc.
    if categoria not in ["Repercussão Geral", "Repetitivos"]:
        novos.append(q)
        intocados_outras_categorias += 1
        continue

    qid = q.get("id", "SEM_ID")

    # remove placeholders/lixo
    if eh_lixo(q):
        removidos_lixo.append({
            "id": qid,
            "categoria": categoria,
            "referencia": q.get("referencia", ""),
            "motivo": "placeholder/lixo",
        })
        continue

    tema = extrair_tema(q)

    # sem tema identificável
    if tema is None:
        removidos_sem_base.append({
            "id": qid,
            "categoria": categoria,
            "tema": "sem_tema",
            "referencia": q.get("referencia", ""),
            "motivo": "sem tema identificável",
        })
        continue

    # RG
    if categoria == "Repercussão Geral":
        if tema not in temas_rg_oficiais:
            removidos_sem_base.append({
                "id": qid,
                "categoria": categoria,
                "tema": tema,
                "referencia": q.get("referencia", ""),
                "motivo": "tema não existe na base RG oficial",
            })
            continue

    # Repetitivos
    if categoria == "Repetitivos":
        if tema not in temas_rep_oficiais:
            removidos_sem_base.append({
                "id": qid,
                "categoria": categoria,
                "tema": tema,
                "referencia": q.get("referencia", ""),
                "motivo": "tema não existe na base Repetitivos oficial",
            })
            continue

    novos.append(q)
    mantidos_rg_rep += 1

# =========================================================
# 4. SALVAR JSON + RELATÓRIO
# =========================================================

JSON.write_text(
    json.dumps(novos, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

relatorio = {
    "antes": len(dados),
    "depois": len(novos),
    "intocados_outras_categorias": intocados_outras_categorias,
    "mantidos_rg_repetitivos": mantidos_rg_rep,
    "removidos_lixo": len(removidos_lixo),
    "removidos_sem_base": len(removidos_sem_base),
    "detalhe_removidos_lixo": removidos_lixo,
    "detalhe_removidos_sem_base": removidos_sem_base,
}

Path("relatorio_limpeza_rg_repetitivos.json").write_text(
    json.dumps(relatorio, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

Path("relatorio_limpeza_rg_repetitivos.txt").write_text(
    "RELATÓRIO DE LIMPEZA RG / REPETITIVOS\n"
    "=====================================\n\n"
    f"Antes: {len(dados)}\n"
    f"Depois: {len(novos)}\n"
    f"Intocados de outras categorias: {intocados_outras_categorias}\n"
    f"Mantidos RG/Repetitivos: {mantidos_rg_rep}\n"
    f"Removidos lixo/placeholders: {len(removidos_lixo)}\n"
    f"Removidos sem base oficial: {len(removidos_sem_base)}\n\n"
    "REMOVIDOS LIXO/PLACEHOLDER:\n"
    + "\n".join(
        f'{x["id"]} | {x["categoria"]} | {x["referencia"]}'
        for x in removidos_lixo
    )
    + "\n\nREMOVIDOS SEM BASE OFICIAL:\n"
    + "\n".join(
        f'{x["id"]} | {x["categoria"]} | {x["tema"]} | {x["referencia"]}'
        for x in removidos_sem_base
    ),
    encoding="utf-8"
)

print()
print("========== RELATÓRIO ==========")
print("Antes:", len(dados))
print("Depois:", len(novos))
print("Intocados de outras categorias:", intocados_outras_categorias)
print("Mantidos RG/Repetitivos:", mantidos_rg_rep)
print("Removidos lixo/placeholders:", len(removidos_lixo))
print("Removidos sem base oficial:", len(removidos_sem_base))

print()
print("Exemplos removidos lixo:")
for x in removidos_lixo[:20]:
    print("-", x["id"], "|", x["categoria"], "|", x["referencia"])

print()
print("Exemplos removidos sem base oficial:")
for x in removidos_sem_base[:20]:
    print("-", x["id"], "|", x["categoria"], "|", x["tema"], "|", x["referencia"])

print()
print("✅ JSON atualizado:", JSON)
print("✅ Relatório TXT: relatorio_limpeza_rg_repetitivos.txt")
print("✅ Relatório JSON: relatorio_limpeza_rg_repetitivos.json")
