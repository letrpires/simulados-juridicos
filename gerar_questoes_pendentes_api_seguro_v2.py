#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
gerar_questoes_pendentes_api_seguro_v2.py

Gera questões por API com TRAVA DE CONTAGEM.

VERSÃO V2:
- Ignora, por padrão, itens e arquivos com "Extracao".
- Prioriza fontes limpas/validadas em vez de extrações brutas.
- Melhora a organização de RG, Repetitivos e Súmulas.
- Mantém a regra: nunca salva direto na pasta final.

Objetivo:
- Ler pendências da auditoria v2.
- Localizar o arquivo-fonte correspondente em pdfs/ ou arquivos .md/.txt.
- Quebrar o conteúdo em itens pequenos:
    Informativo: Julgado
    RG/Repetitivo: Tema
    Súmula: Súmula / Súmula Vinculante
- Enviar pequenos lotes para a API.
- Exigir retorno em JSON estruturado.
- Validar:
    itens enviados == questões recebidas
    ids enviados == ids recebidos
    quantidade final esperada == quantidade final gerada
- Salvar tudo em pasta de revisão, NUNCA direto na pasta final.

IMPORTANTE:
- Este script NÃO substitui sua revisão jurídica.
- Ele evita o erro de gerar só 20 questões quando deveriam ser centenas.
- Se a contagem não bater, o arquivo fica marcado como NAO_VALIDADO.

Requisitos:
    python3 -m pip install requests pymupdf

Chave API:
    export OPENAI_API_KEY="sua_chave_aqui"

Uso básico:
    python3 gerar_questoes_pendentes_api_seguro.py

Uso processando só uma categoria:
    python3 gerar_questoes_pendentes_api_seguro.py --categoria SUMULA

Uso processando só um item:
    python3 gerar_questoes_pendentes_api_seguro.py --item "Súmulas STF"

Uso em modo teste, sem chamar API:
    python3 gerar_questoes_pendentes_api_seguro_v2.py --dry-run

Gerar RG da forma correta, ignorando Extração:
    python3 gerar_questoes_pendentes_api_seguro_v2.py --categoria RG --incluir-incompletos --dry-run
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import requests
except ImportError:
    print("ERRO: instale requests com: python3 -m pip install requests")
    sys.exit(1)

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


# =========================
# CONFIGURAÇÕES PRINCIPAIS
# =========================

BASE_DIR = Path(".").resolve()

PASTA_AUDITORIA = BASE_DIR / "auditoria_final"
PASTA_PDFS = BASE_DIR / "pdfs"
PASTA_QUESTOES = BASE_DIR / "questoes_validadas_pdf"
PASTA_SAIDA = BASE_DIR / "questoes_geradas_api_revisar"
PASTA_LOGS = PASTA_SAIDA / "_logs"

# Modelo configurável pelo Terminal:
# export OPENAI_MODEL="gpt-4.1-mini"
MODELO = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

# Tamanho do lote:
# Para Súmulas, RG e Repetitivos grandes, mantenha pequeno para evitar cortes.
ITENS_POR_LOTE_PADRAO = int(os.getenv("ITENS_POR_LOTE", "10"))

# Limite aproximado por item para não estourar contexto.
# Se um item for enorme, ele será truncado com aviso no controle.
MAX_CARACTERES_POR_ITEM = int(os.getenv("MAX_CARACTERES_POR_ITEM", "12000"))

# Pausa entre chamadas para evitar rate limit.
PAUSA_SEGUNDOS = float(os.getenv("PAUSA_API", "1.5"))

# Status que o script processa por padrão.
# Para não bagunçar, ele começa pelos que não têm questões.
STATUS_PROCESSAR_PADRAO = {"FALTA_GERAR_QUESTOES", "SEM_QUESTOES_MD"}

# Se quiser processar também incompletos:
# python3 gerar_questoes_pendentes_api_seguro.py --incluir-incompletos
STATUS_INCOMPLETOS = {"QUESTOES_INCOMPLETAS"}

# Por segurança, a V2 NÃO usa arquivos/itens com "Extracao" por padrão.
# Use --permitir-extracao apenas se você realmente quiser trabalhar com texto bruto.
BLOQUEAR_EXTRACAO_PADRAO = True


# =========================
# MODELOS DE DADOS
# =========================

@dataclass
class Pendencia:
    categoria: str
    item: str
    pdf_estimado: Optional[int]
    questoes_md: int
    questoes_html: int
    status: str


