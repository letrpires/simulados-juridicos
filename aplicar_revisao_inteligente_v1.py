from pathlib import Path
from datetime import datetime

APP_JS = Path("html_final/assets/app.js")
CSS = Path("html_final/assets/styles.css")

JS_APPEND = r"""
/* === Revisão inteligente v1 === */
function smartLevel(st){
  if(!st || !st.seen) return {label:'Não visto', cls:'level-new'};
  if(st.correct===false) return {label:'Aprendendo', cls:'level-learning'};
  if((st.interval||1) >= 15) return {label:'Dominado', cls:'level-mastered'};
  return {label:'Revisando', cls:'level-reviewing'};
}
function reviewDueList(){
  return questions.filter(q=>{
    const st=qState(q.id);
    return st.nextReview && st.nextReview <= today();
  });
}
function manualMarkedList(){
  return questions.filter(q=>state.marked[q.id]);
}
function scheduleQuestionReview(q, correct){
  let st=qState(q.id);

  st.seen = true;
  st.correct = correct;
  st.attempts = (st.attempts || 0) + 1;
  st.lastReviewed = today();

  if(!st.history) st.history = [];
  st.history.push({
    date: today(),
    correct: correct
  });

  if(correct){
    const atual = st.interval || 1;
    st.interval = Math.min(atual * 2, 30);
    st.nextReview = addDays(today(), st.interval);
    state.xp = (state.xp || 0) + 10;
  }else{
    st.interval = 1;
    st.nextReview = addDays(today(), 1);
    state.xp = (state.xp || 0) + 3;
    state.marked[q.id] = true;
  }

  state.answers[q.id] = st;
  state.lastSession = {
    ids: session.map(x=>x.id),
    currentIndex: Math.min(currentIndex + 1, session.length - 1),
    updatedAt: new Date().toISOString()
  };

  save();
  return st;
}
function toggleReviewLater(){
  const q = session[currentIndex];
  if(!q) return;

  const isMarked = !!state.marked[q.id];

  if(isMarked){
    delete state.marked[q.id];
  }else{
    state.marked[q.id] = true;
    let st = qState(q.id);
    st.nextReview = today();
    st.interval = st.interval || 1;
    state.answers[q.id] = st;
  }

  save();
  renderQuestion();
}
function renderReviewSmart(){
  const due = reviewDueList();
  const marked = manualMarkedList();
  const merged = [...new Map([...due, ...marked].map(q=>[q.id,q])).values()];

  document.getElementById('content').innerHTML = `
    <section class="card study-builder">
      <div class="study-head">
        <div>
          <h2>Revisão inteligente</h2>
          <p class="muted">Questões erradas, marcadas ou vencidas na repetição espaçada aparecem aqui.</p>
        </div>
        <div class="pill-count">${merged.length} pendentes</div>
      </div>

      <div class="review-grid">
        <div class="review-stat">
          <strong>${due.length}</strong>
          <span>vencidas hoje</span>
        </div>
        <div class="review-stat">
          <strong>${marked.length}</strong>
          <span>marcadas</span>
        </div>
        <div class="review-stat">
          <strong>${state.xp || 0}</strong>
          <span>XP</span>
        </div>
      </div>

      <div class="session-actions">
        <button class="primary btn-start" onclick="startSession({list:reviewDueList(),label:'Revisão vencida'})">Revisar vencidas</button>
        <button class="ghost" onclick="startSession({list:manualMarkedList(),label:'Marcadas para revisar'})">Revisar marcadas</button>
        <button class="ghost" onclick="startSession({list:[...new Map([...reviewDueList(),...manualMarkedList()].map(q=>[q.id,q])).values()],label:'Revisão inteligente'})">Revisar tudo</button>
      </div>
    </section>

    <section class="card">
      <h3>Como funciona</h3>
      <p class="muted">
        Ao errar, a questão volta para revisão em 1 dia e fica marcada.
        Ao acertar, o intervalo dobra progressivamente até 30 dias.
        O botão “Revisar depois” envia a questão para esta tela.
      </p>
    </section>
  `;
}
function render(view){
  currentView=view;
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.toggle('active',b.dataset.view===view));
  const titleMap={dashboard:'Dashboard',study:'Estudar',review:'Revisão',library:'Biblioteca',settings:'Ajustes'};
  const title=document.getElementById('viewTitle');
  if(title) title.textContent=titleMap[view]||'Dashboard';

  if(view==='dashboard') return renderDashboard();
  if(view==='study') return renderStudy();
  if(view==='review') return renderReviewSmart();
  if(view==='library' && typeof renderLibrary==='function') return renderLibrary();
  if(view==='settings' && typeof renderSettings==='function') return renderSettings();

  return renderDashboard();
}
function renderQuestion(){
  if(!session.length){
    document.getElementById('content').innerHTML='<div class="card"><h3>Nenhuma questão encontrada.</h3><p class="muted">Ajuste os filtros e tente novamente.</p></div>';
    return;
  }

  const q = session[currentIndex];
  const st = qState(q.id);
  const lvl = smartLevel(st);
  const marked = !!state.marked[q.id];
  const prog = Math.round(((currentIndex+1)/session.length)*100);

  document.getElementById('content').innerHTML = `
    <section class="question-card card">
      <div class="progress"><span style="width:${prog}%"></span></div>

      <div class="q-meta">
        <span>Questão ${currentIndex+1} de ${session.length}</span>
        <span>${q.modulo || ''}</span>
        <span>${q.fonte || ''}</span>
        <span class="level-pill ${lvl.cls}">${lvl.label}</span>
      </div>

      ${(q.disciplina || q.tema) ? `
        <div class="q-taxonomy">
          ${q.disciplina ? `<span>${q.disciplina}</span>` : ''}
          ${q.tema ? `<span>${q.tema}</span>` : ''}
        </div>` : ''
      }

      <h2 class="q-text">${q.enunciado || 'Sem enunciado cadastrado.'}</h2>

      <div class="answers">
        <button class="answer-btn" onclick="answer('C')">CERTO</button>
        <button class="answer-btn" onclick="answer('E')">ERRADO</button>
      </div>

      <div class="q-actions">
        <button class="ghost" onclick="toggleReviewLater()">${marked ? '⭐ Remover revisão' : '⭐ Revisar depois'}</button>
        <button class="ghost" onclick="nextQuestion()">Pular</button>
      </div>

      <div id="feedback"></div>
    </section>
  `;
}
function answer(resp){
  const q = session[currentIndex];
  const correct = q.respostaCorreta === resp;
  const st = scheduleQuestionReview(q, correct);

  document.querySelectorAll('.answer-btn').forEach(b=>{
    const val = b.textContent.trim().charAt(0);
    if(val === q.respostaCorreta){
      b.classList.add('correct');
    }else if(val === resp){
      b.classList.add('wrong');
    }
    b.disabled = true;
  });

  const status = correct ? '✅ Acertou.' : `❌ Errou. Gabarito: ${q.respostaCorreta === 'C' ? 'CERTO' : 'ERRADO'}`;
  const agendada = st.nextReview ? `Próxima revisão: ${st.nextReview}` : '';

  document.getElementById('feedback').innerHTML = `
    <div class="feedback ${correct ? 'ok' : 'bad'}">
      <h3>${status}</h3>
      <p class="muted">${agendada}</p>
      <div class="explanation">${q.explicacao || 'Sem explicação cadastrada.'}</div>
      ${q.referencia ? `<p class="source-ref">${q.referencia}</p>` : ''}
      <button class="primary" onclick="nextQuestion()">Próxima questão</button>
    </div>
  `;
}
function nextQuestion(){
  if(currentIndex < session.length - 1){
    currentIndex++;
    if(state.lastSession){
      state.lastSession.currentIndex = currentIndex;
      state.lastSession.updatedAt = new Date().toISOString();
      save();
    }
    renderQuestion();
  }else{
    const ids = session.map(q=>q.id);
    const ok = ids.filter(id=>state.answers[id]?.correct===true).length;
    const total = ids.length;

    state.sessions.push({
      date: today(),
      label: state.lastSession?.label || 'Sessão',
      correct: ok,
      total: total
    });
    save();

    document.getElementById('content').innerHTML = `
      <section class="card finish-card">
        <h2>Sessão concluída</h2>
        <p class="muted">Você respondeu ${total} questão(ões).</p>
        <div class="review-grid">
          <div class="review-stat"><strong>${ok}</strong><span>acertos</span></div>
          <div class="review-stat"><strong>${total-ok}</strong><span>erros</span></div>
          <div class="review-stat"><strong>${Math.round((ok/Math.max(total,1))*100)}%</strong><span>aproveitamento</span></div>
        </div>
        <div class="session-actions">
          <button class="primary" onclick="render('study')">Nova sessão</button>
          <button class="ghost" onclick="render('review')">Ir para revisão</button>
        </div>
      </section>
    `;
  }
}
"""

