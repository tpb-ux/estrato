"""Prefeito, vice-prefeito e vereadores eleitos em 2024 (TSE). DESLIGADO por flag: config prefeitos.ativo e so vale a partir de prefeitos.liberar_em.
Dados: data/tse/prefeitos.json.gz (tools/datasets_prefeitos.py; ignorado pelo git ate a liberacao). Teste local: PREFEITOS_FORCE=1.
Paginas: /prefeito/ (hub), /prefeito/<uf>/ (hub), /prefeito/<uf>/<municipio>/ (familia `prefeitos`, noindex ate a onda propria).
Sem CPF, patrimonio, cor/raca ou qualquer dado pessoal sensivel; so nome de urna, partido, cargo e votos nominais (resultado oficial)."""
import collections, datetime as dt, gzip, json, os
from core.site import E, slugify
from .dados import UF, data_br, num, pct
from . import local as _loc


def ligado(S):
    c = S.CFG.get("prefeitos") or {}
    return bool(os.environ.get("PREFEITOS_FORCE")) or (bool(c.get("ativo")) and dt.date.today().isoformat() >= str(c.get("liberar_em") or "9999-12-31")[:10])


def build(S):
    f = S.ROOT / "data/tse/prefeitos.json.gz"
    if not ligado(S) or not f.exists() or not getattr(S, "mun", None): return {"urls": []}
    D = json.loads(gzip.decompress(f.read_bytes())); _loc.tse(S); t2c = _loc._T["t2c"]; M, URL = S.mun["M"], S.mun["URL"]; site = S.CFG["site_name"]; col = D["gerado"]; urls = []
    q = S.CFG.setdefault("qualidade", {}).setdefault("faq_pseo", {}); ex = q.setdefault("hubs_exatos", [])
    por_uf = collections.defaultdict(list)
    for t, e in D["m"].items():
        c = t2c.get(t) or t2c.get(t.lstrip("0"))
        if c and e["p"]: por_uf[M[c]["uf"]].append((c, e))
    FONTE = '<a href="https://dadosabertos.tse.jus.br/" target="_blank" rel="noopener">Dados abertos do TSE</a> (candidaturas e votação nominal, eleições municipais de 2024)'
    SLM = lambda c: URL[c].rstrip("/").rsplit("/", 1)[1]
    tot_p = 0
    for uf, L in por_uf.items():
        L.sort(key=lambda x: slugify(M[x[0]]["n"])); ex += [f"/prefeito/{uf.lower()}/"]
        for c, e in L:
            mn = M[c]["n"]; sl = SLM(c); u = f"/prefeito/{uf.lower()}/{sl}/"; p = e["p"]; v = e["v"]; ve = e["ve"]
            part = collections.Counter(x[1] for x in ve); tv = sum(x[2] or 0 for x in ve)
            body = f'<article class="post"><h1>Prefeito e vereadores de {E(mn)} ({uf})</h1>'
            body += (f'<p class="snippet">O prefeito de <a href="{URL[c]}">{E(mn)}</a> ({UF[uf]}) eleito em 2024 é <strong>{E(p[0])}</strong> ({E(p[1])}), com {num(p[2] or 0)} votos nominais'
                     + (f' no {p[3]}º turno' if p[3] > 1 else "") + (f'. O vice-prefeito eleito é {E(v[0])} ({E(v[1])}).' if v else ".") + f' A Câmara Municipal tem {num(len(ve))} vereadores eleitos, de {len(part)} partido(s). Mandato de 2025 a 2028, segundo o resultado oficial do TSE.</p>')
            body += "<h2>Executivo municipal</h2>" + S.table(["Cargo", "Nome de urna", "Partido", "Votos nominais"], [["Prefeito", E(p[0]), E(p[1]), num(p[2] or 0)]] + ([["Vice-prefeito", E(v[0]), E(v[1]), "na chapa do prefeito"]] if v else []), "Eleitos em 2024")
            if ve:
                body += "<h2>Vereadores eleitos</h2>" + S.table(["Vereador (nome de urna)", "Partido", "Votos nominais"], [[E(x[0]), E(x[1]), num(x[2] or 0)] for x in ve], "Ordenados por votos nominais")
                body += "<h2>Cadeiras por partido na Câmara Municipal</h2>" + S.table(["Partido", "Vereadores eleitos", "% das cadeiras"], [[E(k), str(n), pct(n, len(ve))] for k, n in sorted(part.items(), key=lambda kv: (-kv[1], kv[0]))], "Resultado de 2024, sem trocas partidárias posteriores")
                top = part.most_common(1)[0]
                body += f'<p>O partido com mais cadeiras é {E(top[0])}, com {top[1]} de {len(ve)} ({pct(top[1], len(ve))}). A composição reflete o resultado da eleição de 2024 e não acompanha mudanças de partido ocorridas depois.</p>'
            body += (f'<h2>Sobre o município</h2><p><a href="/prefeitura/{uf.lower()}/{sl}/">Prefeitura de {E(mn)}: orçamento e receitas</a> · <a href="/verbas-federais/{uf.lower()}/{sl}/">Emendas e verbas federais</a> · <a href="/eleitorado/{uf.lower()}/{sl}/">Eleitorado e zonas</a> · <a href="/representantes/{uf.lower()}/{sl}/">Quem representa no Congresso</a> · <a href="/prefeito/{uf.lower()}/">Prefeitos de {UF[uf]}</a>.</p>'
                     f'<p class="src">Fonte oficial: {FONTE}. Compilação em {data_br(col)}. Só resultado oficial: sem patrimônio, CPF ou dados pessoais sensíveis. Erros: <a href="/correcoes/">correções</a>.</p></article>')
            fa = [(f"Quem é o prefeito de {mn}?", f"{p[0]} ({p[1]}), eleito em 2024 com {num(p[2] or 0)} votos nominais, para o mandato de 2025 a 2028."),
                  (f"Quantos vereadores tem {mn}?", f"{num(len(ve))} vereadores eleitos em 2024, de {len(part)} partido(s)."),
                  ("De onde vêm os dados?", "Dos dados abertos do TSE sobre candidaturas e votação nominal das eleições municipais de 2024.")]
            S.write(u, S.page(f"Prefeito e vereadores de {mn} ({uf}) | {site}", f"Prefeito, vice e {num(len(ve))} vereadores eleitos em {mn} ({uf}) em 2024, com partido e votos nominais, segundo o TSE.", u, body, faqs=fa,
                              crumbs=[("Prefeitos", "/prefeito/"), (UF[uf], f"/prefeito/{uf.lower()}/"), (mn, u)]), familia="prefeitos", lastmod=col); urls.append(u); tot_p += 1
        rows = [[f'<a href="/prefeito/{uf.lower()}/{SLM(c)}/">{E(M[c]["n"])}</a>', E(e["p"][0]), E(e["p"][1]), num(len(e["ve"]))] for c, e in L]
        fa = [(f"Quantos prefeitos há em {UF[uf]}?", f"{num(len(L))} municípios com prefeito eleito em 2024 constam na base."), ("Quando termina o mandato?", "Em 31 de dezembro de 2028."),
              ("De onde vêm os dados?", "Dos dados abertos do TSE, eleições municipais de 2024."), ("Há dados de patrimônio ou pessoais?", "Não. Só nome de urna, partido, cargo e votos nominais."), ("Como corrigir um dado?", 'Pela página de <a href="/correcoes/">correções</a>.')]
        S.write(f"/prefeito/{uf.lower()}/", S.page(f"Prefeitos e vereadores de {UF[uf]} eleitos em 2024 | {site}", f"Prefeitos eleitos em 2024 nos {num(len(L))} municípios de {UF[uf]}, com partido e número de vereadores, segundo o TSE.", f"/prefeito/{uf.lower()}/",
                '<article class="post"><h1>Prefeitos e vereadores de ' + E(UF[uf]) + f'</h1><p class="snippet">{num(len(L))} municípios de {E(UF[uf])} com prefeito eleito em 2024. Cada município tem página com vice, vereadores e cadeiras por partido.</p>'
                + S.table(["Município", "Prefeito (nome de urna)", "Partido", "Vereadores"], rows, "Eleições municipais de 2024, TSE") + f'<p class="src">Fonte: {FONTE}. Compilação em {data_br(col)}.</p></article>', faqs=fa, crumbs=[("Prefeitos", "/prefeito/"), (UF[uf], f"/prefeito/{uf.lower()}/")]), familia="paginas", lastmod=col); urls.append(f"/prefeito/{uf.lower()}/")
    ex.append("/prefeito/")
    fa = [("Quantos prefeitos foram eleitos em 2024?", f"{num(tot_p)} municípios com prefeito eleito constam na base do Estrato."), ("Quando termina o mandato?", "Em 31 de dezembro de 2028."), ("De onde vêm os dados?", "Dos dados abertos do TSE."),
          ("O Estrato publica patrimônio dos candidatos?", "Não. Só nome de urna, partido, cargo e votos nominais."), ("O Estrato apoia candidatos?", "Não. É um resumo do resultado oficial, sem opinião nem campanha.")]
    S.write("/prefeito/", S.page(f"Prefeitos e vereadores eleitos em 2024, por estado | {site}", f"Prefeitos e vereadores eleitos em 2024 em {num(tot_p)} municípios, por estado, com partido e votos nominais, segundo o TSE.", "/prefeito/",
            f'<article class="post"><h1>Prefeitos e vereadores eleitos em 2024</h1><p class="snippet">Escolha o estado para ver os prefeitos eleitos em 2024, com partido, e a composição das câmaras municipais. Dados oficiais do TSE; {num(tot_p)} municípios.</p><ul class="cols">'
            + "".join(f'<li><a href="/prefeito/{uf.lower()}/">{E(UF[uf])}</a></li>' for uf in sorted(por_uf)) + f'</ul><p class="src">Fonte: {FONTE}. Compilação em {data_br(col)}.</p></article>', faqs=fa, crumbs=[("Prefeitos", "/prefeito/")]), familia="paginas", lastmod=col); urls.append("/prefeito/")
    return {"urls": urls}
