from pathlib import Path
import re
import json
import unicodedata
from datetime import datetime
from collections import Counter, defaultdict

PASTA_ENTRADA = Path("questoes_validadas_pdf")
PASTA_SAIDA = Path("data")
ARQUIVO_JSON = PASTA_SAIDA / "questoes.json"
ARQUIVO_AUDITORIA = PASTA_SAIDA / "auditoria_json.txt"
ARQUIVO_RESUMO = PASTA_SAIDA / "resumo_json.json"

IGNORAR_NOMES = [
    "limpa_padrao", "corrigida", "extracao", "relatorio", "auditoria",
    "controle_", "backup", "dry-run", "dry_run"
]

def normalizar_texto(txt: str) -> str:
    txt = unicodedata.normalize("NFD", txt or "")
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    return txt.lower()

def limpar_campo(txt: str) -> str:
    if not txt:
        return ""
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = re.sub(r"<!--.*?-->", "", txt, flags=re.S)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    txt = re.sub(r"[ \t]+", " ", txt)
    return txt.strip()

def slug(txt: str) -> str:
    txt = normalizar_texto(txt)
    txt = re.sub(r"[^a-z0-9]+", "-", txt)
    return txt.strip("-")

def deve_ignorar(path: Path) -> bool:
    n = normalizar_texto(path.name)
    return any(x in n for x in IGNORAR_NOMES)

def identificar_metadados(nome_arquivo: str) -> dict:
    nome_original = nome_arquivo
    nome = normalizar_texto(nome_arquivo)

    tribunal = ""
    ano = None
    tipo = "informativo"
    informativo = ""
    modulo = "Módulo não identificado"
    categoria = "Informativos"

    if "stf" in nome:
        tribunal = "STF"
    elif "stj" in nome:
        tribunal = "STJ"

    # Súmulas
    if "sumula" in nome or "sumulas" in nome or "súmula" in nome or "súmulas" in nome:
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
            "tribunal": tribunal, "ano": ano, "tipo": tipo, "categoria": categoria,
            "informativo": "", "modulo": modulo, "fonte": nome_original.replace(".md","")
        }

    # Repercussão Geral
    if nome.startswith("rg-") or nome.startswith("rg ") or nome.startswith("rg_") or "rg -" in nome:
        tipo = "repercussao_geral"
        categoria = "Repercussão Geral"
        tribunal = "STF"
        modulo = nome_original.replace(".md","")
        return {
            "tribunal": tribunal, "ano": ano, "tipo": tipo, "categoria": categoria,
            "informativo": "", "modulo": modulo, "fonte": modulo
        }

    # Repetitivos
    if "repetitivo" in nome:
        tipo = "repetitivo"
        categoria = "Repetitivos"
        tribunal = "STJ"
        modulo = nome_original.replace(".md","")
        return {
            "tribunal": tribunal, "ano": ano, "tipo": tipo, "categoria": categoria,
            "informativo": "", "modulo": modulo, "fonte": modulo
        }

    numeros = re.findall(r"\b\d{2,4}\b", nome)
    numero = numeros[0] if numeros else ""
    informativo = numero

    # Edição extraordinária STJ: no seu projeto, Info 22 a 30 do STJ são Ed. Extraordinária.
    if tribunal == "STJ" and numero and 22 <= int(numero) <= 30:
        tipo = "edicao_extraordinaria"
        categoria = "Edição Extraordinária"
        n = int(numero)
        if 22 <= n <= 27:
            ano = 2025
            modulo = "STJ Edição Extraordinária 2025"
        else:
            ano = 2026
            modulo = "STJ Edição Extraordinária 2026"
        fonte = f"Info Extra {numero} STJ"
        return {
            "tribunal": tribunal, "ano": ano, "tipo": tipo, "categoria": categoria,
            "informativo": numero, "modulo": modulo, "fonte": fonte
        }

    if tribunal == "STF" and numero:
        n = int(numero)
        if 1162 <= n <= 1202:
            ano = 2025
            modulo = "Informativos STF 2025"
        elif n > 1202:
            ano = 2026
            modulo = "Informativos STF 2026"
        else:
            modulo = "Informativos STF"

    elif tribunal == "STJ" and numero:
        n = int(numero)
        if 835 <= n <= 874:
            ano = 2025
            modulo = "Informativos STJ 2025"
        elif n >= 875:
            ano = 2026
            modulo = "Informativos STJ 2026"
        else:
            modulo = "Informativos STJ"

    fonte = f"Info {numero} {tribunal}" if tribunal and numero else nome_original.replace(".md","")
    return {
        "tribunal": tribunal, "ano": ano, "tipo": tipo, "categoria": categoria,
        "informativo": informativo, "modulo": modulo, "fonte": fonte
    }