CSS_APPEND = r"""
/* === Revisão inteligente v1 === */
.level-pill{
  display:inline-flex;
  align-items:center;
  border-radius:999px;
  padding:5px 10px;
  font-weight:800;
  font-size:12px;
  border:1px solid var(--border);
}
.level-new{color:#94a3b8;background:rgba(148,163,184,.12)}
.level-learning{color:#fb7185;background:rgba(251,113,133,.12);border-color:rgba(251,113,133,.28)}
.level-reviewing{color:#f97316;background:rgba(249,115,22,.12);border-color:rgba(249,115,22,.32)}
.level-mastered{color:#22c55e;background:rgba(34,197,94,.12);border-color:rgba(34,197,94,.28)}

.q-taxonomy{
  display:flex;
  flex-wrap:wrap;
  gap:8px;
  margin:14px 0 8px;
}
.q-taxonomy span{
  border:1px solid var(--border);
  border-radius:999px;
  padding:7px 11px;
  color:var(--muted);
  background:rgba(148,163,184,.08);
  font-size:13px;
}

.q-actions{
  display:flex;
  gap:10px;
  flex-wrap:wrap;
  margin-top:14px;
}
button.ghost{
  border:1px solid var(--border);
  background:transparent;
  color:var(--text);
  border-radius:14px;
  padding:11px 16px;
  font-weight:700;
  cursor:pointer;
}
button.ghost:hover{
  border-color:var(--orange);
  color:var(--orange);
}

.feedback{
  margin-top:18px;
  border-left:5px solid var(--orange);
  padding:18px;
  border-radius:16px;
  background:rgba(148,163,184,.10);
}
.feedback.ok{border-left-color:#22c55e}
.feedback.bad{border-left-color:#ef4444}
.explanation{
  line-height:1.75;
  margin:14px 0;
}
.source-ref{
  color:var(--muted);
  font-size:14px;
  border-top:1px solid var(--border);
  padding-top:10px;
}
.review-grid{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
  gap:12px;
  margin:18px 0;
}
.review-stat{
  border:1px solid var(--border);
  border-radius:18px;
  padding:16px;
  background:rgba(148,163,184,.08);
}
.review-stat strong{
  display:block;
  font-size:28px;
}
.review-stat span{
  color:var(--muted);
  font-size:14px;
}
.finish-card{
  max-width:760px;
}
"""

def main():
    if not APP_JS.exists():
        raise SystemExit("❌ Não encontrei html_final/assets/app.js. Rode na pasta principal do projeto.")

    txt = APP_JS.read_text(encoding="utf-8")
    backup = APP_JS.with_suffix(f".backup_revisao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.js")
    backup.write_text(txt, encoding="utf-8")

    if "Revisão inteligente v1" not in txt:
        APP_JS.write_text(txt + "\n\n" + JS_APPEND, encoding="utf-8")

    css = CSS.read_text(encoding="utf-8") if CSS.exists() else ""
    if "Revisão inteligente v1" not in css:
        CSS.write_text(css + "\n\n" + CSS_APPEND, encoding="utf-8")

    print("✅ Revisão inteligente aplicada.")
    print("Recursos adicionados:")
    print("- Botão Revisar depois")
    print("- Agendamento automático de revisão")
    print("- Tela Revisão inteligente")
    print("- Níveis: Não visto / Aprendendo / Revisando / Dominado")
    print(f"🧾 Backup do app.js: {backup}")
    print("Atualize o navegador com Command + Shift + R.")

if __name__ == "__main__":
    main()
