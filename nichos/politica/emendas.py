"""Emendas parlamentares ao Orçamento da União desde 2023, por autor e por município.

Dados: data/emendas/emendas.json.gz (tools/datasets_emendas.py), do download em lote público do Portal da Transparência (sem chave).
Páginas: /emendas/ (hub), /emendas/autor/<slug>/, /emendas/municipios/<uf>/, /emendas/municipios/<uf>/<slug>/, /emendas/metodologia/.
Valores por autor: empenhado, liquidado e pago por ano da emenda. Valores por município: valor recebido pelos favorecidos
sediados no município (pagamentos desde 2023). Pessoas físicas e empresários individuais só em totais agregados.
Período eleitoral: só fatos, listas em ordem alfabética, sem ranking.
"""
import collections, csv, gzip, json, re
from core.site import E, slugify
from .dados import UF, PREP, brl, brl0, data_br, num, pct

SIG = {v: k for k, v in UF.items()}
MIN_AUT_MUN = 3
_C = {}
MIN = {"de", "da", "do", "das", "dos", "e", "d'"}


def tit(s):
    w = (s or "").lower().split()
    return " ".join(x if (x in MIN and i) else (x[:2] + x[2:].capitalize() if x.startswith("d'") else x.capitalize()) for i, x in enumerate(w))


def carregar(S):
    if "d" in _C: return _C["d"]
    f = S.ROOT / "data/emendas/emendas.json.gz"
    d = json.loads(gzip.decompress(f.read_bytes())) if f.exists() else {"autores": {}, "mun": {}, "fav_nomes": {}}
    # mesmo autor com mais de um código (ex.: deputado que virou senador): funde pelo nome
    por_nome = {}; alias = {}
    for c, a in list(d["autores"].items()):
        k = slugify(a["nome"])
        if k not in por_nome: por_nome[k] = c; continue
        b = d["autores"][por_nome[k]]; alias[c] = por_nome[k]
        for y, x in a["anos"].items():
            z = b["anos"].setdefault(y, {"emp": 0.0, "liq": 0.0, "pago": 0.0, "rap": 0.0, "n": 0})
            for kk in z: z[kk] += x[kk]
        for kk in ("tipos", "func", "loc", "mun", "fav"):
            for t, v in a[kk].items(): b[kk][t] = b[kk].get(t, 0) + v
        b["n"] += a["n"]; del d["autores"][c]
    for m_ in d["mun"].values():
        for c in [c for c in m_["autores"] if c in alias]: m_["autores"][alias[c]] = m_["autores"].get(alias[c], 0) + m_["autores"].pop(c)
    m = S.ROOT / "data/emendas/meta.json"; meta = json.loads(m.read_text(encoding="utf-8")) if m.exists() else {}
    _C["d"] = (d, meta); return _C["d"]


def _coletivo(n): return bool(re.match(r"^(BANCADA|COM\.|COMISS|RELATOR|COMISSÃO|LIDERAN|MESA)", n.upper()))
def _hbar(v, mx): return f'<span class="mbar" aria-hidden="true"><i style="width:{100 * max(v, 0) / mx if mx else 0:.0f}%;background:#1f4e79"></i></span>'