def dividir_blocos_questoes(conteudo: str) -> list[str]:
    padrao = r"(?=^\s*#{1,6}\s*Quest[aã]o\s+\d+)"
    blocos = re.split(padrao, conteudo, flags=re.I|re.M)
    return [b.strip() for b in blocos if re.search(r"^\s*#{1,6}\s*Quest[aã]o\s+\d+", b, re.I|re.M)]

def extrair_numero_questao(bloco: str, fallback: int) -> int:
    m = re.search(r"Quest[aã]o\s+(\d+)", bloco, flags=re.I)
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
    m = re.search(padrao, bloco, flags=re.I|re.S|re.X)
    return limpar_campo(m.group(1)) if m else ""

def extrair_justificativa_robusta(bloco: str) -> str:
    # Pega de **Justificativa:** até Referência, Comentário, nova questão ou fim.
    padroes = [
        r"\*\*\s*Justificativa\s*:\s*\*\*\s*(.*?)(?=\n\s*\*\*\s*Refer[eê]ncia\s*:\s*\*\*|\n\s*\*\*\s*Fonte\s*:\s*\*\*|\n\s*#{1,6}\s*Quest[aã]o\s+\d+|\n\s*---\s*$|\Z)",
        r"\*\*\s*Explica[cç][aã]o\s*:\s*\*\*\s*(.*?)(?=\n\s*\*\*\s*Refer[eê]ncia\s*:\s*\*\*|\n\s*\*\*\s*Fonte\s*:\s*\*\*|\n\s*#{1,6}\s*Quest[aã]o\s+\d+|\n\s*---\s*$|\Z)",
        r"\*\*\s*Coment[aá]rio\s*:\s*\*\*\s*(.*?)(?=\n\s*\*\*\s*Refer[eê]ncia\s*:\s*\*\*|\n\s*\*\*\s*Fonte\s*:\s*\*\*|\n\s*#{1,6}\s*Quest[aã]o\s+\d+|\n\s*---\s*$|\Z)",
    ]
    for p in padroes:
        m = re.search(p, bloco, flags=re.I|re.S|re.M)
        if m:
            return limpar_campo(m.group(1))
    return ""

def extrair_gabarito(bloco: str) -> str:
    bruto = extrair_campo(bloco, ["Gabarito", "Resposta", "Resposta correta", "Gabarito correto"])
    bruto_norm = normalizar_texto(bruto)
    if "revisar manualmente" in bruto_norm:
        return "REVISAR"
    if "errado" in bruto_norm:
        return "E"
    if "certo" in bruto_norm:
        return "C"

    m = re.search(r"\b(gabarito|resposta)\s*:\s*(certo|errado|c|e)\b", bloco, flags=re.I)
    if m:
        v = normalizar_texto(m.group(2))
        if v in ["e","errado"]:
            return "E"
        if v in ["c","certo"]:
            return "C"
    return ""

def extrair_enunciado(bloco: str) -> str:
    enunciado = extrair_campo(bloco, ["Enunciado", "Questão", "Questao", "Item"])
    if enunciado:
        return enunciado
    bloco_sem_titulo = re.sub(r"^\s*#{1,6}\s*Quest[aã]o\s+\d+\s*", "", bloco, flags=re.I)
    antes_gabarito = re.split(r"\*\*\s*(Gabarito|Resposta|Resposta correta)\s*:\s*\*\*", bloco_sem_titulo, flags=re.I)[0]
    antes_gabarito = re.sub(r"<!--.*?-->", "", antes_gabarito, flags=re.S)
    return limpar_campo(antes_gabarito)

def processar_arquivo(caminho: Path):
    conteudo = caminho.read_text(encoding="utf-8", errors="ignore")
    metadados = identificar_metadados(caminho.name)
    blocos = dividir_blocos_questoes(conteudo)
    questoes = []
    alertas = []

    if not blocos:
        alertas.append(f"[SEM QUESTÕES] {caminho.name}")
        return questoes, alertas

    for i, bloco in enumerate(blocos, start=1):
        n_questao = extrair_numero_questao(bloco, i)
        disciplina = extrair_campo(bloco, ["Disciplina", "Matéria", "Materia"])
        tema = extrair_campo(bloco, ["Tema", "Subtema", "Assunto"])
        enunciado = extrair_enunciado(bloco)
        resposta = extrair_gabarito(bloco)
        explicacao = extrair_justificativa_robusta(bloco)

        if not resposta:
            alertas.append(f"[SEM GABARITO] {caminho.name} | Questão {n_questao}")
        if not enunciado:
            alertas.append(f"[SEM ENUNCIADO] {caminho.name} | Questão {n_questao}")

        tribunal_slug = slug(metadados["tribunal"] or "sem-tribunal")
        tipo_slug = "extra" if metadados["tipo"] == "edicao_extraordinaria" else slug(metadados["tipo"])
        ano_slug = str(metadados["ano"] or "sem-ano")
        info_slug = metadados["informativo"] or slug(metadados["modulo"])
        id_questao = f"{tribunal_slug}-{ano_slug}-{tipo_slug}-{info_slug}-q{i:03d}"

        tags = [x for x in [
            metadados["tribunal"], metadados["categoria"], metadados["modulo"],
            disciplina, tema, metadados["fonte"]
        ] if x]

        questoes.append({
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
            "fonte": metadados["fonte"],
            "nivel": "medio",
            "tags": tags
        })

    return questoes, alertas

