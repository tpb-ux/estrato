"""Cota parlamentar desde 2023: CEAP (Câmara) e CEAPS (Senado), por parlamentar, por categoria e por fornecedor pessoa jurídica.

Dados: data/cotas/<casa>.json.gz, gerados por tools/datasets_cotas.py a partir dos arquivos oficiais públicos (sem chave).
Páginas: /cota/ (hub), /cota/<deputados|senadores>/<slug>/, /cota/<casa>/categoria/<slug>/, /cota/fornecedores/<cnpj>/, /cota/metodologia/.
Privacidade: fornecedores pessoa física (CPF) nunca são publicados; fornecedores PJ cujo nome traz número de CPF (MEI) não ganham página
e o número é removido do nome. Período eleitoral: só dados factuais; listas de parlamentares em ordem alfabética, sem ranking.
Presença: votos registrados nas votações nominais de plenário (placar /votacoes/).
"""
import collections, csv, gzip, json, re
from core.site import E, slugify
from .dados import UF, brl, brl0, data_br, num, pct, MESES
from . import votacoes as _vot

CASA = {"camara": ("Câmara", "Câmara dos Deputados", "deputados", "deputado", "CEAP", "Cota para o Exercício da Atividade Parlamentar"),
        "senado": ("Senado", "Senado Federal", "senadores", "senador", "CEAPS", "Cota para o Exercício da Atividade Parlamentar dos Senadores")}
FONTE = {"camara": ("arquivo anual da cota parlamentar da Câmara", "https://www.camara.leg.br/cotas/Ano-{a}.csv.zip"),
         "senado": ("API de dados administrativos do Senado (CEAPS)", "https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/{a}")}
MIN_FORN_TOT, MIN_FORN_PARL = 250000, 10
_C = {}
CPF_RE = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")


def nome_forn(n):
    n = CPF_RE.sub("", n or "").strip(" -."); return re.sub(r"\s+", " ", n) or "Fornecedor sem nome informado"
def tem_cpf(n): return bool(re.search(r"\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2}", n or ""))
def fmt_cnpj(d): return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def carregar(S):
    if "d" in _C: return _C["d"]
    d = S.ROOT / "data/cotas"; out = {}
    for casa in CASA:
        f = d / f"{casa}.json.gz"
        out[casa] = json.loads(gzip.decompress(f.read_bytes())) if f.exists() else {"parl": {}, "forn": {}, "pf": {}}
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8")) if (d / "meta.json").exists() else {}
    _C["d"] = (out, meta); return _C["d"]


def _medias(P):
    """Por ano: nº de parlamentares com despesa, total, média por parlamentar e média por categoria."""
    m = {}
    for p in P.values():
        for a, x in p["anos"].items():
            r = m.setdefault(a, {"n": 0, "tot": 0.0, "cat": collections.Counter(), "meses": set()}); r["n"] += 1; r["tot"] += x["tot"]
            for c, v in x["cat"].items(): r["cat"][c] += v
            r["meses"] |= {int(k) for k in x["mes"] if int(k)}
    for r in m.values(): r["med"] = r["tot"] / r["n"] if r["n"] else 0
    return m


def _barras_mes(mes, media=None):
    vals = [mes.get(str(i), 0) for i in range(1, 13)]; mx = max(vals + ([media] if media else []) + [1])
    r = "".join(f'<rect x="{(i) * 8.3 + 0.6:.1f}" y="{40 - 38 * v / mx:.1f}" width="7" height="{38 * v / mx:.1f}" fill="#1f4e79"><title>{MESES[i + 1]}: {brl(v)}</title></rect>' for i, v in enumerate(vals) if v > 0)
    ln = f'<line x1="0" x2="100" y1="{40 - 38 * media / mx:.1f}" y2="{40 - 38 * media / mx:.1f}" stroke="#a32d1c" stroke-width=".4" stroke-dasharray="1.5 1"/>' if media else ""
    lbl = "".join(f'<text x="{i * 8.3 + 4.1:.1f}" y="45" font-size="3" text-anchor="middle" fill="#555">{MESES[i + 1][:3]}</text>' for i in range(12))
    return f'<figure class="cbar"><svg viewBox="0 0 100 46" role="img" aria-label="Despesas por mês" width="100%">{r}{ln}{lbl}</svg>' + (f'<figcaption>Barras: valor do mês. Linha tracejada: média mensal por parlamentar da casa.</figcaption>' if media else "") + "</figure>"


def _hbar(v, mx):
    return f'<span class="mbar" aria-hidden="true"><i style="width:{100 * max(v, 0) / mx if mx else 0:.0f}%;background:#1f4e79"></i></span>'


def presenca(S, casa, pid):
    vs, _ = _vot.carregar(S); x = _vot.resumo(S).get(f"{casa}:{pid}")
    tot = sum(1 for v in vs if v["casa"] == casa)
    return (x["n"] if x else 0), tot