@dataclass
class ItemFonte:
    id: str
    titulo: str
    texto: str


@dataclass
class ResultadoArquivo:
    categoria: str
    item: str
    status_auditoria: str
    fonte: str
    esperado_auditoria: Optional[int]
    itens_extraidos: int
    questoes_geradas: int
    status_final: str
    observacao: str
    arquivo_saida_md: str
    arquivo_saida_json: str


# =========================
# UTILITÁRIOS
# =========================

def agora_tag() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def normalizar(txt: str) -> str:
    txt = txt.lower().strip()
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(ch for ch in txt if unicodedata.category(ch) != "Mn")
    txt = re.sub(r"[^a-z0-9]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def nome_arquivo_seguro(txt: str, max_len: int = 120) -> str:
    txt = normalizar(txt).replace(" ", "_")
    txt = re.sub(r"_+", "_", txt).strip("_")
    return txt[:max_len] or "arquivo"


def inteiro_ou_none(valor: str) -> Optional[int]:
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return int(float(valor))
    except ValueError:
        return None


def achar_ultimo_csv_pendencias() -> Path:
    candidatos = sorted(PASTA_AUDITORIA.glob("pendencias_v2_*.csv"))
    if not candidatos:
        candidatos = sorted(PASTA_AUDITORIA.glob("pendencias*.csv"))
    if not candidatos:
        raise FileNotFoundError(
            "Não encontrei pendencias_v2_*.csv em auditoria_final/. "
            "Rode antes auditoria_final_simulados_v2.py."
        )
    return candidatos[-1]


def ler_pendencias(caminho: Path) -> List[Pendencia]:
    pendencias: List[Pendencia] = []
    with caminho.open("r", encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f)
        campos = {c.strip().lower(): c for c in (leitor.fieldnames or [])}

        def get(row: dict, *nomes: str) -> str:
            for n in nomes:
                chave = campos.get(n.lower())
                if chave is not None:
                    return row.get(chave, "")
            return ""

        for row in leitor:
            pendencias.append(
                Pendencia(
                    categoria=get(row, "Categoria").strip(),
                    item=get(row, "Item", "Info").strip(),
                    pdf_estimado=inteiro_ou_none(get(row, "PDF estimado")),
                    questoes_md=inteiro_ou_none(get(row, "Questões MD")) or 0,
                    questoes_html=inteiro_ou_none(get(row, "Questões HTML")) or 0,
                    status=get(row, "Pendência", "Status").strip(),
                )
            )
    return pendencias


def extrair_texto_pdf(caminho: Path) -> str:
    if fitz is None:
        raise RuntimeError("PyMuPDF não instalado. Rode: python3 -m pip install pymupdf")

    partes = []
    with fitz.open(caminho) as doc:
        for i, pagina in enumerate(doc, start=1):
            texto = pagina.get_text("text") or ""
            partes.append(f"\n\n===== PÁGINA {i} =====\n\n{texto}")
    return "\n".join(partes)


def ler_texto_arquivo(caminho: Path) -> str:
    if caminho.suffix.lower() == ".pdf":
        return extrair_texto_pdf(caminho)
    return caminho.read_text(encoding="utf-8", errors="ignore")


def candidatos_fontes(permitir_extracao: bool = False) -> List[Path]:
    ignorar_partes = {
        "html_simulados",
        "auditoria_final",
        "questoes_geradas_api_revisar",
        "scripts_antigos",
        ".git",
        "__pycache__",
    }
    exts = {".pdf", ".md", ".txt"}
    arquivos: List[Path] = []
    for raiz in [PASTA_PDFS, PASTA_QUESTOES, BASE_DIR]:
        if not raiz.exists():
            continue
        for p in raiz.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in exts:
                continue
            partes_norm = {normalizar(x) for x in p.parts}
            if any(normalizar(x) in partes_norm for x in ignorar_partes):
                continue
            if not permitir_extracao and "extracao" in normalizar(str(p)):
                continue
            arquivos.append(p)
    # remove duplicatas mantendo ordem
    vistos = set()
    unicos = []
    for p in arquivos:
        if p.resolve() not in vistos:
            vistos.add(p.resolve())
            unicos.append(p)
    return unicos


def pontuar_fonte(item: str, categoria: str, caminho: Path, permitir_extracao: bool = False) -> int:
    alvo = normalizar(item)
    nome = normalizar(caminho.stem)
    rel = normalizar(str(caminho.relative_to(BASE_DIR) if caminho.is_relative_to(BASE_DIR) else caminho))

    if not permitir_extracao and ("extracao" in nome or "extracao" in rel):
        return -9999

    pontos = 0

    # Correspondência direta
    if alvo and alvo in nome:
        pontos += 100
    if alvo and alvo in rel:
        pontos += 60

    # Tokens principais
    tokens = [t for t in alvo.split() if len(t) >= 2]
    for t in tokens:
        if t in nome:
            pontos += 10
        elif t in rel:
            pontos += 4

    # Categoria
    cat = normalizar(categoria)
    if cat and cat in rel:
        pontos += 15

    # Preferências por tipo/fonte. Para gerar questão, PDFs e MDs limpos são melhores
    # do que arquivos de saída HTML ou extrações brutas.
    if caminho.suffix.lower() == ".pdf":
        pontos += 18
    elif caminho.suffix.lower() == ".md":
        pontos += 10

    rel_parts = [normalizar(x) for x in caminho.parts]
    if "pdfs" in rel_parts:
        pontos += 20
    if "questoes validadas pdf" in rel or "questoes_validadas_pdf" in rel:
        pontos += 8

    # Penaliza nomes genéricos e backups.
    if any(x in rel for x in ["backup", "antigo", "old"]):
        pontos -= 20

    return pontos


def localizar_fonte(pendencia: Pendencia, todos: List[Path], permitir_extracao: bool = False) -> Optional[Path]:
    pontuados = [(pontuar_fonte(pendencia.item, pendencia.categoria, p, permitir_extracao=permitir_extracao), p) for p in todos]
    pontuados = sorted(pontuados, key=lambda x: x[0], reverse=True)
    if not pontuados or pontuados[0][0] <= 0:
        return None
    return pontuados[0][1]


# =========================
# EXTRAÇÃO DE ITENS
# =========================

def limpar_bloco(texto: str) -> str:
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def split_por_heading(texto: str, padrao: str, prefixo_id: str) -> List[ItemFonte]:
    """
    Divide mantendo o delimitador como título.
    padrao precisa capturar o título inteiro em grupo 1.
    """
    matches = list(re.finditer(padrao, texto, flags=re.IGNORECASE | re.MULTILINE))
    itens: List[ItemFonte] = []
    for idx, m in enumerate(matches):
        inicio = m.start()
        fim = matches[idx + 1].start() if idx + 1 < len(matches) else len(texto)
        bloco = limpar_bloco(texto[inicio:fim])
        titulo = limpar_bloco(m.group(1))
        if len(bloco) < 30:
            continue
        ident = f"{prefixo_id}-{idx+1:04d}"
        num = re.search(r"(\d{1,5})", titulo)
        if num:
            ident = f"{prefixo_id}-{num.group(1)}"
        itens.append(ItemFonte(id=ident, titulo=titulo, texto=bloco))
    return itens


def extrair_itens(categoria: str, item: str, texto: str) -> List[ItemFonte]:
    cat = normalizar(categoria)
    nome = normalizar(item)

    # 1) Informativos: normalmente já vêm como ## Julgado 1...
    if cat == "informativo" or nome.startswith("info "):
        itens = split_por_heading(
            texto,
            r"(^\s*#{0,3}\s*Julgado\s+\d+[^\n]*$)",
            "JULGADO"
        )
        if itens:
            return itens

        # Fallback para textos extraídos de PDF com "JULGADO IMPORTANTE", áreas etc.
        # Este fallback é conservador e pode exigir revisão.
        itens = split_por_heading(
            texto,
            r"(^\s*(?:DIREITO|PROCESSO|AGRAVO|RECURSO|HABEAS|MANDADO|AÇÃO|EXECUÇÃO)[^\n]{0,120}$)",
            "BLOCO"
        )
        return itens

    # 2) RG e Repetitivos: Tema nº 123 / Tema 123
    if cat in {"rg", "repetitivo"} or "tema" in nome:
        itens = split_por_heading(
            texto,
            r"(^\s*(?:#{1,4}\s*)?(?:Tema|TEMA)\s*(?:n[ºo]\.?\s*)?\d+[^\n]*$)",
            "TEMA"
        )
        if itens:
            return itens

        # Fallback: alguns arquivos trazem "Tema 123:" no meio da linha.
        partes = re.split(r"(?=(?:^|\n)\s*(?:Tema|TEMA)\s*(?:n[ºo]\.?\s*)?\d+)", texto)
        itens = []
        for idx, parte in enumerate(partes):
            parte = limpar_bloco(parte)
            if not parte or len(parte) < 50:
                continue
            titulo = parte.splitlines()[0][:160]
            num = re.search(r"(?:Tema|TEMA)\s*(?:n[ºo]\.?\s*)?(\d+)", titulo)
            ident = f"TEMA-{num.group(1)}" if num else f"TEMA-{idx+1:04d}"
            itens.append(ItemFonte(id=ident, titulo=titulo, texto=parte))
        return itens

    # 3) Súmulas: Súmula 1 / Súmula Vinculante 1
    if cat == "sumula" or "sumula" in nome:
        itens = split_por_heading(
            texto,
            r"(^\s*(?:#{1,4}\s*)?S[uú]mula(?:\s+Vinculante)?\s+(?:n[ºo]\.?\s*)?\d+[^\n]*$)",
            "SUMULA"
        )
        if itens:
            return itens

        # Fallback para listas: "Súmula 123 - texto..."
        partes = re.split(r"(?=(?:^|\n)\s*S[uú]mula(?:\s+Vinculante)?\s*(?:n[ºo]\.?\s*)?\d+\b)", texto)
        itens = []
        for idx, parte in enumerate(partes):
            parte = limpar_bloco(parte)
            if not parte or len(parte) < 30:
                continue
            titulo = parte.splitlines()[0][:160]
            num = re.search(r"S[uú]mula(?:\s+Vinculante)?\s*(?:n[ºo]\.?\s*)?(\d+)", titulo, flags=re.I)
            ident = f"SUMULA-{num.group(1)}" if num else f"SUMULA-{idx+1:04d}"
            itens.append(ItemFonte(id=ident, titulo=titulo, texto=parte))
        return itens

    return []


# =========================
# CHAMADA À API
# =========================

def esquema_json() -> Dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "questoes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "titulo_origem": {"type": "string"},
                        "questao": {"type": "string"},
                        "gabarito": {"type": "string", "enum": ["CERTO", "ERRADO"]},
                        "justificativa": {"type": "string"},
                    },
                    "required": ["id", "titulo_origem", "questao", "gabarito", "justificativa"],
                },
            }
        },
        "required": ["questoes"],
    }


