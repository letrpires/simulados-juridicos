#!/usr/bin/env bash
set -euo pipefail

echo "🚀 DEPLOY COMPLETO - SIMULADOS"
echo "=============================="

echo ""
echo "1) Rodando pipeline..."
./rodar_pipeline_inteligente.sh

echo ""
echo "2) Validando JSON..."
python3 -m json.tool data/questoes.json > /dev/null || {
  echo "❌ JSON inválido. Abortando deploy."
  exit 1
}

echo ""
echo "3) Validando JavaScript..."
if command -v node >/dev/null 2>&1; then
  node --check html_final/assets/app.js || {
    echo "❌ Erro no app.js. Abortando deploy."
    exit 1
  }
else
  echo "⚠️ Node não instalado — pulando validação JS"
fi

echo ""
echo "4) Preparando docs para GitHub Pages..."
./preparar_docs_pages.sh

echo ""
echo "5) Garantindo app.js atualizado no docs..."
cp html_final/assets/app.js docs/assets/app.js

echo ""
echo "6) Enviando para GitHub..."
git add docs html_final data/questoes.json

if git diff --cached --quiet; then
  echo "✅ Nada novo para publicar."
  exit 0
fi

DATA_HORA=$(date +"%Y-%m-%d %H:%M")
git commit -m "update site ${DATA_HORA}"
git push

echo ""
echo "✅ Deploy finalizado com segurança."