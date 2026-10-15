"""Subcategorias das editorias (data/subcategorias.yaml) -> /<editoria>/<sub>/ e páginas por estado /estados/<uf>/.

Classificação: palavra-chave (sem acento, início de palavra) no título+resumo da matéria da mesma editoria,
feed listado em `fontes` da subcategoria, ou campo `subcategoria` no front matter. Regras extras por feed
podem vir de feeds.yaml (`sub` no feed). Subcategoria com menos de `min_materias` fica noindex até ter conteúdo.
Período eleitoral (até 26/10): listas em ordem alfabética, sem ranking.
"""
import re, unicodedata, yaml
from core.site import E
from core.modulos import glossario as G
from .dados import UF, PREP, brl, num, data_br
from . import emendas as _em

def norm(s): return " " + re.sub(r"\s+", " ", unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()) + " "
def casa(txt, ws): return [w for w in ws if re.search(r"(?<![a-z0-9])" + re.escape(norm(w.rstrip("*")).strip()) + ("" if w.endswith("*") else r"(?![a-z0-9])"), txt)]

def carregar(S):
    return yaml.safe_load((S.ROOT / "data/subcategorias.yaml").read_text(encoding="utf-8"))

def classificar(S, D):
    FY = yaml.safe_load((S.ROOT / "feeds.yaml").read_text(encoding="utf-8"))
    feeds = {f["nome"]: f for f in FY.get("feeds") or []}; PW = FY.get("palavras_subcategoria") or {}
    for ed, v in D.items():
        for s in v if isinstance(v, list) else []: s["palavras"] = PW.get(f"{ed}/{s['slug']}", [])
    out = {}
    for p in S.posts:
        t = norm(f'{p.get("titulo", "")} {p.get("resumo", "")}'); ed = p.get("editoria")
        fs = feeds.get(p.get("fonte"), {}).get("sub") or []
        for s in D.get(ed) or []:
            if s["slug"] in (p.get("subcategoria") or []) or s["slug"] in fs or p.get("fonte") in (s.get("fontes") or []) or casa(t, s.get("palavras") or []):
                out.setdefault((ed, s["slug"]), []).append(p)
        raw = f'{p.get("titulo", "")} {p.get("resumo", "")}'.lower()
        for uf, nome in UF.items():
            if re.search(rf"(?<!\w){re.escape(nome.lower())}(?!\w)(?! do sul)", raw) or re.search(rf"[-(/ ]{uf}\)", p.get("titulo", "")):
                out.setdefault(("estados", uf.lower()), []).append(p)
    return out

