import re
import html
from pathlib import Path

PASTA_ENTRADA = Path("questoes_validadas_pdf")
PASTA_SAIDA = Path("html_simulados")

PASTA_SAIDA.mkdir(exist_ok=True)


def extrair_questoes(texto: str):
    partes = re.split(r"(?=^## Questão\s+\d+)", texto, flags=re.MULTILINE)
    return [p.strip() for p in partes if p.strip().startswith("## Questão")]


def limpar_ruidos(txt: str):
    txt = re.sub(r"\*\*ODS:\*\*\s*.*?(?=\n\*\*|\n\n|$)", "", txt, flags=re.IGNORECASE | re.DOTALL)
    txt = re.sub(r"ODS\s*\d+(?:\s*,\s*\d+)*(?:\s*E\s*\d+)?", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"ODS:\s*.*", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\*\*Observações de saneamento:\*\*\s*.*?(?=\n\*\*|\n---|$)", "", txt, flags=re.IGNORECASE | re.DOTALL)
    txt = re.sub(r"\*\*Status:\*\*\s*Completo", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


def markdown_para_html(txt: str):
    txt = limpar_ruidos(txt)
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
    if not m:
        m = re.search(
            r"\*\*Justificativa:\*\*\s*(.*?)(?=\n\*\*Referência:\*\*|\Z)",
            bloco,
            flags=re.DOTALL,
        )
    return m.group(1).strip() if m else "N/I"


def extrair_referencia(bloco: str):
    m = re.search(r"\*\*Referência:\*\*\s*(.*?)(?=\n---|\Z)", bloco, flags=re.DOTALL)
    return m.group(1).strip() if m else "N/I"


def extrair_disciplina_do_bloco(bloco: str):
    texto = extrair_justificativa(bloco) + "\n" + extrair_referencia(bloco) + "\n" + bloco

    disciplinas = [
        "Direito Constitucional",
        "Direito Administrativo",
        "Direito Civil",
        "Direito Processual Civil",
        "Direito Penal",
        "Direito Processual Penal",
        "Direito Tributário",
        "Direito Empresarial",
        "Direito Ambiental",
        "Direito Previdenciário",
        "Direito do Consumidor",
        "Direito Do Consumidor",
        "Direito Eleitoral",
        "Direito do Trabalho",
        "Direito Do Trabalho",
        "Direito Financeiro",
        "Direito Internacional",
        "Direito Notarial e Registral",
        "ECA",
        "Eca",
    ]

    for d in disciplinas:
        if re.search(re.escape(d), texto, flags=re.IGNORECASE):
            return d.replace("Do", "do")

    return "N/I"


def gerar_html(nome_simulado: str, questoes: list):
    questoes_html = []
    disciplinas = set()

    for i, bloco in enumerate(questoes, start=1):
        numero = extrair_numero(bloco)
        gabarito = extrair_gabarito(bloco)
        enunciado_raw = extrair_enunciado(bloco)
        justificativa_raw = extrair_justificativa(bloco)
        referencia_raw = extrair_referencia(bloco)
        disciplina = extrair_disciplina_do_bloco(bloco)

        disciplinas.add(disciplina)

        enunciado = markdown_para_html(enunciado_raw)
        justificativa = markdown_para_html(justificativa_raw)
        referencia = markdown_para_html(referencia_raw)

        questoes_html.append(f"""
        <section class="card questao" 
            data-gabarito="{gabarito}" 
            data-disciplina="{html.escape(disciplina)}"
            data-texto="{html.escape((enunciado_raw + ' ' + justificativa_raw + ' ' + referencia_raw).lower())}">
            
            <div class="questao-topo">
                <div>
                    <span class="badge">Questão {numero}</span>
                    <span class="disciplina-tag">{html.escape(disciplina)}</span>
                </div>
                <span class="status" id="status-{i}">Não respondida</span>
            </div>

            <p class="enunciado">{enunciado}</p>

            <div class="botoes">
                <button class="btn certo" onclick="responder({i}, 'CERTO')">CERTO</button>
                <button class="btn errado" onclick="responder({i}, 'ERRADO')">ERRADO</button>
            </div>

            <div class="feedback" id="feedback-{i}">
                <p class="resultado"></p>
                <p><strong>Gabarito:</strong> <span class="gabarito-texto">{gabarito}</span></p>
                <div class="justificativa"><strong>Justificativa:</strong><br>{justificativa}</div>
                <p class="referencia"><strong>Referência:</strong><br>{referencia}</p>
            </div>
        </section>
        """)

    total = len(questoes)
    opcoes_disciplinas = "\n".join(
        f'<option value="{html.escape(d)}">{html.escape(d)}</option>'
        for d in sorted(disciplinas)
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>{html.escape(nome_simulado)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
:root {{
    --bg: #020617;
    --panel: rgba(15, 23, 42, 0.88);
    --card: rgba(15, 23, 42, 0.96);
    --card2: rgba(30, 41, 59, 0.92);
    --border: rgba(148, 163, 184, 0.22);
    --text: #e5e7eb;
    --muted: #94a3b8;
    --accent: #38bdf8;
    --accent2: #0ea5e9;
    --green: #22c55e;
    --red: #ef4444;
    --yellow: #facc15;
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    background:
        radial-gradient(circle at top left, rgba(56,189,248,.18), transparent 28%),
        radial-gradient(circle at top right, rgba(34,197,94,.09), transparent 25%),
        linear-gradient(135deg, #020617, #0f172a 48%, #020617);
    color: var(--text);
    line-height: 1.65;
}}

header {{
    padding: 42px 20px 34px;
    text-align: center;
    border-bottom: 1px solid var(--border);
}}

header h1 {{
    margin: 0 0 10px;
    font-size: clamp(28px, 4vw, 44px);
    letter-spacing: -0.04em;
}}

header p {{
    color: var(--muted);
    margin: 0;
    font-size: 17px;
}}

.container {{
    max-width: 1120px;
    margin: 0 auto;
    padding: 26px 16px 80px;
}}

.painel {{
    position: sticky;
    top: 12px;
    z-index: 20;
    background: var(--panel);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 16px;
    margin-bottom: 22px;
    box-shadow: 0 20px 60px rgba(0,0,0,.32);
}}

.stats {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}}

.stat {{
    background: var(--card2);
    padding: 14px;
    border-radius: 18px;
    text-align: center;
    border: 1px solid rgba(148,163,184,.12);
}}

.stat strong {{
    display: block;
    font-size: 26px;
    color: var(--accent);
    line-height: 1.1;
}}

.stat span {{
    color: var(--text);
    font-size: 13px;
}}

.filtros {{
    display: grid;
    grid-template-columns: 1.2fr 1fr auto;
    gap: 12px;
    margin-top: 14px;
}}

input, select {{
    width: 100%;
    background: rgba(2, 6, 23, 0.78);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 13px 14px;
    outline: none;
    font-size: 14px;
}}

input:focus, select:focus {{
    border-color: var(--accent);
}}

.card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 26px;
    margin-bottom: 20px;
    box-shadow: 0 18px 50px rgba(0,0,0,.24);
}}

.questao {{
    scroll-margin-top: 180px;
}}

.questao-topo {{
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
    margin-bottom: 18px;
}}

.badge {{
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color: #00111f;
    font-weight: 800;
    padding: 7px 13px;
    border-radius: 999px;
    display: inline-block;
}}

.disciplina-tag {{
    display: inline-block;
    margin-left: 8px;
    color: var(--muted);
    background: rgba(148, 163, 184, .1);
    border: 1px solid rgba(148, 163, 184, .14);
    padding: 6px 10px;
    border-radius: 999px;
    font-size: 12px;
}}

.status {{
    color: var(--yellow);
    font-size: 13px;
    white-space: nowrap;
}}

.enunciado {{
    font-size: 19px;
    margin: 0 0 22px;
    letter-spacing: -0.01em;
}}

.botoes {{
    display: flex;
    gap: 12px;
    margin-bottom: 18px;
}}

.btn {{
    cursor: pointer;
    border: 0;
    padding: 12px 24px;
    border-radius: 14px;
    color: white;
    font-weight: 800;
    transition: .18s ease;
    letter-spacing: .02em;
}}

.btn:hover {{
    transform: translateY(-2px);
    filter: brightness(1.08);
}}

.btn.certo {{
    background: rgba(34, 197, 94, .20);
    border: 1px solid rgba(34, 197, 94, .42);
}}

.btn.errado {{
    background: rgba(239, 68, 68, .20);
    border: 1px solid rgba(239, 68, 68, .42);
}}

.btn.neutro {{
    background: rgba(56, 189, 248, .16);
    color: var(--text);
    border: 1px solid rgba(56, 189, 248, .32);
}}

.feedback {{
    display: none;
    background: rgba(2, 6, 23, .72);
    border: 1px solid rgba(148, 163, 184, .16);
    border-left: 5px solid var(--accent);
    padding: 18px;
    border-radius: 18px;
    margin-top: 14px;
}}

.feedback.correto {{
    border-left-color: var(--green);
}}

.feedback.errado {{
    border-left-color: var(--red);
}}

.resultado {{
    font-size: 18px;
    font-weight: 900;
    margin-top: 0;
}}

.justificativa {{
    margin-top: 12px;
}}

.referencia {{
    color: var(--muted);
    font-size: 13px;
    margin-top: 16px;
}}

.gabarito-certo {{
    color: var(--green);
    font-weight: 900;
}}

.gabarito-errado {{
    color: var(--red);
    font-weight: 900;
}}

.acoes {{
    text-align: center;
    margin: 26px 0;
}}

.oculta {{
    display: none;
}}

.sem-resultados {{
    text-align: center;
    color: var(--muted);
    display: none;
    padding: 30px;
}}

@media (max-width: 780px) {{
    .stats {{
        grid-template-columns: repeat(2, 1fr);
    }}

    .filtros {{
        grid-template-columns: 1fr;
    }}

    .questao-topo {{
        align-items: flex-start;
        flex-direction: column;
    }}

    .botoes {{
        flex-direction: column;
    }}

    .enunciado {{
        font-size: 16px;
    }}

    .card {{
        padding: 20px;
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
        <div class="stats">
            <div class="stat"><strong id="total">{total}</strong><span>Total</span></div>
            <div class="stat"><strong id="visiveis">{total}</strong><span>Visíveis</span></div>
            <div class="stat"><strong id="respondidas">0</strong><span>Respondidas</span></div>
            <div class="stat"><strong id="acertos">0</strong><span>Acertos</span></div>
        </div>

        <div class="filtros">
            <input id="busca" type="search" placeholder="Buscar por palavra-chave..." oninput="filtrar()">
            <select id="disciplina" onchange="filtrar()">
                <option value="">Todas as disciplinas</option>
                {opcoes_disciplinas}
            </select>
            <button class="btn neutro" onclick="reiniciar()">Reiniciar</button>
        </div>
    </div>

    <div id="sem-resultados" class="sem-resultados">
        Nenhuma questão encontrada com os filtros atuais.
    </div>

    {"".join(questoes_html)}

</div>

<script>
const totalQuestoes = {total};
let respostas = JSON.parse(localStorage.getItem(location.pathname + "_respostas") || "{{}}");

function atualizarPainel() {{
    const cards = Array.from(document.querySelectorAll(".questao"));
    const visiveis = cards.filter(c => !c.classList.contains("oculta")).length;

    let respondidas = 0;
    let acertos = 0;

    for (const key in respostas) {{
        respondidas++;
        if (respostas[key].correto) acertos++;
    }}

    document.getElementById("visiveis").textContent = visiveis;
    document.getElementById("respondidas").textContent = respondidas;
    document.getElementById("acertos").textContent = acertos;
}}

function responder(numero, resposta) {{
    const card = document.querySelectorAll(".questao")[numero - 1];
    const gabarito = card.dataset.gabarito;
    const correto = resposta === gabarito;

    respostas[numero] = {{ resposta, correto }};
    localStorage.setItem(location.pathname + "_respostas", JSON.stringify(respostas));

    mostrarFeedback(numero);
    atualizarPainel();
}}

function destacarGabarito(texto) {{
    if (texto === "CERTO") return '<span class="gabarito-certo">CERTO</span>';
    if (texto === "ERRADO") return '<span class="gabarito-errado">ERRADO</span>';
    return texto;
}}

function mostrarFeedback(numero) {{
    const card = document.querySelectorAll(".questao")[numero - 1];
    const feedback = document.getElementById("feedback-" + numero);
    const status = document.getElementById("status-" + numero);
    const resultado = feedback.querySelector(".resultado");
    const gabarito = card.dataset.gabarito;
    const dados = respostas[numero];

    if (!dados) return;

    feedback.style.display = "block";
    feedback.classList.remove("correto", "errado");

    if (dados.correto) {{
        feedback.classList.add("correto");
        resultado.innerHTML = "Você acertou. A resposta é " + destacarGabarito(gabarito) + ".";
        status.textContent = "Respondida — acerto";
        status.style.color = "var(--green)";
    }} else {{
        feedback.classList.add("errado");
        resultado.innerHTML = "Você errou. O gabarito é " + destacarGabarito(gabarito) + ".";
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

function filtrar() {{
    const busca = document.getElementById("busca").value.trim().toLowerCase();
    const disciplina = document.getElementById("disciplina").value;
    const cards = Array.from(document.querySelectorAll(".questao"));

    let visiveis = 0;

    cards.forEach(card => {{
        const texto = card.dataset.texto || "";
        const disc = card.dataset.disciplina || "";

        const passaBusca = !busca || texto.includes(busca);
        const passaDisciplina = !disciplina || disc === disciplina;

        if (passaBusca && passaDisciplina) {{
            card.classList.remove("oculta");
            visiveis++;
        }} else {{
            card.classList.add("oculta");
        }}
    }});

    document.getElementById("sem-resultados").style.display = visiveis === 0 ? "block" : "none";
    atualizarPainel();
}}

restaurar();
filtrar();
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
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    background:
        radial-gradient(circle at top left, rgba(56,189,248,.18), transparent 28%),
        linear-gradient(135deg, #020617, #0f172a 48%, #020617);
    color: #e5e7eb;
}}
.container {{
    max-width: 1000px;
    margin: 0 auto;
    padding: 38px 16px;
}}
h1 {{
    text-align: center;
    margin-bottom: 8px;
    font-size: 42px;
    letter-spacing: -0.04em;
}}
p {{
    text-align: center;
    color: #94a3b8;
    margin-bottom: 34px;
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 14px;
}}
.link {{
    display: block;
    padding: 20px;
    background: rgba(15,23,42,.95);
    border: 1px solid rgba(148,163,184,.22);
    color: #e5e7eb;
    border-radius: 20px;
    text-decoration: none;
    transition: .2s;
    box-shadow: 0 14px 40px rgba(0,0,0,.22);
}}
.link:hover {{
    transform: translateY(-3px);
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
        print(f"❌ Nenhum arquivo .md encontrado em {PASTA_ENTRADA}.")
        return

    print(f"📚 Arquivos encontrados: {len(arquivos)}")

    for arquivo in arquivos:
        processar_arquivo(arquivo)

    gerar_index()

    print("\n🎯 Finalizado.")
    print(f"Abra: {PASTA_SAIDA / 'index.html'}")


if __name__ == "__main__":
    main()