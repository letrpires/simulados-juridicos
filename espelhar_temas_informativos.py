import json
import re
from pathlib import Path

JSON_PATH = Path("data/questoes.json")
HTML_JSON = Path("html_final/data/questoes.json")

dados = json.loads(JSON_PATH.read_text(encoding="utf-8"))

ids_existentes = {q["id"] for q in dados}
novas = []

def achar_tema(q):
    texto = " ".join([
        str(q.get("referencia", "")),
        str(q.get("tema", "")),
        str(q.get("enunciado", "")),
        str(q.get("explicacao", "")),
    ])

    m = re.search(r"\bTema\s*(?:n[ºo.]?\s*)?(\d{1,5})\b", texto, flags=re.I)
    if not m:
        return ""

    return f"Tema {m.group(1)}"

for q in dados:
    if q.get("categoria") != "Informativos":
        continue

    tema = achar_tema(q)
    if not tema:
        continue

    tribunal = q.get("tribunal", "")

    if tribunal == "STJ":
        nova_categoria = "Repetitivos"
        novo_tipo = "repetitivo"
        novo_modulo = "Repetitivos extraídos de Informativos"
        sufixo = "tema-repetitivo"

    elif tribunal == "STF":
        nova_categoria = "Repercussão Geral"
        novo_tipo = "repercussao_geral"
        novo_modulo = "Repercussão Geral extraída de Informativos"
        sufixo = "tema-rg"

    else:
        continue

    novo_id = f"{q['id']}-{sufixo}"

    if novo_id in ids_existentes:
        continue

    copia = dict(q)
    copia["id"] = novo_id
    copia["categoria"] = nova_categoria
    copia["tipo"] = novo_tipo
    copia["modulo"] = novo_modulo
    copia["tema"] = tema
    copia["referencia"] = tema
    copia["fonte_original"] = q.get("fonte", "")
    copia["espelhado_de_informativo"] = True

    tags = list(copia.get("tags", []))
    for tag in [nova_categoria, tema, "Extraído de Informativo"]:
        if tag not in tags:
            tags.append(tag)
    copia["tags"] = tags

    novas.append(copia)
    ids_existentes.add(novo_id)

dados.extend(novas)

JSON_PATH.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
HTML_JSON.write_text(JSON_PATH.read_text(encoding="utf-8"), encoding="utf-8")

print(f"✅ Questões espelhadas para RG/Repetitivos: {len(novas)}")
print("✅ JSON atualizado em data/ e html_final/data/")
