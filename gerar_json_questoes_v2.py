from pathlib import Path
import re
import json
import unicodedata
from datetime import datetime
from collections import Counter

# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA_ENTRADA = Path("questoes_validadas_pdf")
PASTA_SAIDA = Path("data")
ARQUIVO_JSON = PASTA_SAIDA / "questoes.json"
ARQUIVO_AUDITORIA = PASTA_SAIDA / "auditoria_json.txt"
ARQUIVO_RESUMO = PASTA_SAIDA / "resumo_json.json"

# Arquivos intermediários que NÃO devem virar banco final
IGNORAR_PADROES = [
    "limpa_padrao",
    "corrigida",
    "extracao",
    "relatorio",
    "controle",
]

# Se True, questões com "REVISAR MANUALMENTE" entram no JSON, mas marcadas como revisarManualmente=True
MANTER_REVISAO_MANUAL = True


def normalizar_texto(txt: str) -> str:
    if not txt:
        return ""
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    return txt.lower()


def limpar_campo(txt: str) -> str:
    if not txt:
        return ""
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = re.sub(r"<!--.*?-->", "", txt, flags=re.DOTALL)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    txt = re.sub(r"[ \t]+", " ", txt)
    return txt.strip()


def slug(txt: str) -> str:
    txt = normalizar_texto(txt or "")
    txt = re.sub(r"[^a-z0-9]+", "-", txt)
    return txt.strip("-")


def deve_ignorar_arquivo(caminho: Path) -> bool:
    nome = normalizar_texto(caminho.name)
    return any(p in nome for p in IGNORAR_PADROES)


def primeiro_numero(nome: str) -> str:
    m = re.search(r"\b(\d{1,4})\b", nome)
    return m.group(1) if m else ""


def identificar_metadados(nome_arquivo: str) -> dict:
    nome_original = nome_arquivo
    stem = nome_original.replace(".md", "")
    nome = normalizar_texto(nome_arquivo)

    tribunal = ""
    ano = None
    tipo = "informativo"
    informativo = ""
    modulo = "Módulo não identificado"
    categoria = "Outros"
    fonte = stem

    # Súmulas
    if "sumula" in nome or "súmula" in nome:
        tipo = "sumula"
        categoria = "Súmulas"

        if "vinculante" in nome:
            tribunal = "STF"
            modulo = "Súmulas Vinculantes STF"
            fonte = "Súmulas Vinculantes STF"
        elif "stf" in nome:
            tribunal = "STF"
            modulo = "Súmulas STF"
            fonte = "Súmulas STF"
        elif "stj" in nome:
            tribunal = "STJ"
            modulo = "Súmulas STJ"
            fonte = "Súmulas STJ"
        else:
            modulo = "Súmulas"

        return {"tribunal": tribunal, "ano": ano, "tipo": tipo, "informativo": "", "modulo": modulo, "fonte": fonte, "categoria": categoria}

    # Repercussão Geral
    if nome.startswith("rg ") or nome.startswith("rg-") or "repercussao" in nome:
        tipo = "repercussao_geral"
        tribunal = "STF"
        categoria = "Repercussão Geral"
        area = re.sub(r"^rg\s*[-_]*\s*", "", stem, flags=re.IGNORECASE).strip()
        modulo = f"RG - {area}" if area else "Repercussão Geral STF"
        fonte = modulo
        return {"tribunal": tribunal, "ano": ano, "tipo": tipo, "informativo": "", "modulo": modulo, "fonte": fonte, "categoria": categoria}

    # Repetitivos
    if "repetitivo" in nome:
        tipo = "repetitivo"
        tribunal = "STJ"
        categoria = "Repetitivos"
        modulo = stem
        fonte = stem
        return {"tribunal": tribunal, "ano": ano, "tipo": tipo, "informativo": "", "modulo": modulo, "fonte": fonte, "categoria": categoria}

    # Informativos STF/STJ
    if "stf" in nome:
        tribunal = "STF"
    elif "stj" in nome:
        tribunal = "STJ"

    numero = primeiro_numero(nome)
    if numero:
        informativo = numero

    if tribunal == "STF" and informativo:
        n = int(informativo)
        categoria = "Informativos"
        if 1162 <= n <= 1202:
            ano = 2025
            modulo = "Informativos STF 2025"
        elif n > 1202:
            ano = 2026
            modulo = "Informativos STF 2026"
        else:
            modulo = "Informativos STF"
        fonte = f"Info {informativo} STF"

    elif tribunal == "STJ" and informativo:
        n = int(informativo)
        categoria = "Informativos"
        # Regra do projeto: Info 22 a 30 STJ são edições extraordinárias
        if 22 <= n <= 30:
            tipo = "edicao_extraordinaria"
            categoria = "Edição Extraordinária"
            if 22 <= n <= 27:
                ano = 2025
                modulo = "STJ Edição Extraordinária 2025"
            else:
                ano = 2026
                modulo = "STJ Edição Extraordinária 2026"
            fonte = f"Info Extra {informativo} STJ"
        else:
            if 835 <= n <= 874:
                ano = 2025
                modulo = "Informativos STJ 2025"
            elif n >= 875:
                ano = 2026
                modulo = "Informativos STJ 2026"
            else:
                modulo = "Informativos STJ"
            fonte = f"Info {informativo} STJ"

    return {"tribunal": tribunal, "ano": ano, "tipo": tipo, "informativo": informativo, "modulo": modulo, "fonte": fonte, "categoria": categoria}