def build(S):
    D, meta = carregar(S)
    if not D["autores"]: return {"urls": []}
    col = (meta.get("coletado_em") or "")[:10]; fam = "emendas"; urls = []; FN = D["fav_nomes"]
    fonte = f'<a href="https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares" target="_blank" rel="noopener">download de dados de emendas parlamentares do Portal da Transparência (CGU)</a>'
    parl = {}
    for d in S.parl["deps"]: parl.setdefault(slugify(d["nome"]), (d["url"], "deputado", d))
    for x in S.parl["sens"]: parl.setdefault(slugify(x["nome"]), (x["url"], "senador", x))
    A = {c: a for c, a in D["autores"].items() if a["anos"]}
    usados = set(); aurl = {}
    for c, a in sorted(A.items(), key=lambda x: slugify(x[1]["nome"])):
        s = slugify(a["nome"]) or c; s = s if s not in usados else f"{s}-{c}"; usados.add(s); aurl[c] = f"/emendas/autor/{s}/"
    M = D["mun"]
    def murl(k):
        uf, n = k.split("|", 1); return f"/emendas/municipios/{uf.lower()}/{slugify(n)}/"
    pag_mun = {k for k, m in M.items() if k.split("|")[0] in UF and len(m["autores"]) >= MIN_AUT_MUN}
    mlink = lambda k: (f'<a href="{murl(k)}">{E(tit(k.split("|", 1)[1]))}</a>' if k in pag_mun else E(tit(k.split("|", 1)[1]))) + f' <small>{k.split("|")[0]}</small>'
    alink = lambda c, nome=None: f'<a href="{aurl[c]}">{E(tit(nome or A[c]["nome"]))}</a>' if c in aurl else E(tit(nome or D["autores"].get(c, {}).get("nome", c)))
    anos = sorted({y for a in A.values() for y in a["anos"]})
    TA = {y: {"emp": 0.0, "pago": 0.0, "n": 0, "aut": 0} for y in anos}
    for a in A.values():
        for y, x in a["anos"].items(): TA[y]["emp"] += x["emp"]; TA[y]["pago"] += x["pago"]; TA[y]["n"] += x["n"]; TA[y]["aut"] += 1
    ind = [a for a in A.values() if not _coletivo(a["nome"])]
    med = {y: (sum(a["anos"].get(y, {}).get("emp", 0) for a in ind) / max(sum(1 for a in ind if y in a["anos"]), 1)) for y in anos}
    # ---------- autores ----------
    for c, a in A.items():
        u = aurl[c]; nome = tit(a["nome"]); p = parl.get(slugify(a["nome"])); col_ = _coletivo(a["nome"])
        emp = sum(x["emp"] for x in a["anos"].values()); pago = sum(x["pago"] + x["rap"] for x in a["anos"].values()); n = sum(x["n"] for x in a["anos"].values())
        quem = (f'{"do deputado" if p[1] == "deputado" else "do senador"} <a href="{p[0]}">{E(p[2]["nome"])}</a> ({E(p[2]["partido"])}-{p[2]["uf"]})' if p else (f"da autoria coletiva {E(nome)}" if col_ else f"de {E(nome)}"))
        lead = (f'<p class="snippet">Emendas ao Orçamento da União de autoria {quem} somam <strong>{brl(emp)}</strong> empenhados desde 2023, em {num(n)} registros por emenda e localidade. '
                f'Desses recursos, {brl(pago)} já foram pagos (incluindo restos a pagar), segundo o Portal da Transparência.</p>')
        body = f'<article class="post"><h1>Emendas parlamentares de {E(nome)}: valores por ano, área e município</h1>{lead}'
        hd = ["Ano", "Empenhado", "Liquidado", "Pago", "Restos a pagar pagos"] + ([] if col_ else ["Média por autor individual (empenhado)"])
        body += "<h2>Por ano da emenda</h2>" + S.table(hd, [[y, brl0(x["emp"]), brl0(x["liq"]), brl0(x["pago"]), brl0(x["rap"])] + ([] if col_ else [brl0(med[y])]) for y, x in sorted(a["anos"].items())], "Valores por ano da emenda")
        ts = sorted(a["tipos"].items(), key=lambda x: -x[1])
        body += "<h2>Por tipo de emenda</h2>" + S.table(["Tipo", "Empenhado", "%"], [[E(t), brl(v), pct(v, emp)] for t, v in ts])
        fs = sorted(a["func"].items(), key=lambda x: -x[1])[:12]; mx = fs[0][1] if fs else 1
        body += "<h2>Por área (função orçamentária)</h2>" + S.table(["Função", "Empenhado", ""], [[E(f), brl(v), _hbar(v, mx)] for f, v in fs])
        ls = sorted(a["loc"].items(), key=lambda x: -x[1])[:12]
        body += "<h2>Localidade de aplicação declarada</h2><p>“Múltiplo” indica emendas aplicadas em mais de um município; “(UF)” indica aplicação no estado como um todo.</p>" + S.table(["Localidade", "Empenhado"], [[E(tit(l)) if l.isupper() else E(l), brl(v)] for l, v in ls])
        ms = sorted(a["mun"].items(), key=lambda x: -x[1])[:20]
        if ms: body += "<h2>Municípios dos favorecidos (pagamentos desde 2023)</h2><p>Valor recebido por órgãos, fundos e entidades sediados em cada município com recursos destas emendas.</p>" + S.table(["Município", "Recebido"], [[mlink(k), brl(v)] for k, v in ms], "Até 20 municípios com maior valor recebido")
        fv = sorted(a["fav"].items(), key=lambda x: -x[1])[:10]
        if fv: body += "<h2>Principais favorecidos pessoa jurídica</h2>" + S.table(["Favorecido", "CNPJ", "Recebido"], [[E(FN.get(k, k)), f"{k[:2]}.{k[2:5]}.{k[5:8]}/{k[8:12]}-{k[12:]}", brl(v)] for k, v in fv], "Pessoas físicas e empresários individuais não são exibidos")
        body += f'<p class="src">Fonte oficial: {fonte}, arquivo gerado em {data_br(meta.get("arquivo_gerado_em"))}. Empenho é a reserva do recurso; pagamento é a saída efetiva. Compilação em {data_br(col)}. Veja a <a href="/emendas/metodologia/">metodologia</a> e o <a href="/glossario/emenda-parlamentar/">verbete emenda parlamentar</a>.</p></article>'
        ua = max(a["anos"])
        faqs = [(f"Quanto {nome} destinou em emendas desde 2023?", f"{brl(emp)} empenhados em emendas com ano entre 2023 e {ua}, segundo o Portal da Transparência."),
                (f"Quanto já foi pago das emendas de {nome}?", f"{brl(pago)}, somando pagamentos do ano e restos a pagar pagos."),
                ("Qual a principal área das emendas?", f"{E(fs[0][0])}, com {brl(fs[0][1])} empenhados ({pct(fs[0][1], emp)})." if fs else "Não há função orçamentária registrada."),
                ("Qual o principal tipo de emenda?", f"{E(ts[0][0])}, com {pct(ts[0][1], emp)} do valor empenhado." if ts else "Não informado."),
                ("Qual município mais recebeu recursos destas emendas?", f"{E(tit(ms[0][0].split('|', 1)[1]))} ({ms[0][0].split('|')[0]}), com {brl(ms[0][1])} recebidos por favorecidos sediados lá." if ms else "Não há pagamentos a favorecidos com município informado desde 2023."),
                ("Empenhar emendas é irregular?", "Não. Emendas são instrumentos previstos no Orçamento. A página só descreve os valores oficiais, sem juízo sobre eles.")]
        S.write(u, S.page(f"Emendas parlamentares de {nome} desde 2023: valores e municípios", f"{nome}: {brl0(emp)} empenhados em emendas ao Orçamento desde 2023, {brl0(pago)} pagos. Por ano, tipo, área, município e favorecido.", u, body, faqs=faqs,
                            crumbs=[("Emendas", "/emendas/"), (nome, u)], jsonld={"@type": "Dataset", "name": f"Emendas parlamentares de {nome} (desde 2023)", "description": f"Valores empenhados, liquidados e pagos das emendas de {nome} ao Orçamento da União, por ano, tipo, função e município.",
                            "url": S.BASE + u, "isBasedOn": meta.get("fonte"), "license": "https://creativecommons.org/licenses/by/4.0/deed.pt-br", "isAccessibleForFree": True, "creator": {"@id": S.BASE + "/#org"}, "inLanguage": "pt-BR", "temporalCoverage": f"2023-01-01/{col}",
                            "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{S.BASE}/dados/emendas-autores.csv"}]}), familia=fam, lastmod=col)
        urls.append(u)
    # ---------- municípios ----------
    por_uf = collections.defaultdict(list)
    for k, m in M.items():
        uf = k.split("|")[0]
        if uf in UF: por_uf[uf].append(k)
    for k in sorted(pag_mun):
        m = M[k]; uf, nraw = k.split("|", 1); nome = tit(nraw); u = murl(k); tot = sum(m["anos"].values())
        aus = sorted(m["autores"].items(), key=lambda x: slugify(D["autores"].get(x[0], {}).get("nome", x[0])))
        lead = (f'<p class="snippet">Órgãos, fundos e entidades sediados em <strong>{E(nome)} ({uf})</strong> receberam <strong>{brl(tot)}</strong> em pagamentos de emendas parlamentares desde 2023, '
                f'com recursos de emendas de {num(len(m["autores"]))} autores, segundo o Portal da Transparência.</p>')
        body = f'<article class="post"><h1>Emendas parlamentares em {E(nome)} ({uf}): quanto o município recebeu</h1>{lead}'
        body += "<h2>Por ano do pagamento</h2>" + S.table(["Ano", "Recebido"], [[y, brl(v)] for y, v in sorted(m["anos"].items())])
        body += "<h2>Por tipo de emenda</h2>" + S.table(["Tipo", "Recebido", "%"], [[E(t), brl(v), pct(v, tot)] for t, v in sorted(m["tipos"].items(), key=lambda x: -x[1])])
        body += "<h2>Por natureza do favorecido</h2>" + S.table(["Natureza jurídica", "Recebido"], [[E(t), brl(v)] for t, v in sorted(m["nat"].items(), key=lambda x: -x[1])[:10]])
        fv = sorted(m["fav"].items(), key=lambda x: -x[1])[:15]
        if fv: body += "<h2>Favorecidos pessoa jurídica</h2>" + S.table(["Favorecido", "Recebido"], [[E(FN.get(d, d)), brl(v)] for d, v in fv], "Até 15 favorecidos; pessoas físicas e empresários individuais só no total")
        if m["pf"]: body += f'<p>Pagamentos a pessoas físicas, empresários individuais ou favorecidos sem identificação somam {brl(m["pf"])} e aparecem só neste total.</p>'
        li = "".join(f'<li>{alink(c)} <small>{brl(v)}</small></li>' for c, v in aus)
        body += f'<h2>Autores das emendas (ordem alfabética)</h2><ul class="nlist">{li}</ul>'
        body += f'<p class="src">Fonte oficial: {fonte}. O município é o da sede do favorecido informado pela CGU. Compilação em {data_br(col)}. Veja o <a href="/municipios/{uf.lower()}/{u.rstrip('/').rsplit('/', 1)[1]}/">perfil de {E(nome)}</a>, <a href="/emendas/municipios/{uf.lower()}/">todos os municípios {PREP[uf]} {UF[uf]}</a> e a <a href="/emendas/metodologia/">metodologia</a>.</p></article>'
        ym = max(m["anos"].items(), key=lambda x: x[1]); tp = max(m["tipos"].items(), key=lambda x: x[1]); nat = max(m["nat"].items(), key=lambda x: x[1])
        faqs = [(f"Quanto {nome} recebeu em emendas parlamentares desde 2023?", f"{brl(tot)} em pagamentos a favorecidos sediados no município."),
                (f"Quantos parlamentares ou bancadas destinaram emendas a {nome}?", f"{num(len(m['autores']))} autores tiveram pagamentos a favorecidos do município desde 2023."),
                ("Em que ano o município recebeu mais?", f"Em {ym[0]}, com {brl(ym[1])}."), ("Qual o principal tipo de emenda?", f"{E(tp[0])}, com {pct(tp[1], tot)} do valor."),
                ("Quem recebe o dinheiro?", f"Principalmente “{E(nat[0])}”, com {brl(nat[1])}. Pessoas físicas não são identificadas."),
                ("A lista de autores é um ranking?", "Não. Os autores estão em ordem alfabética, com o valor que o município recebeu de cada um.")]
        S.write(u, S.page(f"Emendas parlamentares em {nome} ({uf}) desde 2023", f"{nome} ({uf}) recebeu {brl0(tot)} em pagamentos de emendas parlamentares desde 2023, de {len(m['autores'])} autores. Por ano, tipo e favorecido.", u, body, faqs=faqs,
                            crumbs=[("Emendas", "/emendas/"), (UF[uf], f"/emendas/municipios/{uf.lower()}/"), (nome, u)]), familia=fam, lastmod=col)
        urls.append(u)
    for uf, ks in sorted(por_uf.items()):
        u = f"/emendas/municipios/{uf.lower()}/"; tot = sum(sum(M[k]["anos"].values()) for k in ks)
        rows = [[mlink(k), brl(sum(M[k]["anos"].values())), num(len(M[k]["autores"]))] for k in sorted(ks, key=lambda k: slugify(k.split("|", 1)[1]))]
        body = (f'<section class="blk"><h1>Emendas parlamentares nos municípios {PREP[uf]} {UF[uf]}</h1><p class="snippet">Favorecidos sediados em {num(len(ks))} municípios {PREP[uf]} {UF[uf]} receberam <strong>{brl(tot)}</strong> em pagamentos de emendas parlamentares desde 2023.</p>'
                + S.table(["Município", "Recebido desde 2023", "Autores"], rows, "Municípios em ordem alfabética") + f'<p class="src">Fonte oficial: {fonte}. Compilação em {data_br(col)}.</p></section>')
        faqs = [(f"Quanto os municípios {PREP[uf]} {UF[uf]} receberam em emendas?", f"{brl(tot)} desde 2023, somando {num(len(ks))} municípios."), ("De onde vêm os dados?", "Do download em lote de emendas parlamentares do Portal da Transparência, mantido pela CGU."),
                ("O valor inclui recursos para o governo estadual?", "Inclui favorecidos sediados na capital, como órgãos e fundos estaduais, porque o município é o da sede do favorecido."),
                ("A tabela é um ranking?", "Não. Os municípios estão em ordem alfabética."), ("Com que frequência os dados são atualizados?", "Diariamente, quando a CGU publica um novo arquivo.")]
        S.write(u, S.page(f"Emendas nos municípios {PREP[uf]} {UF[uf]} | {S.CFG['site_name']}", f"Quanto cada município {PREP[uf]} {UF[uf]} recebeu em emendas parlamentares desde 2023: {brl0(tot)} no total.", u, body, faqs=faqs,
                            crumbs=[("Emendas", "/emendas/"), (UF[uf], u)]), familia="paginas", lastmod=col)
        urls.append(u)
    # ---------- hub, metodologia, CSV ----------
    ali = lambda lst: "".join(f'<li>{alink(c)}</li>' for c, a in sorted(lst, key=lambda x: slugify(x[1]["nome"])))
    ind_l = [(c, a) for c, a in A.items() if not _coletivo(a["nome"])]; col_l = [(c, a) for c, a in A.items() if _coletivo(a["nome"])]
    tt = collections.Counter()
    for a in A.values():
        for t, v in a["tipos"].items(): tt[t] += v
    te = sum(x["emp"] for x in TA.values())
    body = (f'<section class="blk"><h1>Emendas parlamentares desde 2023: autores e municípios</h1><p class="snippet">Emendas ao Orçamento da União com ano entre 2023 e {anos[-1]} somam <strong>{brl(te)}</strong> empenhados, de {num(len(A))} autores (parlamentares, bancadas estaduais e comissões), segundo o Portal da Transparência.</p>'
            + S.table(["Ano", "Empenhado", "Pago no ano", "Autores", f"Média por autor individual"], [[y, brl(x["emp"]), brl(x["pago"]), num(x["aut"]), brl(med[y])] for y, x in sorted(TA.items())], "Por ano da emenda")
            + "<h2>Por tipo</h2>" + S.table(["Tipo", "Empenhado", "%"], [[E(t), brl(v), pct(v, te)] for t, v in tt.most_common()])
            + '<h2>Municípios por estado</h2><div class="chips">' + "".join(f'<a class="chip" href="/emendas/municipios/{uf.lower()}/">{UF[uf]}</a>' for uf in sorted(por_uf, key=lambda x: UF[x])) + "</div>"
            + f'<h2>Autores individuais (ordem alfabética)</h2><details><summary>{num(len(ind_l))} autores</summary><ul class="nlist">{ali(ind_l)}</ul></details>'
            + f'<h2>Bancadas e comissões</h2><details><summary>{num(len(col_l))} autorias coletivas</summary><ul class="nlist">{ali(col_l)}</ul></details>'
            + '<h2>Como ler</h2><p>Empenho é a reserva do recurso no Orçamento; liquidação confirma a entrega; pagamento é a saída do dinheiro. Transferências especiais vão direto ao caixa do estado ou município, sem finalidade definida na emenda. O Estrato não classifica autores.</p>'
            + f'<p>Baixe os dados em <a href="/dados/#emendas">CSV</a> e veja a <a href="/emendas/metodologia/">metodologia</a>.</p><p class="src">Fonte: {fonte}.</p></section>')
    faqs = [("Quanto foi empenhado em emendas desde 2023?", f"{brl(te)}, somando emendas com ano entre 2023 e {anos[-1]}."), ("Quantos autores têm emendas?", f"{num(len(A))}: {num(len(ind_l))} individuais e {num(len(col_l))} bancadas e comissões."),
            ("O que são transferências especiais?", "Emendas individuais repassadas diretamente a estados e municípios, sem finalidade definida na emenda."), ("De onde vêm os dados?", "Do download em lote público do Portal da Transparência, sem uso de chave de API."),
            ("Há ranking de parlamentares?", "Não. As listas estão em ordem alfabética.")]
    S.write("/emendas/", S.page("Emendas parlamentares desde 2023 por autor e município", f"{brl0(te)} empenhados em emendas parlamentares desde 2023: valores por autor, tipo e município, com dados do Portal da Transparência.", "/emendas/", body, faqs=faqs,
                                crumbs=[("Emendas", "/emendas/")]), familia="paginas", lastmod=col)
    urls.append("/emendas/")
    body = ('<article class="post"><h1>Metodologia das emendas parlamentares</h1><p class="snippet">Como o Estrato organiza as emendas ao Orçamento da União por autor e por município.</p>'
            '<h2>Fonte</h2><p>Download em lote de emendas parlamentares do Portal da Transparência, mantido pela Controladoria-Geral da União (CGU). O arquivo é público e não exige cadastro nem chave; a coleta roda uma vez por dia e só processa de novo quando a CGU publica um arquivo novo.</p>'
            '<h2>Por autor</h2><p>Somam-se empenhado, liquidado, pago e restos a pagar pagos de todas as emendas com ano entre 2023 e o ano corrente. A média por autor individual exclui bancadas, comissões e relatoria. O vínculo com a página do parlamentar é feito pelo nome parlamentar.</p>'
            '<h2>Por município</h2><p>Usa o arquivo de pagamentos por favorecido, desde janeiro de 2023: o município é o da sede do favorecido. Recursos para órgãos estaduais sediados na capital aparecem na capital. '
            f'Ganham página os municípios com pagamentos de pelo menos {MIN_AUT_MUN} autores.</p>'
            '<h2>Privacidade</h2><p>Favorecidos pessoa física e empresários individuais não são identificados; entram só em totais agregados.</p>'
            '<h2>Limites</h2><p>Os valores descrevem a execução orçamentária oficial e não indicam irregularidade. Durante o período eleitoral, as listas ficam em ordem alfabética, sem ranking.</p></article>')
    faqs = [("De onde vêm os dados de emendas?", "Do download em lote do Portal da Transparência (CGU)."), ("O que é empenho?", "A reserva do recurso no Orçamento para uma despesa."), ("Como é definido o município?", "Pela sede do favorecido que recebeu o pagamento."),
            ("Pessoas físicas aparecem?", "Não pelo nome; entram só em totais."), ("Há ranking?", "Não. As listas estão em ordem alfabética.")]
    S.write("/emendas/metodologia/", S.page("Metodologia das emendas parlamentares", "Fonte, cálculos por autor e por município e regras de privacidade das páginas de emendas parlamentares do Estrato.", "/emendas/metodologia/", body, faqs=faqs,
                                            crumbs=[("Emendas", "/emendas/"), ("Metodologia", "/emendas/metodologia/")]), familia="paginas", lastmod=col)
    urls.append("/emendas/metodologia/")
    out = S.OUT / "dados"; out.mkdir(parents=True, exist_ok=True); sets = []; n = 0
    with (out / "emendas-autores.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["codigo_autor", "autor", "ano_emenda", "empenhado", "liquidado", "pago", "restos_a_pagar_pagos", "registros"])
        for c, a in sorted(A.items(), key=lambda x: slugify(x[1]["nome"])):
            for y, x in sorted(a["anos"].items()): w.writerow([c, a["nome"], y, f'{x["emp"]:.2f}', f'{x["liq"]:.2f}', f'{x["pago"]:.2f}', f'{x["rap"]:.2f}', x["n"]]); n += 1
    sets.append(("emendas-autores", "Emendas parlamentares por autor e ano", "Uma linha por autor e ano da emenda desde 2023: empenhado, liquidado e pago.", n)); n = 0
    with (out / "emendas-municipios.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["uf", "municipio", "codigo_autor", "autor", "recebido"])
        for k, m in sorted(M.items()):
            uf, mn = k.split("|", 1)
            for c, v in sorted(m["autores"].items()): w.writerow([uf, mn, c, D["autores"].get(c, {}).get("nome", ""), f"{v:.2f}"]); n += 1
    sets.append(("emendas-municipios", "Emendas parlamentares por município e autor", "Uma linha por município do favorecido e autor: valor recebido desde 2023.", n))
    S.emendas_sets = sets; S.emendas_meta = col; S.emendas_aurl = {slugify(a["nome"]): aurl[c] for c, a in A.items()}
    return {"urls": urls}


def link_parl(S, nome):
    D, _ = carregar(S); s = slugify(nome)
    for c, a in D["autores"].items():
        if a["anos"] and slugify(a["nome"]) == s:
            emp = sum(x["emp"] for x in a["anos"].values())
            return emp, c
    return None
