from pathlib import Path
import subprocess
import shutil
from datetime import datetime

# ==============================
# CONFIGURAÇÕES
# ==============================

BASE_DIR = Path.cwd()

SCRIPTS = {
    "renomear": "renomear_pdfs_automatico_v3.py",
    "gerar_md": None,  # se tiver script, coloca aqui depois
    "gerar_questoes": "gerar_questoes_pendentes_api_seguro_v2.py",
    "gerar_json": "gerar_json_questoes_v4.py",
}

JSON_ORIGEM = BASE_DIR / "data/questoes.json"
JSON_DESTINO = BASE_DIR / "html_final/data/questoes.json"

LOG_DIR = BASE_DIR / "logs_pipeline"
LOG_DIR.mkdir(exist_ok=True)


# ==============================
# UTIL
# ==============================

def run(nome, comando):
    print(f"\n🚀 [{nome}] Executando...\n")
    resultado = subprocess.run(comando)

    if resultado.returncode != 0:
        print(f"\n❌ ERRO na etapa: {nome}")
        raise SystemExit(1)

    print(f"\n✅ [{nome}] Concluído\n")


def log(msg):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_DIR / "pipeline.log", "a", encoding="utf-8") as f:
        f.write(f"[{agora}] {msg}\n")


# ==============================
# PIPELINE
# ==============================

def main():
    print("\n==============================")
    print("🔥 PIPELINE TOTAL INICIADO")
    print("==============================\n")

    log("Início do pipeline")

    # 1. RENOMEAR PDFs
    if SCRIPTS["renomear"]:
        run("Renomear PDFs", ["python3", SCRIPTS["renomear"]])
        log("PDFs renomeados")

    # 2. GERAR MD (se existir)
    if SCRIPTS["gerar_md"]:
        run("Gerar MD", ["python3", SCRIPTS["gerar_md"]])
        log("MDs gerados")

    # 3. GERAR QUESTÕES
    if SCRIPTS["gerar_questoes"]:
        run("Gerar questões", ["python3", SCRIPTS["gerar_questoes"]])
        log("Questões geradas")

    # 4. GERAR JSON FINAL
    run("Gerar JSON consolidado", ["python3", SCRIPTS["gerar_json"]])
    log("JSON gerado")

    # 5. COPIAR PARA HTML
    if JSON_ORIGEM.exists():
        shutil.copy(JSON_ORIGEM, JSON_DESTINO)
        print("📦 JSON atualizado no HTML")
        log("JSON copiado para HTML")
    else:
        print("⚠️ JSON não encontrado para cópia")

    print("\n==============================")
    print("✅ PIPELINE FINALIZADO")
    print("==============================\n")

    log("Pipeline finalizado com sucesso")


if __name__ == "__main__":
    main()
