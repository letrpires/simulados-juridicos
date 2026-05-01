import json
import re
import csv
from pathlib import Path
from collections import defaultdict

JSON_PATH = Path("data/questoes.json")
SAIDA = Path("auditoria_final/auditoria_temas_informativos.csv")
SAIDA.parent.mkdir(exist_ok=True)

dados = json.loads(JSON_PATH.read_text(encoding="utf-8"))

def temas_no_texto(*partes):
    texto = " ".join(str(p or "") for p in partes)

    achados = re.findall(
        r"\bTema\s*(?:n[ºo.]?\s*)?(\d[\d.]*)",
        texto,
        flags=re.I,
    )

    temas = set()
    for n in achados:
        n = n.strip(".")
        n_limpo = n.replace(".", "")
        if n_limpo.isdigit():
            temas.add(f"Tema {int(n_limpo)}")

    return sorted(temas, key=lambda x: int(x.split()[1]))

existentes = defaultdict(list)

# Base própria: só tema/referência, para evitar falso positivo em explicação.
for q in dados:
    cat = q.get("categoria")
    if cat not in ["Repetitivos", "Repercussão Geral"]:
        continue
    # Informativos: usar SOMENTE a referência para evitar "Tema 1" contaminado
    for tema in temas_no_texto(q.get("referencia")):
        existentes[(cat, tema)].append(q.get("id"))

linhas = []

# Informativos: só referência/tema, para evitar capturar menções laterais.
for q in dados:
    if q.get("categoria") != "Informativos":
        continue

    tribunal = q.get("tribunal")

    if tribunal == "STJ":
        cat_destino = "Repetitivos"
    elif tribunal == "STF":
        cat_destino = "Repercussão Geral"
    else:
        continue

    # Informativos: usar SOMENTE a referência para evitar "Tema 1" contaminado
    for tema in temas_no_texto(q.get("referencia")):
        ids = existentes.get((cat_destino, tema), [])

        linhas.append({
            "tema": tema,
            "categoria_destino": cat_destino,
            "ja_existe_na_base_propria": "SIM" if ids else "NAO",
            "qtd_existente": len(ids),
            "ids_existentes": " | ".join(ids),
            "id_informativo": q.get("id"),
            "fonte_informativo": q.get("fonte"),
            "referencia_informativo": q.get("referencia"),
        })

with SAIDA.open("w", encoding="utf-8-sig", newline="") as f:
    campos = [
        "tema",
        "categoria_destino",
        "ja_existe_na_base_propria",
        "qtd_existente",
        "ids_existentes",
        "id_informativo",
        "fonte_informativo",
        "referencia_informativo",
    ]
    w = csv.DictWriter(f, fieldnames=campos)
    w.writeheader()
    w.writerows(linhas)

ja = sum(1 for l in linhas if l["ja_existe_na_base_propria"] == "SIM")
faltam = sum(1 for l in linhas if l["ja_existe_na_base_propria"] == "NAO")

print("✅ Auditoria gerada:", SAIDA)
print("Total de temas encontrados em informativos:", len(linhas))
print("Já existem:", ja)
print("Faltam:", faltam)
