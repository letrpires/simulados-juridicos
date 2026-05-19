import re
from pathlib import Path

BASE = Path("rg_temas.md")
LOTE = Path("rg_lote_001.txt")
SAIDA = Path("rg_lote_001.md")

alvos = {int(x) for x in LOTE.read_text().split() if x.strip().isdigit()}
txt = BASE.read_text(encoding="utf-8", errors="ignore")

partes = re.split(r"\n(?=STF\s*\nRepercussão\s*\nTema\s+\d+)", txt)
selecionados = []

for bloco in partes:
    m = re.search(r"Tema\s+(\d+)", bloco)
    if m and int(m.group(1)) in alvos:
        selecionados.append(bloco.strip())

SAIDA.write_text("\n\n\n".join(selecionados) + "\n", encoding="utf-8")

print("Temas pedidos:", len(alvos))
print("Blocos extraídos:", len(selecionados))
print("Arquivo criado:", SAIDA)
