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

IGNORAR_NOMES = [
    "limpa_padrao",
    "corrigida",
    "extracao",
    "relatorio",
    "auditoria",
    "controle_",
    "backup",
    "dry-run",
    "dry_run",
]

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalizar_texto(txt: str) -> str:
    txt = unicodedata.normalize("NFD", txt or "")
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    return txt.lower()


def limpar_campo(txt: str) -> str:
    if not txt:
        return ""

    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = re.sub(r"<!--.*?-->", "", txt, flags=re.DOTALL)

    # Limpezas específicas de resíduos de teste
    txt = txt.replace("[DRY-RUN]", "")
    txt = txt.replace("[DRY RUN]", "")
    txt = txt.replace("Questão simulada.", "")
    txt = txt.replace("Justificativa simulada.", "")

    txt = re.sub(r"\n{3,}", "\n\n", txt)
    txt = re.sub(r"[ \t]+", " ", txt)

    return txt.strip()


def contem_dry_run(txt: str) -> bool:
    n = normalizar_texto(txt)
    return "dry-run" in n or "dry run" in n or "questao simulada" in n or "justificativa simulada" in n


def slug(txt: str) -> str:
    txt = normalizar_texto(txt)
    txt = re.sub(r"[^a-z0-9]+", "-", txt)
    return txt.strip("-")


def deve_ignorar(path: Path) -> bool:
    nome = normalizar_texto(path.name)
    return any(p in nome for p in IGNORAR_NOMES)


# ============================================================
# IDENTIFICAÇÃO DE METADADOS
# ============================================================

def identificar_metadados(nome_arquivo: str) -> dict:
    nome_original = nome_arquivo
    nome = normalizar_texto(nome_arquivo)

    tribunal = ""
    ano = None
    tipo = "informativo"
    categoria = "Informativos"
    informativo = ""
    modulo = "Módulo não identificado"

    if "stf" in nome:
        tribunal = "STF"
    elif "stj" in nome:
        tribunal = "STJ"

    # Súmulas
    if "sumula" in nome or "súmula" in nome:
        tipo = "sumula"
        categoria = "Súmulas"

        if "vinculante" in nome:
            tribunal = "STF"
            modulo = "Súmulas Vinculantes STF"
        elif "stf" in nome:
            tribunal = "STF"
            modulo = "Súmulas STF"
        elif "stj" in nome:
            tribunal = "STJ"
            modulo = "Súmulas STJ"
        else:
            modulo = "Súmulas"

        return {
            "tribunal": tribunal,
            "ano": ano,
            "tipo": tipo,
            "categoria": categoria,
            "informativo": "",
            "modulo": modulo,
            "fonte": nome_original.replace(".md", ""),
        }

    # Repercussão Geral
    if nome.startswith("rg") or "rg -" in nome:
        tipo = "repercussao_geral"
        categoria = "Repercussão Geral"
        tribunal = "STF"
        modulo = nome_original.replace(".md", "")
        return {
            "tribunal": tribunal,
            "ano": ano,
            "tipo": tipo,
            "categoria": categoria,
            "informativo": "",
            "modulo": modulo,
            "fonte": modulo,
        }

    # Repetitivos
    if "repetitivo" in nome:
        tipo = "repetitivo"
        categoria = "Repetitivos"
        tribunal = "STJ"
        modulo = nome_original.replace(".md", "")
        return {
            "tribunal": tribunal,
            "ano": ano,
            "tipo": tipo,
            "categoria": categoria,
            "informativo": "",
            "modulo": modulo,
            "fonte": modulo,
        }

    numeros = re.findall(r"\b\d{2,4}\b", nome)
    numero = numeros[0] if numeros else ""

    if numero:
        informativo = numero

    # Ed. Extraordinária STJ: no seu projeto, Infos 22 a 30 são extras.
    if tribunal == "STJ" and informativo:
        n = int(informativo)
        if 22 <= n <= 30:
            tipo = "edicao_extraordinaria"
            categoria = "Edição Extraordinária"
            if 22 <= n <= 27:
                ano = 2025
                modulo = "STJ Edição Extraordinária 2025"
            else:
                ano = 2026
                modulo = "STJ Edição Extraordinária 2026"

            return {
                "tribunal": tribunal,
                "ano": ano,
                "tipo": tipo,
                "categoria": categoria,
                "informativo": informativo,
                "modulo": modulo,
                "fonte": f"Info Extra {informativo} STJ",
            }

    if tribunal == "STF" and informativo:
        n = int(informativo)
        if 1162 <= n <= 1202:
            ano = 2025
            modulo = "Informativos STF 2025"
        elif n > 1202:
            ano = 2026
            modulo = "Informativos STF 2026"
        else:
            modulo = "Informativos STF"

    elif tribunal == "STJ" and informativo:
        n = int(informativo)
        if 835 <= n <= 874:
            ano = 2025
            modulo = "Informativos STJ 2025"
        elif n >= 875:
            ano = 2026
            modulo = "Informativos STJ 2026"
        else:
            modulo = "Informativos STJ"

    fonte = f"Info {informativo} {tribunal}" if tribunal and informativo else nome_original.replace(".md", "")

    return {
        "tribunal": tribunal,
        "ano": ano,
        "tipo": tipo,
        "categoria": categoria,
        "informativo": informativo,
        "modulo": modulo,
        "fonte": fonte,
    }


