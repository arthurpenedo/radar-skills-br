"""Relatório HTML de arquivo único (sem dependências), com modo escuro e lista de vagas filtrável por nível."""

from __future__ import annotations

from html import escape

_CSS = """
:root{--bg:#f7f7f5;--card:#fff;--fg:#1d1d1b;--mut:#6b6b66;--bar:#2f6fde;--bar2:#e0e6f3;--bd:#e3e3df}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1e1c;--fg:#ecebe6;--mut:#a3a29b;--bar:#6f9cf0;--bar2:#2b2f38;--bd:#33332f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 64px}h1{font-size:1.6rem;margin:0 0 4px}
h2{font-size:1.15rem;margin:32px 0 12px}.mut{color:var(--mut)}a{color:var(--bar)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:20px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px}
.card b{display:block;font-size:1.5rem}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}
@media (max-width:720px){.grid{grid-template-columns:1fr}}
.row{display:grid;grid-template-columns:minmax(120px,210px) 1fr 70px;gap:8px;align-items:center;margin:4px 0}
.track{background:var(--bar2);border-radius:4px;height:12px}.fill{background:var(--bar);height:12px;border-radius:4px}
.num{text-align:right;font-variant-numeric:tabular-nums}table{width:100%;border-collapse:collapse}
td,th{padding:6px 8px;border-bottom:1px solid var(--bd);text-align:left;vertical-align:top}th{font-weight:600}
select{font:inherit;padding:4px 8px;border-radius:6px;border:1px solid var(--bd);background:var(--card);color:var(--fg)}
.wrap{overflow-x:auto}
"""


def _barras(ranking: list[dict], limite: int = 20) -> str:
    if not ranking:
        return '<p class="mut">Sem dados.</p>'
    maior = max(r["pct"] for r in ranking) or 1
    return "".join(
        f'<div class="row"><span>{escape(r["skill"])}</span><div class="track"><div class="fill" '
        f'style="width:{100 * r["pct"] / maior:.1f}%"></div></div><span class="num">{r["pct"]:.0f}% · {r["vagas"]}</span></div>'
        for r in ranking[:limite])


def _tabela(dados: dict, titulo: str) -> str:
    linhas = "".join(f"<tr><td>{escape(str(k))}</td><td class='num'>{v}</td></tr>" for k, v in dados.items())
    return f"<table><tr><th>{escape(titulo)}</th><th class='num'>vagas</th></tr>{linhas}</table>"


def _secao_novas(novas: list[dict] | None) -> str:
    """Lista das vagas que apareceram desde a coleta anterior (None = sem coleta anterior para comparar)."""
    if novas is None:
        return ""
    if not novas:
        return "<h2>Vagas novas desde a última coleta</h2><p class='mut'>Nenhuma vaga nova.</p>"
    itens = "".join(
        f"<li><a href='{escape(v['url'])}' rel='noopener'>{escape(v['titulo'])}</a> "
        f"<span class='mut'>· {escape(v['empresa'])} · {escape(v['nivel'])} · {escape(v['modelo'])}</span></li>"
        for v in novas[:30])
    resto = f"<p class='mut'>E mais {len(novas) - 30} na lista abaixo.</p>" if len(novas) > 30 else ""
    return f"<h2>Vagas novas desde a última coleta ({len(novas)})</h2><ul>{itens}</ul>{resto}"


def _secao_tendencia(tend: dict | None) -> str:
    """Tabela das habilidades mais pedidas com a variação desde o primeiro dia do histórico (None = histórico curto)."""
    if not tend:
        return ""
    linhas = "".join(
        f"<tr><td>{escape(r['skill'])}</td><td class='num'>{r['inicio']:.1f}%</td><td class='num'>{r['pct']:.1f}%</td>"
        f"<td class='num'>{r['variacao']:+.1f} p.p.</td></tr>" for r in tend["skills"])
    return (f"<h2>Tendência das habilidades mais pedidas</h2><p class='mut'>Do histórico diário: {tend['dias']} dias, "
            f"de {escape(tend['de'])} a {escape(tend['ate'])}. p.p. = pontos percentuais.</p>"
            f"<table><tr><th>habilidade</th><th class='num'>início</th><th class='num'>agora</th>"
            f"<th class='num'>variação</th></tr>{linhas}</table>")


