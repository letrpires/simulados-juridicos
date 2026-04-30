from pathlib import Path
import re

entrada = Path("sumulas_extraidas_md/sumula_stj_limpa.md")
saida = Path("sumulas_extraidas_md/sumula_stj_limpa_padrao.md")

texto = entrada.read_text(encoding="utf-8")

linhas = [l.strip() for l in texto.splitlines() if l.strip()]

blocos = []

for linha in linhas:
    m = re.match(r"Súmula\s+(\d+)\s+do\s+STJ:\s*(.+)", linha, re.I)
    if not m:
        continue

    numero = m.group(1)
    enunciado = m.group(2).strip()

    blocos.append(
        f"## Súmula STJ {numero}\n\n"
        f"**Enunciado:**\n"
        f"{enunciado}\n\n"
        f"---"
    )

saida.write_text(
    "# Súmulas STJ\n\n" + "\n\n".join(blocos),
    encoding="utf-8"
)

print(f"Gerado: {saida}")
print(f"Total convertido: {len(blocos)}")
