import json
from datetime import date

import pytest

from radar_skills import analise, coleta, relatorio
from radar_skills.cli import main
from radar_skills.skills import SKILLS, extrair, limpar, nivel

HOJE = date(2026, 10, 19)


def _vaga(id_, nome, desc, publicada="2026-10-10", modelo="remote", cidade=""):
    return {"id": id_, "name": nome, "description": desc, "careerPageName": f"Empresa {id_}", "city": cidade,
            "state": "", "workplaceType": modelo, "publishedDate": f"{publicada}T10:00:00.000Z",
            "jobUrl": f"https://x.gupy.io/job/{id_}"}


VAGAS = [
    _vaga(1, "Analista de IA Jr", "<p>Python, SQL e <b>LLMs</b>. Desejável RAG e LangGraph. Inglês.</p>", cidade="São Paulo",
          modelo="hybrid"),
    _vaga(2, "Engenheiro de Dados Sênior", "Spark, Databricks, AWS, Docker e Python."),
    _vaga(3, "Estágio em Dados", "Power BI e SQL.", modelo="on-site", cidade="São Paulo"),
    _vaga(4, "Desenvolvedor(a) Júnior", "Java, Spring Boot, APIs REST, Git."),
]


def test_limpar_tira_html_e_entidades():
    assert limpar("<p>Ol&aacute;  <b>Mundo</b></p>") == "olá mundo"


@pytest.mark.parametrize("texto,esperado,proibido", [
    ("experiência com javascript e node.js", "JavaScript/TypeScript", "Java"),
    ("java 17 e spring boot", "Java", "JavaScript/TypeScript"),
    ("power bi e dax", "Power BI / BI", None),
    ("agentes de ia com mcp", "Agentes de IA", None),
    ("ci/cd com github actions", "CI/CD", None),
    ("make.com e n8n", "n8n / Make / Zapier", None),
])
def test_extrair(texto, esperado, proibido):
    achou = extrair(texto)
    assert esperado in achou
    assert proibido is None or proibido not in achou


def test_extrair_nao_confunde_palavras_parecidas():
    assert extrair("restante do time, fazer a manutenção e o desenvolvimento") == set()


@pytest.mark.parametrize("titulo,esperado", [
    ("Estágio em IA", "estágio"), ("Analista de Dados Jr.", "júnior/trainee"), ("Programa Trainee 2027", "júnior/trainee"),
    ("Engenheiro(a) de IA - Pleno", "pleno"), ("Especialista em Dados", "sênior+"), ("Desenvolvedor Python", "não informado"),
])
def test_nivel(titulo, esperado):
    assert nivel(titulo) == esperado


def test_catalogo_compila_e_tem_nomes_unicos():
    assert len(SKILLS) == len(set(SKILLS)) >= 30


def test_coletar_pagina_remove_repetidas_e_respeita_janela():
    banco = {"a": [_vaga(i, f"v{i}", "") for i in range(150)] + [_vaga(999, "velha", "", publicada="2026-08-01")],
             "b": [_vaga(1, "v1", ""), _vaga(500, "nova", "")]}
    chamadas = []

    def buscar(termo, limite, offset):
        chamadas.append((termo, offset))
        dados = banco[termo]
        return {"data": dados[offset:offset + limite], "pagination": {"total": len(dados)}}

    vagas = coleta.coletar(["a", "b"], dias=30, hoje=HOJE, buscar=buscar, pausa=0)
    ids = {v["id"] for v in vagas}
    assert len(vagas) == len(ids) == 151  # 150 de "a" + 1 nova de "b"; a velha e a repetida saem
    assert 999 not in ids and ("a", 100) in chamadas


