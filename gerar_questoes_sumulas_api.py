#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_questoes_sumulas_api.py

Gera questões CERTO/ERRADO a partir de arquivos Markdown com súmulas.
Regra central: 1 súmula = 1 questão.

Saída segura: questoes_geradas_api_revisar_sumulas/
Nunca grava diretamente em questoes_validadas_pdf/.

Uso recomendado:
  python3 gerar_questoes_sumulas_api.py --todos --dry-run
  python3 gerar_questoes_sumulas_api.py --arquivo "questoes_validadas_pdf/Súmulas STF.md" --dry-run
  python3 gerar_questoes_sumulas_api.py --arquivo "questoes_validadas_pdf/Súmulas STF.md"

Requer, para geração real:
  export OPENAI_API_KEY="sua_chave"
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    print("ERRO: instale requests com: python3 -m pip install requests")
    sys.exit(1)

BASE_DIR = Path.cwd()
PASTAS_BUSCA = [BASE_DIR / "questoes_validadas_pdf", BASE_DIR / "sumulas", BASE_DIR]
PASTA_SAIDA = BASE_DIR / "questoes_geradas_api_revisar_sumulas"

DEFAULT_MODEL = "gpt-4.1-mini"

PALAVRAS_CANCELADA = [
    "cancelada", "cancelado", "revogada", "revogado", "superada", "superado",
    "sem efeito", "prejudicada", "prejudicado"
]


def agora_tag() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def limpar_texto(txt: str) -> str:
    txt = html.unescape(txt or "")
    txt = txt.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    txt = re.sub(r"\r\n?", "\n", txt)
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    txt = re.sub(r"\s+([,.;:])", r"\1", txt)
    return txt.strip()


def slugify(nome: str) -> str:
    mapa = str.maketrans({
        "á": "a", "à": "a", "ã": "a", "â": "a", "ä": "a",
        "é": "e", "ê": "e", "è": "e", "ë": "e",
        "í": "i", "ì": "i", "î": "i", "ï": "i",
        "ó": "o", "õ": "o", "ô": "o", "ò": "o", "ö": "o",
        "ú": "u", "ù": "u", "û": "u", "ü": "u",
        "ç": "c", "Á": "A", "À": "A", "Ã": "A", "Â": "A",
        "É": "E", "Ê": "E", "Í": "I", "Ó": "O", "Õ": "O",
        "Ô": "O", "Ú": "U", "Ç": "C"
    })
    nome = nome.translate(mapa).lower()
    nome = re.sub(r"[^a-z0-9]+", "_", nome)
    return nome.strip("_") or "sumulas"


def inferir_tribunal(texto: str, arquivo: Path, titulo: str = "") -> str:
    base = f"{arquivo.name} {titulo} {texto[:1000]}".upper()
    if "STJ" in base and "STF" not in base:
        return "STJ"
    if "STF" in base:
        return "STF"
    if "VINCULANTE" in base:
        return "STF"
    return "N/I"


def titulo_para_item(raw: str, arquivo: Path, texto_contexto: str) -> Tuple[str, str, str]:
    """Retorna (tipo, numero, titulo_normalizado)."""
    t = re.sub(r"[*#_`]+", "", raw).strip()
    t = re.sub(r"\s+", " ", t)
    vinc = bool(re.search(r"s[uú]mula\s+vinculante", t, flags=re.I))
    m_num = re.search(r"(?:n[ºo.]?\s*)?(\d{1,4})\b", t, flags=re.I)
    numero = m_num.group(1) if m_num else "000"
    tribunal = inferir_tribunal(texto_contexto, arquivo, t)
    tipo = "Súmula Vinculante" if vinc else "Súmula"
    if tribunal != "N/I" and tribunal not in t.upper():
        titulo = f"{tipo} {numero} {tribunal}"
    else:
        titulo = f"{tipo} {numero}"
        if tribunal != "N/I":
            titulo += f" {tribunal}"
    return tipo, numero, titulo


