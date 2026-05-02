const DB_URL='data/questoes.json';
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


function referenciaFinal(q){
  if(q.referencia && String(q.referencia).trim()){
    return String(q.referencia).trim();
  }

  if(q.categoria === "Informativos" && q.informativo){
    return `Informativo ${q.informativo} ${q.tribunal || ""}`.trim();
  }

  if(q.tipo === "edicao_extraordinaria" && q.informativo){
    return `Edição Extraordinária ${q.informativo} ${q.tribunal || ""}`.trim();
  }

  return q.fonte || "";
}

function limparExplicacaoFinal(txt){
  txt = String(txt || "");

  txt = txt
    .replace(/\*\*Justificativa\s*\(robusta\):\*\*/gi, "")
    .replace(/\*\*Justificativa:\*\*/gi, "")
    .replace(/^Justificativa\s*\(robusta\):\s*/gim, "")
    .replace(/^Justificativa:\s*/gim, "")
    .replace(/\*\*/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  return escapeHtml(txt).replace(/\n/g, "<br>");
}

function renderQuestion(){if(!session.length){document.getElementById('content').innerHTML='<div class="card"><h3>Nenhuma questão encontrada.</h3></div>';return} if(currentIndex>=session.length){finishSession();return} const q=session[currentIndex], st=qState(q.id), pct=Math.round(currentIndex/session.length*100); document.getElementById('viewTitle').textContent='Sessão de estudo'; document.getElementById('content').innerHTML=`<div class="card question-card"><div class="progress-bar"><span style="width:${pct}%"></span></div><p class="eyebrow">Questão ${currentIndex+1} de ${session.length}</p><div class="question-meta"><span>${q.modulo}</span><span>•</span><span>${q.fonte||''}</span><span>•</span><span>${q.disciplina||''}</span></div><div class="question-text">${escapeHtml(q.enunciado)}</div><div class="answers"><button class="answer-btn" onclick="answer('C')">CERTO</button><button class="answer-btn" onclick="answer('E')">ERRADO</button></div><div class="pill-row" style="margin-top:12px"><button class="pill ${state.marked[q.id]?'active':''}" onclick="toggleMark('${q.id}')">⭐ Marcar</button><button class="pill" onclick="currentIndex++;renderQuestion()">Pular</button></div><div id="feedback"></div></div>`}
function answer(resp){const q=session[currentIndex];const correct=q.respostaCorreta===resp;let st=qState(q.id);st.seen=true;st.correct=correct;st.attempts=(st.attempts||0)+1;st.lastReviewed=today();st.interval=correct?Math.max(2,(st.interval||1)*2):1;st.nextReview=addDays(today(),st.interval);st.history=[...(st.history||[]),{date:today(),resp,correct}];state.answers[q.id]=st;state.xp+=(correct?10:3);save();document.querySelectorAll('.answer-btn').forEach(b=>{const val=b.textContent.trim().charAt(0);if(val===q.respostaCorreta){b.classList.add('correct')}else if(val===resp){b.classList.add('wrong')}b.disabled=true});document.getElementById('feedback').innerHTML=`<div class="feedback"><b>${correct?'✅ Acertou':'❌ Errou'}.</b> Gabarito: <b>${q.respostaCorreta==='C'?'CERTO':'ERRADO'}</b><br><br>${limparExplicacaoFinal(q.explicacao||'Sem explicação cadastrada.')}<br><br><div class="referencia-box"><strong>Referência:</strong><br>${escapeHtml(referenciaFinal(q))}</div><br><button class="primary-btn" style="margin-top:12px" onclick="currentIndex++;renderQuestion()">Próxima</button></div>`}
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


/* === Ranking por informativo + filtro por disciplina + limpar filtros === */
let disciplinaFiltroExtra = "";

function fonteRanking(q){
  if (typeof infoLabel === "function") return infoLabel(q) || q.fonte || q.modulo || "Sem fonte";
  if (q.tipo === "edicao_extraordinaria") return `Ed. Extra ${q.informativo} ${q.tribunal || ""}`.trim();
  if (q.informativo) return `Info ${q.informativo} ${q.tribunal || ""}`.trim();
  return q.fonte || q.modulo || "Sem fonte";
}

const filteredOriginalSeguro = filtered;
filtered = function(){
  let lista = filteredOriginalSeguro();
  if (disciplinaFiltroExtra) {
    lista = lista.filter(q => (q.disciplina || "Sem disciplina") === disciplinaFiltroExtra);
  }
  return lista;
};

const renderStudyOriginalSeguro = renderStudy;
renderStudy = function(){
  renderStudyOriginalSeguro();

  const filters = document.querySelector(".filters");
  if (!filters || document.getElementById("disciplinaExtra")) return;

  const disciplinas = [...new Set(questions.map(q => q.disciplina || "Sem disciplina"))]
    .filter(Boolean)
    .sort((a,b)=>a.localeCompare(b, "pt-BR"));

  const select = document.createElement("select");
  select.id = "disciplinaExtra";
  select.className = "discipline-filter-extra";
  select.innerHTML =
    `<option value="">Todas disciplinas</option>` +
    disciplinas.map(d => `<option value="${d}" ${d===disciplinaFiltroExtra ? "selected" : ""}>${d}</option>`).join("");

  select.onchange = () => {
    disciplinaFiltroExtra = select.value;
    renderStudy();
  };

  const limpar = document.createElement("button");
  limpar.type = "button";
  limpar.className = "clear-filters-btn";
  limpar.textContent = "Limpar filtros";
  limpar.onclick = () => {
    disciplinaFiltroExtra = "";
    if (typeof filterState !== "undefined") {
      filterState.term = "";
      filterState.tribunal = "";
      filterState.categoria = "";
      filterState.modulo = "";
      filterState.info = "";
      filterState.status = "";
    }
    renderStudy();
  };

  filters.appendChild(select);
  filters.appendChild(limpar);
};

function rankingPorInformativoHTML(){
  const mapa = {};

  questions.forEach(q => {
    const nome = fonteRanking(q);
    if (!mapa[nome]) {
      mapa[nome] = { total:0, feitas:0, erros:0, acertos:0, modulo:q.modulo || "" };
    }

    mapa[nome].total++;

    const st = state.answers[q.id];
    if (st && st.seen) {
      mapa[nome].feitas++;
      if (st.correct === false) mapa[nome].erros++;
      if (st.correct === true) mapa[nome].acertos++;
    }
  });

  const linhas = Object.entries(mapa)
    .map(([nome,s]) => ({
      nome,
      ...s,
      taxaErro: s.feitas ? Math.round((s.erros / s.feitas) * 100) : 0
    }))
    .filter(s => s.feitas > 0)
    .sort((a,b) => b.taxaErro - a.taxaErro || b.erros - a.erros)
    .slice(0,10);

  if (!linhas.length) {
    return `
      <div class="card ranking-box">
        <h3>Ranking por informativo</h3>
        <p class="muted">Responda algumas questões para aparecer onde você mais erra.</p>
      </div>
    `;
  }

  return `
    <div class="card ranking-box">
      <h3>Ranking por informativo</h3>
      <p class="muted">Priorize os informativos com maior taxa de erro.</p>
      ${linhas.map(s => `
        <div class="rank-row">
          <div>
            <strong>${s.nome}</strong>
            <small>${s.modulo} · ${s.feitas}/${s.total} respondidas</small>
          </div>
          <div>
            <strong>${s.taxaErro}% erro</strong>
            <small>${s.erros} erro(s)</small>
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

const renderDashboardOriginalSeguro = renderDashboard;
renderDashboard = function(){
  renderDashboardOriginalSeguro();
  const content = document.getElementById("content");
  if (content && !document.querySelector(".ranking-box")) {
    content.insertAdjacentHTML("beforeend", rankingPorInformativoHTML());
  }
};


/* === AJUSTE FINAL SEGURO: dashboard limpo === */
function removerCardsIndesejados(){
  const content = document.getElementById("content");
  if(!content) return;

  document.querySelectorAll(".sidebar-sessions").forEach(el => el.remove());
  document.querySelectorAll("#disciplinaExtra, .discipline-filter-extra, .clear-filters-btn").forEach(el => el.remove());

  [...content.querySelectorAll(".card")].forEach(card => {
    const t = (card.textContent || "").toLowerCase();
    if(
      t.includes("atividade 30 dias") ||
      t.includes("últimas sessões") ||
      t.includes("ultimas sessões") ||
      t.includes("xp:")
    ){
      card.remove();
    }
  });
}

(function(){
  const renderDashboardAnterior = renderDashboard;
  renderDashboard = function(){
    renderDashboardAnterior();
    removerCardsIndesejados();
  };

  const renderStudyAnterior = renderStudy;
  renderStudy = function(){
    renderStudyAnterior();
    document.querySelectorAll("#disciplinaExtra, .discipline-filter-extra, .clear-filters-btn").forEach(el => el.remove());
  };
})();


/* === AJUSTE FINAL: filtros em cascata reais === */
function aplicarFiltrosCascataReais(){
  const tribunal = document.getElementById("tribunal");
  const categoria = document.getElementById("categoria");
  const modulo = document.getElementById("modulo") || document.getElementById("mod");
  const info = document.getElementById("info");

  if(!tribunal || !categoria || !modulo) return;

  const t = tribunal.value || "";
  const c = categoria.value || "";

  let base = questions.slice();

  if(t){
    base = base.filter(q => q.tribunal === t);
  }

  if(c){
    base = base.filter(q => q.categoria === c);
  }

  const modAtual = modulo.value || "";
  const mods = [...new Set(base.map(q => q.modulo).filter(Boolean))]
    .sort((a,b)=>String(a).localeCompare(String(b),"pt-BR",{numeric:true}));

  modulo.innerHTML =
    `<option value="">Todos módulos</option>` +
    mods.map(m => `<option value="${m}" ${m===modAtual ? "selected" : ""}>${m}</option>`).join("");

  if(modAtual && !mods.includes(modAtual)){
    modulo.value = "";
  }

  if(info){
    const moduloVal = modulo.value || "";
    let baseInfo = base.slice();

    if(moduloVal){
      baseInfo = baseInfo.filter(q => q.modulo === moduloVal);
    }

    const infoAtual = info.value || "";
    const infos = [...new Map(
      baseInfo
        .filter(q => q.informativo)
        .map(q => {
          const label = typeof infoLabel === "function"
            ? infoLabel(q)
            : `Info ${q.informativo} ${q.tribunal || ""}`.trim();

          return [String(q.informativo) + "|" + (q.tribunal || "") + "|" + (q.tipo || ""), {
            value: String(q.informativo),
            label
          }];
        })
    ).values()].sort((a,b)=>a.label.localeCompare(b.label,"pt-BR",{numeric:true}));

    info.innerHTML =
      `<option value="">Todos informativos</option>` +
      infos.map(i => `<option value="${i.value}" ${i.value===infoAtual ? "selected" : ""}>${i.label}</option>`).join("");

    if(infoAtual && !infos.some(i => i.value === infoAtual)){
      info.value = "";
    }
  }
}

(function(){
  const renderStudyAnteriorCascata = renderStudy;
  renderStudy = function(){
    renderStudyAnteriorCascata();
    aplicarFiltrosCascataReais();

    ["tribunal","categoria","modulo","mod"].forEach(id=>{
      const el = document.getElementById(id);
      if(el && !el.dataset.cascataFinal){
        el.dataset.cascataFinal = "1";
        const old = el.onchange;
        el.onchange = function(e){
          if(typeof old === "function") old.call(this,e);
          setTimeout(aplicarFiltrosCascataReais,0);
        };
      }
    });
  };
})();


/* === FILTRO TRAVADO DEFINITIVO: tribunal -> categoria -> módulo -> informativo === */
function travarFiltrosDefinitivo(){
  const box = document.querySelector(".filters");
  if(!box || !window.questions) return;

  const selects = [...box.querySelectorAll("select")];
  if(selects.length < 4) return;

  const selTribunal = selects[0];
  const selCategoria = selects[1];
  const selModulo = selects[2];
  const selInfo = selects[3];

  const tribunal = selTribunal.value || "";
  const categoria = selCategoria.value || "";
  const moduloAtual = selModulo.value || "";
  const infoAtual = selInfo.value || "";

  let base = questions.slice();

  if(tribunal){
    base = base.filter(q => (q.tribunal || "") === tribunal);
  }

  if(categoria){
    base = base.filter(q => (q.categoria || "") === categoria);
  }

  const modulos = [...new Set(base.map(q => q.modulo).filter(Boolean))]
    .sort((a,b)=>String(a).localeCompare(String(b),"pt-BR",{numeric:true}));

  selModulo.innerHTML =
    `<option value="">Todos módulos</option>` +
    modulos.map(m => `<option value="${m}">${m}</option>`).join("");

  selModulo.value = modulos.includes(moduloAtual) ? moduloAtual : "";

  let baseInfo = base.slice();
  if(selModulo.value){
    baseInfo = baseInfo.filter(q => q.modulo === selModulo.value);
  }

  const infos = [...new Map(
    baseInfo
      .filter(q => q.informativo)
      .map(q => {
        const label = typeof infoLabel === "function"
          ? infoLabel(q)
          : `Info ${q.informativo} ${q.tribunal || ""}`.trim();

        return [label, {value:String(q.informativo), label}];
      })
  ).values()].sort((a,b)=>a.label.localeCompare(b.label,"pt-BR",{numeric:true}));

  selInfo.innerHTML =
    `<option value="">Todos informativos</option>` +
    infos.map(i => `<option value="${i.value}">${i.label}</option>`).join("");

  selInfo.value = infos.some(i => i.value === infoAtual) ? infoAtual : "";
}

(function(){
  const antigoRenderStudy = renderStudy;
  renderStudy = function(){
    antigoRenderStudy();
    travarFiltrosDefinitivo();

    const box = document.querySelector(".filters");
    if(!box) return;

    [...box.querySelectorAll("select")].forEach(sel=>{
      if(sel.dataset.filtroTravadoFinal) return;
      sel.dataset.filtroTravadoFinal = "1";

      const anterior = sel.onchange;
      sel.onchange = function(e){
        if(typeof anterior === "function") anterior.call(this,e);
        setTimeout(travarFiltrosDefinitivo, 0);
      };
    });
  };
})();


/* === TRAVA FINAL: categorias coerentes por tribunal === */
function categoriasPermitidasPorTribunal(tribunal){
  if(tribunal === "STF"){
    return ["Informativos", "Repercussão Geral", "Súmulas"];
  }
  if(tribunal === "STJ"){
    return ["Informativos", "Edição Extraordinária", "Repetitivos", "Súmulas"];
  }
  return null;
}

function aplicarTravaCategoriaTribunal(){
  const trib = document.getElementById("trib");
  const cat = document.getElementById("cat");
  if(!trib || !cat || !window.questions) return;

  const tribunal = trib.value || "";
  const atual = cat.value || "";

  let categorias = [...new Set(
    questions
      .filter(q => !tribunal || q.tribunal === tribunal)
      .map(q => q.categoria)
      .filter(Boolean)
  )];

  const permitidas = categoriasPermitidasPorTribunal(tribunal);
  if(permitidas){
    categorias = categorias.filter(c => permitidas.includes(c));
  }

  categorias.sort((a,b)=>String(a).localeCompare(String(b),"pt-BR",{numeric:true}));

  cat.innerHTML =
    `<option value="">Todas categorias</option>` +
    categorias.map(c => `<option value="${c}">${c}</option>`).join("");

  cat.value = categorias.includes(atual) ? atual : "";
}

(function(){
  const renderStudyAnteriorTravaCat = renderStudy;
  renderStudy = function(){
    renderStudyAnteriorTravaCat();
    aplicarTravaCategoriaTribunal();

    const trib = document.getElementById("trib");
    if(trib && !trib.dataset.travaCategoriaFinal){
      trib.dataset.travaCategoriaFinal = "1";
      const old = trib.onchange;
      trib.onchange = function(e){
        if(typeof old === "function") old.call(this,e);
        setTimeout(aplicarTravaCategoriaTribunal, 0);
      };
    }
  };
})();


/* === TRAVA REAL FINAL DOS FILTROS === */
function categoriasPermitidasFinal(tribunal){
  if(tribunal === "STF"){
    return ["Informativos", "Repercussão Geral", "Súmulas"];
  }
  if(tribunal === "STJ"){
    return ["Informativos", "Edição Extraordinária", "Repetitivos", "Súmulas"];
  }
  return null;
}

function refazerFiltrosTravadosFinal(){
  const trib = document.getElementById("trib");
  const cat = document.getElementById("cat");
  const mod = document.getElementById("mod");
  const info = document.getElementById("info");

  if(!trib || !cat || !mod || !info || typeof questions === "undefined") return;

  const tribunal = trib.value || "";
  const catAtual = cat.value || "";
  const modAtual = mod.value || "";
  const infoAtual = info.value || "";

  let base = questions.slice();

  if(tribunal){
    base = base.filter(q => q.tribunal === tribunal);
  }

  let categorias = [...new Set(base.map(q => q.categoria).filter(Boolean))];

  const permitidas = categoriasPermitidasFinal(tribunal);
  if(permitidas){
    categorias = categorias.filter(c => permitidas.includes(c));
  }

  categorias.sort((a,b)=>String(a).localeCompare(String(b),"pt-BR",{numeric:true}));

  cat.innerHTML =
    `<option value="">Todas categorias</option>` +
    categorias.map(c => `<option value="${c}">${c}</option>`).join("");

  cat.value = categorias.includes(catAtual) ? catAtual : "";

  let baseMod = base.slice();

  if(cat.value){
    baseMod = baseMod.filter(q => q.categoria === cat.value);
  }

  const modulos = [...new Set(baseMod.map(q => q.modulo).filter(Boolean))]
    .sort((a,b)=>String(a).localeCompare(String(b),"pt-BR",{numeric:true}));

  mod.innerHTML =
    `<option value="">Todos módulos</option>` +
    modulos.map(m => `<option value="${m}">${m}</option>`).join("");

  mod.value = modulos.includes(modAtual) ? modAtual : "";

  let baseInfo = baseMod.slice();

  if(mod.value){
    baseInfo = baseInfo.filter(q => q.modulo === mod.value);
  }

  const infos = [...new Map(
    baseInfo
      .filter(q => q.informativo)
      .map(q => {
        const value = `${q.informativo}|${q.tribunal || ""}|${q.tipo || ""}`;
        const label = typeof infoLabel === "function"
          ? infoLabel(q)
          : `Info ${q.informativo} ${q.tribunal || ""}`.trim();
        return [value, {value, label}];
      })
  ).values()].sort((a,b)=>a.label.localeCompare(b.label,"pt-BR",{numeric:true}));

  info.innerHTML =
    `<option value="">Todos informativos</option>` +
    infos.map(i => `<option value="${i.value}">${i.label}</option>`).join("");

  info.value = infos.some(i => i.value === infoAtual) ? infoAtual : "";
}

(function(){
  const renderStudyAntesDaTravaReal = renderStudy;

  renderStudy = function(){
    renderStudyAntesDaTravaReal();
    setTimeout(refazerFiltrosTravadosFinal, 0);
  };

  document.addEventListener("change", function(e){
    if(["trib","cat","mod"].includes(e.target.id)){
      setTimeout(refazerFiltrosTravadosFinal, 0);
    }
  }, true);
})();


/* === BUSCA FINAL: enunciado + justificativa + referência === */
filtered = function(){
  const norm = s => String(s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g,"");

  const term = norm(document.getElementById("search")?.value || "").trim();
  const trib = document.getElementById("trib")?.value || "";
  const cat = document.getElementById("cat")?.value || "";
  const mod = document.getElementById("mod")?.value || "";
  const info = document.getElementById("info")?.value || "";
  const mode = document.getElementById("mode")?.value || "all";

  return questions.filter(q => {
    const texto = norm([
      q.enunciado,
      q.explicacao,
      q.justificativa,
      q.referencia,
      q.fonte,
      q.modulo,
      q.disciplina,
      q.tema,
      q.categoria,
      q.tribunal
    ].join(" "));

    if(term && !texto.includes(term)) return false;
    if(trib && q.tribunal !== trib) return false;
    if(cat && q.categoria !== cat) return false;
    if(mod && q.modulo !== mod) return false;

    if(info){
      const [num, tr, tipo] = info.split("|");
      if(String(q.informativo || "") !== num) return false;
      if((q.tribunal || "") !== tr) return false;
      if((q.tipo || "") !== tipo) return false;
    }

    const st = qState(q.id);
    if(mode === "unseen" && st.seen) return false;
    if(mode === "wrong" && st.correct !== false) return false;
    if(mode === "marked" && !state.marked[q.id]) return false;

    return true;
  });
};
