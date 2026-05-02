from pathlib import Path
import re
import unicodedata
import fitz

PASTA_PDFS = Path("pdfs")
PASTA_SAIDA = Path("md_criticos_reprocessados")
PASTA_AUDITORIA = Path("auditoria_final")

ESPERADOS = {
    14: 19,
    15: 20,
    16: 17,
    17: 31,
    18: 35,
    19: 21,
    20: 31,
    21: 22,
    24: 19,
}

DISCIPLINAS_VALIDAS = {
    "DIREITO ADMINISTRATIVO",
    "DIREITO ADMINISTRATIVO MILITAR",
    "DIREITO AGRÁRIO",
    "DIREITO AMBIENTAL",
    "DIREITO CIVIL",
    "DIREITO DO CONSUMIDOR",
    "DIREITO EMPRESARIAL",
    "DIREITO FINANCEIRO",
    "DIREITO PREVIDENCIÁRIO",
    "DIREITO PROCESSUAL CIVIL",
    "DIREITO PROCESSUAL PENAL",
    "DIREITO PENAL",
    "DIREITO TRIBUTÁRIO",
    "DIREITO CONSTITUCIONAL",
    "DIREITO ELEITORAL",
    "DIREITO DA CRIANÇA E DO ADOLESCENTE",
}


def normalizar_texto(txt: str) -> str:
    txt = unicodedata.normalize("NFKC", txt)
    txt = txt.replace("\u00a0", " ")
    txt = txt.replace("–", "-").replace("—", "-")
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n\s+\n", "\n\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


def titulo_para_nome(s: str) -> str:
    s = s.strip()
    excecoes = {
        "DO": "do",
        "DA": "da",
        "DE": "de",
        "DOS": "dos",
        "DAS": "das",
        "E": "e",
    }
    partes = []
    for p in s.split():
        partes.append(excecoes.get(p.upper(), p.capitalize()))
    return " ".join(partes)


def extrair_texto_pdf(pdf: Path) -> str:
    doc = fitz.open(pdf)
    partes = []

    for page in doc:
        texto = page.get_text()
        partes.append(texto)

    return normalizar_texto("\n".join(partes))


def limpar_linhas_base(texto: str, num: int):
    linhas = []

    for linha in texto.splitlines():
        l = linha.strip()

        if not l:
            linhas.append("")
            continue

        if re.search(rf"Informativo\s+{num}-STJ.*?\|\s*\d+", l, flags=re.I):
            continue

        if re.search(r"Informativo\s+comentado", l, flags=re.I):
            continue

        if "Márcio André Lopes Cavalcante" in l:
            continue

        if l.upper() in {"RESUMIDO", "INFORMATIVO", "COMENTADO"}:
            continue

        if re.fullmatch(r"ODS\s+\d+(?:\s*E\s*\d+)?", l, flags=re.I):
            continue

        if re.fullmatch(r"Importante!!!", l, flags=re.I):
            continue

        if re.fullmatch(r"\d+", l):
            continue

        linhas.append(l)

    return linhas


def detectar_disciplina(linha: str):
    l = linha.strip().upper()
    l = re.sub(r"\s+", " ", l)

    if l in DISCIPLINAS_VALIDAS:
        return titulo_para_nome(l)

    return None


def eh_referencia_stj(linha: str, num: int):
    return (
        "STJ." in linha
        and re.search(rf"\(Info\s*{num}\s*-\s*Edi[cç][aã]o\s+Extraordin[aá]ria\)", linha, flags=re.I)
    )


def juntar_referencias_quebradas(linhas, num: int):
    """
    Junta referências do STJ que ficaram quebradas em duas ou mais linhas.
    Exemplo:
    STJ. 6ª Turma. AgRg ...
    - Edição Extraordinária).
    """
    novas = []
    i = 0

    while i < len(linhas):
        linha = linhas[i]

        if "STJ." in linha and not eh_referencia_stj(linha, num):
            ref = linha
            j = i + 1

            while j < len(linhas) and j <= i + 4:
                ref_tentativa = ref + " " + linhas[j].strip()

                if eh_referencia_stj(ref_tentativa, num):
                    novas.append(ref_tentativa)
                    i = j + 1
                    break

                ref = ref_tentativa
                j += 1
            else:
                novas.append(linha)
                i += 1
        else:
            novas.append(linha)
            i += 1

    return novas