def build(S):
    from core.build import card, sec
    D = carregar(S); minm = D.get("min_materias", 3)
    _, termos = G.carregar(S.ROOT); TN = {t["slug"]: t["termo"] for t in termos}
    C = classificar(S, D); S.SUBS = {}; urls = []; fam = "subcategorias"
    ok = lambda u: u.split("#")[0] in S.urls
    for ed, subs in D.items():
        if not isinstance(subs, list) or ed not in S.EDS: continue
        e = S.EDS[ed]; S.SUBS[ed] = [(s["nome"], f"/{ed}/{s['slug']}/") for s in subs]
        for s in subs:
            u = f"/{ed}/{s['slug']}/"; ps = C.get((ed, s["slug"]), [])
            gl = [(TN[g], f"/glossario/{g}/") for g in s.get("glossario") or [] if g in TN]
            if len(gl) < len(s.get("glossario") or []): S.errors.append(f"{u}: verbete inexistente em {s.get('glossario')}")
            dd = [(n, l) for n, l in s.get("dados") or [] if ok(l)]
            irm = [(n, l) for n, l in S.SUBS[ed] if l != u]
            inner = "".join(card(S, p, "h2") for p in ps[:30]) or f'<p class="vazio">Ainda não há matérias classificadas em {E(s["nome"])}. A página fica fora do índice de busca até reunir {minm} matérias; a coleta roda a cada 30 minutos.</p>'
            b = (f'<section class="blk">{sec(e["nome"], s["nome"], tag="h1")}<p class="lead">{E(s["intro"])}</p>'
                 f'<p class="meta">{num(len(ps))} matéria(s) classificada(s){" · última em " + data_br(ps[0]["data"].date().isoformat()) if ps else ""}.</p>'
                 f'<div class="grid">{inner}</div>'
                 + (f'<h2>Entenda os termos</h2><div class="chips small">{"".join(f"<a class=chip href={l}>{E(n)}</a>" for n, l in gl)}</div>' if gl else "")
                 + (f'<h2>Dados oficiais</h2><ul>{"".join(f"<li><a href={l}>{E(n)}</a></li>" for n, l in dd)}</ul>' if dd else "")
                 + f'<h2>Outras seções de {E(e["nome"])}</h2><div class="chips small">{"".join(f"<a class=chip href={l}>{E(n)}</a>" for n, l in irm)}</div></section>')
            fts = sorted({p.get("fonte") for p in ps if p.get("fonte")})
            ex = ", ".join(w.strip() for w in (s.get("palavras") or [])[:4])
            faqs = [(f"O que entra na seção {s['nome']}?", E(s["intro"])),
                    (f"Como uma notícia é classificada em {s['nome']}?", f"Pela editoria {E(e['nome'])} e por termos no título ou no resumo, como {E(ex)}" + (f", além de todos os itens do feed {E(', '.join(s['fontes']))}" if s.get("fontes") else "") + ". A regra é automática e pública, sem escolha manual de matérias."),
                    (f"Quantas matérias há hoje em {s['nome']}?", f"{num(len(ps))} na última atualização" + (f", de {len(fts)} fonte(s): {E(', '.join(fts[:6]))}" if fts else "") + f". Com menos de {minm}, a página fica fora do índice de busca."),
                    (f"Quais termos do glossário ajudam a entender {s['nome']}?", (", ".join(f'<a href="{l}">{E(n)}</a>' for n, l in gl) or "Veja o <a href=\"/glossario/\">glossário</a>") + "."),
                    (f"Onde ver dados oficiais ligados a {s['nome']}?", (", ".join(f'<a href="{l}">{E(n)}</a>' for n, l in dd) or 'Na página de <a href="/dados/">dados abertos</a>') + ". Os números vêm de fontes públicas, com data de coleta em cada página."),
                    (f"Qual a diferença entre {s['nome']} e o resto de {e['nome']}?", f"A editoria {E(e['nome'])} reúne todas as matérias do tema; {E(s['nome'])} é um recorte dela. Uma matéria pode estar em mais de uma subcategoria, como {E(', '.join(n for n, _ in irm[:3]))}.")]
            ld = {"@type": "CollectionPage", "name": f"{s['nome']} · {e['nome']}", "url": S.BASE + u, "description": s["intro"], "isPartOf": {"@id": S.BASE + "/#site"},
                  "about": [{"@type": "DefinedTerm", "name": n, "url": S.BASE + l} for n, l in gl], "mainEntity": S.itemlist([(p["titulo"], p["url"]) for p in ps])}
            S.write(u, S.page(f"{s['nome']}: notícias e dados | {e.get('curto', e['nome'])} | {S.CFG['site_name']}", s["intro"], u, b, faqs=faqs, crumbs=[(e["nome"], f"/{ed}/"), (s["nome"], u)], jsonld=ld),
                    idx=len(ps) >= minm, familia=fam, lastmod=(ps[0]["data"].date().isoformat() if ps else None)); urls.append(u)
    # estados
    if "estados" in S.EDS:
        Dm, meta = _em.carregar(S); tot = {}
        for k, m in Dm["mun"].items(): tot.setdefault(k.split("|")[0], [0, 0]); tot[k.split("|")[0]][0] += sum(m["anos"].values()); tot[k.split("|")[0]][1] += 1
        S.SUBS["estados"] = S.SUBS.get("estados", []) + [("Todos os estados", "/estados/#ufs")]
        for uf, nome in sorted(UF.items(), key=lambda x: x[1]):
            u = f"/estados/{uf.lower()}/"; ps = C.get(("estados", uf.lower()), []); pr = PREP[uf]
            dep = sorted((d for d in S.parl["deps"] if d["uf"] == uf), key=lambda d: d["nome"]); sen = sorted((x for x in S.parl["sens"] if x["uf"] == uf), key=lambda d: d["nome"])
            em, nm = tot.get(uf, [0, 0]); ar = {"do": "o ", "da": "a ", "de": ""}[pr]
            lis = lambda xs: '<ul class="cols">' + "".join(f'<li><a href="{x["url"]}">{E(x["nome"])}</a> <small>{E(x["partido"])}</small></li>' for x in xs) + "</ul>"
            intro = (f"Página {pr} {nome} ({uf}) no {S.CFG['site_name']}: notícias que citam o estado, a bancada federal em exercício "
                     f"({num(len(dep))} deputados e {num(len(sen))} senadores, em ordem alfabética) e as emendas parlamentares pagas a órgãos e entidades sediados em "
                     f"{num(nm)} municípios {pr} {nome}, que somam {brl(em)} desde 2023, segundo o Portal da Transparência.")
            inner = "".join(card(S, p, "h2") for p in ps[:20]) or f'<p class="vazio">Ainda não há matérias que citem {ar}{E(nome)}.</p>'
            b = (f'<section class="blk">{sec("Estados e Municípios", nome, tag="h1")}<p class="lead">{E(intro)}</p><div class="grid">{inner}</div>'
                 f'<h2>Deputados federais {pr} {E(nome)}</h2>{lis(dep)}<p><a href="/deputados/uf/{uf.lower()}/">Bancada {pr} {E(nome)} na Câmara</a></p>'
                 f'<h2>Senadores {pr} {E(nome)}</h2>{lis(sen)}'
                 f'<h2>Emendas parlamentares</h2><p>{brl(em)} pagos desde 2023 a favorecidos sediados em {num(nm)} municípios. <a href="/emendas/municipios/{uf.lower()}/">Ver por município</a>. Fonte: Portal da Transparência (CGU), compilação em {data_br((meta.get("coletado_em") or "")[:10])}.</p>'
                 f'<h2>Entenda</h2><div class="chips small">' + "".join(f'<a class="chip" href="/glossario/{g}/">{E(TN[g])}</a>' for g in ("federalismo", "assembleia-legislativa", "fundos-de-participacao", "transferencias-voluntarias") if g in TN) + "</div>" + getattr(S, "estado_extra", {}).get(uf, ("", []))[0] + "</section>")
            faqs = [(f"Quantos deputados federais {pr} {nome} há?", f"{num(len(dep))} em exercício na última coleta da Câmara dos Deputados. A lista acima está em ordem alfabética."),
                    (f"Quem são os senadores {pr} {nome}?", (", ".join(E(x["nome"]) for x in sen) or "Sem dados na coleta") + f". Cada estado elege três senadores."),
                    (f"Quanto {ar.strip().capitalize() + ' ' if ar else ''}{nome} recebeu em emendas parlamentares?", f"{brl(em)} em pagamentos a favorecidos sediados em {num(nm)} municípios {pr} {nome} desde 2023, segundo o Portal da Transparência."),
                    (f"Quais notícias aparecem na página {pr} {nome}?", f"Matérias de qualquer editoria que citam {E(nome)} no título ou no resumo. Hoje são {num(len(ps))}."),
                    (f"Onde ver dados por município {pr} {nome}?", f'Na página de <a href="/emendas/municipios/{uf.lower()}/">emendas por município</a>, com valores por ano, tipo e autor.')]
            faqs += getattr(S, "estado_extra", {}).get(uf, ("", []))[1]
            ld = {"@type": "CollectionPage", "name": f"{nome} ({uf})", "url": S.BASE + u, "description": intro, "isPartOf": {"@id": S.BASE + "/#site"},
                  "about": {"@type": "State", "name": nome, "containedInPlace": {"@type": "Country", "name": "Brasil"}}, "mainEntity": S.itemlist([(p["titulo"], p["url"]) for p in ps])}
            S.write(u, S.page(f"{nome} ({uf}): notícias, bancada e emendas | {S.CFG['site_name']}", intro, u, b, faqs=faqs, crumbs=[("Estados e Municípios", "/estados/"), (nome, u)], jsonld=ld),
                    idx=True, familia=fam); urls.append(u)
    return {"urls": urls}
