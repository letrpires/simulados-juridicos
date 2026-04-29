import re
import html
from pathlib import Path

PASTA_ENTRADA = Path("teste_html")
PASTA_SAIDA = Path("html_simulados")

PASTA_SAIDA.mkdir(exist_ok=True)


def extrair_questoes(texto: str):
    partes = re.split(r"(?=^## Questão\s+\d+)", texto, flags=re.MULTILINE)
    return [p.strip() for p in partes if p.strip().startswith("## Questão")]


def limpar_markdown_basico(txt: str):
    # Remove ruídos comuns
    txt = re.sub(r"\*\*ODS:\*\*\s*.*?(?=\n\*\*|\n\n|$)", "", txt, flags=re.IGNORECASE | re.DOTALL)
    txt = re.sub(r"ODS\s*\d+(?:\s*,\s*\d+)*(?:\s*E\s*\d+)?", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"ODS:\s*.*", "", txt, flags=re.IGNORECASE)

    txt = re.sub(r"Observações de saneamento:.*?(?=\n\*\*|\n---|$)", "", txt, flags=re.IGNORECASE | re.DOTALL)
    txt = re.sub(r"\*\*Observações de saneamento:\*\*\s*.*?(?=\n\*\*|\n---|$)", "", txt, flags=re.IGNORECASE | re.DOTALL)

    txt = re.sub(r"Status:\s*Completo", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\*\*Status:\*\*\s*Completo", "", txt, flags=re.IGNORECASE)

    # Limpeza visual
    txt = re.sub(r"\n{3,}", "\n\n", txt)

    # Converter markdown básico para HTML
    txt = html.escape(txt)
    txt = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", txt)
    txt = txt.replace("\n", "<br>")

    return txt.strip()


def extrair_numero(bloco: str):
    m = re.search(r"## Questão\s+(\d+)", bloco)
    return m.group(1) if m else "?"


def extrair_gabarito(bloco: str):
    m = re.search(r"\*\*Gabarito:\*\*\s*(CERTO|ERRADO)", bloco, flags=re.IGNORECASE)
    return m.group(1).upper() if m else "N/I"


def extrair_enunciado(bloco: str):
    bloco = re.sub(r"^## Questão\s+\d+\s*", "", bloco).strip()
    partes = re.split(r"\*\*Gabarito:\*\*", bloco, maxsplit=1)
    return partes[0].strip()


def extrair_justificativa(bloco: str):
    m = re.search(
        r"\*\*Justificativa \(robusta\):\*\*\s*(.*?)(?=\n\*\*Referência:\*\*|\Z)",
        bloco,
        flags=re.DOTALL,
    )
    return m.group(1).strip() if m else "N/I"


def extrair_referencia(bloco: str):
    m = re.search(r"\*\*Referência:\*\*\s*(.*?)(?=\n---|\Z)", bloco, flags=re.DOTALL)
    return m.group(1).strip() if m else "N/I"


def gerar_html(nome_simulado: str, questoes: list):
    questoes_html = []

    for i, bloco in enumerate(questoes, start=1):
        numero = extrair_numero(bloco)
        gabarito = extrair_gabarito(bloco)
        enunciado = limpar_markdown_basico(extrair_enunciado(bloco))
        justificativa = limpar_markdown_basico(extrair_justificativa(bloco))
        referencia = limpar_markdown_basico(extrair_referencia(bloco))

        questoes_html.append(f"""
        <section class="card questao" data-gabarito="{gabarito}">
            <div class="questao-topo">
                <span class="badge">Questão {numero}</span>
                <span class="status" id="status-{i}">Não respondida</span>
            </div>

            <p class="enunciado">{enunciado}</p>

            <div class="botoes">
                <button onclick="responder({i}, 'CERTO')">CERTO</button>
                <button onclick="responder({i}, 'ERRADO')">ERRADO</button>
            </div>

            <div class="feedback" id="feedback-{i}">
                <p class="resultado"></p>
                <p><strong>Gabarito:</strong> {gabarito}</p>
                <p><strong>Justificativa:</strong><br>{justificativa}</p>
                <p class="referencia"><strong>Referência:</strong><br>{referencia}</p>
            </div>
        </section>
        """)

    total = len(questoes)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>{html.escape(nome_simulado)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
:root {{
    --bg: #0f172a;
    --card: #111827;
    --card2: #1f2937;
    --text: #e5e7eb;
    --muted: #9ca3af;
    --accent: #38bdf8;
    --green: #22c55e;
    --red: #ef4444;
    --yellow: #facc15;
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: linear-gradient(135deg, #020617, #111827);
    color: var(--text);
    line-height: 1.6;
}}

header {{
    padding: 32px 20px;
    text-align: center;
    border-bottom: 1px solid #334155;
}}

header h1 {{
    margin: 0 0 10px;
    font-size: 28px;
}}

header p {{
    color: var(--muted);
    margin: 0;
}}

.container {{
    max-width: 980px;
    margin: 0 auto;
    padding: 24px 16px 80px;
}}

.painel {{
    position: sticky;
    top: 0;
    z-index: 10;
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(8px);
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 24px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}}

.stat {{
    background: var(--card2);
    padding: 12px;
    border-radius: 12px;
    text-align: center;
}}

.stat strong {{
    display: block;
    font-size: 22px;
    color: var(--accent);
}}

.card {{
    background: rgba(17, 24, 39, 0.96);
    border: 1px solid #334155;
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 20px;
    box-shadow: 0 12px 30px rgba(0,0,0,.25);
}}

.questao-topo {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
    margin-bottom: 16px;
}}

.badge {{
    background: #0ea5e9;
    color: #00111f;
    font-weight: bold;
    padding: 6px 12px;
    border-radius: 999px;
}}

.status {{
    color: var(--muted);
    font-size: 14px;
}}

.enunciado {{
    font-size: 18px;
    margin-bottom: 20px;
}}

.botoes {{
    display: flex;
    gap: 12px;
    margin-bottom: 18px;
}}

button {{
    cursor: pointer;
    border: 0;
    padding: 12px 22px;
    border-radius: 12px;
    background: #334155;
    color: white;
    font-weight: bold;
    transition: 0.2s;
}}

button:hover {{
    transform: translateY(-1px);
    background: #475569;
}}

.feedback {{
    display: none;
    background: #020617;
    border-left: 4px solid var(--accent);
    padding: 16px;
    border-radius: 12px;
    margin-top: 12px;
}}

.feedback.correto {{
    border-left-color: var(--green);
}}

.feedback.errado {{
    border-left-color: var(--red);
}}

.resultado {{
    font-size: 18px;
    font-weight: bold;
}}

.referencia {{
    color: var(--muted);
    font-size: 14px;
}}

.acoes {{
    text-align: center;
    margin: 30px 0;
}}

.acoes button {{
    background: #0ea5e9;
    color: #00111f;
}}

@media (max-width: 700px) {{
    .painel {{
        grid-template-columns: repeat(2, 1fr);
    }}

    .botoes {{
        flex-direction: column;
    }}

    header h1 {{
        font-size: 22px;
    }}

    .enunciado {{
        font-size: 16px;
    }}
}}
</style>
</head>

<body>

<header>
    <h1>{html.escape(nome_simulado)}</h1>
    <p>Simulado interativo de CERTO ou ERRADO</p>
</header>

<div class="container">

    <div class="painel">
        <div class="stat">
            <strong id="total">{total}</strong>
            Total
        </div>
        <div class="stat">
            <strong id="respondidas">0</strong>
            Respondidas
        </div>
        <div class="stat">
            <strong id="acertos">0</strong>
            Acertos
        </div>
        <div class="stat">
            <strong id="erros">0</strong>
            Erros
        </div>
    </div>

    <div class="acoes">
        <button onclick="reiniciar()">Reiniciar simulado</button>
    </div>

    {"".join(questoes_html)}

</div>

<script>
const totalQuestoes = {total};
let respostas = JSON.parse(localStorage.getItem(location.pathname + "_respostas") || "{{}}");

function atualizarPainel() {{
    const respondidas = Object.keys(respostas).length;
    let acertos = 0;
    let erros = 0;

    for (const key in respostas) {{
        if (respostas[key].correto) acertos++;
        else erros++;
    }}

    document.getElementById("respondidas").textContent = respondidas;
    document.getElementById("acertos").textContent = acertos;
    document.getElementById("erros").textContent = erros;
}}

function responder(numero, resposta) {{
    const card = document.querySelectorAll(".questao")[numero - 1];
    const gabarito = card.dataset.gabarito;
    const correto = resposta === gabarito;

    respostas[numero] = {{
        resposta,
        correto
    }};

    localStorage.setItem(location.pathname + "_respostas", JSON.stringify(respostas));

    mostrarFeedback(numero);
    atualizarPainel();
}}

function mostrarFeedback(numero) {{
    const card = document.querySelectorAll(".questao")[numero - 1];
    const feedback = document.getElementById("feedback-" + numero);
    const status = document.getElementById("status-" + numero);
    const resultado = feedback.querySelector(".resultado");

    const dados = respostas[numero];

    if (!dados) return;

    feedback.style.display = "block";
    feedback.classList.remove("correto", "errado");

    if (dados.correto) {{
        feedback.classList.add("correto");
        resultado.textContent = "Você acertou. A resposta é " + card.dataset.gabarito + ".";
        status.textContent = "Respondida — acerto";
        status.style.color = "var(--green)";
    }} else {{
        feedback.classList.add("errado");
        resultado.textContent = "Você errou. O gabarito é " + card.dataset.gabarito + ".";
        status.textContent = "Respondida — erro";
        status.style.color = "var(--red)";
    }}
}}

function restaurar() {{
    for (const key in respostas) {{
        mostrarFeedback(Number(key));
    }}
    atualizarPainel();
}}

function reiniciar() {{
    if (!confirm("Deseja reiniciar este simulado?")) return;
    localStorage.removeItem(location.pathname + "_respostas");
    location.reload();
}}

restaurar();
</script>

</body>
</html>
"""


def processar_arquivo(caminho: Path):
    texto = caminho.read_text(encoding="utf-8")
    questoes = extrair_questoes(texto)

    if not questoes:
        print(f"⚠️ Nenhuma questão encontrada em {caminho.name}")
        return

    nome_base = caminho.stem.replace("_questoes", "")
    html_final = gerar_html(f"Simulado - {nome_base}", questoes)

    saida = PASTA_SAIDA / f"{nome_base}.html"
    saida.write_text(html_final, encoding="utf-8")

    print(f"✅ HTML gerado: {saida}")


def gerar_index():
    arquivos_html = sorted(PASTA_SAIDA.glob("*.html"))

    links = []
    for arq in arquivos_html:
        if arq.name == "index.html":
            continue
        nome = arq.stem
        links.append(f'<a class="link" href="{arq.name}">{html.escape(nome)}</a>')

    index = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Simulados de Jurisprudência</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body {{
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: linear-gradient(135deg, #020617, #111827);
    color: #e5e7eb;
}}
.container {{
    max-width: 900px;
    margin: 0 auto;
    padding: 32px 16px;
}}
h1 {{
    text-align: center;
    margin-bottom: 10px;
}}
p {{
    text-align: center;
    color: #9ca3af;
    margin-bottom: 32px;
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 14px;
}}
.link {{
    display: block;
    padding: 18px;
    background: #111827;
    border: 1px solid #334155;
    color: #e5e7eb;
    border-radius: 14px;
    text-decoration: none;
    transition: .2s;
}}
.link:hover {{
    transform: translateY(-2px);
    border-color: #38bdf8;
}}
</style>
</head>
<body>
<div class="container">
<h1>Simulados de Jurisprudência</h1>
<p>Escolha um informativo para iniciar.</p>
<div class="grid">
{''.join(links)}
</div>
</div>
</body>
</html>
"""

    (PASTA_SAIDA / "index.html").write_text(index, encoding="utf-8")
    print("✅ index.html gerado.")


def main():
    arquivos = sorted(PASTA_ENTRADA.glob("*.md"))

    if not arquivos:
        print("❌ Nenhum arquivo .md encontrado em questoes_geradas_ok.")
        return

    print(f"📚 Arquivos encontrados: {len(arquivos)}")

    for arquivo in arquivos:
        processar_arquivo(arquivo)

    gerar_index()

    print("\n🎯 Finalizado.")
    print(f"Abra: {PASTA_SAIDA / 'index.html'}")


if __name__ == "__main__":
    main()