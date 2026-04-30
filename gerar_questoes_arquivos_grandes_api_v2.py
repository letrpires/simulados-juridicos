#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_questoes_arquivos_grandes_api_v2.py

Versão corrigida para arquivos grandes com Tema/Tese.

REGRAS ESPECIAIS:
1. Exclui definitivamente:
   - aguardando julgamento de mérito
   - irrelevante
   - duplicados por número
   - duplicados conceituais por tese normalizada
   - observar temas referentes a expurgos/instruções equivalentes
2. Mantém como item de revisão manual:
   - consultar manualmente
   - tese muito grande
   - buscar manualmente
   - tese saúde / importante / consultar manualmente
3. Para itens de revisão manual, NÃO chama API.
   Cria uma questão-sentinela com o número do tema e a frase de revisão.
4. Para itens válidos, chama API e exige 1 questão por tema.
5. Só salva MD final se: questões_api + questões_manuais == total de itens mantidos.

Uso:
python3 gerar_questoes_arquivos_grandes_api_v2.py --arquivo "questoes_validadas_pdf/Repetitivo - Civil.md" --dry-run
python3 gerar_questoes_arquivos_grandes_api_v2.py --arquivo "questoes_validadas_pdf/Repetitivo - Civil.md" --sobrescrever
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("ERRO: instale requests com: python3 -m pip install requests")
    sys.exit(1)

PASTA_SAIDA = Path("questoes_geradas_api_revisar_grandes")
PASTA_SAIDA.mkdir(exist_ok=True)

ARQUIVOS_PADRAO = [
    "questoes_validadas_pdf/RG - Administrativo.md",
    "questoes_validadas_pdf/Repetitivo - Civil.md",
    "questoes_validadas_pdf/Repetitivo - Processo Civil.md",
]

# Excluir de vez: não vira questão e não entra no MD final.
EXCLUIR_PATTERNS = [
    r"\[\s*irrelevante\s*\]",
    r"aguardando\s+julgamento\s+de\s+m[ée]rito",
    r"observar\s+temas\s+referentes",
]

# Manter como questão-sentinela de revisão manual.
MANUAL_PATTERNS = [
    r"consultar\s+manualmente",
    r"buscar\s+manualmente",
    r"tese\s+muito\s+grande",
    r"tese\s+sa[uú]de",
]

@dataclass
class Tema:
    numero: str
    tese: str
    bruto: str
    status: str = "OK"  # OK, MANUAL, EXCLUIR
    observacao: str = ""


