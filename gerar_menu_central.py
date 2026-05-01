from pathlib import Path
import re
from collections import defaultdict

PASTA_SIMULADOS = Path("html_final/simulados")
ARQUIVO_SAIDA = Path("html_final/menu.html")


def titulo_amigavel(nome: str) -> str:
    nome = nome.replace(".html", "")
    nome = nome.replace("-", " ")
    return nome.title().replace("Stf", "STF").replace("Stj", "STJ")


def grupo_do_arquivo(nome: str) -> str:
    n = nome.lower()

    if "stf" in n:
        return "Informativos STF"
    if "stj" in n:
        return "Informativos STJ"
    if "repetitivo" in n:
        return "Repetitivos"
    if "rg" in n:
        return "Repercussão Geral"
    if "sumula" in n or "súmula" in n:
        return "Súmulas"

    return "Outros"


def main():
    PASTA_SIMULADOS.mkdir(parents=True, exist_ok=True)

    arquivos = sorted(PASTA_SIMULADOS.glob("*.html"))

    grupos = defaultdict(list)

    for arq in arquivos:
        grupos[grupo_do_arquivo(arq.name)].append(arq)

    blocos = []

    for grupo in sorted(grupos):
        links = []
        for arq in grupos[grupo]:
            links.append(
                f'<a class="card" href="simulados/{arq.name}">{titulo_amigavel(arq.name)}</a>'
            )

        blocos.append(f"""
        <section>
            <h2>{grupo}</h2>
            <div class="grid">
                {''.join(links)}
            </div>
        </section>
        """)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Central de Simulados</title>
    <style>
        body {{
            margin: 0;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f7f3ed;
            color: #1f2937;
        }}

        header {{
            padding: 40px 28px;
            background: #fffaf3;
            border-bottom: 1px solid #e5ded4;
        }}

        h1 {{
            margin: 0;
            font-size: 2.2rem;
        }}

        p {{
            color: #6b7280;
            font-size: 1.05rem;
        }}

        main {{
            padding: 28px;
            max-width: 1200px;
            margin: auto;
        }}

        section {{
            margin-bottom: 36px;
        }}

        h2 {{
            font-size: 1.4rem;
            margin-bottom: 16px;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 14px;
        }}

        .card {{
            display: block;
            text-decoration: none;
            background: white;
            color: #111827;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 18px;
            font-weight: 700;
            box-shadow: 0 8px 20px rgba(0,0,0,.04);
        }}

        .card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 12px 26px rgba(0,0,0,.08);
        }}
    </style>
</head>
<body>
    <header>
        <h1>Central de Simulados</h1>
        <p>Escolha um caderno para resolver questões por informativo, súmula, repercussão geral ou repetitivo.</p>
    </header>

    <main>
        {''.join(blocos) if blocos else '<p>Nenhum simulado individual encontrado ainda.</p>'}
    </main>
</body>
</html>
"""

    ARQUIVO_SAIDA.write_text(html, encoding="utf-8")
    print(f"✅ Menu central gerado: {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()