def extrair_output_text(resposta: Dict[str, Any]) -> str:
    """
    Tenta extrair o texto de resposta do Responses API de forma tolerante.
    """
    if "output_text" in resposta and isinstance(resposta["output_text"], str):
        return resposta["output_text"]

    partes = []
    for item in resposta.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"}:
                if "text" in content:
                    partes.append(content["text"])
    return "\n".join(partes).strip()


def montar_prompt(categoria: str, item_nome: str, lote: List[ItemFonte]) -> str:
    itens_json = []
    for it in lote:
        texto = it.texto
        truncado = False
        if len(texto) > MAX_CARACTERES_POR_ITEM:
            texto = texto[:MAX_CARACTERES_POR_ITEM] + "\n\n[TRUNCADO PELO SCRIPT: REVISAR MANUALMENTE]"
            truncado = True
        itens_json.append({
            "id": it.id,
            "titulo": it.titulo,
            "texto": texto,
            "truncado": truncado,
        })

    return f"""
Você é examinador experiente de concurso público jurídico.

Tarefa:
Transformar CADA item abaixo em EXATAMENTE UMA questão de CERTO ou ERRADO, em padrão alto de concurso público jurídico, estilo CEBRASPE/CESPE.

Categoria: {categoria}
Arquivo/Item: {item_nome}

REGRAS ABSOLUTAS:
1. Gere exatamente UMA questão para CADA item recebido.
2. Não omita detalhes relevantes da tese, súmula, tema ou julgado.
3. Não simplifique demais.
4. Não use expressões como "segundo o julgado", "conforme o tema", "conforme a súmula".
5. Não copie literalmente a tese como enunciado.
6. Use linguagem de prova.
7. A questão deve ser plausível, técnica e fiel ao entendimento.
8. Pode inverter a lógica para criar item ERRADO.
9. A justificativa deve explicar bem o fundamento.
10. O gabarito deve ser apenas CERTO ou ERRADO.
11. Preserve o mesmo id recebido em cada questão.

FORMATO DE SAÍDA:
Responda apenas no JSON exigido pelo schema.

ITENS:
{json.dumps(itens_json, ensure_ascii=False, indent=2)}
""".strip()


