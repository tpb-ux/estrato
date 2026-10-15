"""Financas publicas de estados, Uniao e municipios (SICONFI/Tesouro, DCA) com dados do IBGE (Censo 2022 e PIB) e emendas federais recebidas.
Dados: data/siconfi/siconfi.json.gz (tools/datasets_siconfi.py), data/ibge/ibge.json.gz (tools/datasets_ibge.py), data/emendas.
Paginas: /financas/ (hub), /financas/<uf>/ e /financas/uniao/ (familia `estados`), /municipios/ (hub), /municipios/<uf>/ (hub), /municipios/<uf>/<slug>/ (familia `municipios`), /municipios/metodologia/.
Hubs indexaveis; paginas de cada ente em noindex ate a onda propria. Listas em ordem alfabetica, sem ranking, sem patrimonio e sem dados de campanha."""
import collections, csv, gzip, json, statistics
from core.site import E, slugify
from .dados import UF, PREP, brl, brl0, data_br, num, pct

COD = {"AC": 12, "AL": 27, "AP": 16, "AM": 13, "BA": 29, "CE": 23, "DF": 53, "ES": 32, "GO": 52, "MA": 21, "MT": 51, "MS": 50, "MG": 31, "PA": 15, "PB": 25, "PR": 41, "PE": 26, "PI": 22, "RJ": 33, "RN": 24, "RS": 43, "RO": 11, "RR": 14, "SC": 42, "SP": 35, "SE": 28, "TO": 17}
POR_COD = {str(v): k for k, v in COD.items()}
_C = {}
FONTE_T = '<a href="https://siconfi.tesouro.gov.br/" target="_blank" rel="noopener">SICONFI, do Tesouro Nacional</a>'
FONTE_I = '<a href="https://sidra.ibge.gov.br/" target="_blank" rel="noopener">IBGE (SIDRA)</a>'


def carregar(S):
    if "d" in _C: return _C["d"]
    f = S.ROOT / "data/siconfi/siconfi.json.gz"; g = S.ROOT / "data/ibge/ibge.json.gz"
    sc = json.loads(gzip.decompress(f.read_bytes())) if f.exists() else {"entes": {}, "anos": [], "gerado": ""}
    ib = json.loads(gzip.decompress(g.read_bytes())) if g.exists() else {"m": {}, "uf": {}}
    _C["d"] = (sc, ib); return _C["d"]


def ult(e):
    """(ano, dados) mais recente com receita e despesa; senao o mais recente com algo."""
    an = e["an"]
    for y in sorted(an, reverse=True):
        if "rec" in an[y] and "desp" in an[y]: return int(y), an[y]
    for y in sorted(an, reverse=True):
        if an[y]: return int(y), an[y]
    return None, {}


def ant(e, ano):
    for y in sorted(e["an"], reverse=True):
        if int(y) < ano and "rec" in e["an"][y]: return int(y), e["an"][y]
    return None, {}


def var(a, b):
    if not a or not b: return ""
    v = 100 * (a - b) / b
    return ("+" if v >= 0 else "−") + f"{abs(v):.1f}".replace(".", ",") + "%"


def n1(v): return f"{v:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pc(v): return "R$ " + f"{v:,.0f}".replace(",", ".")


def tab_rec(S, d, d0, a, a0):
    linhas = [("Receita total (exceto intraorçamentárias)", "rec"), ("Receitas correntes", "rc"), ("Impostos", "imp"), ("Transferências correntes", "tc"), ("Receitas de capital", "rk")]
    rows = []
    for n, k in linhas:
        if k not in d: continue
        rows.append([n, brl0(d[k]), pct(d[k], d["rec"]) if k != "rec" and d.get("rec") else "100%", (brl0(d0[k]) if k in d0 else "—"), var(d[k], d0.get(k)) or "—"])
    return S.table(["Receita", f"{a}", "% do total", f"{a0}" if a0 else "Ano anterior", "Variação nominal"], rows, "Receitas brutas realizadas, valores declarados ao Tesouro")


def tab_fun(S, d, d0, topn=8):
    fn = d.get("fun") or {}; tot = d.get("desp") or sum(v[1] for v in fn.values())
    L = sorted(fn.items(), key=lambda x: -x[1][1])[:topn]
    rows = [[E(v[0]), brl0(v[1]), pct(v[1], tot), var(v[1], (d0.get("fun") or {}).get(c, [0, 0])[1]) or "—"] for c, v in L]
    return S.table(["Função", "Empenhado", "% da despesa", "Variação nominal"], rows, f"Despesas empenhadas por função (as {len(L)} maiores)") if rows else ""


