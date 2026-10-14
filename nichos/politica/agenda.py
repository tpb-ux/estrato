"""/agenda/: agenda dos Três Poderes por dia e por semana. Legislativo: data/agenda/tres_poderes.json (tools/datasets_agenda3p.py,
APIs da Câmara e do Senado). Executivo: agenda oficial do presidente e do vice (data/agenda/*.json.gz, gov.br/planalto).
Judiciário: pauta do STF quando acessível (hoje o portal recusa a coleta automática; a página informa isso)."""
import collections, datetime as dt, gzip, json
from core.site import E
from .dados import data_br, num
DSEM = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

def carregar(S):
    f = S.ROOT / "data/agenda/tres_poderes.json"; L = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"itens": {}}
    por = collections.defaultdict(list)
    for e in L["itens"].values(): por[e["data"]].append(e)
    for q, cargo in (("presidente", "Presidente da República"), ("vice", "Vice-presidente")):
        g = S.ROOT / f"data/agenda/{q}.json.gz"
        if not g.exists(): continue
        A = json.loads(gzip.decompress(g.read_bytes()))
        for d, its in A["dias"].items():
            for it in its:
                por[d].append({"poder": "Executivo", "casa": cargo, "data": d, "hora": (it.get("ini") or "").replace("h", ":"), "tipo": "Compromisso oficial", "orgao": "Planalto", "orgao_nome": cargo,
                               "titulo": it.get("titulo") or "", "local": it.get("local") or "", "url": f"/executivo/presidencia/{q}/agenda/{d[:7]}/"})
    for d in por: por[d].sort(key=lambda e: (e["hora"] or "99", e["poder"], e["casa"]))
    return L, por

def tab(S, its):
    return S.table(["Hora", "Poder", "Onde", "Compromisso", "Situação"], [[E(e["hora"] or "—"), E(e["poder"]), E(f'{e["casa"]} · {e["orgao"]}' if e["orgao"] and e["orgao"] != "Planalto" else e["casa"]),
                   f'<a href="{e["url"]}"{" target=_blank rel=noopener" if e["url"].startswith("http") else ""}>{E(e["titulo"] or e["tipo"])}</a>' + (f' <small>{E(e["tipo"])}</small>' if e["tipo"] and e["titulo"] else ""), E(e.get("situacao", "") or "—")] for e in its])

