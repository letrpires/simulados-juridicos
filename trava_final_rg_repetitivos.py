import json
from pathlib import Path
from datetime import datetime

JSON_SITE = Path("data/questoes.json")
LOTES_DIR = Path("questoes_rg_repetitivos_limpo")

backup = Path("data/backups") / f"backup_antes_trava_final_rg_repetitivos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
backup.parent.mkdir(parents=True, exist_ok=True)

dados = json.loads(JSON_SITE.read_text(encoding="utf-8"))
backup.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

# Remove qualquer RG/Repetitivo antigo gerado pelo pipeline
base = [
    q for q in dados
    if q.get("categoria") not in ["Repercussão Geral", "Repetitivos"]
]

novas = []
ids = set()

for arq in sorted(LOTES_DIR.glob("*.json")):
    lote = json.loads(arq.read_text(encoding="utf-8"))

    for q in lote:
        if not q:
            continue

        id_base = q.get("id_base")
        if not id_base:
            continue

        novo_id = f"{id_base}-q001"

        if novo_id in ids:
            continue

        ids.add(novo_id)

        item = dict(q)
        item["id"] = novo_id
        item["tipo"] = "tema"
        item["fonte"] = item.get("referencia", "")

        if item.get("categoria") == "Repercussão Geral":
            item["modulo"] = "Repercussão Geral"
            item["tribunal"] = "STF"
        elif item.get("categoria") == "Repetitivos":
            item["modulo"] = "Repetitivos"
            item["tribunal"] = "STJ"
        else:
            continue

        item.pop("id_base", None)
        item.pop("tema_numero", None)
        item.pop("disciplina", None)

        novas.append(item)

final = base + novas

JSON_SITE.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")

print("✅ TRAVA FINAL RG/REPETITIVOS APLICADA")
print("Backup:", backup)
print("Base sem RG/Repetitivos antigos:", len(base))
print("RG/Repetitivos limpos reincorporados:", len(novas))
print("Total final:", len(final))
