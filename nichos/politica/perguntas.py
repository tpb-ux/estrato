"""/perguntas/: perguntas e respostas curtas calculadas a partir dos dados oficiais já coletados pelo Estrato
(Câmara e Senado Dados Abertos, Portal da Transparência). Nenhum valor é digitado à mão: tudo sai dos JSON em data/
e muda sozinho a cada coleta. Cada página: resposta direta de 40 a 60 palavras, explicação, fonte com data, pergunta
relacionada, schema QAPage e 5 FAQs. Período eleitoral: listas em ordem alfabética, sem ranking.
"""
import collections
from core.site import E, slugify
from .dados import UF, PREP, brl, num, data_br, pct
from . import emendas as _em

def _pal(s): return len(s.split())

def build(S):
    deps, sens = S.parl["deps"], S.parl["sens"]
    import json
    cd = json.loads((S.ROOT / "data/deputados.json").read_text(encoding="utf-8"))["coletado_em"][:10]
    cs = json.loads((S.ROOT / "data/senadores.json").read_text(encoding="utf-8"))["coletado_em"][:10]
    Dm, meta = _em.carregar(S); ce = (meta.get("coletado_em") or "")[:10]; epa = meta.get("empenhado_por_ano") or {}
    F_CAM = f'<a href="https://dadosabertos.camara.leg.br/" target="_blank" rel="noopener">Câmara dos Deputados, API Dados Abertos</a>, coleta em {data_br(cd)}'
    F_SEN = f'<a href="https://legis.senado.leg.br/dadosabertos" target="_blank" rel="noopener">Senado Federal, Dados Abertos</a>, coleta em {data_br(cs)}'
    F_EM = f'<a href="https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares" target="_blank" rel="noopener">Portal da Transparência (CGU), emendas parlamentares</a>, coleta em {data_br(ce)}'
    Q = []  # dicts: slug, q, resp, corpo, fonte, faqs, links, grupo
    pu = {}
    for k, m in Dm["mun"].items(): pu.setdefault(k.split("|")[0], [0.0, 0]); pu[k.split("|")[0]][0] += sum(m["anos"].values()); pu[k.split("|")[0]][1] += 1
    pa, pt = collections.defaultdict(lambda: collections.Counter()), collections.defaultdict(lambda: collections.Counter())
    for k, m in Dm["mun"].items():
        uf_ = k.split("|")[0]; pa[uf_].update(m["anos"]); pt[uf_].update(m["tipos"])
    fem_d = [d for d in deps if d.get("sexo") == "F"]; fem_s = [x for x in sens if (x.get("sexo") or "").startswith("F")]
    # gerais
    Q.append(dict(slug="quantos-deputados-federais-ha", grupo="Congresso", q="Quantos deputados federais há no Brasil?",
        resp=f"A Câmara dos Deputados tem {num(len(deps))} deputados federais em exercício na última coleta da API oficial da Câmara. Eles representam os 26 estados e o Distrito Federal, eleitos pelo sistema proporcional para mandatos de quatro anos, e cada estado tem entre 8 e 70 cadeiras.",
        corpo=S.table(["Unidade da Federação", "Deputados em exercício"], [[f'<a href="/estados/{u.lower()}/">{E(n)}</a>', num(sum(1 for d in deps if d["uf"] == u))] for u, n in sorted(UF.items(), key=lambda x: x[1])], "Deputados por estado, em ordem alfabética"),
        fonte=F_CAM, links=[("Deputados federais", "/deputados/")]))
    Q.append(dict(slug="quantos-senadores-ha", grupo="Congresso", q="Quantos senadores há no Brasil?",
        resp=f"O Senado Federal tem {num(len(sens))} senadores em exercício na última coleta do Senado. Cada estado e o Distrito Federal elegem três senadores pelo voto majoritário, para mandatos de oito anos, e a renovação se alterna entre um terço e dois terços das cadeiras a cada quatro anos.",
        corpo=S.table(["Unidade da Federação", "Senadores em exercício"], [[f'<a href="/estados/{u.lower()}/">{E(n)}</a>', num(sum(1 for x in sens if x["uf"] == u))] for u, n in sorted(UF.items(), key=lambda x: x[1])], "Senadores por estado"),
        fonte=F_SEN, links=[("Senadores", "/senadores/")]))
    Q.append(dict(slug="quantas-deputadas-ha-na-camara", grupo="Congresso", q="Quantas mulheres há na Câmara dos Deputados?",
        resp=f"Há {num(len(fem_d))} deputadas federais em exercício, o equivalente a {pct(len(fem_d), len(deps))} das {num(len(deps))} cadeiras ocupadas na última coleta da Câmara dos Deputados. O número considera o sexo informado no cadastro oficial de cada parlamentar e muda quando suplentes assumem ou titulares retornam.",
        corpo="<h2>Deputadas em exercício, em ordem alfabética</h2><ul class=\"cols\">" + "".join(f'<li><a href="{d["url"]}">{E(d["nome"])}</a> <small>{E(d["partido"])}-{d["uf"]}</small></li>' for d in sorted(fem_d, key=lambda d: d["nome"])) + "</ul>",
        fonte=F_CAM, links=[("Deputados federais", "/deputados/")]))
    Q.append(dict(slug="quantas-senadoras-ha", grupo="Congresso", q="Quantas mulheres há no Senado Federal?",
        resp=f"Há {num(len(fem_s))} senadoras em exercício, o equivalente a {pct(len(fem_s), len(sens))} das {num(len(sens))} cadeiras ocupadas na última coleta do Senado Federal. O total segue o sexo informado no cadastro oficial e pode mudar com a posse de suplentes, licenças e retornos de titulares ao mandato.",
        corpo="<h2>Senadoras em exercício, em ordem alfabética</h2><ul class=\"cols\">" + "".join(f'<li><a href="{x["url"]}">{E(x["nome"])}</a> <small>{E(x["partido"])}-{x["uf"]}</small></li>' for x in sorted(fem_s, key=lambda d: d["nome"])) + "</ul>",
        fonte=F_SEN, links=[("Senadores", "/senadores/")]))
    ps_ = sorted({d["partido"] for d in deps} | {x["partido"] for x in sens})
    Q.append(dict(slug="quantos-partidos-tem-representacao-no-congresso", grupo="Partidos", q="Quantos partidos têm representantes no Congresso?",
        resp=f"{num(len(ps_))} partidos têm ao menos um parlamentar em exercício: {num(len({d['partido'] for d in deps}))} na Câmara dos Deputados e {num(len({x['partido'] for x in sens}))} no Senado Federal, segundo as últimas coletas oficiais das duas Casas. A tabela abaixo mostra cada bancada em ordem alfabética, sem ranking de tamanho.",
        corpo=S.table(["Partido", "Deputados", "Senadores"], [[E(p), num(sum(1 for d in deps if d["partido"] == p)), num(sum(1 for x in sens if x["partido"] == p))] for p in ps_], "Bancadas em ordem alfabética"),
        fonte=F_CAM + "; " + F_SEN, links=[("Partidos", "/partidos/")]))
    for a, v in sorted(epa.items()):
        Q.append(dict(slug=f"quanto-foi-empenhado-em-emendas-em-{a}", grupo="Emendas", q=f"Quanto foi empenhado em emendas parlamentares em {a}?",
            resp=f"Em {a}, o valor empenhado em emendas parlamentares somou {brl(v)}, segundo o arquivo oficial de emendas do Portal da Transparência, mantido pela Controladoria-Geral da União. Empenho é a reserva do dinheiro no Orçamento; o pagamento efetivo pode ocorrer depois, inclusive em anos seguintes, como restos a pagar.",
            corpo=S.table(["Ano", "Empenhado"], [[y, brl(w)] for y, w in sorted(epa.items())], "Empenho de emendas por ano"),
            fonte=F_EM, links=[("Emendas parlamentares", "/emendas/"), ("Restos a pagar", "/glossario/restos-a-pagar/")]))
    Q.append(dict(slug="quantos-municipios-receberam-emendas", grupo="Emendas", q="Quantos municípios receberam pagamentos de emendas parlamentares?",
        resp=f"{num(sum(n for _, n in pu.values()))} municípios aparecem com pagamentos de emendas parlamentares a órgãos e entidades sediados neles desde 2023, segundo o Portal da Transparência. O município é o da sede do favorecido informado pela CGU, que pode ser prefeitura, governo estadual, fundo de saúde ou entidade privada sem fins lucrativos.",
        corpo=S.table(["Estado", "Municípios com pagamento", "Total pago desde 2023"], [[f'<a href="/emendas/municipios/{u.lower()}/">{E(n)}</a>', num(pu.get(u, [0, 0])[1]), brl(pu.get(u, [0, 0])[0])] for u, n in sorted(UF.items(), key=lambda x: x[1])], "Por estado, em ordem alfabética"),
        fonte=F_EM, links=[("Emendas por município", "/emendas/")]))
    # por estado
    for u, n in sorted(UF.items(), key=lambda x: x[1]):
        pr = PREP[u]; ar = {"do": "o ", "da": "a ", "de": ""}[pr]
        dd = sorted((d for d in deps if d["uf"] == u), key=lambda d: d["nome"]); ss = sorted((x for x in sens if x["uf"] == u), key=lambda d: d["nome"])
        lis = lambda xs: '<ul class="cols">' + "".join(f'<li><a href="{x["url"]}">{E(x["nome"])}</a> <small>{E(x["partido"])}</small></li>' for x in xs) + "</ul>"
        Q.append(dict(slug=f"quantos-deputados-tem-{u.lower()}", grupo="Estados", q=f"Quantos deputados federais tem {ar}{n}?",
            resp=f"{ar.strip().capitalize() + ' ' if ar else ''}{n} tem {num(len(dd))} deputados federais em exercício na última coleta da Câmara dos Deputados, além de {num(len(ss))} senadores. O tamanho da bancada na Câmara é proporcional à população do estado, com mínimo de 8 e máximo de 70 cadeiras por unidade da Federação.",
            corpo=f"<h2>Deputados federais {pr} {E(n)}, em ordem alfabética</h2>{lis(dd)}<h2>Senadores {pr} {E(n)}</h2>{lis(ss)}",
            fonte=F_CAM + "; " + F_SEN, links=[(f"Página {pr} {n}", f"/estados/{u.lower()}/"), (f"Bancada {pr} {n}", f"/deputados/uf/{u.lower()}/")]))
        t, nm = pu.get(u, [0, 0])
        Q.append(dict(slug=f"quanto-{u.lower()}-recebeu-em-emendas", grupo="Estados", q=f"Quanto {ar}{n} recebeu em emendas parlamentares?",
            resp=f"Órgãos e entidades sediados em {num(nm)} municípios {pr} {n} receberam {brl(t)} em pagamentos de emendas parlamentares desde 2023, segundo o Portal da Transparência. O valor soma emendas individuais, de bancada, de comissão e de relator, conforme o município da sede de cada favorecido informado pela CGU.",
            corpo=("<h2>Por ano do pagamento</h2>" + S.table(["Ano", "Pago"], [[y, brl(w)] for y, w in sorted(pa[u].items())])
                   + "<h2>Por tipo de emenda</h2>" + S.table(["Tipo", "Pago", "Participação"], [[E(tp), brl(w), pct(w, t)] for tp, w in sorted(pt[u].items())])
                   + f'<p>Os valores somam pagamentos registrados pela CGU com favorecido sediado {"no" if pr == "do" else "na" if pr == "da" else "em"} {E(n)}, incluindo restos a pagar de anos anteriores. O detalhamento por município, ano, tipo de emenda e autor está na página de <a href="/emendas/municipios/{u.lower()}/">emendas por município {pr} {E(n)}</a>.</p>'),
            fonte=F_EM, links=[(f"Emendas {pr} {n}", f"/emendas/municipios/{u.lower()}/"), (f"Página {pr} {n}", f"/estados/{u.lower()}/")]))
    # por partido (Câmara + Senado)
    for p in ps_:
        dd = sorted((d for d in deps if d["partido"] == p), key=lambda d: d["nome"]); ss = sorted((x for x in sens if x["partido"] == p), key=lambda d: d["nome"])
        if len(dd) + len(ss) < 2: continue
        ufs = sorted({d["uf"] for d in dd} | {x["uf"] for x in ss})
        Q.append(dict(slug=f"quantos-parlamentares-tem-o-{slugify(p)}", grupo="Partidos", q=f"Quantos parlamentares tem o {p}?",
            resp=f"O {p} tem {num(len(dd))} deputados federais e {num(len(ss))} senadores em exercício, {num(len(dd) + len(ss))} parlamentares no total, segundo as últimas coletas oficiais da Câmara e do Senado. Eles representam {num(len(ufs))} unidades da Federação. O número muda com trocas de partido, licenças e posse de suplentes.",
            corpo=S.table(["Estado", "Deputados", "Senadores"], [[E(UF.get(x, x)), num(sum(1 for d in dd if d["uf"] == x)), num(sum(1 for y in ss if y["uf"] == x))] for x in ufs], f"Parlamentares do {p} por estado, em ordem alfabética"),
            fonte=F_CAM + "; " + F_SEN, links=[(f"Partido {p}", f"/partidos/{slugify(p)}/")] if f"/partidos/{slugify(p)}/" in S.urls else [("Partidos", "/partidos/")]))
    # grava
    grupos = collections.defaultdict(list)
    for x in Q: grupos[x["grupo"]].append(x)
    urls = []
    for i, x in enumerate(Q):
        u = f"/perguntas/{x['slug']}/"; x["url"] = u
        w = _pal(x["resp"])
        if not 40 <= w <= 60: S.errors.append(f"{u}: resposta direta com {w} palavras (40 a 60)")
    for i, x in enumerate(Q):
        u = x["url"]; irm = grupos[x["grupo"]]; j = irm.index(x); rel = irm[(j + 1) % len(irm)] if len(irm) > 1 else Q[(i + 1) % len(Q)]
        body = (f'<article class="post qa"><h1>{E(x["q"])}</h1><p class="snippet answer">{x["resp"]}</p>'
                f'<h2>Os números em detalhe</h2>{x["corpo"]}'
                f'<p class="src">Fonte oficial: {x["fonte"]}. Os valores são recalculados a cada coleta, sem digitação manual; veja a <a href="/metodologia/">metodologia</a>.</p>'
                f'<h2>Veja também</h2><ul>' + "".join(f'<li><a href="{l}">{E(n)}</a></li>' for n, l in x["links"]) + f'<li>Pergunta relacionada: <a href="{rel["url"]}">{E(rel["q"])}</a></li><li><a href="/perguntas/">Todas as perguntas</a></li></ul></article>')
        faqs = [(x["q"], x["resp"]),
                ("De onde vêm esses números?", f"De {x['fonte']}. O Estrato só compila e organiza os dados públicos, sem estimativas próprias."),
                ("Com que frequência a resposta é atualizada?", "A cada coleta automática das fontes oficiais. A data da coleta usada aparece na linha de fonte desta página."),
                ("Os números podem mudar?", "Sim. Licenças, posse de suplentes, trocas de partido e novos pagamentos registrados pela CGU alteram os totais na coleta seguinte."),
                (f"Qual pergunta relacionada vale ler?", f'<a href="{rel["url"]}">{E(rel["q"])}</a>'),
                ("Encontrei um erro. Como aviso?", 'Pela página de <a href="/correcoes/">correções</a>. A correção é registrada com data.')]
        ld = {"@type": "QAPage", "mainEntity": {"@type": "Question", "name": x["q"], "answerCount": 1, "dateCreated": cd,
              "acceptedAnswer": {"@type": "Answer", "text": x["resp"], "dateCreated": cd, "url": S.BASE + u, "author": {"@id": S.BASE + "/#org"}}}}
        S.write(u, S.page(f"{x['q']} | {S.CFG['site_name']}", x["resp"], u, body, faqs=faqs, crumbs=[("Perguntas", "/perguntas/"), (x["q"], u)], jsonld=ld), familia="perguntas", lastmod=cd); urls.append(u)
    hub = '<section class="blk"><h1>Perguntas e respostas sobre os Três Poderes</h1><p class="lead">Respostas curtas e verificáveis, calculadas a partir dos dados oficiais da Câmara dos Deputados, do Senado Federal e do Portal da Transparência. Cada resposta traz a fonte e a data da coleta e muda sozinha quando os dados mudam.</p>'
    for g, xs in grupos.items(): hub += f"<h2>{E(g)}</h2><ul>" + "".join(f'<li><a href="{x["url"]}">{E(x["q"])}</a></li>' for x in xs) + "</ul>"
    hub += "</section>"
    hf = [("Como as respostas são feitas?", "Por código que lê os dados oficiais coletados pelo Estrato e calcula cada número. Nada é digitado à mão."),
          ("Quais fontes são usadas?", f"{F_CAM}; {F_SEN}; {F_EM}."),
          ("Por que as listas estão em ordem alfabética?", "Até o fim do período eleitoral, em 26/10/2026, o Estrato não publica rankings de parlamentares ou partidos."),
          ("Quantas perguntas existem?", f"{num(len(Q))} nesta atualização, em {num(len(grupos))} grupos."),
          ("Posso sugerir uma pergunta?", 'Sim, pela página de <a href="/contato/">contato</a>. Só entram perguntas que possam ser respondidas com dado oficial.')]
    S.write("/perguntas/", S.page(f"Perguntas e respostas | {S.CFG['site_name']}", "Respostas curtas sobre Congresso, partidos, estados e emendas, calculadas com dados oficiais e atualizadas a cada coleta.", "/perguntas/", hub, faqs=hf, crumbs=[("Perguntas", "/perguntas/")],
            jsonld={"@type": "CollectionPage", "name": "Perguntas e respostas", "url": S.BASE + "/perguntas/", "mainEntity": S.itemlist([(x["q"], x["url"]) for x in Q])}), lastmod=cd)
    S.perguntas = Q
    from .dados_abertos import _csv
    n = _csv(S.OUT / "dados/perguntas.csv", ["pergunta", "resposta", "url", "grupo"], [[x["q"], x["resp"], S.BASE + x["url"], x["grupo"]] for x in Q])
    S.extra_sets = getattr(S, "extra_sets", []) + [("perguntas", "Perguntas e respostas", "Perguntas com resposta direta calculada dos dados oficiais.", n, "Câmara, Senado e Portal da Transparência", "https://dadosabertos.camara.leg.br/", "Respostas geradas por código a partir dos dados oficiais coletados; sem digitação manual.", cd)]
    return {"urls": urls}