def chamar_api(lote: List[ItemFonte], categoria: str, item_nome: str, dry_run: bool = False) -> Dict[str, Any]:
    if dry_run:
        return {
            "questoes": [
                {
                    "id": it.id,
                    "titulo_origem": it.titulo,
                    "questao": "[DRY-RUN] Questão simulada.",
                    "gabarito": "CERTO",
                    "justificativa": "[DRY-RUN] Justificativa simulada.",
                }
                for it in lote
            ]
        }

    chave = os.getenv("OPENAI_API_KEY")
    if not chave:
        raise RuntimeError(
            "OPENAI_API_KEY não configurada. No Terminal, rode:\n"
            'export OPENAI_API_KEY="sua_chave_aqui"'
        )

    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {chave}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODELO,
        "input": [
            {
                "role": "system",
                "content": (
                    "Você gera questões jurídicas em JSON estruturado. "
                    "Siga estritamente o schema e não omita nenhum item recebido."
                ),
            },
            {
                "role": "user",
                "content": montar_prompt(categoria, item_nome, lote),
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "questoes_juridicas_lote",
                "strict": True,
                "schema": esquema_json(),
            }
        },
        "temperature": 0.2,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=180)
    if resp.status_code >= 400:
        raise RuntimeError(f"Erro API {resp.status_code}: {resp.text[:2000]}")

    bruto = resp.json()
    texto = extrair_output_text(bruto)
    if not texto:
        raise RuntimeError(f"Não consegui extrair output_text da resposta: {json.dumps(bruto)[:2000]}")

    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Resposta não era JSON válido: {e}\nTrecho:\n{texto[:2000]}")


