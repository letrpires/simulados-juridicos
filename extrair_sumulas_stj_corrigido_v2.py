#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extrator corrigido V2 — Súmulas STJ

Objetivo:
- Ler pdfs/Sumulas STJ.pdf
- Extrair enunciados das súmulas do STJ
- Excluir súmulas canceladas
- Remover metadados finais, ex.: (SÚMULA 2, PRIMEIRA SEÇÃO, julgado em..., DJ...)
- Remover ruídos: VEJA MAIS, links, marcadores finais como G
- Salvar em formato simples:
  Súmula 2 do STJ: Não cabe o habeas data...

Saída:
- sumulas_extraidas_md/sumula_stj_corrigida_v2.md
- sumulas_extraidas_md/relatorio_extracao_stj_corrigida_v2_DATA.md
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERRO: instale PyMuPDF com: python3 -m pip install pymupdf")
    sys.exit(1)

PDF_PADRAO = Path("pdfs/Sumulas STJ.pdf")
PASTA_SAIDA = Path("sumulas_extraidas_md")


def normalizar_texto(texto: str) -> str:
    texto = texto.replace("\u00a0", " ")
    texto = texto.replace("\r", "\n")
    texto = re.sub(r"<br\s*/?>", " ", texto, flags=re.I)
    texto = re.sub(r"https?://\S+", " ", texto, flags=re.I)
    texto = re.sub(r"\bscon\.stj\.jus\.br/\S*", " ", texto, flags=re.I)
    texto = re.sub(r"\bVEJA\s+MAIS\b", " ", texto, flags=re.I)
    texto = re.sub(r"\bPágina\s+\d+\b", " ", texto, flags=re.I)
    texto = re.sub(r"\bSuperior Tribunal de Justiça\b", " ", texto, flags=re.I)
    texto = re.sub(r"\bCoordenadoria de Divulgação de Jurisprudência\b", " ", texto, flags=re.I)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def texto_pdf(pdf: Path) -> str:
    doc = fitz.open(pdf)
    partes = []
    for pagina in doc:
        partes.append(pagina.get_text("text"))
    return normalizar_texto("\n".join(partes))


def limpar_enunciado(enunciado: str, numero: int) -> str:
    t = enunciado
    t = t.replace("\n", " ")
    t = normalizar_texto(t)

    # Remove tudo a partir do bloco de metadados oficial da súmula.
    # Ex.: (SÚMULA 2, PRIMEIRA SEÇÃO, julgado em..., DJ...)
    t = re.sub(
        rf"\(\s*S[ÚU]MULA\s+{numero}\s*,.*?(?:\)|$)",
        " ",
        t,
        flags=re.I,
    )
    # Variação sem fechamento perfeito por quebra/truncamento.
    t = re.sub(
        rf"\(\s*S[ÚU]MULA\s+{numero}\s*,.*$",
        " ",
        t,
        flags=re.I,
    )
    # Remove metadados residuais começando por seção/julgamento/DJ.
    t = re.sub(r"\b(?:PRIMEIRA|SEGUNDA|TERCEIRA)\s+SE[ÇC][ÃA]O\b.*$", " ", t, flags=re.I)
    t = re.sub(r"\bCORTE\s+ESPECIAL\b.*$", " ", t, flags=re.I)
    t = re.sub(r"\bjulgado\s+em\b.*$", " ", t, flags=re.I)
    t = re.sub(r"\bDJ\s+\d{1,2}/\d{1,2}/\d{2,4}\b.*$", " ", t, flags=re.I)
    t = re.sub(r"\bDJe\s+\d{1,2}/\d{1,2}/\d{2,4}\b.*$", " ", t, flags=re.I)
    t = re.sub(r"\bREPDJ\b.*$", " ", t, flags=re.I)

    # Remove fragmentos finais comuns.
    t = re.sub(r"\s+G\s*$", "", t)
    t = re.sub(r"\s+\d+\s+G\s*$", "", t)
    t = re.sub(r"\s+\(\s*$", "", t)
    t = re.sub(r"\s+\)\s*$", "", t)
    t = re.sub(r"\s+", " ", t).strip()

    # Corrige espaços antes de pontuação.
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    return t.strip()


def eh_cancelada(numero: int, enunciado_limpo: str, bruto: str) -> bool:
    combinado = f"{enunciado_limpo} {bruto}".lower()
    padroes = [
        "cancelamento da",
        "cancelada",
        "cancelado",
        "súmula cancelada",
        "sumula cancelada",
        "determinou o cancelamento",
        "fica cancelada",
        "foi cancelada",
    ]
    if any(p in combinado for p in padroes):
        return True
    # Súmula 1 do arquivo costuma aparecer apenas como ruído de cancelamento.
    if numero == 1 and len(enunciado_limpo) < 40:
        return True
    return False


