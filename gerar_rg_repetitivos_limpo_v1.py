import json
import re
from pathlib import Path
from datetime import datetime

RG_MD = Path("rg_temas.md")
REP_MD = Path("repetitivos_temas.md")

SAIDA_JSON = Path("data/rg_repetitivos_base_limpa.json")
SAIDA_RELATORIO = Path("relatorio_rg_repetitivos_base_limpa.txt")

def limpar(txt):
    txt = re.sub(r"\n{3,}", "\n\n", str(txt).strip())
    return txt

def tese_invalida(txt):
    t = txt.lower()
    bloqueios = [
        "[matéria ainda não julgada]",
        "materia ainda nao julgada",
        "aguardando julgamento",
        "ainda aguarda julgamento",
        "aguardando a publicação do acórdão",
        "aguardando publicacao do acordao",
        "não foi fixada tese",
        "nao foi fixada tese",
        "sem tese firmada",
        "sem tese definida",
        "mérito ainda não julgado",
        "merito ainda nao julgado",
    ]
    return any(b in t for b in bloqueios)

def parse_rg():
    txt = RG_MD.read_text(encoding="utf-8", errors="ignore")
    partes = re.split(r"\n(?=STF\s*\nRepercussão\s*\nTema\s+\d+)", txt)

    itens = []
    ignorados = []

    for bloco in partes:
        bloco = bloco.strip()
        if not bloco:
            continue

        m = re.search(r"Tema\s+(\d+)", bloco)
        if not m:
            continue

        num = int(m.group(1))

        julgamento = ""
        mj = re.search(r"Julgamento:\s*\n\s*([0-9]{2}/[0-9]{4})", bloco)
        if mj:
            julgamento = mj.group(1)

        mt = re.search(r"TESE DE REPERCUSSÃO GERAL\s*(.*)", bloco, re.S | re.I)
        tese = limpar(mt.group(1)) if mt else ""

        if not tese or tese_invalida(tese):
            ignorados.append(("RG", num, "sem tese válida"))
            continue

        itens.append({
            "id_base": f"stf-rg-tema-{num}",
            "categoria": "Repercussão Geral",
            "modulo": "Repercussão Geral",
            "tribunal": "STF",
            "tema_numero": num,
            "tema": f"Tema {num}",
            "referencia": f"Tema {num} - STF - Repercussão Geral",
            "julgamento": julgamento,
            "tese": tese,
            "origem": "rg_temas.md",
        })

    return itens, ignorados

def parse_repetitivos():
    txt = REP_MD.read_text(encoding="utf-8", errors="ignore")
    partes = re.split(r"\n(?=STJ\s*\n(?:Repetitivo\s*\n)?Tema\s+Repetitivo\s+\d+)", txt)

    itens = []
    ignorados = []

    for bloco in partes:
        bloco = bloco.strip()
        if not bloco:
            continue

        m = re.search(r"Tema\s+Repetitivo\s+(\d+)", bloco, re.I)
        if not m:
            continue

        num = int(m.group(1))

        linhas = [l.strip() for l in bloco.splitlines() if l.strip()]
        # esperado:
        # STJ
        # Tema Repetitivo 1405
        # Status
        # Data
        status = linhas[2] if len(linhas) > 2 else ""
        data = linhas[3] if len(linhas) > 3 else ""

        # tese = tudo após as 4 primeiras linhas úteis
        tese = "\n".join(linhas[4:]).strip() if len(linhas) > 4 else ""
        tese = limpar(tese)

        if not tese or tese_invalida(tese):
            ignorados.append(("Repetitivos", num, "sem tese válida"))
            continue

        itens.append({
            "id_base": f"stj-rep-tema-{num}",
            "categoria": "Repetitivos",
            "modulo": "Repetitivos",
            "tribunal": "STJ",
            "tema_numero": num,
            "tema": f"Tema Repetitivo {num}",
            "referencia": f"Tema Repetitivo {num} - STJ",
            "status": status,
            "julgamento": data,
            "tese": tese,
            "origem": "repetitivos_temas.md",
        })

    return itens, ignorados

def main():
    if not RG_MD.exists():
        raise SystemExit("❌ Não achei rg_temas.md")
    if not REP_MD.exists():
        raise SystemExit("❌ Não achei repetitivos_temas.md")

    rg, ign_rg = parse_rg()
    rep, ign_rep = parse_repetitivos()

    base = rg + rep

    SAIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    SAIDA_JSON.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")

    rel = []
    rel.append("RELATÓRIO — BASE LIMPA RG / REPETITIVOS")
    rel.append("======================================")
    rel.append("")
    rel.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    rel.append("")
    rel.append(f"RG válidos: {len(rg)}")
    rel.append(f"Repetitivos válidos: {len(rep)}")
    rel.append(f"Total válido: {len(base)}")
    rel.append("")
    rel.append(f"RG ignorados: {len(ign_rg)}")
    rel.append(f"Repetitivos ignorados: {len(ign_rep)}")
    rel.append("")
    rel.append("Primeiros RG:")
    rel.extend([f"- Tema {x['tema_numero']}" for x in rg[:20]])
    rel.append("")
    rel.append("Primeiros Repetitivos:")
    rel.extend([f"- Tema Repetitivo {x['tema_numero']}" for x in rep[:20]])
    rel.append("")
    rel.append("Ignorados:")
    for tipo, num, motivo in (ign_rg + ign_rep)[:200]:
        rel.append(f"- {tipo} {num}: {motivo}")

    SAIDA_RELATORIO.write_text("\n".join(rel) + "\n", encoding="utf-8")

    print("✅ Base limpa criada.")
    print("Arquivo:", SAIDA_JSON)
    print("Relatório:", SAIDA_RELATORIO)
    print("RG válidos:", len(rg))
    print("Repetitivos válidos:", len(rep))
    print("Total:", len(base))
    print("Ignorados:", len(ign_rg) + len(ign_rep))

if __name__ == "__main__":
    main()
