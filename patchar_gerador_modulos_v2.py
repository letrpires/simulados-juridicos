from pathlib import Path
from datetime import datetime
import re

ARQ = Path("gerar_questoes_pendentes_api_seguro_v2.py")
txt = ARQ.read_text(encoding="utf-8")

backup = ARQ.with_name(
    f"gerar_questoes_pendentes_api_seguro_v2.backup_modulos_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
)
backup.write_text(txt, encoding="utf-8")

funcao = '''

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
    # insere depois do bloco de imports iniciais
    m = re.search(r"((?:^import .*\n|^from .* import .*\n)+)", txt, flags=re.M)
    if not m:
        raise SystemExit("❌ Não encontrei imports para inserir a função.")

    pos = m.end()
    txt = txt[:pos] + funcao + txt[pos:]

# substitui qualquer modulo simples no dict
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
        "❌ Não encontrei 'modulo: modulo' no arquivo. "
        "Backup criado, mas não salvei alteração."
    )

# tenta validar antes de append
if "validar_modulo_por_categoria(questao)" not in txt:
    txt, n = re.subn(
        r"(\n\s*)questoes\.append\(questao\)",
        r"\1validar_modulo_por_categoria(questao)\1questoes.append(questao)",
        txt,
        count=1
    )
    if n == 0:
        print("⚠️ Não achei questoes.append(questao). A validação ficará só no normalizador.")

ARQ.write_text(txt, encoding="utf-8")

print("✅ Patch aplicado.")
print("Backup:", backup)
print("Ocorrências de módulo substituídas:", trocou)
