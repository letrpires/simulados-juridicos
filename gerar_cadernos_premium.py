import re
import html
import shutil
from pathlib import Path

PASTA_QUESTOES = Path("questoes_validadas_pdf")
PASTA_DOCS = Path("docs")
PASTA_DOCS.mkdir(exist_ok=True)

# =========================
# CONFIGURAÇÃO DOS CADERNOS
# =========================

CADERNOS = [
    {
        "arquivo": "stf-2025.html",
        "titulo": "Simulado STF",
        "subtitulo": "Informativos 1162 - 1202 • CERTO ou ERRADO",
        "cor": "#c084fc",
        "tipo": "STF 2025",
        "filtro": lambda nome: "STF" in nome and extrair_info(nome) and 1162 <= extrair_info(nome) <= 1202,
    },
    {
        "arquivo": "stf-2026.html",
        "titulo": "Simulado STF",
        "subtitulo": "Informativos 1203 - 1212 • CERTO ou ERRADO",
        "cor": "#c084fc",
        "tipo": "STF 2026",
        "filtro": lambda nome: "STF" in nome and extrair_info(nome) and 1203 <= extrair_info(nome) <= 1212,
    },
    {
        "arquivo": "stj-2025.html",
        "titulo": "Simulado STJ",
        "subtitulo": "Informativos 835 - 874 • CERTO ou ERRADO",
        "cor": "#facc15",
        "tipo": "STJ 2025",
        "filtro": lambda nome: "STJ" in nome and extrair_info(nome) and 835 <= extrair_info(nome) <= 874,
    },
    {
        "arquivo": "stj-2026.html",
        "titulo": "Simulado STJ",
        "subtitulo": "Informativos 875 - 884 • CERTO ou ERRADO",
        "cor": "#facc15",
        "tipo": "STJ 2026",
        "filtro": lambda nome: "STJ" in nome and extrair_info(nome) and 875 <= extrair_info(nome) <= 884,
    },
    {
        "arquivo": "stj-extra-2025.html",
        "titulo": "STJ Extraordinários",
        "subtitulo": "Edições Extraordinárias 22 - 27 • 2025",
        "cor": "#38bdf8",
        "tipo": "STJ Extra 2025",
        "filtro": lambda nome: "STJ" in nome and extrair_info(nome) and 22 <= extrair_info(nome) <= 27,
    },
    {
        "arquivo": "stj-extra-2026.html",
        "titulo": "STJ Extraordinários",
        "subtitulo": "Edições Extraordinárias 28 - 30 • 2026",
        "cor": "#38bdf8",
        "tipo": "STJ Extra 2026",
        "filtro": lambda nome: "STJ" in nome and extrair_info(nome) and 28 <= extrair_info(nome) <= 30,
    },
    {
        "arquivo": "sumulas.html",
        "titulo": "Súmulas",
        "subtitulo": "STF, STJ e Súmulas Vinculantes • CERTO ou ERRADO",
        "cor": "#22c55e",
        "tipo": "Súmulas",
        "filtro": lambda nome: any(x in nome.lower() for x in ["sumula", "súmula", "sv_"]),
    },
    {
        "arquivo": "rg.html",
        "titulo": "Repercussão Geral",
        "subtitulo": "Temas STF por disciplina • CERTO ou ERRADO",
        "cor": "#fb7185",
        "tipo": "RG",
        "filtro": lambda nome: "rg" in nome.lower() or "repercuss" in nome.lower(),
    },
    {
        "arquivo": "repetitivos.html",
        "titulo": "Repetitivos STJ",
        "subtitulo": "Temas repetitivos • CERTO ou ERRADO",
        "cor": "#2dd4bf",
        "tipo": "Repetitivos",
        "filtro": lambda nome: "repetitivo" in nome.lower(),
    },
]


# =========================
# EXTRAÇÕES
# =========================

