#!/usr/bin/env bash
set -euo pipefail

echo "🚀 PUBLICAÇÃO DO SITE DE SIMULADOS"
echo "================================="

echo ""
echo "🔄 1) Rodando pipeline antes de publicar..."
./rodar_pipeline_inteligente.sh

echo ""
echo "🧪 2) Conferindo arquivos principais..."

if [ ! -f "html_final/menu.html" ]; then
  echo "❌ Erro: html_final/menu.html não encontrado."
  exit 1
fi

if [ ! -f "html_final/data/questoes.json" ]; then
  echo "❌ Erro: html_final/data/questoes.json não encontrado."
  exit 1
fi

echo "✅ Arquivos principais encontrados."

echo ""
echo "📊 3) Status do Git:"
git status --short

echo ""
read -p "Deseja publicar essas alterações no GitHub? (s/N): " CONFIRMA

if [[ "$CONFIRMA" != "s" && "$CONFIRMA" != "S" ]]; then
  echo "⏸️ Publicação cancelada."
  exit 0
fi

echo ""
echo "📦 4) Preparando commit..."
git add .

MENSAGEM="Atualiza simulados - $(date '+%d/%m/%Y %H:%M')"

if git diff --cached --quiet; then
  echo "ℹ️ Nenhuma alteração para publicar."
  exit 0
fi

git commit -m "$MENSAGEM"

echo ""
echo "☁️ 5) Enviando para o GitHub..."
git push

echo ""
echo "✅ SITE PUBLICADO COM SUCESSO!"
echo "Agora aguarde alguns segundos/minutos para o GitHub Pages atualizar."
