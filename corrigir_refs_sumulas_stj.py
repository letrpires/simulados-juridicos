import json
import re
from pathlib import Path

JSON = Path("data/questoes.json")
MD = Path("questoes_validadas_pdf/Sumulas STJ.md")

dados = json.loads(JSON.read_text(encoding="utf-8"))
txt = MD.read_text(encoding="utf-8", errors="ignore")

blocos = re.split(r"\n## Questão\s+\d+", txt)[1:]

refs = []

for bloco in blocos:
    m = re.search(r"TITULO_ORIGEM:\s*(Súmula\s+\d+\s+STJ)", bloco, re.I)
    refs.append(m.group(1).strip() if m else "")

sumulas_stj = [
    q for q in dados
    if q.get("categoria") == "Súmulas" and q.get("tribunal") == "STJ"
]

print("Questões STJ no JSON:", len(sumulas_stj))
print("Referências no MD:", len(refs))

if len(sumulas_stj) != len(refs):
    raise SystemExit("❌ Quantidades divergentes. Não alterei nada.")

corrigidas = 0

for q, ref in zip(sumulas_stj, refs):
    if ref:
        q["referencia"] = ref
        corrigidas += 1

JSON.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

print("✅ Súmulas STJ corrigidas:", corrigidas)
