import json
import csv
import re
from pathlib import Path

JSON_PATH = Path("data/questoes.json")
CSV_PATH = Path("auditoria_final/auditoria_temas_informativos.csv")

dados = json.loads(JSON_PATH.read_text(encoding="utf-8"))

# -----------------------------
# 1. MAPA: ID -> QUESTÃO
# -----------------------------
mapa = {q["id"]: q for q in dados}

# -----------------------------
# 2. IDENTIFICAR TEMAS FALTANTES
# -----------------------------
faltantes = []

with CSV_PATH.open(encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        if row["ja_existe_na_base_propria"] == "NAO":
            faltantes.append(row)

# evitar duplicidade (tema + categoria)
chaves_vistas = set()
faltantes_unicos = []

for r in faltantes:
    chave = (r["tema"], r["categoria_destino"])
    if chave not in chaves_vistas:
        chaves_vistas.add(chave)
        faltantes_unicos.append(r)

# -----------------------------
# 3. GERAR NOVAS QUESTÕES
# -----------------------------
novas = []
contador = 1

for r in faltantes_unicos:
    origem_id = r["id_informativo"]
    origem = mapa.get(origem_id)

    if not origem:
        continue

    nova = origem.copy()

    nova["id"] = f"tema-gerado-{contador:04d}"
    nova["categoria"] = r["categoria_destino"]
    nova["modulo"] = r["categoria_destino"]
    nova["tema"] = r["tema"]
    nova["espelhado_de_informativo"] = origem_id

    novas.append(nova)
    contador += 1

# -----------------------------
# 4. SALVAR
# -----------------------------
dados_final = dados + novas

JSON_PATH.write_text(
    json.dumps(dados_final, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("✅ Temas criados:", len(novas))
