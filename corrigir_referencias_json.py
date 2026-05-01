import json
import re
from pathlib import Path

JSON_PATH = Path("data/questoes.json")
HTML_JSON = Path("html_final/data/questoes.json")
PASTA_MD_ESTRUTURADO = Path("md_criticos_reprocessados")
PASTA_QUESTOES = Path("questoes_validadas_pdf")


def limpar(txt):
    txt = txt or ""
    txt = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def numero_q(q):
    m = re.search(r"-q(\d+)(?:-|$)", q.get("id", ""))
    if m:
        return int(m.group(1))
    return None


def extrair_referencias_julgados(md_path):
    if not md_path.exists():
        return []

    txt = md_path.read_text(encoding="utf-8", errors="ignore")
    blocos = re.split(r"(?m)^## Julgado\s+\d+", txt)

    refs = []
    for bloco in blocos[1:]:
        m = re.search(
            r"\*\*Refer[eê]ncia:\*\*\s*\n?\s*(.*?)(?=\n\s*\*\*Status|\n\s*\*\*Observações|\n---|\Z)",
            bloco,
            flags=re.I | re.S,
        )
        refs.append(limpar(m.group(1)) if m else "")

    return refs




def extrair_referencias_questoes(md_path):
    if not md_path.exists():
        return []

    txt = md_path.read_text(encoding="utf-8", errors="ignore")
    blocos = re.split(r"(?m)^## Questão\s+\d+", txt)

    refs = []
    for bloco in blocos[1:]:
        m = re.search(
            r"\*\*Refer[eê]ncia:\*\*\s*\n?\s*(.*?)(?=\n\s*## Questão\s+\d+|\n\s*---|\Z)",
            bloco,
            flags=re.I | re.S,
        )
        refs.append(limpar(m.group(1)) if m else "")

    return refs


def extrair_temas_questoes(md_path):
    if not md_path.exists():
        return []

    txt = md_path.read_text(encoding="utf-8", errors="ignore")
    blocos = re.split(r"(?m)^## Questão\s+\d+", txt)

    temas = []
    for bloco in blocos[1:]:
        tema = ""

        m = re.search(r"<!--\s*TEMA:\s*(\d{1,5})\s*-->", bloco, flags=re.I)
        if m:
            tema = f"Tema {m.group(1)}"
        else:
            m = re.search(r"\bTema\s*(?:n[ºo.]?\s*)?(\d{1,5})\b", bloco, flags=re.I)
            if m:
                tema = f"Tema {m.group(1)}"

        temas.append(tema)

    return temas


dados = json.loads(JSON_PATH.read_text(encoding="utf-8"))

# 1) Remove temporariamente os espelhamentos, porque vamos auditar depois.
antes = len(dados)
dados = [q for q in dados if not q.get("espelhado_de_informativo")]
removidos = antes - len(dados)

refs_cache = {}
temas_cache = {}

corrigidos_info = 0
corrigidos_tema = 0
sem_ref_info = []

for q in dados:
    fonte = q.get("fonte", "")
    categoria = q.get("categoria", "")
    modulo = q.get("modulo", "")
    n = numero_q(q)

    if not n:
        continue

    # 2) Informativos: referência completa vem do MD estruturado por julgado.
    if categoria == "Informativos" and fonte.startswith("Info "):
        md_path = PASTA_MD_ESTRUTURADO / f"{fonte}_limpo_estruturado.md"

        if md_path not in refs_cache:
            refs_cache[md_path] = extrair_referencias_julgados(md_path)

        refs = refs_cache[md_path]
        ref = refs[n - 1] if n - 1 < len(refs) else ""

        if not ref:
            qmd_path = PASTA_QUESTOES / f"{fonte}_questoes.md"
            if qmd_path not in refs_cache:
                refs_cache[qmd_path] = extrair_referencias_questoes(qmd_path)
            refs_q = refs_cache[qmd_path]
            ref = refs_q[n - 1] if n - 1 < len(refs_q) else ""

        if ref:
            q["referencia"] = ref
            corrigidos_info += 1

            m = re.search(r"\bTema\s*(?:n[ºo.]?\s*)?(\d{1,5})\b", ref, flags=re.I)
            if m and not q.get("tema"):
                q["tema"] = f"Tema {m.group(1)}"
        else:
            sem_ref_info.append((fonte, n))

    # 3) RG/Repetitivos próprios: referência deve ser Tema XXXX quando existir no MD.
    if categoria in ["Repetitivos", "Repercussão Geral"] and not q.get("espelhado_de_informativo"):
        md_path = PASTA_QUESTOES / f"{modulo}.md"

        if md_path not in temas_cache:
            temas_cache[md_path] = extrair_temas_questoes(md_path)

        temas = temas_cache[md_path]
        tema = temas[n - 1] if n - 1 < len(temas) else ""

        if tema:
            q["tema"] = tema
            q["referencia"] = tema
            corrigidos_tema += 1

JSON_PATH.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
HTML_JSON.write_text(JSON_PATH.read_text(encoding="utf-8"), encoding="utf-8")

print("✅ Espelhamentos removidos temporariamente:", removidos)
print("✅ Referências completas de Informativos corrigidas:", corrigidos_info)
print("✅ Referências de Temas RG/Repetitivos corrigidas:", corrigidos_tema)

if sem_ref_info:
    print("\n⚠️ Informativos ainda sem referência:")
    for fonte, n in sem_ref_info[:30]:
        print(f"- {fonte} q{n:03d}")
    if len(sem_ref_info) > 30:
        print(f"... mais {len(sem_ref_info)-30}")
else:
    print("✅ Nenhum informativo ficou sem referência.")