def extrair_info(nome):
    m = re.search(r"Info\s+(\d+)", nome, flags=re.I)
    return int(m.group(1)) if m else None


def extrair_questoes(texto):
    partes = re.split(r"(?=^## Questão\s+\d+)", texto, flags=re.MULTILINE)
    return [p.strip() for p in partes if p.strip().startswith("## Questão")]


def extrair_numero_questao(bloco):
    m = re.search(r"## Questão\s+(\d+)", bloco)
    return m.group(1) if m else "?"


def extrair_gabarito(bloco):
    m = re.search(r"\*\*Gabarito:\*\*\s*(CERTO|ERRADO)", bloco, flags=re.I)
    return m.group(1).upper() if m else "N/I"


def extrair_enunciado(bloco):
    bloco = re.sub(r"^## Questão\s+\d+\s*", "", bloco).strip()
    return re.split(r"\*\*Gabarito:\*\*", bloco, maxsplit=1)[0].strip()


def extrair_justificativa(bloco):
    padroes = [
        r"\*\*Justificativa \(robusta\):\*\*\s*(.*?)(?=\n\*\*Referência:\*\*|\Z)",
        r"\*\*Justificativa:\*\*\s*(.*?)(?=\n\*\*Referência:\*\*|\Z)",
    ]
    for p in padroes:
        m = re.search(p, bloco, flags=re.S)
        if m:
            return m.group(1).strip()
    return "N/I"


def extrair_referencia(bloco):
    m = re.search(r"\*\*Referência:\*\*\s*(.*?)(?=\n---|\Z)", bloco, flags=re.S)
    return m.group(1).strip() if m else "N/I"


def limpar_ruidos(txt):
    txt = re.sub(r"\*\*ODS:\*\*\s*.*?(?=\n\*\*|\n\n|$)", "", txt, flags=re.I | re.S)
    txt = re.sub(r"ODS\s*\d+(?:\s*,\s*\d+)*(?:\s*E\s*\d+)?", "", txt, flags=re.I)
    txt = re.sub(r"\*\*Observações de saneamento:\*\*\s*.*?(?=\n\*\*|\n---|$)", "", txt, flags=re.I | re.S)
    txt = re.sub(r"\*\*Status:\*\*\s*Completo", "", txt, flags=re.I)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


def md_html(txt):
    txt = limpar_ruidos(txt)
    txt = html.escape(txt)
    txt = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", txt)
    txt = txt.replace("\n", "<br>")
    return txt


def detectar_disciplina(texto):
    disciplinas = [
        "Direito Constitucional", "Direito Administrativo", "Direito Civil",
        "Direito Processual Civil", "Direito Penal", "Direito Processual Penal",
        "Direito Tributário", "Direito Empresarial", "Direito Ambiental",
        "Direito Previdenciário", "Direito do Consumidor", "Direito Do Consumidor",
        "Direito Eleitoral", "Direito do Trabalho", "Direito Do Trabalho",
        "Direito Financeiro", "Direito Internacional", "Direito Notarial e Registral",
        "ECA", "Eca"
    ]
    for d in disciplinas:
        if re.search(re.escape(d), texto, flags=re.I):
            return d.replace("Do", "do")
    return "N/I"


def nome_curto_arquivo(nome):
    info = extrair_info(nome)
    if info:
        return f"Info {info}"
    nome = nome.replace("_questoes", "")
    nome = nome.replace("_final", "")
    nome = nome.replace("_", " ")
    return nome[:45]


# =========================
# CSS
# =========================

