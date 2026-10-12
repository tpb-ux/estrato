"""Deputados federais e senadores em exercício + hub de cota parlamentar (CEAP). Dados: APIs de Dados Abertos da Câmara e do Senado."""
import json, statistics as st
from core.site import E, slugify
from . import votacoes as _vot
from .dados import UF, PREP, MESES, brl, brl0, num, pct, data_br, idade, load

def foto(S, kind, i, alt, w=120, h=160):
    p = S.ROOT / "static/img/parl" / f"{kind}-{i}.webp"
    return f'<img src="/static/img/parl/{kind}-{i}.webp" width="{w}" height="{h}" alt="{E(alt)}" loading="lazy" decoding="async">' if p.exists() else ""

def plist(S, items, kind):
    return '<ul class="plist">' + "".join(f'<li><a href="{x["url"]}">{foto(S, kind, x["id"], x["nome"], 36, 48)}<span><strong>{E(x["nome"])}</strong><small>{E(x["partido"])}-{x["uf"]}</small></span></a></li>' for x in items) + "</ul>"

def build(S):
    WD = json.loads((S.ROOT / "data/wikidata_deputados.json").read_text(encoding="utf-8"))["itens"] if (S.ROOT / "data/wikidata_deputados.json").exists() else {}
    D = load(S, "deputados.json"); SN = load(S, "senadores.json"); C = load(S, "ceap.json")
    deps = [d for d in D["deputados"]]; sens = SN["senadores"]
    col_d, col_s = D["coletado_em"][:10], SN["coletado_em"][:10]
    ano, mes = C["ano"], C["ultimo_mes"]; ceap = C["deputados"]
    usados = set()
    for d in deps:
        s = slugify(d["nome"]); s = s if s not in usados else f"{s}-{d['uf'].lower()}"; usados.add(s)
        d["slug"], d["url"] = s, f"/deputados/{s}/"
        d["c"] = ceap.get(str(d["id"]), {"total": 0, "lancamentos": 0, "por_categoria": {}, "por_mes": {}})
    for x in sens:
        s = slugify(x["nome"]); x["slug"], x["url"] = s, f"/senadores/{s}/"
    S.parl = {"deps": deps, "sens": sens}
    by_uf, by_p = {}, {}
    for d in deps: by_uf.setdefault(d["uf"], []).append(d); by_p.setdefault(d["partido"], []).append(d)
    tot = lambda d: d["c"]["total"]
    rank_all = sorted(deps, key=tot, reverse=True); pos_all = {d["id"]: i + 1 for i, d in enumerate(rank_all)}
    med_all = st.median([tot(d) for d in deps]) if deps else 0
    fonte_d = f'<p class="src">Fonte: Câmara dos Deputados, <a href="https://dadosabertos.camara.leg.br/">API Dados Abertos</a> (cadastro e comissões, coleta em {data_br(col_d)}) e <a href="{E(C["url"])}">arquivo oficial da cota parlamentar {ano}</a> (lançamentos até {MESES[mes]} de {ano}). Valores líquidos declarados e reembolsados; não indicam irregularidade.</p>'
    cmo = [("Cota parlamentar (CEAP)", "/glossario/cota-parlamentar/"), ("Legislatura", "/glossario/legislatura/"), ("Bancada", "/glossario/bancada/"), ("Votação nominal", "/glossario/votacao-nominal/")]
    gl = '<div class="relbox"><h2>Entenda</h2><ul>' + "".join(f'<li><a href="{u}">{E(n)}</a></li>' for n, u in cmo) + "</ul></div>"
    # ---------- deputado ----------
    for d in deps:
        c = d["c"]; uf = d["uf"]; pares = by_uf[uf]; dep_t = "deputada" if d.get("sexo") == "F" else "deputado"
        ru = sorted(pares, key=tot, reverse=True); pu = [x["id"] for x in ru].index(d["id"]) + 1
        medu = st.median([tot(x) for x in pares]); part = by_p[d["partido"]]
        ida = idade(d.get("nascimento"))
        lead = (f'<p class="snippet"><strong>{E(d["nome"])}</strong> é {dep_t} federal pelo <a href="/partidos/{slugify(d["partido"])}/">{E(d["partido"])}</a> '
                f'{PREP[uf]} <a href="/deputados/uf/{uf.lower()}/">{UF[uf]}</a>, em {E((d.get("situacao") or "exercício").lower())} na 57ª legislatura (2023–2027). ')
        if c["total"] > 0:
            top = next(iter(c["por_categoria"].items()))
            lead += (f'De janeiro a {MESES[mes]} de {ano}, declarou {brl(c["total"])} em despesas da cota parlamentar, em {num(c["lancamentos"])} lançamentos. '
                     f'O valor é o {pu}º entre os {len(pares)} deputados {PREP[uf]} {UF[uf]} e o {pos_all[d["id"]]}º entre os {len(deps)} da Câmara. A maior categoria foi “{E(top[0].lower())}”, com {brl(top[1])}.</p>')
        else: lead += f'Não há despesas da cota parlamentar registradas em {ano} até {MESES[mes]} no arquivo oficial da Câmara.</p>'
        info = [("Nome civil", E((d.get("nome_civil") or "").title())), ("Partido", f'<a href="/partidos/{slugify(d["partido"])}/">{E(d["partido"])}</a>'), ("Estado", f'<a href="/deputados/uf/{uf.lower()}/">{UF[uf]}</a>'),
                ("Condição", E(d.get("condicao") or "")), ("Nascimento", f'{data_br(d.get("nascimento"))}{f" ({ida} anos)" if ida else ""}{", " + E(d["municipio_nascimento"]) + "-" + E(d.get("uf_nascimento") or "") if d.get("municipio_nascimento") else ""}'),
                ("Escolaridade", E(d.get("escolaridade") or "")), ("Gabinete", (f'Prédio {E(d["gabinete"]["predio"])}, sala {E(d["gabinete"]["sala"])}' if d["gabinete"].get("sala") else "") + (f', tel. (61) {E(d["gabinete"]["telefone"])}' if d["gabinete"].get("telefone") else "")),
                ("E-mail oficial", E(d.get("email") or ""))]
        info = [(k, v) for k, v in info if v and v.strip(" ,()")]
        prof = f'<div class="prof">{foto(S, "dep", d["id"], d["nome"])}<div class="tw"><table><tbody>' + "".join(f"<tr><th scope=\"row\">{k}</th><td>{v}</td></tr>" for k, v in info) + "</tbody></table></div></div>"
        if (S.ROOT / f"static/img/parl/dep-{d['id']}.webp").exists(): prof += '<p class="src">Foto oficial: Arquivo/Câmara dos Deputados (<a href="https://www.camara.leg.br/internet/bancoimagem/" target="_blank" rel="noopener">uso livre com crédito, CC BY</a>).</p>'
        body = f'<article class="post"><h1>{E(d["nome"])} ({E(d["partido"])}-{uf}): {dep_t} federal</h1>{lead}{prof}'
        if c["total"] > 0:
            cats = list(c["por_categoria"].items())
            body += (f'<h2>Cota parlamentar em {ano}</h2><div class="stats"><div class="stat"><b>{brl0(c["total"])}</b><span>total declarado até {MESES[mes]}</span></div>'
                     f'<div class="stat"><b>{brl0(c["total"] / max(1, len(c["por_mes"])))}</b><span>média por mês com lançamento</span></div><div class="stat"><b>{brl0(medu)}</b><span>mediana {PREP[uf]} {uf}</span></div>'
                     f'<div class="stat"><b>{brl0(med_all)}</b><span>mediana da Câmara</span></div></div>'
                     + S.table(["Categoria", "Valor", "Participação"], [[E(k), f'<span class="ndata">{brl(v)}</span>', pct(v, c["total"])] for k, v in cats], f"Despesas por categoria, {ano}")
                     + S.table(["Mês", "Valor"], [[MESES[int(m)].capitalize(), f'<span class="ndata">{brl(v)}</span>'] for m, v in c["por_mes"].items()], f"Despesas por mês, {ano}"))
            dif = c["total"] - medu
            body += f'<p>Em relação à mediana dos deputados {PREP[uf]} {UF[uf]} ({brl(medu)}), o total declarado está {brl(abs(dif))} {"acima" if dif >= 0 else "abaixo"}. O teto da cota varia por estado; veja a <a href="/deputados/cota-parlamentar/">comparação de todos os deputados</a>.</p>'
        body += _vot.bloco_parlamentar(S, "camara", d["id"], d["nome"])
        if d["orgaos"]:
            body += f'<h2>Comissões e órgãos ({len(d["orgaos"])})</h2>' + S.table(["Órgão", "Sigla", "Cargo"], [[E(o["nome"] or ""), E(o["sigla"] or ""), E(o["cargo"] or "")] for o in d["orgaos"]])
        viz = [x for x in part if x["uf"] == uf and x is not d][:8] or [x for x in pares if x is not d][:8]
        body += f'<h2>Outros deputados {PREP[uf]} {UF[uf]}{" do " + E(d["partido"]) if viz and viz[0]["partido"] == d["partido"] else ""}</h2>{plist(S, viz, "dep")}' + gl + fonte_d + "</article>"
        faqs = [(f"De qual partido é {d['nome']}?", f"{E(d['nome'])} é filiado ao {E(d['partido'])}, segundo o cadastro da Câmara dos Deputados coletado em {data_br(col_d)}."),
                (f"Por qual estado {d['nome']} foi eleito?", f"Pelo estado {PREP[uf]} {UF[uf]}, que tem {len(pares)} deputados federais em exercício."),
                (f"Quanto {d['nome']} gastou da cota parlamentar em {ano}?", (f"{brl(c['total'])} até {MESES[mes]}, em {num(c['lancamentos'])} lançamentos, segundo o arquivo oficial da Câmara." if c["total"] > 0 else f"Não há lançamentos registrados em {ano} até {MESES[mes]} no arquivo oficial da Câmara.")),
                (f"Em quais comissões {d['nome']} atua?", (", ".join(E(o["sigla"] or o["nome"]) for o in d["orgaos"][:8]) + "." if d["orgaos"] else "O cadastro oficial não lista comissões ativas na data da coleta.")),
                (f"Como entrar em contato com {d['nome']}?", (f"Pelo e-mail oficial {E(d['email'])}" if d.get("email") else "Pelos canais oficiais da Câmara") + (f" ou pelo telefone do gabinete, (61) {E(d['gabinete']['telefone'])}." if d["gabinete"].get("telefone") else "."))]
        ld = {"@type": "Person", "name": d["nome"], "jobTitle": f"{dep_t.capitalize()} federal", "affiliation": {"@type": "Organization", "name": d["partido"]}, "memberOf": {"@type": "GovernmentOrganization", "name": "Câmara dos Deputados"},
              "url": S.BASE + d["url"], **({"image": S.BASE + f"/static/img/parl/dep-{d['id']}.webp"} if (S.ROOT / f"static/img/parl/dep-{d['id']}.webp").exists() else {}), "sameAs": [f"https://www.camara.leg.br/deputados/{d['id']}"] + ([WD[str(d['id'])]] if str(d['id']) in WD else [])}
        S.write(d["url"], S.page(f"{d['nome']} ({d['partido']}-{uf}): perfil e cota parlamentar", f"{d['nome']}, {dep_t} federal ({d['partido']}-{uf}): dados oficiais, comissões e gastos da cota parlamentar em {ano}.",
                                 d["url"], body, faqs=faqs, crumbs=[("Deputados", "/deputados/"), (UF[uf], f"/deputados/uf/{uf.lower()}/"), (d["nome"], d["url"])], jsonld=ld, og_img=S.BASE + f"/static/img/parl/dep-{d['id']}.webp"),
                familia="deputados", lastmod=col_d, image=f"/static/img/parl/dep-{d['id']}.webp")
    # ---------- deputados por UF ----------
    for uf, ps in sorted(by_uf.items()):
        ps = sorted(ps, key=lambda x: slugify(x["nome"])); pp = {}
        for x in ps: pp[x["partido"]] = pp.get(x["partido"], 0) + 1
        tu = sum(tot(x) for x in ps); u = f"/deputados/uf/{uf.lower()}/"
        sens_uf = [x for x in sens if x["uf"] == uf]
        body = (f'<section class="blk"><h1>Deputados federais {PREP[uf]} {UF[uf]}</h1><p class="snippet">{UF[uf]} tem <strong>{len(ps)} deputados federais</strong> em exercício, de {len(pp)} partidos. '
                f'A bancada declarou {brl(tu)} em cota parlamentar de janeiro a {MESES[mes]} de {ano}, segundo a Câmara.</p>'
                + S.table(["Partido", "Deputados", "% da bancada"], [[f'<a href="/partidos/{slugify(p)}/">{E(p)}</a>', str(n), pct(n, len(ps))] for p, n in sorted(pp.items(), key=lambda x: (-x[1], x[0]))], "Deputados por partido")
                + f'<h2>Como é definida a bancada</h2><p>O número de deputados de cada estado é proporcional à população, com mínimo de 8 e máximo de 70 cadeiras, conforme o art. 45 da Constituição. {UF[uf]} elege {len(ps)} deputados federais e, como todos os estados, 3 senadores. Os deputados são eleitos pelo sistema proporcional, a partir do <a href="/glossario/quociente-eleitoral/">quociente eleitoral</a>, e os senadores pelo sistema majoritário.</p>'
                + f"<h2>Lista de deputados</h2>{plist(S, ps, 'dep')}"
                + S.table(["Deputado", "Partido", f"Cota {ano}"], [[f'<a href="{x["url"]}">{E(x["nome"])}</a>', E(x["partido"]), f'<span class="ndata">{brl(tot(x))}</span>'] for x in sorted(ps, key=tot, reverse=True)], f"Cota parlamentar declarada, {ano}")
                + (f'<h2>Senadores {PREP[uf]} {UF[uf]}</h2>{plist(S, sens_uf, "sen")}' if sens_uf else "") + fonte_d + "</section>")
        big = max(pp.items(), key=lambda x: x[1])
        faqs = [(f"Quantos deputados federais {UF[uf]} tem?", f"{len(ps)} deputados em exercício na data da coleta ({data_br(col_d)})."),
                (f"Qual partido tem a maior bancada {PREP[uf]} {UF[uf]}?", f"O {E(big[0])}, com {big[1]} deputados."),
                (f"Quanto a bancada {PREP[uf]} {UF[uf]} gastou de cota parlamentar?", f"{brl(tu)} de janeiro a {MESES[mes]} de {ano}, somando os valores líquidos declarados."),
                ("Por que o número de deputados varia entre estados?", "A Constituição define o número proporcional à população, com mínimo de 8 e máximo de 70 por estado (art. 45)."),
                (f"Quem são os senadores {PREP[uf]} {UF[uf]}?", (", ".join(E(x["nome"]) for x in sens_uf) + "." if sens_uf else "Veja a lista de senadores."))]
        S.write(u, S.page(f"Deputados federais {PREP[uf]} {UF[uf]} ({uf}): lista e partidos", f"Os {len(ps)} deputados federais {PREP[uf]} {UF[uf]} em exercício: partidos, perfis e cota parlamentar de {ano}, com dados oficiais da Câmara.",
                          u, body, faqs=faqs, crumbs=[("Deputados", "/deputados/"), (UF[uf], u)], jsonld=S.itemlist([(x["nome"], x["url"]) for x in ps])), familia="deputados", lastmod=col_d)
    # ---------- hub deputados ----------
    pp = {}
    for d in deps: pp[d["partido"]] = pp.get(d["partido"], 0) + 1
    body = (f'<section class="blk"><h1>Deputados federais em exercício</h1><p class="snippet">A Câmara tem <strong>{len(deps)} deputados federais</strong> em exercício na data da coleta ({data_br(col_d)}), de {len(pp)} partidos. '
            f'Cada página traz partido, estado, comissões e os gastos da cota parlamentar de {ano}.</p><h2 id="uf">Por estado</h2><div class="chips">'
            + "".join(f'<a class="chip" href="/deputados/uf/{uf.lower()}/">{UF[uf]} ({len(by_uf[uf])})</a>' for uf in sorted(by_uf, key=lambda u: UF[u])) + "</div>"
            + S.table(["Partido", "Deputados"], [[f'<a href="/partidos/{slugify(p)}/">{E(p)}</a>', str(n)] for p, n in sorted(pp.items(), key=lambda x: (-x[1], x[0]))], "Bancadas na Câmara")
            + f'<h2>Todos os deputados (A–Z)</h2>{plist(S, sorted(deps, key=lambda x: slugify(x["nome"])), "dep")}' + fonte_d + "</section>")
    faqs = [("Quantos deputados federais existem?", "A Câmara tem 513 cadeiras. O número em exercício pode variar momentaneamente com licenças e posse de suplentes."),
            ("Qual partido tem a maior bancada na Câmara?", f"Na data da coleta, o {E(max(pp.items(), key=lambda x: x[1])[0])}, com {max(pp.values())} deputados."),
            ("Quanto dura o mandato de deputado federal?", "Quatro anos, o período de uma legislatura. A atual, a 57ª, vai até 31 de janeiro de 2027."),
            ("De onde vêm os dados?", "Da API de Dados Abertos da Câmara e do arquivo oficial da cota parlamentar, atualizados diariamente."),
            ("Os deputados eleitos em 2026 já aparecem?", "Ainda não. Eles tomam posse em fevereiro de 2027, e as páginas serão atualizadas a partir dos dados oficiais da Câmara.")]
    S.write("/deputados/", S.page("Deputados federais em exercício: lista por estado e partido", f"Lista dos {len(deps)} deputados federais em exercício, por estado e partido, com perfis e cota parlamentar a partir de dados oficiais da Câmara.", "/deputados/", body,
                                  faqs=faqs, crumbs=[("Deputados", "/deputados/")], jsonld=S.itemlist([(d["nome"], d["url"]) for d in deps])), familia="deputados", lastmod=col_d)
    # ---------- CEAP hub ----------
    tt = sum(tot(d) for d in deps); cats = {}
    for d in deps:
        for k, v in d["c"]["por_categoria"].items(): cats[k] = cats.get(k, 0) + v
    ufs = sorted(by_uf, key=lambda u: -sum(tot(x) for x in by_uf[u]) / len(by_uf[u]))
    body = (f'<article class="post"><h1>Cota parlamentar (CEAP) dos deputados em {ano}</h1><p class="snippet">De janeiro a {MESES[mes]} de {ano}, os {len(deps)} deputados em exercício declararam <strong>{brl(tt)}</strong> '
            f'em despesas da Cota para o Exercício da Atividade Parlamentar. A mediana por deputado foi de {brl(med_all)}, segundo o arquivo oficial da Câmara.</p>'
            '<p>A cota reembolsa despesas do mandato mediante nota fiscal, com teto mensal que varia por estado. Os valores abaixo são despesas declaradas; a regularidade é verificada pela Câmara e pelos órgãos de controle. Saiba mais no <a href="/glossario/cota-parlamentar/">glossário</a>.</p>'
            + S.table(["Categoria", "Total", "Participação"], [[E(k), f'<span class="ndata">{brl(v)}</span>', pct(v, tt)] for k, v in sorted(cats.items(), key=lambda x: -x[1])], f"Despesas por categoria, {ano}")
            + S.table(["Estado", "Deputados", "Total", "Média por deputado"], [[f'<a href="/deputados/uf/{u.lower()}/">{UF[u]}</a>', str(len(by_uf[u])), f'<span class="ndata">{brl(sum(tot(x) for x in by_uf[u]))}</span>', f'<span class="ndata">{brl(sum(tot(x) for x in by_uf[u]) / len(by_uf[u]))}</span>'] for u in ufs], "Por estado (ordem: média por deputado)")
            + S.table(["Deputado", "Partido-UF", "Total"], [[f'<a href="{d["url"]}">{E(d["nome"])}</a>', f'{E(d["partido"])}-{d["uf"]}', f'<span class="ndata">{brl(tot(d))}</span>'] for d in rank_all], f"Todos os deputados, do maior ao menor valor declarado, {ano}")
            + fonte_d + "</article>")
    faqs = [(f"Quanto os deputados gastaram de cota parlamentar em {ano}?", f"{brl(tt)} de janeiro a {MESES[mes]}, somando os valores líquidos declarados por {len(deps)} deputados em exercício."),
            ("Qual é a principal despesa da cota?", f"“{E(max(cats.items(), key=lambda x: x[1])[0])}”, com {brl(max(cats.values()))} no ano." if cats else "Ainda não há lançamentos no ano."),
            ("Por que o teto da cota varia por estado?", "Porque inclui passagens aéreas entre o estado de origem e Brasília, que custam mais para estados mais distantes."),
            ("Valor alto de cota significa irregularidade?", "Não. A cota é um direito previsto em ato da Mesa da Câmara. Cada despesa exige nota fiscal, e a análise de regularidade cabe à Câmara e aos órgãos de controle."),
            ("Com que frequência os dados são atualizados?", "O arquivo oficial da Câmara é atualizado diariamente, e o Estrato o processa uma vez por dia. Lançamentos podem entrar com atraso.")]
    S.write("/deputados/cota-parlamentar/", S.page(f"Cota parlamentar {ano}: gastos dos deputados por categoria e estado", f"Gastos da cota parlamentar (CEAP) dos deputados em {ano}: total, categorias, estados e ranking, com dados oficiais da Câmara.",
                                                   "/deputados/cota-parlamentar/", body, faqs=faqs, crumbs=[("Deputados", "/deputados/"), ("Cota parlamentar", "/deputados/cota-parlamentar/")],
                                                   jsonld={"@type": "Dataset", "name": f"Cota parlamentar dos deputados federais {ano}", "creator": {"@type": "GovernmentOrganization", "name": "Câmara dos Deputados"}, "url": S.BASE + "/deputados/cota-parlamentar/", "isBasedOn": C["url"], "temporalCoverage": f"{ano}-01/{ano}-{mes:02d}", "license": "https://dadosabertos.camara.leg.br/"}), familia="deputados", lastmod=C["coletado_em"][:10])
    # ---------- senadores ----------
    sby = {}
    for x in sens: sby.setdefault(x["uf"], []).append(x)
    fonte_s = f'<p class="src">Fonte: Senado Federal, <a href="https://legis.senado.leg.br/dadosabertos/">Dados Abertos</a> (lista de parlamentares em exercício, cadastro e comissões, coleta em {data_br(col_s)}).</p>'
    sp0 = {}
    for y in sens: sp0[y["partido"]] = sp0.get(y["partido"], 0) + 1
    for x in sens:
        uf = x["uf"]; sen_t = "senadora" if (x.get("sexo") or "").startswith("F") else "senador"; ida = idade(x.get("nascimento"))
        fim = (x.get("mandato_fim") or "")[:4]; ini = (x.get("mandato_inicio") or "")[:4]
        colegas = [y for y in sby[uf] if y is not x]
        lead = (f'<p class="snippet"><strong>{E(x["nome"])}</strong> é {sen_t} pelo <a href="/partidos/{slugify(x["partido"])}/">{E(x["partido"])}</a> {PREP[uf]} {UF[uf]}'
                + (f', com mandato de {ini} a {fim}' if ini and fim else "") + f'. Está em exercício como {E((x.get("participacao") or "titular").lower())}, segundo o Senado Federal.</p>')
        info = [("Nome civil", E(x.get("nome_civil") or "")), ("Partido", f'<a href="/partidos/{slugify(x["partido"])}/">{E(x["partido"])}</a>'), ("Estado", UF[uf]), ("Participação", E(x.get("participacao") or "")),
                ("Mandato", f"{data_br(x.get('mandato_inicio'))} a {data_br(x.get('mandato_fim'))}" if x.get("mandato_fim") else ""),
                ("Nascimento", f'{data_br(x.get("nascimento"))}{f" ({ida} anos)" if ida else ""}{", " + E(x["naturalidade"]) + "-" + E(x.get("uf_naturalidade") or "") if x.get("naturalidade") else ""}'), ("E-mail oficial", E(x.get("email") or ""))]
        info = [(k, v) for k, v in info if v and v.strip(" ,()a")]
        body = (f'<article class="post"><h1>{E(x["nome"])} ({E(x["partido"])}-{uf}): {sen_t}</h1>{lead}<div class="prof">{foto(S, "sen", x["id"], x["nome"])}<div class="tw"><table><tbody>'
                + "".join(f"<tr><th scope=\"row\">{k}</th><td>{v}</td></tr>" for k, v in info) + "</tbody></table></div></div>"
                + ('<p class="src">Foto oficial: Agência Senado (<a href="https://www12.senado.leg.br/noticias/politica-de-uso" target="_blank" rel="noopener">reprodução livre com crédito</a>).</p>' if (S.ROOT / f"static/img/parl/sen-{x['id']}.webp").exists() else "")
                + f'<p>{UF[uf]} é representado no Senado por {len(sby[uf])} senadores em exercício. O {E(x["partido"])} tem {sp0.get(x["partido"], 0)} dos {len(sens)} senadores em exercício e {sum(1 for d in deps if d["partido"] == x["partido"])} dos {len(deps)} deputados federais, segundo as bases oficiais.</p>'
                + _vot.bloco_parlamentar(S, "senado", int(x["id"]), x["nome"])
                + "<h2>Como funciona o mandato</h2><p>O mandato de senador dura oito anos, o equivalente a duas legislaturas. O Senado é renovado de forma alternada, por um terço e dois terços das cadeiras, a cada quatro anos. Cada estado tem três senadores, e cada senador é eleito com dois suplentes.</p>"
                + (f'<h2>Comissões e grupos ({len(x["comissoes"])})</h2>' + S.table(["Colegiado", "Sigla", "Participação"], [[E(c["nome"] or ""), E(c["sigla"] or ""), E(c["cargo"] or "")] for c in x["comissoes"]]) if x["comissoes"] else "")
                + f'<h2>Outros senadores {PREP[uf]} {UF[uf]}</h2>{plist(S, colegas, "sen")}<h2>Deputados federais {PREP[uf]} {UF[uf]}</h2><p><a href="/deputados/uf/{uf.lower()}/">Veja os {len(by_uf.get(uf, []))} deputados federais {PREP[uf]} {UF[uf]}</a>.</p>'
                + '<div class="relbox"><h2>Entenda</h2><ul><li><a href="/glossario/suplente/">Suplente</a></li><li><a href="/glossario/legislatura/">Legislatura</a></li><li><a href="/glossario/ccj/">CCJ</a></li><li><a href="/glossario/quorum/">Quórum</a></li></ul></div>' + fonte_s + "</article>")
        faqs = [(f"De qual partido é {x['nome']}?", f"{E(x['nome'])} é filiado ao {E(x['partido'])}, segundo o Senado Federal (coleta em {data_br(col_s)})."),
                (f"Até quando vai o mandato de {x['nome']}?", f"Até {data_br(x.get('mandato_fim'))}, conforme o cadastro oficial do Senado." if x.get("mandato_fim") else "O cadastro oficial não informa a data de fim do mandato."),
                (f"{x['nome']} é titular ou suplente?", f"Está em exercício como {E((x.get('participacao') or 'titular').lower())}, segundo o Senado."),
                (f"Em quantas comissões {x['nome']} atua?", f"Em {len(x['comissoes'])} colegiados ativos na data da coleta, entre comissões e grupos parlamentares." if x["comissoes"] else "O cadastro oficial não lista colegiados ativos na data da coleta."),
                (f"Quem são os outros senadores {PREP[uf]} {UF[uf]}?", (", ".join(E(y["nome"]) + f" ({E(y['partido'])})" for y in colegas) + ".") if colegas else "Não há outros senadores em exercício pelo estado na data da coleta.")]
        ld = {"@type": "Person", "name": x["nome"], "jobTitle": sen_t.capitalize(), "affiliation": {"@type": "Organization", "name": x["partido"]}, "memberOf": {"@type": "GovernmentOrganization", "name": "Senado Federal"}, "url": S.BASE + x["url"], **({"sameAs": [x["pagina"].replace("http://", "https://")]} if x.get("pagina") else {})}
        S.write(x["url"], S.page(f"{x['nome']} ({x['partido']}-{uf}): {sen_t}, mandato e comissões", f"{x['nome']}, {sen_t} ({x['partido']}-{uf}): mandato, comissões e dados oficiais do Senado Federal.", x["url"], body,
                                 faqs=faqs, crumbs=[("Senadores", "/senadores/"), (x["nome"], x["url"])], jsonld=ld), familia="senadores", lastmod=col_s, image=f"/static/img/parl/sen-{x['id']}.webp" if (S.ROOT / f"static/img/parl/sen-{x['id']}.webp").exists() else None)
    sp = {}
    for x in sens: sp[x["partido"]] = sp.get(x["partido"], 0) + 1
    body = (f'<section class="blk"><h1>Senadores em exercício</h1><p class="snippet">O Senado tem <strong>{len(sens)} senadores</strong> em exercício na data da coleta ({data_br(col_s)}), três por estado e pelo Distrito Federal, de {len(sp)} partidos.</p>'
            + S.table(["Partido", "Senadores"], [[f'<a href="/partidos/{slugify(p)}/">{E(p)}</a>', str(n)] for p, n in sorted(sp.items(), key=lambda x: (-x[1], x[0]))], "Bancadas no Senado")
            + "".join(f'<h2>{UF[u]}</h2>{plist(S, sby[u], "sen")}' for u in sorted(sby, key=lambda u: UF[u])) + fonte_s + "</section>")
    faqs = [("Quantos senadores existem?", "81: três por estado e três pelo Distrito Federal."),
            ("Qual partido tem a maior bancada no Senado?", f"Na data da coleta, o {E(max(sp.items(), key=lambda x: x[1])[0])}, com {max(sp.values())} senadores."),
            ("Quanto dura o mandato de senador?", "Oito anos, com renovação alternada de um terço e dois terços das cadeiras a cada quatro anos."),
            ("Quantas vagas do Senado foram disputadas em 2026?", "Dois terços, ou 54 cadeiras. Os eleitos tomam posse em fevereiro de 2027."),
            ("De onde vêm os dados?", "Da base de Dados Abertos do Senado Federal, coletada diariamente.")]
    S.write("/senadores/", S.page("Senadores em exercício: lista por estado e partido", f"Lista dos {len(sens)} senadores em exercício, por estado e partido, com mandato e comissões a partir de dados oficiais do Senado Federal.", "/senadores/", body,
                                  faqs=faqs, crumbs=[("Senadores", "/senadores/")], jsonld=S.itemlist([(x["nome"], x["url"]) for x in sens])), familia="senadores", lastmod=col_s)
    return {"n_dep": len(deps), "n_sen": len(sens), "n_part": len(set(pp) | set(sp)), "ceap_total_fmt": brl0(tt), "ceap_ano": ano, "ceap_mes": MESES[mes], "coleta": data_br(col_d)}
