#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrai PDFs de súmulas para arquivos Markdown-base limpos.

Uso recomendado:
  python3 extrair_sumulas_pdf_para_md.py --todos

Ou arquivo específico:
  python3 extrair_sumulas_pdf_para_md.py --arquivo "pdfs/Sumulas STF (até 736).pdf"

Saída:
  sumulas_extraidas_md/
  relatorio_extracao_sumulas_YYYY-MM-DD_HH-MM-SS.md
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import fitz  # PyMuPDF
except Exception:
    print("ERRO: instale PyMuPDF com: python3 -m pip install pymupdf")
    sys.exit(1)

PASTA_PDFS = Path("pdfs")
PASTA_SAIDA = Path("sumulas_extraidas_md")

PDFS_PADRAO = [
    "Sumulas STF (até 736).pdf",
    "Sumulas Vinculantes STF.pdf",
    "Sumulas Vinculantes STJ.pdf",
]


def ler_pdf(caminho: Path) -> str:
    doc = fitz.open(str(caminho))
    partes = []
    for i, page in enumerate(doc, start=1):
        txt = page.get_text("text") or ""
        partes.append(f"\n\n===== PÁGINA {i} =====\n\n{txt}")
    return "\n".join(partes)


def normalizar(txt: str) -> str:
    txt = txt.replace("\xa0", " ")
    txt = txt.replace("\u00ad", "")
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


def detectar_tipo(nome: str) -> str:
    n = nome.lower()
    if "vinculante" in n and "stf" in n:
        return "Súmula Vinculante STF"
    if "vinculante" in n and "stj" in n:
        return "Súmula Vinculante STJ"
    if "stf" in n:
        return "Súmula STF"
    if "stj" in n:
        return "Súmula STJ"
    return "Súmula"


def slug_tipo(tipo: str) -> str:
    mapa = str.maketrans({"ú": "u", "Ú": "U", "á": "a", "ã": "a", "â": "a", "é": "e", "í": "i", "ó": "o", "õ": "o", "ç": "c"})
    s = tipo.translate(mapa).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def limpar_enunciado(en: str) -> str:
    en = re.sub(r"===== PÁGINA \d+ =====", " ", en)
    en = re.sub(r"\bS[úu]mula(?: Vinculante)?\s*\d+\b", " ", en, flags=re.I)
    en = re.sub(r"\bEnunciado\b\s*:?", " ", en, flags=re.I)
    en = re.sub(r"\bAprovada em.*", " ", en, flags=re.I)
    en = re.sub(r"\bPublicada em.*", " ", en, flags=re.I)
    en = re.sub(r"\bRefer[êe]ncia[s]?\b.*", " ", en, flags=re.I)
    en = re.sub(r"\s+", " ", en)
    return en.strip(" -–—:\n\t")


def extrair_sumulas(texto: str, tipo: str) -> list[dict]:
    texto = normalizar(texto)

    # Padrões aceitos:
    # Súmula 123
    # SUMULA 123
    # Súmula Vinculante 63
    if "Vinculante" in tipo:
        pat = re.compile(r"(?:S[úu]mula\s+Vinculante|SV)\s*(?:n[ºo.]\s*)?(\d{1,4})\b", re.I)
    else:
        pat = re.compile(r"S[úu]mula\s*(?:n[ºo.]\s*)?(\d{1,4})\b", re.I)

    matches = list(pat.finditer(texto))
    itens = []
    vistos = set()

    for idx, m in enumerate(matches):
        num = int(m.group(1))
        if num in vistos:
            continue
        ini = m.end()
        fim = matches[idx + 1].start() if idx + 1 < len(matches) else len(texto)
        bloco = texto[ini:fim]
        en = limpar_enunciado(bloco)
        # Evita capturar sumário/índice sem enunciado útil
        if len(en) < 15:
            continue
        vistos.add(num)
        itens.append({"numero": num, "enunciado": en})

    itens.sort(key=lambda x: x["numero"])
    return itens


def escrever_md(tipo: str, itens: list[dict], origem: Path) -> Path:
    PASTA_SAIDA.mkdir(exist_ok=True)
    saida = PASTA_SAIDA / f"{slug_tipo(tipo)}.md"
    linhas = [f"# {tipo}", "", f"**Arquivo de origem:** `{origem}`", "", "---", ""]
    for it in itens:
        linhas.append(f"## {tipo} {it['numero']}")
        linhas.append("")
        linhas.append("**Enunciado:**")
        linhas.append(it["enunciado"])
        linhas.append("")
        linhas.append("---")
        linhas.append("")
    saida.write_text("\n".join(linhas), encoding="utf-8")
    return saida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arquivo", help="PDF específico de súmulas")
    ap.add_argument("--todos", action="store_true", help="Extrair PDFs padrão de súmulas dentro de pdfs/")
    args = ap.parse_args()

    if args.arquivo:
        arquivos = [Path(args.arquivo)]
    elif args.todos:
        arquivos = [PASTA_PDFS / nome for nome in PDFS_PADRAO if (PASTA_PDFS / nome).exists()]
    else:
        print("Use --todos ou --arquivo caminho/do/pdf")
        sys.exit(1)

    if not arquivos:
        print("Nenhum PDF de súmulas encontrado.")
        sys.exit(1)

    rel = []
    print("Arquivos selecionados:")
    for a in arquivos:
        print(f"- {a}")
    print()

    for arq in arquivos:
        if not arq.exists():
            print(f"AVISO: não encontrado: {arq}")
            rel.append((str(arq), "NÃO ENCONTRADO", 0, ""))
            continue
        tipo = detectar_tipo(arq.name)
        texto = ler_pdf(arq)
        itens = extrair_sumulas(texto, tipo)
        saida = escrever_md(tipo, itens, arq)
        print(f"{tipo}: {len(itens)} súmulas extraídas -> {saida}")
        rel.append((str(arq), tipo, len(itens), str(saida)))

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rel_path = PASTA_SAIDA / f"relatorio_extracao_sumulas_{ts}.md"
    linhas = ["# Relatório de Extração de Súmulas", "", f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", "", "| PDF | Tipo | Extraídas | Saída |", "|---|---|---:|---|"]
    for pdf, tipo, qtd, saida in rel:
        linhas.append(f"| `{pdf}` | {tipo} | {qtd} | `{saida}` |")
    rel_path.write_text("\n".join(linhas), encoding="utf-8")
    print(f"\nRelatório: {rel_path}")


if __name__ == "__main__":
    main()
