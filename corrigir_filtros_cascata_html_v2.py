from pathlib import Path
import re
from datetime import datetime

APP_JS = Path("html_final/assets/app.js")

NOVO_BLOCO = r"""
function norm(v){return (v||'').toString().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase()}
function labelTipo(t){
  const mapa={
    informativo:'Informativos',
    edicao_extraordinaria:'Edição Extraordinária',
    repercussao_geral:'Repercussão Geral',
    repetitivo:'Repetitivos',
    sumula:'Súmulas'
  };
  return mapa[t]||t||'Não identificado';
}
function fonteLabel(q){
  if(q.tipo==='edicao_extraordinaria') return `Ed. Extra ${q.informativo||''} ${q.tribunal||''}`.trim();
  if(q.tipo==='informativo') return `Info ${q.informativo||''} ${q.tribunal||''}`.trim();
  return q.fonte || q.modulo || q.id;
}
function uniqueSorted(arr){
  return [...new Set(arr.filter(Boolean))].sort((a,b)=>a.localeCompare(b,'pt-BR',{numeric:true}));
}
function escapeHtml(s){
  return (s||'').toString().replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}
function optionList(values, selected, allLabel, labelFn=null){
  return `<option value="">${allLabel}</option>` + values.map(v=>`<option value="${escapeHtml(v)}" ${v===selected?'selected':''}>${escapeHtml(labelFn?labelFn(v):v)}</option>`).join('');
}
function selectedFilters(){
  return {
    term:(document.getElementById('search')?.value||'').toLowerCase(),
    tribunal:document.getElementById('tribunal')?.value||'',
    tipo:document.getElementById('cat')?.value||'',
    modulo:document.getElementById('mod')?.value||'',
    fonte:document.getElementById('info')?.value||'',
    status:document.getElementById('status')?.value||''
  };
}
function matchesFilters(q, f, ignore=''){
  const texto=[q.enunciado,q.explicacao,q.fonte,q.modulo,q.disciplina,q.tema].join(' ').toLowerCase();

  if(ignore!=='term' && f.term && !texto.includes(f.term)) return false;
  if(ignore!=='tribunal' && f.tribunal && q.tribunal!==f.tribunal) return false;
  if(ignore!=='tipo' && f.tipo && q.tipo!==f.tipo) return false;
  if(ignore!=='modulo' && f.modulo && q.modulo!==f.modulo) return false;
  if(ignore!=='fonte' && f.fonte && fonteLabel(q)!==f.fonte) return false;

  if(ignore!=='status' && f.status){
    const st=qState(q.id);
    if(f.status==='unseen' && st.seen) return false;
    if(f.status==='wrong' && !(st.seen && st.correct===false)) return false;
    if(f.status==='marked' && !state.marked[q.id]) return false;
    if(f.status==='review' && !(st.nextReview && st.nextReview<=today())) return false;
  }

  return true;
}
function renderStudy(){
  const f=selectedFilters();

  const tribunais=uniqueSorted(questions.filter(q=>matchesFilters(q,f,'tribunal')).map(q=>q.tribunal));
  const tipos=uniqueSorted(questions.filter(q=>matchesFilters(q,f,'tipo')).map(q=>q.tipo));
  const mods=uniqueSorted(questions.filter(q=>matchesFilters(q,f,'modulo')).map(q=>q.modulo));
  const fontes=uniqueSorted(questions.filter(q=>matchesFilters(q,f,'fonte')).map(fonteLabel));

  const total=filtered().length;

  document.getElementById('content').innerHTML=`
    <section class="card">
      <h2>Monte sua sessão</h2>
      <p class="muted">Os filtros funcionam em árvore: cada campo mostra apenas opções compatíveis com os anteriores.</p>

      <div class="filters">
        <input id="search" placeholder="Buscar enunciado, tema, fonte" value="${escapeHtml(f.term)}">
        <select id="tribunal">${optionList(tribunais,f.tribunal,'Todos tribunais')}</select>
        <select id="cat">${optionList(tipos,f.tipo,'Todas categorias',labelTipo)}</select>
        <select id="mod">${optionList(mods,f.modulo,'Todos módulos')}</select>
        <select id="info">${optionList(fontes,f.fonte,'Todos cadernos/fontes')}</select>
        <select id="status">
          <option value="" ${!f.status?'selected':''}>Todas</option>
          <option value="unseen" ${f.status==='unseen'?'selected':''}>Não respondidas</option>
          <option value="wrong" ${f.status==='wrong'?'selected':''}>Erradas</option>
          <option value="marked" ${f.status==='marked'?'selected':''}>Marcadas</option>
          <option value="review" ${f.status==='review'?'selected':''}>Revisão vencida</option>
        </select>
      </div>

      <div class="session-actions">
        <button class="primary" onclick="startSessionFromFilters()">Começar (${total})</button>
      </div>
    </section>`;

  ['search','tribunal','cat','mod','info','status'].forEach(id=>{
    const el=document.getElementById(id);
    if(!el) return;
    if(id==='search'){
      el.oninput=()=>renderStudy();
    } else {
      el.onchange=()=>renderStudy();
    }
  });
}
function filtered(){
  const f=selectedFilters();
  return questions.filter(q=>matchesFilters(q,f));
}
"""

def main():
    if not APP_JS.exists():
        raise SystemExit("❌ Não encontrei html_final/assets/app.js. Rode este script na pasta principal do projeto.")

    txt = APP_JS.read_text(encoding="utf-8")

    backup = APP_JS.with_suffix(f".backup_cascata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.js")
    backup.write_text(txt, encoding="utf-8")

    padrao = r"function renderStudy\(\).*?function filtered\(\).*?(?=function startSessionFromFilters\(\))"

    # Usa função no replace para evitar erro com sequências JS como \u no texto substituto.
    novo_txt, n = re.subn(padrao, lambda m: NOVO_BLOCO + "\n", txt, flags=re.S)

    if n == 0:
        raise SystemExit("❌ Não consegui localizar renderStudy/filtered no app.js. Recrie o HTML com v4 e rode novamente.")

    APP_JS.write_text(novo_txt, encoding="utf-8")
    print("✅ Filtros em cascata aplicados com sucesso.")
    print(f"🧾 Backup criado em: {backup}")
    print("Atualize o navegador com Command + Shift + R.")

if __name__ == "__main__":
    main()