def extrair_campo(bloco: str, nomes: list[str]) -> str:
    nomes_regex = "|".join(re.escape(n) for n in nomes)
    padrao = rf"""
        \*\*\s*(?:{nomes_regex})\s*:\s*\*\*
        \s*
        (.*?)
        (?=
            \n\s*\*\*[^*\n]+:\s*\*\*
            |
            \n\s*#{1,6}\s+
            |
            \n\s*---
            |
            \Z
        )
    """
    m = re.search(padrao, bloco, flags=re.IGNORECASE | re.DOTALL | re.VERBOSE)
    return limpar_campo(m.group(1)) if m else ""


def extrair_gabarito(bloco: str) -> str:
    bruto = extrair_campo(bloco, ["Gabarito", "Resposta", "Resposta correta", "Gabarito correto"])
    bruto_norm = normalizar_texto(bruto)

    if "revisar manualmente" in bruto_norm:
        return "R"
    if "errado" in bruto_norm:
        return "E"
    if "certo" in bruto_norm:
        return "C"

    m = re.search(r"\b(gabarito|resposta)\s*:\s*(certo|errado|c|e)\b", bloco, flags=re.IGNORECASE)
    if m:
        valor = normalizar_texto(m.group(2))
        if valor in ["e", "errado"]:
            return "E"
        if valor in ["c", "certo"]:
            return "C"
    return ""


def dividir_blocos_questoes(conteudo: str) -> list[str]:
    padrao = r"(?=^\s*#{0,6}\s*Quest[aã]o\s+\d+\b)"
    blocos = re.split(padrao, conteudo, flags=re.IGNORECASE | re.MULTILINE)
    return [b.strip() for b in blocos if re.search(r"^\s*#{0,6}\s*Quest[aã]o\s+\d+\b", b, re.IGNORECASE | re.MULTILINE)]


def extrair_numero_questao(bloco: str, fallback: int) -> int:
    m = re.search(r"Quest[aã]o\s+(\d+)", bloco, flags=re.IGNORECASE)
    return int(m.group(1)) if m else fallback


def extrair_referencia(bloco: str) -> str:
    return extrair_campo(bloco, ["Referência", "Referencia", "Fonte"])


def extrair_enunciado_fallback(bloco: str) -> str:
    bloco_sem_titulo = re.sub(r"^\s*#{0,6}\s*Quest[aã]o\s+\d+\s*", "", bloco.strip(), flags=re.IGNORECASE)
    antes_gabarito = re.split(r"\n\s*\*\*\s*(Gabarito|Resposta|Resposta correta|Gabarito correto)\s*:\s*\*\*", bloco_sem_titulo, flags=re.IGNORECASE)[0]
    return limpar_campo(antes_gabarito)


