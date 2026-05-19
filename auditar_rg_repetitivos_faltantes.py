import json
import re
from pathlib import Path

JSON = Path("data/questoes.json")
RG_MD = Path("rg_temas.md")
REP_MD = Path("repetitivos_temas.md")

dados = json.loads(JSON.read_text(encoding="utf-8"))

def temas_do_md(path, repetitivo=False):
    txt = path.read_text(encoding="utf-8", errors="ignore")
    if repetitivo:
        padrao = r"Tema(?:\s+Repetitivo)?\s+(\d+)"
    else:
        padrao = r"Tema(?:\s+RG|\s+de\s+Repercuss[aã]o\s+Geral)?\s+(\d+)"
    return sorted({int(x) for x in re.findall(padrao, txt, flags=re.I)})

def tema_da_questao(q):
    texto = " ".join(str(q.get(k,"")) for k in [
        "id","referencia","fonte","tema","modulo","enunciado","explicacao"
    ])
    m = re.search(r"Tema(?:\s+Repetitivo|\s+RG|\s+de\s+Repercuss[aã]o\s+Geral)?\s+(\d+)", texto, flags=re.I)
    return int(m.group(1)) if m else None

rg_base = temas_do_md(RG_MD, repetitivo=False)
rep_base = temas_do_md(REP_MD, repetitivo=True)

rg_json = sorted({
    tema_da_questao(q) for q in dados
    if q.get("categoria") == "Repercussão Geral"
    and tema_da_questao(q) is not None
})

rep_json = sorted({
    tema_da_questao(q) for q in dados
    if q.get("categoria") == "Repetitivos"
    and q.get("tribunal") == "STJ"
    and tema_da_questao(q) is not None
})

rg_faltantes = sorted(set(rg_base) - set(rg_json))
rep_faltantes = sorted(set(rep_base) - set(rep_json))

Path("auditoria_rg_faltantes.txt").write_text("\n".join(map(str, rg_faltantes)) + "\n", encoding="utf-8")
Path("auditoria_repetitivos_faltantes.txt").write_text("\n".join(map(str, rep_faltantes)) + "\n", encoding="utf-8")

print("===== RG =====")
print("Temas oficiais:", len(rg_base))
print("Temas no JSON:", len(rg_json))
print("Faltantes:", len(rg_faltantes))
print("Primeiros:", rg_faltantes[:80])

print("\n===== REPETITIVOS STJ =====")
print("Temas oficiais:", len(rep_base))
print("Temas no JSON:", len(rep_json))
print("Faltantes:", len(rep_faltantes))
print("Primeiros:", rep_faltantes[:80])

print("\nArquivos criados:")
print("- auditoria_rg_faltantes.txt")
print("- auditoria_repetitivos_faltantes.txt")
