import json, os, re, time, argparse
from pathlib import Path
from datetime import datetime
import requests

BASE = Path("data/rg_repetitivos_base_limpa.json")
OUT_DIR = Path("questoes_rg_repetitivos_limpo")
OUT_DIR.mkdir(exist_ok=True)

API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL = "gpt-4.1-mini"

def prompt_item(item):
    tipo = item["categoria"]
    return f"""
Você é elaborador de questões jurídicas de concurso de alto nível.

Crie UMA questão no formato CERTO/ERRADO a partir da tese abaixo.

Regras:
- Uma única questão.
- Enunciado denso, técnico e plausível.
- Gabarito apenas "C" ou "E".
- Justificativa robusta, explicando a tese.
- Não invente dados.
- Não inclua disciplina.
- Responda somente em JSON válido.

Dados:
Categoria: {item["categoria"]}
Tribunal: {item["tribunal"]}
Tema: {item["tema"]}
Referência: {item["referencia"]}
Tese:
{item["tese"]}

Formato obrigatório:
{{
  "id_base": "{item["id_base"]}",
  "categoria": "{item["categoria"]}",
  "modulo": "{item["modulo"]}",
  "tribunal": "{item["tribunal"]}",
  "tema_numero": {item["tema_numero"]},
  "tema": "{item["tema"]}",
  "referencia": "{item["referencia"]}",
  "enunciado": "...",
  "respostaCorreta": "C ou E",
  "explicacao": "..."
}}
"""

def chamar_api(item):
    if not API_KEY:
        raise SystemExit("❌ OPENAI_API_KEY não encontrada no ambiente.")

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt_item(item)}],
        },
        timeout=120
    )
    r.raise_for_status()
    txt = r.json()["choices"][0]["message"]["content"].strip()
    txt = re.sub(r"^```json|```$", "", txt, flags=re.I).strip()
    return json.loads(txt)

def salvar_md(questoes, path):
    linhas = ["# Questões RG/Repetitivos - Base Limpa", ""]
    for i, q in enumerate(questoes, 1):
        linhas += [
            "---",
            "",
            f"## Questão {i}",
            "",
            f"<!-- ID_ORIGEM: {q['id_base']} -->",
            f"<!-- TEMA: {q['tema_numero']} -->",
            "",
            q["enunciado"].strip(),
            "",
            f"**Gabarito:** {'CERTO' if q['respostaCorreta']=='C' else 'ERRADO'}",
            "",
            "**Justificativa:**",
            "",
            q["explicacao"].strip(),
            "",
            f"**Referência:** {q['referencia']}",
            ""
        ]
    path.write_text("\n".join(linhas), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tipo", choices=["RG", "REP", "ALL"], default="RG")
    ap.add_argument("--inicio", type=int, default=0)
    ap.add_argument("--limite", type=int, default=10)
    ap.add_argument("--pausa", type=float, default=1.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    base = json.loads(BASE.read_text(encoding="utf-8"))

    if args.tipo == "RG":
        itens = [x for x in base if x["categoria"] == "Repercussão Geral"]
    elif args.tipo == "REP":
        itens = [x for x in base if x["categoria"] == "Repetitivos"]
    else:
        itens = base

    lote = itens[args.inicio:args.inicio + args.limite]

    print("Tipo:", args.tipo)
    print("Início:", args.inicio)
    print("Limite:", args.limite)
    print("Itens no lote:", len(lote))
    print("Primeiros:", [x["tema"] for x in lote[:10]])

    if args.dry_run:
        return

    questoes = []
    for idx, item in enumerate(lote, 1):
        print(f"[{idx}/{len(lote)}] {item['referencia']}")
        q = chamar_api(item)
        questoes.append(q)
        time.sleep(args.pausa)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"{args.tipo.lower()}_inicio_{args.inicio}_limite_{args.limite}_{stamp}"

    json_path = OUT_DIR / f"{nome}.json"
    md_path = OUT_DIR / f"{nome}.md"

    json_path.write_text(json.dumps(questoes, ensure_ascii=False, indent=2), encoding="utf-8")
    salvar_md(questoes, md_path)

    print("✅ Gerado:")
    print(json_path)
    print(md_path)

if __name__ == "__main__":
    main()
