import fitz  # PyMuPDF
import re
from pathlib import Path

PASTA_PDFS = Path("reprocessar_criticos")
PASTA_SAIDA = Path("md_criticos_reprocessados")

PASTA_SAIDA.mkdir(exist_ok=True)


# =========================
# 1. EXTRAIR TEXTO DO PDF
# =========================
def extrair_texto(pdf_path):
    doc = fitz.open(pdf_path)
    texto = ""

    for page in doc:
        texto += page.get_text("text") + "\n"

    return texto


# =========================
# 2. LIMPEZA PESADA
# =========================
def limpar_texto(texto: str) -> str:
    patterns = [
        r"Informativo\s+\d+-STJ.*?\|\s*\d+",
        r"Informativo\s+\d+-STF.*?\|\s*\d+",
        r"Informativo\s+comentado",
        r"Márcio André Lopes Cavalcante",
        r"\bRESUMIDO\b",
        r"\n\s*\d+\s*\n",
        r"[ \t]+",
        r"\n{3,}",
    ]

    for p in patterns:
        texto = re.sub(p, "\n" if "\\n" in p else " ", texto, flags=re.IGNORECASE)

    texto = re.sub(r"\n\s+\n", "\n\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    return texto.strip()


# =========================
# 3. REFERÊNCIAS
# =========================
def padrao_referencia():
    return (
        r"(?:STJ|STF)\.\s*"
        r"(?:"
        r"(?:\d+ª\s+Turma)|"
        r"(?:\d+ª\s+Seção)|"
        r"(?:Corte\s+Especial)|"
        r"(?:Plenário)"
        r")\.\s*"
        r"(?:REsp|Resp|AREsp|AgInt|AgRg|HC|RHC|CC|EREsp|ADI|ADPF|ADO|RE|ARE|MS|RMS|AgInt\s+no|AgRg\s+no|EDcl\s+no)"
        r".{0,350}?"
        r"\(Info\s+\d+(?:\s*-\s*Edição\s+Extraordinária)?\)\."
    )


def extrair_referencias(texto: str):
    refs = re.findall(padrao_referencia(), texto, flags=re.DOTALL | re.IGNORECASE)
    refs_limpas = []

    for ref in refs:
        ref = re.sub(r"\s+", " ", ref).strip()
        refs_limpas.append(ref)

    return refs_limpas

def extrair_referencia_final(julgado: str) -> str:
    refs = extrair_referencias(julgado)
    if not refs:
        return "N/I"
    return "\n".join(refs)


# =========================
# 4. DIVIDIR JULGADOS
# =========================
def dividir_julgados_por_referencia(texto: str):
    matches = list(re.finditer(padrao_referencia(), texto, flags=re.DOTALL | re.IGNORECASE))

    julgados = []
    inicio = 0

    for match in matches:
        fim = match.end()
        bloco = texto[inicio:fim].strip()

        if bloco and len(bloco) > 100:
            julgados.append(bloco)

        inicio = fim

    return julgados


# =========================
# 5. METADADOS
# =========================
DISCIPLINAS = [
    "DIREITO CONSTITUCIONAL",
    "DIREITO ADMINISTRATIVO",
    "DIREITO AMBIENTAL",
    "DIREITO NOTARIAL E REGISTRAL",
    "DIREITO NOTARIAL",
    "DIREITO CIVIL",
    "DIREITO EMPRESARIAL",
    "DIREITO PROCESSUAL CIVIL",
    "DIREITO PROCESSUAL PENAL",
    "DIREITO PENAL",
    "DIREITO TRIBUTÁRIO",
    "DIREITO PREVIDENCIÁRIO",
    "DIREITO DO CONSUMIDOR",
    "DIREITO FINANCEIRO",
    "DIREITO DO TRABALHO",
    "DIREITO ELEITORAL",
    "ECA",
]


def normalizar_titulo(txt: str) -> str:
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:1].upper() + txt[1:] if txt else "N/I"


def extrair_disciplina(julgado: str, disciplina_atual: str = "N/I") -> str:
    linhas = [l.strip() for l in julgado.splitlines() if l.strip()]

    for i, linha in enumerate(linhas[:10]):
        linha_limpa = linha.upper().strip()

        if linha_limpa == "DIREITO NOTARIAL" and i + 1 < len(linhas):
            if linhas[i + 1].upper().strip() == "E REGISTRAL":
                return "Direito Notarial e Registral"

        if linha_limpa in DISCIPLINAS:
            return linha_limpa.title()

    return disciplina_atual


def extrair_ods(julgado: str) -> str:
    match = re.search(r"ODS\s+([0-9,\sEe]+)", julgado, flags=re.IGNORECASE)

    if not match:
        return "N/I"

    ods = re.sub(r"\s+", " ", match.group(1)).strip()
    ods = ods.strip(" ,Ee")

    return ods if ods else "N/I"


def limpar_refs_do_texto(julgado: str) -> str:
    texto = julgado

    refs = extrair_referencias(julgado)
    for ref in refs:
        texto = texto.replace(ref, "")

    texto = re.sub(padrao_referencia(), "", texto, flags=re.DOTALL | re.IGNORECASE)

    return texto.strip()


