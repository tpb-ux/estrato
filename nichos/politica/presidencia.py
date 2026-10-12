"""Presidente e vice-presidente da República: agenda oficial diária (gov.br/planalto), viagens do vice (Portal da Transparência)
e cartão de pagamento da Presidência (agregado). Fontes públicas sem chave.

Dados: data/agenda/<presidente|vice>.json.gz (tools/datasets_agenda.py) e data/executivo/executivo.json.gz (tools/datasets_executivo.py).
Páginas: /executivo/presidencia/, /executivo/presidencia/<presidente|vice>/, /executivo/presidencia/<presidente|vice>/agenda/<AAAA-MM>/.
Participantes listados nas agendas não são guardados. Período eleitoral: só fatos, sem adjetivos nem comparação entre candidatos.
"""
import collections, gzip, json, re
from core.site import E, slugify
from .dados import brl, brl0, data_br, num, pct, MESES
from . import executivo as _ex

QUEM = {"presidente": ("Presidente da República", "Luiz Inácio Lula da Silva", "do presidente", "o presidente"),
        "vice": ("Vice-Presidente da República", "Geraldo Alckmin", "do vice-presidente", "o vice-presidente")}
DSEM = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]


def _ag(S, q):
    f = S.ROOT / f"data/agenda/{q}.json.gz"
    return json.loads(gzip.decompress(f.read_bytes())) if f.exists() else {"dias": {}}


def _barras(vals, rot):
    mx = max(vals + [1]); w = 100 / max(len(vals), 1)
    r = "".join(f'<rect x="{i * w + w * .1:.2f}" y="{40 - 38 * v / mx:.2f}" width="{w * .8:.2f}" height="{38 * v / mx:.2f}" fill="#1f4e79"><title>{rot[i]}: {v}</title></rect>' for i, v in enumerate(vals) if v)
    return f'<figure class="cbar"><svg viewBox="0 0 100 42" role="img" aria-label="Compromissos por mês" width="100%">{r}</svg><figcaption>Compromissos publicados por mês, de {rot[0]} a {rot[-1]}.</figcaption></figure>'