def limpar_tese(trecho: str, referencia: str, num: int) -> str:
    tese = trecho.replace(referencia, "").strip()

    # Remove cabeçalhos/ruídos que às vezes entram antes do quadro.
    tese = re.sub(rf"Informativo\s+{num}-STJ.*", "", tese, flags=re.I)
    tese = re.sub(r"\bODS\s+\d+(?:\s*E\s*\d+)?", "", tese, flags=re.I)
    tese = re.sub(r"\bImportante!!!\b", "", tese, flags=re.I)

    # Remove linhas que são disciplinas ou parecem subtítulos em caixa alta.
    linhas_limpas = []
    for linha in tese.splitlines():
        l = linha.strip()
        if not l:
            continue

        if detectar_disciplina(l):
            continue

        # descarta subtítulos curtos em caixa alta: CONTRATOS, PROVAS, SENTENÇA etc.
        apenas_letras = re.sub(r"[^A-Za-zÀ-ÿ]", "", l)
        if (
            len(l) <= 80
            and apenas_letras
            and l.upper() == l
            and not l.startswith("STJ.")
        ):
            continue

        linhas_limpas.append(l)

    tese = "\n".join(linhas_limpas).strip()

    # Limpeza final de espaços.
    tese = re.sub(r"\n{3,}", "\n\n", tese)
    tese = re.sub(r"[ \t]+", " ", tese)

    return tese.strip()


def extrair_julgados(num: int, texto: str):
    linhas = limpar_linhas_base(texto, num)
    linhas = juntar_referencias_quebradas(linhas, num)

    disciplina_atual = ""
    buffer = []
    julgados = []

    for linha in linhas:
        disciplina = detectar_disciplina(linha)
        if disciplina:
            disciplina_atual = disciplina
            buffer = []
            continue

        buffer.append(linha)

        if eh_referencia_stj(linha, num):
            referencia = linha.strip()
            trecho = "\n".join(buffer).strip()
            tese = limpar_tese(trecho, referencia, num)

            if tese:
                julgados.append({
                    "disciplina": disciplina_atual,
                    "tese": tese,
                    "referencia": referencia,
                })

            buffer = []

    return julgados


def gerar_md(num: int):
    pdf = PASTA_PDFS / f"Ed. Extra {num} STJ.pdf"
    saida = PASTA_SAIDA / f"Ed. Extra {num} STJ_limpo_estruturado.md"

    if not pdf.exists():
        return {
            "num": num,
            "status": "PDF_NAO_ENCONTRADO",
            "esperado": ESPERADOS[num],
            "encontrado": 0,
            "arquivo": str(pdf),
        }

    texto = extrair_texto_pdf(pdf)
    julgados = extrair_julgados(num, texto)

    partes = [
        f"# Ed. Extra {num} STJ",
        "",
        "**Status geral:** Reestruturado automaticamente - V2",
        f"**Julgados esperados:** {ESPERADOS[num]}",
        f"**Julgados encontrados:** {len(julgados)}",
        "",
    ]

    for i, j in enumerate(julgados, 1):
        partes.append("---")
        partes.append("")
        partes.append(f"## Julgado {i}")
        partes.append("")
        partes.append(f"**Disciplina:** {j['disciplina']}")
        partes.append("")
        partes.append("**Tese / entendimento:**")
        partes.append("")
        partes.append(j["tese"])
        partes.append("")
        partes.append("**Referência:**")
        partes.append(j["referencia"])
        partes.append("")
        partes.append("**Status:** Completo")
        partes.append("")

    PASTA_SAIDA.mkdir(exist_ok=True)
    saida.write_text("\n".join(partes).strip() + "\n", encoding="utf-8")

    status = "OK" if len(julgados) == ESPERADOS[num] else "DIVERGENTE"

    return {
        "num": num,
        "status": status,
        "esperado": ESPERADOS[num],
        "encontrado": len(julgados),
        "arquivo": str(saida),
    }


def main():
    PASTA_AUDITORIA.mkdir(exist_ok=True)

    resultados = []

    print("🚀 Reestruturando Edições Extras STJ - V2")
    print("========================================")

    for num in ESPERADOS:
        r = gerar_md(num)
        resultados.append(r)

        simbolo = "✅" if r["status"] == "OK" else "⚠️"
        print(
            f"{simbolo} Ed. Extra {num} STJ | "
            f"esperado={r['esperado']} | encontrado={r['encontrado']} | {r['status']}"
        )

    relatorio = PASTA_AUDITORIA / "auditoria_ed_extra_stj_reestruturacao_v2.md"

    linhas = [
        "# Auditoria - Reestruturação Ed. Extra STJ - V2",
        "",
        "| Ed. Extra | Esperado | Encontrado | Status | Arquivo |",
        "|---|---:|---:|---|---|",
    ]

    for r in resultados:
        linhas.append(
            f"| {r['num']} | {r['esperado']} | {r['encontrado']} | {r['status']} | {r['arquivo']} |"
        )

    relatorio.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    print("")
    print(f"📄 Relatório: {relatorio}")

    divergentes = [r for r in resultados if r["status"] != "OK"]

    if divergentes:
        print("")
        print("⚠️ ATENÇÃO: ainda há divergências. NÃO gere questões desses arquivos ainda.")
        for r in divergentes:
            print(f"- Ed. Extra {r['num']} STJ: esperado {r['esperado']}, encontrado {r['encontrado']}")
    else:
        print("")
        print("✅ Todos os MDs bateram com a contagem esperada.")


if __name__ == "__main__":
    main()