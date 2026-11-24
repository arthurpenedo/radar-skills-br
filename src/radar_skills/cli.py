"""Linha de comando: coletar, gerar relatório e comparar um perfil com o mercado."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from . import analise, coleta, exportar, historico, relatorio
from . import remotas as remotas_mod


def _ler_json(caminho: str, chave: str) -> dict | None:
    """Lê um JSON de entrada; arquivo ausente ou quebrado vira mensagem, não traceback."""
    try:
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"Erro: não consegui ler {caminho}: {e}", file=sys.stderr)
        return None
    if not isinstance(dados, dict) or chave not in dados:
        print(f"Erro: {caminho} não tem o formato esperado (falta a chave '{chave}').", file=sys.stderr)
        return None
    return dados


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="radar-skills", description="O que as vagas de tecnologia no Brasil pedem")
    sub = p.add_subparsers(dest="comando", required=True)

    c = sub.add_parser("coletar", help="baixa as vagas da Gupy e salva o JSON enriquecido")
    c.add_argument("--saida", default="vagas.json")
    c.add_argument("--dias", type=int, default=30)
    c.add_argument("--termo", action="append", help="termo de busca (repita); padrão: 12 termos de IA/dados/dev")
    c.add_argument("--remotas", action="store_true",
                   help="inclui vagas remotas internacionais (Remotive, RemoteOK, Himalayas, Jobicy, WWR, Working "
                        "Nomads) que aceitam o Brasil/LATAM/mundo")

    r = sub.add_parser("relatorio", help="gera o resumo JSON e o HTML a partir das vagas coletadas")
    r.add_argument("vagas")
    r.add_argument("--html", default="site/index.html")
    r.add_argument("--resumo", default="site/resumo.json")
    r.add_argument("--anterior", help="vagas.json da coleta anterior: o relatório ganha a seção 'vagas novas' "
                                      "(arquivo que não existe é ignorado)")

    r.add_argument("--historico", help="pasta do histórico diário (grava o resumo de hoje e mostra a tendência das 10 "
                                       "habilidades mais pedidas)")
    r.add_argument("--historico-anterior", help="historico.json publicado na execução anterior (é desempacotado na "
                                                "pasta do histórico; arquivo ausente ou quebrado é ignorado)")

    e = sub.add_parser("exportar", help="grava vagas.csv e vaga_skill.csv (para o Power BI) a partir das vagas coletadas")
    e.add_argument("vagas")
    e.add_argument("--pasta", default="powerbi")

    lc = sub.add_parser("lacunas", help="compara um perfil (JSON com a lista 'skills') com o que as vagas pedem")
    lc.add_argument("resumo")
    lc.add_argument("perfil")
    lc.add_argument("--nivel", default="júnior/trainee")
    lc.add_argument("--minimo", type=float, default=5.0, help="só habilidades citadas em pelo menos X%% das vagas")

    args = p.parse_args(argv)
    if args.comando == "coletar" and args.dias < 1:
        print("Erro: --dias precisa ser 1 ou mais.", file=sys.stderr)
        return 2
    if args.comando == "coletar":
        brutas = coleta.coletar(args.termo or coleta.TERMOS_PADRAO, dias=args.dias)
        if args.remotas:
            corte = (date.today() - timedelta(days=args.dias)).isoformat()
            remotas, por_fonte = remotas_mod.coletar_remotas()
            brutas += [v for v in remotas if v["publishedDate"][:10] >= corte]
            for fonte, info in por_fonte.items():
                print(f"  {fonte}: {info.get('erro') or str(info['aceitam_brasil']) + ' de ' + str(info['lidas']) + ' aceitam o Brasil'}")
        linhas = analise.enriquecer(brutas)
        Path(args.saida).write_text(json.dumps({"dias": args.dias, "vagas": linhas}, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
        print(f"{len(linhas)} vagas salvas em {args.saida}")
    elif args.comando == "exportar":
        dados = _ler_json(args.vagas, "vagas")
        if dados is None:
            return 2
        n = exportar.exportar(dados["vagas"], args.pasta)
        print(f"{n['vagas']} vagas e {n['pares_vaga_skill']} pares vaga-habilidade em {args.pasta}/")
    elif args.comando == "relatorio":
        dados = _ler_json(args.vagas, "vagas")
        if dados is None:
            return 2
        resumo = analise.resumir(dados["vagas"], dias=dados.get("dias", 30))
        novas = None
        if args.anterior and Path(args.anterior).is_file():
            try:
                novas = analise.novas(dados["vagas"], json.loads(Path(args.anterior).read_text(encoding="utf-8"))["vagas"])
            except (ValueError, KeyError):  # download quebrado no CI: gera o relatório sem a seção
                print(f"Aviso: {args.anterior} não é um vagas.json válido; seção de vagas novas omitida.")
        tend = None
        if args.historico:
            if args.historico_anterior:
                historico.importar(args.historico_anterior, args.historico)
            historico.gravar(resumo, args.historico)
            tend = historico.tendencia(historico.carregar(args.historico))
            historico.empacotar(args.historico, Path(args.html).parent / "historico.json")
        for destino, conteudo in ((args.html, relatorio.gerar_html(resumo, dados["vagas"], novas=novas, tendencia=tend)),
                                  (args.resumo, json.dumps(resumo, ensure_ascii=False, indent=1))):
            Path(destino).parent.mkdir(parents=True, exist_ok=True)
            Path(destino).write_text(conteudo, encoding="utf-8")
        top = ", ".join(f"{r['skill']} {r['pct']:.0f}%" for r in resumo["skills"][:5])
        print(f"{resumo['vagas']} vagas · mais pedidas: {top}\nRelatório: {args.html}")
        if novas is not None:
            print(f"{len(novas)} vagas novas desde a coleta anterior")
    else:
        resumo, perfil_json = _ler_json(args.resumo, "skills"), _ler_json(args.perfil, "skills")
        if resumo is None or perfil_json is None:
            return 2
        perfil = set(perfil_json["skills"])
        res = analise.lacunas(resumo, perfil, args.nivel, args.minimo)
        print(f"Base: vagas {res['base']}")
        print("Já cobre:  " + (", ".join(f"{r['skill']} ({r['pct']:.0f}%)" for r in res["cobre"]) or "nada"))
        print("Falta:     " + (", ".join(f"{r['skill']} ({r['pct']:.0f}%)" for r in res["falta"]) or "nada"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