def remover_ruidos_iniciais(texto: str) -> str:
    texto = re.sub(r"^[:\s]+", "", texto)
    texto = re.sub(r"Informativo\s+\d+-STJ\s*\(\s*\)", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"Informativo\s+\d+-STF\s*\(\s*\)", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def extrair_subtema_titulo_tese(julgado: str):
    texto = limpar_refs_do_texto(julgado)
    texto = remover_ruidos_iniciais(texto)

    linhas = [l.strip() for l in texto.splitlines() if l.strip()]

    if len(linhas) >= 2 and linhas[0].upper() == "DIREITO NOTARIAL" and linhas[1].upper() == "E REGISTRAL":
        linhas = linhas[2:]
    elif linhas and linhas[0].upper() in DISCIPLINAS:
        linhas.pop(0)

    if not linhas:
        return "N/I", "N/I", texto

    subtema = linhas[0]

    titulo_linhas = []
    tese_linhas = []
    encontrou_ods = False

    for linha in linhas[1:]:
        if re.match(r"ODS\s+", linha, flags=re.IGNORECASE):
            encontrou_ods = True
            continue

        if not encontrou_ods:
            titulo_linhas.append(linha)
        else:
            tese_linhas.append(linha)

    titulo = normalizar_titulo(" ".join(titulo_linhas))
    tese = "\n".join(tese_linhas).strip()

    if not tese:
        tese = "\n".join(linhas[1:]).strip()

    return subtema.title(), titulo, tese


def definir_status(disciplina, subtema, titulo, tese, referencia):
    problemas = []

    if disciplina == "N/I":
        problemas.append("disciplina")
    if subtema == "N/I":
        problemas.append("subtema")
    if titulo == "N/I" or len(titulo) < 20:
        problemas.append("título")
    if not tese or len(tese) < 120:
        problemas.append("tese curta")
    if referencia == "N/I":
        problemas.append("referência")

    if not problemas:
        return "Completo", "Nenhuma."

    if len(problemas) <= 2:
        return "Revisão leve", "Verificar: " + ", ".join(problemas) + "."

    return "Revisão crítica", "Verificar: " + ", ".join(problemas) + "."


# =========================
# 6. MONTAR MARKDOWN
# =========================
def montar_md(nome_arquivo, julgados):
    linhas = []

    linhas.append(f"# {nome_arquivo}")
    linhas.append("")
    linhas.append("**Status geral:** Estruturado automaticamente")
    linhas.append("")
    linhas.append("---")
    linhas.append("")

    disciplina_atual = "N/I"

    for i, j in enumerate(julgados, start=1):
        disciplina = extrair_disciplina(j, disciplina_atual)

        if disciplina != "N/I":
            disciplina_atual = disciplina

        subtema, titulo, tese = extrair_subtema_titulo_tese(j)
        ods = extrair_ods(j)
        referencia = extrair_referencia_final(j)

        status, obs = definir_status(disciplina, subtema, titulo, tese, referencia)

        linhas.append(f"## Julgado {i}")
        linhas.append("")
        linhas.append(f"**Disciplina:** {disciplina}")
        linhas.append("")
        linhas.append(f"**Subtema:** {subtema}")
        linhas.append("")
        linhas.append(f"**ODS:** {ods}")
        linhas.append("")
        linhas.append("**Título do julgado:**")
        linhas.append("")
        linhas.append(titulo)
        linhas.append("")
        linhas.append("**Tese / entendimento:**")
        linhas.append("")
        linhas.append(tese)
        linhas.append("")
        linhas.append("**Referência:**")
        linhas.append("")
        linhas.append(referencia)
        linhas.append("")
        linhas.append(f"**Status:** {status}")
        linhas.append("")
        linhas.append("**Observações de saneamento:**")
        linhas.append("")
        linhas.append(obs)
        linhas.append("")
        linhas.append("---")
        linhas.append("")

    return "\n".join(linhas)


# =========================
# 7. PROCESSAR PDF
# =========================
def processar_pdf(pdf_path):
    print(f"\n📄 Processando: {pdf_path.name}")

    texto = extrair_texto(pdf_path)
    texto = limpar_texto(texto)

    julgados = dividir_julgados_por_referencia(texto)

    print(f"➡️ Julgados encontrados: {len(julgados)}")

    nome_saida = pdf_path.stem + "_limpo_estruturado.md"
    caminho_saida = PASTA_SAIDA / nome_saida

    md = montar_md(pdf_path.stem, julgados)

    caminho_saida.write_text(md, encoding="utf-8")

    print(f"✅ Gerado: {caminho_saida}")


# =========================
# 8. EXECUÇÃO
# =========================
def main():
    pdfs = list(PASTA_PDFS.glob("*.pdf"))

    if not pdfs:
        print("❌ Nenhum PDF encontrado na pasta 'pdfs'")
        return

    print(f"📚 PDFs encontrados: {len(pdfs)}")

    for pdf in pdfs:
        processar_pdf(pdf)

    print("\n🎯 ETAPA 2 FINALIZADA")


if __name__ == "__main__":
    main()