def gerar_html(resumo: dict, linhas: list[dict], titulo: str = "radar-skills-br", novas: list[dict] | None = None,
               tendencia: dict | None = None) -> str:
    n = resumo["vagas"]
    niveis = resumo["niveis"]
    remoto = resumo["modelos"].get("remoto", 0)
    cards = [("vagas analisadas", n), ("júnior/trainee", niveis.get("júnior/trainee", 0)),
             ("estágio", niveis.get("estágio", 0)), ("remotas", f"{100 * remoto / n:.0f}%" if n else "0%")]
    por_nivel = "".join(
        f"<div><h3>{escape(nv)} <span class='mut'>({niveis[nv]} vagas)</span></h3>{_barras(rk, 10)}</div>"
        for nv, rk in resumo["skills_por_nivel"].items() if nv in ("estágio", "júnior/trainee", "pleno", "sênior+"))
    vagas = sorted(linhas, key=lambda x: x["publicada"], reverse=True)
    corpo_vagas = "".join(
        f"<tr data-nivel='{escape(v['nivel'])}'><td><a href='{escape(v['url'])}' rel='noopener'>{escape(v['titulo'])}</a>"
        f"<div class='mut'>{escape(', '.join(v['skills'][:8]))}</div></td><td>{escape(v['empresa'])}</td>"
        f"<td>{escape(v['cidade'] or '—')} · {escape(v['modelo'])}</td><td>{escape(v['publicada'])}</td></tr>"
        for v in vagas)
    opcoes = "".join(f"<option{' selected' if nv == 'júnior/trainee' else ''}>{escape(nv)}</option>"
                     for nv in ["todos", *niveis] if nv == "todos" or niveis.get(nv))
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(titulo)}</title><style>{_CSS}</style></head>
<body><main><h1>O que as vagas de tecnologia pedem</h1>
<p class="mut">Vagas de IA, dados, automação e desenvolvimento publicadas na Gupy nos últimos {resumo['janela_dias']} dias.
Atualizado em {escape(resumo['gerado_em'])}. Contagem por palavra-chave na descrição: é aproximada (veja os limites no README).</p>
<div class="cards">{''.join(f'<div class="card"><b>{v}</b><span class="mut">{escape(k)}</span></div>' for k, v in cards)}</div>
{_secao_novas(novas)}
<h2>Habilidades mais pedidas (todas as vagas)</h2>{_barras(resumo['skills'], 25)}
{_secao_tendencia(tendencia)}
<h2>Por nível</h2><div class="grid">{por_nivel}</div>
<h2>Onde estão</h2><div class="grid">{_tabela(resumo['modelos'], 'modelo')}{_tabela(resumo['cidades'], 'cidade')}</div>
<h2>Quem mais publicou</h2>{_tabela(resumo['empresas'], 'empresa')}
<h2>Vagas</h2><p><label>Nível: <select id="f">{opcoes}</select></label></p>
<div class="wrap"><table id="v"><tr><th>vaga</th><th>empresa</th><th>local</th><th>publicada</th></tr>{corpo_vagas}</table></div>
<p class="mut">Feito por <a href="https://github.com/arthurpenedo/radar-skills-br">Arthur Penedo</a>. Dados públicos do portal da Gupy.</p>
</main><script>
const f=document.getElementById('f');function ap(){{for(const r of document.querySelectorAll('#v tr[data-nivel]'))
r.style.display=(f.value==='todos'||r.dataset.nivel===f.value)?'':'none'}}f.onchange=ap;ap();
</script></body></html>"""
