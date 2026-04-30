from pathlib import Path
from datetime import datetime

APP_JS = Path("html_final/assets/app.js")
CSS = Path("html_final/assets/styles.css")

BLOCO_NOVO = """
function uniqueSorted(vals){
  return [...new Set(vals.filter(v=>v!==undefined&&v!==null&&String(v).trim()!==''))]
    .sort((a,b)=>String(a).localeCompare(String(b),'pt-BR',{numeric:true}));
}
function escapeHtml(s){
  return (s||'').toString().replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}
function infoLabel(q){
  if(q.tipo==='edicao_extraordinaria') return `Ed. Extra ${q.informativo} STJ`;
  if(q.tipo==='informativo' && q.informativo) return `Info ${q.informativo} ${q.tribunal||''}`.trim();
  return q.fonte || q.modulo || '';
}
function optionList(values, selected, allLabel){
  return `<option value="">${allLabel}</option>` + values.map(v=>`<option value="${escapeHtml(v)}" ${v===selected?'selected':''}>${escapeHtml(v)}</option>`).join('');
}
let filterState={term:'',tribunal:'',categoria:'',modulo:'',info:'',status:''};
function syncFilterStateFromDom(){
  filterState.term=document.getElementById('search')?.value||filterState.term||'';
  filterState.tribunal=document.getElementById('tribunal')?.value||'';
  filterState.categoria=document.getElementById('cat')?.value||'';
  filterState.modulo=document.getElementById('mod')?.value||'';
  filterState.info=document.getElementById('info')?.value||'';
  filterState.status=document.getElementById('status')?.value||'';
}
function matchesStatus(q,status){
  if(!status) return true;
  const st=qState(q.id);
  if(status==='unseen') return !st.seen;
  if(status==='wrong') return st.seen && st.correct===false;
  if(status==='marked') return !!state.marked[q.id];
  if(status==='review') return !!(st.nextReview && st.nextReview<=today());
  return true;
}
function matchesFilters(q,ignore=''){
  const f=filterState;
  const texto=[q.enunciado,q.explicacao,q.fonte,q.modulo,q.disciplina,q.tema].join(' ').toLowerCase();
  if(ignore!=='term' && f.term && !texto.includes(f.term.toLowerCase())) return false;
  if(ignore!=='tribunal' && f.tribunal && q.tribunal!==f.tribunal) return false;
  if(ignore!=='categoria' && f.categoria && q.categoria!==f.categoria) return false;
  if(ignore!=='modulo' && f.modulo && q.modulo!==f.modulo) return false;
  if(ignore!=='info' && f.info && infoLabel(q)!==f.info) return false;
  if(ignore!=='status' && !matchesStatus(q,f.status)) return false;
  return true;
}
function filtered(){return questions.filter(q=>matchesFilters(q))}
function renderStudy(){
  const tribunais=uniqueSorted(questions.filter(q=>matchesFilters(q,'tribunal')).map(q=>q.tribunal));
  const cats=uniqueSorted(questions.filter(q=>matchesFilters(q,'categoria')).map(q=>q.categoria));
  const mods=uniqueSorted(questions.filter(q=>matchesFilters(q,'modulo')).map(q=>q.modulo));
  const infos=uniqueSorted(questions.filter(q=>matchesFilters(q,'info')).map(infoLabel));
  const total=filtered().length;
  document.getElementById('content').innerHTML=`
    <section class="card study-builder">
      <div class="study-head">
        <div>
          <h2>Monte sua sessão</h2>
          <p class="muted">Filtre por tribunal, categoria, módulo e informativo. As opções se ajustam automaticamente.</p>
        </div>
        <div class="pill-count">${total} questões</div>
      </div>
      <div class="filters">
        <input id="search" placeholder="Buscar enunciado, tema, fonte" value="${escapeHtml(filterState.term)}">
        <select id="tribunal">${optionList(tribunais,filterState.tribunal,'Todos tribunais')}</select>
        <select id="cat">${optionList(cats,filterState.categoria,'Todas categorias')}</select>
        <select id="mod">${optionList(mods,filterState.modulo,'Todos módulos')}</select>
        <select id="info">${optionList(infos,filterState.info,'Todos informativos/cadernos')}</select>
        <select id="status">
          <option value="" ${!filterState.status?'selected':''}>Todas</option>
          <option value="unseen" ${filterState.status==='unseen'?'selected':''}>Não respondidas</option>
          <option value="wrong" ${filterState.status==='wrong'?'selected':''}>Erradas</option>
          <option value="marked" ${filterState.status==='marked'?'selected':''}>Marcadas</option>
          <option value="review" ${filterState.status==='review'?'selected':''}>Revisão vencida</option>
        </select>
      </div>
      <div class="session-actions">
        <button class="primary btn-start" onclick="startSessionFromFilters()">Começar sessão</button>
      </div>
    </section>`;
  const search=document.getElementById('search');
  if(search){
    search.addEventListener('input',(e)=>{
      filterState.term=e.target.value;
      const totalAtual=filtered().length;
      const pill=document.querySelector('.pill-count');
      if(pill) pill.textContent=`${totalAtual} questões`;
    });
  }
  ['tribunal','cat','mod','info','status'].forEach(id=>{
    const el=document.getElementById(id);
    if(!el) return;
    el.onchange=()=>{
      syncFilterStateFromDom();
      if(id==='tribunal'){filterState.categoria='';filterState.modulo='';filterState.info=''}
      if(id==='cat'){filterState.modulo='';filterState.info=''}
      if(id==='mod'){filterState.info=''}
      renderStudy();
    };
  });
}
"""

