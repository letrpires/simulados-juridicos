import re
from pathlib import Path
import fitz  # PyMuPDF

PASTA_PDFS = Path("pdfs")

def extrair_nome_pdf(caminho):
    try:
        with fitz.open(caminho) as doc:
            texto = doc[0].get_text("text")  # primeira página

        # padrão: Informativo 833-STJ
        match = re.search(r"Informativo\s+(\d{3,4})[-\s]*(STJ|STF)", texto, re.IGNORECASE)
        if match:
            numero = match.group(1)
            tribunal = match.group(2).upper()
            return f"Info {numero} {tribunal}.pdf"

    except Exception as e:
        print(f"Erro ao ler {caminho.name}: {e}")

    return None


def main():
    for pdf in PASTA_PDFS.glob("*.pdf"):
        novo_nome = extrair_nome_pdf(pdf)

        if not novo_nome:
            print(f"⚠️ Não identificado: {pdf.name}")
            continue

        destino = pdf.with_name(novo_nome)

        if destino.exists():
            print(f"⚠️ Já existe: {destino.name}")
            continue

        pdf.rename(destino)
        print(f"✅ Renomeado: {pdf.name} → {novo_nome}")


if __name__ == "__main__":
    main()
