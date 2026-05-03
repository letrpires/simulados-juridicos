#!/usr/bin/env bash
set -euo pipefail

echo "🚀 DEPLOY COMPLETO - SIMULADOS"
echo "=============================="

echo ""
echo "1) Rodando pipeline..."
./rodar_pipeline_inteligente.sh

echo ""
echo "2) Preparando docs para GitHub Pages..."
./preparar_docs_pages.sh

echo ""
echo "3) Enviando para GitHub..."
git add docs html_final data/questoes.json

if git diff --cached --quiet; then
  echo "✅ Nada novo para publicar."
  exit 0
fi

DATA_HORA=$(date +"%Y-%m-%d %H:%M")
git commit -m "update site ${DATA_HORA}"
git push

echo ""
echo "✅ Deploy finalizado."
