import re
import time
from pathlib import Path
from openai import OpenAI

# ============================
# CONFIGURAÇÕES
# ============================

PASTA_ENTRADA = Path("md_corrigidos_manualmente")
PASTA_SAIDA = Path("questoes_geradas_ok")
PASTA_ERROS = Path("erros_geracao")

PASTA_SAIDA.mkdir(exist_ok=True)
PASTA_ERROS.mkdir(exist_ok=True)

MODELO = "gpt-5.4-mini"

client = OpenAI()


# ============================
# EXTRAIR JULGADOS
# ============================

def extrair_julgados(texto: str):
    partes = re.split(r"(?=^## Julgado\s+\d+)", texto, flags=re.MULTILINE)
    return [p.strip() for p in partes if p.strip().startswith("## Julgado")]


def extrair_numero_julgado(julgado: str):
    match = re.search(r"## Julgado\s+(\d+)", julgado)
    return match.group(1) if match else "N/I"


def extrair_campo(julgado: str, campo: str):
    padrao = rf"\*\*{re.escape(campo)}:\*\*\s*(.*?)(?=\n\*\*|\Z)"
    match = re.search(padrao, julgado, flags=re.DOTALL)
    if not match:
        return "N/I"
    return match.group(1).strip()


# ============================
# PROMPT
# ============================

def montar_prompt(julgado: str):
    numero = extrair_numero_julgado(julgado)
    disciplina = extrair_campo(julgado, "Disciplina")
    subtema = extrair_campo(julgado, "Subtema")
    titulo = extrair_campo(julgado, "Título do julgado")
    tese = extrair_campo(julgado, "Tese / entendimento")
    referencia = extrair_campo(julgado, "Referência")

    return f"""
Você é examinador de concurso público jurídico, nível CEBRASPE.

Crie UMA questão de CERTO ou ERRADO para o julgado fornecido.

REGRAS OBRIGATÓRIAS:
1. Gere exatamente UMA questão.
2. O enunciado deve ser técnico, denso, plausível e com potencial de induzir erro.
3. Explore exceções, limites do entendimento, fundamentos legais, constitucionais ou processuais relevantes.
4. Evite questão óbvia ou meramente descritiva.
5. Não copie literalmente o título ou a tese.
6. Não use expressões como "segundo o julgado", "conforme o STJ" ou "conforme o STF" no enunciado.
7. Não invente informação que não esteja no julgado.
8. Misture, ao longo do arquivo, questões certas e erradas.
9. A justificativa deve ser robusta, fiel ao julgado e útil para revisão de concurso.
10. Não inclua comentários fora do formato pedido.

FORMATO OBRIGATÓRIO:

## Questão {numero}

[enunciado elaborado]

**Gabarito:** CERTO ou ERRADO

**Justificativa (robusta):**
[explicação aprofundada e fiel ao entendimento]

**Referência:**
{referencia}

---

DADOS DO JULGADO:

Disciplina: {disciplina}

Subtema: {subtema}

Título:
{titulo}

Tese / entendimento:
{tese}

Referência:
{referencia}
""".strip()


# ============================
# CHAMADA API
# ============================

def gerar_questao(julgado: str):
    prompt = montar_prompt(julgado)

    resposta = client.responses.create(
        model=MODELO,
        input=prompt,
        temperature=0.35,
        max_output_tokens=1400,
    )

    return resposta.output_text.strip()


# ============================
# PROCESSAR ARQUIVO
# ============================

def processar_arquivo(caminho: Path):
    print(f"\n📄 Processando: {caminho.name}")

    texto = caminho.read_text(encoding="utf-8")
    julgados = extrair_julgados(texto)

    if not julgados:
        print("⚠️ Nenhum julgado encontrado.")
        return

    nome_base = caminho.stem.replace("_limpo_estruturado", "")
    saida = PASTA_SAIDA / f"{nome_base}_questoes.md"

    linhas = []
    linhas.append(f"# Simulado - {nome_base}")
    linhas.append("")
    linhas.append(f"**Arquivo de origem:** {caminho.name}")
    linhas.append(f"**Total de julgados:** {len(julgados)}")
    linhas.append("")
    linhas.append("---")
    linhas.append("")

    # salva cabeçalho logo no início
    saida.write_text("\n".join(linhas), encoding="utf-8")

    for idx, julgado in enumerate(julgados, start=1):
        numero = extrair_numero_julgado(julgado)
        print(f"  Gerando questão {idx}/{len(julgados)} — Julgado {numero}")

        try:
            questao = gerar_questao(julgado)

            linhas.append(questao)
            linhas.append("")

            # SALVAMENTO INCREMENTAL
            # salva imediatamente após cada questão gerada
            saida.write_text("\n".join(linhas), encoding="utf-8")

            time.sleep(0.5)

        except Exception as e:
            print(f"  ❌ Erro no julgado {numero}: {e}")

            erro_path = PASTA_ERROS / f"{nome_base}_julgado_{numero}_erro.md"
            erro_path.write_text(julgado, encoding="utf-8")

            linhas.append(f"## Questão {numero}")
            linhas.append("")
            linhas.append("ERRO AO GERAR QUESTÃO.")
            linhas.append("")
            linhas.append(f"Erro: {e}")
            linhas.append("")
            linhas.append("---")
            linhas.append("")

            # salva também quando houver erro
            saida.write_text("\n".join(linhas), encoding="utf-8")

    print(f"✅ Salvo em: {saida}")


# ============================
# EXECUÇÃO
# ============================

def main():
    arquivos = sorted(PASTA_ENTRADA.glob("*.md"))

    if not arquivos:
        print("❌ Nenhum arquivo encontrado na pasta ok.")
        return

    print(f"📚 Arquivos OK encontrados: {len(arquivos)}")

    for arquivo in arquivos:
        processar_arquivo(arquivo)

    print("\n🎯 Geração finalizada.")
    print(f"Arquivos gerados em: {PASTA_SAIDA}")
    print(f"Erros, se houver, em: {PASTA_ERROS}")


if __name__ == "__main__":
    main()