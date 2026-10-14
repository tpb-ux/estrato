"""/calendario/: calendário legislativo (Constituição, art. 57, e sessões plenárias publicadas nas APIs da Câmara e do Senado)
e eleitoral (Resolução TSE nº 23.760/2026). Datas fixas em data/calendario.yaml, todas conferidas na fonte oficial."""
import datetime as dt, yaml
from core.site import E
from .dados import data_br, num
from . import agenda as _ag
DSEM = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]

def util(d):
    while d.weekday() >= 5: d += dt.timedelta(days=1)
    return d

def build(S):
    C = yaml.safe_load((S.ROOT / "data/calendario.yaml").read_text(encoding="utf-8")); L, por = _ag.carregar(S)
    col = (L.get("coletado_em") or "")[:10]; hoje = dt.date.fromisoformat(col) if col else dt.date.today()
    ev = []
    for d, t in C["eleitoral"]["datas"]: ev.append((str(d), "Eleitoral", t, C["eleitoral"]["fonte"][1]))
    for a in (hoje.year, hoje.year + 1):
        for m, dd, t in ((2, 2, "Início da sessão legislativa ordinária"), (7, 17, "Fim do primeiro período da sessão legislativa"), (8, 1, "Início do segundo período da sessão legislativa"), (12, 22, "Fim da sessão legislativa ordinária")):
            x = dt.date(a, m, dd); x2 = util(x) if t.startswith("Início") else x
            ev.append((x2.isoformat(), "Legislativo", t + (f" (data constitucional {data_br(x.isoformat())}, transferida para o primeiro dia útil)" if x2 != x else ""), C["legislativo"]["fonte"][1]))
    ses = [(d, e) for d, es in por.items() for e in es if d >= hoje.isoformat() and e["poder"] == "Legislativo" and ("Plenário" in (e["orgao"] or "") or e.get("orgao") == "PLEN" or "Sessão" in (e["tipo"] or ""))]
    for d, e in sorted(ses, key=lambda x: (x[0], x[1]["hora"]))[:40]: ev.append((d, "Plenário", f'{e["casa"]}: {e["titulo"] or e["tipo"]} {("às " + e["hora"]) if e["hora"] else ""}'.strip(), e["url"]))
    ev.sort(); fut = [x for x in ev if x[0] >= hoje.isoformat()]; pas = [x for x in ev if x[0] < hoje.isoformat()]
    def tab(xs): return S.table(["Data", "Tipo", "Evento"], [[f'{data_br(d)} <small>{DSEM[dt.date.fromisoformat(d).weekday()]}</small>', E(k), f'<a href="{u}"{" target=_blank rel=noopener" if u.startswith("http") else ""}>{E(t)}</a>'] for d, k, t, u in xs])
    prox = fut[0] if fut else None
    b = (f'<article class="post"><h1>Calendário legislativo e eleitoral</h1><p class="snippet">Datas oficiais do Congresso Nacional e das Eleições 2026: sessão legislativa, sessões plenárias já marcadas, turnos de votação, diplomação e posse dos eleitos. '
         + (f'Próxima data: {data_br(prox[0])}, {E(prox[2])}.' if prox else "") + "</p>"
         f'<h2>Próximas datas</h2>{tab(fut)}<h2>Regra da sessão legislativa</h2><p>{E(C["legislativo"]["regra"])}</p>'
         + (f'<h2>Datas já passadas</h2>{tab(pas)}' if pas else "")
         + f'<p class="src">Fontes oficiais: {E(C["eleitoral"]["fonte"][0])} (<a href="{C["eleitoral"]["fonte"][1]}" target="_blank" rel="noopener">TSE</a>); {E(C["legislativo"]["fonte"][0])} (<a href="{C["legislativo"]["fonte"][1]}" target="_blank" rel="noopener">planalto.gov.br</a>); sessões plenárias das APIs da Câmara e do Senado, coleta em {data_br(col)}.</p>'
         '<p>Veja também: <a href="/agenda/">agenda dos Três Poderes</a> · <a href="/explica/como-funciona-a-sessao-legislativa/">como funciona o ano legislativo</a> · <a href="/explica/como-funciona-a-eleicao-para-presidente/">como funciona a eleição para presidente</a> · <a href="/eleicoes/calendario/">notícias do calendário</a></p></article>')
    faqs = [("Quando é o 2º turno das eleições de 2026?", "Em 25 de outubro de 2026, das 8h às 17h no horário de Brasília, onde houver disputa para presidente ou governador, segundo o calendário do TSE."),
            ("Até quando os eleitos são diplomados?", "Até 18 de dezembro de 2026, data-limite fixada pelo TSE."),
            ("Quando tomam posse o presidente e os governadores?", "O presidente e o vice em 5 de janeiro de 2027; governadores e vices em 6 de janeiro de 2027, pela regra da Emenda Constitucional 111/2021."),
            ("Quando começa a nova legislatura?", "Em 1º de fevereiro de 2027, com a posse dos deputados federais e senadores eleitos."),
            ("Quais são os períodos da sessão legislativa?", "De 2 de fevereiro a 17 de julho e de 1º de agosto a 22 de dezembro, pelo art. 57 da Constituição."),
            ("Até quando posso justificar a ausência?", "Até 3 de dezembro de 2026 para o 1º turno e até 8 de janeiro de 2027 para o eventual 2º turno.")]
    ld = {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": k + 1, "item": {"@type": "Event", "name": t, "startDate": d, "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "eventStatus": "https://schema.org/EventScheduled", "location": {"@type": "Place", "name": "Brasil"}}} for k, (d, _k, t, _u) in enumerate(fut[:30])]}
    S.write("/calendario/", S.page(f"Calendário legislativo e eleitoral | {S.CFG['site_name']}", "Datas oficiais do Congresso e das Eleições 2026: 2º turno, diplomação, posse e sessões plenárias marcadas.", "/calendario/", b, faqs=faqs, crumbs=[("Calendário", "/calendario/")], jsonld=ld), familia="calendario", lastmod=col)
    return {"urls": ["/calendario/"]}