def test_resumir_conta_por_nivel_e_modelo():
    linhas = analise.enriquecer(VAGAS)
    resumo = analise.resumir(linhas, hoje=HOJE)
    assert resumo["vagas"] == 4
    assert resumo["niveis"]["júnior/trainee"] == 2 and resumo["niveis"]["estágio"] == 1
    assert resumo["modelos"] == {"remoto": 2, "híbrido": 1, "presencial": 1}
    top = {r["skill"]: r for r in resumo["skills"]}
    assert top["Python"]["vagas"] == 2 and top["Python"]["pct"] == 50.0
    assert top["SQL"]["vagas"] == 2
    junior = {r["skill"] for r in resumo["skills_por_nivel"]["júnior/trainee"]}
    assert {"Python", "Java", "LangChain/LangGraph"} <= junior and "Spark / dbt / Airflow" not in junior


def test_lacunas_separa_o_que_cobre_e_o_que_falta():
    resumo = analise.resumir(analise.enriquecer(VAGAS), hoje=HOJE)
    res = analise.lacunas(resumo, {"Python", "SQL"}, "júnior/trainee")
    assert res["base"] == "júnior/trainee"
    assert {r["skill"] for r in res["cobre"]} == {"Python", "SQL"}
    assert "Java" in {r["skill"] for r in res["falta"]}
    assert analise.lacunas(resumo, {"Python"}, "nível que não existe")["base"] == "todas"
    with pytest.raises(ValueError):
        analise.lacunas(resumo, {"Cobol"})


def test_html_escapa_e_tem_filtro():
    vagas = VAGAS + [_vaga(9, "<script>alert(1)</script> Jr", "python")]
    linhas = analise.enriquecer(vagas)
    html = relatorio.gerar_html(analise.resumir(linhas, hoje=HOJE), linhas)
    assert "<script>alert(1)" not in html and "&lt;script&gt;" in html
    assert 'data-nivel="júnior/trainee"' in html.replace("'", '"') and "vagas analisadas" in html


def test_exportar_gera_tabelas_ligadas_pelo_id(tmp_path, capsys):
    import csv
    arquivo = tmp_path / "vagas.json"
    arquivo.write_text(json.dumps({"dias": 30, "vagas": analise.enriquecer(VAGAS)}), encoding="utf-8")
    assert main(["exportar", str(arquivo), "--pasta", str(tmp_path / "pb")]) == 0
    vagas = list(csv.DictReader(open(tmp_path / "pb" / "vagas.csv", encoding="utf-8-sig")))
    pares = list(csv.DictReader(open(tmp_path / "pb" / "vaga_skill.csv", encoding="utf-8-sig")))
    assert [v["id"] for v in vagas] == ["1", "2", "3", "4"] and vagas[0]["nivel"] == "júnior/trainee"
    assert vagas[0]["fonte"] == "gupy" and vagas[2]["modelo"] == "presencial"
    assert {"id": "1", "skill": "Python"} in pares and {"id": "3", "skill": "Power BI / BI"} in pares
    assert {p["id"] for p in pares} <= {v["id"] for v in vagas}
    assert f"{len(pares)} pares" in capsys.readouterr().out


def test_cli_relatorio_e_lacunas(tmp_path, capsys):
    arquivo = tmp_path / "vagas.json"
    arquivo.write_text(json.dumps({"dias": 30, "vagas": analise.enriquecer(VAGAS)}), encoding="utf-8")
    html, resumo = tmp_path / "site" / "index.html", tmp_path / "site" / "resumo.json"
    assert main(["relatorio", str(arquivo), "--html", str(html), "--resumo", str(resumo)]) == 0
    assert html.exists() and json.loads(resumo.read_text(encoding="utf-8"))["vagas"] == 4
    perfil = tmp_path / "perfil.json"
    perfil.write_text(json.dumps({"skills": ["Python"]}), encoding="utf-8")
    assert main(["lacunas", str(resumo), str(perfil)]) == 0
    saida = capsys.readouterr().out
    assert "Já cobre:  Python" in saida and "SQL" in saida.split("Falta:")[1]