def bloco_ente(S, e, nome, pop, ib, extra_med=None, uniao=False):
    """Retorna (html, dados) com receitas, despesas e indicadores de um ente."""
    a, d = ult(e)
    if not a: return "", None
    a0, d0 = ant(e, a)
    h = ""
    if "rec" in d: h += "<h2>Receitas</h2>" + tab_rec(S, d, d0, a, a0)
    if d.get("fun") or "desp" in d: h += "<h2>Despesas por função</h2>" + tab_fun(S, d, d0)
    return h, (a, d, a0, d0)


def base(S):
    sc, ib = carregar(S)
    M = {}; ufs = {}; uniao = None
    for c, e in sc["entes"].items():
        if e["e"] == "M": M[c] = e
        elif e["e"] in ("E", "D"): ufs[POR_COD.get(c)] = (c, e)
        elif e["e"] == "U": uniao = (c, e)
    return sc, ib, M, ufs, uniao


def _fl(vals):
    return statistics.median(vals) if vals else None


def build(S):
    sc, ib, M, UFS, UN = base(S)
    if not M: return {"urls": []}
    try:
        from . import emendas as _em
        ED, _meta = _em.carregar(S)
    except Exception: ED = {"mun": {}}
    col = sc.get("gerado") or ""; urls = []; site = S.CFG["site_name"]
    por_uf = collections.defaultdict(list)
    for c, e in M.items():
        if e["uf"] in UF: por_uf[e["uf"]].append(c)
    slug = {}
    for uf, L in por_uf.items():
        L.sort(key=lambda c: (slugify(M[c]["n"]), c)); usados = set()
        for c in L:
            s = slugify(M[c]["n"]) or c
            if s in usados: s = f"{s}-{c}"
            usados.add(s); slug[c] = s
    URL = {c: f"/municipios/{M[c]['uf'].lower()}/{slug[c]}/" for c in slug}
    em_idx = {(k.split("|")[0], slugify(k.split("|", 1)[1])): k for k in ED["mun"]}
    def emd(c):
        k = em_idx.get((M[c]["uf"], slugify(M[c]["n"])))
        if not k: return None
        m = ED["mun"][k]; u = f"/emendas/municipios/{M[c]['uf'].lower()}/{slugify(k.split('|', 1)[1])}/"
        return sum(m["anos"].values()), len(m["autores"]), (u if u in S.urls else None)
    POP = {c: (ib["m"].get(c, {}).get("pop") or M[c]["pop"] or 0) for c in M}
    UD = {c: ult(M[c]) for c in M}
    med = {}
    for uf, L in por_uf.items():
        r = [UD[c][1]["rec"] / POP[c] for c in L if UD[c][1].get("rec") and POP[c]]; d_ = [UD[c][1]["desp"] / POP[c] for c in L if UD[c][1].get("desp") and POP[c]]
        med[uf] = (_fl(r), _fl(d_))
    cobertos = sum(1 for c in M if UD[c][0])
    fams = "municipios"
    S.mun = {"sc": sc, "ib": ib, "M": M, "URL": URL, "slug": slug, "por_uf": por_uf, "POP": POP, "UD": UD, "med": med, "col": col, "ED": ED, "UFS": UFS, "UN": UN, "em_idx": em_idx}  # usado por local.py, bairros.py, eleitorado
    try: COM_BAIRROS = {b["m"] for b in json.loads(gzip.decompress((S.ROOT / "data/bairros/bairros.json.gz").read_bytes()))["b"]}  # municípios com página de bairros (hub existe)
    except OSError: COM_BAIRROS = set()
    # ---------- paginas de municipios ----------
    for uf, L in por_uf.items():
        for i, c in enumerate(L):
            e = M[c]; nome = e["n"]; u = URL[c]; pop = POP[c]; a, d = UD[c]; ibm = ib["m"].get(c, {})
            h, pack = bloco_ente(S, e, nome, pop, ibm)
            body = f'<article class="post"><h1>{E(nome)} ({uf}): receitas, despesas e indicadores do município</h1>'
            fa = []
            if a and d.get("rec") and d.get("desp"):
                body += (f'<p class="snippet"><strong>{E(nome)} ({uf})</strong> tinha <strong>{num(int(pop))} habitantes</strong> no Censo 2022 e registrou <strong>{brl0(d["rec"])}</strong> em receitas e '
                         f'<strong>{brl0(d["desp"])}</strong> em despesas empenhadas em {a}, segundo as contas anuais enviadas ao Tesouro Nacional.</p>')
                rpc, dpc = d["rec"] / pop if pop else 0, d["desp"] / pop if pop else 0; mr, md = med[uf]
                txt = f'Por habitante, a receita foi de {fmt_pc(rpc)} e a despesa empenhada, de {fmt_pc(dpc)}.' if pop else ""
                if mr: txt += f' A mediana dos municípios {PREP[uf]} {UF[uf]} é de {fmt_pc(mr)} de receita por habitante.'
                if d.get("tc") and d.get("rec"): txt += f' As transferências correntes, em geral de União e estado, somaram {pct(d["tc"], d["rec"])} da receita'
                if d.get("imp") is not None and d.get("rec"): txt += f' e os impostos arrecadados pelo próprio município, {pct(d["imp"], d["rec"])}.'
                elif d.get("tc"): txt += "."
                fn = d.get("fun") or {}
                if fn.get("10") and fn.get("12") and d["desp"]: txt += f' Saúde ficou com {pct(fn["10"][1], d["desp"])} da despesa e educação, com {pct(fn["12"][1], d["desp"])}.'
                body += f"<p>{txt}</p>"
            else:
                body += f'<p class="snippet"><strong>{E(nome)} ({uf})</strong> tinha <strong>{num(int(pop))} habitantes</strong> no Censo 2022. As contas anuais do município não constam com receitas e despesas completas na base do Tesouro Nacional na compilação do Estrato.</p>'
            body += h
            ind = [["Código IBGE", c], ["População (Censo 2022)", num(int(pop))]]
            if ibm.get("area"): ind.append(["Área", n1(ibm["area"]) + " km²"])
            if ibm.get("dens"): ind.append(["Densidade demográfica", n1(ibm["dens"]) + " hab./km²"])
            if ibm.get("pib"): ind.append([f'PIB a preços correntes ({ib.get("pib_ano")})', brl0(ibm["pib"])]); ind.append(["PIB por habitante", fmt_pc(ibm["pib"] / pop) if pop else "—"])
            if e["cap"]: ind.append(["Capital estadual", "Sim"])
            body += "<h2>População e economia</h2>" + S.table(["Indicador", "Valor"], ind)
            ee = emd(c)
            if ee:
                body += f'<h2>Emendas parlamentares federais</h2><p>Órgãos e entidades sediados em {E(nome)} receberam {brl(ee[0])} em pagamentos de emendas ao Orçamento da União desde 2023, de {num(ee[1])} autores.' + (f' Veja os detalhes em <a href="{ee[2]}">emendas parlamentares em {E(nome)}</a>.' if ee[2] else "") + "</p>"
            else:
                body += f'<h2>Emendas parlamentares federais</h2><p>Não há pagamentos de emendas parlamentares a favorecidos identificados com sede em {E(nome)} na compilação do Estrato (desde 2023). Veja o <a href="/emendas/municipios/{uf.lower()}/">painel de emendas {PREP[uf]} {UF[uf]}</a>.</p>'
            sl_ = URL[c].rstrip("/").rsplit("/", 1)[1]; ul_ = uf.lower()
            irm = [(f"/prefeitura/{ul_}/{sl_}/", f"Orçamento da prefeitura de {nome}"), (f"/verbas-federais/{ul_}/{sl_}/", f"Emendas e verbas federais em {nome}"),
                   (f"/representantes/{ul_}/{sl_}/", f"Quem representa {nome} no Congresso"), (f"/eleitorado/{ul_}/{sl_}/", f"Eleitorado e locais de votação em {nome}"),
                   (f"/perguntas/local/{ul_}/{sl_}/", f"Perguntas e respostas sobre {nome}")]
            if c in COM_BAIRROS: irm.append((f"/bairros/{ul_}/{sl_}/", f"Bairros de {nome}"))
            body += f'<h2>Mais sobre {E(nome)}</h2><ul>' + "".join(f'<li><a href="{a_}">{E(t_)}</a></li>' for a_, t_ in irm) + '</ul>'
            viz = L[max(0, i - 5):i] + L[i + 1:i + 6]
            body += f'<h2>Outros municípios {PREP[uf]} {UF[uf]}</h2><p>Vizinhos na lista alfabética: ' + ", ".join(f'<a href="{URL[x]}">{E(M[x]["n"])}</a>' for x in viz) + f'. Veja todos em <a href="/municipios/{uf.lower()}/">municípios {PREP[uf]} {UF[uf]}</a>, os <a href="/financas/{uf.lower()}/">dados do estado</a> e os <a href="/deputados/uf/{uf.lower()}/">deputados federais eleitos</a>.</p>'
            body += f'<p class="src">Fontes oficiais: {FONTE_T} (Declaração de Contas Anuais, anexos I-C e I-E, exercícios 2023 e 2024) e {FONTE_I} (Censo 2022 e PIB dos municípios). Compilação em {data_br(col)}. Valores nominais, como declarados pelo município. Veja a <a href="/municipios/metodologia/">metodologia</a>.</p></article>'
            if a and d.get("rec"):
                fa = [(f"Quantos habitantes tem {nome}?", f"{num(int(pop))} habitantes, segundo o Censo 2022 do IBGE."),
                      (f"Quanto {nome} arrecadou em {a}?", f"As receitas brutas realizadas, exceto intraorçamentárias, somaram {brl(d['rec'])}, segundo a declaração enviada ao Tesouro."),
                      ("De onde vem a receita do município?", (f"Transferências correntes somaram {pct(d['tc'], d['rec'])} e impostos, {pct(d['imp'], d['rec'])} da receita." if d.get("tc") and d.get("imp") is not None else "A base do Tesouro traz receitas correntes e de capital; veja a tabela de receitas acima.")),
                      ("Quanto foi gasto em saúde e em educação?", (f"Em {a}, saúde somou {brl0(d['fun']['10'][1])} e educação, {brl0(d['fun']['12'][1])} em despesas empenhadas." if d.get("fun", {}).get("10") and d.get("fun", {}).get("12") else "A tabela de despesas por função mostra as áreas com valor declarado.")),
                      ("O que significa despesa empenhada?", "É o valor que a prefeitura reservou no orçamento para um gasto, antes de a entrega ser liquidada e de o pagamento ser feito."),
                      ("De onde vêm os dados desta página?", "Do Tesouro Nacional (SICONFI) e do IBGE, atualizados uma vez por mês. O arquivo completo está em /dados/financas-entes.csv.")]
            else:
                fa = [(f"Quantos habitantes tem {nome}?", f"{num(int(pop))} habitantes, segundo o Censo 2022 do IBGE."), ("Por que não há receitas e despesas?", "O Tesouro Nacional não tem, na compilação do Estrato, a declaração anual completa do município."),
                      ("De onde vêm os dados desta página?", "Do Tesouro Nacional (SICONFI) e do IBGE.")]
            ld = {"@type": "City", "@id": S.BASE + u + "#city", "name": nome, "url": S.BASE + u, "containedInPlace": {"@type": "AdministrativeArea", "name": UF[uf]}, "identifier": c}
            desc = f"{nome} ({uf}): {num(int(pop))} habitantes" + (f", receita de {brl0(d['rec'])} e despesa de {brl0(d['desp'])} em {a}. Dados do Tesouro e do IBGE." if a and d.get("rec") and d.get("desp") else ". Dados do IBGE e do Tesouro Nacional.")
            S.write(u, S.page(f"Indicadores de {nome} ({uf}): população, PIB e área | {site}", desc, u, body, faqs=fa, crumbs=[("Municípios", "/municipios/"), (UF[uf], f"/municipios/{uf.lower()}/"), (nome, u)], jsonld=ld), familia=fams, lastmod=col); urls.append(u)
    # ---------- hubs por UF (municipios) ----------
    totpop = {uf: sum(POP[c] for c in L) for uf, L in por_uf.items()}
    for uf, L in por_uf.items():
        u = f"/municipios/{uf.lower()}/"
        rows = [[f'<a href="{URL[c]}">{E(M[c]["n"])}</a>', num(int(POP[c])), brl0(UD[c][1]["rec"]) if UD[c][1].get("rec") else "—", brl0(UD[c][1]["desp"]) if UD[c][1].get("desp") else "—"] for c in L]
        com = sum(1 for c in L if UD[c][1].get("rec")); mr, md = med[uf]
        body = (f'<section class="blk"><h1>Municípios {PREP[uf]} {UF[uf]}: população, receitas e despesas</h1><p class="snippet">{UF[uf]} tem <strong>{num(len(L))} municípios</strong> e <strong>{num(int(totpop[uf]))} habitantes</strong> pelo Censo 2022. '
                f'{num(com)} deles têm receitas e despesas declaradas ao Tesouro Nacional' + (f'; a mediana de receita é de {fmt_pc(mr)} por habitante.' if mr else ".") + '</p>'
                + S.table(["Município", "Habitantes", "Receita", "Despesa empenhada"], rows, "Em ordem alfabética; não é ranking") +
                f'<p>Veja também os <a href="/financas/{uf.lower()}/">dados do estado {PREP[uf]} {UF[uf]}</a>, as <a href="/emendas/municipios/{uf.lower()}/">emendas por município</a> e os <a href="/deputados/uf/{uf.lower()}/">deputados federais {PREP[uf]} {UF[uf]}</a>.</p>'
                f'<p class="src">Fontes: {FONTE_T} e {FONTE_I}. Compilação em {data_br(col)}. <a href="/municipios/metodologia/">Metodologia</a>.</p></section>')
        fa = [(f"Quantos municípios tem {UF[uf]}?", f"{num(len(L))} municípios, segundo o IBGE."), (f"Quantos habitantes {PREP[uf]} {UF[uf]} vivem nos municípios listados?", f"{num(int(totpop[uf]))} pelo Censo 2022."),
              ("A lista é um ranking?", "Não. Os municípios aparecem em ordem alfabética, e os valores não medem a qualidade da gestão."), ("O que são receita e despesa empenhada?", "Receita é o que o município arrecadou ou recebeu no ano; despesa empenhada é o valor reservado no orçamento para pagar um gasto."),
              ("De onde vêm os valores?", "Da Declaração de Contas Anuais que cada município envia ao Tesouro Nacional, no SICONFI."), ("Faltam municípios na tabela de valores?", f"{num(len(L) - com)} municípios não têm receita e despesa completas na base do Tesouro na compilação de {data_br(col)}." if len(L) > com else "Todos os municípios têm valores declarados."),
              ("Posso baixar os dados?", "Sim, em /dados/financas-entes.csv, com licença aberta.")]
        S.write(u, S.page(f"Municípios {PREP[uf]} {UF[uf]}: população, receitas e despesas | {site}", f"Todos os {num(len(L))} municípios {PREP[uf]} {UF[uf]} com população do Censo 2022, receitas e despesas declaradas ao Tesouro Nacional.", u, body, faqs=fa,
                            crumbs=[("Municípios", "/municipios/"), (UF[uf], u)], jsonld={"@type": "ItemList", "name": f"Municípios {PREP[uf]} {UF[uf]}", "itemListElement": [{"@type": "ListItem", "position": k + 1, "url": S.BASE + URL[c], "name": M[c]["n"]} for k, c in enumerate(L[:50])]}), familia="paginas", lastmod=col); urls.append(u)
    # ---------- hub /municipios/ ----------
    tot = sum(len(L) for L in por_uf.values())
    rows = [[f'<a href="/municipios/{uf.lower()}/">{UF[uf]}</a>', num(len(por_uf[uf])), num(int(totpop[uf]))] for uf in sorted(por_uf, key=lambda k: slugify(UF[k]))]
    body = (f'<section class="blk"><h1>Municípios do Brasil: população, receitas e despesas</h1><p class="snippet">Dados oficiais de <strong>{num(tot)} municípios</strong>: população do Censo 2022, PIB, receitas e despesas declaradas ao Tesouro Nacional e emendas federais recebidas. {num(cobertos)} municípios têm contas declaradas na base.</p>'
            + S.table(["Estado", "Municípios", "Habitantes (Censo 2022)"], rows, "Em ordem alfabética") +
            '<p>Cada município tem uma página própria com tabelas de receitas e despesas por função, indicadores e links para emendas e bancada do estado. Veja a <a href="/municipios/metodologia/">metodologia</a> e os <a href="/financas/">dados dos estados e da União</a>.</p>'
            f'<p class="src">Fontes: {FONTE_T} e {FONTE_I}. Compilação em {data_br(col)}.</p></section>')
    fa = [("Quais municípios estão no Estrato?", f"Os {num(tot)} municípios brasileiros, agrupados por estado."), ("De onde vêm os números?", "Da Declaração de Contas Anuais enviada pelos municípios ao Tesouro Nacional e do Censo 2022 e das contas regionais do IBGE."),
          ("As páginas comparam ou classificam prefeituras?", "Não. As listas são alfabéticas e as páginas descrevem apenas os números de cada município."), ("Os valores estão corrigidos pela inflação?", "Não. São valores nominais, como declarados."),
          ("Com que frequência os dados mudam?", "O Tesouro e o IBGE publicam por ano; o Estrato atualiza a coleta uma vez por mês."), ("Há dados de prefeitos ou candidatos?", "Não nesta etapa. As páginas trazem apenas dados fiscais, demográficos e de emendas federais."),
          ("Onde baixo os dados?", "Em /dados/financas-entes.csv.")]
    S.write("/municipios/", S.page(f"Municípios do Brasil: população, receitas e despesas | {site}", f"{num(tot)} municípios com população do Censo 2022, PIB, receitas e despesas declaradas ao Tesouro Nacional e emendas federais recebidas.", "/municipios/", body, faqs=fa, crumbs=[("Municípios", "/municipios/")]), familia="paginas", lastmod=col); urls.append("/municipios/")
    # ---------- estados e Uniao ----------
    deps = collections.defaultdict(list); sens = collections.defaultdict(list)
    for d_ in S.parl["deps"]: deps[d_["uf"]].append(d_)
    for x in S.parl["sens"]: sens[x["uf"]].append(x)
    emuf = collections.defaultdict(float)
    for k, m in ED["mun"].items(): emuf[k.split("|")[0]] += sum(m["anos"].values())
    est_rows = []
    for uf in sorted(UF, key=lambda k: slugify(UF[k])):
        if uf not in UFS: continue
        c, e = UFS[uf]; a, d = ult(e); ibu = ib["uf"].get(c, {}); pop = ibu.get("pop") or e["pop"] or 0; u = f"/financas/{uf.lower()}/"
        h, pack = bloco_ente(S, e, UF[uf], pop, ibu); nm = UF[uf]
        body = f'<article class="post"><h1>{E(nm)}: receitas, despesas, bancada e indicadores do estado</h1>'
        if a and d.get("rec") and d.get("desp"):
            body += (f'<p class="snippet">O governo {PREP[uf]} <strong>{E(nm)}</strong> registrou <strong>{brl0(d["rec"])}</strong> em receitas e <strong>{brl0(d["desp"])}</strong> em despesas empenhadas em {a}, para uma população de {num(int(pop))} habitantes no Censo 2022. '
                     f'Por habitante, são {fmt_pc(d["rec"] / pop)} de receita e {fmt_pc(d["desp"] / pop)} de despesa.</p>')
        else: body += f'<p class="snippet">{E(nm)} tinha {num(int(pop))} habitantes no Censo 2022.</p>'
        body += h
        ind = [["Código IBGE", c], ["População (Censo 2022)", num(int(pop))]]
        if ibu.get("area"): ind.append(["Área", f'{ibu["area"]:,.0f} km²'.replace(",", ".")])
        if ibu.get("pib"): ind.append([f'PIB a preços correntes ({ib.get("pib_ano")})', brl0(ibu["pib"])])
        ind.append(["Municípios", num(len(por_uf[uf]))])
        if emuf.get(uf): ind.append(["Emendas federais pagas a favorecidos sediados no estado desde 2023 (municípios)", brl0(emuf[uf])])
        body += "<h2>População e economia</h2>" + S.table(["Indicador", "Valor"], ind)
        dd = sorted(deps[uf], key=lambda x: slugify(x["nome"])); pp = collections.Counter(x["partido"] for x in dd)
        body += f'<h2>Bancada federal</h2><p>{E(nm)} elege {len(dd)} deputados federais e {len(sens[uf])} senadores. Veja a lista completa em <a href="/deputados/uf/{uf.lower()}/">deputados federais {PREP[uf]} {E(nm)}</a>.</p>'
        body += S.table(["Partido", "Deputados federais"], [[f'<a href="/partidos/{slugify(p)}/">{E(p)}</a>', str(n)] for p, n in sorted(pp.items())], "Composição da bancada na Câmara, em ordem alfabética")
        if sens[uf]: body += "<p>Senadores: " + ", ".join(f'<a href="{x["url"]}">{E(x["nome"])}</a> ({E(x["partido"])})' for x in sorted(sens[uf], key=lambda x: slugify(x["nome"]))) + ".</p>"
        body += f'<h2>Municípios</h2><p>Os {num(len(por_uf[uf]))} municípios {PREP[uf]} {E(nm)} têm página própria com receitas, despesas e indicadores: <a href="/municipios/{uf.lower()}/">municípios {PREP[uf]} {E(nm)}</a>. Veja também as <a href="/emendas/municipios/{uf.lower()}/">emendas parlamentares por município</a> e as <a href="/estados/{uf.lower()}/">notícias {PREP[uf]} {E(nm)}</a>.</p>'
        body += f'<p class="src">Fontes oficiais: {FONTE_T} (DCA, anexos I-C e I-E), {FONTE_I} (Censo 2022 e PIB), Câmara e Senado (bancada). Compilação em {data_br(col)}. <a href="/municipios/metodologia/">Metodologia</a>.</p></article>'
        fa = [(f"Quanto o governo {PREP[uf]} {nm} arrecadou em {a}?", f"As receitas brutas realizadas somaram {brl(d['rec'])} (exceto intraorçamentárias)." if d.get("rec") else "O Tesouro não traz esse dado na compilação."),
              (f"Quantos habitantes tem {nm}?", f"{num(int(pop))}, segundo o Censo 2022."), (f"Quantos deputados e senadores {nm} elege?", f"{len(dd)} deputados federais e {len(sens[uf])} senadores."),
              ("O que significa despesa empenhada?", "É o valor reservado no orçamento para um gasto, antes da liquidação e do pagamento."), ("Os valores estão corrigidos pela inflação?", "Não, são valores nominais declarados ao Tesouro."), ("De onde vêm os dados?", "Do SICONFI (Tesouro Nacional), do IBGE, da Câmara e do Senado.")]
        S.write(u, S.page(f"{nm}: receitas, despesas, bancada e indicadores do estado | {site}", f"{nm}: {num(int(pop))} habitantes" + (f", receita de {brl0(d['rec'])} e despesa de {brl0(d['desp'])} em {a}." if d.get("rec") and d.get("desp") else ".") + " Bancada federal, municípios e emendas.", u, body, faqs=fa,
                            crumbs=[("Estados e União", "/financas/"), (nm, u)], jsonld={"@type": "AdministrativeArea", "name": nm, "url": S.BASE + u, "identifier": c}), familia="financas", lastmod=col); urls.append(u)
        est_rows.append([f'<a href="{u}">{E(nm)}</a>', num(int(pop)), brl0(d["rec"]) if d.get("rec") else "—", brl0(d["desp"]) if d.get("desp") else "—"])
    if UN:
        c, e = UN; a, d = ult(e); u = "/financas/uniao/"; h, pack = bloco_ente(S, e, "União", 0, {})
        body = f'<article class="post"><h1>União: receitas e despesas do governo federal</h1>'
        if a and d.get("rec"): body += f'<p class="snippet">A União registrou <strong>{brl0(d["rec"])}</strong> em receitas brutas realizadas' + (f' e <strong>{brl0(d["desp"])}</strong> em despesas empenhadas' if d.get("desp") else "") + f' em {a}, segundo a Declaração de Contas Anuais enviada ao Tesouro Nacional.</p>'
        else: body += "<p class=\"snippet\">A União declara suas contas anuais ao Tesouro Nacional por meio do SICONFI.</p>"
        body += h + f'<p>Veja como os recursos federais chegam aos estados e municípios em <a href="/emendas/">emendas parlamentares</a>, <a href="/executivo/">Poder Executivo</a> e <a href="/financas/">dados dos estados</a>.</p>'
        body += f'<p class="src">Fonte oficial: {FONTE_T} (DCA, anexos I-C e I-E). Compilação em {data_br(col)}. <a href="/municipios/metodologia/">Metodologia</a>.</p></article>'
        fa = [("Quanto a União arrecadou?", f"{brl(d['rec'])} em receitas brutas realizadas em {a}." if d.get("rec") else "O dado não consta na compilação."), ("O que é a DCA?", "A Declaração de Contas Anuais reúne os balanços que cada ente envia ao Tesouro Nacional."),
              ("Os valores estão corrigidos pela inflação?", "Não, são nominais."), ("O que é despesa empenhada?", "É o valor reservado no orçamento para um gasto, antes da liquidação e do pagamento."), ("Onde estão os dados dos estados?", "Em /financas/, com uma página por estado.")]
        S.write(u, S.page(f"União: receitas e despesas do governo federal | {site}", f"Receitas e despesas da União em {a}, declaradas ao Tesouro Nacional, por categoria e função de governo." if a else "Receitas e despesas da União declaradas ao Tesouro Nacional.", u, body, faqs=fa, crumbs=[("Estados e União", "/financas/"), ("União", u)]), familia="financas", lastmod=col); urls.append(u)
        est_rows.append([f'<a href="{u}">União</a>', "—", brl0(d["rec"]) if d.get("rec") else "—", brl0(d["desp"]) if d.get("desp") else "—"])
    body = ('<section class="blk"><h1>Estados e União: receitas, despesas e bancada</h1><p class="snippet">Dados oficiais dos 26 estados, do Distrito Federal e da União: receitas e despesas declaradas ao Tesouro Nacional, população e PIB do IBGE e bancada federal na Câmara e no Senado.</p>'
            + S.table(["Ente", "Habitantes", "Receita", "Despesa empenhada"], est_rows, "Em ordem alfabética; não é ranking") +
            '<p>Para os municípios de cada estado, veja <a href="/municipios/">municípios do Brasil</a>. A <a href="/municipios/metodologia/">metodologia</a> explica as fontes e os conceitos.</p>'
            f'<p class="src">Fontes: {FONTE_T} e {FONTE_I}. Compilação em {data_br(col)}.</p></section>')
    fa = [("Quais entes aparecem aqui?", "Os 26 estados, o Distrito Federal e a União."), ("A tabela é um ranking?", "Não. Os entes estão em ordem alfabética e os números não medem a qualidade da gestão."), ("De onde vêm as receitas e despesas?", "Da Declaração de Contas Anuais enviada ao Tesouro Nacional."),
          ("Por que a receita de um estado é maior que a de outro?", "Porque estados diferem em população, economia e transferências recebidas; a tabela só informa os valores."), ("Os valores são atuais?", f"São do último exercício declarado, compilado em {data_br(col)}. O Estrato atualiza a coleta uma vez por mês."), ("Onde baixo os dados?", "Em /dados/financas-entes.csv.")]
    S.write("/financas/", S.page(f"Estados e União: receitas, despesas e bancada | {site}", "Receitas e despesas dos estados, do DF e da União declaradas ao Tesouro Nacional, com população, PIB e bancada federal de cada estado.", "/financas/", body, faqs=fa, crumbs=[("Estados e União", "/financas/")]), familia="paginas", lastmod=col); urls.append("/financas/")
    # ---------- metodologia ----------
    body = ('<section class="blk"><h1>Metodologia: finanças de estados e municípios</h1><p class="snippet">Como o Estrato monta as páginas de estados, União e municípios: fontes, conceitos, limites e atualização.</p>'
            f'<h2>Fontes</h2><ul><li>Receitas e despesas: {FONTE_T}, Declaração de Contas Anuais (DCA), anexo I-C (receitas orçamentárias) e anexo I-E (despesas por função), exercícios {", ".join(str(a) for a in sc["anos"])}.</li>'
            f'<li>População, área e densidade: Censo 2022; PIB a preços correntes de {ib.get("pib_ano")}: {FONTE_I}.</li><li>Emendas federais: <a href="/emendas/metodologia/">metodologia de emendas</a>. Bancada: dados abertos da Câmara e do Senado.</li></ul>'
            '<h2>Conceitos</h2><ul><li><strong>Receita total</strong>: receitas brutas realizadas, exceto intraorçamentárias, sem deduções.</li><li><strong>Despesa empenhada</strong>: valor reservado no orçamento para um gasto; não é o mesmo que despesa paga.</li>'
            '<li><strong>Transferências correntes</strong>: recursos recebidos de outros entes, como fundos de participação; <strong>impostos</strong>: arrecadação própria.</li><li><strong>Variação nominal</strong>: diferença entre exercícios sem correção pela inflação.</li></ul>'
            '<h2>Limites</h2><p>Os valores são os declarados pelos próprios entes e podem ser retificados. Municípios que não enviaram a DCA aparecem só com dados do IBGE. As listas são alfabéticas e não classificam gestões. Dados de candidatos, prefeitos e patrimônio não fazem parte desta etapa.</p>'
            f'<p class="src">Atualização mensal. Compilação em {data_br(col)}. Dados abertos: <a href="/dados/">/dados/</a>.</p></section>')
    fa = [("Por que a receita não considera as deduções?", "Para refletir o valor bruto realizado declarado; as deduções do Fundeb aparecem apenas na declaração original."), ("O que é a DCA?", "A Declaração de Contas Anuais é o balanço que estados e municípios enviam ao Tesouro Nacional."), ("Por que alguns municípios não têm valores?", "Porque não enviaram a declaração ou ela não estava completa na compilação."),
          ("Os valores podem ser comparados entre municípios?", "Os valores por habitante ajudam a dimensionar, mas municípios diferem muito em economia e transferências. O Estrato não publica rankings."), ("Com que frequência os dados são atualizados?", "Uma vez por mês."), ("Como corrijo um dado?", "Escreva pela página de correções; a fonte primária é sempre o SICONFI.")]
    S.write("/municipios/metodologia/", S.page(f"Metodologia: finanças de estados e municípios | {site}", "Fontes, conceitos e limites dos dados de receitas, despesas, população e PIB de estados e municípios no Estrato.", "/municipios/metodologia/", body, faqs=fa, crumbs=[("Municípios", "/municipios/"), ("Metodologia", "/municipios/metodologia/")]), familia="paginas", lastmod=col); urls.append("/municipios/metodologia/")
    # ---------- CSV ----------
    out = S.OUT / "dados"; out.mkdir(parents=True, exist_ok=True); n = 0
    with (out / "financas-entes.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["codigo_ibge", "esfera", "uf", "ente", "ano", "populacao_censo_2022", "receita_total", "receitas_correntes", "impostos", "transferencias_correntes", "receitas_de_capital", "despesa_empenhada", "pib"])
        for c, e in sorted(sc["entes"].items(), key=lambda x: (x[1]["e"], x[1]["uf"] or "", slugify(x[1]["n"]))):
            a, d = ult(e); ibx = (ib["m"] if e["e"] == "M" else ib["uf"]).get(c, {})
            w.writerow([c, e["e"], e["uf"] or POR_COD.get(c, ""), e["n"], a or "", int(ibx.get("pop") or (e["pop"] if e["e"] != "U" else 0) or 0) or "", *[f'{d[k]:.2f}' if k in d else "" for k in ("rec", "rc", "imp", "tc", "rk", "desp")], f'{ibx["pib"]:.0f}' if ibx.get("pib") else ""]); n += 1
    S.extra_sets = getattr(S, "extra_sets", []) + [("financas-entes", "Finanças de estados, União e municípios", "Uma linha por ente: população, receitas, despesa empenhada e PIB do último exercício declarado.", n, "Tesouro Nacional (SICONFI/DCA) e IBGE (SIDRA)", "https://siconfi.tesouro.gov.br/", "Anexos I-C e I-E da DCA; Censo 2022 e PIB; valores nominais.", col)]
    return {"urls": urls}
