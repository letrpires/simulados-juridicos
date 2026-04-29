from pathlib import Path

PASTA_QUESTOES = Path("questoes_validadas_pdf")
PASTA_HTML = Path("html_simulados")
PASTA_AUDITORIA = Path("auditoria")

PASTA_AUDITORIA.mkdir(exist_ok=True)


def nome_base_questao(arq: Path):
    return arq.stem.replace("_questoes", "").strip()


def nome_base_html(arq: Path):
    return arq.stem.strip()


def main():
    questoes = sorted(PASTA_QUESTOES.glob("*.md"))
    htmls = sorted([h for h in PASTA_HTML.glob("*.html") if h.name != "index.html"])

    bases_questoes = {nome_base_questao(q): q.name for q in questoes}
    bases_html = {nome_base_html(h): h.name for h in htmls}

    faltando_html = sorted(set(bases_questoes) - set(bases_html))
    html_sem_md = sorted(set(bases_html) - set(bases_questoes))
    ok = sorted(set(bases_questoes) & set(bases_html))

    linhas = []
    linhas.append("# Auditoria - Questões validadas x HTML")
    linhas.append("")
    linhas.append(f"- Arquivos de questões: {len(questoes)}")
    linhas.append(f"- Arquivos HTML: {len(htmls)}")
    linhas.append(f"- Já convertidos: {len(ok)}")
    linhas.append(f"- Faltando HTML: {len(faltando_html)}")
    linhas.append(f"- HTML sem MD correspondente: {len(html_sem_md)}")
    linhas.append("")

    linhas.append("## Faltando gerar HTML")
    linhas.append("")
    if faltando_html:
        for nome in faltando_html:
            linhas.append(f"- {bases_questoes[nome]}")
    else:
        linhas.append("Nenhum.")
    linhas.append("")

    linhas.append("## HTML sem arquivo .md correspondente")
    linhas.append("")
    if html_sem_md:
        for nome in html_sem_md:
            linhas.append(f"- {bases_html[nome]}")
    else:
        linhas.append("Nenhum.")
    linhas.append("")

    saida = PASTA_AUDITORIA / "relatorio_questoes_vs_html.md"
    saida.write_text("\n".join(linhas), encoding="utf-8")

    print(f"Relatório gerado em: {saida}")
    print(f"Questões: {len(questoes)}")
    print(f"HTMLs: {len(htmls)}")
    print(f"Faltando HTML: {len(faltando_html)}")
    print(f"HTML sem MD: {len(html_sem_md)}")


if __name__ == "__main__":
    main()
