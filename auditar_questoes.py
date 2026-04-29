from pathlib import Path
import re

PASTA_MD = Path("ok")
PASTA_QUESTOES = Path("questoes_geradas_ok")
PASTA_AUDITORIA = Path("auditoria")

PASTA_AUDITORIA.mkdir(exist_ok=True)


def contar_julgados(texto: str) -> int:
    return len(re.findall(r"^## Julgado\s+\d+", texto, flags=re.MULTILINE))


def contar_questoes(texto: str) -> int:
    return len(re.findall(r"^## Questão\s+\d+", texto, flags=re.MULTILINE))


def nome_questoes(nome_md: str) -> str:
    return nome_md.replace("_limpo_estruturado.md", "_questoes.md")


def main():
    arquivos_md = sorted(PASTA_MD.glob("*.md"))

    linhas = []
    problemas = 0

    linhas.append("# Relatório de auditoria - MD estruturado x questões")
    linhas.append("")

    for md in arquivos_md:
        texto_md = md.read_text(encoding="utf-8")
        qtd_julgados = contar_julgados(texto_md)

        nome_q = nome_questoes(md.name)
        caminho_q = PASTA_QUESTOES / nome_q

        linhas.append(f"## {md.name}")
        linhas.append(f"- Julgados no MD: {qtd_julgados}")

        if not caminho_q.exists():
            linhas.append("- Questões geradas: ARQUIVO NÃO ENCONTRADO")
            linhas.append("- Status: ❌ PROBLEMA")
            linhas.append("")
            problemas += 1
            continue

        texto_q = caminho_q.read_text(encoding="utf-8")
        qtd_questoes = contar_questoes(texto_q)

        linhas.append(f"- Questões geradas: {qtd_questoes}")

        if qtd_julgados == qtd_questoes:
            linhas.append("- Status: ✅ OK")
        else:
            linhas.append(f"- Status: ⚠️ DIVERGÊNCIA — faltam/sobram {qtd_julgados - qtd_questoes}")
            problemas += 1

        linhas.append("")

    linhas.append("---")
    linhas.append("")
    linhas.append(f"Total de arquivos analisados: {len(arquivos_md)}")
    linhas.append(f"Total de problemas encontrados: {problemas}")

    saida = PASTA_AUDITORIA / "relatorio_md_vs_questoes.md"
    saida.write_text("\n".join(linhas), encoding="utf-8")

    print(f"Relatório gerado em: {saida}")
    print(f"Problemas encontrados: {problemas}")


if __name__ == "__main__":
    main()