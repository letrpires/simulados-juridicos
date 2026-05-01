#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Iniciando pipeline..."

echo "1) Renomeando PDFs..."
python3 renomear_pdfs_automatico_v3.py

echo "2) Processando PDFs..."
python3 atualizar_lote_pdfs_novos.py

echo "3) Corrigindo referências..."
python3 corrigir_referencias_json.py

echo "4) Auditando temas..."
python3 auditar_temas_informativos.py

echo "5) Gerando temas faltantes..."
python3 gerar_temas_faltantes.py

echo "6) Normalizando JSON..."
python3 normalizar_json.py

echo "7) Atualizando HTML..."
cp data/questoes.json html_final/data/questoes.json

echo "✅ Pipeline concluído com sucesso!"
