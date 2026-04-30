from pathlib import Path
import re

entrada = Path("sumulas_extraidas_md/sumula_stj_corrigida.md")
saida = Path("sumulas_extraidas_md/sumula_stj_limpa.md")

conteudo = entrada.read_text(encoding="utf-8")

blocos = re.split(r"\n## Súmula STJ \d+\n", conteudo)

resultado = []
numeros = re.findall(r"## Súmula STJ (\d+)", conteudo)

for i, bloco in enumerate(blocos[1:]):
    numero = numeros[i]

    # pega só o enunciado
    m = re.search(r"\*\*Enunciado:\*\*\n(.+)", bloco, re.S)
    if not m:
        continue

    texto = m.group(1)

    # remove metadados finais (tudo que começa com "(SÚMULA")
    texto = re.sub(r"\(SÚMULA.*", "", texto)

    # remove lixo
    texto = texto.replace("VEJA MAIS", "")
    texto = re.sub(r"http\S+", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    # remove canceladas
    if "CANCELAMENTO" in texto.upper():
        continue

    if len(texto) < 20:
        continue

    resultado.append(f"Súmula {numero} do STJ: {texto}")

saida.write_text("\n\n".join(resultado), encoding="utf-8")

print(f"Gerado: {saida}")
print(f"Total: {len(resultado)}")
