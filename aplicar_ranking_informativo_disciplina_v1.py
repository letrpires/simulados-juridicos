from pathlib import Path
from datetime import datetime

APP_JS = Path("html_final/assets/app.js")
CSS = Path("html_final/assets/styles.css")

JS_APPEND = r"""
/* === Ranking por informativo + marcador por disciplina v1 === */
function disciplineClassName(disciplina){
  const raw = (disciplina || 'sem-disciplina').toString().normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  if(raw.includes('constitucional')) return 'disc-constitucional';
  if(raw.includes('administrativo')) return 'disc-administrativo';
  if(raw.includes('civil') && !raw.includes('process')) return 'disc-civil';
  if(raw.includes('processo civil') || raw.includes('processual civil')) return 'disc-proc-civil';
  if(raw.includes('penal') && !raw.includes('process')) return 'disc-penal';
  if(raw.includes('processo penal') || raw.includes('processual penal')) return 'disc-proc-penal';
  if(raw.includes('tribut')) return 'disc-tributario';
  if(raw.includes('empresarial')) return 'disc-empresarial';
  if(raw.includes('consumidor')) return 'disc-consumidor';
  if(raw.includes('ambiental')) return 'disc-ambiental';
  if(raw.includes('eleitoral')) return 'disc-eleitoral';
  if(raw.includes('human')) return 'disc-humanistica';
  return 'disc-generica';
}

function disciplineMarker(disciplina){
  if(!disciplina) return '';
  return `<span class="discipline-chip ${disciplineClassName(disciplina)}">${disciplina}</span>`;
}

function statsPorInformativoCompleto(){
  const mapa = {};

  questions.forEach(q=>{
    const nome = infoLabel(q) || q.fonte || q.modulo || 'Sem fonte';
    if(!mapa[nome]){
      mapa[nome] = {
        nome,
        total:0,
        feitas:0,
        acertos:0,
        erros:0,
        modulo:q.modulo || '',
        tribunal:q.tribunal || '',
        categoria:q.categoria || '',
        piorDisciplina:{nome:'', erros:0}
      };
    }

    mapa[nome].total++;
    const st = state.answers[q.id];

    if(st?.seen){
      mapa[nome].feitas++;
      if(st.correct){
        mapa[nome].acertos++;
      }else{
        mapa[nome].erros++;
      }
    }
  });

  Object.values(mapa).forEach(item=>{
    const errosDisc = {};
    questions.forEach(q=>{
      const nome = infoLabel(q) || q.fonte || q.modulo || 'Sem fonte';
      if(nome !== item.nome) return;
      const st = state.answers[q.id];
      if(st?.seen && st.correct === false){
        const d = q.disciplina || 'Sem disciplina';
        errosDisc[d] = (errosDisc[d] || 0) + 1;
      }
    });
    const pior = Object.entries(errosDisc).sort((a,b)=>b[1]-a[1])[0];
    if(pior) item.piorDisciplina = {nome:pior[0], erros:pior[1]};
  });

  return Object.values(mapa).map(s=>{
    s.taxaErro = s.feitas ? Math.round((s.erros / s.feitas) * 100) : 0;
    s.taxaAcerto = s.feitas ? Math.round((s.acertos / s.feitas) * 100) : 0;
    s.progresso = s.total ? Math.round((s.feitas / s.total) * 100) : 0;
    return s;
  });
}

function questoesDosPioresInformativos(){
  const piores = new Set(
    statsPorInformativoCompleto()
      .filter(s=>s.feitas > 0 && s.erros > 0)
      .sort((a,b)=>b.taxaErro-a.taxaErro || b.erros-a.erros)
      .slice(0,5)
      .map(s=>s.nome)
  );
  return questions.filter(q=>piores.has(infoLabel(q) || q.fonte || q.modulo));
}

function renderRankingInformativos(){
  const stats = statsPorInformativoCompleto()
    .filter(s=>s.feitas > 0)
    .sort((a,b)=>{
      if(b.taxaErro !== a.taxaErro) return b.taxaErro - a.taxaErro;
      return b.erros - a.erros;
    })
    .slice(0,12);

  if(!stats.length){
    return `
      <section class="card full">
        <h3>Ranking de atenção por informativo</h3>
        <p class="muted">Responda algumas questões para o ranking mostrar onde você mais erra.</p>
      </section>
    `;
  }

  return `
    <section class="card full">
      <div class="ranking-head">
        <div>
          <h3>Ranking de atenção por informativo</h3>
          <p class="muted">Mostra onde sua taxa de erro está maior. Use para priorizar revisão.</p>
        </div>
        <button class="ghost" onclick="startSession({list:questoesDosPioresInformativos(),label:'Revisão dos informativos com mais erros'})">Revisar piores</button>
      </div>
      <div class="ranking-list">
        ${stats.map((s,idx)=>`
          <div class="rank-item">
            <div class="rank-pos">${idx+1}</div>
            <div class="rank-main">
              <strong>${s.nome}</strong>
              <span>${s.modulo}</span>
              ${s.piorDisciplina.nome ? `<small>Pior disciplina: ${disciplineMarker(s.piorDisciplina.nome)} · ${s.piorDisciplina.erros} erro(s)</small>` : `<small>Sem padrão de disciplina identificado ainda</small>`}
              <div class="mini-progress"><span style="width:${s.progresso}%"></span></div>
            </div>
            <div class="rank-score">
              <strong>${s.taxaErro}%</strong>
              <span>erro</span>
              <small>${s.erros}/${s.feitas}</small>
            </div>
          </div>
        `).join('')}
      </div>
    </section>
  `;
}

function renderMarcadoresDisciplinaResumo(){
  const mapa = {};
  questions.forEach(q=>{
    const d = q.disciplina || 'Sem disciplina';
    if(!mapa[d]) mapa[d] = {total:0, feitas:0, erros:0};
    mapa[d].total++;
    const st = state.answers[q.id];
    if(st?.seen){
      mapa[d].feitas++;
      if(st.correct === false) mapa[d].erros++;
    }
  });

  const itens = Object.entries(mapa)
    .sort((a,b)=>b[1].erros-a[1].erros || b[1].total-a[1].total)
    .slice(0,18);

  return `
    <section class="card full">
      <h3>Marcadores por disciplina</h3>
      <p class="muted">Cores ajudam a identificar rapidamente temas recorrentes e pontos fracos.</p>
      <div class="discipline-cloud">
        ${itens.map(([nome,s])=>`
          <button class="discipline-chip ${disciplineClassName(nome)}" onclick='startSession({list:questions.filter(q=>(q.disciplina||"Sem disciplina")===${JSON.stringify(nome)}),label:${JSON.stringify(nome)}})'>
            ${nome}
            <small>${s.erros} erro(s) · ${s.feitas}/${s.total}</small>
          </button>
        `).join('')}
      </div>
    </section>
  `;
}

(function patchDashboardRanking(){
  const oldRenderDashboard = window.renderDashboard || renderDashboard;
  window.renderDashboard = function(){
    oldRenderDashboard();
    const content = document.getElementById('content');
    if(!content) return;
    if(!document.querySelector('.ranking-list') && !document.querySelector('.discipline-cloud')){
      content.insertAdjacentHTML('beforeend', renderRankingInformativos());
      content.insertAdjacentHTML('beforeend', renderMarcadoresDisciplinaResumo());
    }
  };
})();

(function patchQuestionDisciplineMarker(){
  const oldRenderQuestion = window.renderQuestion || renderQuestion;
  window.renderQuestion = function(){
    oldRenderQuestion();
    const q = session[currentIndex];
    if(!q) return;
    const meta = document.querySelector('.q-taxonomy') || document.querySelector('.question-meta') || document.querySelector('.q-meta');
    if(meta && q.disciplina && !meta.querySelector('.discipline-chip')){
      meta.insertAdjacentHTML('afterbegin', disciplineMarker(q.disciplina));
    }
  };
})();
"""