def extrair_sumulas(texto: str) -> Dict[int, str]:
    # O PDF pode vir como "Súmula 2" ou "SUMULA 2".
    padrao = re.compile(r"(?:^|\n)\s*S[úu]mula\s+(\d{1,4})\b", re.I)
    matches = list(padrao.finditer(texto))
    itens: Dict[int, str] = {}

    for i, m in enumerate(matches):
        numero = int(m.group(1))
        inicio = m.end()
        fim = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        bruto = texto[inicio:fim].strip()

        # Remove labels repetidos e ruídos de cabeçalho próximos.
        bruto = re.sub(r"^\s*[-–—:]+\s*", "", bruto)
        bruto = re.sub(r"\bENUNCIADO\b\s*:?", " ", bruto, flags=re.I)
        bruto = re.sub(r"\bVEJA\s+MAIS\b", " ", bruto, flags=re.I)

        limpo = limpar_enunciado(bruto, numero)
        if not limpo:
            continue
        if eh_cancelada(numero, limpo, bruto):
            continue
        if len(limpo) < 15:
            continue

        # Se houver duplicidade numérica, mantém o texto mais longo, em geral mais completo.
        if numero not in itens or len(limpo) > len(itens[numero]):
            itens[numero] = limpo

    return dict(sorted(itens.items()))


def salvar_md(sumulas: Dict[int, str], saida: Path) -> None:
    linhas = ["# Súmulas STJ", "", "Formato: 1 súmula = 1 enunciado-base para questão.", ""]
    for numero, enunciado in sumulas.items():
        linhas.append(f"Súmula {numero} do STJ: {enunciado}")
        linhas.append("")
    saida.write_text("\n".join(linhas).strip() + "\n", encoding="utf-8")


def salvar_relatorio(sumulas: Dict[int, str], pdf: Path, saida_md: Path) -> Path:
    agora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rel = PASTA_SAIDA / f"relatorio_extracao_stj_corrigida_v2_{agora}.md"
    nums = list(sumulas.keys())
    faltantes = []
    if nums:
        presentes = set(nums)
        faltantes = [n for n in range(min(nums), max(nums) + 1) if n not in presentes]

    amostra = []
    for n in nums[:20]:
        amostra.append(f"- Súmula {n}: {sumulas[n]}")

    conteudo = f"""# Relatório — Extração Corrigida V2 de Súmulas STJ

Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

- PDF: `{pdf}`
- Súmulas válidas extraídas: **{len(sumulas)}**
- Arquivo MD: `{saida_md}`
- Menor número: **{min(nums) if nums else ''}**
- Maior número: **{max(nums) if nums else ''}**
- Números ausentes na sequência: **{len(faltantes)}**
- Primeiros ausentes: `{', '.join(map(str, faltantes[:50]))}`
- Enunciados com metadados `(SÚMULA..., julgado...)`: **{sum(1 for v in sumulas.values() if re.search(r'\(\s*S[ÚU]MULA\s+\d+', v, re.I))}**
- Enunciados com `VEJA MAIS`: **{sum(1 for v in sumulas.values() if 'VEJA MAIS' in v.upper())}**
- Enunciados indicando cancelamento: **{sum(1 for v in sumulas.values() if 'CANCELAD' in v.upper())}**

## Amostra inicial

{chr(10).join(amostra)}
"""
    rel.write_text(conteudo, encoding="utf-8")
    return rel


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrai Súmulas STJ em formato limpo.")
    parser.add_argument("--pdf", default=str(PDF_PADRAO), help="Caminho do PDF de Súmulas STJ")
    args = parser.parse_args()

    pdf = Path(args.pdf)
    if not pdf.exists():
        print(f"ERRO: PDF não encontrado: {pdf}")
        sys.exit(1)

    PASTA_SAIDA.mkdir(exist_ok=True)
    txt = texto_pdf(pdf)
    sumulas = extrair_sumulas(txt)

    saida_md = PASTA_SAIDA / "sumula_stj_corrigida_v2.md"
    salvar_md(sumulas, saida_md)
    rel = salvar_relatorio(sumulas, pdf, saida_md)

    print(f"Súmulas STJ válidas extraídas: {len(sumulas)}")
    print(f"MD: {saida_md}")
    print(f"Relatório: {rel}")
    print("Formato: Súmula XX do STJ: enunciado")
    print("Canceladas e metadados finais foram removidos.")


if __name__ == "__main__":
    main()
