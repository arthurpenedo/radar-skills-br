"""Agrega as vagas: quanto cada habilidade aparece, no total e por nível, onde estão as vagas e quem contrata."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date

from .skills import NIVEIS, SKILLS, extrair, limpar, nivel

MODELOS = {"on-site": "presencial", "remote": "remoto", "hybrid": "híbrido"}


def enriquecer(vagas: list[dict]) -> list[dict]:
    """Uma linha enxuta por vaga, com nível e habilidades já calculados."""
    linhas = []
    for v in vagas:
        texto = limpar(f"{v.get('name', '')} {v.get('description', '')}")
        linhas.append({
            "titulo": (v.get("name") or "").strip(),
            "empresa": (v.get("careerPageName") or "").strip(),
            "cidade": (v.get("city") or "").strip(),
            "uf": (v.get("state") or "").strip(),
            "modelo": MODELOS.get(v.get("workplaceType"), v.get("workplaceType") or "não informado"),
            "publicada": (v.get("publishedDate") or "")[:10],
            "url": v.get("jobUrl") or "",
            "fonte": v.get("fonte", "gupy"),
            "nivel": nivel(v.get("name") or ""),
            "skills": sorted(extrair(texto)),
        })
    return linhas


def novas(linhas: list[dict], anteriores: list[dict]) -> list[dict]:
    """Vagas de `linhas` que não estavam na coleta anterior (compara pelo link), das mais recentes para as mais antigas."""
    vistas = {v["url"] for v in anteriores}
    return sorted((v for v in linhas if v["url"] not in vistas), key=lambda v: v["publicada"], reverse=True)


def _ranking(contagem: Counter, total: int) -> list[dict]:
    return [{"skill": s, "vagas": c, "pct": round(100 * c / total, 1) if total else 0.0}
            for s, c in sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))]


def resumir(linhas: list[dict], hoje: date | None = None, dias: int = 30) -> dict:
    """O resumo que vira relatório e JSON."""
    total = Counter()
    por_nivel: dict[str, Counter] = defaultdict(Counter)
    niveis, modelos, cidades, empresas = Counter(), Counter(), Counter(), Counter()
    for linha in linhas:
        niveis[linha["nivel"]] += 1
        modelos[linha["modelo"]] += 1
        cidades[linha["cidade"] or "sem cidade (remoto)"] += 1
        empresas[linha["empresa"]] += 1
        for s in linha["skills"]:
            total[s] += 1
            por_nivel[linha["nivel"]][s] += 1
    return {
        "gerado_em": (hoje or date.today()).isoformat(),
        "janela_dias": dias,
        "vagas": len(linhas),
        "niveis": {n: niveis.get(n, 0) for n in NIVEIS},
        "modelos": dict(modelos.most_common()),
        "cidades": dict(cidades.most_common(10)),
        "empresas": dict(empresas.most_common(15)),
        "skills": _ranking(total, len(linhas)),
        "skills_por_nivel": {n: _ranking(por_nivel[n], niveis[n]) for n in NIVEIS if niveis[n]},
    }


def lacunas(resumo: dict, perfil: set[str], nivel_alvo: str | None = None, minimo_pct: float = 5.0) -> dict:
    """Compara um perfil (habilidades que a pessoa já mostra) com o que as vagas pedem.

    Devolve o que já cobre e o que falta, das habilidades citadas em pelo menos `minimo_pct`% das vagas
    (do nível alvo, se houver vagas dele; senão, de todas)."""
    desconhecidas = perfil - set(SKILLS)
    if desconhecidas:
        raise ValueError(f"habilidades fora do catálogo: {sorted(desconhecidas)}")
    ranking = resumo["skills_por_nivel"].get(nivel_alvo) if nivel_alvo else None
    ranking = ranking or resumo["skills"]
    relevantes = [r for r in ranking if r["pct"] >= minimo_pct]
    return {
        "base": nivel_alvo if ranking is not resumo["skills"] else "todas",
        "cobre": [r for r in relevantes if r["skill"] in perfil],
        "falta": [r for r in relevantes if r["skill"] not in perfil],
    }
