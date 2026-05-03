import json
import re
from pathlib import Path

JSON = Path("data/questoes.json")

dados = json.loads(JSON.read_text(encoding="utf-8"))

corrigidas = 0

for q in dados:

    modulo = str(q.get("modulo",""))

    if "Súmula" not in modulo:
        continue

    texto = " ".join([
        q.get("enunciado",""),
        q.get("explicacao",""),
        q.get("justificativa","")
    ])

    # Súmula Vinculante
    m = re.search(r"S[úu]mula\s+Vinculante\s+(\d+)", texto, re.I)
    if m:
        num = m.group(1)
        q["referencia"] = f"Súmula Vinculante {num} STF"
        corrigidas += 1
        continue

    # Súmula STF
    m = re.search(r"S[úu]mula\s+(\d+)\s+STF", texto, re.I)
    if m:
        num = m.group(1)
        q["referencia"] = f"Súmula {num} STF"
        corrigidas += 1
        continue

    # Súmula STJ
    m = re.search(r"S[úu]mula\s+(\d+)\s+STJ", texto, re.I)
    if m:
        num = m.group(1)
        q["referencia"] = f"Súmula {num} STJ"
        corrigidas += 1
        continue

JSON.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

print("Súmulas corrigidas:", corrigidas)
