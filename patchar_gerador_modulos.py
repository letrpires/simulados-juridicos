from pathlib import Path
from datetime import datetime
import re

ARQ = Path("gerar_questoes_pendentes_api_seguro_v2.py")

txt = ARQ.read_text(encoding="utf-8")

backup = ARQ.with_name(
    f"gerar_questoes_pendentes_api_seguro_v2.backup_modulos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
)
backup.write_text(txt, encoding="utf-8")

funcao = r'''

# ============================================================
# BLINDAGEM DE MÓDULO POR CATEGORIA
# ============================================================

def definir_modulo_por_categoria(categoria, disciplina, modulo_original):
    mapa_area = {
        "Direito Administrativo": "Administrativo",
        "Direito Ambiental": "Ambiental",
        "Direito Civil": "Civil",
        "Direito do Consumidor": "Consumidor",
        "Direito Consumidor": "Consumidor",
        "Direito Empresarial": "Empresarial",
        "Direito Penal": "Penal",
        "Direito Processual Civil": "Processo Civil",
        "Direito Processual Penal": "Processo Penal",
        "Direito Tributário": "Tributário",
        "Direito Eleitoral": "Eleitoral",
        "Direito Constitucional": "Constitucional",
    }

    area = mapa_area.get(str(disciplina or "").strip(), "")

    if categoria == "Repercussão Geral":
        return f"RG - {area}" if area else "RG - Geral"

    if categoria == "Repetitivos":
        return f"Repetitivo - {area}" if area else "Repetitivos"

    return modulo_original


def validar_modulo_por_categoria(questao):
    categoria = questao.get("categoria")
    modulo = str(questao.get("modulo", ""))

    if categoria in ["Repercussão Geral", "Repetitivos"] and "Informativos" in modulo:
        raise ValueError(
            f"Erro crítico: {categoria} não pode ficar dentro de módulo de Informativos: {modulo}"
        )

'''

if "def definir_modulo_por_categoria" not in txt:
    marcador = "# ============================================================\n#"
    pos = txt.find(marcador)
    if pos == -1:
        raise SystemExit("❌ Não encontrei ponto seguro para inserir a função.")
    txt = txt[:pos] + funcao + "\n" + txt[pos:]

# troca padrões comuns de módulo no dicionário da questão
padroes = [
    r'"modulo"\s*:\s*modulo\s*,',
    r"'modulo'\s*:\s*modulo\s*,",
]

substituicao = '"modulo": definir_modulo_por_categoria(categoria, disciplina, modulo),'

trocou = 0
for padrao in padroes:
    txt, n = re.subn(padrao, substituicao, txt)
    trocou += n

if trocou == 0:
    raise SystemExit(
        "❌ Não encontrei exatamente '\"modulo\": modulo,'. "
        "Nenhuma alteração foi salva além do backup."
    )

# inserir validação logo após blocos comuns de criação de questão
if "validar_modulo_por_categoria(questao)" not in txt:
    padrao_questao = r'(questoes\.append\(questao\))'
    if re.search(padrao_questao, txt):
        txt = re.sub(
            padrao_questao,
            'validar_modulo_por_categoria(questao)\n        \\1',
            txt,
            count=1
        )
    else:
        print("⚠️ Não achei 'questoes.append(questao)'. Função inserida, mas validação não foi encaixada automaticamente.")

ARQ.write_text(txt, encoding="utf-8")

print("✅ Patch aplicado.")
print("Backup:", backup)
print("Ocorrências de módulo substituídas:", trocou)