CSS_APPEND = r"""
/* === Ranking por informativo + marcador por disciplina v1 === */
.ranking-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:16px}
.ranking-list{display:grid;gap:12px}
.rank-item{display:grid;grid-template-columns:44px 1fr 92px;gap:14px;align-items:center;border:1px solid var(--border,var(--line));border-radius:18px;padding:14px;background:rgba(148,163,184,.08)}
.rank-pos{width:36px;height:36px;display:grid;place-items:center;border-radius:12px;background:rgba(249,115,22,.14);color:var(--orange);font-weight:900}
.rank-main strong{display:block;font-size:15px}
.rank-main span,.rank-main small{display:block;color:var(--muted);margin-top:3px}
.rank-score{text-align:right}
.rank-score strong{display:block;color:#ef4444;font-size:22px}
.rank-score span,.rank-score small{display:block;color:var(--muted);font-size:12px}
.mini-progress{height:8px;border-radius:999px;background:rgba(148,163,184,.18);margin-top:9px;overflow:hidden}
.mini-progress span{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,var(--orange),var(--orange-2))}
.discipline-cloud{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}
.discipline-chip{display:inline-flex;align-items:center;gap:8px;border-radius:999px;padding:8px 12px;font-size:13px;font-weight:800;border:1px solid rgba(148,163,184,.28);background:rgba(148,163,184,.10);color:var(--text)}
button.discipline-chip{cursor:pointer}
.discipline-chip small{opacity:.75;font-size:11px;font-weight:700}
.disc-constitucional{background:rgba(59,130,246,.13);border-color:rgba(59,130,246,.30);color:#60a5fa}
.disc-administrativo{background:rgba(249,115,22,.13);border-color:rgba(249,115,22,.32);color:#fb923c}
.disc-civil{background:rgba(168,85,247,.13);border-color:rgba(168,85,247,.30);color:#c084fc}
.disc-proc-civil{background:rgba(14,165,233,.13);border-color:rgba(14,165,233,.30);color:#38bdf8}
.disc-penal{background:rgba(239,68,68,.13);border-color:rgba(239,68,68,.30);color:#f87171}
.disc-proc-penal{background:rgba(244,63,94,.13);border-color:rgba(244,63,94,.30);color:#fb7185}
.disc-tributario{background:rgba(34,197,94,.13);border-color:rgba(34,197,94,.30);color:#4ade80}
.disc-empresarial{background:rgba(234,179,8,.13);border-color:rgba(234,179,8,.30);color:#facc15}
.disc-consumidor{background:rgba(20,184,166,.13);border-color:rgba(20,184,166,.30);color:#2dd4bf}
.disc-ambiental{background:rgba(16,185,129,.13);border-color:rgba(16,185,129,.30);color:#34d399}
.disc-eleitoral{background:rgba(99,102,241,.13);border-color:rgba(99,102,241,.30);color:#818cf8}
.disc-humanistica{background:rgba(236,72,153,.13);border-color:rgba(236,72,153,.30);color:#f472b6}
.disc-generica{background:rgba(148,163,184,.13);border-color:rgba(148,163,184,.30);color:#cbd5e1}
@media(max-width:720px){.ranking-head{flex-direction:column}.rank-item{grid-template-columns:34px 1fr}.rank-score{grid-column:2;text-align:left;display:flex;gap:8px;align-items:baseline}}
"""

def main():
    if not APP_JS.exists():
        raise SystemExit("❌ Não encontrei html_final/assets/app.js. Rode na pasta principal do projeto.")

    txt = APP_JS.read_text(encoding="utf-8")
    backup = APP_JS.with_suffix(f".backup_ranking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.js")
    backup.write_text(txt, encoding="utf-8")

    if "Ranking por informativo + marcador por disciplina v1" not in txt:
        APP_JS.write_text(txt + "\n\n" + JS_APPEND, encoding="utf-8")

    css = CSS.read_text(encoding="utf-8") if CSS.exists() else ""
    if "Ranking por informativo + marcador por disciplina v1" not in css:
        CSS.write_text(css + "\n\n" + CSS_APPEND, encoding="utf-8")

    print("✅ Ranking por informativo e marcadores por disciplina aplicados.")
    print("Abra o Dashboard para ver:")
    print("- Ranking dos informativos com maior erro")
    print("- Marcadores coloridos por disciplina")
    print(f"🧾 Backup do app.js: {backup}")
    print("Atualize o navegador com Command + Shift + R.")

if __name__ == "__main__":
    main()