CSS = """
:root{
  --bg:#0b0d12;
  --card:#171a22;
  --card2:#11141b;
  --border:#2a2f3a;
  --muted:#8f96a8;
  --text:#e7e9ef;
  --ok:#22c55e;
  --err:#ef4444;
}
*{box-sizing:border-box}
body{
  margin:0;
  font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;
  background:#0b0d12;
  color:var(--text);
}
.container{
  max-width:1180px;
  margin:0 auto;
  padding:28px 18px 90px;
}
.hero{
  text-align:center;
  padding:28px 10px 22px;
}
.hero h1{
  margin:0;
  font-size:clamp(48px,8vw,86px);
  line-height:.88;
  letter-spacing:-.08em;
  font-weight:950;
}
.hero p{
  margin:14px 0 0;
  color:var(--muted);
  font-size:20px;
  font-weight:700;
  letter-spacing:.04em;
}
.stats{
  display:flex;
  justify-content:center;
  gap:14px;
  flex-wrap:wrap;
  margin:26px 0 28px;
}
.stat{
  background:var(--card);
  border:1px solid var(--border);
  color:var(--muted);
  border-radius:12px;
  padding:12px 22px;
  font-weight:900;
  font-size:18px;
}
.stat strong{color:var(--text)}
.stat.ok strong{color:var(--ok)}
.stat.err strong{color:var(--err)}
.filtros-wrap{
  margin:24px 0 22px;
}
.rotulo{
  color:var(--muted);
  text-transform:uppercase;
  letter-spacing:.12em;
  font-weight:900;
  margin-bottom:10px;
}
.filtros{
  display:flex;
  flex-wrap:wrap;
  gap:10px;
}
.filtros button{
  cursor:pointer;
  background:var(--card);
  border:1px solid var(--border);
  color:var(--muted);
  padding:13px 20px;
  border-radius:10px;
  font-weight:850;
  font-size:16px;
}
.filtros button.ativo{
  color:var(--accent);
  border-color:var(--accent);
  box-shadow:0 0 0 1px rgba(255,255,255,.03);
}
.busca-area{
  display:grid;
  grid-template-columns:1.5fr 1fr 1fr;
  gap:10px;
  margin:22px 0;
}
input,select{
  width:100%;
  background:var(--card2);
  color:var(--text);
  border:1px solid var(--border);
  border-radius:10px;
  padding:14px 16px;
  font-size:15px;
  outline:none;
}
.linha{
  height:4px;
  background:var(--border);
  border-radius:99px;
  margin:22px 0 28px;
}
.questao{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:18px;
  margin-bottom:22px;
  overflow:hidden;
}
.questao-topo{
  padding:16px 24px;
  border-bottom:1px solid var(--border);
  display:flex;
  justify-content:space-between;
  gap:12px;
  align-items:center;
}
.tags{display:flex;gap:8px;flex-wrap:wrap}
.tag{
  border:1px solid var(--accent);
  color:var(--accent);
  background:color-mix(in srgb, var(--accent) 16%, transparent);
  border-radius:6px;
  padding:5px 12px;
  font-weight:900;
}
.tag2{
  color:var(--muted);
  border-color:var(--border);
  background:#10131a;
}
.status{
  color:var(--muted);
  font-weight:800;
}
.enunciado{
  padding:24px;
  font-size:22px;
  line-height:1.55;
  font-weight:650;
}
.botoes{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:14px;
  padding:0 24px 24px;
}
.btn{
  cursor:pointer;
  border:1px solid var(--border);
  background:var(--card2);
  color:var(--muted);
  border-radius:14px;
  padding:18px;
  font-weight:950;
  font-size:20px;
  letter-spacing:.06em;
}
.btn:hover{
  border-color:var(--accent);
  color:var(--text);
}
.feedback{
  display:none;
  border-top:1px solid var(--border);
  background:#0f1218;
  padding:24px;
  font-size:17px;
}
.feedback.correto{border-left:5px solid var(--ok)}
.feedback.errado{border-left:5px solid var(--err)}
.resultado{
  font-size:20px;
  font-weight:950;
  margin:0 0 16px;
}
.gabarito-certo{color:var(--ok);font-weight:950}
.gabarito-errado{color:var(--err);font-weight:950}
.referencia{
  color:var(--muted);
  font-size:13px;
  margin-top:18px;
}
.oculta{display:none}
.vazio{
  display:none;
  text-align:center;
  color:var(--muted);
  padding:40px;
}
.home-grid{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
  gap:16px;
}
.home-card{
  text-decoration:none;
  color:var(--text);
  background:var(--card);
  border:1px solid var(--border);
  border-radius:18px;
  padding:24px;
  min-height:160px;
  display:flex;
  flex-direction:column;
  justify-content:space-between;
}
.home-card:hover{
  border-color:var(--accent);
}
.home-card h2{
  margin:0;
  font-size:26px;
  letter-spacing:-.04em;
}
.home-card p{
  color:var(--muted);
  margin:10px 0 0;
}
.home-card span{
  color:var(--accent);
  font-weight:950;
}
@media(max-width:800px){
  .busca-area{grid-template-columns:1fr}
  .botoes{grid-template-columns:1fr}
  .enunciado{font-size:18px}
  .hero h1{font-size:48px}
}
"""


