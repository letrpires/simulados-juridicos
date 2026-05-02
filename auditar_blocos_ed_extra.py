from pathlib import Path
import re

PASTA = Path("md_criticos_reprocessados")

for num in [17, 18]:
    arq = PASTA / f"Ed. Extra {num} STJ_limpo_estruturado.md"

    print("\n" + "=" * 80)
    print(f"ED. EXTRA {num}")
    print("=" * 80)

    if not arq.exists():
        print("Arquivo não encontrado")
        continue

    txt = arq.read_text(encoding="utf-8", errors="ignore")
    blocos = re.split(r"\n## Julgado\s+\d+\n", txt)[1:]

    print("Total:", len(blocos))

    for i, bloco in enumerate(blocos, 1):
        disc = re.search(r"\*\*Disciplina:\*\*\s*(.*)", bloco)
        tese = re.search(r"\*\*Tese / entendimento:\*\*\s*(.*?)(?:\n\*\*Referência:\*\*)", bloco, re.S)

        primeira = ""
        if tese:
            linhas = [l.strip() for l in tese.group(1).splitlines() if l.strip()]
            primeira = linhas[0] if linhas else ""

        print(f"{i:02d}. {disc.group(1) if disc else ''} | {primeira[:120]}")