# ============================================================
# EXTRAÇÃO DOS CAMPOS DAS QUESTÕES
# ============================================================

def dividir_blocos_questoes(conteudo: str) -> list[str]:
    padrao = r"(?=^\s*#{1,6}\s*Quest[aã]o\s+\d+)"
    blocos = re.split(padrao, conteudo, flags=re.IGNORECASE | re.MULTILINE)
    return [
        b.strip()
        for b in blocos
        if re.search(r"^\s*#{1,6}\s*Quest[aã]o\s+\d+", b, re.IGNORECASE | re.MULTILINE)
    ]


def extrair_numero_questao(bloco: str, fallback: int) -> int:
    m = re.search(r"Quest[aã]o\s+(\d+)", bloco, flags=re.IGNORECASE)
    return int(m.group(1)) if m else fallback


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
        return "REVISAR"
    if "errado" in bruto_norm:
        return "E"
    if "certo" in bruto_norm:
        return "C"

    m = re.search(
        r"\b(gabarito|resposta)\s*:\s*(certo|errado|c|e)\b",
        bloco,
        flags=re.IGNORECASE,
    )
    if m:
        valor = normalizar_texto(m.group(2))
        if valor in ["e", "errado"]:
            return "E"
        if valor in ["c", "certo"]:
            return "C"

    return ""


def extrair_enunciado(bloco: str) -> str:
    enunciado = extrair_campo(bloco, ["Enunciado", "Questão", "Questao", "Item"])

    if enunciado:
        return enunciado

    bloco_sem_titulo = re.sub(
        r"^\s*#{1,6}\s*Quest[aã]o\s+\d+\s*",
        "",
        bloco,
        flags=re.IGNORECASE,
    )

    antes_gabarito = re.split(
        r"\*\*\s*(Gabarito|Resposta|Resposta correta|Gabarito correto)\s*:\s*\*\*",
        bloco_sem_titulo,
        flags=re.IGNORECASE,
    )[0]

    return limpar_campo(antes_gabarito)