def validar_lote(lote: List[ItemFonte], resposta: Dict[str, Any]) -> Tuple[bool, str]:
    questoes = resposta.get("questoes", [])
    if not isinstance(questoes, list):
        return False, "Campo questoes ausente ou inválido."

    ids_enviados = [x.id for x in lote]
    ids_recebidos = [q.get("id") for q in questoes]

    if len(questoes) != len(lote):
        return False, f"Contagem do lote não bate. Enviados={len(lote)} Recebidos={len(questoes)}"

    if set(ids_enviados) != set(ids_recebidos):
        faltantes = sorted(set(ids_enviados) - set(ids_recebidos))
        extras = sorted(set(ids_recebidos) - set(ids_enviados))
        return False, f"IDs não batem. Faltantes={faltantes} Extras={extras}"

    for q in questoes:
        if q.get("gabarito") not in {"CERTO", "ERRADO"}:
            return False, f"Gabarito inválido no id {q.get('id')}: {q.get('gabarito')}"
        if not str(q.get("questao", "")).strip():
            return False, f"Questão vazia no id {q.get('id')}"
        if not str(q.get("justificativa", "")).strip():
            return False, f"Justificativa vazia no id {q.get('id')}"

    return True, "OK"


def renderizar_md(categoria: str, item_nome: str, questoes: List[Dict[str, Any]], validado: bool, observacao: str) -> str:
    linhas = []
    linhas.append(f"# {item_nome}")
    linhas.append("")
    linhas.append(f"**Categoria:** {categoria}")
    linhas.append(f"**Status de validação:** {'VALIDADO' if validado else 'NÃO VALIDADO'}")
    if observacao:
        linhas.append(f"**Observação:** {observacao}")
    linhas.append("")
    linhas.append("---")
    linhas.append("")

    for idx, q in enumerate(questoes, start=1):
        linhas.append(f"## Questão {idx}")
        linhas.append("")
        linhas.append(f"<!-- ID_ORIGEM: {q.get('id','')} -->")
        linhas.append(f"<!-- TITULO_ORIGEM: {q.get('titulo_origem','')} -->")
        linhas.append("")
        linhas.append(str(q.get("questao", "")).strip())
        linhas.append("")
        linhas.append(f"**Gabarito:** {q.get('gabarito', '').strip()}")
        linhas.append("")
        linhas.append("**Justificativa:**")
        linhas.append("")
        linhas.append(str(q.get("justificativa", "")).strip())
        linhas.append("")
        linhas.append("---")
        linhas.append("")

    return "\n".join(linhas)


# =========================
# PROCESSAMENTO
# =========================

