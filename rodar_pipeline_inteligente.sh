#!/usr/bin/env bash
set -euo pipefail

echo "🚀 PIPELINE INTELIGENTE - SIMULADOS"
echo "==================================="

echo ""
echo "📦 1) Backup preventivo do JSON atual..."
mkdir -p data/backups
DATA_HORA=$(date +"%Y%m%d_%H%M%S")

if [ -f "data/questoes.json" ]; then
  cp data/questoes.json "data/backups/questoes_backup_pipeline_${DATA_HORA}.json"
  echo "✅ Backup criado: data/backups/questoes_backup_pipeline_${DATA_HORA}.json"
else
  echo "⚠️ data/questoes.json ainda não existe. Pulando backup."
fi

echo ""
echo "🏷️ 2) Renomeando PDFs automaticamente..."
python3 renomear_pdfs_automatico_v3.py

echo ""
echo "📚 3) Detectando PDFs novos (DELTA HASH)..."
python3 controlar_delta_pdfs.py

if [ -f "data/pdfs_novos_detectados.txt" ]; then
  echo ""
  echo "🚀 Processando apenas PDFs novos..."
  python3 atualizar_lote_pdfs_novos.py
else
  echo "✅ Nenhum PDF novo para processar."
fi

echo ""
echo "⚡ 3.1) Gerando HTML apenas dos novos PDFs..."
echo ""
echo "⚡ 3.1) Gerando HTML apenas dos novos PDFs..."
# python3 gerar_html_por_pdf_novo.py

echo ""
echo "🧭 Gerando menu central..."
# python3 gerar_menu_central.py

echo ""
echo "🔎 4) Corrigindo referências..."
python3 corrigir_referencias_json.py

echo ""
echo "🧭 5) Auditando temas de Informativos..."
python3 auditar_temas_informativos.py

echo ""
echo "🧩 6) Gerando apenas temas faltantes..."
python3 gerar_temas_faltantes.py

echo ""
echo "🧼 7) Normalizando JSON..."
python3 normalizar_json.py

echo ""
echo "🌐 8) Atualizando JSON do site..."
cp data/questoes.json html_final/data/questoes.json

echo ""
echo "🧪 9) Validação final..."
python3 - <<'PY'
import json
from pathlib import Path
from collections import Counter

dados = json.loads(Path("data/questoes.json").read_text(encoding="utf-8"))

ids = Counter(q["id"] for q in dados)

print("Total:", len(dados))
print("IDs duplicados:", sum(1 for k,v in ids.items() if v > 1))
print("Referências vazias:", sum(1 for q in dados if not q.get("referencia")))
print("Disciplinas vazias:", sum(1 for q in dados if not q.get("disciplina")))
print("Módulos genéricos:", Counter(q.get("modulo") for q in dados if q.get("modulo") in ["Informativos STF", "Informativos STJ"]))
print("Respostas:", Counter(q.get("respostaCorreta") for q in dados))
print("Súmulas STF sem número:", sum(1 for q in dados if q.get("modulo") == "Súmulas STF" and q.get("referencia") == "Súmulas STF"))
print("Súmulas STJ sem número:", sum(1 for q in dados if q.get("modulo") == "Súmulas STJ" and q.get("referencia") == "Súmulas STJ"))
PY

echo ""
echo "💾 Registrando PDFs processados..."
python3 - <<'PY'
from pathlib import Path
import sys
sys.path.append(".")

import controlar_delta_pdfs as ctrl

arquivo = Path("data/pdfs_novos_detectados.txt")

if arquivo.exists():
    pdfs = [Path(l.strip()) for l in arquivo.read_text().splitlines() if l.strip()]
    ctrl.registrar_processados(pdfs)
    print("✅ Controle atualizado.")
else:
    print("ℹ️ Nada para registrar.")
PY

echo ""
echo "🔒 Aplicando trava final RG/Repetitivos..."
python3 trava_final_rg_repetitivos.py

echo ""
echo "🌐 Repreparando docs após trava final..."
./preparar_docs_pages.sh

echo ""
echo "✅ PIPELINE FINALIZADO COM SUCESSO"
echo "Agora teste o site antes de subir para o GitHub."