CSS_APPEND = """
/* === Ajustes finais: cinza + laranja, botões e filtros === */
:root{--orange:#f97316;--orange-2:#fb923c;--orange-dark:#ea580c;--graphite:#111827;--line:#e5e7eb}
[data-theme="light"]{--bg:#f5f5f4;--card:#fff;--text:#1f2937;--muted:#6b7280;--border:#e5e7eb;--primary:var(--orange)}
[data-theme="dark"]{--bg:#0f1115;--card:#181b20;--text:#f3f4f6;--muted:#a1a1aa;--border:#2f343d;--primary:var(--orange-2)}
.study-builder{border:1px solid var(--border);box-shadow:0 18px 45px rgba(15,17,21,.10)}
.study-head{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;margin-bottom:18px}
.pill-count{background:rgba(249,115,22,.12);color:var(--orange);border:1px solid rgba(249,115,22,.35);font-weight:800;padding:10px 14px;border-radius:999px;white-space:nowrap}
.filters{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;align-items:center}
.filters input,.filters select{min-height:46px;border-radius:14px;border:1px solid var(--border);background:var(--card);color:var(--text);padding:0 14px;font-size:15px;outline:none;transition:border .2s, box-shadow .2s}
.filters input:focus,.filters select:focus{border-color:var(--orange);box-shadow:0 0 0 4px rgba(249,115,22,.15)}
.session-actions{display:flex;justify-content:flex-end;margin-top:18px}
.btn-start,button.primary{background:linear-gradient(135deg,var(--orange),var(--orange-2));color:#fff;font-weight:800;border:none;border-radius:16px;padding:13px 22px;min-height:48px;box-shadow:0 12px 28px rgba(249,115,22,.28);transition:transform .18s,box-shadow .18s,filter .18s}
.btn-start:hover,button.primary:hover{transform:translateY(-1px);box-shadow:0 16px 36px rgba(249,115,22,.35);filter:saturate(1.05)}
.answer-btn.correct{border-color:#22c55e!important;background:rgba(34,197,94,.12)!important}
.answer-btn.wrong{border-color:#ef4444!important;background:rgba(239,68,68,.12)!important}
@media(max-width:720px){.study-head{flex-direction:column}.session-actions{justify-content:stretch}.btn-start{width:100%}}
"""

def main():
    if not APP_JS.exists():
        raise SystemExit("❌ Não encontrei html_final/assets/app.js. Rode na pasta principal do projeto.")
    txt=APP_JS.read_text(encoding="utf-8")
    backup=APP_JS.with_suffix(f".backup_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.js")
    backup.write_text(txt,encoding="utf-8")
    start=txt.find("function uniqueSorted")
    end=txt.find("function startSessionFromFilters")
    if start==-1 or end==-1 or end<=start:
        raise SystemExit("❌ Não localizei o bloco de filtros. Gere o HTML com v4 e rode novamente.")
    APP_JS.write_text(txt[:start]+BLOCO_NOVO+"\n"+txt[end:],encoding="utf-8")
    css=CSS.read_text(encoding="utf-8") if CSS.exists() else ""
    if "Ajustes finais: cinza + laranja" not in css:
        CSS.write_text(css+"\n\n"+CSS_APPEND,encoding="utf-8")
    print("✅ App corrigido: busca sem perder foco, filtros em cascata e visual cinza/laranja.")
    print(f"🧾 Backup do app.js: {backup}")
    print("Atualize o navegador com Command + Shift + R.")

if __name__=="__main__":
    main()
