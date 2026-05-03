import re
from pathlib import Path

CRITICOS = Path("md_criticos_reprocessados")
VALIDADAS = Path("questoes_validadas_pdf")

NUMEROS = [14, 16, 17, 18, 20, 21, 24, 28, 29, 30]

def extrair_refs_critico(num):
    p = CRITICOS / f"Ed. Extra {num} STJ_limpo_estruturado.md"
    txt = p.read_text(encoding="utf-8", errors="ignore")
    blocos = re.split(r"\n## Julgado\s+\d+", txt)[1:]

    refs = []
    for bloco in blocos:
        m = re.search(
            r"\*\*Referência:\*\*\s*(.*?)(?=\n\*\*|\n---|\Z)",
            bloco,
            re.S | re.I
        )
        refs.append(" ".join(m.group(1).split()) if m else "")

    return refs

def inserir_ref(bloco, ref):
    bloco = re.sub(
        r"\*\*Referência:\*\*\s*.*?(?=\n\*\*|\n---|\Z)",
        "",
        bloco,
        flags=re.S | re.I
    ).strip()

    if "**Status:**" in bloco:
        bloco = bloco.replace("**Status:**", f"**Referência:**\n{ref}\n\n**Status:**", 1)
    else:
        bloco = bloco + f"\n\n**Referência:**\n{ref}"

    return bloco.strip()

for num in NUMEROS:
    qfile = VALIDADAS / f"Ed. Extra {num} STJ_questoes.md"

    if not qfile.exists():
        print(f"❌ Não existe: {qfile}")
        continue

    refs = extrair_refs_critico(num)

    txt = qfile.read_text(encoding="utf-8", errors="ignore")
    partes = re.split(r"\n## Questão\s+\d+", txt)
    cabecalho = partes[0].rstrip()
    blocos = partes[1:]

    print(f"Ed. Extra {num}: questões={len(blocos)} | refs={len(refs)}")

    if len(blocos) != len(refs):
        print(f"⚠️ PULADO por divergência: {num}")
        continue

    novo = [cabecalho]

    for i, bloco in enumerate(blocos, 1):
        novo.append(f"\n\n## Questão {i}\n\n{inserir_ref(bloco, refs[i-1])}")

    qfile.write_text("".join(novo).strip() + "\n", encoding="utf-8")
    print(f"✅ Atualizado: {qfile}")