# =========================
# GERAR CADERNO
# =========================

def carregar_questoes_do_caderno(caderno):
    itens = []

    for arq in sorted(PASTA_QUESTOES.glob("*.md")):
        nome = arq.stem

        if not caderno["filtro"](nome):
            continue

        texto = arq.read_text(encoding="utf-8", errors="ignore")
        questoes = extrair_questoes(texto)

        for q in questoes:
            enunciado = extrair_enunciado(q)
            justificativa = extrair_justificativa(q)
            referencia = extrair_referencia(q)
            disciplina = detectar_disciplina(enunciado + " " + justificativa + " " + referencia)

            itens.append({
                "origem": nome_curto_arquivo(nome),
                "ordem": extrair_info(nome) or 99999,
                "gabarito": extrair_gabarito(q),
                "enunciado": enunciado,
                "justificativa": justificativa,
                "referencia": referencia,
                "disciplina": disciplina,
                "busca": (nome + " " + enunciado + " " + justificativa + " " + referencia + " " + disciplina).lower()
            })

    return sorted(itens, key=lambda x: (x["ordem"], x["origem"]))


def gerar_caderno(caderno):
    questoes = carregar_questoes_do_caderno(caderno)

    botoes_origem = sorted(set(q["origem"] for q in questoes), key=lambda x: int(re.search(r"\d+", x).group()) if re.search(r"\d+", x) else 99999)
    botoes_disciplina = sorted(set(q["disciplina"] for q in questoes))

    html_questoes = []

    for idx, q in enumerate(questoes, start=1):
        html_questoes.append(f"""
<section class="questao"
 data-origem="{html.escape(q['origem'])}"
 data-disciplina="{html.escape(q['disciplina'])}"
 data-gabarito="{q['gabarito']}"
 data-texto="{html.escape(q['busca'])}">

  <div class="questao-topo">
    <div class="tags">
      <span class="tag">{html.escape(q['origem'])}</span>
      <span class="tag tag2">{html.escape(q['disciplina'])}</span>
    </div>
    <span class="status" id="status-{idx}">Não respondida</span>
  </div>

  <div class="enunciado">{md_html(q['enunciado'])}</div>

  <div class="botoes">
    <button class="btn" onclick="responder({idx}, 'CERTO')">CERTO</button>
    <button class="btn" onclick="responder({idx}, 'ERRADO')">ERRADO</button>
  </div>

  <div class="feedback" id="feedback-{idx}">
    <p class="resultado"></p>
    <p><strong>Gabarito:</strong> {q['gabarito']}</p>
    <div><strong>Justificativa:</strong><br>{md_html(q['justificativa'])}</div>
    <p class="referencia"><strong>Referência:</strong><br>{md_html(q['referencia'])}</p>
  </div>
</section>
""")

    filtros_origem = ['<button class="ativo" onclick="setOrigem(\'\', this)">Todos</button>']
    filtros_origem += [
        f'<button onclick="setOrigem(\'{html.escape(o)}\', this)">{html.escape(o)}</button>'
        for o in botoes_origem
    ]

    opcoes_disciplina = '<option value="">Todas as disciplinas</option>' + "".join(
        f'<option value="{html.escape(d)}">{html.escape(d)}</option>'
        for d in botoes_disciplina
    )

    html_final = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>{html.escape(caderno['titulo'])}</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
{CSS}
:root{{--accent:{caderno['cor']};}}
</style>
</head>
<body>

