import json
from datetime import date

from radar_skills import analise, historico, relatorio
from radar_skills.cli import main

from test_radar import HOJE, VAGAS


def _resumo(dia, pcts, vagas=10):
    return {"gerado_em": dia, "vagas": vagas, "skills": [{"skill": s, "vagas": 1, "pct": p} for s, p in pcts.items()]}


def test_gravar_e_carregar_ordenam_por_dia_e_ignoram_arquivo_quebrado(tmp_path):
    historico.gravar(_resumo("2026-10-20", {"Python": 50.0}), tmp_path)
    historico.gravar(_resumo("2026-10-19", {"Python": 48.0}), tmp_path)
    (tmp_path / "2026-10-21.json").write_text("{quebrado", encoding="utf-8")
    dias = historico.carregar(tmp_path)
    assert [d["gerado_em"] for d in dias] == ["2026-10-19", "2026-10-20"]
    assert dias[1]["skills"] == {"Python": 50.0}
    assert historico.carregar(tmp_path / "nao-existe") == []


def test_tendencia_compara_primeiro_e_ultimo_dia():
    dias = [{"gerado_em": "2026-10-19", "vagas": 9, "skills": {"Python": 48.0, "SQL": 40.0}},
            {"gerado_em": "2026-10-26", "vagas": 12, "skills": {"Python": 42.5, "Docker": 10.0, "SQL": 41.0}}]
    t = historico.tendencia(dias, top=3)
    assert (t["de"], t["ate"], t["dias"]) == ("2026-10-19", "2026-10-26", 2)
    por_skill = {r["skill"]: r for r in t["skills"]}
    assert por_skill["Python"]["variacao"] == -5.5
    assert por_skill["SQL"]["variacao"] == 1.0
    assert por_skill["Docker"]["inicio"] == 0.0 and por_skill["Docker"]["variacao"] == 10.0  # habilidade nova
    assert [r["skill"] for r in t["skills"]] == ["Python", "SQL", "Docker"]  # ordem do dia mais recente


def test_tendencia_sem_dois_dias_nao_tem_o_que_comparar():
    assert historico.tendencia([]) is None
    assert historico.tendencia([{"gerado_em": "2026-10-19", "vagas": 1, "skills": {"Python": 1.0}}]) is None


def test_importar_nao_sobrescreve_e_aguenta_arquivo_ruim(tmp_path):
    origem, pasta = tmp_path / "historico.json", tmp_path / "h"
    historico.gravar(_resumo("2026-10-19", {"Python": 48.0}), tmp_path / "fonte")
    assert historico.empacotar(tmp_path / "fonte", origem) == 1
    assert historico.importar(origem, pasta) == 1
    assert historico.importar(origem, pasta) == 0  # já existe
    origem.write_text("isto não é json", encoding="utf-8")
    assert historico.importar(origem, pasta) == 0
    assert historico.importar(tmp_path / "nao-existe.json", pasta) == 0


def test_html_mostra_tendencia_so_com_historico():
    linhas = analise.enriquecer(VAGAS)
    resumo = analise.resumir(linhas, hoje=HOJE)
    assert "Tendência" not in relatorio.gerar_html(resumo, linhas)
    tend = {"de": "2026-10-19", "ate": "2026-10-26", "dias": 2,
            "skills": [{"skill": "Python", "pct": 42.5, "inicio": 48.0, "variacao": -5.5}]}
    html = relatorio.gerar_html(resumo, linhas, tendencia=tend)
    assert "Tendência das habilidades" in html and "-5.5 p.p." in html


def test_cli_relatorio_grava_historico_e_publica_o_pacote(tmp_path, capsys):
    vagas = tmp_path / "vagas.json"
    vagas.write_text(json.dumps({"dias": 30, "vagas": analise.enriquecer(VAGAS)}), encoding="utf-8")
    pasta, site = tmp_path / "historico", tmp_path / "site"
    antigo = {"dias": [{"gerado_em": "2026-10-01", "vagas": 5, "skills": {"Python": 10.0}}]}
    (tmp_path / "anterior.json").write_text(json.dumps(antigo), encoding="utf-8")
    args = ["relatorio", str(vagas), "--html", str(site / "index.html"), "--resumo", str(site / "resumo.json"),
            "--historico", str(pasta), "--historico-anterior", str(tmp_path / "anterior.json")]
    assert main(args) == 0
    hoje = date.today().isoformat()
    assert (pasta / "2026-10-01.json").exists() and (pasta / f"{hoje}.json").exists()
    pacote = json.loads((site / "historico.json").read_text(encoding="utf-8"))
    assert [d["gerado_em"] for d in pacote["dias"]] == ["2026-10-01", hoje]
    assert "Tendência das habilidades" in (site / "index.html").read_text(encoding="utf-8")
    assert main(args) == 0  # rodar de novo no mesmo dia não duplica
    assert len(json.loads((site / "historico.json").read_text(encoding="utf-8"))["dias"]) == 2
