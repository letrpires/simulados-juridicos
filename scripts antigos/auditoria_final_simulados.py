from pathlib import Path
import re
import csv
import html
from datetime import datetime
from collections import defaultdict

# ============================================================
# AUDITORIA FINAL DOS SIMULADOS JURÍDICOS
# ------------------------------------------------------------
# O que este script faz:
# 1. Lê a pasta pdfs/
# 2. Lê a pasta questoes_validadas_pdf/
# 3. Lê a pasta html_simulados/
# 4. Cruza PDF x QUESTÕES x HTML
# 5. Gera relatório em .md e .csv dentro da pasta auditoria_final/
#
# Como usar:
#   python3 auditoria_final_simulados.py
#
# Dependência recomendada para contar julgados dentro dos PDFs:
#   python3 -m pip install pymupdf
#
# Se o PyMuPDF não estiver instalado, o script continua rodando,
# mas não conseguirá estimar a quantidade de julgados dentro dos PDFs.
# ============================================================

PASTA_RAIZ = Path.cwd()
PASTA_PDFS = PASTA_RAIZ / "pdfs"
PASTA_QUESTOES = PASTA_RAIZ / "questoes_validadas_pdf"
PASTA_HTML = PASTA_RAIZ / "html_simulados"
PASTA_SAIDA = PASTA_RAIZ / "auditoria_final"
PASTA_CACHE = PASTA_SAIDA / "cache_textos_pdf"

PASTA_SAIDA.mkdir(exist_ok=True)
PASTA_CACHE.mkdir(exist_ok=True)

DATA_HORA = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
CSV_GERAL = PASTA_SAIDA / f"auditoria_geral_{DATA_HORA}.csv"
RELATORIO_MD = PASTA_SAIDA / f"relatorio_auditoria_final_{DATA_HORA}.md"
CSV_PENDENCIAS = PASTA_SAIDA / f"pendencias_{DATA_HORA}.csv"
CSV_SCRIPTS = PASTA_SAIDA / f"scripts_encontrados_{DATA_HORA}.csv"