def build(S):
    D, meta = carregar(S)
    if not any(D[c]["parl"] for c in CASA): return {"urls": []}
    col = (meta.get("coletado_em") or "")[:10]; fam = "cotas"; urls = []
    atuais = {"camara": {str(d["id"]): d for d in S.parl["deps"]}, "senado": {str(x["id"]): x for x in S.parl["sens"]}}
    # fornecedores: CNPJ (PJ) somando as duas casas
    FO = {}  # agrupado pela raiz do CNPJ (8 dígitos): matriz e filiais da mesma empresa
    for casa in CASA:
        for cn, f in D[casa]["forn"].items():
            r = cn[:8]; g = FO.setdefault(r, {"nome": f["nome"], "tot": 0.0, "casas": {}, "cnpjs": {}, "cpf_no_nome": False})
            g["tot"] += f["tot"]; g["cpf_no_nome"] |= tem_cpf(f["nome"]); g["cnpjs"][cn] = g["cnpjs"].get(cn, 0) + f["tot"]
            if f["tot"] >= max(g["cnpjs"].values()): g["nome"] = f["nome"]
            h = g["casas"].setdefault(casa, {"tot": 0.0, "n": 0, "cat": collections.Counter(), "parl": collections.Counter(), "anos": collections.Counter()})
            h["tot"] += f["tot"]; h["n"] += f["n"]; h["cat"].update(f["cat"]); h["parl"].update(f["parl"]); h["anos"].update(f["anos"])
    pag_forn = {r for r, g in FO.items() if not g["cpf_no_nome"] and (sum(len(f["parl"]) for f in g["casas"].values()) >= MIN_FORN_PARL or (g["tot"] >= MIN_FORN_TOT and sum(len(f["parl"]) for f in g["casas"].values()) >= 3))}
    furl = lambda cn: f"/cota/fornecedores/{cn[:8]}/"
    flink = lambda cn, nome: f'<a href="{furl(cn)}">{E(nome_forn(nome))}</a>' if cn[:8] in pag_forn else E(nome_forn(nome))
    cats = {casa: sorted({c for p in D[casa]["parl"].values() for a in p["anos"].values() for c in a["cat"]}) for casa in CASA}
    curl = lambda casa, c: f"/cota/{casa}/categoria/{slugify(c)[:70]}/"
    M = {casa: _medias(D[casa]["parl"]) for casa in CASA}
    anos = [str(a) for a in meta.get("anos", [])]
    ult = {casa: max((a for a in M[casa]), default="") for casa in CASA}
    ult_mes = {casa: max(M[casa][ult[casa]]["meses"]) if ult[casa] and M[casa][ult[casa]]["meses"] else 12 for casa in CASA}
    fonte_txt = lambda casa: ", ".join(f'<a href="{FONTE[casa][1].format(a=a)}" target="_blank" rel="noopener">{a}</a>' for a in anos)
    S.cota_urls = {}
    # ---------- parlamentares ----------
    for casa in CASA:
        cn_, cl, kind, sing, sig, sig_l = CASA[casa]; P = D[casa]["parl"]
        for pid, a in sorted(atuais[casa].items(), key=lambda x: slugify(x[1]["nome"])):
            p = P.get(pid)
            if not p: continue
            u = f"/cota/{kind}/{a['slug']}/"; S.cota_urls[f"{casa}:{pid}"] = u
            uf = a["uf"]; part = a["partido"]; nome = a["nome"]
            tot = sum(x["tot"] for x in p["anos"].values()); nl = sum(x["n"] for x in p["anos"].values())
            ua = max(p["anos"]); xa = p["anos"][ua]; ma = M[casa][ua]
            dif = xa["tot"] - ma["med"]
            prs, ptot = presenca(S, casa, int(pid) if casa == "senado" else a["id"])
            lead = (f'<p class="snippet"><strong>{E(nome)}</strong> ({E(part)}-{uf}) declarou <strong>{brl(tot)}</strong> em despesas da {sig} desde 2023, em {num(nl)} lançamentos reembolsados. '
                    f'Em {ua}{" (até " + MESES[ult_mes[casa]] + ")" if ua == ult[casa] else ""}, foram {brl(xa["tot"])}, {brl(abs(dif))} {"acima" if dif >= 0 else "abaixo"} da média de {brl(ma["med"])} por {sing} com despesas no ano.</p>')
            body = f'<article class="post"><h1>Cota parlamentar de {E(nome)}: gastos por ano, categoria e fornecedor</h1>{lead}'
            body += "<h2>Total por ano e média da casa</h2>" + S.table(["Ano", "Total declarado", "Lançamentos", f"Média por {sing}", "Diferença"],
                    [[a_, brl(p["anos"][a_]["tot"]), num(p["anos"][a_]["n"]), brl(M[casa][a_]["med"]), ("+" if p["anos"][a_]["tot"] >= M[casa][a_]["med"] else "−") + brl(abs(p["anos"][a_]["tot"] - M[casa][a_]["med"]))] for a_ in sorted(p["anos"])],
                    f"Despesas da {sig} por ano")
            body += f"<h2>Despesas por mês em {ua}</h2>" + _barras_mes(xa["mes"], ma["med"] / max(len(ma["meses"]), 1))
            mx = max(list(xa["cat"].values()) + [1]); rows = []
            for c, v in sorted(xa["cat"].items(), key=lambda x: -x[1]):
                mc = ma["cat"][c] / ma["n"]
                rows.append([f'<a href="{curl(casa, c)}">{E(c)}</a>', brl(v), brl(mc), pct(v, xa["tot"]), _hbar(v, mx)])
            body += f"<h2>Por categoria de gasto em {ua}</h2>" + S.table(["Categoria", "Valor", f"Média por {sing}", "% do total", ""], rows, f"Categorias da {sig} em {ua}")
            fs = sorted(p["forn"].items(), key=lambda x: -x[1])[:15]; ff = D[casa]["forn"]
            if fs:
                body += ("<h2>Principais fornecedores (pessoa jurídica)</h2><p>Soma desde 2023 dos documentos emitidos por empresas (CNPJ). Fornecedores pessoa física não são exibidos.</p>"
                         + S.table(["Fornecedor", "CNPJ", "Valor"], [[flink(k, ff[k]["nome"]), fmt_cnpj(k), brl(v)] for k, v in fs], "Até 15 fornecedores com maior valor para este parlamentar"))
            body += (f'<h2>Presença nas votações nominais</h2><p>{E(nome)} tem voto registrado em <strong>{num(prs)}</strong> das {num(ptot)} votações nominais de plenário {"da Câmara" if casa == "camara" else "do Senado"} desde fevereiro de 2023 ({pct(prs, ptot)}). '
                     f'Quem assumiu depois do início da legislatura tem menos votações possíveis. Veja <a href="{a["url"]}#votacoes">como votou</a>.</p>')
            body += (f'<p class="src">Fonte oficial: {FONTE[casa][0]} ({fonte_txt(casa)}). Valores reembolsados, como declarados; não indicam irregularidade. Compilação do Estrato em {data_br(col)}. '
                     f'Veja a <a href="{a["url"]}">página de {E(nome)}</a>, a <a href="/cota/">cota parlamentar</a> e a <a href="/cota/metodologia/">metodologia</a>.</p></article>')
            top_c = max(xa["cat"].items(), key=lambda x: x[1]) if xa["cat"] else ("—", 0)
            faqs = [(f"Quanto {nome} gastou da cota parlamentar desde 2023?", f"{brl(tot)} em {num(nl)} lançamentos, segundo {FONTE[casa][0]}."),
                    (f"Quanto {nome} gastou em {ua}?", f"{brl(xa['tot'])}{' até ' + MESES[ult_mes[casa]] if ua == ult[casa] else ''}. A média por {sing} com despesas no ano foi {brl(ma['med'])}."),
                    (f"Qual foi a maior categoria de gasto em {ua}?", f"{E(top_c[0])}, com {brl(top_c[1])} ({pct(top_c[1], xa['tot'])} do total do ano)."),
                    ("Quem são os principais fornecedores?", (f"O maior fornecedor pessoa jurídica desde 2023 é {E(nome_forn(ff[fs[0][0]]['nome']))}, com {brl(fs[0][1])}." if fs else "Não há fornecedores pessoa jurídica registrados.") + " Fornecedores pessoa física não são exibidos."),
                    (f"Qual a presença de {nome} nas votações nominais?", f"Voto registrado em {num(prs)} de {num(ptot)} votações nominais de plenário desde fevereiro de 2023 ({pct(prs, ptot)})."),
                    ("Gastar acima da média é irregular?", "Não necessariamente. O teto da cota varia por estado, e cada despesa é conferida pela casa. A página só descreve os valores declarados.")]
            ld = {"@type": "Dataset", "name": f"Cota parlamentar de {nome} ({cl}, desde 2023)", "description": f"Despesas reembolsadas pela {sig} a {nome} desde 2023, por ano, mês, categoria e fornecedor pessoa jurídica, com a média da casa.",
                  "url": S.BASE + u, "temporalCoverage": f"2023-01-01/{col or ua}", "spatialCoverage": "Brasil", "isBasedOn": FONTE[casa][1].format(a=ua), "license": "https://creativecommons.org/licenses/by/4.0/deed.pt-br",
                  "isAccessibleForFree": True, "inLanguage": "pt-BR", "creator": {"@id": S.BASE + "/#org"}, "variableMeasured": ["valor reembolsado", "categoria de despesa", "fornecedor (CNPJ)"],
                  "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{S.BASE}/dados/cota-{casa}.csv"}]}
            S.write(u, S.page(f"Cota parlamentar de {nome} ({part}-{uf}): gastos desde 2023", f"{nome} declarou {brl0(tot)} da {sig} desde 2023. Gastos por ano, mês, categoria e fornecedor, comparados à média da {cn_}.", u, body, faqs=faqs,
                                crumbs=[("Cota parlamentar", "/cota/"), (cl, f"/cota/#{casa}"), (nome, u)], jsonld=ld), familia=fam, lastmod=col)
            urls.append(u)
    # ---------- categorias ----------
    for casa in CASA:
        cn_, cl, kind, sing, sig, _ = CASA[casa]; P = D[casa]["parl"]; ff = D[casa]["forn"]
        for c in cats[casa]:
            u = curl(casa, c); ua = ult[casa]
            rows_a = [[a_, brl(M[casa][a_]["cat"][c]), num(sum(1 for p in P.values() if p["anos"].get(a_, {}).get("cat", {}).get(c))), brl(M[casa][a_]["cat"][c] / M[casa][a_]["n"]), pct(M[casa][a_]["cat"][c], M[casa][a_]["tot"])] for a_ in sorted(M[casa])]
            tot = sum(M[casa][a_]["cat"][c] for a_ in M[casa]); na = sum(1 for p in P.values() if any(x["cat"].get(c) for x in p["anos"].values()))
            if tot <= 0 and na == 0: continue
            fc = sorted(((k, f["cat"].get(c, 0)) for k, f in ff.items() if f["cat"].get(c)), key=lambda x: -x[1])[:20]
            body = (f'<article class="post"><h1>{E(c)}: gastos da {sig} {"na" if casa == "camara" else "no"} {cn_} desde 2023</h1><p class="snippet">{"Deputados" if casa == "camara" else "Senadores"} declararam <strong>{brl(tot)}</strong> na categoria “{E(c)}” desde 2023; '
                    f'{num(na)} {kind} tiveram ao menos um lançamento. Em {ua}, a média foi de {brl(M[casa][ua]["cat"][c] / M[casa][ua]["n"])} por {sing} com despesas no ano.</p>')
            body += "<h2>Por ano</h2>" + S.table(["Ano", "Total", f"{kind.capitalize()} com gasto", f"Média por {sing}", "% da cota no ano"], rows_a)
            if fc: body += "<h2>Fornecedores pessoa jurídica com maior valor na categoria</h2>" + S.table(["Fornecedor", "CNPJ", "Valor desde 2023"], [[flink(k, ff[k]["nome"]), fmt_cnpj(k), brl(v)] for k, v in fc], "Até 20 fornecedores (CNPJ); pessoas físicas não são exibidas")
            pf = sum(v for k, v in D[casa]["pf"].items() if k.split("|", 1)[1] == c)
            if pf: body += f'<p>Despesas com fornecedores pessoa física nesta categoria somam {brl(pf)} desde 2023 e aparecem só de forma agregada.</p>'
            li = []
            for pid, a in sorted(atuais[casa].items(), key=lambda x: slugify(x[1]["nome"])):
                v = P.get(pid, {}).get("anos", {}).get(ua, {}).get("cat", {}).get(c)
                if v: li.append(f'<li><a href="{S.cota_urls.get(f"{casa}:{pid}", a["url"])}">{E(a["nome"])}</a> <small>{E(a["partido"])}-{a["uf"]} · {brl(v)}</small></li>')
            if li: body += f'<h2>{kind.capitalize()} em exercício com gasto em {ua} (ordem alfabética)</h2><ul class="nlist">{"".join(li)}</ul>'
            body += f'<p class="src">Fonte oficial: {FONTE[casa][0]} ({fonte_txt(casa)}). Valores reembolsados; não indicam irregularidade. Compilação em {data_br(col)}. Veja a <a href="/cota/metodologia/">metodologia</a>.</p></article>'
            faqs = [(f"Quanto foi gasto em “{c}” desde 2023?", f"{brl(tot)}, somando os lançamentos de {num(na)} {kind}."),
                    (f"Qual a média por {sing} em {ua}?", f"{brl(M[casa][ua]['cat'][c] / M[casa][ua]['n'])}, considerando os {num(M[casa][ua]['n'])} {kind} com alguma despesa em {ua}."),
                    ("Que fatia da cota essa categoria representa?", f"Em {ua}, {pct(M[casa][ua]['cat'][c], M[casa][ua]['tot'])} do total declarado {'na' if casa == 'camara' else 'no'} {cn_}."),
                    ("Qual fornecedor recebeu mais nesta categoria?", (f"{E(nome_forn(ff[fc[0][0]]['nome']))} (CNPJ {fmt_cnpj(fc[0][0])}), com {brl(fc[0][1])} desde 2023." if fc else "Não há fornecedor pessoa jurídica registrado.")),
                    ("A lista de parlamentares é um ranking?", "Não. A lista está em ordem alfabética e mostra só o valor declarado no ano.")]
            S.write(u, S.page(f"{c}: gastos da {sig} {'na' if casa == 'camara' else 'no'} {cn_} desde 2023", f"Quanto {kind} gastaram em {c.lower()} com a {sig} desde 2023: total por ano, média por parlamentar e fornecedores.", u, body, faqs=faqs,
                                crumbs=[("Cota parlamentar", "/cota/"), (cl, f"/cota/#{casa}"), (c, u)], jsonld=S.itemlist([(nome_forn(ff[k]["nome"]), furl(k)) for k, _ in fc if k[:8] in pag_forn])), familia=fam, lastmod=col)
            urls.append(u)
    # ---------- fornecedores ----------
    nm_parl = {casa: {pid: (atuais[casa][pid]["nome"] if pid in atuais[casa] else p["nome"].title()) for pid, p in D[casa]["parl"].items()} for casa in CASA}
    for cn in sorted(pag_forn):
        g = FO[cn]; u = furl(cn); nome = nome_forn(g["nome"]); faqs_x = []
        cl_ = sorted(g["cnpjs"].items(), key=lambda x: -x[1]); princ = cl_[0][0]
        nparl = sum(len(f["parl"]) for f in g["casas"].values())
        body = f'<article class="post"><h1>{E(nome)}: pagamentos da cota parlamentar</h1><p class="snippet"><strong>{E(nome)}</strong> (CNPJ {fmt_cnpj(princ)}{f" e mais {len(cl_) - 1} estabelecimento(s) da mesma empresa" if len(cl_) > 1 else ""}) aparece em despesas da cota parlamentar que somam <strong>{brl(g["tot"])}</strong> desde 2023, em documentos de {num(nparl)} parlamentares.</p>'
        info = [("Fornecedor", E(nome)), ("Raiz do CNPJ", f"{cn[:2]}.{cn[2:5]}.{cn[5:8]}"), ("Estabelecimentos (CNPJ)", ", ".join(f"{fmt_cnpj(k)} ({brl(v)})" for k, v in cl_[:12]) + (f" e mais {len(cl_) - 12}" if len(cl_) > 12 else "")), ("Total desde 2023", brl(g["tot"]))]
        body += '<div class="tw"><table><tbody>' + "".join(f'<tr><th scope="row">{k}</th><td>{v}</td></tr>' for k, v in info) + "</tbody></table></div>"
        for casa, f in g["casas"].items():
            cn_, cl, kind, sing, sig, _ = CASA[casa]
            body += f"<h2>{cl}</h2>" + S.table(["Ano", "Valor"], [[a_, brl(v)] for a_, v in sorted(f["anos"].items())], f"Pagamentos da {sig} por ano")
            body += S.table(["Categoria", "Valor"], [[f'<a href="{curl(casa, c)}">{E(c)}</a>' if curl(casa, c) in S.urls else E(c), brl(v)] for c, v in sorted(f["cat"].items(), key=lambda x: -x[1])], "Por categoria de despesa")
            li = "".join((f'<li><a href="{S.cota_urls[f"{casa}:{pid}"]}">{E(nm_parl[casa][pid])}</a> <small>{brl(v)}</small></li>' if f"{casa}:{pid}" in S.cota_urls else f'<li>{E(nm_parl[casa][pid])} <small>{brl(v)}</small></li>')
                         for pid, v in sorted(f["parl"].items(), key=lambda x: slugify(nm_parl[casa][x[0]])))
            body += f'<h3>{kind.capitalize()} com despesas neste fornecedor (ordem alfabética)</h3><ul class="nlist">{li}</ul>'
            top_c = max(f["cat"].items(), key=lambda x: x[1])
            faqs_x.append((f"Quanto {kind} pagaram a {nome} com a cota?", f"{brl(f['tot'])} desde 2023, em {num(f['n'])} documentos de {num(len(f['parl']))} {kind}, principalmente em “{E(top_c[0])}”."))
        ct = collections.Counter()
        for f in g["casas"].values(): ct.update(f["cat"])
        cps = sorted(ct.items(), key=lambda x: -x[1])
        body += ("<h2>Resumo</h2><p>" + f"A principal categoria de despesa é “{E(cps[0][0])}”, com {pct(cps[0][1], g['tot'])} do valor. " + (f"Também aparecem {', '.join('“' + E(c) + '”' for c, _ in cps[1:4])}. " if len(cps) > 1 else "")
                 + f"Os pagamentos vêm de {' e '.join(CASA[c][1] for c in g['casas'])}, com média de {brl(g['tot'] / max(nparl, 1))} por parlamentar atendido. Os valores são reembolsos da cota a parlamentares; a empresa não é contratada diretamente pela casa legislativa.</p>")
        anos_t = collections.Counter()
        for f in g["casas"].values():
            for a_, v in f["anos"].items(): anos_t[a_] += v
        am = max(anos_t.items(), key=lambda x: x[1])
        body += f'<p class="src">Fonte oficial: {", ".join(FONTE[c][0] for c in g["casas"])}. Nome e CNPJ como registrados nos documentos; valores reembolsados não indicam irregularidade. Compilação em {data_br(col)}. Veja a <a href="/cota/metodologia/">metodologia</a>.</p></article>'
        faqs = [(f"Quanto {nome} recebeu da cota parlamentar desde 2023?", f"{brl(g['tot'])} em despesas declaradas por {num(nparl)} parlamentares."), (f"Qual é o CNPJ de {nome}?", f"{fmt_cnpj(princ)}" + (f", além de {len(cl_) - 1} outro(s) estabelecimento(s) com a mesma raiz" if len(cl_) > 1 else "") + ", como registrado nos documentos da cota.")] + faqs_x + \
               [(f"Em que ano o valor foi maior?", f"Em {am[0]}, com {brl(am[1])}."), ("O pagamento indica irregularidade?", "Não. A página reproduz despesas declaradas e reembolsadas pelas casas legislativas, sem juízo sobre elas.")]
        S.write(u, S.page(f"{nome} (CNPJ {fmt_cnpj(princ)}): pagamentos da cota parlamentar", f"{nome} recebeu {brl0(g['tot'])} em despesas da cota parlamentar desde 2023, de {nparl} parlamentares. Valores por ano, categoria e parlamentar.", u, body, faqs=faqs[:7],
                            crumbs=[("Cota parlamentar", "/cota/"), ("Fornecedores", "/cota/fornecedores/"), (nome, u)],
                            jsonld={"@type": "Organization", "name": nome, "taxID": fmt_cnpj(princ), "url": S.BASE + u}), familia=fam, lastmod=col)
        urls.append(u)
    # ---------- hub, metodologia, CSV ----------
    blocos = ""
    for casa in CASA:
        cn_, cl, kind, sing, sig, sig_l = CASA[casa]; ua = ult[casa]
        rows = [[a_, brl(M[casa][a_]["tot"]), num(M[casa][a_]["n"]), brl(M[casa][a_]["med"])] for a_ in sorted(M[casa])]
        cs = sorted(M[casa][ua]["cat"].items(), key=lambda x: -x[1]); mx = cs[0][1] if cs else 1
        li = "".join(f'<li><a href="{S.cota_urls[f"{casa}:{pid}"]}">{E(a["nome"])}</a> <small>{E(a["partido"])}-{a["uf"]}</small></li>' for pid, a in sorted(atuais[casa].items(), key=lambda x: slugify(x[1]["nome"])) if f"{casa}:{pid}" in S.cota_urls)
        blocos += (f'<h2 id="{casa}">{cl}: {sig}</h2>' + S.table(["Ano", "Total", f"{kind.capitalize()} com despesa", f"Média por {sing}"], rows, f"{sig_l} por ano")
                   + S.table(["Categoria", f"Total em {ua}", ""], [[f'<a href="{curl(casa, c)}">{E(c)}</a>', brl(v), _hbar(v, mx)] for c, v in cs], f"Categorias em {ua}")
                   + f'<details><summary>{kind.capitalize()} em exercício (ordem alfabética)</summary><ul class="nlist">{li}</ul></details>')
    fs = sorted(pag_forn, key=lambda k: -FO[k]["tot"])[:30]
    blocos += f'<h2 id="fornecedores">Fornecedores pessoa jurídica</h2><p>{num(len(pag_forn))} empresas (agrupadas pela raiz do CNPJ, que reúne matriz e filiais) têm página própria (ao menos {MIN_FORN_PARL} parlamentares atendidos, ou {brl0(MIN_FORN_TOT)} recebidos de pelo menos 3 parlamentares, desde 2023). As 30 de maior valor somado:</p>' + \
              S.table(["Fornecedor", "CNPJ", "Total desde 2023"], [[f'<a href="/cota/fornecedores/{k}/">{E(nome_forn(FO[k]["nome"]))}</a>', fmt_cnpj(max(FO[k]["cnpjs"], key=FO[k]["cnpjs"].get)), brl(FO[k]["tot"])] for k in fs])
    # hub com TODOS os fornecedores PJ com página (alcançabilidade: sem ele as páginas de fornecedor ficam órfãs); ordem alfabética, sem ranking
    fa_ = sorted(pag_forn, key=lambda k: slugify(nome_forn(FO[k]["nome"])))
    S.write("/cota/fornecedores/", S.page("Fornecedores da cota parlamentar: lista de empresas", f"{num(len(fa_))} empresas fornecedoras da cota parlamentar (CEAP e CEAPS) com página própria, em ordem alfabética, com CNPJ e total recebido desde 2023.", "/cota/fornecedores/",
        f'<section class="blk"><h1>Fornecedores pessoa jurídica da cota parlamentar</h1><p class="snippet">{num(len(fa_))} empresas, agrupadas pela raiz do CNPJ, têm página própria por terem atendido ao menos {MIN_FORN_PARL} parlamentares desde 2023. A lista está em ordem alfabética e não é ranking.</p>'
        + S.table(["Fornecedor", "CNPJ", "Total desde 2023"], [[f'<a href="/cota/fornecedores/{k}/">{E(nome_forn(FO[k]["nome"]))}</a>', fmt_cnpj(max(FO[k]["cnpjs"], key=FO[k]["cnpjs"].get)), brl(FO[k]["tot"])] for k in fa_], "Fornecedores PJ em ordem alfabética")
        + '<p>Voltar à <a href="/cota/">cota parlamentar</a>. Fornecedores pessoa física não são exibidos; veja a <a href="/cota/metodologia/">metodologia</a>.</p></section>',
        crumbs=[("Cota parlamentar", "/cota/"), ("Fornecedores", "/cota/fornecedores/")]), familia="paginas", lastmod=col, idx=False, faq_min=0); urls.append("/cota/fornecedores/")
    blocos += f'<p>Veja a <a href="/cota/fornecedores/">lista completa das {num(len(fa_))} empresas fornecedoras</a>, em ordem alfabética.</p>'
    tc = {casa: sum(M[casa][a]["tot"] for a in M[casa]) for casa in CASA}
    body = (f'<section class="blk"><h1>Cota parlamentar: gastos de deputados e senadores desde 2023</h1><p class="snippet">Deputados federais declararam <strong>{brl(tc["camara"])}</strong> em despesas da CEAP e senadores, <strong>{brl(tc["senado"])}</strong> da CEAPS, de janeiro de 2023 até {MESES[ult_mes["camara"]]} de {ult["camara"]}. '
            f'Cada {"deputado e senador em exercício"} tem uma página com gastos por ano, mês, categoria e fornecedor, comparados à média da casa.</p>{blocos}'
            '<h2>Como ler</h2><p>A cota reembolsa despesas ligadas ao mandato, como passagens, divulgação, combustível e manutenção de escritório. O teto mensal varia por estado. Os valores são os reembolsados, como declarados pelas casas; o Estrato não faz juízo sobre eles e não publica rankings. Fornecedores pessoa física não são exibidos.</p>'
            f'<p>Baixe os dados em <a href="/dados/#cota">CSV</a> e veja a <a href="/cota/metodologia/">metodologia</a>.</p></section>')
    faqs = [("Quanto os deputados gastaram da cota desde 2023?", f"{brl(tc['camara'])}, segundo os arquivos anuais da Câmara."), ("Quanto os senadores gastaram da cota desde 2023?", f"{brl(tc['senado'])}, segundo a API de dados administrativos do Senado."),
            (f"Qual foi a média por deputado em {ult['camara']}?", f"{brl(M['camara'][ult['camara']]['med'])} até {MESES[ult_mes['camara']]}, entre {num(M['camara'][ult['camara']]['n'])} deputados com despesa."),
            (f"Qual foi a média por senador em {ult['senado']}?", f"{brl(M['senado'][ult['senado']]['med'])}, entre {num(M['senado'][ult['senado']]['n'])} senadores com despesa."),
            ("Por que fornecedores pessoa física não aparecem?", "Por privacidade. Despesas com CPF entram só nos totais agregados."), ("Os dados são atualizados?", "Sim, uma vez por dia, a partir dos arquivos oficiais.")]
    S.write("/cota/", S.page("Cota parlamentar de deputados e senadores desde 2023", f"Gastos da cota parlamentar (CEAP e CEAPS) desde 2023: {brl0(tc['camara'])} na Câmara e {brl0(tc['senado'])} no Senado, por parlamentar, categoria e fornecedor.", "/cota/", body, faqs=faqs,
                             crumbs=[("Cota parlamentar", "/cota/")], jsonld={"@type": "Dataset", "name": "Cota parlamentar da Câmara e do Senado desde 2023", "description": "Despesas reembolsadas da CEAP e da CEAPS por parlamentar, categoria e fornecedor pessoa jurídica.", "url": S.BASE + "/cota/",
                             "license": "https://creativecommons.org/licenses/by/4.0/deed.pt-br", "isAccessibleForFree": True, "creator": {"@id": S.BASE + "/#org"}, "inLanguage": "pt-BR", "temporalCoverage": f"2023-01-01/{col}",
                             "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{S.BASE}/dados/cota-{c}.csv"} for c in CASA]}), familia="paginas", lastmod=col)
    urls.append("/cota/")
    body = ('<article class="post"><h1>Metodologia da cota parlamentar</h1><p class="snippet">Como o Estrato coleta e organiza as despesas da cota parlamentar da Câmara (CEAP) e do Senado (CEAPS) desde 2023.</p>'
            '<h2>Fontes</h2><p>Câmara: arquivo anual oficial da cota parlamentar (camara.leg.br/cotas), atualizado diariamente. Senado: API pública de dados administrativos (adm.senado.gov.br/adm-dadosabertos). Nenhuma das fontes exige cadastro ou chave. A coleta roda uma vez por dia e baixa de novo só os arquivos que mudaram.</p>'
            '<h2>Valores</h2><p>Câmara: valor líquido de cada documento (já descontadas glosas). Senado: valor reembolsado. Lançamentos de lideranças e órgãos da Câmara, sem deputado associado, ficam de fora.</p>'
            '<h2>Média da casa</h2><p>Para cada ano, a média é o total declarado dividido pelo número de parlamentares com pelo menos um lançamento no ano. A média por categoria usa o mesmo divisor. No ano corrente, a comparação vale até o último mês com lançamentos.</p>'
            '<h2>Fornecedores</h2><p>Só fornecedores pessoa jurídica (CNPJ de 14 dígitos) são exibidos. Fornecedores pessoa física (CPF) entram apenas em totais agregados. Empresas individuais cujo nome registrado contém número de CPF não ganham página e o número é retirado do nome. Nomes de passageiros, trechos e números de documento não são publicados. '
            f'Os fornecedores são agrupados pela raiz do CNPJ (8 primeiros dígitos), que reúne matriz e filiais. Ganham página as empresas com ao menos {MIN_FORN_PARL} parlamentares atendidos, ou {brl0(MIN_FORN_TOT)} recebidos de pelo menos 3 parlamentares, desde 2023.</p>'
            '<h2>Presença</h2><p>A presença é o número de votações nominais de plenário com voto registrado do parlamentar, sobre o total desde fevereiro de 2023 (veja o <a href="/votacoes/metodologia/">placar de votações</a>). Não inclui sessões sem votação nominal nem comissões.</p>'
            '<h2>Limites</h2><p>Valores declarados não indicam irregularidade. O teto da cota varia por estado, então diferenças em relação à média são esperadas. Durante o período eleitoral, as listas de parlamentares ficam em ordem alfabética, sem ranking.</p>'
            '<p>Erros podem ser comunicados pela página de <a href="/correcoes/">correções</a>.</p></article>')
    faqs = [("De onde vêm os dados da cota?", "Dos arquivos oficiais públicos da Câmara e da API de dados administrativos do Senado."), ("Como é calculada a média?", "Total do ano dividido pelo número de parlamentares com ao menos um lançamento no ano."),
            ("Por que não aparecem pessoas físicas?", "Por privacidade: despesas com CPF entram só em totais agregados."), ("Como é medida a presença?", "Pelos votos registrados nas votações nominais de plenário desde fevereiro de 2023."), ("Há ranking de parlamentares?", "Não. As listas estão em ordem alfabética.")]
    S.write("/cota/metodologia/", S.page("Metodologia da cota parlamentar (CEAP e CEAPS)", "Fontes, cálculo da média, regras de privacidade de fornecedores e medida de presença usadas nas páginas de cota parlamentar do Estrato.", "/cota/metodologia/", body, faqs=faqs,
                                         crumbs=[("Cota parlamentar", "/cota/"), ("Metodologia", "/cota/metodologia/")]), familia="paginas", lastmod=col)
    urls.append("/cota/metodologia/")
    out = S.OUT / "dados"; out.mkdir(parents=True, exist_ok=True); sets = []
    for casa in CASA:
        n = 0
        with (out / f"cota-{casa}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(["casa", "id_parlamentar", "nome", "ano", "categoria", "valor"])
            for pid, p in D[casa]["parl"].items():
                for a_, x in sorted(p["anos"].items()):
                    for c, v in sorted(x["cat"].items()): w.writerow([casa, pid, nm_parl[casa][pid], a_, c, f"{v:.2f}"]); n += 1
        sets.append((f"cota-{casa}", f"Cota parlamentar por categoria: {CASA[casa][1]}", "Uma linha por parlamentar, ano e categoria de despesa desde 2023.", n))
        n = 0
        with (out / f"cota-fornecedores-{casa}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(["casa", "cnpj", "fornecedor", "id_parlamentar", "parlamentar", "valor"])
            for cn, fo in D[casa]["forn"].items():
                if tem_cpf(fo["nome"]): continue
                for pid, v in fo["parl"].items(): w.writerow([casa, fmt_cnpj(cn), nome_forn(fo["nome"]), pid, nm_parl[casa][pid], f"{v:.2f}"]); n += 1
        sets.append((f"cota-fornecedores-{casa}", f"Cota parlamentar por fornecedor PJ: {CASA[casa][1]}", "Uma linha por fornecedor pessoa jurídica (CNPJ) e parlamentar desde 2023.", n))
    S.cota_meta = col; S.cota_sets = sets; S.cota_stats = {"forn_pag": len(pag_forn), "tc": tc}
    return {"urls": urls}


def link_parl(S, casa, pid, slug, nome):
    """Parágrafo com link para a página de cota do parlamentar (usado em parlamentares.py, que roda antes)."""
    D, _ = carregar(S); p = D[casa]["parl"].get(str(pid))
    if not p: return ""
    tot = sum(x["tot"] for x in p["anos"].values()); u = f"/cota/{CASA[casa][2]}/{slug}/"
    return f'<p>Desde 2023, {E(nome)} declarou {brl(tot)} em despesas da {CASA[casa][4]}. Veja a <a href="{u}">cota parlamentar por ano, categoria e fornecedor</a>.</p>'
