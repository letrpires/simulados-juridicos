import json
from pathlib import Path
from datetime import datetime

JSON = Path("data/questoes.json")
dados = json.loads(JSON.read_text(encoding="utf-8"))

backup = Path("data/backups") / f"backup_antes_padronizar_modulos_rg_repetitivos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
backup.parent.mkdir(parents=True, exist_ok=True)
backup.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

alteradas = 0

for q in dados:
    if q.get("categoria") == "Repercussão Geral" and q.get("modulo") != "Repercussão Geral":
        q["modulo"] = "Repercussão Geral"
        alteradas += 1

    if q.get("categoria") == "Repetitivos" and q.get("modulo") != "Repetitivos":
        q["modulo"] = "Repetitivos"
        alteradas += 1

JSON.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
print("Backup:", backup)
print("Módulos alterados:", alteradas)
