# Auditoria de organização do projeto

Gerada em: 30/04/2026 14:27:25

## 1. Resumo executivo

- `data/questoes.json`: OK — 3926 questões
- `html_final/index.html`: OK
- `questoes_validadas_pdf/`: 130 arquivos
- `pdfs/`: 130 arquivos

## 2. PDFs que parecem novos ou sem correspondência final

- PDFs com correspondência final encontrada: **129**
- PDFs sem correspondência final encontrada: **0**

Nenhum PDF pendente encontrado.

## 3. Arquivos finais de questões

- Total de questões detectadas em `.md`: **3926**
- Arquivos sem bloco de questão: **0**
- Arquivos com DRY-RUN: **0**

## 4. Classificação de pastas e arquivos da raiz

### ESSENCIAL

- `data` (pasta, 3 arquivo(s), 5.6 MB) — JSON mestre e auditorias
- `html_final` (pasta, 67 arquivo(s), 7.3 MB) — site final publicado/usado
- `pdfs` (pasta, 130 arquivo(s), 103.6 MB) — PDFs originais
- `questoes_validadas_pdf` (pasta, 130 arquivo(s), 4.3 MB) — base final de questões validadas

### SCRIPT ESSENCIAL

- `atualizar_base_novos_pdfs_v1.py` (arquivo, 1 arquivo(s), 4.6 KB) — auditoria de PDFs novos
- `converter_pdf_md.py` (arquivo, 1 arquivo(s), 8.8 KB) — conversão PDF → MD
- `gerar_html_final_profissional_v4.py` (arquivo, 1 arquivo(s), 22.1 KB) — regenera html_final
- `gerar_json_questoes_v4.py` (arquivo, 1 arquivo(s), 17.6 KB) — gera data/questoes.json final
- `gerar_questoes_arquivos_grandes_api_v2.py` (arquivo, 1 arquivo(s), 19.0 KB) — geração de arquivos grandes RG/REP
- `gerar_questoes_pendentes_api_seguro_v2.py` (arquivo, 1 arquivo(s), 34.2 KB) — geração segura de questões por API
- `gerar_questoes_sumulas_api.py` (arquivo, 1 arquivo(s), 17.7 KB) — geração de questões de súmulas

### INTERMEDIÁRIA / GUARDAR POR ENQUANTO

- `auditoria_final` (pasta, 134 arquivo(s), 3.5 MB) — relatórios de auditoria
- `questoes_geradas_api_revisar` (pasta, 49 arquivo(s), 797.3 KB) — saídas de revisão da API
- `questoes_geradas_api_revisar_grandes` (pasta, 35 arquivo(s), 1.8 MB) — saídas de revisão para RG/REP grandes
- `questoes_geradas_api_revisar_sumulas` (pasta, 82 arquivo(s), 2.6 MB) — saídas de revisão de súmulas
- `sumulas_extraidas_md` (pasta, 25 arquivo(s), 540.3 KB) — extrações intermediárias de súmulas

### PATCH JÁ APLICADO / PODE ARQUIVAR

- `aplicar_destaque_justificativa_v1.py` (arquivo, 1 arquivo(s), 5.0 KB) — script usado para alterar app/css; não precisa para rodar o site
- `aplicar_ranking_informativo_disciplina_v1.py` (arquivo, 1 arquivo(s), 11.0 KB) — script usado para alterar app/css; não precisa para rodar o site
- `aplicar_revisao_inteligente_v1.py` (arquivo, 1 arquivo(s), 11.3 KB) — script usado para alterar app/css; não precisa para rodar o site
- `corrigir_app_final_v6.py` (arquivo, 1 arquivo(s), 8.2 KB) — script usado para alterar app/css; não precisa para rodar o site
- `corrigir_filtros_cascata_html_v2.py` (arquivo, 1 arquivo(s), 5.7 KB) — script usado para alterar app/css; não precisa para rodar o site

### ANTIGA / PODE ARQUIVAR

- `html_simulados` (pasta, 347 arquivo(s), 19.2 MB) — HTML antigo/versões anteriores
- `scripts antigos` (pasta, 114 arquivo(s), 2.0 MB) — scripts arquivados antigos

### ARQUIVO COMPACTADO / OPCIONAL

- `pdfs.zip` (arquivo, 1 arquivo(s), 99.0 MB) — backup/exportação
- `simulados_juridicos_final.zip` (arquivo, 1 arquivo(s), 1.2 MB) — backup/exportação

### SCRIPT / REVISAR