<div class="container">

  <header class="hero">
    <h1 style="color:{caderno['cor']}">{html.escape(caderno['titulo'])}</h1>
    <p>{html.escape(caderno['subtitulo'])}</p>
  </header>

  <section class="stats">
    <div class="stat">Total <strong>{len(questoes)}</strong></div>
    <div class="stat">Resp. <strong id="respondidas">0</strong></div>
    <div class="stat ok">✓ <strong id="acertos">0</strong></div>
    <div class="stat err">✗ <strong id="erros">0</strong></div>
    <div class="stat">% <strong id="aproveitamento">–</strong></div>
  </section>

  <section class="filtros-wrap">
    <div class="rotulo">Filtrar por informativo / bloco</div>
    <div class="filtros">
      {''.join(filtros_origem)}
    </div>

    <div class="busca-area">
      <input id="busca" type="search" placeholder="Buscar palavra-chave..." oninput="filtrar()">
      <select id="disciplina" onchange="filtrar()">{opcoes_disciplina}</select>
      <select id="statusFiltro" onchange="filtrar()">
        <option value="">Todas</option>
        <option value="nao">Não respondidas</option>
        <option value="acerto">Acertos</option>
        <option value="erro">Erros</option>
      </select>
    </div>
  </section>

  <div class="linha"></div>

  <div id="vazio" class="vazio">Nenhuma questão encontrada.</div>

  {''.join(html_questoes)}

</div>

<script>
const storageKey = location.pathname + "_respostas";
let respostas = JSON.parse(localStorage.getItem(storageKey) || "{{}}");
let origemAtual = "";

function setOrigem(origem, btn){{
  origemAtual = origem;
  document.querySelectorAll(".filtros button").forEach(b => b.classList.remove("ativo"));
  btn.classList.add("ativo");
  filtrar();
}}

function destacar(t){{
 if(t === "CERTO") return '<span class="gabarito-certo">CERTO</span>';
 if(t === "ERRADO") return '<span class="gabarito-errado">ERRADO</span>';
 return t;
}}

function responder(num, resp){{
  const card = document.querySelectorAll(".questao")[num - 1];
  const gab = card.dataset.gabarito;
  respostas[num] = {{resposta: resp, correto: resp === gab}};
  localStorage.setItem(storageKey, JSON.stringify(respostas));
  mostrarFeedback(num);
  atualizar();
  filtrar();
}}

function mostrarFeedback(num){{
  const card = document.querySelectorAll(".questao")[num - 1];
  const fb = document.getElementById("feedback-" + num);
  const st = document.getElementById("status-" + num);
  const res = fb.querySelector(".resultado");
  const gab = card.dataset.gabarito;
  const dados = respostas[num];

  if(!dados) return;

  fb.style.display = "block";
  fb.classList.remove("correto", "errado");

  if(dados.correto){{
    fb.classList.add("correto");
    res.innerHTML = "Você acertou. A resposta é " + destacar(gab) + ".";
    st.textContent = "Respondida — acerto";
    st.style.color = "var(--ok)";
  }} else {{
    fb.classList.add("errado");
    res.innerHTML = "Você errou. O gabarito é " + destacar(gab) + ".";
    st.textContent = "Respondida — erro";
    st.style.color = "var(--err)";
  }}
}}

