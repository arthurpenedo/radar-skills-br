"""Vagas remotas internacionais pelas APIs públicas (sem login e sem chave).

Fontes: Remotive, RemoteOK, Himalayas, Jobicy, Working Nomads (JSON) e We Work Remotely (RSS). Cada leitor devolve
vagas no mesmo formato da Gupy (com o campo extra `fonte`), então `analise.enriquecer` serve para todas. Só ficam as
vagas que aceitam o Brasil: localização "Worldwide", "Anywhere", "LATAM", "Brazil" etc.
"""

from __future__ import annotations

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Callable

URLS = {
    "remotive": "https://remotive.com/api/remote-jobs",
    "remoteok": "https://remoteok.com/api",
    "himalayas": "https://himalayas.app/jobs/api?limit=100",
    "jobicy": "https://jobicy.com/api/v2/remote-jobs?count=100",
    "wwr": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "workingnomads": "https://www.workingnomads.com/api/exposed_jobs/",
}
Baixar = Callable[[str], str]

_ACEITA = re.compile(r"\b(brazil|brasil|latam|latin america|south america|americas|worldwide|anywhere|global|"
                     r"world ?wide|everywhere|international)\b", re.I)


def _baixar_http(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "radar-skills-br (github.com/arthurpenedo)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def aceita_brasil(local: str) -> bool:
    """A localização aceita quem mora no Brasil (Brasil, LATAM ou mundo todo)?"""
    return bool(_ACEITA.search(local or ""))


def _vaga(fonte: str, id_, titulo, empresa, descricao, url, publicada, local) -> dict:
    return {"id": f"{fonte}:{id_}", "name": (titulo or "").strip(), "description": descricao or "",
            "careerPageName": (empresa or "").strip(), "city": "", "state": "", "workplaceType": "remote",
            "publishedDate": publicada, "jobUrl": url or "", "fonte": fonte, "local": (local or "").strip()}


def _data(valor) -> str:
    """Data ISO (AAAA-MM-DD...) a partir de texto ISO, RFC 822 (RSS) ou segundos desde 1970."""
    if isinstance(valor, (int, float)):
        return datetime.fromtimestamp(valor, timezone.utc).isoformat()
    texto = str(valor or "").strip()
    if re.fullmatch(r"\d{9,10}", texto):
        return _data(int(texto))
    for formato in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(texto, formato).astimezone(timezone.utc).isoformat()
        except ValueError:
            pass
    return texto.replace(" ", "T")


def ler_remotive(bruto: str) -> list[dict]:
    return [_vaga("remotive", j["id"], j.get("title"), j.get("company_name"), j.get("description"), j.get("url"),
                  _data(j.get("publication_date")), j.get("candidate_required_location"))
            for j in json.loads(bruto).get("jobs", [])]


def ler_remoteok(bruto: str) -> list[dict]:
    # o primeiro item da lista é o aviso legal, sem "position"
    return [_vaga("remoteok", j["id"], j.get("position"), j.get("company"), j.get("description"),
                  j.get("url") or j.get("apply_url"), _data(j.get("date")), j.get("location") or "Worldwide")
            for j in json.loads(bruto) if isinstance(j, dict) and j.get("position")]


def ler_himalayas(bruto: str) -> list[dict]:
    saida = []
    for j in json.loads(bruto).get("jobs", []):
        local = ", ".join(j.get("locationRestrictions") or []) or "Worldwide"  # lista vazia = sem restrição
        saida.append(_vaga("himalayas", j.get("guid") or j.get("applicationLink"), j.get("title"), j.get("companyName"),
                           j.get("description") or j.get("excerpt"), j.get("applicationLink") or j.get("guid"),
                           _data(j.get("pubDate")), local))
    return saida


def ler_jobicy(bruto: str) -> list[dict]:
    return [_vaga("jobicy", j["id"], j.get("jobTitle"), j.get("companyName"), j.get("jobDescription"), j.get("url"),
                  _data(j.get("pubDate")), j.get("jobGeo"))
            for j in json.loads(bruto).get("jobs", [])]


def ler_workingnomads(bruto: str) -> list[dict]:
    return [_vaga("workingnomads", j.get("url"), j.get("title"), j.get("company_name"), j.get("description"),
                  j.get("url"), _data(j.get("pub_date")), j.get("location"))
            for j in json.loads(bruto)]


def ler_wwr(bruto: str) -> list[dict]:
    """RSS do We Work Remotely: o título vem como "Empresa: Cargo" e a região em <region>."""
    saida = []
    for item in ET.fromstring(bruto).iter("item"):
        titulo = item.findtext("title") or ""
        empresa, _, cargo = titulo.partition(": ")
        link = item.findtext("link") or item.findtext("guid")
        saida.append(_vaga("wwr", link, cargo or titulo, empresa if cargo else "", item.findtext("description"), link,
                           _data(item.findtext("pubDate")), item.findtext("region")))
    return saida


LEITORES = {"remotive": ler_remotive, "remoteok": ler_remoteok, "himalayas": ler_himalayas, "jobicy": ler_jobicy,
            "wwr": ler_wwr, "workingnomads": ler_workingnomads}


def coletar_remotas(fontes: list[str] | None = None, baixar: Baixar = _baixar_http) -> tuple[list[dict], dict]:
    """Vagas de todas as fontes que aceitam o Brasil, sem repetição. Uma fonte fora do ar não derruba as outras.

    Devolve (vagas, relatório por fonte com o total lido, o total que aceita o Brasil ou o erro)."""
    vagas: dict[str, dict] = {}
    relatorio: dict[str, dict] = {}
    for fonte in fontes or list(LEITORES):
        try:
            lidas = LEITORES[fonte](baixar(URLS[fonte]))
        except Exception as erro:  # rede, JSON ou XML fora do formato: registra e segue
            relatorio[fonte] = {"erro": f"{type(erro).__name__}: {erro}"}
            continue
        aceitas = [v for v in lidas if aceita_brasil(v["local"])]
        for v in aceitas:
            vagas.setdefault(v["id"], v)
        relatorio[fonte] = {"lidas": len(lidas), "aceitam_brasil": len(aceitas)}
    return list(vagas.values()), relatorio