def encontrar_sumulas(caminho: Path, pular_canceladas: bool = False) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    bruto = caminho.read_text(encoding="utf-8", errors="ignore")
    texto = limpar_texto(bruto)

    # Padrões de títulos comuns em markdown: ## Súmula 123, **Súmula 123 STF**, etc.
    padrao_titulo = re.compile(
        r"(?im)^\s*(?:#{1,6}\s*)?(?:\*\*)?\s*"
        r"(S[uú]mula(?:\s+Vinculante)?(?:\s+(?:STF|STJ))?\s*(?:n[ºo.]?\s*)?\d{1,4}[^\n*]*)"
        r"\s*(?:\*\*)?\s*$"
    )

    matches = list(padrao_titulo.finditer(texto))

    itens: List[Dict[str, Any]] = []
    pulados: List[Dict[str, Any]] = []
    vistos: set[str] = set()

    if matches:
        for idx, match in enumerate(matches):
            inicio = match.end()
            fim = matches[idx + 1].start() if idx + 1 < len(matches) else len(texto)
            raw_title = match.group(1).strip()
            bloco = limpar_texto(texto[inicio:fim])
            tipo, numero, titulo = titulo_para_item(raw_title, caminho, texto)
            chave = f"{tipo}|{inferir_tribunal(texto, caminho, titulo)}|{numero}"
            if chave in vistos:
                pulados.append({"titulo": titulo, "motivo": "DUPLICADO_NUMERO"})
                continue
            vistos.add(chave)
            enunciado = limpar_enunciado_sumula(bloco)
            if not enunciado:
                pulados.append({"titulo": titulo, "motivo": "SEM_ENUNCIADO"})
                continue
            cancelada = any(p in enunciado.lower() for p in PALAVRAS_CANCELADA)
            if pular_canceladas and cancelada:
                pulados.append({"titulo": titulo, "motivo": "CANCELADA_REVOGADA"})
                continue
            itens.append({
                "id_origem": f"{slugify(titulo)}",
                "titulo": titulo,
                "tipo": tipo,
                "numero": numero,
                "tribunal": inferir_tribunal(texto, caminho, titulo),
                "enunciado": enunciado,
                "cancelada_ou_revogada": cancelada,
                "arquivo_origem": str(caminho),
            })
        return itens, pulados

    # Fallback: tenta capturar em formato corrido: Súmula 123: texto ... Súmula 124: texto ...
    padrao_corrida = re.compile(
        r"(?is)(S[uú]mula(?:\s+Vinculante)?(?:\s+(?:STF|STJ))?\s*(?:n[ºo.]?\s*)?\d{1,4})\s*[:\-–]?\s*(.*?)"
        r"(?=\n?\s*S[uú]mula(?:\s+Vinculante)?(?:\s+(?:STF|STJ))?\s*(?:n[ºo.]?\s*)?\d{1,4}\b|\Z)"
    )
    for match in padrao_corrida.finditer(texto):
        raw_title, bloco = match.group(1), match.group(2)
        tipo, numero, titulo = titulo_para_item(raw_title, caminho, texto)
        chave = f"{tipo}|{inferir_tribunal(texto, caminho, titulo)}|{numero}"
        if chave in vistos:
            pulados.append({"titulo": titulo, "motivo": "DUPLICADO_NUMERO"})
            continue
        vistos.add(chave)
        enunciado = limpar_enunciado_sumula(bloco)
        if not enunciado:
            pulados.append({"titulo": titulo, "motivo": "SEM_ENUNCIADO"})
            continue
        cancelada = any(p in enunciado.lower() for p in PALAVRAS_CANCELADA)
        if pular_canceladas and cancelada:
            pulados.append({"titulo": titulo, "motivo": "CANCELADA_REVOGADA"})
            continue
        itens.append({
            "id_origem": f"{slugify(titulo)}",
            "titulo": titulo,
            "tipo": tipo,
            "numero": numero,
            "tribunal": inferir_tribunal(texto, caminho, titulo),
            "enunciado": enunciado,
            "cancelada_ou_revogada": cancelada,
            "arquivo_origem": str(caminho),
        })

    return itens, pulados


