#!/usr/bin/env bash

set -euo pipefail

TOTAL=815
LOTE=25
INICIO=25

echo "🚀 GERANDO RG EM LOTES"
echo "======================"
echo "Começando do índice: $INICIO"

for ((i=INICIO; i<TOTAL; i+=LOTE))
do
  echo ""
  echo "📦 Lote iniciando em $i"

  python3 gerar_questoes_rg_repetitivos_limpo_v1.py \
    --tipo RG \
    --inicio $i \
    --limite $LOTE

  echo "✅ Lote $i concluído"
  sleep 5
done

echo ""
echo "🏁 RG FINALIZADO"
