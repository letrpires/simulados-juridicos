from pathlib import Path
import argparse
import re
from datetime import datetime


def ler_blocos_sumulas(texto: str):
    # Espera blocos no formato: ## Súmula STF 1\n\n**Enunciado:**\n...
    pattern = re.compile(r"(?ms)^##\s*S[uú]mula\s+STF\s+(\d+)\s*\n(.*?)(?=^##\s*S[uú]mula\s+STF\s+\d+\s*\n|\Z)")
    blocos = []
    for m in pattern.finditer(texto):
        numero = int(m.group(1))
        conteudo = m.group(0).strip()
        if "**Enunciado:**" not in conteudo:
            continue
        blocos.append((numero, conteudo))
    return blocos


def main():
    parser = argparse.ArgumentParser(description="Divide sumula_stf.md em blocos menores para geração segura por API.")
    parser.add_argument("--arquivo", default="sumulas_extraidas_md/sumula_stf.md", help="Arquivo base de súmulas STF")
    parser.add_argument("--tamanho", type=int, default=50, help="Quantidade de súmulas por bloco")
    parser.add_argument("--saida", default="sumulas_extraidas_md/blocos_stf", help="Pasta de saída dos blocos")
    args = parser.parse_args()

    entrada = Path(args.arquivo)
    if not entrada.exists():
        raise SystemExit(f"ERRO: arquivo não encontrado: {entrada}")

    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    texto = entrada.read_text(encoding="utf-8", errors="ignore")
    blocos = ler_blocos_sumulas(texto)

    if not blocos:
        raise SystemExit("ERRO: nenhuma súmula STF foi encontrada no padrão esperado.")

    # Limpa blocos antigos gerados por este script
    for antigo in saida.glob("sumula_stf_bloco_*.md"):
        antigo.unlink()

    arquivos = []
    for idx in range(0, len(blocos), args.tamanho):
        pedaco = blocos[idx: idx + args.tamanho]
        primeiro = pedaco[0][0]
        ultimo = pedaco[-1][0]
        n_bloco = idx // args.tamanho + 1
        nome = saida / f"sumula_stf_bloco_{n_bloco:03d}_{primeiro:03d}_a_{ultimo:03d}.md"
        conteudo = (
            f"# Súmulas STF — Bloco {n_bloco:03d}\n\n"
            f"**Arquivo de origem:** `{entrada}`\n"
            f"**Faixa:** Súmulas {primeiro} a {ultimo}\n"
            f"**Total no bloco:** {len(pedaco)}\n\n"
            "---\n\n"
            + "\n\n---\n\n".join(c for _, c in pedaco)
            + "\n"
        )
        nome.write_text(conteudo, encoding="utf-8")
        arquivos.append(nome)

    relatorio = saida / f"relatorio_blocos_stf_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md"
    linhas = [
        "# Relatório de divisão das Súmulas STF em blocos",
        "",
        f"Arquivo de origem: `{entrada}`",
        f"Súmulas encontradas: **{len(blocos)}**",
        f"Tamanho do bloco: **{args.tamanho}**",
        f"Blocos gerados: **{len(arquivos)}**",
        "",
        "| Bloco | Arquivo | Quantidade |",
        "|---:|---|---:|",
    ]
    for i, arq in enumerate(arquivos, 1):
        qtd = len(ler_blocos_sumulas(arq.read_text(encoding="utf-8", errors="ignore")))
        linhas.append(f"| {i} | `{arq}` | {qtd} |")
    relatorio.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    print(f"Súmulas encontradas: {len(blocos)}")
    print(f"Blocos gerados: {len(arquivos)}")
    print(f"Pasta: {saida}")
    print(f"Relatório: {relatorio}")
    print("\nPróximo passo: rode o gerador de questões em cada bloco.")


if __name__ == "__main__":
    main()
