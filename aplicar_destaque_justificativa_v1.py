from pathlib import Path
from datetime import datetime

APP_JS = Path("html_final/assets/app.js")
CSS = Path("html_final/assets/styles.css")

JS_APPEND = r"""
/* === Destaque inteligente de justificativa v1 === */
function splitSentences(text){
  return (text || '')
    .replace(/\s+/g,' ')
    .split(/(?<=[.!?])\s+/)
    .map(s=>s.trim())
    .filter(Boolean);
}
function normalizeWords(text){
  return (text || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g,'')
    .replace(/[^a-z0-9\s]/g,' ')
    .split(/\s+/)
    .filter(w=>w.length>4);
}
function smartHighlightExplanation(q, wasCorrect){
  const exp = q.explicacao || 'Sem explicação cadastrada.';
  const sentences = splitSentences(exp);

  if(sentences.length <= 1){
    return `<div class="explanation">${exp}</div>`;
  }

  const enWords = new Set(normalizeWords(q.enunciado));
  let scored = sentences.map((s, idx)=>{
    const words = normalizeWords(s);
    let score = 0;

    words.forEach(w=>{
      if(enWords.has(w)) score += 1;
    });

    const lower = s.toLowerCase();

    if(/portanto|assim|logo|desse modo|por isso|razão pela qual|entendimento|tese|firmou|fixou|consolidou|não se admite|é vedado|é possível|é legítimo|é ilegítimo/.test(lower)){
      score += 3;
    }

    if(!wasCorrect && /errad|incorret|contraria|não|vedad|inconstitucional|impossível|não cabe|não autoriza|não configura/.test(lower)){
      score += 4;
    }

    if(wasCorrect && /corret|certo|compatível|admite|possível|legítim|conforme|de acordo/.test(lower)){
      score += 3;
    }

    return {s, idx, score};
  });

  scored.sort((a,b)=>b.score-a.score);

  const highlightIdx = new Set(scored.slice(0,2).map(x=>x.idx));

  const rendered = sentences.map((s,idx)=>{
    if(highlightIdx.has(idx)){
      return `<p class="hl-sentence">${s}</p>`;
    }
    return `<p>${s}</p>`;
  }).join('');

  const label = wasCorrect
    ? 'Trecho-chave para fixar o entendimento'
    : 'Trecho-chave para entender o erro';

  return `
    <div class="smart-explanation">
      <div class="smart-label">✨ ${label}</div>
      ${rendered}
    </div>
  `;
}
(function patchSmartAnswer(){
  const oldAnswer = window.answer;
  window.answer = function(resp){
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
    const explicacao = smartHighlightExplanation(q, correct);

    document.getElementById('feedback').innerHTML = `
      <div class="feedback ${correct ? 'ok' : 'bad'}">
        <h3>${status}</h3>
        <p class="muted">${agendada}</p>
        ${explicacao}
        ${q.referencia ? `<p class="source-ref">${q.referencia}</p>` : ''}
        <button class="primary" onclick="nextQuestion()">Próxima questão</button>
      </div>
    `;
  };
})();
"""

CSS_APPEND = r"""
/* === Destaque inteligente de justificativa v1 === */
.smart-explanation{
  line-height:1.75;
  margin:16px 0;
}
.smart-label{
  display:inline-flex;
  align-items:center;
  gap:6px;
  margin-bottom:10px;
  padding:7px 11px;
  border-radius:999px;
  font-size:13px;
  font-weight:800;
  color:var(--orange);
  background:rgba(249,115,22,.12);
  border:1px solid rgba(249,115,22,.28);
}
.smart-explanation p{
  margin:10px 0;
}
.hl-sentence{
  padding:12px 14px;
  border-radius:14px;
  background:linear-gradient(135deg, rgba(249,115,22,.16), rgba(251,146,60,.08));
  border:1px solid rgba(249,115,22,.30);
  box-shadow:0 10px 24px rgba(249,115,22,.10);
}
.feedback.bad .hl-sentence{
  background:linear-gradient(135deg, rgba(239,68,68,.15), rgba(249,115,22,.08));
  border-color:rgba(239,68,68,.30);
}
"""

def main():
    if not APP_JS.exists():
        raise SystemExit("❌ Não encontrei html_final/assets/app.js. Rode na pasta principal do projeto.")

    txt = APP_JS.read_text(encoding="utf-8")
    backup = APP_JS.with_suffix(f".backup_destaque_{datetime.now().strftime('%Y%m%d_%H%M%S')}.js")
    backup.write_text(txt, encoding="utf-8")

    if "Destaque inteligente de justificativa v1" not in txt:
        APP_JS.write_text(txt + "\n\n" + JS_APPEND, encoding="utf-8")

    css = CSS.read_text(encoding="utf-8") if CSS.exists() else ""
    if "Destaque inteligente de justificativa v1" not in css:
        CSS.write_text(css + "\n\n" + CSS_APPEND, encoding="utf-8")

    print("✅ Destaque inteligente aplicado.")
    print("Agora o feedback destaca trechos-chave da justificativa, especialmente quando houver erro.")
    print(f"🧾 Backup do app.js: {backup}")
    print("Atualize o navegador com Command + Shift + R.")

if __name__ == "__main__":
    main()