def extrair_justificativa_robusta(bloco: str) -> str:
    """
    Captura a justificativa dos arquivos novos e antigos.

    Estratégia:
    1. Tenta capturar o campo **Justificativa:** até Referência/Fonte/nova questão/fim.
    2. Se falhar, captura tudo depois do gabarito.
    3. Remove referência seca, comentários HTML e resíduos de DRY-RUN.
    """

    padroes = [
        r"\*\*\s*Justificativa\s*:\s*\*\*\s*(.*?)(?=\n\s*\*\*\s*Refer[eê]ncia\s*:\s*\*\*|\n\s*\*\*\s*Fonte\s*:\s*\*\*|\n\s*#{1,6}\s*Quest[aã]o\s+\d+|\n\s*---\s*$|\Z)",
        r"\*\*\s*Explica[cç][aã]o\s*:\s*\*\*\s*(.*?)(?=\n\s*\*\*\s*Refer[eê]ncia\s*:\s*\*\*|\n\s*\*\*\s*Fonte\s*:\s*\*\*|\n\s*#{1,6}\s*Quest[aã]o\s+\d+|\n\s*---\s*$|\Z)",
        r"\*\*\s*Coment[aá]rio\s*:\s*\*\*\s*(.*?)(?=\n\s*\*\*\s*Refer[eê]ncia\s*:\s*\*\*|\n\s*\*\*\s*Fonte\s*:\s*\*\*|\n\s*#{1,6}\s*Quest[aã]o\s+\d+|\n\s*---\s*$|\Z)",
    ]

    for padrao in padroes:
        m = re.search(padrao, bloco, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE)
        if m:
            texto = limpar_campo(m.group(1))
            if texto:
                return texto

    # Fallback forte: tudo depois do gabarito até referência/fim.
    m = re.search(
        r"\*\*\s*(?:Gabarito|Resposta|Resposta correta|Gabarito correto)\s*:\s*\*\*\s*(?:CERTO|ERRADO|C|E|REVISAR MANUALMENTE)?\s*(.*?)(?=\n\s*\*\*\s*Refer[eê]ncia\s*:\s*\*\*|\n\s*\*\*\s*Fonte\s*:\s*\*\*|\n\s*#{1,6}\s*Quest[aã]o\s+\d+|\n\s*---\s*$|\Z)",
        bloco,
        flags=re.IGNORECASE | re.DOTALL | re.MULTILINE,
    )
    if m:
        texto = limpar_campo(m.group(1))
        texto = re.sub(r"^\*\*\s*Justificativa\s*:\s*\*\*", "", texto, flags=re.IGNORECASE).strip()
        texto = re.sub(r"^\*\*\s*Explica[cç][aã]o\s*:\s*\*\*", "", texto, flags=re.IGNORECASE).strip()
        if texto:
            return limpar_campo(texto)

    return ""


def extrair_referencia(bloco: str) -> str:
    return extrair_campo(bloco, ["Referência", "Referencia", "Fonte"])


# ============================================================
# PROCESSAMENTO PRINCIPAL
# ============================================================

def processar_arquivo(caminho: Path) -> tuple[list[dict], list[str]]:
    conteudo = caminho.read_text(encoding="utf-8", errors="ignore")
    metadados = identificar_metadados(caminho.name)
    blocos = dividir_blocos_questoes(conteudo)

    questoes = []
    alertas = []

    if contem_dry_run(conteudo):
        alertas.append(f"[ARQUIVO COM DRY-RUN] {caminho.name}")

    if not blocos:
        alertas.append(f"[SEM QUESTÕES] {caminho.name}")
        return questoes, alertas

    for i, bloco in enumerate(blocos, start=1):
        numero_questao = extrair_numero_questao(bloco, i)

        disciplina = extrair_campo(bloco, ["Disciplina", "Matéria", "Materia"])
        tema = extrair_campo(bloco, ["Tema", "Subtema", "Assunto"])
        enunciado = extrair_enunciado(bloco)
        resposta = extrair_gabarito(bloco)
        explicacao = extrair_justificativa_robusta(bloco)
        referencia = extrair_referencia(bloco)

        if not enunciado:
            alertas.append(f"[SEM ENUNCIADO] {caminho.name} | Questão {numero_questao}")
        if not resposta:
            alertas.append(f"[SEM GABARITO] {caminho.name} | Questão {numero_questao}")
        if not explicacao:
            alertas.append(f"[SEM EXPLICAÇÃO] {caminho.name} | Questão {numero_questao}")
        if contem_dry_run(bloco):
            alertas.append(f"[QUESTÃO COM DRY-RUN] {caminho.name} | Questão {numero_questao}")

        tribunal_slug = slug(metadados["tribunal"] or "sem-tribunal")
        tipo_slug = "extra" if metadados["tipo"] == "edicao_extraordinaria" else slug(metadados["tipo"])
        ano_slug = str(metadados["ano"] or "sem-ano")
        info_slug = metadados["informativo"] or slug(metadados["modulo"])

        id_questao = f"{tribunal_slug}-{ano_slug}-{tipo_slug}-{info_slug}-q{i:03d}"

        tags = [
            x
            for x in [
                metadados["tribunal"],
                metadados["categoria"],
                metadados["modulo"],
                disciplina,
                tema,
                metadados["fonte"],
            ]
            if x
        ]

        questoes.append(
            {
                "id": id_questao,
                "modulo": metadados["modulo"],
                "tribunal": metadados["tribunal"],
                "ano": metadados["ano"],
                "tipo": metadados["tipo"],
                "categoria": metadados["categoria"],
                "informativo": metadados["informativo"],
                "disciplina": disciplina,
                "tema": tema,
                "enunciado": enunciado,
                "respostaCorreta": resposta,
                "explicacao": explicacao,
                "referencia": referencia,
                "fonte": metadados["fonte"],
                "nivel": "medio",
                "tags": tags,
            }
        )

    return questoes, alertas


