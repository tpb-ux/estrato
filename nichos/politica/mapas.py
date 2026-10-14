"""/mapas/: mapas e rankings por estado (mapa em grade de 27 quadrados, SVG leve). DESLIGADO até o fim do período eleitoral:
enquanto config mapas.ativo for false ou a data for anterior a mapas.liberar_em, as páginas são geradas em noindex,
sem link no menu, no sitemap ou em outras páginas. Fontes: Portal da Transparência (emendas), Câmara (cota e cadastro)."""
import datetime as dt, json
from core.site import E
from .dados import UF, PREP, brl, num, pct, data_br
from . import emendas as _em
POS = {"RR": (2, 0), "AP": (4, 0), "AM": (1, 1), "PA": (3, 1), "MA": (4, 1), "CE": (5, 1), "RN": (6, 1), "AC": (0, 2), "RO": (1, 2), "TO": (3, 2), "PI": (4, 2), "PE": (5, 2), "PB": (6, 2),
       "MT": (2, 3), "GO": (3, 3), "BA": (4, 3), "SE": (5, 3), "AL": (6, 3), "MS": (2, 4), "DF": (3, 4), "MG": (4, 4), "ES": (5, 4), "PR": (2, 5), "SP": (3, 5), "RJ": (4, 5), "SC": (2, 6), "RS": (2, 7)}

def mapa(vals, fmt, rot):
    mx = max(vals.values()) or 1; r = []
    for uf, (c, l) in POS.items():
        v = vals.get(uf, 0); a = 0.15 + 0.85 * v / mx
        r.append(f'<g><rect x="{c * 44 + 2}" y="{l * 44 + 2}" width="40" height="40" rx="4" fill="#1f4e79" fill-opacity="{a:.2f}"><title>{UF[uf]}: {fmt(v)}</title></rect>'
                 f'<text x="{c * 44 + 22}" y="{l * 44 + 27}" font-size="12" text-anchor="middle" font-weight="700" fill="{"#fff" if a > .55 else "#1f2a37"}">{uf}</text></g>')
    return f'<figure class="diag"><svg viewBox="0 0 312 356" role="img" aria-label="{E(rot)}" width="100%" style="max-width:420px">{"".join(r)}</svg><figcaption>{E(rot)}. Cor mais forte, valor maior.</figcaption></figure>'

def build(S):
    cfg = S.CFG.get("mapas") or {}; lib = str(cfg.get("liberar_em", "2026-10-27"))
    ativo = bool(cfg.get("ativo")) and dt.date.today().isoformat() >= lib
    deps = S.parl["deps"]; Dm, meta = _em.carregar(S); ce = (meta.get("coletado_em") or "")[:10]
    em = {}
    for k, m in Dm["mun"].items(): em[k.split("|")[0]] = em.get(k.split("|")[0], 0) + sum(m["anos"].values())
    cota = {}; nd = {}; fem = {}
    for d in deps: cota[d["uf"]] = cota.get(d["uf"], 0) + d["c"]["total"]; nd[d["uf"]] = nd.get(d["uf"], 0) + 1; fem[d["uf"]] = fem.get(d["uf"], 0) + (d.get("sexo") == "F")
    C = json.loads((S.ROOT / "data/ceap.json").read_text(encoding="utf-8"))
    M = [("emendas-pagas", "Emendas parlamentares pagas por estado", em, brl, f"Pagamentos desde 2023 a favorecidos sediados em cada estado. Fonte: Portal da Transparência (CGU), coleta em {data_br(ce)}."),
         ("cota-parlamentar", f"Cota parlamentar da bancada federal por estado em {C['ano']}", cota, brl, f"Soma da cota dos deputados em exercício de cada estado em {C['ano']}, até o mês {C['ultimo_mes']}. Fonte: Câmara dos Deputados."),
         ("cota-por-deputado", f"Cota parlamentar média por deputado em {C['ano']}", {u: cota.get(u, 0) / nd[u] for u in nd}, brl, "Cota da bancada dividida pelo número de deputados em exercício. Fonte: Câmara dos Deputados."),
         ("mulheres-na-bancada", "Participação de mulheres na bancada federal", {u: 100 * fem.get(u, 0) / nd[u] for u in nd}, lambda v: f"{v:.1f}%".replace(".", ","), "Deputadas em exercício sobre o total da bancada. Fonte: Câmara dos Deputados.")]
    urls = []; aviso = '' if ativo else f'<p class="warn">Seção em preparação e fora do índice de busca até {data_br(lib)}, depois do período eleitoral.</p>'
    for slug, t, vals, fmt, nota in M:
        u = f"/mapas/{slug}/"; rk = sorted(vals.items(), key=lambda x: -x[1])
        b = (f'<article class="post"><h1>{E(t)}</h1>{aviso}<p class="snippet">{E(nota)}</p>{mapa(vals, fmt, t)}'
             + S.table(["Posição", "Estado", "Valor"], [[str(i + 1), f'<a href="/estados/{uf.lower()}/">{E(UF[uf])}</a>', fmt(v)] for i, (uf, v) in enumerate(rk)], "Ranking dos estados") + '<p><a href="/mapas/">Todos os mapas</a></p></article>')
        S.write(u, S.page(f"{t} | {S.CFG['site_name']}", nota[:150], u, b, crumbs=[("Mapas", "/mapas/"), (t, u)],
                faqs=[("Qual é a fonte?", E(nota)), ("Qual estado lidera?", f"{E(UF[rk[0][0]])}, com {fmt(rk[0][1])}."), ("Qual tem o menor valor?", f"{E(UF[rk[-1][0]])}, com {fmt(rk[-1][1])}."), ("O mapa é geográfico?", "É um mapa em grade: cada estado ocupa um quadrado de mesmo tamanho, na posição aproximada."), ("Com que frequência atualiza?", "A cada coleta das fontes oficiais.")]),
                idx=ativo, familia="mapas"); urls.append(u)
    b = f'<section class="blk"><h1>Mapas e rankings por estado</h1>{aviso}<ul>' + "".join(f'<li><a href="/mapas/{s}/">{E(t)}</a></li>' for s, t, *_ in M) + "</ul></section>"
    S.write("/mapas/", S.page(f"Mapas e rankings por estado | {S.CFG['site_name']}", "Mapas e rankings dos estados com dados oficiais de emendas e cota parlamentar.", "/mapas/", b, crumbs=[("Mapas", "/mapas/")],
            faqs=[("Que mapas existem?", ", ".join(t for _, t, *_ in M) + "."), ("Por que a seção está fora do ar?", "Rankings ficam desligados até o fim do período eleitoral."), ("Quais as fontes?", "Portal da Transparência e Câmara dos Deputados."), ("Os mapas atualizam?", "Sim, a cada coleta."), ("Há ranking de candidatos?", "Não. Só estados.")]), idx=ativo, familia="mapas")
    return {"urls": urls}
