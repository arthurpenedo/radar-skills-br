"""Exporta as vagas em CSV no formato que o Power BI gosta: uma tabela de vagas e uma de habilidades (modelo estrela).

`vagas.csv` tem uma linha por vaga (id, título, empresa, cidade, modelo, nível, data, fonte, link) e
`vaga_skill.csv` tem uma linha por par vaga-habilidade, ligando as duas pelo `id`. Assim o Power BI conta
habilidades por nível com uma relação simples, sem separar texto em coluna.
"""

from __future__ import annotations

import csv
from pathlib import Path


def exportar(linhas: list[dict], pasta: str | Path) -> dict[str, int]:
    """Grava `vagas.csv` e `vaga_skill.csv` em `pasta` (UTF-8 com BOM, que o Excel e o Power BI leem sem erro de acento)."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / "vagas.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "titulo", "empresa", "cidade", "uf", "modelo", "nivel", "publicada", "fonte", "url"])
        for i, v in enumerate(linhas, 1):
            w.writerow([i, v["titulo"], v["empresa"], v["cidade"], v["uf"], v["modelo"], v["nivel"], v["publicada"],
                        v.get("fonte", "gupy"), v["url"]])
    pares = 0
    with open(pasta / "vaga_skill.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "skill"])
        for i, v in enumerate(linhas, 1):
            for s in v["skills"]:
                w.writerow([i, s])
                pares += 1
    return {"vagas": len(linhas), "pares_vaga_skill": pares}
