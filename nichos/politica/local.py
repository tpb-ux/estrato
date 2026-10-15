"""Paginas por intencao de busca, SEO local (MPI): para cada municipio e estado, com dados oficiais ja coletados (SICONFI, IBGE, emendas, Camara/Senado, TSE perfil do eleitorado).
Familias (todas em noindex ate a onda propria, so hubs indexaveis; texto factual, listas alfabeticas, sem ranking):
  /prefeitura/<uf>/<slug>/       Prefeitura de X: orcamento, receitas, despesas, fiscalizacao        (familia prefeituras)
  /verbas-federais/<uf>/<slug>/  Emendas e verbas federais em X por ano                              (familia verbas)
  /representantes/<uf>/<slug>/   Quem representa X no Congresso (+ /representantes/<uf>/)            (familia representantes)
  /eleitorado/<uf>/<slug>/       Eleicoes em X: eleitorado, zonas e locais de votacao (TSE)          (familia eleitorado)
  /perguntas/local/<uf>/<slug>/  Perguntas locais com resposta direta e dados                        (familia perguntas_local)
Mais: bloco extra na pagina /estados/<uf>/ (orcamento, eleitorado, municipios, bairros). Roda depois de `financas` e antes de `subcategorias`."""
import collections, difflib, gzip, json, statistics
from core.site import E, slugify
from .dados import UF, PREP, brl, brl0, data_br, num, pct
from .financas import ult, ant, var, fmt_pc, n1, FONTE_T, FONTE_I
from . import emendas as _em, cotas as _cot

ART = {"do": "o", "da": "a", "de": ""}
FONTE_TSE = '<a href="https://dadosabertos.tse.jus.br/dataset/eleitorado-atual" target="_blank" rel="noopener">dados abertos do TSE (perfil do eleitorado)</a>'
FONTE_EM = '<a href="https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares" target="_blank" rel="noopener">Portal da Transparência (CGU)</a>'
FAMS = ["prefeituras", "verbas", "representantes", "eleitorado", "perguntas_local"]
_T = {}


def tse(S):
    """Dados do TSE por codigo IBGE: {cod_ibge: (registro_municipio, locais)} e por UF."""
    if "d" in _T: return _T["d"]
    f = S.ROOT / "data/tse/eleitorado.json.gz"
    d = json.loads(gzip.decompress(f.read_bytes())) if f.exists() else {"m": {}, "locais": {}, "gerado": "", "base": ""}
    idx = {(S.mun["M"][c]["uf"], slugify(S.mun["M"][c]["n"])): c for c in S.mun["M"]}
    por_uf = collections.defaultdict(dict)
    for c, e in S.mun["M"].items(): por_uf[e["uf"]][slugify(e["n"])] = c
    out = {}; t2c = {}
    for t, x in d["m"].items():
        if x["uf"] not in UF: continue
        k = (x["uf"], slugify(x["n"])); c = idx.get(k)
        if not c:
            q = difflib.get_close_matches(slugify(x["n"]), list(por_uf[x["uf"]]), n=1, cutoff=0.85); c = por_uf[x["uf"]][q[0]] if q else None
        if c and c not in out: out[c] = (x, d["locais"].get(t)); t2c[t] = c
    _T["t2c"] = t2c; _T["d"] = (out, d.get("base") or d.get("gerado")); return _T["d"]


def mediana(v): v = [x for x in v if x is not None]; return statistics.median(v) if v else None


def nomes_aut(S, ED):
    """URL da pagina de emendas de cada autor (mesma regra de nichos/politica/emendas.py)."""
    r = {}
    for c, a in ED["autores"].items():
        s = slugify(a["nome"]) or c
        for u in (f"/emendas/autor/{s}/", f"/emendas/autor/{s}-{c}/"):
            if u in S.urls: r[c] = u; break
    return r


