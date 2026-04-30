from pathlib import Path
import re
import csv
import html
import unicodedata
from datetime import datetime
from collections import defaultdict

# ============================================================
# AUDITORIA FINAL DOS SIMULADOS JURÍDICOS - VERSÃO 2
# ------------------------------------------------------------
# Inclui auditoria de:
#   1. Informativos STF/STJ
#   2. Repetitivos STJ
#   3. Repercussão Geral STF (RG)
#   4. Súmulas / Súmulas Vinculantes
#
# Como usar:
#   python3 auditoria_final_simulados_v2.py
#
# Dependência recomendada para contar itens dentro dos PDFs:
#   python3 -m pip install pymupdf
#
# Se o PyMuPDF não estiver instalado, o script continua rodando,
# mas não conseguirá estimar a quantidade de itens dentro dos PDFs.
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
CSV_GERAL = PASTA_SAIDA / f"auditoria_geral_v2_{DATA_HORA}.csv"
CSV_PENDENCIAS = PASTA_SAIDA / f"pendencias_v2_{DATA_HORA}.csv"
CSV_SCRIPTS = PASTA_SAIDA / f"scripts_encontrados_v2_{DATA_HORA}.csv"
RELATORIO_MD = PASTA_SAIDA / f"relatorio_auditoria_final_v2_{DATA_HORA}.md"


# -----------------------------
# Utilidades de texto
# -----------------------------

