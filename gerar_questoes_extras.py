from pathlib import Path
from openai import OpenAI
import time

client = OpenAI()

PASTA_ENTRADA = Path("md_extras")
PASTA_SAIDA = Path("questoes_extras")
PASTA_SAIDA.mkdir(exist_ok=True)

MODELO = "gpt-5-mini"


PROMPT_BASE = """
Você é examinador de concurso público jurídico, nível CEBRASPE.

Vou fornecer um arquivo em Markdown contendo:
- súmulas;
- temas de repercussão geral;
- temas repetitivos;
- teses jurídicas;
- enunciados jurisprudenciais.

Sua tarefa é transformar CADA ITEM em UMA questão de CERTO ou ERRADO.

REGRAS ABSOLUTAS:
1. Gere UMA questão para CADA item.
2. NÃO omita itens.
3. NÃO agrupe itens.
4. NÃO copie literalmente o enunciado original.
5. NÃO simplifique demais.
6. Use linguagem técnica, densa e plausível.
7. Misture itens CERTO e ERRADO.
8. Pode inverter a lógica do enunciado para criar questão errada.
9. Explore exceções, limites, competências, requisitos e pegadinhas clássicas.
10. Mantenha alto nível até o final.

FORMATO OBRIGATÓRIO:

# NOME_DO_ARQUIVO - Questões

---

## Questão X

[enunciado elaborado]

**Gabarito:** CERTO ou ERRADO

**Justificativa:**
[explicação clara, técnica e fiel ao item]

**Referência:**
[nome da súmula, tema ou enunciado]

---

Agora gere as questões com base no arquivo abaixo.
"""


def gerar_questoes(nome_arquivo, conteudo):
    resposta = client.responses.create(
        model=MODELO,
        input=[
            {
                "role": "system",
                "content": "Você gera questões jurídicas de alto nível em formato Markdown."
            },
            {
                "role": "user",
                "content": f"{PROMPT_BASE}\n\nArquivo: {nome_arquivo}\n\n{conteudo}"
            }
        ],
    )

    return resposta.output_text


def main():
    arquivos = sorted(PASTA_ENTRADA.glob("*.md"))

    if not arquivos:
        print("Nenhum arquivo .md encontrado em md_extras.")
        return

    print(f"Arquivos encontrados: {len(arquivos)}")

    for arquivo in arquivos:
        nome_saida = arquivo.stem.replace("_final", "").replace("_limpo", "") + "_questoes.md"
        caminho_saida = PASTA_SAIDA / nome_saida

        if caminho_saida.exists():
            print(f"Pulando, já existe: {caminho_saida.name}")
            continue

        print(f"\nGerando questões: {arquivo.name}")

        conteudo = arquivo.read_text(encoding="utf-8")

        try:
            questoes = gerar_questoes(arquivo.stem, conteudo)
            caminho_saida.write_text(questoes, encoding="utf-8")
            print(f"✔ Salvo: {caminho_saida.name}")
            time.sleep(2)

        except Exception as e:
            print(f"❌ Erro em {arquivo.name}: {e}")

    print("\nFinalizado.")


if __name__ == "__main__":
    main()