def main():
    PASTA_SAIDA.mkdir(exist_ok=True)
    arquivos_md = [p for p in sorted(PASTA_ENTRADA.glob("*.md")) if not deve_ignorar(p)]

    todas = []
    alertas = []

    print("\n🔎 Iniciando leitura dos arquivos .md...\n")
    for p in arquivos_md:
        qs, al = processar_arquivo(p)
        todas.extend(qs)
        alertas.extend(al)
        print(f"📄 {p.name}: {len(qs)} questão(ões) extraída(s)")

    ids = [q["id"] for q in todas]
    dup = [k for k,v in Counter(ids).items() if v > 1]
    for d in dup:
        alertas.append(f"[ID DUPLICADO] {d}")

    sem_questoes = [a for a in alertas if a.startswith("[SEM QUESTÕES]")]
    sem_gabarito = [a for a in alertas if a.startswith("[SEM GABARITO]")]
    sem_enunciado = [a for a in alertas if a.startswith("[SEM ENUNCIADO]")]
    revisar = [q for q in todas if q["respostaCorreta"] == "REVISAR"]

    ARQUIVO_JSON.write_text(json.dumps(todas, ensure_ascii=False, indent=2), encoding="utf-8")

    por_categoria = Counter(q["categoria"] for q in todas)
    por_modulo = Counter(q["modulo"] for q in todas)

    resumo = {
        "geradoEm": datetime.now().isoformat(),
        "totalArquivos": len(arquivos_md),
        "totalQuestoes": len(todas),
        "revisarManualmente": len(revisar),
        "porCategoria": dict(sorted(por_categoria.items())),
        "porModulo": dict(sorted(por_modulo.items()))
    }
    ARQUIVO_RESUMO.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")

    linhas = []
    linhas.append("AUDITORIA DE GERAÇÃO DO JSON")
    linhas.append(f"Data/hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    linhas.append("")
    linhas.append(f"Total de arquivos lidos: {len(arquivos_md)}")
    linhas.append(f"Total de questões extraídas: {len(todas)}")
    linhas.append(f"Questões marcadas para revisão manual: {len(revisar)}")
    linhas.append(f"Arquivos sem questões detectadas: {len(sem_questoes)}")
    linhas.append(f"Questões sem gabarito: {len(sem_gabarito)}")
    linhas.append(f"Questões sem enunciado: {len(sem_enunciado)}")
    linhas.append(f"IDs duplicados: {len(dup)}")
    linhas.append("")
    linhas.append("RESUMO POR CATEGORIA:")
    for k,v in sorted(por_categoria.items()):
        linhas.append(f"- {k}: {v}")
    linhas.append("")
    linhas.append("RESUMO POR MÓDULO:")
    for k,v in sorted(por_modulo.items()):
        linhas.append(f"- {k}: {v}")
    linhas.append("")
    linhas.append("DETALHES DOS ALERTAS:")
    linhas.append("")
    linhas.extend(alertas if alertas else ["Nenhum alerta encontrado."])

    ARQUIVO_AUDITORIA.write_text("\n".join(linhas), encoding="utf-8")

    print("\n✅ JSON gerado com sucesso!")
    print(f"📦 Arquivo: {ARQUIVO_JSON}")
    print(f"🧾 Auditoria: {ARQUIVO_AUDITORIA}")
    print(f"📊 Resumo: {ARQUIVO_RESUMO}")
    print("\n📊 RELATÓRIO FINAL")
    print(f"- Total de arquivos lidos: {len(arquivos_md)}")
    print(f"- Total de questões extraídas: {len(todas)}")
    print(f"- Revisar manualmente: {len(revisar)}")
    print(f"- Arquivos sem questões: {len(sem_questoes)}")
    print(f"- Questões sem gabarito: {len(sem_gabarito)}")
    print(f"- Questões sem enunciado: {len(sem_enunciado)}")
    print(f"- IDs duplicados: {len(dup)}")

    if alertas:
        print("\n⚠️ Há alertas. Veja:")
        print(f"   {ARQUIVO_AUDITORIA}")

if __name__ == "__main__":
    main()