def slugify(nome: str) -> str:
    s = nome.lower().strip()
    s = re.sub(r"[áàâãä]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[íìîï]", "i", s)
    s = re.sub(r"[óòôõö]", "o", s)
    s = re.sub(r"[úùûü]", "u", s)
    s = re.sub(r"ç", "c", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def limpar_texto(t: str) -> str:
    t = html.unescape(t)
    t = t.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    t = re.sub(r"\*\*Anotações NUGEP.*", "", t, flags=re.I | re.S)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s+([,.;:])", r"\1", t)
    t = t.replace("despartes", "das partes")
    t = t.replace("des partes", "das partes")
    t = t.replace("agentepúblico", "agente público")
    t = t.replace("segurançajurídica", "segurança jurídica")
    return t.strip()


def normalizar_tese_para_duplicidade(t: str) -> str:
    t = limpar_texto(t).lower()
    t = re.sub(r"[^a-z0-9áàâãéèêíóôõúç ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def frase_manual(tese: str) -> str:
    baixa = tese.lower()
    if re.search(r"tese\s+muito\s+grande", baixa, flags=re.I):
        return "Tese muito grande. Consultar manualmente."
    if re.search(r"tese\s+sa[uú]de", baixa, flags=re.I):
        return "Tese Saúde. Importante. Consultar manualmente."
    if re.search(r"buscar\s+manualmente", baixa, flags=re.I):
        return "Buscar manualmente."
    if re.search(r"consultar\s+manualmente", baixa, flags=re.I):
        return "Consultar manualmente."
    return "Consultar manualmente."


def extrair_temas(texto: str) -> list[Tema]:
    padrao = re.compile(r"(?im)^\s*(?:##\s*Tema\s+(\d+)|\*\*Tema\s+(\d+)\*\*)\s*$")
    matches = list(padrao.finditer(texto))
    temas: list[Tema] = []
    numeros_vistos = set()
    teses_vistas: dict[str, str] = {}

    for i, m in enumerate(matches):
        num = m.group(1) or m.group(2)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        bloco = texto[start:end].strip()
        bloco = re.sub(r"\n?---\s*$", "", bloco).strip()

        tese_match = re.search(r"\*\*Tese(?:\s+Firmada)?\s*:\*\*\s*(.*)", bloco, flags=re.I | re.S)
        tese = tese_match.group(1).strip() if tese_match else bloco
        tese = limpar_texto(tese)

        status = "OK"
        obs = ""

        if not tese:
            status = "EXCLUIR"
            obs = "Tema sem tese identificada."
        elif num in numeros_vistos:
            status = "EXCLUIR"
            obs = "Tema duplicado por número no arquivo."
        elif any(re.search(p, tese, flags=re.I) for p in EXCLUIR_PATTERNS):
            status = "EXCLUIR"
            obs = "Excluído por regra: aguardando julgamento, irrelevante ou instrução de tema correlato."
        elif any(re.search(p, tese, flags=re.I) for p in MANUAL_PATTERNS):
            status = "MANUAL"
            obs = frase_manual(tese)
        else:
            chave = normalizar_tese_para_duplicidade(tese)
            if chave and chave in teses_vistas:
                status = "EXCLUIR"
                obs = f"Duplicado conceitual da tese do Tema {teses_vistas[chave]}."
            else:
                teses_vistas[chave] = num

        numeros_vistos.add(num)
        temas.append(Tema(numero=num, tese=tese, bruto=bloco, status=status, observacao=obs))

    return temas


def montar_prompt(nome_item: str, lote: list[Tema]) -> str:
    itens = []
    for t in lote:
        itens.append({"id": f"TEMA-{t.numero}", "tema": t.numero, "tese": t.tese})
    return f"""
Você é examinador experiente de concurso público jurídico.

Transforme CADA tema/tese abaixo em EXATAMENTE UMA questão de CERTO ou ERRADO, em padrão alto de concurso público jurídico, estilo CEBRASPE/CESPE.

REGRAS ABSOLUTAS:
1. Gere exatamente UMA questão para CADA item recebido.
2. Não omita detalhes relevantes da tese.
3. Não simplifique demais.
4. Não use expressões como "segundo o tema", "segundo o julgado" ou "conforme a tese".
5. Não copie literalmente a tese como enunciado.
6. Use linguagem técnica de prova.
7. A questão deve ser plausível, técnica e fiel ao entendimento.
8. Pode inverter a lógica da tese para criar item ERRADO.
9. A justificativa deve explicar bem o fundamento do entendimento.
10. O gabarito deve ser apenas CERTO ou ERRADO.
11. NÃO inclua comentários fora do JSON.
12. A resposta deve conter exatamente {len(lote)} objetos no array JSON.

FORMATO DE SAÍDA OBRIGATÓRIO:
{{
  "questoes": [
    {{
      "id_origem": "TEMA-0000",
      "tema": "0000",
      "questao": "enunciado da questão",
      "gabarito": "CERTO ou ERRADO",
      "justificativa": "explicação completa e didática"
    }}
  ]
}}

FONTE: {nome_item}
ITENS:
{json.dumps(itens, ensure_ascii=False, indent=2)}
""".strip()


def extrair_texto_responses(data: dict[str, Any]) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    partes = []
    for out in data.get("output", []):
        for c in out.get("content", []):
            if "text" in c:
                partes.append(c["text"])
    texto = "\n".join(partes).strip()
    if not texto:
        raise RuntimeError("Resposta da API sem texto extraível.")
    texto = re.sub(r"^```(?:json)?\s*", "", texto.strip(), flags=re.I)
    texto = re.sub(r"\s*```$", "", texto.strip())
    return texto.strip()


def chamar_api(prompt: str, modelo: str, temperatura: float, tentativas: int = 3) -> list[dict[str, Any]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY não configurada. Use: export OPENAI_API_KEY="sua_chave"')

    url = "https://api.openai.com/v1/responses"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": modelo,
        "input": prompt,
        "temperature": temperatura,
        "text": {"format": {"type": "json_object"}},
    }

    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=180)
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:1000]}")
            data = r.json()
            texto = extrair_texto_responses(data)
            parsed = json.loads(texto)
            if isinstance(parsed, dict):
                for key in ["questoes", "questions", "itens", "items", "respostas"]:
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
            if isinstance(parsed, list):
                return parsed
            raise RuntimeError("JSON retornado não contém array de questões.")
        except Exception as e:
            ultimo_erro = e
            time.sleep(2 * tentativa)
    raise RuntimeError(str(ultimo_erro))


