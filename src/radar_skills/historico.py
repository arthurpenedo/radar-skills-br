"""Histórico diário: um resumo enxuto por dia em `historico/AAAA-MM-DD.json` e a tendência das habilidades mais pedidas."""

from __future__ import annotations

import json
from pathlib import Path


def gravar(resumo: dict, pasta: str | Path) -> Path:
    """Grava (ou sobrescreve, se rodar duas vezes no mesmo dia) o resumo do dia; guarda só o que a tendência usa."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"{resumo['gerado_em']}.json"
    enxuto = {"gerado_em": resumo["gerado_em"], "vagas": resumo["vagas"],
              "skills": {r["skill"]: r["pct"] for r in resumo["skills"]}}
    destino.write_text(json.dumps(enxuto, ensure_ascii=False, indent=1), encoding="utf-8")
    return destino


def carregar(pasta: str | Path) -> list[dict]:
    """Resumos guardados, do mais antigo ao mais recente. Arquivo quebrado é ignorado."""
    pasta = Path(pasta)
    if not pasta.is_dir():
        return []
    dias = []
    for arq in sorted(pasta.glob("*.json")):
        try:
            d = json.loads(arq.read_text(encoding="utf-8"))
            dias.append({"gerado_em": d["gerado_em"], "vagas": d["vagas"], "skills": d["skills"]})
        except (ValueError, KeyError, TypeError):
            continue
    return sorted(dias, key=lambda d: d["gerado_em"])


def importar(arquivo: str | Path, pasta: str | Path) -> int:
    """Desempacota um `historico.json` publicado antes (lista de dias) na pasta, sem sobrescrever dias que já existem.

    Arquivo ausente ou quebrado (download que falhou no CI) conta como zero dias importados."""
    arquivo = Path(arquivo)
    if not arquivo.is_file():
        return 0
    try:
        dias = json.loads(arquivo.read_text(encoding="utf-8"))["dias"]
        novos = 0
        Path(pasta).mkdir(parents=True, exist_ok=True)
        for d in dias:
            destino = Path(pasta) / f"{d['gerado_em']}.json"
            if not destino.exists():
                destino.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
                novos += 1
        return novos
    except (ValueError, KeyError, TypeError):
        return 0


def empacotar(pasta: str | Path, destino: str | Path) -> int:
    """Junta todos os dias da pasta num único `historico.json` (é o que o Pages publica para a próxima execução)."""
    dias = carregar(pasta)
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    Path(destino).write_text(json.dumps({"dias": dias}, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(dias)


def tendencia(dias: list[dict], top: int = 10) -> dict | None:
    """As `top` habilidades do dia mais recente com a variação (em pontos percentuais) contra o dia mais antigo.

    Devolve None com menos de 2 dias (não há o que comparar)."""
    if len(dias) < 2:
        return None
    ini, fim = dias[0], dias[-1]
    maiores = sorted(fim["skills"].items(), key=lambda kv: (-kv[1], kv[0]))[:top]
    return {
        "de": ini["gerado_em"], "ate": fim["gerado_em"], "dias": len(dias),
        "skills": [{"skill": s, "pct": pct, "inicio": ini["skills"].get(s, 0.0),
                    "variacao": round(pct - ini["skills"].get(s, 0.0), 1)} for s, pct in maiores],
    }
