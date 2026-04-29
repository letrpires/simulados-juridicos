import fitz
from pathlib import Path

PASTA_PDFS = Path("reprocessar_criticos")
PASTA_SAIDA = Path("txt_criticos_brutos")

PASTA_SAIDA.mkdir(exist_ok=True)

def extrair(pdf_path):
    doc = fitz.open(pdf_path)
    linhas = []

    linhas.append(f"# {pdf_path.stem}")
    linhas.append("")

    for i, page in enumerate(doc, start=1):
        linhas.append(f"\n\n===== PÁGINA {i} =====\n\n")
        linhas.append(page.get_text("text"))

    saida = PASTA_SAIDA / f"{pdf_path.stem}.txt"
    saida.write_text("\n".join(linhas), encoding="utf-8")
    print(f"Gerado: {saida}")

def main():
    for pdf in sorted(PASTA_PDFS.glob("*.pdf")):
        extrair(pdf)

if __name__ == "__main__":
    main()