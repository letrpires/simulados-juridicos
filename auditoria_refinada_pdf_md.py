import fitz
import re
import shutil
from pathlib import Path

PASTA_PDFS = Path("pdfs")
PASTA_MD = Path("md_estruturado")
PASTA_OK = Path("ok")
PASTA_QUESTOES = Path("questoes_geradas_ok")

PASTA_AUDITORIA = Path("auditoria")
PASTA_CRITICOS = Path("conferir_pdf_criticos")
PASTA_CONFERIR = Path("conferir_pdf_leve")

PASTA_AUDITORIA.mkdir(exist_ok=True)
PASTA_CRITICOS.mkdir(exist_ok=True)
PASTA_CONFERIR.mkdir(exist_ok=True)


def extrair_texto_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    texto = ""

    for i, page in enumerate(doc, start=1):
        texto += f"\n\n===== PÁGINA {i} =====\n\n"
        texto += page.get_text("text")

    return texto, len(doc)


def contar_julgados_md(texto):
    return len(re.findall(r"^## Julgado\s+\d+", texto, flags=re.MULTILINE))


def contar_referencias_pdf(texto):
    padrao = (
        r"(?:STJ|STF)\.\s*"
        r".{0,500}?"
        r"\(Info\s+\d+(?:\s*-\s*Edição\s+Extraordinária)?\)\."
    )
    return len(re.findall(padrao, texto, flags=re.DOTALL | re.IGNORECASE))


def nome_md_correspondente(pdf_path):
    return PASTA_MD / f"{pdf_path.stem}_limpo_estruturado.md"


def nome_questoes_correspondente(pdf_path):
    return PASTA_QUESTOES / f"{pdf_path.stem}_questoes.md"


def classificar(qtd_paginas, refs_pdf, julgados_md, tamanho_pdf, tamanho_md, md_existe):
    motivos = []

    if not md_existe:
        return "CRÍTICO", ["MD correspondente não encontrado"]

    if julgados_md == 0:
        return "CRÍTICO", ["MD sem julgados"]

    if tamanho_md < tamanho_pdf * 0.35:
        return "CRÍTICO", ["MD muito menor que o texto extraído do PDF"]

    diferenca = refs_pdf - julgados_md

    if diferenca >= 3:
        return "CRÍTICO", [f"PDF tem {diferenca} referências a mais que julgados no MD"]

    if diferenca in [1, 2]:
        return "CONFERIR", [f"PDF tem {diferenca} referência(s) a mais que julgados no MD"]

    if qtd_paginas <= 2 and julgados_md <= 1 and refs_pdf >= 2:
        return "CRÍTICO", ["PDF curto com mais referências que julgados no MD"]

    return "OK", motivos


def copiar_para_pasta(origem: Path, destino_pasta: Path):
    if origem.exists():
        shutil.copy2(origem, destino_pasta / origem.name)


def main():
    pdfs = sorted(PASTA_PDFS.glob("*.pdf"))

    linhas = []
    linhas.append("# Auditoria refinada PDF x MD")
    linhas.append("")

    contagem = {
        "OK": 0,
        "CONFERIR": 0,
        "CRÍTICO": 0,
    }

    for pdf in pdfs:
        texto_pdf, qtd_paginas = extrair_texto_pdf(pdf)
        refs_pdf = contar_referencias_pdf(texto_pdf)
        tamanho_pdf = len(texto_pdf)

        md_path = nome_md_correspondente(pdf)
        md_existe = md_path.exists()

        if md_existe:
            texto_md = md_path.read_text(encoding="utf-8")
            julgados_md = contar_julgados_md(texto_md)
            tamanho_md = len(texto_md)
        else:
            julgados_md = 0
            tamanho_md = 0

        status, motivos = classificar(
            qtd_paginas=qtd_paginas,
            refs_pdf=refs_pdf,
            julgados_md=julgados_md,
            tamanho_pdf=tamanho_pdf,
            tamanho_md=tamanho_md,
            md_existe=md_existe
        )

        contagem[status] += 1

        linhas.append(f"## {pdf.name}")
        linhas.append(f"- Status: {status}")
        linhas.append(f"- Páginas PDF: {qtd_paginas}")
        linhas.append(f"- Referências no PDF: {refs_pdf}")
        linhas.append(f"- Julgados no MD: {julgados_md}")
        linhas.append(f"- Tamanho PDF: {tamanho_pdf}")
        linhas.append(f"- Tamanho MD: {tamanho_md}")

        if motivos:
            linhas.append("- Motivos:")
            for m in motivos:
                linhas.append(f"  - {m}")

        linhas.append("")

        # Copiar arquivos para conferência
        if status == "CRÍTICO":
            copiar_para_pasta(pdf, PASTA_CRITICOS)
            copiar_para_pasta(md_path, PASTA_CRITICOS)
            copiar_para_pasta(nome_questoes_correspondente(pdf), PASTA_CRITICOS)

        elif status == "CONFERIR":
            copiar_para_pasta(pdf, PASTA_CONFERIR)
            copiar_para_pasta(md_path, PASTA_CONFERIR)

    linhas.append("---")
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append(f"- OK: {contagem['OK']}")
    linhas.append(f"- Conferir: {contagem['CONFERIR']}")
    linhas.append(f"- Crítico: {contagem['CRÍTICO']}")

    saida = PASTA_AUDITORIA / "relatorio_refinado_pdf_vs_md.md"
    saida.write_text("\n".join(linhas), encoding="utf-8")

    print(f"Relatório gerado em: {saida}")
    print("Resumo:")
    print(f"OK: {contagem['OK']}")
    print(f"Conferir: {contagem['CONFERIR']}")
    print(f"Crítico: {contagem['CRÍTICO']}")
    print("")
    print(f"Críticos copiados para: {PASTA_CRITICOS}")
    print(f"Conferir copiados para: {PASTA_CONFERIR}")


if __name__ == "__main__":
    main()