def sem_acentos(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def normalizar_texto(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = sem_acentos(s)
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def limpar_base_nome(nome: str) -> str:
    base = Path(nome).stem
    remover = [
        "_questoes", " questoes", "-questoes",
        "_simulado", " simulado", "-simulado",
        "limpo", "saneado", "resumido", "html",
    ]
    for r in remover:
        base = re.sub(re.escape(r), " ", base, flags=re.I)
    return normalizar_texto(base)


def padronizar_disciplina(raw: str) -> str:
    """Padroniza nomes de disciplinas extraídos de PDFs/MD/HTML."""
    s = limpar_base_nome(raw)
    s = re.sub(r"\b(Rep|Repetitivo|Repetitivos|RG|Repercussao Geral)\b", " ", s, flags=re.I)
    s = re.sub(r"\b(STF|STJ)\b", " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()

    # Correções comuns dos nomes dos arquivos.
    mapa = {
        "Proc Civil": "Processo Civil",
        "Processual Civil": "Processo Civil",
        "Proc Penal": "Processo Penal",
        "Processual Penal": "Processo Penal",
        "Tributario": "Tributário",
        "Administrativo": "Administrativo",
        "Ambiental": "Ambiental",
        "Civil": "Civil",
        "Penal": "Penal",
        "Consumidor": "Consumidor",
        "Empresarial": "Empresarial",
        "Eleitoral": "Eleitoral",
    }

    chave = s.lower()
    for origem, destino in mapa.items():
        if origem.lower() == chave:
            return destino

    # Title case simples, mantendo termos jurídicos legíveis.
    if not s:
        return "Geral"
    return " ".join(p.capitalize() for p in s.split())


# -----------------------------
# Identificação das chaves
# -----------------------------

def identificar_item(caminho: Path):
    """
    Retorna dicionário com categoria, chave, tribunal e ordem.

    Categorias:
      - INFORMATIVO
      - REPETITIVO
      - RG
      - SUMULA
      - OUTRO/None
    """
    nome = caminho.name
    base = limpar_base_nome(nome)
    base_ascii = sem_acentos(base).lower()

    # 1) Informativos STF/STJ
    m = re.search(r"(?:\bInfo\b|\bInformativo\b)\s*(\d{1,4})\s*(STF|STJ)", base, re.I)
    if m:
        numero = int(m.group(1))
        tribunal = m.group(2).upper()
        return {
            "categoria": "INFORMATIVO",
            "chave": f"Info {numero} {tribunal}",
            "tribunal": tribunal,
            "ordem": (1, 0 if tribunal == "STF" else 1, numero, ""),
        }

    # 2) Repercussão Geral STF
    # Evita pegar "rg" dentro de outras palavras: usa token isolado.
    if re.search(r"(^|\s)RG(\s|$)", base, re.I) or "repercussao geral" in base_ascii:
        disciplina = padronizar_disciplina(base)
        return {
            "categoria": "RG",
            "chave": f"RG - {disciplina}",
            "tribunal": "STF",
            "ordem": (2, 0, 0, disciplina),
        }

    # 3) Repetitivos STJ
    if re.search(r"(^|\s)(Rep|Repetitivo|Repetitivos)(\s|$)", base, re.I):
        disciplina = padronizar_disciplina(base)
        return {
            "categoria": "REPETITIVO",
            "chave": f"Repetitivo - {disciplina}",
            "tribunal": "STJ",
            "ordem": (3, 1, 0, disciplina),
        }

    # 4) Súmulas / Súmulas Vinculantes
    if "sumula" in base_ascii or "sumulas" in base_ascii or "enunciados sumulas" in base_ascii:
        if "vinculante" in base_ascii:
            # Arquivo genérico: Súmulas Vinculantes.md
            if "stj" in base_ascii:
                chave = "Súmulas Vinculantes STJ"
                tribunal = "STJ"
            else:
                chave = "Súmulas Vinculantes STF"
                tribunal = "STF"
        else:
            if "stj" in base_ascii:
                chave = "Súmulas STJ"
                tribunal = "STJ"
            elif "stf" in base_ascii:
                chave = "Súmulas STF"
                tribunal = "STF"
            else:
                chave = "Súmulas"
                tribunal = "GERAL"

        return {
            "categoria": "SUMULA",
            "chave": chave,
            "tribunal": tribunal,
            "ordem": (4, 0 if tribunal == "STF" else 1, 0, chave),
        }

    return None


def listar_arquivos(pasta: Path, extensoes):
    if not pasta.exists():
        return []
    return [
        p for p in pasta.rglob("*")
        if p.is_file()
        and p.suffix.lower() in extensoes
        and not p.name.startswith("._")
        and "__MACOSX" not in str(p)
    ]


def tentar_ler_texto(caminho: Path) -> str:
    try:
        return caminho.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            return caminho.read_text(encoding="latin-1", errors="ignore")
        except Exception:
            return ""


def extrair_texto_pdf(pdf: Path) -> str:
    cache_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", pdf.stem) + ".txt"
    cache = PASTA_CACHE / cache_name
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


# -----------------------------
# Contagens
# -----------------------------

def estimar_itens_pdf(texto: str, categoria: str):
    """
    Estima a quantidade de itens-base existentes no PDF.

    Para informativos: julgados.
    Para RG: temas de repercussão geral.
    Para repetitivos: temas repetitivos.
    Para súmulas: enunciados/súmulas.
    """
    if not texto.strip():
        return None

    t = texto
    t_ascii = sem_acentos(t)

    # Remove ruídos comuns.
    t = re.sub(r"Informativo\s+\d{1,4}[- ](?:STF|STJ).*?\|\s*\d+", " ", t, flags=re.I)
    t = re.sub(r"Márcio André Lopes Cavalcante", " ", t, flags=re.I)

    if categoria == "INFORMATIVO":
        contagens = []
        ods = re.findall(r"\bODS\s*\d+(?:\s*(?:E|e|,)\s*\d+)*\b", t)
        if ods:
            contagens.append(len(ods))

        julgados = re.findall(r"(?:^|\n)\s*(?:##\s*)?Julgado\s+\d+\b", t, flags=re.I)
        if julgados:
            contagens.append(len(julgados))

        # Em informativos, Tema pode aparecer dentro de um julgado; usa só como fallback.
        temas = re.findall(r"\bTema\s+\d{1,5}\b", t, flags=re.I)
        if temas and not contagens:
            contagens.append(len(set(x.lower() for x in temas)))

        return max(contagens) if contagens else 0

    if categoria in {"RG", "REPETITIVO"}:
        # A contagem principal é por Tema único.
        temas = re.findall(r"\bTema\s*(?:n[ºo.]?\s*)?(\d{1,5})\b", t_ascii, flags=re.I)
        if temas:
            return len(set(temas))

        # Fallback: blocos iniciados por assunto/tese.
        teses = re.findall(r"\bTese\s+(?:fixada|firmada|aprovada)\b", t_ascii, flags=re.I)
        if teses:
            return len(teses)

        # Fallback conservador: 'Controvérsia' pode aparecer em repetitivos.
        controversias = re.findall(r"\bControversia\s*(?:n[ºo.]?\s*)?\d+\b", t_ascii, flags=re.I)
        if controversias:
            return len(set(controversias))

        return 0

    if categoria == "SUMULA":
        # Captura Súmula, Súmula Vinculante, Enunciado etc.
        padroes = [
            r"\bSumula\s+Vinculante\s*(?:n[ºo.]?\s*)?(\d{1,4})\b",
            r"\bSumula\s*(?:n[ºo.]?\s*)?(\d{1,4})\b",
            r"\bEnunciado\s*(?:n[ºo.]?\s*)?(\d{1,4})\b",
        ]
        nums = []
        for p in padroes:
            nums.extend(re.findall(p, t_ascii, flags=re.I))
        if nums:
            return len(set(nums))

        return 0

    return None


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
            return "HTML_INCOMPLETO"
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


# -----------------------------
# Scripts
# -----------------------------

def analisar_scripts():
    scripts = [p for p in PASTA_RAIZ.glob("*.py") if p.is_file()]
    linhas = []

    for s in sorted(scripts, key=lambda p: p.name.lower()):
        nome = s.name.lower()
        if "backup" in nome:
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


# -----------------------------
# Auditoria principal
# -----------------------------

def main():
    pdfs = listar_arquivos(PASTA_PDFS, {".pdf"})
    mds = listar_arquivos(PASTA_QUESTOES, {".md"})
    htmls = listar_arquivos(PASTA_HTML, {".html", ".htm"})

    itens = defaultdict(lambda: {
        "categoria": "",
        "tribunal": "",
        "ordem": (999, 999, 999999, ""),
        "pdfs": [],
        "mds": [],
        "htmls": [],
        "itens_estimados_pdf": None,
        "questoes_md": 0,
        "questoes_html": 0,
    })

    nao_classificados = []

    for grupo, arquivos in [("PDF", pdfs), ("MD", mds), ("HTML", htmls)]:
        for p in arquivos:
            info = identificar_item(p)
            if not info:
                nao_classificados.append({"tipo": grupo, "arquivo": str(p.relative_to(PASTA_RAIZ))})
                continue
            k = info["chave"]
            itens[k]["categoria"] = info["categoria"]
            itens[k]["tribunal"] = info["tribunal"]
            itens[k]["ordem"] = info["ordem"]
            if grupo == "PDF":
                itens[k]["pdfs"].append(p)
            elif grupo == "MD":
                itens[k]["mds"].append(p)
            elif grupo == "HTML":
                itens[k]["htmls"].append(p)

    linhas = []
    for chave in sorted(itens.keys(), key=lambda k: itens[k]["ordem"]):
        item = itens[chave]
        categoria = item["categoria"]

        estimativas_pdf = []
        for pdf in item["pdfs"]:
            texto_pdf = extrair_texto_pdf(pdf)
            estimativa = estimar_itens_pdf(texto_pdf, categoria)
            if estimativa is not None:
                estimativas_pdf.append(estimativa)
        item["itens_estimados_pdf"] = max(estimativas_pdf) if estimativas_pdf else None

        item["questoes_md"] = sum(contar_questoes_md(tentar_ler_texto(md)) for md in item["mds"])

        contagens_html = [contar_questoes_html(tentar_ler_texto(h)) for h in item["htmls"]]
        item["questoes_html"] = max(contagens_html) if contagens_html else 0

        pdf_count = item["itens_estimados_pdf"]
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
            "categoria": categoria,
            "item": chave,
            "tribunal": item["tribunal"],
            "pdfs_encontrados": len(item["pdfs"]),
            "arquivos_md": len(item["mds"]),
            "arquivos_html": len(item["htmls"]),
            "itens_estimados_pdf": "" if pdf_count is None else pdf_count,
            "questoes_md": md_count,
            "questoes_html": html_count,
            "faltam_questoes_md": faltam_md,
            "faltam_no_html": faltam_html,
            "status": status,
            "pdfs": " | ".join(p.name for p in item["pdfs"]),
            "mds": " | ".join(p.name for p in item["mds"]),
            "htmls": " | ".join(p.name for p in item["htmls"]),
        })

    fieldnames = [
        "categoria", "item", "tribunal", "pdfs_encontrados", "arquivos_md", "arquivos_html",
        "itens_estimados_pdf", "questoes_md", "questoes_html", "faltam_questoes_md",
        "faltam_no_html", "status", "pdfs", "mds", "htmls"
    ]

    with CSV_GERAL.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(linhas)

    pendentes = [l for l in linhas if l["status"] not in {"OK", "OK_SEM_CONTAGEM_PDF"}]
    with CSV_PENDENCIAS.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(pendentes)

    scripts = analisar_scripts()

    total_pdf = len(pdfs)
    total_md = len(mds)
    total_html = len(htmls)
    total_itens = len(linhas)
    total_ok = sum(1 for l in linhas if l["status"] == "OK")
    total_pend = len(pendentes)

    por_categoria = defaultdict(int)
    por_categoria_ok = defaultdict(int)
    por_categoria_pend = defaultdict(int)
    por_status = defaultdict(int)
    for l in linhas:
        por_categoria[l["categoria"]] += 1
        por_status[l["status"]] += 1
        if l["status"] == "OK":
            por_categoria_ok[l["categoria"]] += 1
        elif l["status"] not in {"OK", "OK_SEM_CONTAGEM_PDF"}:
            por_categoria_pend[l["categoria"]] += 1

    with RELATORIO_MD.open("w", encoding="utf-8") as f:
        f.write("# Relatório de Auditoria Final dos Simulados — V2\n\n")
        f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")

        f.write("## 1. Resumo geral\n\n")
        f.write(f"- PDFs encontrados: **{total_pdf}**\n")
        f.write(f"- Arquivos Markdown de questões: **{total_md}**\n")
        f.write(f"- Arquivos HTML: **{total_html}**\n")
        f.write(f"- Itens identificados: **{total_itens}**\n")
        f.write(f"- Itens OK: **{total_ok}**\n")
        f.write(f"- Itens com pendência: **{total_pend}**\n\n")

        f.write("## 2. Resumo por categoria\n\n")
        f.write("| Categoria | Itens | OK | Com pendência |\n")
        f.write("|---|---:|---:|---:|\n")
        for cat in ["INFORMATIVO", "RG", "REPETITIVO", "SUMULA"]:
            f.write(f"| {cat} | {por_categoria[cat]} | {por_categoria_ok[cat]} | {por_categoria_pend[cat]} |\n")
        f.write("\n")

        f.write("## 3. Status encontrados\n\n")
        for status, qtd in sorted(por_status.items(), key=lambda x: (-x[1], x[0])):
            f.write(f"- **{status}**: {qtd}\n")
        f.write("\n")

        f.write("## 4. Pendências prioritárias\n\n")
        if not pendentes:
            f.write("Nenhuma pendência encontrada pelos critérios automáticos.\n\n")
        else:
            f.write("| Categoria | Item | PDF estimado | Questões MD | Questões HTML | Pendência |\n")
            f.write("|---|---|---:|---:|---:|---|\n")
            for l in pendentes:
                f.write(
                    f"| {l['categoria']} | {l['item']} | {l['itens_estimados_pdf']} | "
                    f"{l['questoes_md']} | {l['questoes_html']} | {l['status']} |\n"
                )
            f.write("\n")

        f.write("## 5. Tabela completa por categoria\n\n")
        for cat in ["INFORMATIVO", "RG", "REPETITIVO", "SUMULA"]:
            linhas_cat = [l for l in linhas if l["categoria"] == cat]
            if not linhas_cat:
                continue
            f.write(f"### {cat}\n\n")
            f.write("| Item | PDFs | MDs | HTMLs | PDF estimado | Questões MD | Questões HTML | Status |\n")
            f.write("|---|---:|---:|---:|---:|---:|---:|---|\n")
            for l in linhas_cat:
                f.write(
                    f"| {l['item']} | {l['pdfs_encontrados']} | {l['arquivos_md']} | {l['arquivos_html']} | "
                    f"{l['itens_estimados_pdf']} | {l['questoes_md']} | {l['questoes_html']} | {l['status']} |\n"
                )
            f.write("\n")

        f.write("## 6. Arquivos não classificados\n\n")
        if nao_classificados:
            f.write("Estes arquivos existem, mas não entraram em Informativo/RG/Repetitivo/Súmula. Revise se algum deveria entrar.\n\n")
            f.write("| Tipo | Arquivo |\n")
            f.write("|---|---|\n")
            for n in nao_classificados[:200]:
                f.write(f"| {n['tipo']} | `{n['arquivo']}` |\n")
            if len(nao_classificados) > 200:
                f.write(f"\nForam omitidos {len(nao_classificados) - 200} arquivos não classificados adicionais.\n")
        else:
            f.write("Nenhum arquivo relevante ficou sem classificação.\n")
        f.write("\n")

        f.write("## 7. Scripts encontrados\n\n")
        if scripts:
            f.write("| Script | Classificação | Tamanho KB |\n")
            f.write("|---|---|---:|\n")
            for s in scripts:
                f.write(f"| {s['script']} | {s['classificacao']} | {s['tamanho_kb']} |\n")
        else:
            f.write("Nenhum script .py encontrado na raiz.\n")

        f.write("\n## 8. Observações importantes\n\n")
        f.write("- Esta versão inclui Informativos, RG, Repetitivos e Súmulas.\n")
        f.write("- A contagem de itens no PDF é uma estimativa automática: serve para localizar lacunas, mas os casos críticos devem ser revisados.\n")
        f.write("- Para RG e Repetitivos, a estimativa principal usa quantidade de `Tema nº ...` único.\n")
        f.write("- Para Súmulas, a estimativa usa números de súmulas/enunciados identificados no PDF.\n")
        f.write("- A fonte mais segura para finalizar o simulado continua sendo a pasta `questoes_validadas_pdf/`.\n")

    print("\n✅ Auditoria V2 concluída!")
    print(f"\nArquivos gerados em: {PASTA_SAIDA}")
    print(f"- Relatório principal: {RELATORIO_MD.name}")
    print(f"- CSV geral: {CSV_GERAL.name}")
    print(f"- CSV de pendências: {CSV_PENDENCIAS.name}")
    print(f"- CSV de scripts: {CSV_SCRIPTS.name}")
    print("\nPróximo passo: abra o relatório .md dentro da pasta auditoria_final.")


if __name__ == "__main__":
    main()
