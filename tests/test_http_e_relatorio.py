"""Pontas que o resto dos testes não alcança: leitores HTTP (urlopen simulado) e seções vazias do relatório."""

import io
import json

from radar_skills import coleta, relatorio, remotas


class RespostaFalsa(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def test_buscar_http_monta_a_url_e_le_o_json(monkeypatch):
    vistos = {}

    def urlopen(req, timeout):
        vistos["url"], vistos["ua"], vistos["timeout"] = req.full_url, req.get_header("User-agent"), timeout
        return RespostaFalsa(json.dumps({"data": [{"id": 1}]}).encode())

    monkeypatch.setattr(coleta.urllib.request, "urlopen", urlopen)
    assert coleta._buscar_http("engenheiro de ia", 100, 200) == {"data": [{"id": 1}]}
    assert "jobName=engenheiro+de+ia" in vistos["url"] and "offset=200" in vistos["url"]
    assert vistos["ua"].startswith("radar-skills-br") and vistos["timeout"] == 30


def test_baixar_http_decodifica_utf8_e_tolera_bytes_ruins(monkeypatch):
    dados = "Vaga de automação".encode() + b"\xff"
    monkeypatch.setattr(remotas.urllib.request, "urlopen", lambda req, timeout: RespostaFalsa(dados))
    texto = remotas._baixar_http("https://x.test/feed")
    assert texto.startswith("Vaga de automação") and texto.endswith("�")


def test_barras_sem_ranking_avisa():
    assert "Sem dados" in relatorio._barras([])


def test_secao_novas_vazia_diz_que_nao_ha_vaga_nova():
    assert "Nenhuma vaga nova" in relatorio._secao_novas([])
    assert relatorio._secao_novas(None) == ""


def test_cli_recusa_destino_do_tipo_errado(tmp_path, capsys):
    from radar_skills.cli import main

    arq = tmp_path / "arq.txt"
    arq.write_text("x")
    vagas = tmp_path / "v.json"
    vagas.write_text('{"dias": 30, "vagas": []}')
    assert main(["coletar", "--saida", str(tmp_path)]) == 2
    assert main(["relatorio", str(vagas), "--html", str(tmp_path)]) == 2
    assert main(["relatorio", str(vagas), "--resumo", str(tmp_path)]) == 2
    assert main(["exportar", str(vagas), "--pasta", str(arq)]) == 2
    assert capsys.readouterr().err.count("Erro:") == 4
