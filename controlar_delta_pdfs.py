import json
import hashlib
from pathlib import Path
from datetime import datetime

PASTA_PDFS = Path("pdfs")  # ajuste se sua pasta for diferente
ARQUIVO_CONTROLE = Path("data/controle_pdfs_processados.json")


def calcular_hash(arquivo: Path):
    h = hashlib.md5()
    with arquivo.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def carregar_controle():
    if ARQUIVO_CONTROLE.exists():
        return json.loads(ARQUIVO_CONTROLE.read_text())
    return {}


def salvar_controle(dados):
    ARQUIVO_CONTROLE.parent.mkdir(exist_ok=True)
    ARQUIVO_CONTROLE.write_text(json.dumps(dados, indent=2))


def detectar_pdfs_novos():
    controle = carregar_controle()
    novos = []

    for pdf in PASTA_PDFS.glob("*.pdf"):
        nome = pdf.name
        hash_atual = calcular_hash(pdf)

        if nome not in controle:
            print(f"🆕 Novo: {nome}")
            novos.append(pdf)
        elif controle[nome]["hash"] != hash_atual:
            print(f"♻️ Alterado: {nome}")
            novos.append(pdf)

    return novos


def registrar_processados(pdfs):
    controle = carregar_controle()

    for pdf in pdfs:
        controle[pdf.name] = {
            "hash": calcular_hash(pdf),
            "processado_em": datetime.now().isoformat()
        }

    salvar_controle(controle)


if __name__ == "__main__":
    novos = detectar_pdfs_novos()

    if not novos:
        print("✅ Nenhum PDF novo.")
    else:
        print("\n📚 PDFs a processar:")
        for pdf in novos:
            print("-", pdf.name)

        # salva lista temporária
        Path("data/pdfs_novos_detectados.txt").write_text(
            "\n".join(str(p) for p in novos)
        )