function atualizar(){{
  let resp = 0, ac = 0, er = 0;
  for(const k in respostas){{
    resp++;
    if(respostas[k].correto) ac++;
    else er++;
  }}
  document.getElementById("respondidas").textContent = resp;
  document.getElementById("acertos").textContent = ac;
  document.getElementById("erros").textContent = er;
  document.getElementById("aproveitamento").textContent = resp ? Math.round((ac / resp) * 100) + "%" : "–";
}}

function filtrar(){{
  const busca = document.getElementById("busca").value.trim().toLowerCase();
  const disciplina = document.getElementById("disciplina").value;
  const status = document.getElementById("statusFiltro").value;

  let vis = 0;

  document.querySelectorAll(".questao").forEach((card, idx) => {{
    const n = idx + 1;
    const r = respostas[n];

    let passaStatus = true;
    if(status === "nao") passaStatus = !r;
    if(status === "acerto") passaStatus = r && r.correto;
    if(status === "erro") passaStatus = r && !r.correto;

    const ok =
      (!origemAtual || card.dataset.origem === origemAtual) &&
      (!busca || card.dataset.texto.includes(busca)) &&
      (!disciplina || card.dataset.disciplina === disciplina) &&
      passaStatus;

    card.classList.toggle("oculta", !ok);
    if(ok) vis++;
  }});

  document.getElementById("vazio").style.display = vis === 0 ? "block" : "none";
}}

function restaurar(){{
  for(const k in respostas) mostrarFeedback(Number(k));
  atualizar();
  filtrar();
}}

restaurar();
</script>

</body>
</html>
"""

    (PASTA_DOCS / caderno["arquivo"]).write_text(html_final, encoding="utf-8")
    print(f"✅ {caderno['arquivo']} — {len(questoes)} questões")

    return {
        "arquivo": caderno["arquivo"],
        "titulo": caderno["titulo"],
        "subtitulo": caderno["subtitulo"],
        "tipo": caderno["tipo"],
        "cor": caderno["cor"],
        "questoes": len(questoes),
    }


def gerar_home(cadernos_gerados):
    cards = []

    for c in cadernos_gerados:
        if c["questoes"] == 0:
            continue

        cards.append(f"""
<a class="home-card" href="{c['arquivo']}" style="--accent:{c['cor']}">
  <div>
    <h2>{html.escape(c['tipo'])}</h2>
    <p>{html.escape(c['subtitulo'])}</p>
  </div>
  <span>{c['questoes']} questões</span>
</a>
""")

    total_questoes = sum(c["questoes"] for c in cadernos_gerados)

    home = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Simulados de Jurisprudência</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect width=%22100%22 height=%22100%22 rx=%2220%22 fill=%22%230b0d12%22/><text x=%2250%22 y=%2264%22 font-size=%2254%22 text-anchor=%22middle%22 fill=%22%23c084fc%22>§</text></svg>">
<style>{CSS}</style>
</head>
<body>

<div class="container">
  <header class="hero">
    <h1 style="color:#c084fc">Simulados</h1>
    <p>Jurisprudência STF/STJ • Informativos, Súmulas, RG e Repetitivos</p>
  </header>

  <section class="stats">
    <div class="stat">Cadernos <strong>{len([c for c in cadernos_gerados if c['questoes'] > 0])}</strong></div>
    <div class="stat">Questões <strong>{total_questoes}</strong></div>
  </section>

  <div class="home-grid">
    {''.join(cards)}
  </div>
</div>

</body>
</html>
"""

    (PASTA_DOCS / "index.html").write_text(home, encoding="utf-8")
    print("✅ docs/index.html gerado")


def main():
    print("Gerando cadernos premium...\n")
    gerados = []

    for caderno in CADERNOS:
        gerados.append(gerar_caderno(caderno))

    gerar_home(gerados)

    print("\nFinalizado.")
    print("Abra: docs/index.html")


if __name__ == "__main__":
    main()