def processar_arquivo(caminho: Path) -> tuple[list[dict], list[str]]:
    conteudo = caminho.read_text(encoding="utf-8", errors="ignore")
    metadados = identificar_metadados(caminho.name)
    blocos = dividir_blocos_questoes(conteudo)
    questoes = []
    alertas = []

    if not blocos:
        alertas.append(f"[SEM QUESTÕES] {caminho.name}")
        return questoes, alertas

    contador = 0
    arquivo_slug = slug(caminho.stem)

    for i, bloco in enumerate(blocos, start=1):
        numero_questao = extrair_numero_questao(bloco, i)
        disciplina = extrair_campo(bloco, ["Disciplina", "Matéria", "Materia"])
        tema = extrair_campo(bloco, ["Tema", "Subtema", "Assunto"])
        enunciado = extrair_campo(bloco, ["Enunciado", "Questão", "Questao", "Item"])
        explicacao = extrair_campo(bloco, ["Justificativa", "Explicação", "Explicacao", "Comentário", "Comentario"])
        referencia = extrair_referencia(bloco)
        resposta = extrair_gabarito(bloco)

        if not enunciado:
            enunciado = extrair_enunciado_fallback(bloco)

        enunciado = limpar_campo(enunciado)
        explicacao = limpar_campo(explicacao)
        revisar_manualmente = resposta == "R"

        if revisar_manualmente and not MANTER_REVISAO_MANUAL:
            continue

        contador += 1

        if not disciplina:
            if metadados["tipo"] == "sumula":
                disciplina = "Súmulas"
            elif metadados["tipo"] == "repercussao_geral":
                disciplina = "Repercussão Geral"
            elif metadados["tipo"] == "repetitivo":
                disciplina = "Repetitivos"

        if not resposta:
            alertas.append(f"[SEM GABARITO] {caminho.name} | Questão {numero_questao}")
        if not enunciado:
            alertas.append(f"[SEM ENUNCIADO] {caminho.name} | Questão {numero_questao}")

        tribunal_slug = slug(metadados["tribunal"] or "sem-tribunal")
        tipo_slug = "extra" if metadados["tipo"] == "edicao_extraordinaria" else metadados["tipo"]
        ano_slug = str(metadados["ano"] or "geral")
        info_slug = metadados["informativo"] or slug(metadados["modulo"] or arquivo_slug)
        id_questao = f"{tribunal_slug}-{ano_slug}-{tipo_slug}-{info_slug}-{arquivo_slug}-q{contador:04d}"

        tags = []
        for valor in [metadados["tribunal"], metadados["categoria"], metadados["modulo"], disciplina, tema, metadados["fonte"], referencia]:
            if valor and valor not in tags:
                tags.append(valor)

        questoes.append({
            "id": id_questao,
            "modulo": metadados["modulo"],
            "categoria": metadados["categoria"],
            "tribunal": metadados["tribunal"],
            "ano": metadados["ano"],
            "tipo": metadados["tipo"],
            "informativo": metadados["informativo"],
            "disciplina": disciplina,
            "tema": tema,
            "enunciado": enunciado,
            "respostaCorreta": resposta,
            "explicacao": explicacao,
            "fonte": referencia or metadados["fonte"],
            "arquivoOrigem": caminho.name,
            "numeroQuestaoOrigem": numero_questao,
            "nivel": "medio",
            "revisarManualmente": revisar_manualmente,
            "tags": tags,
        })

    return questoes, alertas


