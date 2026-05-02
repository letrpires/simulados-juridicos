import re
import json
from pathlib import Path
from datetime import datetime
import fitz

PASTA_PDFS = Path("pdfs")
RELATORIO = Path("controle_processamento/relatorio_renomeacao_pdfs.json")
RELATORIO.parent.mkdir(exist_ok=True)


def ler_texto(pdf_path):
    texto = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            if i >= 3:
                break
            texto.append(page.get_text() or "")
    return "\n".join(texto)


def identificar_info(texto, nome_arquivo):
    # Cabeçalho principal: Informativo 1202-STF / Informativo 16-STJ
    m = re.search(r"Informativo\s+(\d{2,4})\s*[-–—]?\s*(STJ|STF)", texto, re.I)

    if m:
        numero = m.group(1)
        tribunal = m.group(2).upper()

        # Regra segura:
        # STJ com número pequeno (16, 22, 30 etc.) = edição extraordinária
        if tribunal == "STJ" and int(numero) < 100:
            return numero, tribunal, "extra"

        return numero, tribunal, "normal"

    # fallback pelo nome do arquivo
    m2 = re.search(
        r"(?:Info\s*(\d{2,4})\s*(STJ|STF)|Ed\.?\s*Extra(?:ordin[aá]ria)?\s*(\d{2,4})\s*STJ)",
        nome_arquivo,
        re.I
    )

    if m2:
        if m2.group(3):
            return m2.group(3), "STJ", "extra"

        numero = m2.group(1)
        tribunal = m2.group(2).upper()
        tipo = "extra" if tribunal == "STJ" and int(numero) < 100 else "normal"
        return numero, tribunal, tipo

    return None, None, None

def extrair_temas(texto):
    encontrados = set()

    for m in re.finditer(r"Tema\s*(\d{2,5})", texto):
        num = m.group(1)

        # ignora ruído
        if num == "1":
            continue

        encontrados.add(f"Tema {num}")

    return sorted(encontrados)


def nome_final(numero, tribunal, tipo):
    if tipo == "extra":
        return f"Ed. Extra {numero} STJ.pdf"
    return f"Info {numero} {tribunal}.pdf"


def main():
    registros = []

    for pdf in sorted(PASTA_PDFS.glob("*.pdf")):
        try:
            texto = ler_texto(pdf)
            info = identificar_info(texto, pdf.name)
            temas = extrair_temas(texto)

            numero, tribunal, tipo = info
            
            if not numero or not tribunal:
                print(f"⚠️ Não identificado: {pdf.name}")
                registros.append({
                    "arquivo": pdf.name,
                    "status": "NAO_IDENTIFICADO",
                    "temas": temas
                })
                continue
          
            novo_nome = nome_final(numero, tribunal, tipo)

            # 🔒 NÃO RENOMEIA SE JÁ ESTÁ CERTO
            if pdf.name == novo_nome:
                print(f"✅ Já correto: {pdf.name}")
                status = "JA_CORRETO"
                destino = pdf

            else:
                destino = pdf.with_name(novo_nome)

                if destino.exists():
                    print(f"⚠️ Já existe destino: {novo_nome} (mantido)")
                    status = "CONFLITO"
                else:
                    pdf.rename(destino)
                    print(f"✅ Renomeado: {pdf.name} → {novo_nome}")
                    status = "RENOMEADO"

            if temas:
                print(f"   🎯 Temas: {', '.join(temas)}")

            registros.append({
                "original": pdf.name,
                "final": destino.name,
                "status": status,
                "tipo": tipo,
                "temas": temas
            })

        except Exception as e:
            print(f"❌ Erro em {pdf.name}: {e}")

    RELATORIO.write_text(json.dumps(registros, indent=2, ensure_ascii=False))
    print("\n🧾 Relatório atualizado.")


if __name__ == "__main__":
    main()
