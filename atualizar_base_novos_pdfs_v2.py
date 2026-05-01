from pathlib import Path
import subprocess
import json
from datetime import datetime

PASTA_PDFS = Path("pdfs")
CONTROLE = Path("controle_processamento/pdfs_processados.json")

def run(cmd):
    print(f"\n🚀 Executando: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        raise Exception(f"❌ Erro ao executar: {cmd}")

def carregar_controle():
    if CONTROLE.exists():
        return json.loads(CONTROLE.read_text(encoding="utf-8"))
    return {}

def salvar_controle(ctrl):
    CONTROLE.parent.mkdir(exist_ok=True)
    CONTROLE.write_text(json.dumps(ctrl, indent=2, ensure_ascii=False), encoding="utf-8")

def detectar_novos():
    ctrl = carregar_controle()
    novos = []

    for pdf in PASTA_PDFS.glob("*.pdf"):
        if pdf.name not in ctrl:
            novos.append(pdf)

    return novos

def processar_pdf(pdf):
    nome = pdf.stem

    print(f"\n==============================")
    print(f"📄 PROCESSANDO: {nome}")
    print(f"==============================")

    # 1. Converter PDF → MD
    run("python3 converter_pdf_md.py")

    # 2. Gerar questões
    if "Info" in nome:
        cmd = f'python3 gerar_questoes_pendentes_api_seguro_v2.py --categoria INFORMATIVO --item "{nome}" --sobrescrever --itens-por-lote 1'
        run(cmd)
    else:
        print("⚠️ Tipo não automatizado (RG/Repetitivo/Súmulas). Pulei geração automática.")
        return False

    return True

def atualizar_site():
    print("\n🔄 Atualizando JSON...")
    run("python3 gerar_json_questoes_v4.py")

    print("\n🎨 Atualizando HTML...")
    run("python3 gerar_html_final_profissional_v4.py")

def git_push():
    print("\n🌐 Enviando para GitHub...")
    run("cd html_final && git add .")
    run('cd html_final && git commit -m "Atualização automática de informativos"')
    run("cd html_final && git push")

def main():
    novos = detectar_novos()

    if not novos:
        print("✅ Nenhum PDF novo encontrado.")
        return

    print(f"\n📊 PDFs novos detectados: {len(novos)}")
    for pdf in novos:
        print(f"- {pdf.name}")

    confirmar = input("\nDeseja processar automaticamente? (s/N): ").lower()
    if confirmar != "s":
        print("❌ Cancelado.")
        return

    ctrl = carregar_controle()

    for pdf in novos:
        try:
            ok = processar_pdf(pdf)

            if ok:
                ctrl[pdf.name] = {
                    "status": "OK",
                    "processadoEm": datetime.now().isoformat()
                }
            else:
                ctrl[pdf.name] = {
                    "status": "IGNORADO",
                    "processadoEm": datetime.now().isoformat()
                }

        except Exception as e:
            print(f"❌ Erro ao processar {pdf.name}: {e}")
            ctrl[pdf.name] = {
                "status": "ERRO",
                "erro": str(e),
                "processadoEm": datetime.now().isoformat()
            }

    salvar_controle(ctrl)

    atualizar_site()

    subir = input("\nDeseja enviar para o GitHub? (s/N): ").lower()
    if subir == "s":
        git_push()

    print("\n🏁 Processo finalizado.")

if __name__ == "__main__":
    main()
