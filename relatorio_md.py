from pathlib import Path
import re
from collections import defaultdict

PASTAS = {
    "ok": Path("ok"),
    "revisao_leve": Path("revisao_leve"),
    "revisao_critica": Path("revisao_critica"),
}


def extrair_julgados(texto):
    return re.split(r"\n## Julgado \d+\n", texto)[1:]


def extrair_disciplina(julgado):
    match = re.search(r"\*\*Disciplina:\*\*\s*(.+)", julgado)
    return match.group(1).strip() if match else "N/I"


def campo_vazio(julgado):
    return (
        "**Título do julgado:**\n\n" in julgado
        or "**Tese / entendimento:**\n\n" in julgado
        or "**Disciplina:** N/I" in julgado
    )


def analisar_pasta(nome, caminho):
    arquivos = list(caminho.glob("*.md"))

    total_julgados = 0
    disciplinas = defaultdict(int)
    incompletos = 0

    print(f"\n📂 Pasta: {nome.upper()}")

    for arquivo in arquivos:
        texto = arquivo.read_text(encoding="utf-8")

        julgados = extrair_julgados(texto)
        total_julgados += len(julgados)

        for j in julgados:
            disciplina = extrair_disciplina(j)
            disciplinas[disciplina] += 1

            if campo_vazio(j):
                incompletos += 1

    print(f"Arquivos: {len(arquivos)}")
    print(f"Julgados: {total_julgados}")
    print(f"Incompletos: {incompletos}")

    print("\nDisciplinas:")
    for d, q in sorted(disciplinas.items(), key=lambda x: -x[1]):
        print(f"  {d}: {q}")


def main():
    for nome, caminho in PASTAS.items():
        if caminho.exists():
            analisar_pasta(nome, caminho)
        else:
            print(f"Pasta não encontrada: {nome}")


if __name__ == "__main__":
    main()