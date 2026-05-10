import json
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

JSON = Path("data/questoes.json")
PASTA = Path("questoes_validadas_pdf")
BACKUP = Path("data/backups")
BACKUP.mkdir(parents=True, exist_ok=True)

ALVOS = [15, 19, 24, 28, 29, 30]

def ano_extra(n):
    if 14 <= n <= 21:
        return 2024
    if 22 <= n <= 27:
        return 2025
    if 28 <= n <= 30:
        return 2026
    return 2025

def campo(bloco, nome):
    m = re.search(
        rf"\*\*{nome}:\*\*\s*(.*?)(?=\n\*\*|\n---|\n## Questão|\Z)",
        bloco,
        re.S | re.I
    )
    return m.group(1).strip() if m else ""

def limpar(txt):
    return re.sub(r"\n{3,}", "\n\n", str(txt or "").strip())

def enunciado_do_bloco(bloco):
    e = campo(bloco, "Enunciado")
    if e:
        return limpar(e)

    # fallback: texto após comentários de origem até o gabarito
    b = re.sub(r"<!--.*?-->", "", bloco, flags=re.S).strip()
    b = re.split(r"\n\*\*Gabarito:\*\*|\n\*\*Resposta:\*\*", b, maxsplit=1, flags=re.I)[0]
    return limpar(b)

def resposta_do_bloco(bloco):
    g = campo(bloco, "Gabarito") or campo(bloco, "Resposta")
    g = g.upper()
    if "CERTO" in g or re.search(r"\bC\b", g):
        return "C"
    return "E"

def explicacao_do_bloco(bloco):
    return limpar(campo(bloco, "Justificativa") or campo(bloco, "Explicação") or campo(bloco, "Explicacao"))

def referencia_do_bloco(bloco):
    ref = campo(bloco, "Referência")
    return " ".join(ref.split())

def parse_arquivo(num):
    p = PASTA / f"Ed. Extra {num} STJ_questoes.md"
    if not p.exists():
        raise SystemExit(f"❌ Não achei: {p}")

    txt = p.read_text(encoding="utf-8", errors="ignore")
    blocos = re.split(r"\n## Questão\s+\d+", txt)[1:]

    ano = ano_extra(num)
    modulo = f"STJ Edição Extraordinária {ano}"

    questoes = []
    problemas = []

    for i, bloco in enumerate(blocos, 1):
        q = {
            "id": f"stj-{ano}-extra-{num}-q{i:03d}",
            "categoria": "Edição Extraordinária",
            "modulo": modulo,
            "tribunal": "STJ",
            "ano": ano,
            "informativo": num,
            "tipo": "edicao_extraordinaria",
            "fonte": f"Ed. Extra {num} STJ",
            "disciplina": "",
            "tema": "",
            "enunciado": enunciado_do_bloco(bloco),
            "respostaCorreta": resposta_do_bloco(bloco),
            "explicacao": explicacao_do_bloco(bloco),
            "referencia": referencia_do_bloco(bloco),
        }

        if not q["enunciado"]:
            problemas.append((q["id"], "sem enunciado"))
        if not q["referencia"]:
            problemas.append((q["id"], "sem referência"))

        questoes.append(q)

    return questoes, problemas

dados = json.loads(JSON.read_text(encoding="utf-8"))

backup = BACKUP / f"questoes_backup_antes_ed_extra_pontual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
backup.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
print("Backup:", backup)

# remove versões antigas desses informativos
alvos_str = {str(n) for n in ALVOS}
antes = len(dados)
dados = [
    q for q in dados
    if not (
        q.get("categoria") == "Edição Extraordinária"
        and str(q.get("informativo")) in alvos_str
    )
]
print("Removidas antigas:", antes - len(dados))

novas = []
todos_problemas = []

for n in ALVOS:
    qs, probs = parse_arquivo(n)
    print(f"Ed. Extra {n}: {len(qs)} questões")
    novas.extend(qs)
    todos_problemas.extend(probs)

if todos_problemas:
    print("\n❌ Problemas encontrados. Não salvei.")
    for item in todos_problemas[:50]:
        print(item)
    raise SystemExit(1)

dados.extend(novas)

ids = [q["id"] for q in dados]
dups = [x for x, c in Counter(ids).items() if c > 1]
if dups:
    print("\n❌ IDs duplicados. Não salvei.")
    print(dups[:20])
    raise SystemExit(1)

JSON.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

extras = [q for q in dados if q.get("categoria") == "Edição Extraordinária"]
print("\n✅ JSON atualizado.")
print("Total:", len(dados))
print("Ed Extra por informativo:", Counter(q.get("informativo") for q in extras))
