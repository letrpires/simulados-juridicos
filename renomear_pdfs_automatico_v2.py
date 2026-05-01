import re
import json
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF

PASTA_PDFS = Path("pdfs")
PASTA_CONTROLE = Path("controle_processamento")
PASTA_CONTROLE.mkdir(exist_ok=True)

RELATORIO = PASTA_CONTROLE / "relatorio_renomeacao_pdfs.json"


def ler_texto_inicial(pdf_path: Path, max_paginas: int = 3) -> str:
    partes = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            if i >= max_paginas:
                break
            partes.append(page.get_text("text") or "")
    return "\n".join(partes)


def identificar_info(texto: str):
    m = re.search(r"Informativo\s+(\d{3,4})\s*[-–]?\s*(STJ|STF)", texto, re.I)
    if not m:
        return None

    numero = m.group(1)
    tribunal = m.group(2).upper()
    return numero, tribunal


def extrair_temas(texto: str):
    temas = []

    padroes = [
        r"Recurso\s+Repetitivo\s*[–-]\s*Tema\s*(\d{1,5})",
        r"Tema\s*(\d{1,5})",
    ]

    for padrao in padroes:
        for m in re.finditer(padrao, texto, re.I):
            tema = f"Tema {m.group(1)}"
            if tema not in temas:
                temas.append(tema)

    return temas


def nome_unico(destino: Path) -> Path:
    if not destino.exists():
        return destino

    base = destino.stem
    ext = destino.suffix
    i = 2

    while True:
        novo = destino.with_name(f"{base} ({i}){ext}")
        if not novo.exists():
            return novo
        i += 1


def main():
    registros = []

    pdfs = sorted(PASTA_PDFS.glob("*.pdf"))

    if not pdfs:
        print("❌ Nenhum PDF encontrado em pdfs/")
        return

    print(f"📚 PDFs encontrados: {len(pdfs)}")

    for pdf in pdfs:
        try:
            texto = ler_texto_inicial(pdf)
            info = identificar_info(texto)
            temas = extrair_temas(texto)

            if not info:
                print(f"⚠️ Não identificado: {pdf.name}")
                registros.append({
                    "arquivo_original": pdf.name,
                    "status": "NAO_IDENTIFICADO",
                    "temas_detectados": temas,
                    "data": datetime.now().isoformat()
                })
                continue

            numero, tribunal = info
            novo_nome = f"Info {numero} {tribunal}.pdf"
            destino = nome_unico(pdf.with_name(novo_nome))

            if pdf.name == destino.name:
                status = "JA_CORRETO"
                print(f"✅ Já correto: {pdf.name}")
            else:
                pdf.rename(destino)
                status = "RENOMEADO"
                print(f"✅ Renomeado: {pdf.name} → {destino.name}")

            if temas:
                print(f"   🎯 Temas detectados: {', '.join(temas)}")

            registros.append({
                "arquivo_original": pdf.name,
                "arquivo_final": destino.name,
                "status": status,
                "informativo": numero,
                "tribunal": tribunal,
                "temas_detectados": temas,
                "data": datetime.now().isoformat()
            })

        except Exception as e:
            print(f"❌ Erro em {pdf.name}: {e}")
            registros.append({
                "arquivo_original": pdf.name,
                "status": "ERRO",
                "erro": str(e),
                "data": datetime.now().isoformat()
            })

    RELATORIO.write_text(
        json.dumps(registros, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\n🧾 Relatório salvo em: {RELATORIO}")


if __name__ == "__main__":
    main()