def build(S):
    L, por = carregar(S); col = (L.get("coletado_em") or "")[:10]; stf = (L.get("status") or {}).get("stf", "não verificado")
    hoje = dt.date.fromisoformat(col) if col else dt.date.today(); urls = []
    fonte = ('<p class="src">Fontes: <a href="https://dadosabertos.camara.leg.br/" target="_blank" rel="noopener">Câmara dos Deputados, API Dados Abertos</a>, '
             '<a href="https://legis.senado.leg.br/dadosabertos" target="_blank" rel="noopener">Senado Federal, Dados Abertos</a> e '
             '<a href="https://www.gov.br/planalto/pt-br/acompanhe-o-planalto/agenda-do-presidente-da-republica-lula" target="_blank" rel="noopener">agenda oficial do Planalto</a>'
             f'; coleta em {data_br(col)}. A pauta do <a href="https://portal.stf.jus.br/pauta/" target="_blank" rel="noopener">STF</a> não entra por enquanto: o portal recusa a coleta automática.</p>')
    dias = sorted(por); semanas = collections.defaultdict(list)
    for d in dias: y, w, _ = dt.date.fromisoformat(d).isocalendar(); semanas[f"{y}-S{w:02d}"].append(d)
    def ddesc(d): x = dt.date.fromisoformat(d); return f"{DSEM[x.weekday()]}, {data_br(d)}"
    for i, d in enumerate(dias):
        u = f"/agenda/{d}/"; its = por[d]; c = collections.Counter(e["poder"] for e in its)
        y, w, _ = dt.date.fromisoformat(d).isocalendar(); sw = f"{y}-S{w:02d}"
        nav = (f'<p>' + (f'<a href="/agenda/{dias[i - 1]}/">← {data_br(dias[i - 1])}</a> · ' if i else "") + f'<a href="/agenda/semana/{sw}/">semana {w}</a>' + (f' · <a href="/agenda/{dias[i + 1]}/">{data_br(dias[i + 1])} →</a>' if i + 1 < len(dias) else "") + "</p>")
        res = ", ".join(f"{num(n)} do {p}" for p, n in sorted(c.items()))
        b = f'<article class="post"><h1>Agenda dos Três Poderes: {E(ddesc(d))}</h1><p class="snippet">{num(len(its))} compromissos publicados para {E(ddesc(d))}: {res}. Horários de Brasília, conforme as fontes oficiais.</p>{nav}{tab(S, its)}{fonte}</article>'
        faqs = [(f"Quantos compromissos há em {data_br(d)}?", f"{num(len(its))}: {res}."),
                ("De onde vêm os dados?", "Das APIs de dados abertos da Câmara e do Senado e da agenda oficial do Planalto."),
                ("A agenda pode mudar?", "Sim. Sessões e reuniões são canceladas ou remarcadas; a página é refeita a cada coleta."),
                ("Por que o STF não aparece?", "O portal do STF recusa a coleta automática no momento. Quando houver acesso, a pauta entra aqui."),
                ("Onde ver a semana inteira?", f'Na <a href="/agenda/semana/{sw}/">agenda da semana {w}</a>.')]
        S.write(u, S.page(f"Agenda dos Três Poderes em {data_br(d)} | {S.CFG['site_name']}", f"{num(len(its))} compromissos de Câmara, Senado e Planalto em {ddesc(d)}.", u, b, faqs=faqs,
                          crumbs=[("Agenda", "/agenda/"), (data_br(d), u)], jsonld={"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": k + 1, "item": {"@type": "Event", "name": e["titulo"] or e["tipo"], "startDate": f"{d}T{e['hora']}" if len(e["hora"]) == 5 else d, "location": {"@type": "Place", "name": e["local"] or e["casa"]}, "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "eventStatus": "https://schema.org/EventScheduled", "organizer": {"@type": "GovernmentOrganization", "name": e["casa"]}}} for k, e in enumerate(its[:30])]}),
                familia="agenda", lastmod=col); urls.append(u)
    for sw, ds in semanas.items():
        u = f"/agenda/semana/{sw}/"; n = sum(len(por[d]) for d in ds)
        b = f'<article class="post"><h1>Agenda dos Três Poderes: semana {sw[-2:]} de {sw[:4]}</h1><p class="snippet">{num(n)} compromissos entre {data_br(ds[0])} e {data_br(ds[-1])}, em {num(len(ds))} dias com agenda publicada.</p>'
        for d in ds: b += f'<h2><a href="/agenda/{d}/">{E(ddesc(d)).capitalize()}</a></h2>{tab(S, por[d])}'
        b += fonte + "</article>"
        faqs = [(f"Quantos compromissos há na semana {sw[-2:]}?", f"{num(n)} em {num(len(ds))} dias."), ("Quais Poderes aparecem?", "Legislativo (Câmara, Senado e Congresso) e Executivo (presidente e vice)."),
                ("Os horários são de Brasília?", "Sim, como publicados pelas fontes."), ("Como saber se a sessão foi realizada?", "Pela coluna Situação, atualizada a cada coleta."),
                ("Onde fica a agenda de hoje?", 'Na <a href="/agenda/">página principal da agenda</a>.')]
        S.write(u, S.page(f"Agenda da semana {sw[-2:]}/{sw[:4]} | {S.CFG['site_name']}", f"{num(n)} compromissos de Câmara, Senado e Planalto de {data_br(ds[0])} a {data_br(ds[-1])}.", u, b, faqs=faqs, crumbs=[("Agenda", "/agenda/"), (f"Semana {sw[-2:]}/{sw[:4]}", u)]), familia="agenda", lastmod=col); urls.append(u)
    from .dados_abertos import _csv
    n = _csv(S.OUT / "dados/agenda-tres-poderes.csv", ["data", "hora", "poder", "casa_ou_cargo", "orgao", "tipo", "titulo", "situacao", "local", "url"],
             [[d, e["hora"], e["poder"], e["casa"], e["orgao"], e["tipo"], e["titulo"], e.get("situacao", ""), e["local"], e["url"] if e["url"].startswith("http") else S.BASE + e["url"]] for d in dias for e in por[d]])
    S.extra_sets = getattr(S, "extra_sets", []) + [("agenda-tres-poderes", "Agenda dos Três Poderes", "Sessões, reuniões de comissões e agenda oficial do presidente e do vice, por dia.", n, "APIs da Câmara e do Senado e agenda do Planalto", "https://dadosabertos.camara.leg.br/", "Eventos das APIs oficiais e agenda publicada pelo Planalto, sem participantes.", col)]
    prox = [d for d in dias if d >= hoje.isoformat()][:7]; rec = [d for d in dias if d < hoje.isoformat()][-7:][::-1]
    b = f'<section class="blk"><h1>Agenda dos Três Poderes</h1><p class="lead">Sessões do plenário, reuniões de comissões da Câmara e do Senado e a agenda oficial do presidente e do vice-presidente, por dia e por semana, a partir das fontes oficiais.</p>'
    b += "<h2>Próximos dias</h2>" + ("".join(f'<h3><a href="/agenda/{d}/">{E(ddesc(d)).capitalize()}</a></h3>{tab(S, por[d][:15])}' for d in prox) or "<p>Sem compromissos publicados para os próximos dias.</p>")
    b += "<h2>Dias recentes</h2><ul>" + "".join(f'<li><a href="/agenda/{d}/">{E(ddesc(d))}</a>: {num(len(por[d]))} compromissos</li>' for d in rec) + "</ul>"
    b += "<h2>Semanas</h2><div class=\"chips small\">" + "".join(f'<a class="chip" href="/agenda/semana/{w}/">{w[-2:]}/{w[:4]}</a>' for w in sorted(semanas, reverse=True)[:20]) + "</div>" + fonte + "</section>"
    hf = [("O que a agenda mostra?", "Sessões e reuniões da Câmara, do Senado e do Congresso e os compromissos oficiais do presidente e do vice."),
          ("Com que frequência é atualizada?", f"A cada coleta automática; a última foi em {data_br(col)}."),
          ("A agenda do presidente aparece antes do dia?", "Não. O Planalto publica a agenda no próprio dia; ela entra na coleta seguinte."),
          ("Por que o STF não aparece?", "O portal do STF recusa a coleta automática no momento."),
          ("Quantos dias estão disponíveis?", f"{num(len(dias))} dias com compromissos, em {num(len(semanas))} semanas.")]
    S.write("/agenda/", S.page(f"Agenda dos Três Poderes | {S.CFG['site_name']}", "Agenda diária e semanal de Câmara, Senado e Planalto, com dados oficiais.", "/agenda/", b, faqs=hf, crumbs=[("Agenda", "/agenda/")]), lastmod=col)
    return {"urls": urls}
