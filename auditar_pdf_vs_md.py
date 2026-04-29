import fitz
import re
from pathlib import Path

PASTA_PDFS = Path("pdfs")
PASTA_MD = Path("md_estruturado")
PASTA_AUDITORIA = Path("auditoria")

PASTA_AUDITORIA.mkdir(exist_ok=True)


def extrair_texto_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    texto = ""

    for i, page in enumerate(doc, start=1):
        texto_pagina = page.get_text("text")
        texto += f"\n\n===== PÁGINA {i} =====\n\n"
        texto += texto_pagina

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


def classificar_suspeita(qtd_paginas, refs_pdf, julgados_md, tamanho_pdf, tamanho_md):
    motivos = []

    if julgados_md == 0:
        motivos.append("MD sem julgados")

    if refs_pdf > julgados_md:
        motivos.append(f"PDF parece ter mais referências ({refs_pdf}) que julgados no MD ({julgados_md})")

    if qtd_paginas <= 3 and julgados_md <= 1:
        motivos.append("PDF curto com 0 ou 1 julgado — conferir manualmente")

    if tamanho_md < tamanho_pdf * 0.25:
        motivos.append("MD muito menor que o texto extraído do PDF")

    if motivos:
        return "SUSPEITO", motivos

    return "OK", []


def main():
    pdfs = sorted(PASTA_PDFS.glob("*.pdf"))

    linhas = []
    linhas.append("# Auditoria PDF x MD estruturado")
    linhas.append("")

    suspeitos = 0

    for pdf in pdfs:
        md_path = nome_md_correspondente(pdf)

        texto_pdf, qtd_paginas = extrair_texto_pdf(pdf)
        tamanho_pdf = len(texto_pdf)
        refs_pdf = contar_referencias_pdf(texto_pdf)

        linhas.append(f"## {pdf.name}")
        linhas.append(f"- Páginas no PDF: {qtd_paginas}")
        linhas.append(f"- Referências detectadas no PDF: {refs_pdf}")

        if not md_path.exists():
            linhas.append("- MD correspondente: NÃO ENCONTRADO")
            linhas.append("- Status: ❌ SUSPEITO")
            linhas.append("")
            suspeitos += 1
            continue

        texto_md = md_path.read_text(encoding="utf-8")
        tamanho_md = len(texto_md)
        julgados_md = contar_julgados_md(texto_md)

        status, motivos = classificar_suspeita(
            qtd_paginas,
            refs_pdf,
            julgados_md,
            tamanho_pdf,
            tamanho_md
        )

        linhas.append(f"- Julgados no MD: {julgados_md}")
        linhas.append(f"- Tamanho texto PDF: {tamanho_pdf}")
        linhas.append(f"- Tamanho texto MD: {tamanho_md}")
        linhas.append(f"- Status: {'✅ OK' if status == 'OK' else '⚠️ SUSPEITO'}")

        if motivos:
            suspeitos += 1
            linhas.append("- Motivos:")
            for m in motivos:
                linhas.append(f"  - {m}")

        linhas.append("")

    linhas.append("---")
    linhas.append("")
    linhas.append(f"PDFs analisados: {len(pdfs)}")
    linhas.append(f"Arquivos suspeitos: {suspeitos}")

    saida = PASTA_AUDITORIA / "relatorio_pdf_vs_md.md"
    saida.write_text("\n".join(linhas), encoding="utf-8")

    print(f"Relatório gerado em: {saida}")
    print(f"Arquivos suspeitos: {suspeitos}")


if __name__ == "__main__":
    main()