def main():
    PASTA_SAIDA.mkdir(exist_ok=True)

    if not PASTA_ENTRADA.exists():
        print(f"❌ Pasta não encontrada: {PASTA_ENTRADA}")
        return

    arquivos_md = sorted([p for p in PASTA_ENTRADA.glob("*.md") if not deve_ignorar_arquivo(p)])
    todas_questoes = []
    todos_alertas = []

    print("\n🔎 Iniciando leitura dos arquivos .md...\n")
    for arquivo in arquivos_md:
        questoes, alertas = processar_arquivo(arquivo)
        todas_questoes.extend(questoes)
        todos_alertas.extend(alertas)
        print(f"📄 {arquivo.name}: {len(questoes)} questão(ões) extraída(s)")

    ids = [q["id"] for q in todas_questoes]
    duplicados = [id_ for id_, qtd in Counter(ids).items() if qtd > 1]
    for id_ in duplicados:
        todos_alertas.append(f"[ID DUPLICADO] {id_}")

    with ARQUIVO_JSON.open("w", encoding="utf-8") as f:
        json.dump(todas_questoes, f, ensure_ascii=False, indent=2)

    por_modulo = Counter(q["modulo"] for q in todas_questoes)
    por_categoria = Counter(q["categoria"] for q in todas_questoes)
    por_tribunal = Counter(q["tribunal"] or "Sem tribunal" for q in todas_questoes)
    por_tipo = Counter(q["tipo"] for q in todas_questoes)

    sem_questoes = [a for a in todos_alertas if a.startswith("[SEM QUESTÕES]")]
    sem_gabarito = [a for a in todos_alertas if a.startswith("[SEM GABARITO]")]
    sem_enunciado = [a for a in todos_alertas if a.startswith("[SEM ENUNCIADO]")]
    ids_dup = [a for a in todos_alertas if a.startswith("[ID DUPLICADO]")]
    revisar = [q for q in todas_questoes if q.get("revisarManualmente")]

    resumo = {
        "geradoEm": datetime.now().isoformat(),
        "totalArquivosLidos": len(arquivos_md),
        "totalQuestoes": len(todas_questoes),
        "totalRevisarManualmente": len(revisar),
        "porModulo": dict(por_modulo),
        "porCategoria": dict(por_categoria),
        "porTribunal": dict(por_tribunal),
        "porTipo": dict(por_tipo),
        "alertas": {
            "semQuestoes": len(sem_questoes),
            "semGabarito": len(sem_gabarito),
            "semEnunciado": len(sem_enunciado),
            "idsDuplicados": len(ids_dup),
        }
    }
    ARQUIVO_RESUMO.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")

    auditoria = []
    auditoria.append("AUDITORIA DE GERAÇÃO DO JSON")
    auditoria.append(f"Data/hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    auditoria.append("")
    auditoria.append(f"Total de arquivos lidos: {len(arquivos_md)}")
    auditoria.append(f"Total de questões extraídas: {len(todas_questoes)}")
    auditoria.append(f"Questões marcadas para revisão manual: {len(revisar)}")
    auditoria.append(f"Arquivos sem questões detectadas: {len(sem_questoes)}")
    auditoria.append(f"Questões sem gabarito: {len(sem_gabarito)}")
    auditoria.append(f"Questões sem enunciado: {len(sem_enunciado)}")
    auditoria.append(f"IDs duplicados: {len(ids_dup)}")
    auditoria.append("")
    auditoria.append("RESUMO POR CATEGORIA:")
    for k, v in sorted(por_categoria.items()):
        auditoria.append(f"- {k}: {v}")
    auditoria.append("")
    auditoria.append("RESUMO POR MÓDULO:")
    for k, v in sorted(por_modulo.items()):
        auditoria.append(f"- {k}: {v}")
    auditoria.append("")
    auditoria.append("DETALHES DOS ALERTAS:")
    auditoria.append("")
    auditoria.extend(todos_alertas if todos_alertas else ["Nenhum alerta encontrado."])
    ARQUIVO_AUDITORIA.write_text("\n".join(auditoria), encoding="utf-8")

    print("\n✅ JSON gerado com sucesso!")
    print(f"📦 Arquivo: {ARQUIVO_JSON}")
    print(f"🧾 Auditoria: {ARQUIVO_AUDITORIA}")
    print(f"📊 Resumo: {ARQUIVO_RESUMO}")

    print("\n📊 RELATÓRIO FINAL")
    print(f"- Total de arquivos lidos: {len(arquivos_md)}")
    print(f"- Total de questões extraídas: {len(todas_questoes)}")
    print(f"- Revisar manualmente: {len(revisar)}")
    print(f"- Arquivos sem questões: {len(sem_questoes)}")
    print(f"- Questões sem gabarito: {len(sem_gabarito)}")
    print(f"- Questões sem enunciado: {len(sem_enunciado)}")
    print(f"- IDs duplicados: {len(ids_dup)}")

    if sem_questoes or sem_gabarito or sem_enunciado or ids_dup:
        print("\n⚠️ Há alertas. Veja:")
        print(f"   {ARQUIVO_AUDITORIA}")


if __name__ == "__main__":
    main()
