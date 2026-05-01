from pathlib import Path
import subprocess

ARQUIVO_LISTA = Path("data/pdfs_novos_detectados.txt")

def main():
    if not ARQUIVO_LISTA.exists():
        print("ℹ️ Nenhum PDF novo.")
        return

    pdfs = [l.strip() for l in ARQUIVO_LISTA.read_text().splitlines() if l.strip()]

    for pdf in pdfs:
        nome = Path(pdf).stem

        print(f"\n🚀 Gerando HTML para: {nome}")

        # chama seu gerador de HTML existente
        subprocess.run([
            "python3",
            "gerar_html_final_profissional_v4.py",  # 👈 ajuste se o nome for outro
            "--fonte", nome
        ])

    print("\n✅ HTMLs novos gerados.")

if __name__ == "__main__":
    main()