def main():
    PASTA_SAIDA.mkdir(exist_ok=True)

    if not PASTA_ENTRADA.exists():
        print(f"❌ Pasta não encontrada: {PASTA_ENTRADA}")
        return

    arquivos_md = [p for p in sorted(PASTA_ENTRADA.glob("*.md")) if not deve_ignorar(p)]

    todas_questoes = []
    todos_alertas = []

    print("\n🔎 Iniciando leitura dos arquivos .md...\n")

    for arquivo in arquivos_md:
        questoes, alertas = processar_arquivo(arquivo)
        todas_questoes.extend(questoes)
        todos_alertas.extend(alertas)
        print(f"📄 {arquivo.name}: {len(questoes)} questão(ões) extraída(s)")

    ids = [q["id"] for q in todas_questoes]
    ids_duplicados = sorted([k for k, v in Counter(ids).items() if v > 1])
    for id_dup in ids_duplicados:
        todos_alertas.append(f"[ID DUPLICADO] {id_dup}")

    sem_questoes = [a for a in todos_alertas if a.startswith("[SEM QUESTÕES]")]
    sem_gabarito = [a for a in todos_alertas if a.startswith("[SEM GABARITO]")]
    sem_enunciado = [a for a in todos_alertas if a.startswith("[SEM ENUNCIADO]")]
    sem_explicacao = [a for a in todos_alertas if a.startswith("[SEM EXPLICAÇÃO]")]
    dry_run = [a for a in todos_alertas if "DRY-RUN" in a]
    revisar = [q for q in todas_questoes if q["respostaCorreta"] == "REVISAR"]

    with ARQUIVO_JSON.open("w", encoding="utf-8") as f:
        json.dump(todas_questoes, f, ensure_ascii=False, indent=2)

    por_categoria = Counter(q["categoria"] for q in todas_questoes)
    por_modulo = Counter(q["modulo"] for q in todas_questoes)

    resumo = {
        "geradoEm": datetime.now().isoformat(),
        "totalArquivos": len(arquivos_md),
        "totalQuestoes": len(todas_questoes),
        "revisarManualmente": len(revisar),
        "arquivosSemQuestoes": len(sem_questoes),
        "questoesSemGabarito": len(sem_gabarito),
        "questoesSemEnunciado": len(sem_enunciado),
        "questoesSemExplicacao": len(sem_explicacao),
        "alertasDryRun": len(dry_run),
        "idsDuplicados": len(ids_duplicados),
        "porCategoria": dict(sorted(por_categoria.items())),
        "porModulo": dict(sorted(por_modulo.items())),
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
    auditoria.append(f"Questões sem explicação: {len(sem_explicacao)}")
    auditoria.append(f"Alertas de DRY-RUN: {len(dry_run)}")
    auditoria.append(f"IDs duplicados: {len(ids_duplicados)}")
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

    if todos_alertas:
        auditoria.extend(todos_alertas)
    else:
        auditoria.append("Nenhum alerta encontrado.")

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
    print(f"- Questões sem explicação: {len(sem_explicacao)}")
    print(f"- Alertas de DRY-RUN: {len(dry_run)}")
    print(f"- IDs duplicados: {len(ids_duplicados)}")

    if todos_alertas:
        print("\n⚠️ Há alertas. Veja:")
        print(f"   {ARQUIVO_AUDITORIA}")


if __name__ == "__main__":
    main()