- `auditar_md_vs_html.py` (arquivo, 1 arquivo(s), 2.0 KB) — script Python não classificado
- `auditar_organizacao_projeto.py` (arquivo, 1 arquivo(s), 10.7 KB) — script Python não classificado
- `auditar_pdf_vs_md.py` (arquivo, 1 arquivo(s), 3.4 KB) — script Python não classificado
- `auditar_questoes.py` (arquivo, 1 arquivo(s), 2.1 KB) — script Python não classificado
- `auditoria_final_simulados_v2.py` (arquivo, 1 arquivo(s), 21.5 KB) — script Python não classificado
- `auditoria_refinada_pdf_md.py` (arquivo, 1 arquivo(s), 4.8 KB) — script Python não classificado
- `classificar_md.py` (arquivo, 1 arquivo(s), 1.4 KB) — script Python não classificado
- `converter_sumula_stj_limpa_para_padrao.py` (arquivo, 1 arquivo(s), 756.0 B) — script Python não classificado
- `copiar_questoes_validadas.py` (arquivo, 1 arquivo(s), 1.3 KB) — script Python não classificado
- `dividir_sumulas_stf_em_blocos.py` (arquivo, 1 arquivo(s), 3.3 KB) — script Python não classificado
- `extrair_pdf_bruto_criticos.py` (arquivo, 1 arquivo(s), 696.0 B) — script Python não classificado
- `extrair_sumulas_pdf_para_md.py` (arquivo, 1 arquivo(s), 5.6 KB) — script Python não classificado
- `extrair_sumulas_stj_corrigido.py` (arquivo, 1 arquivo(s), 6.4 KB) — script Python não classificado
- `extrair_sumulas_stj_corrigido_v2.py` (arquivo, 1 arquivo(s), 7.5 KB) — script Python não classificado
- `gerar_cadernos_premium.py` (arquivo, 1 arquivo(s), 20.1 KB) — script Python não classificado
- `gerar_html_final_profissional.py` (arquivo, 1 arquivo(s), 20.3 KB) — script Python não classificado
- `gerar_html_final_profissional_v3.py` (arquivo, 1 arquivo(s), 20.6 KB) — script Python não classificado
- `gerar_html_simulados.py` (arquivo, 1 arquivo(s), 16.8 KB) — script Python não classificado
- `gerar_json_questoes_v2.py` (arquivo, 1 arquivo(s), 14.7 KB) — script Python não classificado
- `gerar_json_questoes_v3.py` (arquivo, 1 arquivo(s), 12.9 KB) — script Python não classificado
- `gerar_questoes_arquivos_grandes_api.py` (arquivo, 1 arquivo(s), 15.4 KB) — script Python não classificado
- `gerar_questoes_extras.py` (arquivo, 1 arquivo(s), 2.7 KB) — script Python não classificado
- `gerar_questoes_ok.py` (arquivo, 1 arquivo(s), 5.5 KB) — script Python não classificado
- `gerar_questoes_pendentes_api_seguro.py` (arquivo, 1 arquivo(s), 31.5 KB) — script Python não classificado
- `limpar_sumulas_stj.py` (arquivo, 1 arquivo(s), 1.1 KB) — script Python não classificado
- `relatorio_md.py` (arquivo, 1 arquivo(s), 1.6 KB) — script Python não classificado

### REVISAR

- `controle_processamento` (pasta, 1 arquivo(s), 17.5 KB) — pasta não classificada
- `md_criticos_reprocessados` (pasta, 0 arquivo(s), 0.0 B) — pasta não classificada
- `ok` (pasta, 0 arquivo(s), 0.0 B) — pasta não classificada
- `repetitivos` (pasta, 0 arquivo(s), 0.0 B) — pasta não classificada
- `revisao_critica` (pasta, 0 arquivo(s), 0.0 B) — pasta não classificada
- `revisao_leve` (pasta, 0 arquivo(s), 0.0 B) — pasta não classificada
- `rg` (pasta, 0 arquivo(s), 0.0 B) — pasta não classificada
- `sumulas` (pasta, 0 arquivo(s), 0.0 B) — pasta não classificada

## 5. Recomendação prática

### Manter na raiz para rotina diária

- `data/`
- `html_final/`
- `pdfs/`
- `questoes_validadas_pdf/`
- `atualizar_base_novos_pdfs_v1.py`
- `converter_pdf_md.py`
- `gerar_html_final_profissional_v4.py`
- `gerar_json_questoes_v4.py`
- `gerar_questoes_arquivos_grandes_api_v2.py`
- `gerar_questoes_pendentes_api_seguro_v2.py`
- `gerar_questoes_sumulas_api.py`

### Não apagar ainda, mas pode mover para `arquivo_intermediario/` depois

- `auditoria_final/`
- `questoes_geradas_api_revisar/`
- `questoes_geradas_api_revisar_grandes/`
- `questoes_geradas_api_revisar_sumulas/`
- `sumulas_extraidas_md/`

### Pode arquivar quando estiver segura

- `html_simulados/`
- `scripts antigos/`
- scripts `aplicar_*.py` e `corrigir_*.py` já usados

**Não apague nada automaticamente ainda.** Use este relatório para decidir com calma.