def limpar_enunciado_sumula(bloco: str) -> str:
    bloco = limpar_texto(bloco)
    bloco = re.sub(r"(?im)^\s*\*\*\s*Enunciado\s*:\s*\*\*\s*", "", bloco)
    bloco = re.sub(r"(?im)^\s*Enunciado\s*:\s*", "", bloco)
    bloco = re.sub(r"(?im)^\s*Tese\s*:\s*", "", bloco)
    bloco = re.sub(r"(?im)^\s*-{3,}\s*$", "", bloco)
    bloco = re.sub(r"\n{3,}", "\n\n", bloco).strip()
    return bloco


def selecionar_arquivos(args: argparse.Namespace) -> List[Path]:
    if args.arquivo:
        p = Path(args.arquivo)
        if not p.exists():
            print(f"ERRO: arquivo não encontrado: {p}")
            sys.exit(1)
        return [p]

    candidatos: List[Path] = []
    if args.todos:
        for pasta in PASTAS_BUSCA:
            if not pasta.exists():
                continue
            for p in pasta.rglob("*.md"):
                nome = p.name.lower()
                if "sumula" in slugify(nome) or "súmula" in nome:
                    candidatos.append(p)
    # Remove duplicados preservando ordem
    vistos = set()
    unicos = []
    for p in candidatos:
        rp = p.resolve()
        if rp not in vistos:
            vistos.add(rp)
            unicos.append(p)
    return unicos


def chamada_api_sumula(item: Dict[str, Any], modelo: str, temperatura: float) -> Dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não definido. Use: export OPENAI_API_KEY='sua_chave'")

    status = "cancelada/revogada" if item.get("cancelada_ou_revogada") else "vigente ou sem status especial identificado"
    prompt = f"""
Você é examinador experiente de concurso público jurídico.

Transforme a súmula abaixo em EXATAMENTE UMA questão de CERTO ou ERRADO, em padrão alto de concurso público jurídico, estilo CEBRASPE/CESPE.

REGRAS ABSOLUTAS:
1. Gere exatamente UMA questão.
2. Não copie literalmente o enunciado como questão.
3. Não use expressões como "segundo a súmula".
4. A questão deve ser técnica, plausível e fiel ao enunciado.
5. Pode inverter a lógica para criar item ERRADO.
6. Se a súmula estiver cancelada, revogada, superada ou sem efeito, a questão deve cobrar esse status de forma expressa e fiel.
7. A justificativa deve explicar didaticamente o fundamento.
8. O gabarito deve ser apenas CERTO ou ERRADO.

DADOS DA SÚMULA:
Título: {item['titulo']}
Tribunal: {item['tribunal']}
Status detectado: {status}
Enunciado:
{item['enunciado']}

Responda APENAS em JSON válido, neste formato:
{{
  "questoes": [
    {{
      "id_origem": "{item['id_origem']}",
      "titulo_origem": "{item['titulo']}",
      "questao": "...",
      "gabarito": "CERTO ou ERRADO",
      "justificativa": "..."
    }}
  ]
}}
""".strip()

    payload = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": "Você gera questões jurídicas em JSON válido, sem markdown fora do JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperatura,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=180,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Erro API {resp.status_code}: {resp.text[:1000]}")
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    qs = parsed.get("questoes", [])
    if not isinstance(qs, list) or len(qs) != 1:
        raise RuntimeError(f"Resposta inválida: esperava 1 questão, recebi {len(qs) if isinstance(qs, list) else 'N/A'}")
    q = qs[0]
    if q.get("gabarito") not in {"CERTO", "ERRADO"}:
        raise RuntimeError(f"Gabarito inválido: {q.get('gabarito')}")
    for campo in ["questao", "justificativa"]:
        if not str(q.get(campo, "")).strip():
            raise RuntimeError(f"Campo vazio: {campo}")
    return q


