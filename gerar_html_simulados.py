import re
import html
import json
from pathlib import Path

PASTA_ENTRADA = Path("questoes_validadas_pdf")
PASTA_SAIDA = Path("html_simulados")

PASTA_SAIDA.mkdir(exist_ok=True)


def slug_tipo(nome):
    n = nome.lower()
    if "súmula" in n or "sumula" in n or "sv" in n:
        return "Súmulas"
    if "repercuss" in n or "rg" in n or "tema" in n:
        return "Repercussão Geral"
    if "repetitivo" in n or "repetitivos" in n:
        return "Repetitivos"
    if "stj" in n or "stf" in n:
        return "Informativos"
    return "Extras"


def extrair_questoes(texto):
    partes = re.split(r"(?=^## Questão\s+\d+)", texto, flags=re.MULTILINE)
    return [p.strip() for p in partes if p.strip().startswith("## Questão")]


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
    return txt.strip()


def extrair_numero(bloco):
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


CSS = """
:root{
--bg:#020617;--panel:rgba(15,23,42,.88);--card:rgba(15,23,42,.96);
--card2:rgba(30,41,59,.92);--border:rgba(148,163,184,.22);
--text:#e5e7eb;--muted:#94a3b8;--accent:#38bdf8;--accent2:#0ea5e9;
--green:#22c55e;--red:#ef4444;--yellow:#facc15;--purple:#a78bfa;
}
*{box-sizing:border-box}
body{
margin:0;font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;
background:radial-gradient(circle at top left,rgba(56,189,248,.20),transparent 28%),
radial-gradient(circle at top right,rgba(167,139,250,.15),transparent 28%),
linear-gradient(135deg,#020617,#0f172a 50%,#020617);
color:var(--text);line-height:1.65;
}
header{padding:44px 20px 32px;text-align:center;border-bottom:1px solid var(--border)}
header h1{margin:0 0 10px;font-size:clamp(28px,4vw,46px);letter-spacing:-.05em}
header p{color:var(--muted);margin:0;font-size:16px}
.container{max-width:1160px;margin:0 auto;padding:26px 16px 80px}
.painel{
position:sticky;top:10px;z-index:10;background:var(--panel);backdrop-filter:blur(18px);
border:1px solid var(--border);border-radius:26px;padding:16px;margin-bottom:22px;
box-shadow:0 22px 70px rgba(0,0,0,.35)
}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.stat{background:var(--card2);padding:14px;border-radius:18px;text-align:center;border:1px solid rgba(148,163,184,.12)}
.stat strong{display:block;font-size:25px;color:var(--accent);line-height:1.1}
.stat span{font-size:12px;color:var(--muted)}
.filtros{display:grid;grid-template-columns:1.4fr 1fr 1fr auto;gap:12px;margin-top:14px}
input,select{
width:100%;background:rgba(2,6,23,.78);color:var(--text);border:1px solid var(--border);
border-radius:14px;padding:13px 14px;outline:none;font-size:14px
}
input:focus,select:focus{border-color:var(--accent)}
.card{
background:var(--card);border:1px solid var(--border);border-radius:24px;padding:26px;
margin-bottom:20px;box-shadow:0 18px 50px rgba(0,0,0,.24)
}
.questao{scroll-margin-top:190px}
.questao-topo{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:18px}
.badge{
background:linear-gradient(135deg,var(--accent),var(--accent2));color:#00111f;font-weight:900;
padding:7px 13px;border-radius:999px;display:inline-block
}
.disciplina-tag,.tipo-tag{
display:inline-block;margin-left:8px;color:var(--muted);background:rgba(148,163,184,.10);
border:1px solid rgba(148,163,184,.14);padding:6px 10px;border-radius:999px;font-size:12px
}
.tipo-tag{color:#ddd6fe;border-color:rgba(167,139,250,.25)}
.status{color:var(--yellow);font-size:13px;white-space:nowrap}
.enunciado{font-size:19px;margin:0 0 22px;letter-spacing:-.01em}
.botoes{display:flex;gap:12px;margin-bottom:18px;flex-wrap:wrap}
.btn{
cursor:pointer;border:0;padding:12px 22px;border-radius:14px;color:white;font-weight:900;
transition:.18s ease;letter-spacing:.02em
}
.btn:hover{transform:translateY(-2px);filter:brightness(1.08)}
.btn.certo{background:rgba(34,197,94,.20);border:1px solid rgba(34,197,94,.42)}
.btn.errado{background:rgba(239,68,68,.20);border:1px solid rgba(239,68,68,.42)}
.btn.neutro{background:rgba(56,189,248,.16);color:var(--text);border:1px solid rgba(56,189,248,.32)}
.feedback{
display:none;background:rgba(2,6,23,.72);border:1px solid rgba(148,163,184,.16);
border-left:5px solid var(--accent);padding:18px;border-radius:18px;margin-top:14px
}
.feedback.correto{border-left-color:var(--green)}
.feedback.errado{border-left-color:var(--red)}
.resultado{font-size:18px;font-weight:900;margin-top:0}
.justificativa{margin-top:12px}
.referencia{color:var(--muted);font-size:13px;margin-top:16px}
.gabarito-certo{color:var(--green);font-weight:900}
.gabarito-errado{color:var(--red);font-weight:900}
.oculta{display:none}
.sem-resultados{text-align:center;color:var(--muted);display:none;padding:30px}
.grid-index{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px}
.link-card{
display:block;padding:20px;background:rgba(15,23,42,.95);border:1px solid rgba(148,163,184,.22);
color:#e5e7eb;border-radius:22px;text-decoration:none;transition:.2s;box-shadow:0 14px 40px rgba(0,0,0,.22)
}
.link-card:hover{transform:translateY(-3px);border-color:#38bdf8}
.link-card strong{display:block;font-size:17px;margin-bottom:8px}
.link-card span{color:#94a3b8;font-size:13px}
.index-tools{display:grid;grid-template-columns:1.5fr 1fr;gap:12px;margin-bottom:20px}
@media(max-width:850px){
.stats{grid-template-columns:repeat(2,1fr)}
.filtros,.index-tools{grid-template-columns:1fr}
.questao-topo{align-items:flex-start;flex-direction:column}
.botoes{flex-direction:column}
.enunciado{font-size:16px}
.card{padding:20px}
}
"""


