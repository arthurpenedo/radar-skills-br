import json

import pytest

from radar_skills import analise, remotas

REMOTIVE = json.dumps({"jobs": [
    {"id": 1, "title": "Junior AI Engineer", "company_name": "Acme", "url": "https://remotive.com/1",
     "publication_date": "2026-10-20T10:00:00", "candidate_required_location": "Worldwide",
     "description": "<p>Python, LLMs e RAG</p>"},
    {"id": 2, "title": "Backend Dev", "company_name": "Foo", "url": "https://remotive.com/2",
     "publication_date": "2026-10-20T10:00:00", "candidate_required_location": "USA Only", "description": "Go"},
]})
REMOTEOK = json.dumps([
    {"legal": "aviso legal, sem position"},
    {"id": "77", "position": "Data Analyst", "company": "Bar", "url": "https://remoteok.com/77",
     "date": "2026-10-19T08:00:00+00:00", "location": "", "description": "SQL e Power BI"},
])
HIMALAYAS = json.dumps({"jobs": [
    {"guid": "h1", "title": "ML Engineer (Intern)", "companyName": "Hima", "applicationLink": "https://himalayas.app/h1",
     "pubDate": 1792483200, "locationRestrictions": ["Brazil", "Argentina"], "description": "Python"},
    {"guid": "h2", "title": "Designer", "companyName": "Hima", "applicationLink": "https://himalayas.app/h2",
     "pubDate": 1792483200, "locationRestrictions": ["Germany"], "description": "Figma"},
]})
JOBICY = json.dumps({"jobs": [
    {"id": 5, "jobTitle": "Automation Specialist", "companyName": "Job", "url": "https://jobicy.com/5",
     "pubDate": "2026-10-18 09:00:00", "jobGeo": "LATAM", "jobDescription": "n8n e Python"}]})
NOMADS = json.dumps([
    {"url": "https://workingnomads.com/jobs/9", "title": "Python Developer", "company_name": "Nom",
     "pub_date": "2026-10-17T00:00:00-04:00", "location": "Anywhere", "description": "Python e Docker"}])
WWR = """<?xml version="1.0"?><rss><channel>
<item><title>Zeta: Junior Developer</title><region>Anywhere in the World</region>
<link>https://weworkremotely.com/z1</link><pubDate>Mon, 19 Oct 2026 12:00:00 +0000</pubDate>
<description>&lt;p&gt;Python e SQL&lt;/p&gt;</description></item>
<item><title>Eta: Rails Dev</title><region>North America Only</region><link>https://weworkremotely.com/e1</link>
<pubDate>Mon, 19 Oct 2026 12:00:00 +0000</pubDate><description>Rails</description></item>
</channel></rss>"""

GRAVADO = {remotas.URLS["remotive"]: REMOTIVE, remotas.URLS["remoteok"]: REMOTEOK, remotas.URLS["himalayas"]: HIMALAYAS,
           remotas.URLS["jobicy"]: JOBICY, remotas.URLS["workingnomads"]: NOMADS, remotas.URLS["wwr"]: WWR}


@pytest.mark.parametrize("local,esperado", [
    ("Worldwide", True), ("LATAM", True), ("Brazil, Argentina", True), ("Latin America", True), ("Anywhere in the World", True),
    ("USA Only", False), ("Germany", False), ("", False), (None, False),
])
def test_aceita_brasil(local, esperado):
    assert remotas.aceita_brasil(local) is esperado


def test_leitores_normalizam_para_o_formato_da_gupy():
    vaga = remotas.ler_remotive(REMOTIVE)[0]
    assert vaga["id"] == "remotive:1" and vaga["fonte"] == "remotive" and vaga["workplaceType"] == "remote"
    assert vaga["name"] == "Junior AI Engineer" and vaga["careerPageName"] == "Acme" and vaga["jobUrl"].endswith("/1")
    assert [v["name"] for v in remotas.ler_remoteok(REMOTEOK)] == ["Data Analyst"]  # o aviso legal sai
    assert remotas.ler_remoteok(REMOTEOK)[0]["local"] == "Worldwide"
    assert remotas.ler_himalayas(HIMALAYAS)[0]["publishedDate"][:10] == "2026-10-20"  # segundos desde 1970
    assert remotas.ler_jobicy(JOBICY)[0]["publishedDate"] == "2026-10-18T09:00:00"
    wwr = remotas.ler_wwr(WWR)[0]
    assert (wwr["careerPageName"], wwr["name"], wwr["local"]) == ("Zeta", "Junior Developer", "Anywhere in the World")
    assert wwr["publishedDate"].startswith("2026-10-19")


def test_coletar_remotas_filtra_pelo_brasil_e_conta_por_fonte():
    vagas, rel = remotas.coletar_remotas(baixar=GRAVADO.__getitem__)
    assert {v["name"] for v in vagas} == {"Junior AI Engineer", "Data Analyst", "ML Engineer (Intern)",
                                          "Automation Specialist", "Python Developer", "Junior Developer"}
    assert rel["remotive"] == {"lidas": 2, "aceitam_brasil": 1}
    assert rel["wwr"] == {"lidas": 2, "aceitam_brasil": 1}


def test_fonte_fora_do_ar_nao_derruba_as_outras():
    def baixar(url):
        if url == remotas.URLS["remoteok"]:
            raise OSError("sem rede")
        if url == remotas.URLS["jobicy"]:
            return "isto não é JSON"
        return GRAVADO[url]

    vagas, rel = remotas.coletar_remotas(baixar=baixar)
    assert "OSError" in rel["remoteok"]["erro"] and "JSONDecodeError" in rel["jobicy"]["erro"]
    assert len(vagas) == 4 and rel["remotive"]["aceitam_brasil"] == 1


def test_remotas_entram_na_analise_com_fonte_e_nivel():
    vagas, _ = remotas.coletar_remotas(baixar=GRAVADO.__getitem__)
    linhas = analise.enriquecer(vagas)
    por_titulo = {linha["titulo"]: linha for linha in linhas}
    assert por_titulo["Junior AI Engineer"]["nivel"] == "júnior/trainee"
    assert por_titulo["ML Engineer (Intern)"]["nivel"] == "estágio"
    assert por_titulo["Junior AI Engineer"]["fonte"] == "remotive" and "Python" in por_titulo["Junior AI Engineer"]["skills"]
    assert analise.resumir(linhas)["modelos"] == {"remoto": 6}