def questao_manual(nome_item: str, t: Tema) -> dict[str, Any]:
    frase = t.observacao or frase_manual(t.tese)
    return {
        "id_origem": f"TEMA-{t.numero}",
        "tema": t.numero,
        "questao": f"Tema {t.numero}: {frase}",
        "gabarito": "REVISAR MANUALMENTE",
        "justificativa": frase,
        "tipo": "MANUAL",
    }


def render_md(nome_item: str, questoes: list[dict[str, Any]]) -> str:
    linhas = [f"# {nome_item}", "", "**Status de validação:** VALIDADO", "", "---", ""]
    for i, q in enumerate(questoes, 1):
        g = str(q.get("gabarito", "")).strip().upper()
        # Para questões-sentinela, mantemos a resposta de revisão manual.
        if g not in {"CERTO", "ERRADO", "REVISAR MANUALMENTE"}:
            g = "REVISAR MANUALMENTE"
        linhas += [
            f"## Questão {i}", "",
            f"<!-- ID_ORIGEM: {q.get('id_origem','')} -->",
            f"<!-- TEMA: {q.get('tema','')} -->",
            f"<!-- TIPO: {q.get('tipo','API')} -->", "",
            str(q.get("questao", "")).strip(), "",
            f"**Gabarito:** {g}", "",
            "**Justificativa:**", "",
            str(q.get("justificativa", "")).strip(), "",
            "---", "",
        ]
    return "\n".join(linhas)