def formatar_md(item_nome: str, questoes: List[Dict[str, Any]], itens: List[Dict[str, Any]]) -> str:
    linhas = [
        f"# {item_nome}",
        "",
        "**Categoria:** SÚMULAS",
        "**Regra:** 1 súmula = 1 questão",
        "**Status de validação:** VALIDADO",
        "",
        "---",
        "",
    ]
    mapa = {i["id_origem"]: i for i in itens}
    for idx, q in enumerate(questoes, start=1):
        origem = mapa.get(q.get("id_origem", ""), {})
        linhas.extend([
            f"## Questão {idx}",
            "",
            f"<!-- ID_ORIGEM: {q.get('id_origem', '')} -->",
            f"<!-- TITULO_ORIGEM: {q.get('titulo_origem', origem.get('titulo', ''))} -->",
            f"<!-- ARQUIVO_ORIGEM: {origem.get('arquivo_origem', '')} -->",
            "",
            str(q.get("questao", "")).strip(),
            "",
            f"**Gabarito:** {q.get('gabarito', '').strip()}",
            "",
            "**Justificativa:**",
            "",
            str(q.get("justificativa", "")).strip(),
            "",
            "---",
            "",
        ])
    return "\n".join(linhas).strip() + "\n"


def salvar_relatorios(tag: str, rows: List[Dict[str, Any]]) -> Tuple[Path, Path]:
    PASTA_SAIDA.mkdir(exist_ok=True)
    csv_path = PASTA_SAIDA / f"controle_sumulas_{tag}.csv"
    md_path = PASTA_SAIDA / f"relatorio_sumulas_{tag}.md"

    campos = ["arquivo", "item", "sumulas_extraidas", "sumulas_puladas", "geradas", "status", "observacao"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in campos})

    total = len(rows)
    ok = sum(1 for r in rows if r.get("status") == "OK_VALIDADO")
    nao = sum(1 for r in rows if r.get("status") == "NAO_VALIDADO")
    outros = total - ok - nao
    linhas = [
        "# Relatório — Geração de Súmulas por API",
        "",
        f"Gerado em: {dt.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "",
        "## Resumo",
        "",
        f"- Arquivos processados: **{total}**",
        f"- OK_VALIDADO: **{ok}**",
        f"- NAO_VALIDADO: **{nao}**",
        f"- Outros/Pulados: **{outros}**",
        "",
        "## Detalhamento",
        "",
        "| Arquivo | Item | Súmulas extraídas | Puladas | Geradas | Status | Observação |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for r in rows:
        linhas.append(
            f"| {r.get('arquivo','')} | {r.get('item','')} | {r.get('sumulas_extraidas',0)} | "
            f"{r.get('sumulas_puladas',0)} | {r.get('geradas',0)} | {r.get('status','')} | {r.get('observacao','')} |"
        )
    linhas.extend([
        "",
        "## Segurança",
        "",
        "Só copie para `questoes_validadas_pdf/` arquivos com status `OK_VALIDADO`.",
        "Em `dry-run`, nenhum arquivo `.md` de questões é criado.",
    ])
    md_path.write_text("\n".join(linhas), encoding="utf-8")
    return csv_path, md_path


def processar_arquivo(caminho: Path, args: argparse.Namespace) -> Dict[str, Any]:
    itens, pulados = encontrar_sumulas(caminho, pular_canceladas=args.pular_canceladas)
    item_nome = caminho.stem
    print(f"\nArquivo: {caminho}")
    print(f"Item: {item_nome}")
    print(f"Súmulas extraídas: {len(itens)}")
    print(f"Súmulas puladas: {len(pulados)}")

    row = {
        "arquivo": str(caminho),
        "item": item_nome,
        "sumulas_extraidas": len(itens),
        "sumulas_puladas": len(pulados),
        "geradas": 0,
        "status": "",
        "observacao": "",
    }

    if not itens:
        row["status"] = "SEM_SUMULAS_EXTRAIDAS"
        row["observacao"] = "Verifique se o arquivo usa títulos como '## Súmula 123'."
        return row

    if args.dry_run:
        row["geradas"] = len(itens)
        row["status"] = "DRY_RUN_OK"
        return row

    PASTA_SAIDA.mkdir(exist_ok=True)
    out_md = PASTA_SAIDA / f"{slugify(item_nome)}.md"
    out_json = PASTA_SAIDA / f"{slugify(item_nome)}.json"
    if out_md.exists() and not args.sobrescrever:
        row["status"] = "PULADO_JA_EXISTE"
        row["observacao"] = "Arquivo já existia. Use --sobrescrever para gerar novamente."
        return row

    questoes: List[Dict[str, Any]] = []
    erros: List[str] = []
    for idx, item in enumerate(itens, start=1):
        print(f"  [{idx}/{len(itens)}] {item['titulo']}")
        try:
            q = chamada_api_sumula(item, args.modelo, args.temperatura)
            questoes.append(q)
        except Exception as e:
            erros.append(f"{item['titulo']}: {e}")
            print(f"    ERRO: {e}")
            break
        if args.pausa:
            time.sleep(args.pausa)

    row["geradas"] = len(questoes)
    if len(questoes) == len(itens) and not erros:
        out_md.write_text(formatar_md(item_nome, questoes, itens), encoding="utf-8")
        out_json.write_text(json.dumps({"itens": itens, "questoes": questoes}, ensure_ascii=False, indent=2), encoding="utf-8")
        row["status"] = "OK_VALIDADO"
    else:
        row["status"] = "NAO_VALIDADO"
        row["observacao"] = f"Geradas {len(questoes)} de {len(itens)}. " + " | ".join(erros[:3])
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arquivo", help="Caminho de um arquivo .md específico de súmulas")
    ap.add_argument("--todos", action="store_true", help="Processa arquivos com 'sumula/súmula' no nome")
    ap.add_argument("--dry-run", action="store_true", help="Conta e valida extração, sem chamar API")
    ap.add_argument("--sobrescrever", action="store_true", help="Sobrescreve saída existente na pasta de revisão")
    ap.add_argument("--modelo", default=DEFAULT_MODEL)
    ap.add_argument("--temperatura", type=float, default=0.2)
    ap.add_argument("--pausa", type=float, default=0.2, help="Pausa entre chamadas da API")
    ap.add_argument("--pular-canceladas", action="store_true", help="Não gera questões para súmulas canceladas/revogadas")
    args = ap.parse_args()

    arquivos = selecionar_arquivos(args)
    if not arquivos:
        print("Nenhum arquivo encontrado. Use --arquivo caminho/do/arquivo.md ou --todos.")
        sys.exit(1)

    print("Arquivos selecionados:")
    for a in arquivos:
        print(f"- {a}")
    print(f"Dry-run: {args.dry_run}")
    print(f"Modelo: {args.modelo}")
    print("Regra: 1 súmula = 1 questão")

    rows = []
    for arquivo in arquivos:
        rows.append(processar_arquivo(arquivo, args))

    tag = agora_tag()
    csv_path, md_path = salvar_relatorios(tag, rows)
    print("\nConcluído.")
    print(f"Controle CSV: {csv_path}")
    print(f"Relatório MD: {md_path}")
    print("\nREGRA DE SEGURANÇA: só copie arquivos OK_VALIDADO para questoes_validadas_pdf/.")


if __name__ == "__main__":
    main()
