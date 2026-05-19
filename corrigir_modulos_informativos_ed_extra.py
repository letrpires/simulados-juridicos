import json
import re
from pathlib import Path
from collections import Counter

ARQ = Path("data/questoes.json")
BACKUP = Path("data/backups/questoes_backup_antes_corrigir_modulos.json")

dados = json.loads(ARQ.read_text(encoding="utf-8"))
BACKUP.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

alterados = 0

def extrair_numero(q):
    texto = " ".join(str(q.get(k, "")) for k in ["id", "modulo", "referencia", "titulo", "tema"])
    m = re.search(r"(?:info|informativo)[^\d]*(\d{3,4})", texto, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"ed\.?\s*extra[^\d]*(\d{1,3})", texto, re.I)
    if m:
        return int(m.group(1))
    return None

for q in dados:
    antigo = q.get("modulo", "")
    texto = " ".join(str(q.get(k, "")) for k in ["id", "modulo", "referencia", "titulo", "tema"])
    novo = antigo

    # Edição Extraordinária STJ
    m_extra = re.search(r"ed\.?\s*extra[^\d]*(\d{1,3})", texto, re.I)
    if m_extra:
        n = int(m_extra.group(1))
        if 14 <= n <= 21:
            novo = "STJ Edição Extraordinária 2024"
        elif 22 <= n <= 27:
            novo = "STJ Edição Extraordinária 2025"
        elif 28 <= n <= 30:
            novo = "STJ Edição Extraordinária 2026"

    # Informativos STJ
    elif "stj" in texto.lower():
        n = extrair_numero(q)
        if n:
            if 800 <= n <= 837:
                novo = "Informativos STJ 2024"
            elif 838 <= n <= 874:
                novo = "Informativos STJ 2025"
            elif n >= 875:
                novo = "Informativos STJ 2026"

    # Informativos STF
    elif "stf" in texto.lower():
        n = extrair_numero(q)
        if n:
            if 1121 <= n <= 1162:
                novo = "Informativos STF 2024"
            elif 1163 <= n <= 1202:
                novo = "Informativos STF 2025"
            elif n >= 1203:
                novo = "Informativos STF 2026"

    if novo != antigo:
        q["modulo"] = novo
        alterados += 1

ARQ.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

print("✅ Módulos corrigidos:", alterados)
print("Backup:", BACKUP)

print("\nResumo por módulo:")
for mod, total in Counter(q.get("modulo") for q in dados).most_common():
    print(total, "-", mod)