def processar_pendencia(
    p: Pendencia,
    fontes: List[Path],
    dry_run: bool,
    itens_por_lote: int,
    sobrescrever: bool,
    permitir_extracao: bool = False,
) -> ResultadoArquivo:
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    PASTA_LOGS.mkdir(parents=True, exist_ok=True)

    if not permitir_extracao and "extracao" in normalizar(p.item):
        base_nome_skip = nome_arquivo_seguro(f"{p.categoria}_{p.item}")
        return ResultadoArquivo(
            categoria=p.categoria,
            item=p.item,
            status_auditoria=p.status,
            fonte="",
            esperado_auditoria=p.pdf_estimado,
            itens_extraidos=0,
            questoes_geradas=0,
            status_final="PULADO_EXTRACAO",
            observacao="Item com 'Extracao' ignorado por segurança. Use --permitir-extracao se quiser processar texto bruto.",
            arquivo_saida_md=str(PASTA_SAIDA / f"{base_nome_skip}.md"),
            arquivo_saida_json=str(PASTA_SAIDA / f"{base_nome_skip}.json"),
        )

    base_nome = nome_arquivo_seguro(f"{p.categoria}_{p.item}")
    saida_md = PASTA_SAIDA / f"{base_nome}.md"
    saida_json = PASTA_SAIDA / f"{base_nome}.json"

    if saida_md.exists() and saida_json.exists() and not sobrescrever:
        return ResultadoArquivo(
            categoria=p.categoria,
            item=p.item,
            status_auditoria=p.status,
            fonte="",
            esperado_auditoria=p.pdf_estimado,
            itens_extraidos=0,
            questoes_geradas=0,
            status_final="PULADO_JA_EXISTE",
            observacao="Arquivo já existia. Use --sobrescrever para gerar novamente.",
            arquivo_saida_md=str(saida_md),
            arquivo_saida_json=str(saida_json),
        )

    fonte = localizar_fonte(p, fontes, permitir_extracao=permitir_extracao)
    if not fonte:
        return ResultadoArquivo(
            categoria=p.categoria,
            item=p.item,
            status_auditoria=p.status,
            fonte="NAO_ENCONTRADA",
            esperado_auditoria=p.pdf_estimado,
            itens_extraidos=0,
            questoes_geradas=0,
            status_final="ERRO_FONTE",
            observacao="Não localizei arquivo-fonte correspondente.",
            arquivo_saida_md=str(saida_md),
            arquivo_saida_json=str(saida_json),
        )

    try:
        texto = ler_texto_arquivo(fonte)
    except Exception as e:
        return ResultadoArquivo(
            categoria=p.categoria,
            item=p.item,
            status_auditoria=p.status,
            fonte=str(fonte),
            esperado_auditoria=p.pdf_estimado,
            itens_extraidos=0,
            questoes_geradas=0,
            status_final="ERRO_LEITURA",
            observacao=str(e),
            arquivo_saida_md=str(saida_md),
            arquivo_saida_json=str(saida_json),
        )

    itens = extrair_itens(p.categoria, p.item, texto)
    if not itens:
        return ResultadoArquivo(
            categoria=p.categoria,
            item=p.item,
            status_auditoria=p.status,
            fonte=str(fonte),
            esperado_auditoria=p.pdf_estimado,
            itens_extraidos=0,
            questoes_geradas=0,
            status_final="ERRO_EXTRACAO",
            observacao="Não consegui separar julgados/temas/súmulas automaticamente.",
            arquivo_saida_md=str(saida_md),
            arquivo_saida_json=str(saida_json),
        )

    todas_questoes: List[Dict[str, Any]] = []
    logs_lotes: List[Dict[str, Any]] = []
    erro_observacoes: List[str] = []

    for inicio in range(0, len(itens), itens_por_lote):
        lote = itens[inicio:inicio + itens_por_lote]
        num_lote = inicio // itens_por_lote + 1

        try:
            resposta = chamar_api(lote, p.categoria, p.item, dry_run=dry_run)
            ok, obs = validar_lote(lote, resposta)
            logs_lotes.append({
                "lote": num_lote,
                "ids_enviados": [x.id for x in lote],
                "ok": ok,
                "observacao": obs,
                "resposta": resposta,
            })

            if not ok:
                erro_observacoes.append(f"Lote {num_lote}: {obs}")
            else:
                todas_questoes.extend(resposta["questoes"])

        except Exception as e:
            obs = f"Lote {num_lote}: {e}"
            erro_observacoes.append(obs)
            logs_lotes.append({
                "lote": num_lote,
                "ids_enviados": [x.id for x in lote],
                "ok": False,
                "observacao": obs,
            })

        if not dry_run:
            time.sleep(PAUSA_SEGUNDOS)

    # Validação final
    esperado = p.pdf_estimado or len(itens)
    questoes_geradas = len(todas_questoes)
    validado = True
    observacao_final = ""

    if erro_observacoes:
        validado = False
        observacao_final = " | ".join(erro_observacoes[:10])

    if questoes_geradas != len(itens):
        validado = False
        obs = f"Questões geradas ({questoes_geradas}) não batem com itens extraídos ({len(itens)})."
        observacao_final = f"{observacao_final} | {obs}".strip(" |")

    if p.pdf_estimado is not None and len(itens) != p.pdf_estimado:
        # Não invalida completamente se a extração divergir, mas marca como revisão obrigatória.
        validado = False
        obs = f"Itens extraídos ({len(itens)}) não batem com PDF estimado da auditoria ({p.pdf_estimado})."
        observacao_final = f"{observacao_final} | {obs}".strip(" |")

    status_final = "OK_VALIDADO" if validado else "NAO_VALIDADO"

    saida_json.write_text(
        json.dumps({
            "categoria": p.categoria,
            "item": p.item,
            "status_auditoria": p.status,
            "fonte": str(fonte),
            "esperado_auditoria": p.pdf_estimado,
            "itens_extraidos": len(itens),
            "questoes_geradas": questoes_geradas,
            "status_final": status_final,
            "observacao": observacao_final,
            "logs_lotes": logs_lotes,
            "questoes": todas_questoes,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md = renderizar_md(p.categoria, p.item, todas_questoes, validado, observacao_final)
    saida_md.write_text(md, encoding="utf-8")

    return ResultadoArquivo(
        categoria=p.categoria,
        item=p.item,
        status_auditoria=p.status,
        fonte=str(fonte),
        esperado_auditoria=p.pdf_estimado,
        itens_extraidos=len(itens),
        questoes_geradas=questoes_geradas,
        status_final=status_final,
        observacao=observacao_final,
        arquivo_saida_md=str(saida_md),
        arquivo_saida_json=str(saida_json),
    )


def salvar_controle(resultados: List[ResultadoArquivo], tag: str) -> Path:
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_SAIDA / f"controle_geracao_api_{tag}.csv"
    campos = [
        "categoria",
        "item",
        "status_auditoria",
        "fonte",
        "esperado_auditoria",
        "itens_extraidos",
        "questoes_geradas",
        "status_final",
        "observacao",
        "arquivo_saida_md",
        "arquivo_saida_json",
    ]
    with caminho.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for r in resultados:
            w.writerow({
                "categoria": r.categoria,
                "item": r.item,
                "status_auditoria": r.status_auditoria,
                "fonte": r.fonte,
                "esperado_auditoria": r.esperado_auditoria if r.esperado_auditoria is not None else "",
                "itens_extraidos": r.itens_extraidos,
                "questoes_geradas": r.questoes_geradas,
                "status_final": r.status_final,
                "observacao": r.observacao,
                "arquivo_saida_md": r.arquivo_saida_md,
                "arquivo_saida_json": r.arquivo_saida_json,
            })
    return caminho


def salvar_relatorio(resultados: List[ResultadoArquivo], tag: str) -> Path:
    caminho = PASTA_SAIDA / f"relatorio_geracao_api_{tag}.md"

    total = len(resultados)
    ok = sum(1 for r in resultados if r.status_final == "OK_VALIDADO")
    nao = sum(1 for r in resultados if r.status_final == "NAO_VALIDADO")
    outros = total - ok - nao

    linhas = []
    linhas.append("# Relatório de Geração de Questões por API")
    linhas.append("")
    linhas.append(f"Gerado em: {dt.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    linhas.append("")
    linhas.append("## Resumo")
    linhas.append("")
    linhas.append(f"- Itens processados: **{total}**")
    linhas.append(f"- OK_VALIDADO: **{ok}**")
    linhas.append(f"- NAO_VALIDADO: **{nao}**")
    linhas.append(f"- Outros/Pulados: **{outros}**")
    linhas.append("")
    linhas.append("## Detalhamento")
    linhas.append("")
    linhas.append("| Categoria | Item | Esperado | Extraído | Gerado | Status | Observação |")
    linhas.append("|---|---|---:|---:|---:|---|---|")
    for r in resultados:
        obs = (r.observacao or "").replace("|", "\\|")
        if len(obs) > 160:
            obs = obs[:157] + "..."
        linhas.append(
            f"| {r.categoria} | {r.item} | "
            f"{r.esperado_auditoria if r.esperado_auditoria is not None else ''} | "
            f"{r.itens_extraidos} | {r.questoes_geradas} | "
            f"{r.status_final} | {obs} |"
        )

    caminho.write_text("\n".join(linhas), encoding="utf-8")
    return caminho


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pendencias", type=str, default="", help="Caminho para pendencias_v2_*.csv")
    parser.add_argument("--categoria", type=str, default="", help="Filtrar por categoria: INFORMATIVO, RG, REPETITIVO, SUMULA")
    parser.add_argument("--item", type=str, default="", help='Filtrar por item exato ou parcial. Ex: "Info 1184 STF"')
    parser.add_argument("--incluir-incompletos", action="store_true", help="Também processa QUESTOES_INCOMPLETAS")
    parser.add_argument("--todos-status", action="store_true", help="Processa todos os status do CSV")
    parser.add_argument("--dry-run", action="store_true", help="Não chama API; apenas simula geração para testar fluxo")
    parser.add_argument("--itens-por-lote", type=int, default=ITENS_POR_LOTE_PADRAO)
    parser.add_argument("--sobrescrever", action="store_true", help="Sobrescreve arquivos já gerados na pasta de revisão")
    parser.add_argument("--permitir-extracao", action="store_true", help="Permite processar itens/fontes com 'Extracao'. NÃO recomendado para a base final.")
    args = parser.parse_args()

    caminho_pendencias = Path(args.pendencias).resolve() if args.pendencias else achar_ultimo_csv_pendencias()
    pendencias = ler_pendencias(caminho_pendencias)

    status_processar = set(STATUS_PROCESSAR_PADRAO)
    if args.incluir_incompletos:
        status_processar |= STATUS_INCOMPLETOS

    if not args.todos_status:
        pendencias = [p for p in pendencias if p.status in status_processar]

    if args.categoria:
        cat = normalizar(args.categoria)
        pendencias = [p for p in pendencias if normalizar(p.categoria) == cat]

    if args.item:
        alvo = normalizar(args.item)
        pendencias = [p for p in pendencias if alvo in normalizar(p.item)]

    if not args.permitir_extracao:
        antes = len(pendencias)
        pendencias = [p for p in pendencias if "extracao" not in normalizar(p.item)]
        pulados_extracao = antes - len(pendencias)
    else:
        pulados_extracao = 0

    print(f"CSV usado: {caminho_pendencias}")
    print(f"Pendências selecionadas: {len(pendencias)}")
    print(f"Modelo: {MODELO}")
    print(f"Itens por lote: {args.itens_por_lote}")
    print(f"Dry-run: {args.dry_run}")
    print(f"Permitir Extracao: {args.permitir_extracao}")
    if pulados_extracao:
        print(f"Itens 'Extracao' ignorados: {pulados_extracao}")
    print("")

    if not pendencias:
        print("Nada para processar com os filtros atuais.")
        return

    fontes = candidatos_fontes(permitir_extracao=args.permitir_extracao)
    print(f"Arquivos-fonte candidatos: {len(fontes)}")
    print("")

    resultados: List[ResultadoArquivo] = []
    for idx, p in enumerate(pendencias, start=1):
        print(f"[{idx}/{len(pendencias)}] {p.categoria} — {p.item} — {p.status}")
        r = processar_pendencia(
            p,
            fontes=fontes,
            dry_run=args.dry_run,
            itens_por_lote=args.itens_por_lote,
            sobrescrever=args.sobrescrever,
            permitir_extracao=args.permitir_extracao,
        )
        resultados.append(r)
        print(f"    -> {r.status_final} | extraídos={r.itens_extraidos} geradas={r.questoes_geradas}")
        if r.observacao:
            print(f"    obs: {r.observacao[:300]}")
        print("")

    tag = agora_tag()
    controle = salvar_controle(resultados, tag)
    relatorio = salvar_relatorio(resultados, tag)

    print("Concluído.")
    print(f"Controle CSV: {controle}")
    print(f"Relatório MD: {relatorio}")
    print("")
    print("REGRA DE SEGURANÇA:")
    print("Só copie para questoes_validadas_pdf/ os arquivos com status OK_VALIDADO e fonte sem Extracao.")


if __name__ == "__main__":
    main()