def processar_arquivo(caminho: Path, args: argparse.Namespace, timestamp: str, writer: csv.DictWriter) -> dict[str, Any]:
    nome_item = caminho.stem
    texto = caminho.read_text(encoding="utf-8")
    temas = extrair_temas(texto)
    temas_ok = [t for t in temas if t.status == "OK"]
    temas_manual = [t for t in temas if t.status == "MANUAL"]
    temas_excluir = [t for t in temas if t.status == "EXCLUIR"]
    temas_mantidos = temas_ok + temas_manual
    slug = slugify(nome_item)

    print(f"\nArquivo: {caminho}")
    print(f"Item: {nome_item}")
    print(f"Temas encontrados: {len(temas)}")
    print(f"Temas API válidos: {len(temas_ok)}")
    print(f"Temas manuais mantidos: {len(temas_manual)}")
    print(f"Temas excluídos: {len(temas_excluir)}")
    print(f"Total mantido para MD final: {len(temas_mantidos)}")

    limpos_path = PASTA_SAIDA / f"{slug}_temas_classificados_{timestamp}.csv"
    with limpos_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["tema", "status", "observacao", "tese"])
        w.writeheader()
        for t in temas:
            w.writerow({"tema": t.numero, "status": t.status, "observacao": t.observacao, "tese": t.tese})

    if args.dry_run:
        writer.writerow({
            "arquivo": str(caminho), "item": nome_item, "temas_encontrados": len(temas),
            "temas_api": len(temas_ok), "temas_manuais": len(temas_manual), "temas_excluidos": len(temas_excluir),
            "total_mantido": len(temas_mantidos), "gerado_api": 0, "gerado_manual": 0,
            "status": "DRY_RUN", "observacao": "Dry-run: nenhuma API chamada e nenhum MD de questões criado."
        })
        return {"item": nome_item, "encontrados": len(temas), "api": len(temas_ok), "manuais": len(temas_manual), "excluidos": len(temas_excluir), "mantido": len(temas_mantidos), "gerado": 0, "status": "DRY_RUN"}

    saida_md = PASTA_SAIDA / f"{slug}.md"
    saida_json = PASTA_SAIDA / f"{slug}.json"
    if saida_md.exists() and not args.sobrescrever:
        status = "PULADO_JA_EXISTE"
        writer.writerow({
            "arquivo": str(caminho), "item": nome_item, "temas_encontrados": len(temas),
            "temas_api": len(temas_ok), "temas_manuais": len(temas_manual), "temas_excluidos": len(temas_excluir),
            "total_mantido": len(temas_mantidos), "gerado_api": 0, "gerado_manual": 0,
            "status": status, "observacao": "Use --sobrescrever para gerar novamente."
        })
        return {"item": nome_item, "encontrados": len(temas), "api": len(temas_ok), "manuais": len(temas_manual), "excluidos": len(temas_excluir), "mantido": len(temas_mantidos), "gerado": 0, "status": status}

    questoes_api: list[dict[str, Any]] = []
    questoes_manuais = [questao_manual(nome_item, t) for t in temas_manual]
    observacoes = []

    for idx in range(0, len(temas_ok), args.itens_por_lote):
        lote = temas_ok[idx:idx + args.itens_por_lote]
        print(f"  Lote {idx//args.itens_por_lote + 1}: temas {lote[0].numero} a {lote[-1].numero} ({len(lote)} itens)")
        prompt = montar_prompt(nome_item, lote)
        try:
            resp = chamar_api(prompt, args.modelo, args.temperatura)
            if len(resp) != len(lote):
                observacoes.append(f"Lote iniciado no tema {lote[0].numero}: enviados={len(lote)} recebidos={len(resp)}")
                continue
            for q in resp:
                q.setdefault("tipo", "API")
            questoes_api.extend(resp)
        except Exception as e:
            observacoes.append(f"Erro no lote iniciado no tema {lote[0].numero}: {e}")
            continue
        time.sleep(args.pausa)

    total_gerado = len(questoes_api) + len(questoes_manuais)
    if len(questoes_api) == len(temas_ok) and total_gerado == len(temas_mantidos):
        status = "OK_VALIDADO"
        questoes = questoes_api + questoes_manuais
        questoes.sort(key=lambda q: int(re.sub(r"\D", "", str(q.get("tema", "0"))) or 0))
        saida_json.write_text(json.dumps(questoes, ensure_ascii=False, indent=2), encoding="utf-8")
        saida_md.write_text(render_md(nome_item, questoes), encoding="utf-8")
    else:
        status = "NAO_VALIDADO"
        parcial = PASTA_SAIDA / f"{slug}_PARCIAL_NAO_VALIDADO_{timestamp}.json"
        parcial.write_text(json.dumps({"api": questoes_api, "manual": questoes_manuais}, ensure_ascii=False, indent=2), encoding="utf-8")

    writer.writerow({
        "arquivo": str(caminho), "item": nome_item, "temas_encontrados": len(temas),
        "temas_api": len(temas_ok), "temas_manuais": len(temas_manual), "temas_excluidos": len(temas_excluir),
        "total_mantido": len(temas_mantidos), "gerado_api": len(questoes_api), "gerado_manual": len(questoes_manuais),
        "status": status, "observacao": " | ".join(observacoes)
    })
    return {"item": nome_item, "encontrados": len(temas), "api": len(temas_ok), "manuais": len(temas_manual), "excluidos": len(temas_excluir), "mantido": len(temas_mantidos), "gerado": total_gerado, "status": status, "obs": " | ".join(observacoes)}


