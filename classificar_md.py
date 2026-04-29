from pathlib import Path
import shutil

PASTA_ENTRADA = Path("md_estruturado")

PASTA_OK = Path("ok")
PASTA_LEVE = Path("revisao_leve")
PASTA_CRITICA = Path("revisao_critica")

for pasta in [PASTA_OK, PASTA_LEVE, PASTA_CRITICA]:
    pasta.mkdir(exist_ok=True)


def classificar_arquivo(caminho: Path):
    texto = caminho.read_text(encoding="utf-8")

    tem_critica = "**Status:** Revisão crítica" in texto
    tem_leve = "**Status:** Revisão leve" in texto

    if tem_critica:
        destino = PASTA_CRITICA
        status = "revisao_critica"
    elif tem_leve:
        destino = PASTA_LEVE
        status = "revisao_leve"
    else:
        destino = PASTA_OK
        status = "ok"

    shutil.copy2(caminho, destino / caminho.name)

    return status


def main():
    arquivos = list(PASTA_ENTRADA.glob("*.md"))

    if not arquivos:
        print("Nenhum arquivo .md encontrado em md_estruturado.")
        return

    contagem = {
        "ok": 0,
        "revisao_leve": 0,
        "revisao_critica": 0,
    }

    for arquivo in arquivos:
        status = classificar_arquivo(arquivo)
        contagem[status] += 1
        print(f"{arquivo.name} -> {status}")

    print("\nResumo:")
    print(f"OK: {contagem['ok']}")
    print(f"Revisão leve: {contagem['revisao_leve']}")
    print(f"Revisão crítica: {contagem['revisao_critica']}")


if __name__ == "__main__":
    main()