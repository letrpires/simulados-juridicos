from pathlib import Path
import json
import shutil

import sys

fonte_filtrar = None

if "--fonte" in sys.argv:
    i = sys.argv.index("--fonte")
    if i + 1 < len(sys.argv):
        fonte_filtrar = sys.argv[i + 1]

PASTA_DATA = Path('data')
ARQUIVO_QUESTOES = PASTA_DATA / 'questoes.json'
PASTA_SAIDA = Path('html_final')
PASTA_ASSETS = PASTA_SAIDA / 'assets'
PASTA_DADOS = PASTA_SAIDA / 'data'


def carregar_resumo():
    if not ARQUIVO_QUESTOES.exists():
        raise FileNotFoundError('Não encontrei data/questoes.json. Rode antes: python3 gerar_json_questoes_v2.py')
    questoes = json.loads(ARQUIVO_QUESTOES.read_text(encoding='utf-8'))
    return {
        'total': len(questoes),
        'modulos': len(set(q.get('modulo','') for q in questoes)),
        'categorias': len(set(q.get('categoria','') for q in questoes)),
    }


INDEX_HTML = r'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Simulados Jurídicos STF/STJ</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Fraunces:wght@600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/styles.css" />
</head>
<body>
  <div id="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">⚖️</div>
        <div>
          <h1>Simulados</h1>
          <p>STF · STJ · Súmulas</p>
        </div>
      </div>
      <nav class="nav" aria-label="Navegação principal">
        <button data-view="dashboard" class="nav-btn active">🏠 <span>Dashboard</span></button>
        <button data-view="study" class="nav-btn">🧠 <span>Estudar</span></button>
        <button data-view="review" class="nav-btn">🔁 <span>Revisão</span></button>
        <button data-view="library" class="nav-btn">📚 <span>Biblioteca</span></button>
        <button data-view="settings" class="nav-btn">⚙️ <span>Ajustes</span></button>
      </nav>
      <div class="sidebar-footer">
        <button id="themeToggle" class="ghost-btn">🌙 Modo escuro</button>
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <p class="eyebrow">Banco local de questões</p>
          <h2 id="viewTitle">Dashboard</h2>
        </div>
        <div class="top-actions">
          <button id="continueBtn" class="primary-btn">Continuar</button>
        </div>
      </header>
      <section id="content" class="content"></section>
    </main>

    <nav class="bottom-nav" aria-label="Navegação mobile">
      <button data-view="dashboard" class="nav-btn active">🏠<small>Início</small></button>
      <button data-view="study" class="nav-btn">🧠<small>Estudar</small></button>
      <button data-view="review" class="nav-btn">🔁<small>Revisão</small></button>
      <button data-view="library" class="nav-btn">📚<small>Base</small></button>
      <button data-view="settings" class="nav-btn">⚙️<small>Ajustes</small></button>
    </nav>
  </div>
  <script src="assets/app.js"></script>
