import json
from pathlib import Path
from datetime import datetime

JSON_SITE = Path("data/questoes.json")
LOTES_DIR = Path("questoes_rg_repetitivos_limpo")

backup = Path("data/backups") / f"backup_antes_incorporar_rg_repetitivos_limpo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
backup.parent.mkdir(parents=True, exist_ok=True)

dados = json.loads(JSON_SITE.read_text(encoding="utf-8"))
backup.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

# remove RG/Repetitivos antigos
base_sem_antigos = [
    q for q in dados
    if q.get("categoria") not in ["Repercussão Geral", "Repetitivos"]
]

novas = []
ids_novos = set()

for arq in sorted(LOTES_DIR.glob("*.json")):
    lote = json.loads(arq.read_text(encoding="utf-8"))

    for q in lote:
        novo_id = f"{q['id_base']}-q001"

        if novo_id in ids_novos:
            print(f"⚠️ DUPLICADO IGNORADO: {novo_id}")
            continue

        ids_novos.add(novo_id)

        q["id"] = novo_id
        q["tipo"] = "tema"
        q["fonte"] = q.get("referencia", "")

        q.pop("id_base", None)
        q.pop("tema_numero", None)

        novas.append(q)


final = base_sem_antigos + novas

JSON_SITE.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")

print("Backup:", backup)
print("Base anterior:", len(dados))
print("Sem RG/Repetitivos antigos:", len(base_sem_antigos))
print("Novas RG/Repetitivos:", len(novas))
print("Total final:", len(final))