def build(S):
    D, meta = _ex.carregar(S); urls = []; fam = "executivo"
    col = (meta.get("coletado_em") or "")[:10]
    vice_v = [v for v in D["viagens"] if v["cargo"] == "VICE-PRESIDENTE DA REPUBLICA" and v["sit"] == "Realizada"]
    cp = D["cpgf"].get("20000")
    res = {}
    for q, (cargo, nome, do_, o_) in QUEM.items():
        A = _ag(S, q); dias = A["dias"]
        if not dias: continue
        base = f"/executivo/presidencia/{q}/"
        meses = collections.defaultdict(dict)
        for d, it in dias.items(): meses[d[:7]][d] = it
        mlist = sorted(meses)
        # páginas mensais
        for i, m in enumerate(mlist):
            u = f"{base}agenda/{m}/"; ds = meses[m]; n = sum(len(x) for x in ds.values()); dc = sum(1 for x in ds.values() if x)
            ano, mm = m.split("-"); mn = MESES[int(mm)]
            locs = collections.Counter(c["local"] for x in ds.values() for c in x if c["local"])
            body = f'<article class="post"><h1>Agenda {do_} da República em {mn} de {ano}</h1><p class="snippet">A agenda oficial {do_} {E(nome)} publicada em gov.br/planalto tem <strong>{num(n)} compromissos</strong> em {num(dc)} dias de {mn} de {ano}.</p>'
            if locs: body += "<h2>Locais mais citados no mês</h2>" + S.table(["Local", "Compromissos"], [[E(l), num(c)] for l, c in locs.most_common(6)])
            body += "<h2>Compromissos dia a dia</h2>"
            for d in sorted(ds):
                it = ds[d]
                if not it: continue
                import datetime as _dt
                wd = DSEM[_dt.date.fromisoformat(d).weekday()]
                body += f'<h3>{data_br(d)} ({wd})</h3>' + S.table(["Horário", "Compromisso", "Local"], [[E(c["ini"] + (f"–{c['fim']}" if c["fim"] else "")), E(c["titulo"]), E(c["local"])] for c in it])
            nav = []
            if i: nav.append(f'<a href="{base}agenda/{mlist[i - 1]}/">← {MESES[int(mlist[i - 1][5:])]} de {mlist[i - 1][:4]}</a>')
            if i < len(mlist) - 1: nav.append(f'<a href="{base}agenda/{mlist[i + 1]}/">{MESES[int(mlist[i + 1][5:])]} de {mlist[i + 1][:4]} →</a>')
            body += f'<p>{" · ".join(nav)}</p><p class="src">Fonte oficial: agenda {do_} da República em <a href="{E(A["fonte"].replace("<AAAA-MM-DD>", sorted(ds)[0]))}" target="_blank" rel="noopener">gov.br/planalto</a>, reproduzida sem alterações de texto; participantes não são listados. Compilação em {data_br(col)}. Veja a <a href="{base}">página {do_}</a>.</p></article>'
            dmx = max(ds.items(), key=lambda x: len(x[1]))
            faqs = [(f"Quantos compromissos {o_} teve em {mn} de {ano}?", f"{num(n)} compromissos publicados em {num(dc)} dias, segundo a agenda oficial."),
                    ("Qual dia teve mais compromissos?", f"{data_br(dmx[0])}, com {num(len(dmx[1]))} compromissos." if dmx[1] else "Não há compromissos publicados no mês."),
                    ("Qual o local mais frequente?", f"{E(locs.most_common(1)[0][0])}, citado em {num(locs.most_common(1)[0][1])} compromissos." if locs else "A agenda do mês não informa locais."),
                    ("A agenda inclui todos os compromissos?", "A página reproduz o que foi publicado na agenda oficial. Compromissos não publicados não aparecem."),
                    ("De onde vem a agenda?", f"Da agenda oficial {do_} da República no site gov.br/planalto, coletada diariamente.")]
            S.write(u, S.page(f"Agenda {do_} da República: {mn} de {ano}", f"Agenda oficial {do_} {nome} em {mn} de {ano}: {n} compromissos em {dc} dias, com horário e local.", u, body, faqs=faqs,
                                crumbs=[("Executivo", "/executivo/"), ("Presidência", "/executivo/presidencia/"), (cargo, base), (f"{mn.capitalize()} de {ano}", u)]), familia=fam, lastmod=max(ds))
            urls.append(u)
        # página da autoridade
        pa = collections.Counter(); pd = collections.Counter(); locs = collections.Counter()
        for d, it in dias.items():
            pa[d[:4]] += len(it); pd[d[:4]] += bool(it)
            for c in it:
                if c["local"]: locs[c["local"]] += 1
        tot = sum(pa.values()); ult = max((d for d, it in dias.items() if it), default="")
        body = (f'<article class="post"><h1>{cargo}: agenda oficial{", viagens" if q == "vice" else ""} e gastos desde 2023</h1><p class="snippet">A agenda oficial {do_} da República, {E(nome)}, registra <strong>{num(tot)} compromissos</strong> publicados em {num(sum(pd.values()))} dias desde 1º de janeiro de 2023. '
                f'Último dia com compromissos publicados: {data_br(ult)}.</p>')
        body += "<h2>Agenda por ano</h2>" + S.table(["Ano", "Compromissos", "Dias com compromissos"], [[a, num(pa[a]), num(pd[a])] for a in sorted(pa)])
        rot = [f"{MESES[int(m[5:])][:3]}/{m[2:4]}" for m in mlist]
        body += _barras([sum(len(x) for x in meses[m].values()) for m in mlist], rot)
        body += "<h2>Locais mais citados</h2>" + S.table(["Local", "Compromissos"], [[E(l), num(c)] for l, c in locs.most_common(10)])
        body += '<h2>Agenda mês a mês</h2><div class="chips">' + "".join(f'<a class="chip" href="{base}agenda/{m}/">{MESES[int(m[5:])][:3]}/{m[:4]}</a>' for m in reversed(mlist)) + "</div>"
        if q == "vice":
            tv = sum(v["valor"] for v in vice_v)
            body += f'<h2>Viagens a serviço</h2><p>O Portal da Transparência registra {num(len(vice_v))} viagens realizadas com o cargo de vice-presidente da República desde 2023, somando {brl(tv)} em diárias, passagens e outros gastos.</p>'
            if vice_v: body += _ex.tabela_viagens(S, vice_v, limite=30)
            mdic = [v for v in D["viagens"] if v["nome"] == "GERALDO JOSE RODRIGUES ALCKMIN FILHO" and v["funcao"] == "CNE-0001" and v["sit"] == "Realizada"]
            if mdic: body += f'<p>Como ministro, há ainda {num(len(mdic))} viagens registradas com Cargo de Natureza Especial.</p>'
        else:
            pv = [v for v in D["viagens"] if v["cargo"] == "PRESIDENTE DA REPUBLICA" and v["sit"] == "Realizada"]
            body += f'<h2>Viagens a serviço</h2><p>O Portal da Transparência registra {num(len(pv))} viagens realizadas com o cargo de presidente da República desde 2023, somando {brl(sum(v["valor"] for v in pv))}.</p>'
            if pv: body += _ex.tabela_viagens(S, pv, limite=30)
        if cp:
            ct = sum(x[1] for x in cp["anos"].values()); cs = sum(cp["sig"].values())
            body += (f'<h2>Cartão de pagamento da Presidência da República</h2><p>O órgão Presidência da República, que inclui a estrutura {do_}, teve {brl(ct)} em transações do cartão de pagamento do governo federal desde 2023, das quais {brl(cs)} ({pct(cs, ct)}) marcadas como protegidas por sigilo na fonte. '
                     'O arquivo público não atribui as despesas a uma autoridade.</p>' + S.table(["Ano", "Transações", "Valor", "Sob sigilo"], [[a, num(x[0]), brl(x[1]), brl(cp["sig"].get(a, 0))] for a, x in sorted(cp["anos"].items())])
                     + f'<p>Detalhes por tipo e unidade em <a href="{_ex_url(S)}">Presidência da República: viagens e cartão</a>.</p>')
        body += (f'<p class="src">Fontes oficiais: agenda {do_} em <a href="{E(A["fonte"].replace("<AAAA-MM-DD>", ult))}" target="_blank" rel="noopener">gov.br/planalto</a>; {_ex.FONTE_V}; {_ex.FONTE_C}. '
                 f'Compilação em {data_br(col)}. Dados factuais, sem avaliação; veja a <a href="/executivo/metodologia/">metodologia</a>.</p></article>')
        ma = max(pa.items(), key=lambda x: x[1])
        faqs = [(f"Quantos compromissos a agenda oficial {do_} tem desde 2023?", f"{num(tot)} compromissos publicados em {num(sum(pd.values()))} dias."),
                ("Em que ano houve mais compromissos publicados?", f"Em {ma[0]}, com {num(ma[1])}."),
                ("Qual o local mais citado na agenda?", f"{E(locs.most_common(1)[0][0])}, em {num(locs.most_common(1)[0][1])} compromissos." if locs else "A agenda não informa locais."),
                ("Quanto a Presidência gastou no cartão corporativo?", f"{brl(sum(x[1] for x in cp['anos'].values()))} desde 2023, com {pct(sum(cp['sig'].values()), sum(x[1] for x in cp['anos'].values()))} sob sigilo." if cp else "Sem dados."),
                ("Por que os participantes das reuniões não aparecem?", "O Estrato reproduz horário, título e local de cada compromisso e não guarda a lista de participantes, que inclui pessoas sem cargo público."),
                ("A página tem relação com a eleição?", "Não. São registros oficiais publicados pelo governo, sem avaliação nem comparação entre candidatos.")]
        S.write(base, S.page(f"{cargo}: agenda oficial e gastos desde 2023", f"Agenda oficial {do_} {nome}: {num(tot)} compromissos desde 2023, mês a mês, com viagens e cartão de pagamento da Presidência.", base, body, faqs=faqs,
                               crumbs=[("Executivo", "/executivo/"), ("Presidência", "/executivo/presidencia/"), (cargo, base)],
                               jsonld={"@type": "Dataset", "name": f"Agenda oficial {do_} da República (desde 2023)", "description": f"Compromissos publicados na agenda oficial {do_} da República desde 2023, com horário, título e local.", "url": S.BASE + base,
                                       "isBasedOn": A["fonte"], "license": "https://creativecommons.org/licenses/by/4.0/deed.pt-br", "isAccessibleForFree": True, "creator": {"@id": S.BASE + "/#org"}, "inLanguage": "pt-BR", "temporalCoverage": f"2023-01-01/{ult}"}), familia="paginas", lastmod=ult)
        urls.append(base); res[q] = (tot, len(mlist), base)
    if res:
        body = ('<section class="blk"><h1>Presidência e Vice-Presidência da República: agendas e gastos</h1><p class="snippet">Agendas oficiais diárias do presidente e do vice-presidente da República desde 2023, viagens a serviço do vice-presidente e cartão de pagamento da Presidência, a partir de fontes oficiais públicas.</p>'
                + S.table(["Autoridade", "Compromissos desde 2023", "Meses com agenda"], [[f'<a href="{b}">{QUEM[q][0]}</a>', num(t), num(m)] for q, (t, m, b) in res.items()])
                + '<p>Viagens e cartão de ministros estão no <a href="/executivo/">hub do Executivo</a>.</p></section>')
        faqs = [("De onde vêm as agendas?", "Das páginas oficiais de agenda do presidente e do vice-presidente em gov.br/planalto."), ("Com que frequência são atualizadas?", "Diariamente; os últimos dez dias são lidos de novo para captar correções."),
                ("O que aparece de cada compromisso?", "Horário, título e local, como publicados."), ("Há dados de viagens?", "Sim, as registradas no sistema de viagens a serviço do Portal da Transparência com os cargos de presidente e de vice-presidente."),
                ("Há avaliação dos governantes?", "Não. As páginas só reproduzem dados oficiais.")]
        S.write("/executivo/presidencia/", S.page("Presidência e Vice-Presidência: agendas oficiais e gastos desde 2023", "Agendas oficiais diárias do presidente e do vice-presidente da República desde 2023, viagens do vice e cartão de pagamento da Presidência.", "/executivo/presidencia/", body, faqs=faqs,
                                                 crumbs=[("Executivo", "/executivo/"), ("Presidência", "/executivo/presidencia/")]), familia="paginas", lastmod=col)
        urls.append("/executivo/presidencia/")
    return {"urls": urls}


def _ex_url(S): return (getattr(S, "exec_ourl", {}) or {}).get("20000", "/executivo/")
