from pathlib import Path
import argparse
import json
import re
from datetime import datetime

PASTA_PDFS = Path("pdfs")
PASTA_QUESTOES = Path("questoes_validadas_pdf")
PASTA_CONTROLE = Path("controle_processamento")
ARQ_CONTROLE = PASTA_CONTROLE / "pdfs_processados.json"

def normalizar_nome_pdf(pdf: Path) -> str:
    return pdf.stem.strip()

def caminho_questoes_esperado(pdf: Path) -> Path:
    base = normalizar_nome_pdf(pdf)
    return PASTA_QUESTOES / f"{base}_questoes.md"

def carregar_controle() -> dict:
    if not ARQ_CONTROLE.exists():
        return {}
    try:
        return json.loads(ARQ_CONTROLE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def salvar_controle(controle: dict):
    PASTA_CONTROLE.mkdir(exist_ok=True)
    ARQ_CONTROLE.write_text(json.dumps(controle, ensure_ascii=False, indent=2), encoding="utf-8")

def listar_pdfs():
    return sorted(PASTA_PDFS.glob("*.pdf"))

def identificar_pdfs_novos():
    controle = carregar_controle()
    novos = []
    for pdf in listar_pdfs():
        esperado = caminho_questoes_esperado(pdf)
        ja_tem_questoes = esperado.exists()
        ja_no_controle = controle.get(pdf.name, {}).get("status") == "OK"
        if not ja_tem_questoes and not ja_no_controle:
            novos.append(pdf)
    return novos

def categoria_item(pdf: Path):
    base = normalizar_nome_pdf(pdf)
    if re.search(r"\bInfo\s+\d+\s+(STF|STJ)\b", base, re.I):
        return "INFORMATIVO", base
    return "DESCONHECIDO", base

def imprimir_plano(novos):
    print("\nAUDITORIA DE PDFs NOVOS")
    print("=" * 60)
    print(f"Data/hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"PDFs na pasta: {len(listar_pdfs())}")
    print(f"PDFs novos detectados: {len(novos)}")
    print("")

    if not novos:
        print("✅ Nenhum PDF novo encontrado.")
        return

    print("PDFs novos:")
    for pdf in novos:
        cat, item = categoria_item(pdf)
        esperado = caminho_questoes_esperado(pdf)
        print(f"- {pdf.name}")
        print(f"  categoria: {cat}")
        print(f"  item: {item}")
        print(f"  esperado: {esperado}")
        print("")

    print("PLANO SEGURO SUGERIDO")
    print("=" * 60)
    print("1. Converter PDF novo para MD bruto/estruturado.")
    print("2. Auditar se todos os julgados foram extraídos.")
    print("3. Gerar questões pela API, uma por julgado.")
    print("4. Validar: sem DRY-RUN, sem gabarito vazio, sem explicação vazia.")
    print("5. Copiar arquivo validado para questoes_validadas_pdf/.")
    print("6. Rodar gerar_json_questoes_v4.py.")
    print("7. Copiar data/questoes.json para html_final/data/questoes.json, se necessário.")
    print("8. Rodar gerar_html_final_profissional_v4.py.")
    print("9. Reaplicar patches visuais/UX, se necessário.")
    print("10. Git add/commit/push dentro de html_final.")
    print("")

    print("COMANDOS PROVÁVEIS PARA GERAR QUESTÕES")
    print("=" * 60)
    for pdf in novos:
        cat, item = categoria_item(pdf)
        if cat == "INFORMATIVO":
            print(f'python3 gerar_questoes_pendentes_api_seguro_v2.py --categoria INFORMATIVO --item "{item}" --sobrescrever --itens-por-lote 1')

def marcar_ok():
    controle = carregar_controle()
    total = 0
    for pdf in listar_pdfs():
        esperado = caminho_questoes_esperado(pdf)
        if esperado.exists():
            controle[pdf.name] = {
                "status": "OK",
                "questoes": str(esperado),
                "atualizadoEm": datetime.now().isoformat()
            }
            total += 1
    salvar_controle(controle)
    print(f"✅ Controle atualizado: {ARQ_CONTROLE}")
    print(f"PDFs marcados como OK: {total}")

def main():
    parser = argparse.ArgumentParser(description="Detecta PDFs novos e monta plano seguro de atualização da base.")
    parser.add_argument("--dry-run", action="store_true", help="Só mostra o plano. Não altera nada.")
    parser.add_argument("--marcar-ok", action="store_true", help="Marca como OK PDFs que já possuem arquivo de questões correspondente.")
    args = parser.parse_args()

    if not PASTA_PDFS.exists():
        print(f"❌ Pasta não encontrada: {PASTA_PDFS}")
        return
    if not PASTA_QUESTOES.exists():
        print(f"❌ Pasta não encontrada: {PASTA_QUESTOES}")
        return

    if args.marcar_ok:
        marcar_ok()
        return

    novos = identificar_pdfs_novos()
    imprimir_plano(novos)

    if not args.dry_run:
        print("\n⚠️ Esta v1 é apenas auditoria/plano.")
        print("Use --dry-run para checar. Depois criaremos a v2 para executar etapas automaticamente.")

if __name__ == "__main__":
    main()
