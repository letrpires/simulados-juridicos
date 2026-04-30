#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrator corrigido para Súmulas STJ.

Objetivo:
- Ler o PDF `pdfs/Sumulas STJ.pdf`;
- Extrair uma súmula por número;
- Remover ruídos como VEJA MAIS, links, referências finais soltas e quebras ruins;
- Gerar `sumulas_extraidas_md/sumula_stj_corrigida.md`;
- Gerar relatório de conferência.

Uso:
    python3 extrair_sumulas_stj_corrigido.py

Se faltar PyMuPDF:
    python3 -m pip install pymupdf
"""

from __future__ import annotations

import re
from pathlib import Path
from datetime import datetime

try:
    import fitz  # PyMuPDF
except ImportError:
    raise SystemExit("ERRO: instale o PyMuPDF com: python3 -m pip install pymupdf")

PDF_PADRAO = Path("pdfs/Sumulas STJ.pdf")
SAIDA_DIR = Path("sumulas_extraidas_md")


def ler_pdf(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"ERRO: PDF não encontrado: {path}")
    partes: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            partes.append(page.get_text("text"))
    return "\n".join(partes)


def normalizar_texto_base(texto: str) -> str:
    texto = texto.replace("\xa0", " ")
    texto = texto.replace("\u00ad", "")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto


def limpar_enunciado(raw: str) -> str:
    t = raw
    t = t.replace("\xa0", " ")
    t = t.replace("\u00ad", "")

    # Remove ruídos recorrentes do site/PDF do STJ.
    t = re.sub(r"\bVEJA\s+MAIS\b", " ", t, flags=re.I)
    t = re.sub(r"\bLeia\s+mais\b.*", " ", t, flags=re.I)
    t = re.sub(r"https?://\S+", " ", t, flags=re.I)
    t = re.sub(r"www\.\S+", " ", t, flags=re.I)

    # Remove referências finais comuns que vieram truncadas ou iniciadas por parêntese.
    # Mantém parênteses internos necessários quando não parecem metadados finais.
    t = re.sub(r"\s*\(\s*$", "", t)
    t = re.sub(r"\s*\(\s*(?:Corte|Primeira|Segunda|Terceira|Quarta|Quinta|Sexta|Especial|S[úu]mula|DJ|DJe|REsp|AgRg|EREsp).*$", "", t, flags=re.I)

    # Remove pedaços de navegação/metadados comuns.
    t = re.sub(r"\bP[áa]gina\s+\d+\b", " ", t, flags=re.I)
    t = re.sub(r"\bSuperior Tribunal de Justiça\b", " ", t, flags=re.I)
    t = re.sub(r"\bSTJ\b\s*-\s*\bS[úu]mulas\b", " ", t, flags=re.I)

    # Corrige quebras e espaços.
    t = re.sub(r"\s*\n\s*", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" -–—\t\n")

    # Corrige espaços antes de pontuação.
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)

    return t.strip()


def extrair_sumulas_stj(texto: str) -> list[tuple[int, str]]:
    texto = normalizar_texto_base(texto)

    # Estratégia principal: separar por ocorrências de "Súmula N" ou "Súmula n. N".
    padrao = re.compile(
        r"(?:^|\n|\s)(?:S[úu]mula)\s*(?:n[ºo\.]?\s*)?(\d{1,4})\b[\s:–—-]*(.*?)(?=(?:\n|\s)S[úu]mula\s*(?:n[ºo\.]?\s*)?\d{1,4}\b|\Z)",
        re.I | re.S,
    )

    encontrados: list[tuple[int, str]] = []
    vistos: set[int] = set()

    for m in padrao.finditer(texto):
        num = int(m.group(1))
        if num in vistos:
            continue
        bruto = m.group(2)

        # Se a extração capturou cabeçalho/lixo antes do enunciado real, tenta cortar até depois de marcadores.
        bruto = re.sub(r"^\s*(?:Enunciado|Texto|Tese)\s*[:\-–—]\s*", "", bruto, flags=re.I)
        enunciado = limpar_enunciado(bruto)

        # Filtra entradas claramente inválidas.
        if len(enunciado) < 12:
            continue
        if re.fullmatch(r"[\W\d_]+", enunciado):
            continue

        vistos.add(num)
        encontrados.append((num, enunciado))

    encontrados.sort(key=lambda x: x[0])
    return encontrados


def salvar_md(sumulas: list[tuple[int, str]], origem: Path) -> Path:
    SAIDA_DIR.mkdir(exist_ok=True)
    out = SAIDA_DIR / "sumula_stj_corrigida.md"
    linhas: list[str] = []
    linhas.append("# Súmulas STJ — extração corrigida")
    linhas.append("")
    linhas.append(f"**Arquivo de origem:** `{origem}`")
    linhas.append("")
    linhas.append("---")
    linhas.append("")

    for num, enunciado in sumulas:
        linhas.append(f"## Súmula STJ {num}")
        linhas.append("")
        linhas.append("**Enunciado:**")
        linhas.append(enunciado)
        linhas.append("")
        linhas.append("---")
        linhas.append("")

    out.write_text("\n".join(linhas), encoding="utf-8")
    return out


def salvar_relatorio(sumulas: list[tuple[int, str]], saida: Path) -> Path:
    SAIDA_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rel = SAIDA_DIR / f"relatorio_extracao_stj_corrigida_{ts}.md"

    nums = [n for n, _ in sumulas]
    faltantes = []
    if nums:
        for n in range(min(nums), max(nums) + 1):
            if n not in set(nums):
                faltantes.append(n)

    curtas = [(n, e) for n, e in sumulas if len(e) < 30]
    com_veja = [(n, e) for n, e in sumulas if "VEJA MAIS" in e.upper()]

    linhas = []
    linhas.append("# Relatório — Extração Corrigida de Súmulas STJ")
    linhas.append("")
    linhas.append(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    linhas.append("")
    linhas.append(f"- Súmulas extraídas: **{len(sumulas)}**")
    linhas.append(f"- Arquivo MD: `{saida}`")
    linhas.append(f"- Menor número: **{min(nums) if nums else '-'}**")
    linhas.append(f"- Maior número: **{max(nums) if nums else '-'}**")
    linhas.append(f"- Possíveis faltantes na sequência: **{len(faltantes)}**")
    if faltantes[:50]:
        linhas.append(f"  - Primeiros faltantes: `{', '.join(map(str, faltantes[:50]))}`")
    linhas.append(f"- Enunciados muito curtos: **{len(curtas)}**")
    if curtas[:20]:
        linhas.append("  - Conferir: " + ", ".join(f"{n}" for n, _ in curtas[:20]))
    linhas.append(f"- Enunciados ainda com 'VEJA MAIS': **{len(com_veja)}**")
    linhas.append("")
    linhas.append("## Amostra inicial")
    linhas.append("")
    for n, e in sumulas[:20]:
        linhas.append(f"- **Súmula {n}:** {e[:250]}")

    rel.write_text("\n".join(linhas), encoding="utf-8")
    return rel


def main() -> None:
    texto = ler_pdf(PDF_PADRAO)
    sumulas = extrair_sumulas_stj(texto)
    saida = salvar_md(sumulas, PDF_PADRAO)
    rel = salvar_relatorio(sumulas, saida)

    print(f"Súmulas STJ extraídas: {len(sumulas)}")
    print(f"MD corrigido: {saida}")
    print(f"Relatório: {rel}")
    print("\nConfira a amostra no relatório antes de gerar questões.")


if __name__ == "__main__":
    main()