</body>
</html>
'''

STYLES = r''':root{
  --bg:#f6f3ee; --surface:#ffffff; --surface-2:#eef6f1; --text:#172033; --muted:#667085;
  --line:#e6e0d7; --primary:#1E5EFF; --green:#00a878; --red:#d92d20; --amber:#f5a623;
  --shadow:0 18px 50px rgba(31,41,55,.10); --radius:20px;
}
[data-theme="dark"]{--bg:#101522;--surface:#171d2c;--surface-2:#1f293b;--text:#f8fafc;--muted:#aab4c3;--line:#2d3748;--shadow:0 18px 60px rgba(0,0,0,.35)}
*{box-sizing:border-box} body{margin:0;font-family:'DM Sans',system-ui,sans-serif;background:var(--bg);color:var(--text)}
button,input,select{font:inherit} button{cursor:pointer} .sidebar{position:fixed;inset:0 auto 0 0;width:292px;background:rgba(255,255,255,.72);backdrop-filter:blur(18px);border-right:1px solid var(--line);padding:24px;display:flex;flex-direction:column;gap:28px;z-index:3}[data-theme="dark"] .sidebar{background:rgba(23,29,44,.72)}
.brand{display:flex;gap:12px;align-items:center}.brand-mark{width:48px;height:48px;border-radius:16px;background:linear-gradient(135deg,#dfe7ff,#d9f7ea);display:grid;place-items:center;font-size:25px}.brand h1{font-family:'Fraunces',serif;margin:0;font-size:24px;color:var(--text)}.brand p,.eyebrow{margin:0;color:var(--muted);font-size:13px}
.nav{display:grid;gap:8px}.nav-btn{border:0;background:transparent;color:var(--muted);padding:12px 14px;border-radius:14px;display:flex;gap:10px;align-items:center;text-align:left}.nav-btn.active,.nav-btn:hover{background:var(--surface-2);color:var(--text)}.sidebar-footer{margin-top:auto}.ghost-btn{border:1px solid var(--line);background:transparent;color:var(--text);border-radius:14px;padding:10px 12px}.primary-btn,.accent-btn{border:0;background:var(--primary);color:white;border-radius:14px;padding:12px 16px;font-weight:800}.accent-btn{background:var(--green)}.danger-btn{border:0;background:var(--red);color:white;border-radius:14px;padding:10px 14px}.secondary-btn{border:1px solid var(--line);background:var(--surface);color:var(--text);border-radius:14px;padding:11px 14px;font-weight:700}
.main{margin-left:292px;min-height:100vh;padding:28px 34px 96px}.topbar{display:flex;justify-content:space-between;align-items:center;gap:18px;margin-bottom:24px}.topbar h2{font-family:'Fraunces',serif;font-size:34px;margin:4px 0 0}.content{display:grid;gap:18px}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:16px}.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:20px}.stat{grid-column:span 3}.wide{grid-column:span 8}.side{grid-column:span 4}.full{grid-column:1/-1}.stat strong{display:block;font-size:32px}.stat span{color:var(--muted)}
.filters{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px}.filters input,.filters select{width:100%;border:1px solid var(--line);border-radius:14px;background:var(--surface);color:var(--text);padding:11px 12px}.pill-row{display:flex;flex-wrap:wrap;gap:8px}.pill{border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:8px 12px;color:var(--muted)}.pill.active{background:var(--primary);color:white;border-color:var(--primary)}
.question-card{max-width:980px;margin:auto}.question-meta{display:flex;gap:8px;flex-wrap:wrap;color:var(--muted);font-size:13px}.question-text{font-size:21px;line-height:1.65;margin:22px 0}.answers{display:grid;grid-template-columns:1fr 1fr;gap:12px}.answer-btn{border:1px solid var(--line);background:var(--surface);color:var(--text);border-radius:18px;padding:18px;font-size:18px;font-weight:800}.answer-btn.correct{background:#e8fff6;border-color:var(--green);color:#066548}.answer-btn.wrong{background:#fff0ee;border-color:var(--red);color:#8a1f17}.feedback{margin-top:16px;border-left:5px solid var(--primary);padding:14px 16px;background:var(--surface-2);border-radius:14px;line-height:1.6}.progress-bar{height:12px;background:var(--surface-2);border-radius:999px;overflow:hidden}.progress-bar span{display:block;height:100%;background:linear-gradient(90deg,var(--primary),var(--green));width:0%}.table{width:100%;border-collapse:collapse}.table td,.table th{border-bottom:1px solid var(--line);padding:10px;text-align:left}.chart{height:260px;display:flex;align-items:end;gap:10px;padding:42px 4px 4px;overflow:hidden}.bar{flex:1;background:linear-gradient(180deg,var(--primary),#9eb8ff);border-radius:12px 12px 4px 4px;min-height:8px;position:relative}.bar small{position:absolute;bottom:100%;left:0;font-size:10px;color:var(--muted);white-space:nowrap;transform:rotate(-28deg);transform-origin:left bottom;max-width:120px;overflow:hidden;text-overflow:ellipsis}.heatmap{display:grid;grid-template-columns:repeat(15,1fr);gap:5px}.heat{height:18px;border-radius:5px;background:var(--surface-2)}.h1{background:#d9f7ea}.h2{background:#8ee7c0}.h3{background:#00c48c}.bottom-nav{display:none}
@media(max-width:900px){.sidebar{display:none}.main{margin:0;padding:20px 14px 86px}.grid{grid-template-columns:1fr}.stat,.wide,.side{grid-column:1/-1}.filters{grid-template-columns:1fr}.answers{grid-template-columns:1fr}.topbar h2{font-size:28px}.bottom-nav{position:fixed;left:10px;right:10px;bottom:10px;display:grid;grid-template-columns:repeat(5,1fr);background:var(--surface);border:1px solid var(--line);border-radius:22px;padding:8px;box-shadow:var(--shadow);z-index:5}.bottom-nav .nav-btn{justify-content:center;display:grid;gap:1px;padding:8px 2px}.bottom-nav small{font-size:11px}.question-text{font-size:18px}}
'''

APP_JS = r'''const DB_URL='data/questoes.json';
const LS_KEY='simulados_juridicos_estado_v1';
let questions=[]; let state=loadState(); let currentView='dashboard'; let session=[]; let currentIndex=0;
function today(){return new Date().toISOString().slice(0,10)}
function addDays(d,n){const x=new Date(d||today());x.setDate(x.getDate()+n);return x.toISOString().slice(0,10)}
function loadState(){try{return JSON.parse(localStorage.getItem(LS_KEY))||defaultState()}catch{return defaultState()}}
function defaultState(){return{answers:{},marked:{},xp:0,badges:[],sessions:[],settings:{theme:localStorage.getItem('theme')||''},lastSession:null,studySeconds:0}}
function save(){localStorage.setItem(LS_KEY,JSON.stringify(state))}
function qState(id){return state.answers[id]||{seen:false,correct:null,attempts:0,interval:1,lastReviewed:null,nextReview:null,history:[]}}
function setTheme(t){document.documentElement.dataset.theme=t;localStorage.setItem('theme',t);state.settings.theme=t;save();document.getElementById('themeToggle').textContent=t==='dark'?'☀️ Modo claro':'🌙 Modo escuro'}
async function init(){questions=await fetch(DB_URL).then(r=>r.json());setTheme(state.settings.theme|| (matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'));bindNav();render('dashboard')}
function bindNav(){document.querySelectorAll('.nav-btn[data-view]').forEach(b=>b.onclick=()=>render(b.dataset.view));document.getElementById('themeToggle').onclick=()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark');document.getElementById('continueBtn').onclick=()=>startSession({mode:'continue'})}
function render(view){currentView=view;document.querySelectorAll('.nav-btn').forEach(b=>b.classList.toggle('active',b.dataset.view===view));document.getElementById('viewTitle').textContent={dashboard:'Dashboard',study:'Estudar',review:'Revisão inteligente',library:'Biblioteca',settings:'Ajustes'}[view]||'Simulados';({dashboard:renderDashboard,study:renderStudy,review:renderReview,library:renderLibrary,settings:renderSettings}[view]||renderDashboard)()}
function stats(){const total=questions.length;const ans=Object.values(state.answers);const done=ans.filter(a=>a.seen).length;const ok=ans.filter(a=>a.correct===true).length;const err=ans.filter(a=>a.correct===false).length;const due=questions.filter(q=>{const s=qState(q.id);return s.nextReview&&s.nextReview<=today()}).length;return{total,done,ok,err,due,acc:done?Math.round(ok/done*100):0}}
function by(arr,key){return arr.reduce((m,x)=>{const k=x[key]||'Não identificado';m[k]=(m[k]||0)+1;return m},{})}
function renderDashboard(){const s=stats(); const byMod=Object.entries(by(questions,'modulo')).sort((a,b)=>b[1]-a[1]).slice(0,10); const max=Math.max(...byMod.map(x=>x[1]),1); document.getElementById('content').innerHTML=`<div class="grid"><div class="card stat"><span>Total</span><strong>${s.total}</strong></div><div class="card stat"><span>Respondidas</span><strong>${s.done}</strong></div><div class="card stat"><span>Taxa de acerto</span><strong>${s.acc}%</strong></div><div class="card stat"><span>Revisões vencidas</span><strong>${s.due}</strong></div><div class="card wide"><h3>Desempenho por módulo</h3><div class="chart">${byMod.map(([k,v])=>`<div class="bar" style="height:${Math.max(8,v/max*190)}px"><small>${k.replace('Informativos ','')}</small></div>`).join('')}</div></div><div class="card side"><h3>Atividade 30 dias</h3><div class="heatmap">${heatmap()}</div><p class="muted">XP: <b>${state.xp}</b></p><button class="primary-btn" onclick="startSession({})">Iniciar sessão</button></div><div class="card full"><h3>Últimas sessões</h3>${sessionTable()}</div></div>`}
function heatmap(){const counts={};state.sessions.forEach(s=>counts[s.date]=(counts[s.date]||0)+s.total);let out='';for(let i=29;i>=0;i--){const d=addDays(today(),-i);const c=counts[d]||0;out+=`<span class="heat ${c>20?'h3':c>5?'h2':c>0?'h1':''}" title="${d}: ${c} questões"></span>`}return out}
function sessionTable(){if(!state.sessions.length)return'<p>Nenhuma sessão registrada ainda.</p>';return`<table class="table"><tr><th>Data</th><th>Módulo</th><th>Resultado</th></tr>${state.sessions.slice(-8).reverse().map(s=>`<tr><td>${s.date}</td><td>${s.label||'Sessão'}</td><td>${s.correct}/${s.total}</td></tr>`).join('')}</table>`}
function uniqueSorted(vals){return [...new Set(vals.filter(v=>v!==undefined&&v!==null&&String(v).trim()!==''))].sort((a,b)=>String(a).localeCompare(String(b),'pt-BR',{numeric:true}))}
function infoLabel(q){if(q.tipo==='edicao_extraordinaria')return `Ed. Extra ${q.informativo} STJ`; if(q.informativo)return `Info ${q.informativo} ${q.tribunal||''}`.trim(); return q.fonte||''}
function renderStudy(){
  const tribunais=uniqueSorted(questions.map(q=>q.tribunal));
  const cats=uniqueSorted(questions.map(q=>q.categoria));
  const mods=uniqueSorted(questions.map(q=>q.modulo));
  const infos=uniqueSorted(questions.filter(q=>q.informativo).map(q=>`${String(q.informativo).padStart(4,'0')}|${infoLabel(q)}|${q.informativo}|${q.tribunal||''}|${q.tipo||''}`));
  document.getElementById('content').innerHTML=`<div class="card"><h3>Monte sua sessão</h3><p class="eyebrow">Use o filtro por informativo para estudar exatamente um caderno, como Info 1162 STF ou Ed. Extra 28 STJ.</p><div class="filters"><input id="search" placeholder="Buscar enunciado, tema, fonte..."><select id="trib"><option value="">Todos tribunais</option>${tribunais.map(x=>`<option>${x}</option>`).join('')}</select><select id="cat"><option value="">Todas categorias</option>${cats.map(x=>`<option>${x}</option>`).join('')}</select><select id="mod"><option value="">Todos módulos</option>${mods.map(x=>`<option>${x}</option>`).join('')}</select><select id="info"><option value="">Todos informativos</option>${infos.map(raw=>{const [,label,num,trib,tipo]=raw.split('|');const value=`${num}|${trib}|${tipo}`;return `<option value="${value}">${label}</option>`}).join('')}</select><select id="mode"><option value="all">Todas</option><option value="unseen">Não vistas</option><option value="wrong">Erradas</option><option value="marked">Marcadas</option></select></div><br><button class="primary-btn" onclick="startSessionFromFilters()">Começar</button></div>`
}
function filtered(){
  const term=(document.getElementById('search')?.value||'').toLowerCase();
  const trib=document.getElementById('trib')?.value||'';
  const cat=document.getElementById('cat')?.value||'';
  const mod=document.getElementById('mod')?.value||'';
  const info=document.getElementById('info')?.value||'';
  const mode=document.getElementById('mode')?.value||'all';
  return questions.filter(q=>{
    const st=qState(q.id);
    if(trib&&q.tribunal!==trib)return false;
    if(cat&&q.categoria!==cat)return false;
    if(mod&&q.modulo!==mod)return false;
    if(info){const [num,t,tipo]=info.split('|');if(String(q.informativo)!==String(num)||String(q.tribunal||'')!==t||String(q.tipo||'')!==tipo)return false;}
    if(mode==='unseen'&&st.seen)return false;
    if(mode==='wrong'&&st.correct!==false)return false;
    if(mode==='marked'&&!state.marked[q.id])return false;
    if(term&&!(`${q.enunciado||''} ${q.tema||''} ${q.fonte||''} ${q.disciplina||''} ${q.modulo||''} ${q.informativo||''}`.toLowerCase().includes(term)))return false;
    return true
  })
}
function startSessionFromFilters(){const label=document.getElementById('info')?.selectedOptions?.[0]?.text || document.getElementById('mod').value || document.getElementById('cat').value || 'Sessão personalizada';startSession({list:filtered(),label})}
function startSession(opts={}){let list=opts.list;let startAt=0;if(!list){if(opts.mode==='continue'&&state.lastSession?.ids?.length){list=state.lastSession.ids.map(id=>questions.find(q=>q.id===id)).filter(Boolean);startAt=list.findIndex(q=>!qState(q.id).seen);if(startAt<0){list=questions.filter(q=>!qState(q.id).seen).slice(0,30);startAt=0}}else{list=questions.filter(q=>!qState(q.id).seen).slice(0,30)}} session=list.slice(0,50); currentIndex=Math.min(startAt,Math.max(session.length-1,0)); state.lastSession={ids:session.map(q=>q.id)}; save(); renderQuestion()}
function renderQuestion(){if(!session.length){document.getElementById('content').innerHTML='<div class="card"><h3>Nenhuma questão encontrada.</h3></div>';return} if(currentIndex>=session.length){finishSession();return} const q=session[currentIndex], st=qState(q.id), pct=Math.round(currentIndex/session.length*100); document.getElementById('viewTitle').textContent='Sessão de estudo'; document.getElementById('content').innerHTML=`<div class="card question-card"><div class="progress-bar"><span style="width:${pct}%"></span></div><p class="eyebrow">Questão ${currentIndex+1} de ${session.length}</p><div class="question-meta"><span>${q.modulo}</span><span>•</span><span>${q.fonte||''}</span><span>•</span><span>${q.disciplina||''}</span></div><div class="question-text">${escapeHtml(q.enunciado)}</div><div class="answers"><button class="answer-btn" onclick="answer('C')">CERTO</button><button class="answer-btn" onclick="answer('E')">ERRADO</button></div><div class="pill-row" style="margin-top:12px"><button class="pill ${state.marked[q.id]?'active':''}" onclick="toggleMark('${q.id}')">⭐ Marcar</button><button class="pill" onclick="currentIndex++;renderQuestion()">Pular</button></div><div id="feedback"></div></div>`}
function answer(resp){const q=session[currentIndex];const correct=q.respostaCorreta===resp;let st=qState(q.id);st.seen=true;st.correct=correct;st.attempts=(st.attempts||0)+1;st.lastReviewed=today();st.interval=correct?Math.max(2,(st.interval||1)*2):1;st.nextReview=addDays(today(),st.interval);st.history=[...(st.history||[]),{date:today(),resp,correct}];state.answers[q.id]=st;state.xp+=(correct?10:3);save();document.querySelectorAll('.answer-btn').forEach(b=>{const val=b.textContent.trim().charAt(0);if(val===q.respostaCorreta){b.classList.add('correct')}else if(val===resp){b.classList.add('wrong')}b.disabled=true});document.getElementById('feedback').innerHTML=`<div class="feedback"><b>${correct?'✅ Acertou':'❌ Errou'}.</b> Gabarito: <b>${q.respostaCorreta==='C'?'CERTO':'ERRADO'}</b><br><br>${escapeHtml(q.explicacao||'Sem explicação cadastrada.')}<br><br><small>${q.fonte||''}</small><br><button class="primary-btn" style="margin-top:12px" onclick="currentIndex++;renderQuestion()">Próxima</button></div>`}
function toggleMark(id){state.marked[id]=!state.marked[id];save();renderQuestion()}
function finishSession(){const ids=session.map(q=>q.id);const correct=ids.filter(id=>qState(id).correct===true).length;state.sessions.push({date:today(),label:'Sessão',total:ids.length,correct});save();document.getElementById('content').innerHTML=`<div class="card question-card"><h2>Sessão concluída</h2><p>Você acertou <b>${correct}</b> de <b>${ids.length}</b>.</p><p>XP atual: <b>${state.xp}</b></p><button class="primary-btn" onclick="render('dashboard')">Ver dashboard</button></div>`}
function renderReview(){const due=questions.filter(q=>{const s=qState(q.id);return s.nextReview&&s.nextReview<=today()});document.getElementById('content').innerHTML=`<div class="card"><h3>Revisões de hoje</h3><p>${due.length} questão(ões) vencidas para revisão.</p><button class="primary-btn" onclick='startSession({list:${JSON.stringify(due.map(q=>q.id))}.map(id=>questions.find(q=>q.id===id)).filter(Boolean),label:"Revisão"})'>Iniciar revisão</button></div>`}
function renderLibrary(){const cats=Object.entries(by(questions,'categoria')).sort();const mods=Object.entries(by(questions,'modulo')).sort();document.getElementById('content').innerHTML=`<div class="grid"><div class="card side"><h3>Categorias</h3>${cats.map(([k,v])=>`<p><b>${k}</b><br><span class="eyebrow">${v} questões</span></p>`).join('')}</div><div class="card wide"><h3>Módulos</h3><table class="table">${mods.map(([k,v])=>`<tr><td>${k}</td><td>${v}</td></tr>`).join('')}</table></div></div>`}
function renderSettings(){document.getElementById('content').innerHTML=`<div class="card"><h3>Dados e progresso</h3><p>Seu progresso fica salvo neste navegador.</p><button class="secondary-btn" onclick="exportProgress()">Exportar progresso</button> <button class="danger-btn" onclick="resetProgress()">Resetar tudo</button><br><br><textarea id="importBox" placeholder="Cole aqui um JSON de progresso para importar" style="width:100%;min-height:120px;border-radius:14px;padding:12px;background:var(--surface);color:var(--text);border:1px solid var(--line)"></textarea><br><button class="primary-btn" onclick="importProgress()">Importar progresso</button></div>`}
function exportProgress(){const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='progresso-simulados.json';a.click()}
function importProgress(){try{state=JSON.parse(document.getElementById('importBox').value);save();alert('Importado com sucesso.');render('dashboard')}catch(e){alert('JSON inválido.')}}
function resetProgress(){if(confirm('Tem certeza?')&&confirm('Confirma apagar todo o progresso?')){state=defaultState();save();render('dashboard')}}
function escapeHtml(s){return String(s||'').replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m])).replace(/\n/g,'<br>')}
init().catch(e=>{document.body.innerHTML='<pre style="padding:24px">Erro ao carregar data/questoes.json:\n'+e+'</pre>'})
'''


def main():
    PASTA_ASSETS.mkdir(parents=True, exist_ok=True)
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    (PASTA_SAIDA / "simulados").mkdir(parents=True, exist_ok=True)

    # Define o arquivo HTML de saída
    if fonte_filtrar:
        nome_arquivo = fonte_filtrar.lower().replace(" ", "-")
        caminho_html = PASTA_SAIDA / "simulados" / f"{nome_arquivo}.html"
    else:
        caminho_html = PASTA_SAIDA / "index.html"

    # Escreve os arquivos do site
    caminho_html.write_text(INDEX_HTML, encoding="utf-8")
    (PASTA_ASSETS / "styles.css").write_text(STYLES, encoding="utf-8")
    (PASTA_ASSETS / "app.js").write_text(APP_JS, encoding="utf-8")

    # Carrega todas as questões
    questoes = json.loads(ARQUIVO_QUESTOES.read_text(encoding="utf-8"))

    # Se veio --fonte, gera JSON filtrado para o HTML
    if fonte_filtrar:
        questoes = [
            q for q in questoes
            if fonte_filtrar.lower() in (q.get("fonte") or "").lower()
        ]

        print(f"🎯 Filtrando HTML: {fonte_filtrar} | {len(questoes)} questões")

        (PASTA_DADOS / "questoes.json").write_text(
            json.dumps(questoes, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # Caso normal: copia o JSON completo
    else:
        shutil.copy2(ARQUIVO_QUESTOES, PASTA_DADOS / "questoes.json")

    resumo = {
        "total": len(questoes),
        "modulos": len(set(q.get("modulo", "") for q in questoes)),
        "categorias": len(set(q.get("categoria", "") for q in questoes)),
    }

    print("✅ HTML final gerado com sucesso!")
    print(f"🌐 Abra: {caminho_html}")
    print(f'📊 Questões: {resumo["total"]} | Módulos: {resumo["modulos"]} | Categorias: {resumo["categorias"]}')

if __name__ == '__main__':
    main()