def gerar_html(nome_simulado, nome_base, tipo, questoes):
    questoes_html = []
    disciplinas = set()

    for i, bloco in enumerate(questoes, start=1):
        numero = extrair_numero(bloco)
        gabarito = extrair_gabarito(bloco)
        enunciado_raw = extrair_enunciado(bloco)
        justificativa_raw = extrair_justificativa(bloco)
        referencia_raw = extrair_referencia(bloco)
        disciplina = detectar_disciplina(enunciado_raw + " " + justificativa_raw + " " + referencia_raw)

        disciplinas.add(disciplina)

        texto_busca = (enunciado_raw + " " + justificativa_raw + " " + referencia_raw).lower()

        questoes_html.append(f"""
<section class="card questao"
data-gabarito="{gabarito}"
data-disciplina="{html.escape(disciplina)}"
data-texto="{html.escape(texto_busca)}">

<div class="questao-topo">
  <div>
    <span class="badge">Questão {numero}</span>
    <span class="disciplina-tag">{html.escape(disciplina)}</span>
    <span class="tipo-tag">{html.escape(tipo)}</span>
  </div>
  <span class="status" id="status-{i}">Não respondida</span>
</div>

<p class="enunciado">{md_html(enunciado_raw)}</p>

<div class="botoes">
  <button class="btn certo" onclick="responder({i}, 'CERTO')">CERTO</button>
  <button class="btn errado" onclick="responder({i}, 'ERRADO')">ERRADO</button>
</div>

<div class="feedback" id="feedback-{i}">
  <p class="resultado"></p>
  <p><strong>Gabarito:</strong> <span>{gabarito}</span></p>
  <div class="justificativa"><strong>Justificativa:</strong><br>{md_html(justificativa_raw)}</div>
  <p class="referencia"><strong>Referência:</strong><br>{md_html(referencia_raw)}</p>
</div>
</section>
""")

    opcoes_disciplinas = "\n".join(
        f'<option value="{html.escape(d)}">{html.escape(d)}</option>'
        for d in sorted(disciplinas)
    )

    total = len(questoes)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>{html.escape(nome_simulado)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>{CSS}</style>
</head>
<body>
<header>
<h1>{html.escape(nome_simulado)}</h1>
<p>{html.escape(tipo)} • Simulado interativo de CERTO ou ERRADO</p>
</header>

<div class="container">
<div class="painel">
<div class="stats">
<div class="stat"><strong>{total}</strong><span>Total</span></div>
<div class="stat"><strong id="visiveis">{total}</strong><span>Visíveis</span></div>
<div class="stat"><strong id="respondidas">0</strong><span>Respondidas</span></div>
<div class="stat"><strong id="acertos">0</strong><span>Acertos</span></div>
<div class="stat"><strong id="erros">0</strong><span>Erros</span></div>
</div>

<div class="filtros">
<input id="busca" type="search" placeholder="Buscar por palavra-chave..." oninput="filtrar()">
<select id="disciplina" onchange="filtrar()">
<option value="">Todas as disciplinas</option>
{opcoes_disciplinas}
</select>
<select id="statusFiltro" onchange="filtrar()">
<option value="">Todas</option>
<option value="nao">Não respondidas</option>
<option value="acerto">Acertos</option>
<option value="erro">Erros</option>
</select>
<button class="btn neutro" onclick="reiniciar()">Reiniciar</button>
</div>
</div>

<div id="sem-resultados" class="sem-resultados">Nenhuma questão encontrada com os filtros atuais.</div>

{''.join(questoes_html)}
</div>

<script>
const storageKey = location.pathname + "_respostas";
let respostas = JSON.parse(localStorage.getItem(storageKey) || "{{}}");

function destacar(t){{
 if(t==="CERTO") return '<span class="gabarito-certo">CERTO</span>';
 if(t==="ERRADO") return '<span class="gabarito-errado">ERRADO</span>';
 return t;
}}

function responder(numero, resposta){{
 const card=document.querySelectorAll(".questao")[numero-1];
 const gabarito=card.dataset.gabarito;
 const correto=resposta===gabarito;
 respostas[numero]={{resposta,correto}};
 localStorage.setItem(storageKey, JSON.stringify(respostas));
 mostrarFeedback(numero);
 atualizarPainel();
 filtrar();
}}

function mostrarFeedback(numero){{
 const card=document.querySelectorAll(".questao")[numero-1];
 const feedback=document.getElementById("feedback-"+numero);
 const status=document.getElementById("status-"+numero);
 const resultado=feedback.querySelector(".resultado");
 const gabarito=card.dataset.gabarito;
 const dados=respostas[numero];
 if(!dados) return;
 feedback.style.display="block";
 feedback.classList.remove("correto","errado");
 if(dados.correto){{
   feedback.classList.add("correto");
   resultado.innerHTML="Você acertou. A resposta é "+destacar(gabarito)+".";
   status.textContent="Respondida — acerto";
   status.style.color="var(--green)";
 }} else {{
   feedback.classList.add("errado");
   resultado.innerHTML="Você errou. O gabarito é "+destacar(gabarito)+".";
   status.textContent="Respondida — erro";
   status.style.color="var(--red)";
 }}
}}

function atualizarPainel(){{
 let respondidas=0, acertos=0, erros=0;
 for(const k in respostas){{
   respondidas++;
   if(respostas[k].correto) acertos++; else erros++;
 }}
 document.getElementById("respondidas").textContent=respondidas;
 document.getElementById("acertos").textContent=acertos;
 document.getElementById("erros").textContent=erros;
 document.getElementById("visiveis").textContent=document.querySelectorAll(".questao:not(.oculta)").length;
}}

function filtrar(){{
 const busca=document.getElementById("busca").value.trim().toLowerCase();
 const disciplina=document.getElementById("disciplina").value;
 const statusFiltro=document.getElementById("statusFiltro").value;
 const cards=Array.from(document.querySelectorAll(".questao"));
 let vis=0;
 cards.forEach((card,idx)=>{{
   const n=idx+1;
   const texto=card.dataset.texto||"";
   const disc=card.dataset.disciplina||"";
   const r=respostas[n];
   let passaStatus=true;
   if(statusFiltro==="nao") passaStatus=!r;
   if(statusFiltro==="acerto") passaStatus=r && r.correto;
   if(statusFiltro==="erro") passaStatus=r && !r.correto;
   const ok=(!busca||texto.includes(busca)) && (!disciplina||disc===disciplina) && passaStatus;
   card.classList.toggle("oculta", !ok);
   if(ok) vis++;
 }});
 document.getElementById("sem-resultados").style.display=vis===0?"block":"none";
 atualizarPainel();
}}

function reiniciar(){{
 if(!confirm("Deseja reiniciar este simulado?")) return;
 localStorage.removeItem(storageKey);
 location.reload();
}}

function restaurar(){{
 for(const k in respostas) mostrarFeedback(Number(k));
 filtrar();
 atualizarPainel();
}}

restaurar();
</script>
</body>
</html>"""


def processar_arquivo(caminho):
    texto = caminho.read_text(encoding="utf-8")
    questoes = extrair_questoes(texto)
    if not questoes:
        print(f"⚠️ Nenhuma questão encontrada em {caminho.name}")
        return None

    nome_base = caminho.stem.replace("_questoes", "")
    tipo = slug_tipo(nome_base)
    saida = PASTA_SAIDA / f"{nome_base}.html"
    html_final = gerar_html(f"Simulado - {nome_base}", nome_base, tipo, questoes)
    saida.write_text(html_final, encoding="utf-8")

    print(f"✅ HTML gerado: {saida.name}")

    return {
        "nome": nome_base,
        "arquivo": saida.name,
        "tipo": tipo,
        "questoes": len(questoes)
    }


def gerar_index(itens):
    tipos = sorted(set(i["tipo"] for i in itens))
    opcoes = "\n".join(f'<option value="{html.escape(t)}">{html.escape(t)}</option>' for t in tipos)

    cards = []
    for i in sorted(itens, key=lambda x: x["nome"]):
        cards.append(f"""
<a class="link-card" href="{html.escape(i['arquivo'])}" data-tipo="{html.escape(i['tipo'])}" data-texto="{html.escape(i['nome'].lower())}">
<strong>{html.escape(i['nome'])}</strong>
<span>{html.escape(i['tipo'])} • {i['questoes']} questões</span>
</a>
""")

    total_questoes = sum(i["questoes"] for i in itens)

    index = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Simulados de Jurisprudência</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>{CSS}</style>
</head>
<body>
<header>
<h1>Simulados de Jurisprudência</h1>
<p>{len(itens)} simulados • {total_questoes} questões</p>
</header>

<div class="container">
<div class="painel">
<div class="index-tools">
<input id="busca" type="search" placeholder="Buscar informativo, súmula, tema..." oninput="filtrarIndex()">
<select id="tipo" onchange="filtrarIndex()">
<option value="">Todos os tipos</option>
{opcoes}
</select>
</div>
</div>

<div class="grid-index" id="grid">
{''.join(cards)}
</div>
</div>

<script>
function filtrarIndex(){{
 const busca=document.getElementById("busca").value.trim().toLowerCase();
 const tipo=document.getElementById("tipo").value;
 document.querySelectorAll(".link-card").forEach(card=>{{
   const texto=card.dataset.texto||"";
   const t=card.dataset.tipo||"";
   const ok=(!busca||texto.includes(busca)) && (!tipo||t===tipo);
   card.style.display=ok?"block":"none";
 }});
}}
</script>
</body>
</html>"""

    (PASTA_SAIDA / "index.html").write_text(index, encoding="utf-8")
    print("✅ index.html gerado.")


def main():
    arquivos = sorted(PASTA_ENTRADA.glob("*.md"))
    if not arquivos:
        print(f"❌ Nenhum arquivo .md encontrado em {PASTA_ENTRADA}.")
        return

    print(f"📚 Arquivos encontrados: {len(arquivos)}")
    itens = []

    for arquivo in arquivos:
        item = processar_arquivo(arquivo)
        if item:
            itens.append(item)

    gerar_index(itens)

    print("\n🎯 Finalizado.")
    print(f"Abra: {PASTA_SAIDA / 'index.html'}")


if __name__ == "__main__":
    main()