def build(S):
    q = S.CFG.setdefault("qualidade", {}).setdefault("faq_pseo", {})
    q.setdefault("prefixos", []).extend(["/prefeitura/", "/verbas-federais/", "/representantes/", "/eleitorado/", "/bairros/"])
    ex = q.setdefault("hubs_exatos", [])
    for r_ in ("/prefeitura/", "/verbas-federais/", "/eleitorado/", "/representantes/"): ex.extend(f"{r_}{u_.lower()}/" for u_ in UF)
    if not getattr(S, "mun", None): return {"urls": []}
    m = S.mun; M, URL, POP, UD, por_uf, ib, ED, sc = m["M"], m["URL"], m["POP"], m["UD"], m["por_uf"], m["ib"], m["ED"], m["sc"]
    col = m["col"]; site = S.CFG["site_name"]; urls = []; hubs = []
    TS, tse_base = tse(S)
    em_idx = m["em_idx"]; aurl = nomes_aut(S, ED)
    parl = {}
    for d in S.parl["deps"]: parl.setdefault(slugify(d["nome"]), ("deputado", d))
    for x in S.parl["sens"]: parl.setdefault(slugify(x["nome"]), ("senador", x))
    fonte_fin = f"{FONTE_T} (DCA) e {FONTE_I}"
    # medianas por UF: transferencias/receita, saude e educacao por habitante, impostos/receita
    medc = {}
    for uf, L in por_uf.items():
        tcs, sps, eps, ims = [], [], [], []
        for c in L:
            a, d = UD[c]; p = POP[c]
            if not d.get("rec") or not p: continue
            if d.get("tc") is not None: tcs.append(d["tc"] / d["rec"])
            if d.get("imp") is not None: ims.append(d["imp"] / d["rec"])
            fn = d.get("fun") or {}
            if fn.get("10"): sps.append(fn["10"][1] / p)
            if fn.get("12"): eps.append(fn["12"][1] / p)
        medc[uf] = {"tc": mediana(tcs), "imp": mediana(ims), "saude": mediana(sps), "edu": mediana(eps)}
    nm_uf = lambda uf: f"{PREP[uf]} {UF[uf]}"
    def emd(c):
        k = em_idx.get((M[c]["uf"], slugify(M[c]["n"])))
        return (k, ED["mun"][k]) if k else (None, None)
    def vizinhos(L, i, n=4):
        v = L[max(0, i - n):i] + L[i + 1:i + 1 + n]
        return ", ".join(f'<a href="{URL[x]}">{E(M[x]["n"])}</a>' for x in v)
    def viz_pref(L, i): return ", ".join(f'<a href="/prefeitura/{x_["uf"].lower()}/{URL[x].rstrip("/").rsplit("/", 1)[1]}/">{E(x_["n"])}</a>' for x in L[max(0, i - 4):i] + L[i + 1:i + 5] for x_ in [M[x]])
    def ib_slug(c): return slugify(M[c]["n"])
    ibge_link = lambda c: f'<a href="https://cidades.ibge.gov.br/brasil/{M[c]["uf"].lower()}/{ib_slug(c)}/panorama" target="_blank" rel="noopener nofollow">IBGE Cidades</a>'
    def ld_city(c, u):
        """Uma única entidade City por município (@id na página do município); cada página-irmã é um WebPage que fala dela (about)."""
        cid = S.BASE + URL[c] + "#city"
        city = {"@type": "City", "@id": cid, "name": M[c]["n"], "url": S.BASE + URL[c], "containedInPlace": {"@type": "AdministrativeArea", "name": UF[M[c]["uf"]]}, "identifier": c}
        pag = {"@type": "WebPage", "@id": S.BASE + u + "#pagina", "url": S.BASE + u, "about": {"@id": cid}, "isPartOf": {"@id": S.BASE + "/#site"}}
        out = [city, pag]
        if u.startswith("/prefeitura/"): out.append({"@type": "GovernmentOrganization", "@id": S.BASE + u + "#prefeitura", "name": f"Prefeitura de {M[c]['n']}", "areaServed": {"@id": cid}, "url": S.BASE + u})
        return out
    # senadores e deputados por UF
    deps_uf = collections.defaultdict(list); sens_uf = collections.defaultdict(list)
    for d in S.parl["deps"]: deps_uf[d["uf"]].append(d)
    for x in S.parl["sens"]: sens_uf[x["uf"]].append(x)
    for L in list(deps_uf.values()) + list(sens_uf.values()): L.sort(key=lambda x: slugify(x["nome"]))
    nat = collections.defaultdict(list)   # deputados naturais do municipio (cadastro oficial da Camara)
    idm = {(M[c]["uf"], slugify(M[c]["n"])): c for c in M}
    for d in S.parl["deps"]:
        c = idm.get((d.get("uf_nascimento"), slugify(d.get("municipio_nascimento") or "")))
        if c: nat[c].append(d)
    for x in S.parl["sens"]:
        c = idm.get((x.get("uf_naturalidade"), slugify(x.get("naturalidade") or "")))
        if c: nat[c].append(x)
    def plink(p): return f'<a href="{p["url"]}">{E(p["nome"])}</a> <small>{E(p["partido"])}-{p["uf"]}</small>'
    # =================== PREFEITURA ===================
    for uf, L in por_uf.items():
        for i, c in enumerate(L):
            e = M[c]; nome = e["n"]; pop = int(POP[c]); a, d = UD[c]; u = f"/prefeitura/{uf.lower()}/{URL[c].rstrip('/').rsplit('/', 1)[1]}/"
            a0, d0 = ant(e, a) if a else (None, {})
            md = medc[uf]; mu = f"/municipios/{uf.lower()}/"
            body = f'<article class="post"><h1>Prefeitura de {E(nome)} ({uf}): orçamento, receitas e despesas</h1>'
            fa = []
            if a and d.get("rec") and d.get("desp"):
                rec, desp = d["rec"], d["desp"]; dif = rec - desp
                body += (f'<p class="snippet">A Prefeitura de <strong>{E(nome)}</strong>, em {UF[uf]}, declarou <strong>{brl0(rec)}</strong> em receitas e <strong>{brl0(desp)}</strong> em despesas empenhadas em {a}. '
                         f'O município tinha {num(pop)} habitantes no Censo 2022, o que equivale a {fmt_pc(rec / pop)} de receita e {fmt_pc(desp / pop)} de despesa por habitante.</p>')
                body += (f'<p>Em {a}, a receita realizada ficou {"acima" if dif >= 0 else "abaixo"} da despesa empenhada em {brl0(abs(dif))} ({pct(abs(dif), rec)} da receita). '
                         'A diferença é nominal, entre dois campos da declaração anual ao Tesouro; não corresponde ao resultado fiscal oficial da prefeitura.</p>')
                rows = []
                def lin(n_, k):
                    if k in d: rows.append([n_, brl0(d[k]), brl0(d0[k]) if k in d0 else "—", var(d[k], d0.get(k)) or "—"])
                for n_, k in (("Receita total", "rec"), ("Impostos arrecadados pelo município", "imp"), ("Transferências correntes", "tc"), ("Receitas de capital", "rk"), ("Despesa empenhada", "desp")): lin(n_, k)
                fn, fn0 = d.get("fun") or {}, d0.get("fun") or {}
                for cod, n_ in (("10", "Despesa com saúde"), ("12", "Despesa com educação"), ("04", "Despesa com administração"), ("15", "Despesa com urbanismo")):
                    if fn.get(cod): rows.append([n_, brl0(fn[cod][1]), brl0(fn0[cod][1]) if fn0.get(cod) else "—", var(fn[cod][1], (fn0.get(cod) or [0, 0])[1]) or "—"])
                body += "<h2>Orçamento em números</h2>" + S.table(["Item", f"{a}", f"{a0}" if a0 else "Ano anterior", "Variação nominal"], rows, "Valores nominais declarados ao Tesouro Nacional")
                t = f"<h2>De onde vem o dinheiro da prefeitura</h2><p>"
                if d.get("tc") is not None:
                    t += f'Em {a}, as transferências correntes, que vêm de União e estado, somaram {pct(d["tc"], rec)} da receita de {E(nome)}'
                    if md["tc"]: t += f', contra uma mediana de {pct(md["tc"], 1)} entre os municípios {nm_uf(uf)}'
                    t += ". "
                if d.get("imp") is not None:
                    t += f'Os impostos cobrados pelo próprio município responderam por {pct(d["imp"], rec)}'
                    if md["imp"]: t += f' (mediana {nm_uf(uf)}: {pct(md["imp"], 1)})'
                    t += ". "
                if d.get("tc") is not None and d.get("imp") is not None: t += "Quanto maior a fatia de transferências, mais a receita depende de repasses de outros entes; o número descreve a composição, não avalia a gestão."
                body += t + "</p>"
                if fn:
                    top = sorted(fn.items(), key=lambda x: -x[1][1])[:8]
                    body += f"<h2>Para onde vai o dinheiro</h2><p>Em {a}, a maior despesa empenhada de {E(nome)} foi com <strong>{E(top[0][1][0].lower())}</strong>, com {pct(top[0][1][1], desp)} do total. "
                    if fn.get("10") and md["saude"]: body += f'Em saúde, foram {fmt_pc(fn["10"][1] / pop)} por habitante (mediana {nm_uf(uf)}: {fmt_pc(md["saude"])}). '
                    if fn.get("12") and md["edu"]: body += f'Em educação, {fmt_pc(fn["12"][1] / pop)} por habitante (mediana {nm_uf(uf)}: {fmt_pc(md["edu"])}).'
                    body += "</p>" + S.table(["Função", "Empenhado", "% da despesa"], [[E(v[0]), brl0(v[1]), pct(v[1], desp)] for _, v in top], f"As {len(top)} maiores funções de governo")
                fa = [(f"Qual o orçamento da Prefeitura de {nome}?", f"Em {a}, a prefeitura declarou {brl(rec)} em receitas e {brl(desp)} em despesas empenhadas, segundo o Tesouro Nacional."),
                      (f"Quanto a Prefeitura de {nome} gasta com saúde?", f"{brl0(fn['10'][1])} em {a}, ou {pct(fn['10'][1], desp)} da despesa empenhada." if fn.get("10") else "A declaração não traz despesa na função saúde."),
                      (f"Quanto a Prefeitura de {nome} gasta com educação?", f"{brl0(fn['12'][1])} em {a}, ou {pct(fn['12'][1], desp)} da despesa empenhada." if fn.get("12") else "A declaração não traz despesa na função educação."),
                      (f"{nome} depende de repasses?", f"As transferências correntes representaram {pct(d['tc'], rec)} da receita em {a}." if d.get("tc") is not None else "A declaração não detalha as transferências."),
                      ("De onde vêm os números?", "Da Declaração de Contas Anuais enviada pela própria prefeitura ao Tesouro Nacional (SICONFI) e do Censo 2022 do IBGE.")]
            else:
                body += f'<p class="snippet">O Tesouro Nacional não tem, na compilação do Estrato, a declaração anual completa de receitas e despesas da Prefeitura de <strong>{E(nome)}</strong> ({UF[uf]}), município com {num(pop)} habitantes no Censo 2022.</p>'
                fa = [(f"Qual o orçamento da Prefeitura de {nome}?", "A declaração anual completa não consta na base do Tesouro Nacional compilada pelo Estrato."), ("De onde vêm os números?", "Da Declaração de Contas Anuais enviada ao Tesouro Nacional (SICONFI).")]
            k, em = emd(c)
            if em:
                tot = sum(em["anos"].values())
                body += f'<h2>Emendas parlamentares recebidas</h2><p>Órgãos e entidades sediados em {E(nome)} receberam {brl0(tot)} em pagamentos de emendas ao Orçamento da União desde 2023, de {num(len(em["autores"]))} autores. Os valores por ano e por autor estão em <a href="/verbas-federais/{uf.lower()}/{u.rstrip("/").rsplit("/", 1)[1]}/">emendas e verbas federais em {E(nome)}</a>.</p>'
            else:
                body += f'<h2>Emendas parlamentares recebidas</h2><p>Não há pagamentos de emendas a favorecidos com sede em {E(nome)} na compilação do Estrato, que cobre os pagamentos desde 2023.</p>'
            sl = u.rstrip("/").rsplit("/", 1)[1]
            body += (f'<h2>Canais oficiais e fiscalização</h2><p>O Estrato só publica site, telefone e endereço de prefeituras quando constam de fonte oficial aberta. Hoje não há base nacional unificada com esses dados, então eles não são exibidos aqui. '
                     f'Para acompanhar a prefeitura, use as ferramentas públicas: as contas declaradas no <a href="https://siconfi.tesouro.gov.br/siconfi/pages/public/consulta_finbra/finbra_list.jsf" target="_blank" rel="noopener">SICONFI</a>, '
                     f'o <a href="https://portaldatransparencia.gov.br/" target="_blank" rel="noopener">Portal da Transparência</a> do governo federal para repasses da União, e o painel {ibge_link(c)} do IBGE. '
                     'A fiscalização das contas municipais cabe à Câmara de Vereadores, com auxílio do Tribunal de Contas competente.</p>')
            body += (f'<h2>Veja também</h2><ul><li><a href="{URL[c]}">{E(nome)}: receitas, despesas e indicadores</a></li><li><a href="/verbas-federais/{uf.lower()}/{sl}/">Emendas e verbas federais em {E(nome)}</a></li>'
                     f'<li><a href="/representantes/{uf.lower()}/{sl}/">Quem representa {E(nome)} no Congresso</a></li><li><a href="/eleitorado/{uf.lower()}/{sl}/">Eleitorado e locais de votação em {E(nome)}</a></li>'
                     f'<li><a href="/perguntas/local/{uf.lower()}/{sl}/">Perguntas e respostas sobre {E(nome)}</a></li></ul><p>Outras prefeituras {nm_uf(uf)}: {viz_pref(L, i)}.</p>')
            body += f'<p class="src">Fontes oficiais: {fonte_fin}, exercícios 2023 e 2024, e {FONTE_EM}. Compilação em {data_br(col)}. Valores nominais. <a href="/municipios/metodologia/">Metodologia</a>.</p></article>'
            desc = f"Orçamento da Prefeitura de {nome} ({uf}): receitas, despesas por função, repasses e emendas recebidas, com dados do Tesouro e do IBGE."
            S.write(u, S.page(f"Prefeitura de {nome} ({uf}): orçamento, receitas e despesas | {site}", desc, u, body, faqs=fa, crumbs=[("Prefeituras", "/prefeitura/"), (UF[uf], f"/prefeitura/{uf.lower()}/"), (nome, u)], jsonld=ld_city(c, u)), familia="prefeituras", lastmod=col); urls.append(u)
    # slug por municipio (mesmo da pagina /municipios/): URLs auxiliares
    SL = {c: URL[c].rstrip("/").rsplit("/", 1)[1] for c in M}
    # =================== VERBAS FEDERAIS ===================
    for uf, L in por_uf.items():
        for i, c in enumerate(L):
            e = M[c]; nome = e["n"]; sl = SL[c]; u = f"/verbas-federais/{uf.lower()}/{sl}/"; pop = int(POP[c]); a, d = UD[c]; a0, d0 = ant(e, a) if a else (None, {})
            k, em = emd(c)
            body = f'<article class="post"><h1>Emendas e verbas federais em {E(nome)} ({uf}), por ano</h1>'
            fa = []
            tcs = {y: x["tc"] for y, x in e["an"].items() if x.get("tc") is not None}
            if em:
                tot = sum(em["anos"].values()); anos = sorted(em["anos"]); ult_y = anos[-1]
                body += (f'<p class="snippet">Órgãos, fundos e entidades sediados em <strong>{E(nome)}</strong> receberam <strong>{brl0(tot)}</strong> em pagamentos de emendas parlamentares ao Orçamento da União entre {anos[0]} e {ult_y}, '
                         f'de {num(len(em["autores"]))} autores, segundo o Portal da Transparência.' + (f' Isso equivale a {fmt_pc(tot / pop)} por habitante no período.' if pop else "") + "</p>")
                body += "<h2>Emendas pagas por ano</h2>" + S.table(["Ano do pagamento", "Valor pago", "Variação em relação ao ano anterior"], [[y, brl0(em["anos"][y]), (var(em["anos"][y], em["anos"][anos[j - 1]]) if j else "—") or "—"] for j, y in enumerate(anos)], "Pagamentos a favorecidos sediados no município (o ano corrente é parcial)")
                ra = sorted(em["autores"].items(), key=lambda x: -x[1])[:25]
                rows = []
                for cd, v in sorted(ra, key=lambda x: slugify(ED["autores"].get(x[0], {}).get("nome", "z"))):
                    au = ED["autores"].get(cd)
                    if not au: continue
                    nm_ = _em.tit(au["nome"]); pp = parl.get(slugify(au["nome"]))
                    rows.append([f'<a href="{aurl[cd]}">{E(nm_)}</a>' if cd in aurl else E(nm_), (f'<a href="{pp[1]["url"]}">{E(pp[1]["partido"])}-{pp[1]["uf"]}</a>' if pp else "—"), brl0(v)])
                body += (f"<h2>Autores das emendas</h2><p>Os {len(rows)} autores com maior valor recebido em {E(nome)}, em ordem alfabética" + (f", de um total de {num(len(em['autores']))}" if len(em["autores"]) > len(rows) else "") + ". Autoria coletiva, como bancadas e comissões, aparece com o nome da bancada ou comissão.</p>" + S.table(["Autor", "Partido-UF", "Valor recebido no município"], rows))
            else:
                body += f'<p class="snippet">Não há pagamentos de emendas parlamentares a favorecidos com sede em <strong>{E(nome)}</strong> ({UF[uf]}) na compilação do Estrato, que cobre os pagamentos ao município desde 2023.</p>'
            if tcs:
                ys = sorted(tcs)
                rows = [[y, brl0(tcs[y]), pct(tcs[y], e["an"][y]["rec"]) if e["an"][y].get("rec") else "—"] for y in ys]
                body += f'<h2>Transferências correntes recebidas pela prefeitura</h2><p>Além das emendas, a prefeitura recebe transferências de outros entes, como o Fundo de Participação dos Municípios e repasses do SUS e da educação. Nos exercícios declarados ao Tesouro, elas somaram:</p>' + S.table(["Exercício", "Transferências correntes", "% da receita"], rows, "Receitas declaradas pela prefeitura (DCA)")
                if len(ys) > 1 and tcs[ys[-1]] and tcs[ys[0]]: body += f"<p>A variação nominal entre {ys[0]} e {ys[-1]} foi de {var(tcs[ys[-1]], tcs[ys[0]])}.</p>"
            else:
                body += "<h2>Transferências correntes recebidas pela prefeitura</h2><p>A declaração anual da prefeitura ao Tesouro Nacional não consta com esse detalhe na compilação do Estrato.</p>"
            body += (f'<p>As emendas aparecem separadas das transferências porque seguem caminhos diferentes: emendas são indicadas por parlamentares no Orçamento da União; transferências correntes englobam repasses constitucionais e legais. Os dois valores não devem ser somados sem cuidado, já que parte das emendas é paga a entidades que não são a prefeitura.</p>'
                     f'<h2>Veja também</h2><ul><li><a href="/prefeitura/{uf.lower()}/{sl}/">Prefeitura de {E(nome)}: orçamento e despesas</a></li><li><a href="{URL[c]}">{E(nome)}: indicadores do município</a></li>'
                     f'<li><a href="/representantes/{uf.lower()}/{sl}/">Quem representa {E(nome)} no Congresso</a></li>' + (f'<li><a href="/emendas/municipios/{uf.lower()}/{slugify(k.split("|", 1)[1])}/">Painel de emendas de {E(nome)}</a></li>' if k and f"/emendas/municipios/{uf.lower()}/{slugify(k.split('|', 1)[1])}/" in S.urls else "") + '<li><a href="/emendas/">Emendas parlamentares no Brasil</a></li></ul>')
            body += f'<p class="src">Fontes oficiais: {FONTE_EM}, emendas pagas desde 2023; {FONTE_T}, DCA. Compilação em {data_br(col)}. Valores nominais. Veja a <a href="/emendas/metodologia/">metodologia de emendas</a>.</p></article>'
            if em: fa = [(f"Quanto {nome} recebeu em emendas parlamentares?", f"{brl(sum(em['anos'].values()))} em pagamentos a favorecidos sediados no município, entre {min(em['anos'])} e {max(em['anos'])}."), (f"Quantos parlamentares enviaram emendas para {nome}?", f"{num(len(em['autores']))} autores, entre individuais, de bancada e de comissão."),
                          (f"Quem manda dinheiro para {nome}?", f'Emendas de {num(len(em["autores"]))} autores, listados nesta página, e transferências constitucionais da União e do estado, como o FPM.'), ("Emenda é o mesmo que repasse do FPM?", "Não. O FPM é transferência constitucional; a emenda é indicada por parlamentares no Orçamento."), ("Os valores são do ano corrente?", "Os pagamentos de 2026 são parciais, até a data de compilação.")]
            else: fa = [(f"{nome} recebeu emendas parlamentares?", "Não há pagamentos a favorecidos sediados no município na compilação, que cobre desde 2023."), ("Emenda é o mesmo que repasse do FPM?", "Não. O FPM é transferência constitucional; a emenda é indicada por parlamentares no Orçamento.")]
            S.write(u, S.page(f"Emendas e verbas federais em {nome} ({uf}) por ano | {site}", f"Quanto {nome} ({uf}) recebeu de emendas parlamentares e de transferências federais por ano, quem enviou os recursos e de que fontes vêm os dados.", u, body, faqs=fa,
                              crumbs=[("Verbas federais", "/verbas-federais/"), (UF[uf], f"/verbas-federais/{uf.lower()}/"), (nome, u)], jsonld=ld_city(c, u)), familia="verbas", lastmod=col); urls.append(u)
    # =================== REPRESENTANTES ===================
    for uf, L in por_uf.items():
        dd, ss = deps_uf[uf], sens_uf[uf]
        for i, c in enumerate(L):
            e = M[c]; nome = e["n"]; sl = SL[c]; u = f"/representantes/{uf.lower()}/{sl}/"; k, em = emd(c)
            body = f'<article class="post"><h1>Quem representa {E(nome)} ({uf}) no Congresso</h1>'
            body += (f'<p class="snippet">No Congresso Nacional, <strong>{E(nome)}</strong> não elege um representante próprio: os eleitores votam em deputados federais e senadores de todo o estado {PREP[uf]} <a href="/deputados/uf/{uf.lower()}/">{UF[uf]}</a>. '
                     f'A bancada é de <strong>{num(len(dd))} deputados federais</strong> e <strong>{num(len(ss))} senadores</strong>. Abaixo estão os senadores, os parlamentares naturais de {E(nome)} e os autores de emendas pagas ao município.</p>')
            body += f"<h2>Senadores {PREP[uf]} {E(UF[uf])}</h2>" + S.table(["Senador", "Partido", "Votos registrados em votações nominais"], [[f'<a href="{x["url"]}">{E(x["nome"])}</a>', E(x["partido"]), "{} de {}".format(*[num(v) for v in _cot.presenca(S, "senado", int(x["id"]))])] for x in ss], "Em ordem alfabética")
            nn = sorted(nat.get(c, []), key=lambda x: slugify(x["nome"]))
            if nn: body += f"<h2>Parlamentares naturais de {E(nome)}</h2><p>Segundo o cadastro oficial da Câmara e do Senado, nasceram em {E(nome)}:</p><ul>" + "".join(f"<li>{plink(x)}</li>" for x in nn) + "</ul>"
            else: body += f"<h2>Parlamentares naturais de {E(nome)}</h2><p>Nenhum deputado ou senador em exercício consta, no cadastro oficial, como natural de {E(nome)}.</p>"
            if em:
                ps = []
                for cd, v in em["autores"].items():
                    au = ED["autores"].get(cd)
                    if not au: continue
                    pp = parl.get(slugify(au["nome"]))
                    if pp: ps.append((pp[1], v))
                ps.sort(key=lambda x: slugify(x[0]["nome"]))
                if ps: body += (f"<h2>Parlamentares em exercício que enviaram emendas a {E(nome)}</h2><p>{num(len(ps))} dos {num(len(em['autores']))} autores de emendas pagas ao município são deputados ou senadores em exercício. Em ordem alfabética:</p>" + S.table(["Parlamentar", "UF", "Pago ao município desde 2023"], [[plink(p).split(" <small>")[0], p["uf"], brl0(v)] for p, v in ps[:40]]))
                else: body += f"<h2>Emendas ao município</h2><p>Os autores das emendas pagas a {E(nome)} não incluem parlamentares atualmente em exercício identificados pelo nome.</p>"
            else: body += f"<h2>Emendas ao município</h2><p>Não há pagamentos de emendas parlamentares a favorecidos sediados em {E(nome)} na compilação do Estrato.</p>"
            body += (f'<h2>Veja também</h2><ul><li><a href="{URL[c]}">{E(nome)}: população, receitas e indicadores</a></li><li><a href="/representantes/{uf.lower()}/">Bancada completa {PREP[uf]} {E(UF[uf])} no Congresso</a>, com presença e cota parlamentar</li><li><a href="/verbas-federais/{uf.lower()}/{sl}/">Emendas e verbas federais em {E(nome)}</a></li>'
                     f'<li><a href="/prefeitura/{uf.lower()}/{sl}/">Prefeitura de {E(nome)}</a></li><li><a href="/deputados/uf/{uf.lower()}/">Deputados federais {PREP[uf]} {E(UF[uf])}</a></li></ul>')
            body += f'<p class="src">Fontes oficiais: Câmara dos Deputados e Senado Federal (dados abertos), {FONTE_EM}. Compilação em {data_br(col)}. A lista não é ranking e não indica preferência de voto.</p></article>'
            fa = [(f"Quem são os senadores que representam {nome}?", ", ".join(E(x["nome"]) for x in ss) + f". Cada estado elege três senadores."), (f"Quantos deputados federais representam {nome}?", f"{num(len(dd))}, a bancada inteira {PREP[uf]} {UF[uf]}, porque a eleição de deputado federal é estadual."),
                  (f"{nome} tem deputado federal próprio?", "Não. A eleição é por estado; um deputado pode ter votos de qualquer município."), (f"Quantos parlamentares nasceram em {nome}?", f"{num(len(nn))} em exercício, segundo o cadastro oficial."), ("Os dados são oficiais?", "Sim: cadastro e votações da Câmara e do Senado e pagamentos do Portal da Transparência.")]
            S.write(u, S.page(f"Quem representa {nome} ({uf}) no Congresso | {site}", f"Senadores e bancada federal que representam {nome} ({uf}), parlamentares naturais do município e autores de emendas pagas a {nome}.", u, body, faqs=fa,
                              crumbs=[("Representantes", "/representantes/"), (UF[uf], f"/representantes/{uf.lower()}/"), (nome, u)], jsonld=ld_city(c, u)), familia="representantes", lastmod=col); urls.append(u)
    # =================== ELEITORADO ===================
    hoje = data_br(str(tse_base)[:10]) if tse_base and "-" in str(tse_base) else str(tse_base)
    for uf, L in por_uf.items():
        for i, c in enumerate(L):
            e = M[c]; nome = e["n"]; sl = SL[c]; u = f"/eleitorado/{uf.lower()}/{sl}/"; pop = int(POP[c]); t = TS.get(c)
            body = f'<article class="post"><h1>Eleições em {E(nome)} ({uf}): eleitorado, zonas e locais de votação</h1>'
            if t:
                x, lo = t; tot = x["tot"]
                body += (f'<p class="snippet"><strong>{E(nome)}</strong> tem <strong>{num(tot)} eleitores</strong> aptos, segundo o perfil do eleitorado do TSE (base de {E(hoje)}), o equivalente a {pct(tot, pop)} da população do Censo 2022. '
                         f'{pct(x["fem"], tot)} são mulheres e {pct(x["mas"], tot)}, homens' + (f'. O município tem {num(lo["z"])} zona(s) eleitoral(is), {num(lo["l"])} locais de votação e {num(lo["s"])} seções (eleições de 2024).' if lo else ".") + "</p>")
                fx = x["fx"]; ordem = ["16 a 17", "18 a 24", "25 a 34", "35 a 44", "45 a 59", "60 a 69", "70 ou mais"]
                body += "<h2>Eleitorado por faixa etária</h2>" + S.table(["Faixa etária", "Eleitores", "% do eleitorado"], [[f, num(fx.get(f, 0)), pct(fx.get(f, 0), tot)] for f in ordem if f in fx])
                ins = sorted(x["ins"].items(), key=lambda z: -z[1])
                body += "<h2>Eleitorado por escolaridade</h2>" + S.table(["Grau de instrução", "Eleitores", "% do eleitorado"], [[E(g), num(v), pct(v, tot)] for g, v in ins], "Escolaridade declarada ao cadastrar o título")
                body += (f'<h2>Voto obrigatório, biometria e acessibilidade</h2><p>O voto é facultativo para {num(x["fac"])} eleitores de {E(nome)} ({pct(x["fac"], tot)}): jovens de 16 e 17 anos, maiores de 70 e pessoas que não leem nem escrevem. '
                         f'A biometria está cadastrada para {pct(x["bio"], tot)} do eleitorado, e {num(x["def"])} eleitores ({pct(x["def"], tot)}) declararam alguma deficiência ao TSE, informação usada para planejar a acessibilidade dos locais de votação.</p>')
                if lo: body += (f'<h2>Zonas, locais de votação e seções</h2><p>Nas eleições de 2024, {E(nome)} teve {num(lo["l"])} locais de votação, com {num(lo["s"])} seções distribuídas em {num(lo["z"])} zona(s) eleitoral(is). Em média, cada seção reunia {num(round(lo["e"] / max(lo["s"], 1)))} eleitores aptos. '
                                f'Zonas eleitorais do perfil atual: {", ".join(str(z) for z in x["zonas"])}. O local e a seção de cada eleitor aparecem no aplicativo e-Título e no site do TSE.</p>')
                fa = [(f"Quantos eleitores tem {nome}?", f"{num(tot)} eleitores aptos, segundo o perfil do eleitorado do TSE (base de {hoje})."), (f"Quantas zonas eleitorais tem {nome}?", f"{num(len(x['zonas']))} zona(s): {', '.join(str(z) for z in x['zonas'])}."),
                      (f"Qual a faixa etária que mais tem eleitores em {nome}?", f"A faixa de {max(fx, key=fx.get)} anos, com {pct(max(fx.values()), tot)} do eleitorado." if fx else "Sem dado."), (f"Quantos locais de votação há em {nome}?", f"{num(lo['l'])} locais e {num(lo['s'])} seções nas eleições de 2024." if lo else "O dado de locais de votação não consta na base."),
                      ("O que é perfil do eleitorado?", "É o conjunto de totais por gênero, idade e escolaridade dos eleitores aptos, publicado pelo TSE sem identificar ninguém.")]
            else:
                body += f'<p class="snippet">O perfil do eleitorado do TSE não foi associado a <strong>{E(nome)}</strong> ({UF[uf]}) na compilação do Estrato. O município tinha {num(pop)} habitantes no Censo 2022.</p>'
                fa = [(f"Quantos eleitores tem {nome}?", "O dado não foi associado ao município na compilação."), ("O que é perfil do eleitorado?", "É o conjunto de totais por gênero, idade e escolaridade dos eleitores aptos, publicado pelo TSE sem identificar ninguém.")]
            body += (f'<h2>Veja também</h2><ul><li><a href="/prefeitura/{uf.lower()}/{sl}/">Prefeitura de {E(nome)}</a></li><li><a href="/representantes/{uf.lower()}/{sl}/">Quem representa {E(nome)} no Congresso</a></li><li><a href="{URL[c]}">{E(nome)}: indicadores do município</a></li>'
                     f'<li><a href="/eleicoes/">Editoria Eleições</a> e o <a href="/calendario/">calendário eleitoral</a></li></ul>')
            body += f'<p class="src">Fonte oficial: {FONTE_TSE} e locais de votação 2024. Dados agregados, sem identificação de eleitores. Compilação em {data_br(col)}. O Estrato não publica pesquisas eleitorais nem conteúdo de campanha.</p></article>'
            S.write(u, S.page(f"Eleições em {nome} ({uf}): eleitorado e locais de votação | {site}", f"Perfil do eleitorado de {nome} ({uf}): eleitores por idade e escolaridade, zonas eleitorais, locais de votação e seções, com dados oficiais do TSE.", u, body, faqs=fa,
                              crumbs=[("Eleitorado", "/eleitorado/"), (UF[uf], f"/eleitorado/{uf.lower()}/"), (nome, u)], jsonld=ld_city(c, u)), familia="eleitorado", lastmod=col); urls.append(u)
    # =================== PERGUNTAS LOCAIS ===================
    for uf, L in por_uf.items():
        for i, c in enumerate(L):
            e = M[c]; nome = e["n"]; sl = SL[c]; u = f"/perguntas/local/{uf.lower()}/{sl}/"; pop = int(POP[c]); a, d = UD[c]; k, em = emd(c); t = TS.get(c); fn = d.get("fun") or {}
            ss = sens_uf[uf]; dd = deps_uf[uf]
            fa = []
            if a and d.get("tc") is not None and d.get("rec"):
                s_ = f"Em {a}, a prefeitura declarou {brl(d['tc'])} em transferências correntes, que vêm de União e estado, o equivalente a {pct(d['tc'], d['rec'])} da receita"
                if em: s_ += f", e órgãos sediados no município receberam {brl0(sum(em['anos'].values()))} em emendas parlamentares federais desde 2023"
                fa.append((f"Quanto {nome} recebe do governo federal?", s_ + f'. Detalhes por ano em <a href="/verbas-federais/{uf.lower()}/{sl}/">emendas e verbas federais em {E(nome)}</a>.'))
            else: fa.append((f"Quanto {nome} recebe do governo federal?", (f"Órgãos sediados no município receberam {brl0(sum(em['anos'].values()))} em emendas federais desde 2023. " if em else "") + f'As transferências declaradas pela prefeitura não constam na base. Veja <a href="/verbas-federais/{uf.lower()}/{sl}/">emendas e verbas federais em {E(nome)}</a>.'))
            fa.append((f"Quem manda dinheiro para {nome}?", (f"{num(len(em['autores']))} autores de emendas parlamentares enviaram recursos pagos a favorecidos sediados em {E(nome)} desde 2023, além das transferências constitucionais da União e do estado. " if em else "Não há emendas pagas a favorecidos sediados no município na compilação; ficam as transferências constitucionais da União e do estado. ") + f'Lista de autores em <a href="/verbas-federais/{uf.lower()}/{sl}/">verbas federais</a>.'))
            if a and d.get("rec"): fa.append((f"Qual o orçamento de {nome}?", f"{brl(d['rec'])} em receitas e {brl(d['desp'])} em despesas empenhadas em {a}. Veja <a href=\"/prefeitura/{uf.lower()}/{sl}/\">Prefeitura de {E(nome)}</a>." if d.get("desp") else f"{brl(d['rec'])} em receitas em {a}."))
            else: fa.append((f"Qual o orçamento de {nome}?", "A declaração anual do município não consta na base do Tesouro Nacional compilada pelo Estrato."))
            fa.append((f"Quantos habitantes tem {nome}?", f"{num(pop)}, segundo o Censo 2022 do IBGE" + (f", em {n1(ib['m'][c]['area'])} km² (densidade de {n1(ib['m'][c]['dens'])} hab./km²)." if ib["m"].get(c, {}).get("area") and ib["m"][c].get("dens") else ".")))
            if fn.get("10") or fn.get("12"): fa.append((f"Quanto {nome} gasta com saúde e educação?", (f"Saúde: {brl0(fn['10'][1])} ({pct(fn['10'][1], d['desp'])} da despesa). " if fn.get("10") and d.get("desp") else "") + (f"Educação: {brl0(fn['12'][1])} ({pct(fn['12'][1], d['desp'])}). " if fn.get("12") and d.get("desp") else "") + f"Valores empenhados em {a}."))
            if t: fa.append((f"Quantos eleitores tem {nome}?", f"{num(t[0]['tot'])} eleitores aptos, em {num(len(t[0]['zonas']))} zona(s) eleitoral(is). Veja <a href=\"/eleitorado/{uf.lower()}/{sl}/\">eleições em {E(nome)}</a>."))
            fa.append((f"Quem representa {nome} no Congresso?", f"Os {num(len(ss))} senadores e os {num(len(dd))} deputados federais {PREP[uf]} {UF[uf]}: {', '.join(E(x['nome']) for x in ss)} são os senadores. Veja <a href=\"/representantes/{uf.lower()}/{sl}/\">quem representa {E(nome)}</a>."))
            body = (f'<article class="post"><h1>Perguntas e respostas sobre {E(nome)} ({uf})</h1><p class="snippet">Respostas diretas, com dados oficiais, para as dúvidas mais comuns sobre <strong>{E(nome)}</strong>, município {PREP[uf]} {E(UF[uf])} com {num(pop)} habitantes: '
                    f'quanto recebe do governo federal, quem envia recursos, quanto gasta e quem o representa no Congresso. Cada resposta leva para a página de dados com a fonte.</p>')
            rows = [["População (Censo 2022)", num(pop)]]
            if a and d.get("rec"): rows += [[f"Receita da prefeitura ({a})", brl0(d["rec"])]] + ([[f"Despesa empenhada ({a})", brl0(d["desp"])]] if d.get("desp") else [])
            if em: rows.append(["Emendas pagas ao município desde 2023", brl0(sum(em["anos"].values()))])
            if t: rows.append(["Eleitores aptos", num(t[0]["tot"])])
            body += "<h2>Resumo em números</h2>" + S.table(["Indicador", "Valor"], rows)
            body += (f'<h2>Páginas de dados sobre {E(nome)}</h2><ul><li><a href="/prefeitura/{uf.lower()}/{sl}/">Prefeitura de {E(nome)}: orçamento</a></li><li><a href="/verbas-federais/{uf.lower()}/{sl}/">Emendas e verbas federais</a></li><li><a href="/representantes/{uf.lower()}/{sl}/">Quem representa no Congresso</a></li>'
                     f'<li><a href="/eleitorado/{uf.lower()}/{sl}/">Eleitorado e locais de votação</a></li><li><a href="{URL[c]}">Indicadores do município</a></li></ul>'
                     f'<p class="src">Fontes oficiais: {fonte_fin}; {FONTE_EM}; {FONTE_TSE}; Câmara e Senado. Compilação em {data_br(col)}.</p></article>')
            S.write(u, S.page(f"Perguntas sobre {nome} ({uf}): verbas, orçamento e Congresso | {site}", f"Quanto {nome} ({uf}) recebe do governo federal, quem manda dinheiro, quanto gasta e quem representa o município no Congresso: respostas com dados oficiais.", u, body, faqs=fa,
                              crumbs=[("Perguntas", "/perguntas/"), ("Perguntas locais", "/perguntas/local/"), (UF[uf], f"/perguntas/local/{uf.lower()}/"), (nome, u)], jsonld=ld_city(c, u)), familia="perguntas_local", faq_min=0, lastmod=col); urls.append(u)
    # =================== REPRESENTANTES POR UF (bancada completa) ===================
    for uf in UF:
        dd, ss = deps_uf[uf], sens_uf[uf]; u = f"/representantes/{uf.lower()}/"
        rows = []
        for d in dd:
            pr, pt = _cot.presenca(S, "camara", d["id"])
            rows.append([f'<a href="{d["url"]}">{E(d["nome"])}</a>', E(d["partido"]), brl0(d["c"]["total"]) if d["c"]["total"] else "—", f"{num(pr)} de {num(pt)}"])
        srows = [[f'<a href="{x["url"]}">{E(x["nome"])}</a>', E(x["partido"]), "{} de {}".format(*[num(v) for v in _cot.presenca(S, "senado", int(x["id"]))])] for x in ss]
        ps = collections.Counter(d["partido"] for d in dd)
        body = (f'<section class="blk"><h1>Quem representa {nm_uf(uf)} no Congresso: deputados e senadores</h1><p class="snippet">{UF[uf]} elege <strong>{num(len(dd))} deputados federais</strong> e <strong>{num(len(ss))} senadores</strong>. A bancada em exercício reúne {num(len(ps))} partidos. '
                f'As tabelas trazem presença em votações nominais e a cota parlamentar declarada no ano, sempre em ordem alfabética, sem classificação.</p><h2>Senadores</h2>' + S.table(["Senador", "Partido", "Votos registrados em votações nominais"], srows) +
                "<h2>Deputados federais</h2>" + S.table(["Deputado", "Partido", "Cota parlamentar declarada no ano", "Votos registrados em votações nominais"], rows, "Em ordem alfabética; não é ranking") +
                "<h2>Bancada por partido</h2>" + S.table(["Partido", "Deputados"], [[f'<a href="/partidos/{slugify(p)}/">{E(p)}</a>', num(n)] for p, n in sorted(ps.items())]) +
                f'<p>Veja também os <a href="/municipios/{uf.lower()}/">municípios {nm_uf(uf)}</a>, as <a href="/emendas/municipios/{uf.lower()}/">emendas por município</a> e as <a href="/financas/{uf.lower()}/">finanças do estado</a>.</p>'
                f'<p class="src">Fontes oficiais: Câmara dos Deputados e Senado Federal (dados abertos). Compilação em {data_br(col)}.</p></section>')
        fa = [(f"Quantos deputados federais {UF[uf]} tem?", f"{num(len(dd))} em exercício."), (f"Quem são os senadores {nm_uf(uf)}?", ", ".join(E(x["nome"]) for x in ss) + "."), ("A tabela é um ranking?", "Não. Os parlamentares estão em ordem alfabética, e a presença e a cota não medem a qualidade do mandato."),
              ("O que é a cota parlamentar?", 'É a verba mensal para despesas do mandato, como passagens e escritório. Veja o <a href="/cota/">painel da cota</a>.'), ("O que significa votos registrados em votações nominais?", "É o número de votações nominais de plenário em que o parlamentar registrou voto, dentre as realizadas desde fevereiro de 2023."),
              ("Como saber quem representa meu município?", f'Cada município tem uma página própria dentro de <a href="/representantes/{uf.lower()}/">{UF[uf]}</a>; use a lista abaixo ou a <a href="/busca/">busca</a>.')]
        body = body.replace('<p class="src">', "<h2>Municípios " + nm_uf(uf) + "</h2><p>Escolha o município para ver os parlamentares naturais da cidade e os autores de emendas pagas a ela:</p>" + '<ul class="cols">' + "".join(f'<li><a href="/representantes/{uf.lower()}/{SL[c]}/">{E(M[c]["n"])}</a></li>' for c in por_uf[uf]) + '</ul><p class="src">', 1)
        S.write(u, S.page(f"Quem representa {nm_uf(uf)} no Congresso | {site}", f"Deputados federais e senadores {PREP[uf]} {UF[uf]}: partido, presença em votações nominais e cota parlamentar, em ordem alfabética.", u, body, faqs=fa, crumbs=[("Representantes", "/representantes/"), (UF[uf], u)]), familia="paginas", lastmod=col); urls.append(u); hubs.append(u)
    # =================== HUBS: nacional e por UF ===================
    def hubs_familia(raiz, nome_fam, h1, snippet, descr, titulo_uf, h1_uf, snip_uf, desc_uf, faqs, faqs_uf, fonte, linkfn, extra_cols=None, hub_uf_tem_pagina=True):
        for uf, L in por_uf.items():
            u = f"{raiz}{uf.lower()}/"; rows = [[f'<a href="{raiz}{uf.lower()}/{SL[c]}/">{E(M[c]["n"])}</a>', num(int(POP[c]))] for c in L]
            body = (f'<section class="blk"><h1>{h1_uf(uf)}</h1><p class="snippet">{snip_uf(uf, len(L))}</p>' + S.table(["Município", "Habitantes (Censo 2022)"], rows, "Em ordem alfabética; não é ranking") +
                    f'<p>Veja também <a href="{raiz}">todas as páginas desta série</a>, os <a href="/municipios/{uf.lower()}/">municípios {nm_uf(uf)}</a> e os <a href="/representantes/{uf.lower()}/">representantes {nm_uf(uf)} no Congresso</a>.</p><p class="src">{fonte} Compilação em {data_br(col)}.</p></section>')
            S.write(u, S.page(titulo_uf(uf) + f" | {site}", desc_uf(uf), u, body, faqs=faqs_uf(uf), crumbs=[(nome_fam, raiz), (UF[uf], u)]), familia="paginas", lastmod=col); urls.append(u); hubs.append(u)
        tp = sum(len(L) for L in por_uf.values())
        rows = [[f'<a href="{raiz}{uf.lower()}/">{UF[uf]}</a>', num(len(por_uf[uf]))] for uf in sorted(por_uf, key=lambda k: slugify(UF[k]))]
        body = (f'<section class="blk"><h1>{h1}</h1><p class="snippet">{snippet(tp)}</p>' + S.table(["Estado", "Municípios"], rows, "Em ordem alfabética") +
                f'<p class="src">{fonte} Compilação em {data_br(col)}. Veja a <a href="/municipios/metodologia/">metodologia</a>.</p></section>')
        S.write(raiz, S.page(f"{nome_fam}: páginas de todos os municípios do Brasil | {site}", descr, raiz, body, faqs=faqs, crumbs=[(nome_fam, raiz)]), familia="paginas", lastmod=col); urls.append(raiz); hubs.append(raiz)
    cm = lambda *x: list(x)
    hubs_familia("/prefeitura/", "Prefeituras", "Prefeituras do Brasil: orçamento, receitas e despesas", lambda n: f"Uma página para cada uma das <strong>{num(n)} prefeituras</strong> do país, com receitas, despesas por função, dependência de repasses e emendas recebidas, a partir das contas que cada prefeitura enviou ao Tesouro Nacional.",
                 "Orçamento, receitas, despesas por função e emendas recebidas de todas as prefeituras do Brasil, com dados do Tesouro Nacional e do IBGE.", lambda uf: f"Prefeituras {nm_uf(uf)}: orçamento e despesas",
                 lambda uf: f"Prefeituras {nm_uf(uf)}: orçamento, receitas e despesas", lambda uf, n: f"As <strong>{num(n)} prefeituras</strong> {nm_uf(uf)} com receitas, despesas e emendas recebidas, a partir das contas declaradas ao Tesouro Nacional.",
                 lambda uf: f"Receitas, despesas por função e emendas recebidas das {len(por_uf[uf])} prefeituras {nm_uf(uf)}, com dados do Tesouro Nacional.",
                 [("O que há em cada página de prefeitura?", "Receitas e despesas dos dois últimos exercícios declarados, despesa por função, dependência de transferências, emendas recebidas e ferramentas oficiais de fiscalização."), ("De onde vêm os dados?", "Da Declaração de Contas Anuais enviada ao Tesouro Nacional (SICONFI), do IBGE e do Portal da Transparência."), ("As páginas classificam prefeituras?", "Não. Os números descrevem cada município, sem ranking."),
                  ("Por que algumas prefeituras não têm valores?", "Porque a declaração anual não consta completa na base do Tesouro compilada pelo Estrato."), ("Os valores estão corrigidos pela inflação?", "Não, são nominais."), ("Como corrigir um dado?", 'Pela página de <a href="/correcoes/">correções</a>; a fonte primária é sempre o SICONFI.')],
                 lambda uf: [(f"Quantas prefeituras {PREP[uf]} {UF[uf]} estão no Estrato?", f"{num(len(por_uf[uf]))}, todos os municípios {nm_uf(uf)}."), ("A lista é um ranking?", "Não, é alfabética."), ("De onde vêm os números?", "Das contas anuais declaradas ao Tesouro Nacional e do Censo 2022."), ("O que é despesa empenhada?", "É o valor reservado no orçamento para um gasto, antes da liquidação e do pagamento."), ("Os valores são atuais?", "São do último exercício declarado e atualizados uma vez por mês."), ("Posso baixar os dados?", "Sim, em /dados/financas-entes.csv.")],
                 f"Fontes: {FONTE_T} e {FONTE_I}.", None)
    hubs_familia("/verbas-federais/", "Verbas federais", "Emendas e verbas federais em cada município", lambda n: f"Quanto cada um dos <strong>{num(n)} municípios</strong> recebeu de emendas parlamentares, por ano e por autor, e quanto a prefeitura declarou de transferências correntes, com dados do Portal da Transparência e do Tesouro Nacional.",
                 "Emendas parlamentares e transferências federais por ano em todos os municípios do Brasil, com autores e fontes oficiais.", lambda uf: f"Emendas e verbas federais {nm_uf(uf)} por município",
                 lambda uf: f"Emendas e verbas federais nos municípios {nm_uf(uf)}", lambda uf, n: f"Páginas de emendas parlamentares e transferências federais dos <strong>{num(n)} municípios</strong> {nm_uf(uf)}, por ano e por autor.",
                 lambda uf: f"Quanto cada município {nm_uf(uf)} recebeu de emendas e de transferências federais por ano, com autores e fontes oficiais.",
                 [("O que mostram estas páginas?", "Emendas parlamentares pagas por ano a favorecidos sediados no município, os autores e as transferências correntes declaradas pela prefeitura."), ("Emenda e FPM são a mesma coisa?", "Não. O FPM é transferência constitucional; a emenda é indicada por parlamentares no Orçamento."), ("De onde vêm os dados?", "Do Portal da Transparência (CGU) e do Tesouro Nacional."), ("O valor é da prefeitura?", "Nem sempre: o favorecido pode ser uma entidade, um fundo ou um órgão sediado no município."), ("Há ranking de quem recebe mais?", "Não. As listas são alfabéticas."), ("Desde quando vão os dados?", "Emendas pagas desde 2023.")],
                 lambda uf: [(f"Quais municípios {PREP[uf]} {UF[uf]} aparecem?", f"Os {num(len(por_uf[uf]))} municípios {nm_uf(uf)}, mesmo os sem emendas na base."), ("A lista é ranking?", "Não, é alfabética."), ("De onde vêm os dados?", "Do Portal da Transparência e do Tesouro Nacional."), ("O que é emenda parlamentar?", "É a indicação de deputados e senadores para destinar parte do Orçamento da União."), ("Os valores são nominais?", "Sim, sem correção pela inflação."), ("Onde ver por autor?", 'No painel de <a href="/emendas/">emendas</a>.')],
                 f"Fontes: {FONTE_EM} e {FONTE_T}.", None)
    hubs_familia("/eleitorado/", "Eleitorado", "Eleições em cada município: eleitorado, zonas e locais de votação", lambda n: f"Perfil do eleitorado de <strong>{num(n)} municípios</strong>: eleitores por faixa etária e escolaridade, zonas eleitorais, locais de votação e seções, com dados abertos do TSE. Sem pesquisas eleitorais e sem conteúdo de campanha.",
                 "Perfil do eleitorado, zonas eleitorais e locais de votação de todos os municípios do Brasil, com dados abertos do TSE.", lambda uf: f"Eleitorado {nm_uf(uf)} por município",
                 lambda uf: f"Eleitorado e locais de votação nos municípios {nm_uf(uf)}", lambda uf, n: f"Perfil do eleitorado, zonas e locais de votação dos <strong>{num(n)} municípios</strong> {nm_uf(uf)}, com dados abertos do TSE.",
                 lambda uf: f"Eleitores, zonas eleitorais e locais de votação dos municípios {nm_uf(uf)}, com dados abertos do TSE.",
                 [("O que mostram estas páginas?", "Total de eleitores aptos, faixa etária, escolaridade, biometria, zonas eleitorais e locais de votação de cada município."), ("De onde vêm os dados?", "Dos dados abertos do TSE: perfil do eleitorado atual e locais de votação de 2024."), ("Há dados individuais?", "Não. Só totais agregados, sem identificar eleitores."), ("O Estrato publica pesquisas eleitorais?", "Não."), ("Como descobrir meu local de votação?", "No aplicativo e-Título ou no site do TSE, com o número do título."), ("Com que frequência atualiza?", "Uma vez por mês.")],
                 lambda uf: [(f"Quantos eleitores {PREP[uf]} {UF[uf]} há?", f"Veja a soma nas páginas de cada município, em ordem alfabética."), ("A lista é ranking?", "Não, é alfabética."), ("De onde vêm os dados?", "Dos dados abertos do TSE."), ("O que são zonas eleitorais?", "São divisões da Justiça Eleitoral que agrupam seções de votação."), ("Há dados de candidatos?", "Não nesta série."), ("Os dados identificam eleitores?", "Não, são totais agregados.")],
                 f"Fonte: {FONTE_TSE}.", None)
    hubs_familia("/perguntas/local/", "Perguntas locais", "Perguntas e respostas sobre cada município", lambda n: f"Respostas diretas e com dados oficiais sobre <strong>{num(n)} municípios</strong>: quanto recebem do governo federal, quem envia recursos, quanto gastam, quantos eleitores têm e quem os representa no Congresso.",
                 "Perguntas e respostas sobre todos os municípios do Brasil: verbas federais, orçamento, eleitores e representantes, com fontes oficiais.", lambda uf: f"Perguntas sobre municípios {nm_uf(uf)}",
                 lambda uf: f"Perguntas e respostas sobre municípios {nm_uf(uf)}", lambda uf, n: f"Perguntas e respostas com dados oficiais sobre os <strong>{num(n)} municípios</strong> {nm_uf(uf)}.",
                 lambda uf: f"Quanto recebe, quem manda dinheiro e quem representa cada município {nm_uf(uf)}: respostas com dados oficiais.",
                 [("Que perguntas são respondidas?", "Quanto o município recebe do governo federal, quem manda dinheiro, qual o orçamento, quantos habitantes e eleitores tem e quem o representa no Congresso."), ("De onde vêm as respostas?", "Do Tesouro Nacional, do IBGE, do Portal da Transparência, do TSE, da Câmara e do Senado."), ("As respostas são opinião?", "Não. São números oficiais com link para a página de dados."), ("Há ranking?", "Não."), ("Os dados são atuais?", "São atualizados uma vez por mês."), ("Posso sugerir uma pergunta?", 'Sim, pela página de <a href="/contato/">contato</a>.')],
                 lambda uf: [(f"Quantos municípios {PREP[uf]} {UF[uf]} têm página?", f"{num(len(por_uf[uf]))}."), ("A lista é ranking?", "Não, é alfabética."), ("De onde vêm os dados?", "De fontes oficiais, citadas em cada página."), ("As respostas mudam?", "Sim, quando os dados oficiais são atualizados."), ("Posso copiar os dados?", 'Sim, veja os <a href="/dados/">dados abertos</a>.'), ("E municípios sem dados?", "A resposta informa que o dado não consta na base.")],
                 f"Fontes: {FONTE_T}, {FONTE_I}, {FONTE_EM}, {FONTE_TSE}.", None)
    # hub nacional de representantes
    rows = [[f'<a href="/representantes/{uf.lower()}/">{UF[uf]}</a>', num(len(deps_uf[uf])), num(len(sens_uf[uf]))] for uf in sorted(UF, key=lambda k: slugify(UF[k]))]
    body = ('<section class="blk"><h1>Quem representa seu estado e seu município no Congresso</h1><p class="snippet">Deputados federais e senadores de cada estado, com partido, presença em votações nominais e cota parlamentar, e uma página para cada município com os parlamentares naturais da cidade e os autores de emendas pagas a ela.</p>'
            + S.table(["Estado", "Deputados federais", "Senadores"], rows, "Em ordem alfabética") + f'<p class="src">Fontes oficiais: Câmara dos Deputados, Senado Federal e {FONTE_EM}. Compilação em {data_br(col)}.</p></section>')
    fa = [("Quem representa meu município no Congresso?", "Todos os deputados federais e senadores do seu estado; a eleição é estadual."), ("Quantos senadores cada estado elege?", "Três."), ("Os deputados têm distritos?", "Não. O Brasil não adota o voto distrital para deputado federal."), ("A lista é um ranking?", "Não, é alfabética."), ("De onde vêm os dados?", "Dos dados abertos da Câmara e do Senado."), ("O que é cota parlamentar?", 'Verba mensal para despesas do mandato. Veja o <a href="/cota/">painel da cota</a>.')]
    S.write("/representantes/", S.page(f"Quem representa seu estado e município no Congresso | {site}", "Deputados federais e senadores de cada estado, presença, cota parlamentar e páginas por município com parlamentares naturais e autores de emendas.", "/representantes/", body, faqs=fa, crumbs=[("Representantes", "/representantes/")]), familia="paginas", lastmod=col); urls.append("/representantes/"); hubs.append("/representantes/")
    # =================== BLOCO EXTRA DOS ESTADOS (/estados/<uf>/) ===================
    S.estado_extra = {}
    from . import bairros as _bai
    bu = {M[b["m"]]["uf"] for b in _bai.carregar(S)["b"] if b["m"] in M}
    est = {k: v for k, v in m["UFS"].items()}
    tot_el = collections.Counter(); tot_loc = collections.Counter()
    for c, (x, lo) in TS.items():
        tot_el[M[c]["uf"]] += x["tot"]
        if lo: tot_loc[M[c]["uf"]] += lo["l"]
    for uf in UF:
        h = ""; fq = []
        L = por_uf.get(uf, []); ent = est.get(uf)
        if ent:
            a, d = ult(ent[1])
            if a and d.get("rec"):
                h += f'<h2>Orçamento do estado</h2><p>O governo {PREP[uf]} {E(UF[uf])} declarou {brl0(d["rec"])} em receitas e {brl0(d["desp"]) if d.get("desp") else "—"} em despesas empenhadas em {a}. Detalhes por função em <a href="/financas/{uf.lower()}/">finanças {nm_uf(uf)}</a>.</p>'
                fq.append((f"Qual o orçamento {PREP[uf]} {UF[uf]}?", f"Em {a}, o governo estadual declarou {brl(d['rec'])} em receitas ao Tesouro Nacional."))
        if tot_el.get(uf):
            h += f'<h2>Eleições {nm_uf(uf)}</h2><p>O eleitorado {PREP[uf]} {E(UF[uf])} soma {num(tot_el[uf])} eleitores aptos em {num(len(L))} municípios, com {num(tot_loc.get(uf, 0))} locais de votação nas eleições de 2024. O perfil de cada município está em <a href="/eleitorado/{uf.lower()}/">eleitorado {nm_uf(uf)}</a>.</p>'
            fq.append((f"Quantos eleitores {PREP[uf]} {UF[uf]} há?", f"{num(tot_el[uf])} eleitores aptos, segundo o TSE (base de {hoje})."))
        h += (f'<h2>Prefeituras, verbas e representantes</h2><ul><li><a href="/municipios/{uf.lower()}/">Municípios {nm_uf(uf)}</a>: população, receitas e despesas</li><li><a href="/prefeitura/{uf.lower()}/">Prefeituras {nm_uf(uf)}</a>: orçamento de cada uma</li>'
              f'<li><a href="/verbas-federais/{uf.lower()}/">Emendas e verbas federais por município</a></li><li><a href="/representantes/{uf.lower()}/">Quem representa {nm_uf(uf)} no Congresso</a></li>' + (f'<li><a href="/bairros/{uf.lower()}/">Bairros {nm_uf(uf)}</a> do Censo 2022</li>' if uf in bu else "") + '</ul>')
        h += f'<h2>Governador e secretarias</h2><p>Os nomes do governador e dos secretários {PREP[uf]} {E(UF[uf])} não são exibidos nesta etapa: o Estrato só publica dados de ocupantes de cargos eletivos depois do fim do período eleitoral, em 26/10/2026, e a lista de secretarias ainda depende de fonte oficial aberta e padronizada, que não foi verificada.</p>'
        S.estado_extra[uf] = (h, fq)
    return {"urls": urls}