def normalizar_texto(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def chave_info(nome: str):
    """
    Extrai chave padronizada: Info 835 STJ, Info 1162 STF etc.
    Funciona para PDF, MD e HTML.
    """
    base = Path(nome).stem
    base = base.replace("_questoes", "")
    base = base.replace("_simulado", "")
    base = base.replace("-questoes", "")
    base = normalizar_texto(base)

    m = re.search(r"(?:Info|Informativo)\s*(\d{1,4})\s*[-_ ]*\s*(STF|STJ)", base, re.I)
    if not m:
        return None

    numero = int(m.group(1))
    tribunal = m.group(2).upper()
    return f"Info {numero} {tribunal}"


def ordenar_chave(chave: str):
    m = re.search(r"Info\s+(\d+)\s+(STF|STJ)", chave)
    if not m:
        return (9999, chave)
    tribunal = m.group(2)
    num = int(m.group(1))
    ordem_tribunal = 0 if tribunal == "STF" else 1
    return (ordem_tribunal, num)


def listar_arquivos(pasta: Path, extensoes):
    if not pasta.exists():
        return []
    return [p for p in pasta.rglob("*") if p.is_file() and p.suffix.lower() in extensoes and not p.name.startswith("._")]


def tentar_ler_texto(caminho: Path) -> str:
    try:
        return caminho.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            return caminho.read_text(encoding="latin-1", errors="ignore")
        except Exception:
            return ""


def extrair_texto_pdf(pdf: Path) -> str:
    """Extrai texto do PDF usando PyMuPDF, com cache."""
    cache = PASTA_CACHE / f"{pdf.stem}.txt"
    if cache.exists() and cache.stat().st_size > 0:
        return tentar_ler_texto(cache)

    try:
        import fitz  # PyMuPDF
    except Exception:
        return ""

    partes = []
    try:
        doc = fitz.open(pdf)
        for page in doc:
            partes.append(page.get_text("text"))
        texto = "\n".join(partes)
        cache.write_text(texto, encoding="utf-8")
        return texto
    except Exception:
        return ""


def estimar_julgados_pdf(texto: str) -> int | None:
    """
    Estimativa conservadora de julgados/teses no PDF.

    Observação importante:
    PDFs de informativos nem sempre vêm com marcação 'Julgado 1'.
    Por isso usamos vários sinais:
      - 'ODS 3', 'ODS 3 e 16' etc.
      - 'Tese fixada:'
      - 'Tema xxx'
      - perguntas/títulos antes de ODS
    A estimativa serve para encontrar lacunas, não para substituir revisão jurídica.
    """
    if not texto.strip():
        return None

    t = texto

    # Remove ruídos comuns para evitar inflar contagem
    t = re.sub(r"Informativo\s+\d{1,4}[- ](?:STF|STJ).*?\|\s*\d+", " ", t, flags=re.I)
    t = re.sub(r"Márcio André Lopes Cavalcante", " ", t, flags=re.I)

    contagens = []

    # Muitos PDFs do Dizer o Direito marcam cada julgado com ODS.
    ods = re.findall(r"\bODS\s*\d+(?:\s*(?:E|e|,)\s*\d+)*\b", t)
    if ods:
        contagens.append(len(ods))

    # Se já houver marcação explícita de julgado.
    julgados = re.findall(r"(?:^|\n)\s*(?:##\s*)?Julgado\s+\d+\b", t, flags=re.I)
    if julgados:
        contagens.append(len(julgados))

    # Temas de RG/repetitivos geralmente aparecem assim.
    temas = re.findall(r"\bTema\s+\d{1,5}\b", t, flags=re.I)
    if temas:
        # Usa quantidade de temas únicos para evitar repetição exagerada.
        contagens.append(len(set(x.lower() for x in temas)))

    # Súmulas.
    sumulas = re.findall(r"\bS[úu]mula(?:\s+Vinculante)?\s+\d+\b", t, flags=re.I)
    if sumulas:
        contagens.append(len(set(x.lower() for x in sumulas)))

    if not contagens:
        return 0

    # Estratégia: usar a maior contagem razoável, porque costuma ser a que melhor captura os itens.
    return max(contagens)


def contar_questoes_md(texto: str) -> int:
    if not texto.strip():
        return 0

    padroes = [
        r"^###\s*Quest[ãa]o\b",
        r"\*\*Gabarito:\*\*\s*(CERTO|ERRADO)",
        r"\bGabarito:\s*(CERTO|ERRADO)\b",
    ]

    contagens = []
    for p in padroes:
        achados = re.findall(p, texto, flags=re.I | re.M)
        if achados:
            contagens.append(len(achados))

    return max(contagens) if contagens else 0


def contar_questoes_html(texto: str) -> int:
    if not texto.strip():
        return 0

    texto_sem_tags = re.sub(r"<script.*?</script>", " ", texto, flags=re.I | re.S)
    texto_sem_tags = re.sub(r"<style.*?</style>", " ", texto_sem_tags, flags=re.I | re.S)
    texto_limpo = html.unescape(texto_sem_tags)

    padroes = [
        r"\bGabarito\b",
        r"class=[\"'][^\"']*(?:questao|question|card-questao|question-card)[^\"']*[\"']",
        r"data-(?:gabarito|answer|resposta)=",
        r"Quest[ãa]o\s+\d+",
    ]

    contagens = []
    for p in padroes:
        achados = re.findall(p, texto_limpo, flags=re.I)
        if achados:
            contagens.append(len(achados))

    return max(contagens) if contagens else 0


def classificar_status(pdf_count, md_count, html_count):
    if pdf_count is None:
        if md_count == 0:
            return "SEM_QUESTOES_MD"
        if html_count == 0:
            return "SEM_HTML"
        if html_count < md_count:
            return "HTML_MENOR_QUE_MD"
        return "OK_SEM_CONTAGEM_PDF"

    if pdf_count == 0 and md_count == 0 and html_count == 0:
        return "SEM_DADOS"
    if md_count == 0:
        return "FALTA_GERAR_QUESTOES"
    if pdf_count > 0 and md_count < pdf_count:
        return "QUESTOES_INCOMPLETAS"
    if html_count == 0:
        return "FALTA_GERAR_HTML"
    if html_count < md_count:
        return "HTML_INCOMPLETO"
    if pdf_count > 0 and html_count < pdf_count:
        return "HTML_INCOMPLETO_VS_PDF"
    return "OK"


def analisar_scripts():
    scripts = [p for p in PASTA_RAIZ.glob("*.py") if p.is_file()]
    linhas = []

    for s in sorted(scripts, key=lambda p: p.name.lower()):
        nome = s.name.lower()
        if "backup" in nome or "final" in nome:
            classe = "REVISAR/ARQUIVAR"
        elif "auditar" in nome or "auditoria" in nome:
            classe = "AUDITORIA"
        elif "gerar_html" in nome or "cadernos" in nome:
            classe = "GERADOR_HTML"
        elif "gerar_quest" in nome:
            classe = "GERADOR_QUESTOES"
        elif "converter" in nome or "extrair" in nome:
            classe = "EXTRACAO_PDF_MD"
        else:
            classe = "OUTRO"

        linhas.append({
            "script": s.name,
            "classificacao": classe,
            "tamanho_kb": round(s.stat().st_size / 1024, 1),
        })

    with CSV_SCRIPTS.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["script", "classificacao", "tamanho_kb"])
        writer.writeheader()
        writer.writerows(linhas)

    return linhas


