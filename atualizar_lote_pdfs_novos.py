from pathlib import Path
import subprocess
import re
import csv
import shutil

PASTA_PDFS = Path("pdfs")
PASTA_MD = Path("md_criticos_reprocessados")
PASTA_QUESTOES = Path("questoes_validadas_pdf")
PASTA_AUDITORIA = Path("auditoria_final")
PASTA_GERADAS = Path("questoes_geradas_api_revisar")

ARQUIVO_LISTA_DELTA = Path("data/pdfs_novos_detectados.txt")

JSON_RAIZ = Path("data/questoes.json")
JSON_HTML = Path("html_final/data/questoes.json")


def run(cmd):
    print("\n🚀", " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise SystemExit("❌ Erro ao executar: " + " ".join(cmd))


def normalizar_nome(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def item_e_tribunal(pdf):
    item = pdf.stem

    m_info = re.match(r"Info\s+\d+\s+(STF|STJ)$", item, flags=re.I)
    if m_info:
        return item, m_info.group(1).upper()

    m_extra = re.match(r"Ed\.?\s*Extra\s+\d+\s+STJ$", item, flags=re.I)
    if m_extra:
        return item, "STJ"

    return None, None


def contar_julgados(md):
    txt = md.read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r"^## Julgado\s+\d+", txt, flags=re.M))


def contar_questoes(md):
    txt = md.read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r"^## Questão\s+\d+", txt, flags=re.M))


def limpar_md(md):
    txt = md.read_text(encoding="utf-8", errors="ignore")
    txt = re.sub(r"\n?\*\*ODS:\*\*\s*\d+(?:\s*E\s*\d+)?\s*\n?", "\n", txt, flags=re.I)
    txt = re.sub(
        r"\n\*\*Observações de saneamento:\*\*.*?(?=\n---|\n## Julgado|\Z)",
        "\n",
        txt,
        flags=re.I | re.S
    )
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    md.write_text(txt.strip() + "\n", encoding="utf-8")


def criar_csv(item, tribunal, md, julgados):
    PASTA_AUDITORIA.mkdir(exist_ok=True)

    csv_path = PASTA_AUDITORIA / f"pendencias_{item.replace(' ', '_')}_md_forcado.csv"

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)

        w.writerow([
            "categoria", "item", "tribunal", "pdfs_encontrados", "arquivos_md", "arquivos_html",
            "itens_estimados_pdf", "questoes_md", "questoes_html", "faltam_questoes_md",
            "faltam_no_html", "status", "pdfs", "mds", "htmls"
        ])

        w.writerow([
            "INFORMATIVO", item, tribunal, 0, 1, 0,
            julgados, 0, 0, julgados,
            "", "FALTA_GERAR_QUESTOES", "", str(md.resolve()), ""
        ])

    return csv_path


def carregar_pdfs_delta():
    if not ARQUIVO_LISTA_DELTA.exists():
        print("✅ Nenhuma lista de PDFs novos encontrada.")
        return []

    linhas = [
        linha.strip()
        for linha in ARQUIVO_LISTA_DELTA.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]

    pdfs = []

    for nome in linhas:
        caminho = Path(nome)

        if not caminho.exists():
            caminho = PASTA_PDFS / nome

        if caminho.exists():
            pdfs.append(caminho)
        else:
            print(f"⚠️ Arquivo listado no delta não existe mais: {nome}")

    return pdfs


def encontrar_saida_api(item):
    slug = normalizar_nome(item)

    arquivos_md = [
        p for p in PASTA_GERADAS.glob("*.md")
        if slug in normalizar_nome(p.stem)
        and not p.name.startswith(("relatorio_", "controle_"))
    ]

    arquivos_md = sorted(
        arquivos_md,
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if arquivos_md:
        return arquivos_md[0]

    print(f"❌ Nenhum arquivo gerado pela API para: {item}")
    return None


def processar_pdf(pdf):
    item, tribunal = item_e_tribunal(pdf)

    if not item:
        print(f"⚠️ Pulando {pdf.name}")
        return False

    md = PASTA_MD / f"{item}_limpo_estruturado.md"

    if not md.exists():
        print(f"❌ MD não encontrado: {md}")
        return False

    limpar_md(md)

    julgados = contar_julgados(md)
    print(f"\n📄 {item}: {julgados} julgado(s)")

    if julgados == 0:
        print("❌ Nenhum julgado encontrado")
        return False

    csv_path = criar_csv(item, tribunal, md, julgados)

    run([
        "python3", "gerar_questoes_pendentes_api_seguro_v2.py",
        "--pendencias", str(csv_path),
        "--categoria", "INFORMATIVO",
        "--item", item,
        "--sobrescrever",
        "--itens-por-lote", "1"
    ])

    saida = encontrar_saida_api(item)

    if saida is None:
        return False

    print(f"📄 Usando: {saida.name}")

    questoes = contar_questoes(saida)
    print(f"🔎 Validação: julgados={julgados} | questões={questoes}")

    if questoes != julgados:
        print("🚨 BLOQUEADO: quantidade divergente")
        return False

    destino = PASTA_QUESTOES / f"{item}_questoes.md"
    shutil.copy2(saida, destino)

    print(f"✅ Copiado: {destino}")

    return True


def main():
    novos = carregar_pdfs_delta()

    if not novos:
        print("✅ Nenhum PDF novo encontrado.")
        return

    print("📚 PDFs novos:")
    for p in novos:
        print("-", p.name)

    resp = input("\nGerar questões? (s/N): ").strip().lower()

    if resp != "s":
        print("Cancelado.")
        return

    print("\n🔄 Convertendo PDFs...")
    run(["python3", "converter_pdf_md.py"])

    ok = []
    falhas = []

    for pdf in novos:
        if processar_pdf(pdf):
            ok.append(pdf.name)
        else:
            falhas.append(pdf.name)

    if ok:
        print("\n🔄 Atualizando JSON...")
        run(["python3", "gerar_json_questoes_v4.py"])

        if JSON_RAIZ.exists():
            JSON_HTML.parent.mkdir(parents=True, exist_ok=True)
            JSON_HTML.write_text(JSON_RAIZ.read_text(encoding="utf-8"), encoding="utf-8")
            print("✅ JSON atualizado no site")

    print("\n📊 RESUMO")
    print("OK:", len(ok))
    for x in ok:
        print("  ✅", x)

    print("FALHAS:", len(falhas))
    for x in falhas:
        print("  ❌", x)


if __name__ == "__main__":
    main()