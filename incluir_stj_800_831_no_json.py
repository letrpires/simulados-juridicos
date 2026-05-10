import json
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

JSON = Path("data/questoes.json")
PASTA = Path("questoes_validadas_pdf")
BACKUP = Path("data/backups")
BACKUP.mkdir(parents=True, exist_ok=True)

ALVOS = [800,801,802,803,804,805,806,807,808,809,810,811,812,813,814,815,816,817,818,819,820,823,824,825,826,827,828,829,830,831]

def campo(bloco, nome):
    m = re.search(
        rf"\*\*{nome}:\*\*\s*(.*?)(?=\n\*\*|\n---|\n## Questão|\Z)",
        bloco,
        re.S | re.I
    )
    return m.group(1).strip() if m else ""

def limpar(txt):
    txt = re.sub(r"<!--.*?-->", "", str(txt), flags=re.S)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()

def extrair_enunciado(bloco):
    e = campo(bloco, "Enunciado")
    if e:
        return limpar(e)

    b = re.sub(r"<!--.*?-->", "", bloco, flags=re.S).strip()
    b = re.split(r"\n\*\*Gabarito:\*\*|\n\*\*Resposta:\*\*", b, maxsplit=1, flags=re.I)[0]
    return limpar(b)

def extrair_resposta(bloco):
    g = (campo(bloco, "Gabarito") or campo(bloco, "Resposta")).upper()
    if "CERTO" in g or re.search(r"\bC\b", g):
        return "C"
    return "E"

def extrair_explicacao(bloco):
    return limpar(campo(bloco, "Justificativa") or campo(bloco, "Explicação") or campo(bloco, "Explicacao"))

def extrair_referencia(bloco, info):
    ref = campo(bloco, "Referência")
    ref = " ".join(ref.split())
    return ref or f"Informativo {info} STJ"

def achar_arquivo(info):
    candidatos = sorted(PASTA.glob(f"*{info}*STJ*questoes*.md")) + sorted(PASTA.glob(f"*{info}*STJ*.md"))
    candidatos = [p for p in candidatos if "Ed. Extra" not in p.name and "Extra" not in p.name]
    if candidatos:
        return candidatos[0]
    return None

dados = json.loads(JSON.read_text(encoding="utf-8"))

backup = BACKUP / f"questoes_backup_antes_incluir_stj_800_831_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
backup.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
print("Backup:", backup)

# remove versões antigas dos mesmos infos, se houver
alvos_str = {str(n) for n in ALVOS}
antes = len(dados)
dados = [
    q for q in dados
    if not (
        q.get("tribunal") == "STJ"
        and q.get("categoria") == "Informativos"
        and str(q.get("informativo")) in alvos_str
    )
]
print("Removidas antigas:", antes - len(dados))

novas = []
problemas = []

for info in ALVOS:
    arq = achar_arquivo(info)
    if not arq:
        problemas.append((info, "arquivo não encontrado"))
        continue

    txt = arq.read_text(encoding="utf-8", errors="ignore")
    blocos = re.split(r"\n## Questão\s+\d+", txt)[1:]

    print(f"Info {info}: arquivo={arq.name} | questões={len(blocos)}")

    for i, bloco in enumerate(blocos, 1):
        q = {
            "id": f"stj-2024-info-{info}-q{i:03d}",
            "categoria": "Informativos",
            "modulo": "Informativos STJ 2024",
            "tribunal": "STJ",
            "ano": 2024,
            "informativo": info,
            "tipo": "informativo",
            "fonte": f"Info {info} STJ",
            "disciplina": campo(bloco, "Disciplina"),
            "tema": campo(bloco, "Tema") or campo(bloco, "Subtema"),
            "enunciado": extrair_enunciado(bloco),
            "respostaCorreta": extrair_resposta(bloco),
            "explicacao": extrair_explicacao(bloco),
            "referencia": extrair_referencia(bloco, info),
        }

        if not q["enunciado"]:
            problemas.append((q["id"], "sem enunciado"))
        if not q["explicacao"]:
            problemas.append((q["id"], "sem explicação"))
        if not q["referencia"]:
            problemas.append((q["id"], "sem referência"))

        novas.append(q)

if problemas:
    print("\n❌ Problemas encontrados. Não salvei.")
    for p in problemas[:80]:
        print(p)
    raise SystemExit(1)

dados.extend(novas)

ids = [q["id"] for q in dados]
duplicados = [k for k, v in Counter(ids).items() if v > 1]
if duplicados:
    print("\n❌ IDs duplicados. Não salvei.")
    print(duplicados[:30])
    raise SystemExit(1)

JSON.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

nums = sorted({
    int(q["informativo"]) for q in dados
    if q.get("tribunal") == "STJ"
    and q.get("categoria") == "Informativos"
    and q.get("informativo")
})

print("\n✅ JSON atualizado.")
print("Total JSON:", len(dados))
print("Primeiro STJ Info:", nums[0])
print("Último STJ Info:", nums[-1])
print("Infos STJ faltando 800-831:", sorted(set(ALVOS) - set(nums)))
