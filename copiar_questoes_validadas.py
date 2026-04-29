from pathlib import Path
import re
import shutil

RELATORIO = Path("auditoria/relatorio_refinado_pdf_vs_md.md")
PASTA_QUESTOES = Path("questoes_geradas_ok")
PASTA_DESTINO = Path("questoes_validadas_pdf")

PASTA_DESTINO.mkdir(exist_ok=True)


def extrair_oks(relatorio: str):
    blocos = re.split(r"(?=^## .+\.pdf)", relatorio, flags=re.MULTILINE)
    oks = []

    for bloco in blocos:
        if "- Status: OK" not in bloco:
            continue

        m = re.search(r"^## (.+?)\.pdf", bloco, flags=re.MULTILINE)
        if not m:
            continue

        nome_base = m.group(1)
        oks.append(nome_base)

    return oks


def main():
    texto = RELATORIO.read_text(encoding="utf-8")
    oks = extrair_oks(texto)

    copiados = 0
    faltantes = []

    for nome_base in oks:
        origem = PASTA_QUESTOES / f"{nome_base}_questoes.md"

        if origem.exists():
            shutil.copy2(origem, PASTA_DESTINO / origem.name)
            copiados += 1
        else:
            faltantes.append(origem.name)

    print(f"Arquivos OK no relatório: {len(oks)}")
    print(f"Questões copiadas: {copiados}")

    if faltantes:
        print("\nArquivos de questões não encontrados:")
        for f in faltantes:
            print(f"- {f}")


if __name__ == "__main__":
    main()