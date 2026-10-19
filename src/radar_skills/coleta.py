"""Coleta de vagas no portal público de busca da Gupy (o mesmo que o site portal.gupy.io usa).

Sem login e sem chave. A busca devolve título, empresa, cidade, modelo de trabalho, data e a descrição completa.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Callable, Iterable

URL = "https://portal.gupy.io/api/job-search/jobs"
TERMOS_PADRAO = [
    "inteligencia artificial", "engenheiro de ia", "llm", "ia generativa", "automacao", "desenvolvedor junior",
    "python", "engenheiro de dados", "analista de dados junior", "machine learning", "rpa", "back-end",
]
Buscar = Callable[[str, int, int], dict]


def _buscar_http(termo: str, limite: int, offset: int) -> dict:
    query = urllib.parse.urlencode({"jobName": termo, "limit": limite, "offset": offset})
    req = urllib.request.Request(f"{URL}?{query}", headers={"User-Agent": "radar-skills-br (github.com/arthurpenedo)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def buscar_termo(termo: str, buscar: Buscar = _buscar_http, por_pagina: int = 100, maximo: int = 500,
                 pausa: float = 0.5) -> list[dict]:
    """Todas as páginas de um termo, até `maximo` vagas."""
    vagas, offset = [], 0
    while offset < maximo:
        pagina = buscar(termo, por_pagina, offset)
        vagas += pagina.get("data", [])
        offset += por_pagina
        if offset >= pagina.get("pagination", {}).get("total", 0):
            break
        time.sleep(pausa)
    return vagas


def coletar(termos: Iterable[str] = TERMOS_PADRAO, dias: int = 30, hoje: date | None = None,
            buscar: Buscar = _buscar_http, pausa: float = 0.5) -> list[dict]:
    """Vagas publicadas nos últimos `dias`, sem repetição (a mesma vaga aparece em vários termos)."""
    corte = ((hoje or date.today()) - timedelta(days=dias)).isoformat()
    unicas: dict = {}
    for termo in termos:
        for vaga in buscar_termo(termo, buscar, pausa=pausa):
            if (vaga.get("publishedDate") or "")[:10] >= corte:
                unicas.setdefault(vaga["id"], vaga)
        time.sleep(pausa)
    return list(unicas.values())
