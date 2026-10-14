"""/linha-do-tempo/: 10 temas longos (data/linha_do_tempo.yaml). Marcos = votações nominais de plenário das proposições do tema
(data/votacoes, com link para cada votação) + marcos legais com data conferida. Atualiza sozinho quando há nova votação."""
import collections, yaml
from core.site import E
from .dados import data_br, num
from . import votacoes as _vt

def build(S):
    X = yaml.safe_load((S.ROOT / "data/linha_do_tempo.yaml").read_text(encoding="utf-8")); vs, _ = _vt.carregar(S); urls = []
    for i, x in enumerate(X):
        u = f"/linha-do-tempo/{x['slug']}/"
        vv = [v for v in vs if v["titulo"] in x["props"]]
        ev = [(v["data"], "v", v) for v in vv] + [(str(d), "m", t) for d, t in x.get("marcos") or []]
        ev.sort(key=lambda e: (e[0], e[1] == "m"))
        anos = collections.Counter(e[0][:4] for e in ev)
        li = ""
        for d, k, o in ev:
            if k == "m": li += f'<li class="tm marco"><time datetime="{d}">{data_br(d)}</time><strong>{E(o)}</strong></li>'
            else:
                c = o.get("placar") or {}; pl = f' · {num(c.get("sim", 0))} sim, {num(c.get("nao", 0))} não' if c else ""
                li += (f'<li class="tm"><time datetime="{d}">{data_br(d)}</time><a href="{o["url"]}">{E(o["titulo"])} · plenário {"da Câmara" if o["casa"] == "camara" else "do Senado"}</a>'
                       f'<span>{E(o["res"])}{pl}. {E((o.get("descricao") or "")[:220])}</span></li>')
        ini, fim = (ev[0][0], ev[-1][0]) if ev else ("", "")
        ex = x.get("explica"); prox = X[(i + 1) % len(X)]
        b = (f'<article class="post"><h1>Linha do tempo: {E(x["titulo"])}</h1><p class="snippet">{E(x["intro"])} São {num(len(vv))} votações nominais de plenário entre {data_br(ini)} e {data_br(fim)}'
             + (f" e {num(len(x['marcos']))} marco(s) legal(is)" if x.get("marcos") else "") + ".</p>"
             f'<p>Proposições acompanhadas: {E(", ".join(x["props"]))}. Por ano: ' + ", ".join(f"{a}: {num(n)}" for a, n in sorted(anos.items())) + ".</p>"
             f'<ol class="tline">{li}</ol>'
             f'<p class="src">Fontes: votações nominais das APIs de dados abertos da Câmara e do Senado (placar e texto oficial de cada votação); marcos legais conferidos em <a href="https://www.planalto.gov.br/" target="_blank" rel="noopener">planalto.gov.br</a>.</p>'
             + (f'<p>Entenda o processo: <a href="/explica/{ex}/">guia Como funciona</a>.</p>' if ex else "")
             + f'<p>Próximo tema: <a href="/linha-do-tempo/{prox["slug"]}/">{E(prox["titulo"])}</a> · <a href="/linha-do-tempo/">todos os temas</a> · <a href="/votacoes/">placar de votações</a></p></article>')
        faqs = [(f"Quantas votações houve sobre {x['titulo'].lower()}?", f"{num(len(vv))} votações nominais de plenário compiladas pelo Estrato, entre {data_br(ini)} e {data_br(fim)}."),
                ("Quais proposições entram nesta linha do tempo?", E(", ".join(x["props"])) + "."),
                ("O que conta como marco?", "Cada votação nominal no plenário da Câmara ou do Senado e, quando houver, a promulgação ou sanção conferida no texto oficial."),
                ("Votações simbólicas aparecem?", "Não. Só votações nominais, que registram o voto de cada parlamentar."),
                ("A página é atualizada?", "Sim. Novas votações das proposições listadas entram sozinhas na coleta seguinte."),
                ("Onde ver como votou cada parlamentar?", "Em cada votação listada, com lista nominal, placar por partido e orientação das lideranças.")]
        ld = {"@type": "ItemList", "name": f"Linha do tempo: {x['titulo']}", "itemListOrder": "https://schema.org/ItemListOrderAscending",
              "itemListElement": [{"@type": "ListItem", "position": k + 1, "name": (o if kk == "m" else f'{o["titulo"]} ({data_br(d)})'), **({"url": S.BASE + o["url"]} if kk == "v" else {})} for k, (d, kk, o) in enumerate(ev[:100])]}
        S.write(u, S.page(f"Linha do tempo: {x['titulo']} | {S.CFG['site_name']}", f"{x['intro'][:120]} {num(len(vv))} votações nominais com placar.", u, b, faqs=faqs, crumbs=[("Linha do tempo", "/linha-do-tempo/"), (x["titulo"], u)], jsonld=ld),
                familia="linha_do_tempo", lastmod=fim or None); urls.append(u)
    hub = '<section class="blk"><h1>Linhas do tempo</h1><p class="lead">Dez temas longos do Congresso contados pelas votações nominais de plenário, com placar oficial, e pelos marcos legais de promulgação e sanção.</p><ul>' + "".join(f'<li><a href="/linha-do-tempo/{x["slug"]}/">{E(x["titulo"])}</a></li>' for x in X) + "</ul></section>"
    hf = [("O que é uma linha do tempo?", "A sequência de votações nominais e marcos legais de um tema, em ordem cronológica."), ("Quantos temas existem?", f"{num(len(X))}."),
          ("De onde vêm os dados?", "Das APIs de dados abertos da Câmara e do Senado e do texto oficial das leis."), ("As linhas são atualizadas?", "Sim, a cada coleta de votações."),
          ("Posso sugerir um tema?", 'Sim, pela página de <a href="/contato/">contato</a>.')]
    S.write("/linha-do-tempo/", S.page(f"Linhas do tempo | {S.CFG['site_name']}", "Reforma tributária, arcabouço fiscal, precatórios e outros temas contados pelas votações nominais.", "/linha-do-tempo/", hub, faqs=hf, crumbs=[("Linha do tempo", "/linha-do-tempo/")]))
    return {"urls": urls}
