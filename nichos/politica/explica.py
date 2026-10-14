"""/explica/: guias "Como funciona" (data/explica.yaml). Cada guia: passos (HowTo), diagrama SVG leve gerado dos passos,
base legal conferida, termos do glossário com resumo e votações nominais ligadas (data/votacoes)."""
import yaml
from core.site import E
from core.modulos import glossario as G
from .dados import data_br, num
from . import votacoes as _vt

def svg(passos):
    h = 46 * len(passos) + 4; r = []
    for i, p in enumerate(passos):
        y = 4 + 46 * i; t = p.rstrip("."); t = t if len(t) <= 58 else t[:56].rsplit(" ", 1)[0].rstrip(",;:") + "…"
        r.append(f'<rect x="2" y="{y}" width="396" height="36" rx="6" fill="#f4f6f8" stroke="#c7cbd1"/><circle cx="22" cy="{y + 18}" r="12" fill="#1f4e79"/>'
                 f'<text x="22" y="{y + 22}" font-size="12" text-anchor="middle" fill="#fff" font-weight="700">{i + 1}</text><text x="42" y="{y + 22}" font-size="12" fill="#2e333d">{E(t)}</text>')
        if i < len(passos) - 1: r.append(f'<path d="M22 {y + 36} v10" stroke="#1f4e79" stroke-width="2"/>')
    return f'<figure class="diag"><svg viewBox="0 0 400 {h}" role="img" aria-label="Diagrama das etapas" width="100%" style="max-width:560px">{"".join(r)}</svg><figcaption>Etapas em resumo.</figcaption></figure>'

def build(S):
    X = yaml.safe_load((S.ROOT / "data/explica.yaml").read_text(encoding="utf-8")); _, termos = G.carregar(S.ROOT); T = {t["slug"]: t for t in termos}
    vs, _m = _vt.carregar(S); urls = []
    for i, x in enumerate(X):
        u = f"/explica/{x['slug']}/"; gl = [T[g] for g in x.get("glossario") or [] if g in T]
        if len(gl) < len(x.get("glossario") or []): S.errors.append(f"{u}: verbete inexistente")
        vv = sorted((v for v in vs if v["titulo"] in (x.get("votacoes") or [])), key=lambda v: v["data"], reverse=True)[:12]
        prox = X[(i + 1) % len(X)]
        b = (f'<article class="post"><h1>{E(x["titulo"])}</h1><p class="snippet">{E(x["intro"])}</p>{svg(x["passos"])}'
             f'<h2>Passo a passo</h2><ol class="steps">' + "".join(f"<li>{E(p)}</li>" for p in x["passos"]) + "</ol>"
             f'<h2>Base legal</h2><ul>' + "".join(f"<li>{E(b)}</li>" for b in x["base"]) + '</ul><p class="src">Textos oficiais em <a href="https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm" target="_blank" rel="noopener">planalto.gov.br</a> e nos regimentos das Casas.</p>'
             + (f'<h2>Termos-chave</h2><ul>' + "".join(f'<li><a href="/glossario/{t["slug"]}/">{E(t["termo"])}</a>: {E(t.get("resumo", ""))}</li>' for t in gl) + "</ul>" if gl else "")
             + (f'<h2>Votações nominais ligadas</h2>' + S.table(["Data", "Proposição", "Casa", "Resultado"], [[data_br(v["data"]), f'<a href="{v["url"]}">{E(v["titulo"])}</a>', "Câmara" if v["casa"] == "camara" else "Senado", E(v["res"])] for v in vv]) if vv else "")
             + f'<p>Próximo guia: <a href="/explica/{prox["slug"]}/">{E(prox["titulo"])}</a> · <a href="/explica/">todos os guias</a> · <a href="/votacoes/">placar de votações</a> · <a href="/glossario/">glossário</a></p></article>')
        faqs = [(f"{x['titulo']}: resumo", E(x["intro"])),
                ("Quantas etapas tem o processo?", f"{len(x['passos'])} etapas principais, da primeira ({E(x['passos'][0].rstrip('.'))}) à última ({E(x['passos'][-1].rstrip('.'))})."),
                ("Qual é a base legal?", E("; ".join(x["base"])) + "."),
                ("Que termos ajudam a entender o tema?", ", ".join(f'<a href="/glossario/{t["slug"]}/">{E(t["termo"])}</a>' for t in gl) + "." if gl else 'Veja o <a href="/glossario/">glossário</a>.'),
                ("Há votações ligadas a este tema?", (f"Sim, {num(len(vv))} votação(ões) nominal(is) listada(s) nesta página, com placar oficial." if vv else 'Não há votação nominal ligada a este guia; veja o <a href="/votacoes/">placar de votações</a>.')),
                ("Este guia substitui o texto da lei?", "Não. É um resumo didático; vale sempre o texto oficial publicado no Diário Oficial e nos regimentos.")]
        ld = {"@type": "HowTo", "name": x["titulo"], "description": x["intro"], "step": [{"@type": "HowToStep", "position": k + 1, "text": p} for k, p in enumerate(x["passos"])]}
        S.write(u, S.page(f"{x['titulo']} | {S.CFG['site_name']}", x["intro"], u, b, faqs=faqs, crumbs=[("Explica", "/explica/"), (x["titulo"], u)], jsonld=ld), familia="explica"); urls.append(u)
    hub = '<section class="blk"><h1>Como funciona: guias do Estrato</h1><p class="lead">Guias curtos sobre o funcionamento dos Três Poderes, com passo a passo, diagrama, base legal conferida no texto oficial e links para o glossário e as votações.</p><ul>' + "".join(f'<li><a href="/explica/{x["slug"]}/">{E(x["titulo"])}</a></li>' for x in X) + "</ul></section>"
    hf = [("O que são os guias?", "Explicações passo a passo de processos do Legislativo, do Executivo, do Judiciário e das eleições."),
          ("De onde vem a base legal?", "Da Constituição, das leis e dos regimentos, conferidos no texto oficial."),
          ("Quantos guias existem?", f"{num(len(X))} nesta versão."),
          ("Os guias têm opinião?", "Não. Descrevem regras e etapas, sem avaliação política."),
          ("Como sugerir um guia?", 'Pela página de <a href="/contato/">contato</a>.')]
    S.write("/explica/", S.page(f"Como funciona: guias | {S.CFG['site_name']}", "Guias passo a passo sobre leis, Orçamento, STF, eleições e Executivo, com base legal e diagramas.", "/explica/", hub, faqs=hf, crumbs=[("Explica", "/explica/")],
            jsonld={"@type": "CollectionPage", "name": "Como funciona", "url": S.BASE + "/explica/", "mainEntity": S.itemlist([(x["titulo"], f"/explica/{x['slug']}/") for x in X])}))
    return {"urls": urls}
