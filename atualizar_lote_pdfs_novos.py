from pathlib import Path
import subprocess
import re
import csv
import shutil
import json
from datetime import datetime

PASTA_PDFS = Path("pdfs")
PASTA_MD = Path("md_criticos_reprocessados")
PASTA_QUESTOES = Path("questoes_validadas_pdf")
PASTA_AUDITORIA = Path("auditoria_final")
PASTA_GERADAS = Path("questoes_geradas_api_revisar")
JSON_RAIZ = Path("data/questoes.json")
JSON_HTML = Path("html_final/data/questoes.json")

def run(cmd):
    print("\n🚀", " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise SystemExit("❌ Erro ao executar: " + " ".join(cmd))

def nome_saida_api(item):
    return PASTA_GERADAS / ("informativo_" + item.lower().replace(" ", "_") + ".md")

def nome_saida_json_api(item):
    return PASTA_GERADAS / ("informativo_" + item.lower().replace(" ", "_") + ".json")

def contar_julgados(md):
    txt = md.read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r"^## Julgado\s+\d+", txt, flags=re.M))

def contar_questoes(md):
    txt = md.read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r"^## Questão\s+\d+", txt, flags=re.M))

def limpar_md(md):
    txt = md.read_text(encoding="utf-8", errors="ignore")
    txt = re.sub(r"\n?\*\*ODS:\*\*\s*\d+(?:\s*E\s*\d+)?\s*\n?", "\n", txt, flags=re.I)
    txt = re.sub(r"\n\*\*Observações de saneamento:\*\*.*?(?=\n---|\n## Julgado|\Z)", "\n", txt, flags=re.I | re.S)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    md.write_text(txt.strip() + "\n", encoding="utf-8")

def criar_csv(item, tribunal, md, julgados):
    PASTA_AUDITORIA.mkdir(exist_ok=True)
    csv_path = PASTA_AUDITORIA / f"pendencias_{item.replace(' ', '_')}_md_forcado.csv"

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "categoria","item","tribunal","pdfs_encontrados","arquivos_md","arquivos_html",
            "itens_estimados_pdf","questoes_md","questoes_html","faltam_questoes_md",
            "faltam_no_html","status","pdfs","mds","htmls"
        ])
        w.writerow([
            "INFORMATIVO", item, tribunal, 0, 1, 0,
            julgados, 0, 0, julgados,
            "", "FALTA_GERAR_QUESTOES", "", str(md.resolve()), ""
        ])

    return csv_path

def pdfs_novos():
    novos = []
    for pdf in sorted(PASTA_PDFS.glob("Info * *.pdf")):
        item = pdf.stem
        final = PASTA_QUESTOES / f"{item}_questoes.md"
        if not final.exists():
            novos.append(pdf)
    return novos

def processar_pdf(pdf):
    item = pdf.stem

    m = re.match(r"Info\s+\d+\s+(STF|STJ)$", item, flags=re.I)
    if not m:
        print(f"⚠️ Pulando {pdf.name}: não parece informativo STF/STJ.")
        return False

    tribunal = m.group(1).upper()
    md = PASTA_MD / f"{item}_limpo_estruturado.md"

    if not md.exists():
        print(f"❌ MD não encontrado: {md}")
        return False

    limpar_md(md)

    julgados = contar_julgados(md)
    print(f"\n📄 {item}: {julgados} julgado(s) no MD")

    if julgados == 0:
        print("❌ Abortado: nenhum julgado encontrado.")
        return False

    csv_path = criar_csv(item, tribunal, md, julgados)

    nome_saida_api(item).unlink(missing_ok=True)
    nome_saida_json_api(item).unlink(missing_ok=True)

    run([
        "python3", "gerar_questoes_pendentes_api_seguro_v2.py",
        "--pendencias", str(csv_path),
        "--categoria", "INFORMATIVO",
        "--item", item,
        "--sobrescrever",
        "--itens-por-lote", "1"
    ])

    saida = nome_saida_api(item)

    if not saida.exists():
        print("❌ Saída da API não encontrada.")
        return False

    questoes = contar_questoes(saida)
    print(f"🔎 Validação: julgados={julgados} | questões={questoes}")

    if questoes != julgados:
        print("🚨 BLOQUEADO: quantidade de questões diferente dos julgados.")
        return False

    destino = PASTA_QUESTOES / f"{item}_questoes.md"
    shutil.copy2(saida, destino)
    print(f"✅ Copiado para base final: {destino}")

    return True

def main():
    novos = pdfs_novos()

    if not novos:
        print("✅ Nenhum PDF novo encontrado.")
        return

    print("📚 PDFs novos detectados:")
    for p in novos:
        print("-", p.name)

    resp = input("\nConverter PDFs e gerar questões para todos? (s/N): ").strip().lower()
    if resp != "s":
        print("Cancelado.")
        return

    print("\n🔄 Convertendo PDFs para MD...")
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
            JSON_HTML.write_text(JSON_RAIZ.read_text(encoding="utf-8"), encoding="utf-8")
            print("✅ JSON copiado para html_final/data/questoes.json")

    print("\n📊 RESUMO")
    print("OK:", len(ok))
    for x in ok:
        print("  ✅", x)

    print("Falhas:", len(falhas))
    for x in falhas:
        print("  ❌", x)

    print("\nFinalizado. Suba para o GitHub manualmente depois de testar.")

if __name__ == "__main__":
    main()
