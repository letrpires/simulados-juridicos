import json
import re
import shutil
from pathlib import Path
from datetime import datetime

JSON_PATH = Path("data/questoes.json")
HTML_JSON_PATH = Path("html_final/data/questoes.json")
BACKUP_DIR = Path("data/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

agora = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BACKUP_DIR / f"questoes_backup_antes_normalizacao_{agora}.json"

shutil.copy(JSON_PATH, backup)

dados = json.loads(JSON_PATH.read_text(encoding="utf-8"))

def limpar(txt):
    return re.sub(r"\s+", " ", str(txt or "")).strip()

def tema_normalizado(txt):
    txt = limpar(txt)
    m = re.search(r"\bTema\s*(?:n[ºo.]?\s*)?(\d[\d.]*)", txt, flags=re.I)
    if not m:
        return ""
    n = m.group(1).replace(".", "")
    return f"Tema {int(n)}" if n.isdigit() else ""

def extrair_anos_referencia(txt):
    txt = limpar(txt)
    anos = re.findall(r"\bjulgad[oa]s?\s+em\s+\d{1,2}/\d{1,2}/(20\d{2})\b", txt, flags=re.I)

    if not anos:
        anos = re.findall(r"\b(20\d{2})\b", txt)

    return [int(a) for a in anos]


def aplicar_ano_majoritario_informativos(dados):
    from collections import Counter, defaultdict

    anos_por_fonte = defaultdict(list)

    for q in dados:
        if q.get("categoria") != "Informativos":
            continue

        fonte = limpar(q.get("fonte"))
        if not fonte.startswith("Info "):
            continue

        texto_ref = " ".join([
            limpar(q.get("referencia")),
            limpar(q.get("explicacao")),
            limpar(q.get("enunciado")),
        ])

        anos = extrair_anos_referencia(texto_ref)

        if anos:
            anos_por_fonte[fonte].extend(anos)

    ano_majoritario = {}

    for fonte, anos in anos_por_fonte.items():
        if anos:
            ano_majoritario[fonte] = Counter(anos).most_common(1)[0][0]

    corrigidos = 0

    for q in dados:
        if q.get("categoria") != "Informativos":
            continue

        fonte = limpar(q.get("fonte"))
        tribunal = limpar(q.get("tribunal"))

        if fonte in ano_majoritario and tribunal in ["STF", "STJ"]:
            ano = ano_majoritario[fonte]
            modulo_correto = f"Informativos {tribunal} {ano}"

            if q.get("ano") != ano or q.get("modulo") != modulo_correto:
                q["ano"] = ano
                q["modulo"] = modulo_correto
                corrigidos += 1

    return corrigidos

def detectar_disciplina(q):
    partes = " ".join([
        q.get("disciplina", ""),
        q.get("modulo", ""),
        q.get("fonte", ""),
        q.get("tags", []) if isinstance(q.get("tags"), str) else " ".join(q.get("tags", [])),
        q.get("enunciado", ""),
        q.get("explicacao", ""),
    ]).lower()

    mapa = [
        ("Direito Constitucional", ["constitucional", "controle de constitucionalidade", "competência legislativa"]),
        ("Direito Administrativo", ["administrativo", "servidor", "licitação", "improbidade", "concurso público"]),
        ("Direito Civil", ["civil", "contrato", "responsabilidade civil", "família", "sucessões", "posse", "propriedade"]),
        ("Direito Processual Civil", ["processual civil", "processo civil", "cpc", "cumprimento de sentença", "coisa julgada"]),
        ("Direito Penal", ["penal", "crime", "pena", "tráfico", "homicídio", "roubo", "furto"]),
        ("Direito Processual Penal", ["processual penal", "processo penal", "prisão", "habeas corpus", "júri", "prova penal"]),
        ("Direito Tributário", ["tributário", "tributo", "icms", "iss", "ipi", "irpj", "contribuição", "taxa"]),
        ("Direito Ambiental", ["ambiental", "meio ambiente", "unidade de conservação"]),
        ("Direito do Consumidor", ["consumidor", "cdc", "plano de saúde", "produto", "serviço"]),
        ("Direito Empresarial", ["empresarial", "falência", "recuperação judicial", "sociedade empresária"]),
        ("Direito Eleitoral", ["eleitoral", "eleição", "mandato", "partido"]),
        ("Direitos Humanos", ["direitos humanos", "convencionalidade"]),
    ]

    for disciplina, termos in mapa:
        if any(t in partes for t in termos):
            return disciplina

    return "Não classificada"

def normalizar_modulo(q):
    modulo = limpar(q.get("modulo"))
    categoria = q.get("categoria")
    tribunal = q.get("tribunal")
    ano = q.get("ano")

    # Mantém módulos específicos de súmulas, RG e Repetitivos.
    if categoria in ["Súmulas", "Repetitivos", "Repercussão Geral", "Edição Extraordinária"]:
        return modulo

    # Padroniza Informativos sem apagar o ano.
    if categoria == "Informativos":
        if tribunal == "STF":
            return f"Informativos STF {ano}" if ano else "Informativos STF"
        if tribunal == "STJ":
            return f"Informativos STJ {ano}" if ano else "Informativos STJ"

    return modulo

def completar_referencia(q):
    ref = limpar(q.get("referencia"))
    if ref:
        return ref

    categoria = q.get("categoria")
    tribunal = limpar(q.get("tribunal"))
    tema = tema_normalizado(" ".join([
        limpar(q.get("tema")),
        limpar(q.get("referencia")),
        limpar(q.get("enunciado")),
        limpar(q.get("explicacao")),
    ]))

    if categoria == "Repetitivos" and tema:
        return f"{tema} STJ"

    if categoria == "Repercussão Geral" and tema:
        return f"{tema} STF"

    if categoria == "Súmulas":
        fonte = limpar(q.get("fonte"))
        modulo = limpar(q.get("modulo"))
        texto = " ".join([fonte, modulo, q.get("enunciado", "")])
        m = re.search(r"\bS[úu]mula(?:\s+Vinculante)?\s*(\d+)\b", texto, flags=re.I)
        if m:
            if "vinculante" in texto.lower():
                return f"Súmula Vinculante {m.group(1)} STF"
            return f"Súmula {m.group(1)} {tribunal}".strip()

        return modulo or fonte or "Súmula"

    if categoria == "Informativos":
        return limpar(q.get("fonte")) or "Informativo"

    return limpar(q.get("fonte")) or limpar(q.get("modulo")) or "Referência não identificada"

alterados = {
    "disciplina": 0,
    "referencia": 0,
    "modulo": 0,
    "tema": 0,
    "resposta_revisar": 0,
}

for q in dados:
    # Disciplina
    if not limpar(q.get("disciplina")):
        q["disciplina"] = detectar_disciplina(q)
        alterados["disciplina"] += 1

    # Tema normalizado quando houver
    tema = tema_normalizado(" ".join([
        limpar(q.get("tema")),
        limpar(q.get("referencia")),
    ]))
    if tema and q.get("tema") != tema:
        q["tema"] = tema
        alterados["tema"] += 1

    # Referência
    if not limpar(q.get("referencia")):
        q["referencia"] = completar_referencia(q)
        alterados["referencia"] += 1

    # Módulo
    novo_modulo = normalizar_modulo(q)
    if novo_modulo != q.get("modulo"):
        q["modulo"] = novo_modulo
        alterados["modulo"] += 1

    # REVISAR: mantém a questão, mas evita quebrar frontend.
    if q.get("respostaCorreta") == "REVISAR":
        q["respostaCorreta"] = "E"
        q["revisar_manualmente"] = True
        alterados["resposta_revisar"] += 1

# ============================================================
# AJUSTES FINAIS BLINDADOS
# ============================================================

ajustes_finais = {
    "modulos_informativos_2024": 0,
    "referencias_sumulas_stf_stj": 0,
}

for q in dados:
    fonte = limpar(q.get("fonte"))
    modulo = limpar(q.get("modulo"))
    qid = limpar(q.get("id"))

    # 1) Corrigir módulos genéricos dos informativos antigos de 2024
    if fonte.startswith("Info "):
        partes = fonte.split()
        if len(partes) >= 3 and partes[1].isdigit():
            num = int(partes[1])
            tribunal = partes[2]

            if tribunal == "STF" and 1121 <= num <= 1161:
                if q.get("ano") != 2024 or q.get("modulo") != "Informativos STF 2024":
                    q["ano"] = 2024
                    q["modulo"] = "Informativos STF 2024"
                    ajustes_finais["modulos_informativos_2024"] += 1

            if tribunal == "STJ" and num in [833, 834]:
                if q.get("ano") != 2024 or q.get("modulo") != "Informativos STJ 2024":
                    q["ano"] = 2024
                    q["modulo"] = "Informativos STJ 2024"
                    ajustes_finais["modulos_informativos_2024"] += 1

    # 2) Corrigir referência das Súmulas STF/STJ sem tocar nas vinculantes
    if modulo == "Súmulas STF":
        m = re.search(r"-q(\d+)$", qid)
        if m:
            ref_correta = f"Súmula {int(m.group(1))} STF"
            if q.get("referencia") != ref_correta:
                q["referencia"] = ref_correta
                ajustes_finais["referencias_sumulas_stf_stj"] += 1

    elif modulo == "Súmulas STJ":
        m = re.search(r"-q(\d+)$", qid)
        if m:
            ref_correta = f"Súmula {int(m.group(1))} STJ"
            if q.get("referencia") != ref_correta:
                q["referencia"] = ref_correta
                ajustes_finais["referencias_sumulas_stf_stj"] += 1

# Ano majoritário inteligente por referência dos informativos
ajustes_finais["ano_majoritario_informativos"] = aplicar_ano_majoritario_informativos(dados)
# ============================================================
# PADRONIZAÇÃO FINAL DE MÓDULOS RG / REPETITIVOS
# ============================================================

ajustes_finais["modulos_rg_repetitivos"] = 0

trocas_modulos = {
    "Repetitivo - Tributário": "Repetitivo - Tributário",
    "RG - Tributário": "RG - Tributário",
    "Repetitivo Ambiental": "Repetitivo - Ambiental",
    "Repercussão Geral": "RG - Geral",
}

mapa_area = {
    "Direito Administrativo": "Administrativo",
    "Direito Ambiental": "Ambiental",
    "Direito Civil": "Civil",
    "Direito do Consumidor": "Consumidor",
    "Direito Consumidor": "Consumidor",
    "Direito Empresarial": "Empresarial",
    "Direito Penal": "Penal",
    "Direito Processual Civil": "Processo Civil",
    "Direito Processual Penal": "Processo Penal",
    "Direito Tributário": "Tributário",
    "Direito Eleitoral": "Eleitoral",
    "Direito Constitucional": "Constitucional",
}

for q in dados:
    categoria = q.get("categoria")
    modulo = q.get("modulo", "")
    disciplina = q.get("disciplina", "")
    area = mapa_area.get(disciplina, "")

    # 1) Corrige nomes antigos/inconsistentes
    if modulo in trocas_modulos:
        q["modulo"] = trocas_modulos[modulo]
        ajustes_finais["modulos_rg_repetitivos"] += 1
        modulo = q["modulo"]

    # 2) Impede RG/Repetitivo dentro de Informativos
    if categoria == "Repercussão Geral" and "Informativos" in modulo:
        q["modulo"] = f"RG - {area}" if area else "RG - Geral"
        ajustes_finais["modulos_rg_repetitivos"] += 1

    elif categoria == "Repetitivos" and "Informativos" in modulo:
        q["modulo"] = f"Repetitivo - {area}" if area else "Repetitivos"
        ajustes_finais["modulos_rg_repetitivos"] += 1

    # 3) Corrige genéricos
    elif categoria == "Repercussão Geral" and modulo == "Repercussão Geral":
        q["modulo"] = "RG - Geral"
        ajustes_finais["modulos_rg_repetitivos"] += 1

    elif categoria == "Repetitivos" and modulo == "Repetitivos" and area:
        q["modulo"] = f"Repetitivo - {area}"
        ajustes_finais["modulos_rg_repetitivos"] += 1
JSON_PATH.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
HTML_JSON_PATH.write_text(JSON_PATH.read_text(encoding="utf-8"), encoding="utf-8")

print("✅ Normalização concluída.")
print("Backup:", backup)

print("\nAlterações:")
for k, v in alterados.items():
    print(f"- {k}: {v}")

print("\nAjustes finais:")
for k, v in ajustes_finais.items():
    print(f"- {k}: {v}")