def localizar_arquivos(args: argparse.Namespace) -> list[Path]:
    if args.arquivo:
        return [Path(args.arquivo)]
    if args.todos:
        return [Path(a) for a in ARQUIVOS_PADRAO if Path(a).exists()]
    return [Path(a) for a in ARQUIVOS_PADRAO if Path(a).exists()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arquivo", help="Processar um arquivo específico .md")
    ap.add_argument("--todos", action="store_true", help="Processar os três arquivos padrão em questoes_validadas_pdf/")
    ap.add_argument("--dry-run", action="store_true", help="Só contar/classificar temas; não chama API e não cria MD de questões")
    ap.add_argument("--sobrescrever", action="store_true", help="Sobrescrever saída existente")
    ap.add_argument("--itens-por-lote", type=int, default=1, help="Quantidade de temas por chamada API. Recomendado: 1")
    ap.add_argument("--modelo", default="gpt-4.1-mini")
    ap.add_argument("--temperatura", type=float, default=0.2)
    ap.add_argument("--pausa", type=float, default=0.4)
    args = ap.parse_args()

    if args.itens_por_lote < 1:
        print("ERRO: --itens-por-lote deve ser >= 1")
        sys.exit(1)

    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    arquivos = localizar_arquivos(args)
    if not arquivos:
        print("Nenhum arquivo encontrado. Use --arquivo caminho/do/arquivo.md")
        sys.exit(1)

    print("Arquivos selecionados:")
    for a in arquivos:
        print(f"- {a}")
    print(f"Dry-run: {args.dry_run}")
    print(f"Itens por lote: {args.itens_por_lote}")
    print(f"Modelo: {args.modelo}")
    print("Regras: excluir aguardando/irrelevante/duplicados; manter consultar manualmente/tese muito grande como sentinela.")

    controle = PASTA_SAIDA / f"controle_arquivos_grandes_v2_{timestamp}.csv"
    relatorio = PASTA_SAIDA / f"relatorio_arquivos_grandes_v2_{timestamp}.md"
    resultados = []
    campos = ["arquivo", "item", "temas_encontrados", "temas_api", "temas_manuais", "temas_excluidos", "total_mantido", "gerado_api", "gerado_manual", "status", "observacao"]
    with controle.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for caminho in arquivos:
            if not caminho.exists():
                print(f"AVISO: não encontrado: {caminho}")
                continue
            resultados.append(processar_arquivo(caminho, args, timestamp, writer))

    linhas = ["# Relatório — Arquivos Grandes V2", "", f"Gerado em: {dt.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", "", "## Resumo", ""]
    linhas += ["| Item | Encontrados | API | Manuais mantidos | Excluídos | Total mantido | Gerado | Status |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in resultados:
        linhas.append(f"| {r['item']} | {r['encontrados']} | {r['api']} | {r['manuais']} | {r['excluidos']} | {r['mantido']} | {r['gerado']} | {r['status']} |")
    linhas += [
        "", "## Regras aplicadas", "",
        "- Excluídos: `aguardando julgamento`, `irrelevante`, duplicados por número, duplicados conceituais e instruções de temas correlatos.",
        "- Mantidos como revisão manual: `consultar manualmente`, `buscar manualmente`, `tese muito grande` e equivalentes.",
        "- Questões manuais recebem `Gabarito: REVISAR MANUALMENTE`.",
        "", "## Segurança", "",
        "Só copie para `questoes_validadas_pdf/` arquivos com status `OK_VALIDADO`.",
        "Em `dry-run`, nenhum arquivo `.md` de questões é criado.",
    ]
    relatorio.write_text("\n".join(linhas), encoding="utf-8")

    print("\nConcluído.")
    print(f"Controle CSV: {controle}")
    print(f"Relatório MD: {relatorio}")
    print("\nREGRA DE SEGURANÇA: só copie arquivos OK_VALIDADO para questoes_validadas_pdf/.")

if __name__ == "__main__":
    main()
