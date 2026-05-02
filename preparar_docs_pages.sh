#!/usr/bin/env bash
set -euo pipefail

echo "🌐 Preparando pasta docs para GitHub Pages..."

# Garante que html_final não seja submódulo interno
rm -rf html_final/.git

# Recria docs do zero
rm -rf docs
cp -R html_final docs

# Garante que docs não vire submódulo
rm -rf docs/.git

echo "✅ Pasta docs atualizada com sucesso."
echo "📁 GitHub Pages deve usar: main /docs"