def main():
    pdfs = listar_arquivos(PASTA_PDFS, {".pdf"})
    mds = listar_arquivos(PASTA_QUESTOES, {".md"})
    htmls = listar_arquivos(PASTA_HTML, {".html", ".htm"})

    por_info = defaultdict(lambda: {
        "pdfs": [],
        "mds": [],
        "htmls": [],
        "julgados_estimados_pdf": None,
        "questoes_md": 0,
        "questoes_html": 0,
    })

    for p in pdfs:
        k = chave_info(p.name)
        if k:
            por_info[k]["pdfs"].append(p)

    for p in mds:
        k = chave_info(p.name)
        if k:
            por_info[k]["mds"].append(p)

    for p in htmls:
        k = chave_info(p.name)
        if k:
            por_info[k]["htmls"].append(p)

    linhas = []

    for chave in sorted(por_info.keys(), key=ordenar_chave):
        item = por_info[chave]

        # PDF: usa maior estimativa entre os PDFs da chave, se houver duplicatas.
        estimativas_pdf = []
        for pdf in item["pdfs"]:
            texto_pdf = extrair_texto_pdf(pdf)
            estimativa = estimar_julgados_pdf(texto_pdf)
            if estimativa is not None:
                estimativas_pdf.append(estimativa)

        item["julgados_estimados_pdf"] = max(estimativas_pdf) if estimativas_pdf else None

        # MD: soma questões dos MDs da chave.
        item["questoes_md"] = sum(contar_questoes_md(tentar_ler_texto(md)) for md in item["mds"])

        # HTML: usa maior contagem entre HTMLs da chave, pois pode haver duplicatas/versionamentos.
        contagens_html = [contar_questoes_html(tentar_ler_texto(h)) for h in item["htmls"]]
        item["questoes_html"] = max(contagens_html) if contagens_html else 0

        pdf_count = item["julgados_estimados_pdf"]
        md_count = item["questoes_md"]
        html_count = item["questoes_html"]
        status = classificar_status(pdf_count, md_count, html_count)

        faltam_md = ""
        faltam_html = ""
        if pdf_count is not None and pdf_count > md_count:
            faltam_md = pdf_count - md_count
        if md_count > html_count:
            faltam_html = md_count - html_count

        linhas.append({
            "info": chave,
            "tribunal": chave.split()[-1],
            "pdfs_encontrados": len(item["pdfs"]),
            "arquivos_md": len(item["mds"]),
            "arquivos_html": len(item["htmls"]),
            "julgados_estimados_pdf": "" if pdf_count is None else pdf_count,
            "questoes_md": md_count,
            "questoes_html": html_count,
            "faltam_questoes_md": faltam_md,
            "faltam_no_html": faltam_html,
            "status": status,
            "pdfs": " | ".join(p.name for p in item["pdfs"]),
            "mds": " | ".join(p.name for p in item["mds"]),
            "htmls": " | ".join(p.name for p in item["htmls"]),
        })

    # CSV geral
    fieldnames = [
        "info", "tribunal", "pdfs_encontrados", "arquivos_md", "arquivos_html",
        "julgados_estimados_pdf", "questoes_md", "questoes_html",
        "faltam_questoes_md", "faltam_no_html", "status", "pdfs", "mds", "htmls"
    ]

    with CSV_GERAL.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(linhas)

    pendentes = [l for l in linhas if l["status"] != "OK" and l["status"] != "OK_SEM_CONTAGEM_PDF"]
    with CSV_PENDENCIAS.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(pendentes)

    scripts = analisar_scripts()

    total_pdf = len(pdfs)
    total_md = len(mds)
    total_html = len(htmls)
    total_infos = len(linhas)
    total_ok = sum(1 for l in linhas if l["status"] == "OK")
    total_pend = len(pendentes)

    por_status = defaultdict(int)
    for l in linhas:
        por_status[l["status"]] += 1

    # Relatório MD
    with RELATORIO_MD.open("w", encoding="utf-8") as f:
        f.write(f"# Relatório de Auditoria Final dos Simulados\n\n")
        f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")

        f.write("## 1. Resumo geral\n\n")
        f.write(f"- PDFs encontrados: **{total_pdf}**\n")
        f.write(f"- Arquivos Markdown de questões: **{total_md}**\n")
        f.write(f"- Arquivos HTML: **{total_html}**\n")
        f.write(f"- Informativos/itens identificados: **{total_infos}**\n")
        f.write(f"- Itens OK: **{total_ok}**\n")
        f.write(f"- Itens com pendência: **{total_pend}**\n\n")

        f.write("## 2. Status encontrados\n\n")
        for status, qtd in sorted(por_status.items(), key=lambda x: (-x[1], x[0])):
            f.write(f"- **{status}**: {qtd}\n")
        f.write("\n")

        f.write("## 3. Pendências prioritárias\n\n")
        if not pendentes:
            f.write("Nenhuma pendência encontrada pelos critérios automáticos.\n\n")
        else:
            f.write("| Info | PDF estimado | Questões MD | Questões HTML | Pendência |\n")
            f.write("|---|---:|---:|---:|---|\n")
            for l in pendentes:
                f.write(
                    f"| {l['info']} | {l['julgados_estimados_pdf']} | {l['questoes_md']} | "
                    f"{l['questoes_html']} | {l['status']} |\n"
                )
            f.write("\n")

        f.write("## 4. Tabela completa\n\n")
        f.write("| Info | PDFs | MDs | HTMLs | PDF estimado | Questões MD | Questões HTML | Status |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---|\n")
        for l in linhas:
            f.write(
                f"| {l['info']} | {l['pdfs_encontrados']} | {l['arquivos_md']} | {l['arquivos_html']} | "
                f"{l['julgados_estimados_pdf']} | {l['questoes_md']} | {l['questoes_html']} | {l['status']} |\n"
            )

        f.write("\n## 5. Scripts encontrados\n\n")
        if scripts:
            f.write("| Script | Classificação | Tamanho KB |\n")
            f.write("|---|---|---:|\n")
            for s in scripts:
                f.write(f"| {s['script']} | {s['classificacao']} | {s['tamanho_kb']} |\n")
        else:
            f.write("Nenhum script .py encontrado na raiz.\n")

        f.write("\n## 6. Observações importantes\n\n")
        f.write("- A contagem de julgados no PDF é uma estimativa automática. Ela ajuda a localizar lacunas, mas deve ser revisada nos casos críticos.\n")
        f.write("- A fonte mais segura para finalizar o simulado deve ser a pasta `questoes_validadas_pdf/`.\n")
        f.write("- Se o PDF tem mais julgados estimados do que questões em MD, o item aparece como `QUESTOES_INCOMPLETAS`.\n")
        f.write("- Se o MD tem mais questões do que o HTML, o item aparece como `HTML_INCOMPLETO`.\n")

    print("\n✅ Auditoria concluída!")
    print(f"\nArquivos gerados em: {PASTA_SAIDA}")
    print(f"- Relatório principal: {RELATORIO_MD.name}")
    print(f"- CSV geral: {CSV_GERAL.name}")
    print(f"- CSV de pendências: {CSV_PENDENCIAS.name}")
    print(f"- CSV de scripts: {CSV_SCRIPTS.name}")
    print("\nPróximo passo: abra o relatório .md dentro da pasta auditoria_final.")


if __name__ == "__main__":
    main()
