import json
from pathlib import Path

JSON = Path("data/questoes.json")
dados = json.loads(JSON.read_text(encoding="utf-8"))

novos = [
    q for q in dados
    if q.get("categoria") not in ["Repercussão Geral", "Repetitivos"]
]

print("Antes:", len(dados))
print("Depois:", len(novos))
print("Removidos:", len(dados) - len(novos))

JSON.write_text(json.dumps(novos, ensure_ascii=False, indent=2), encoding="utf-8")
