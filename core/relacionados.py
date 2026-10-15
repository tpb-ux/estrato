"""Bloco "Dados relacionados" nas notícias: liga cada matéria às páginas de dados do próprio site que ela cita (parlamentar, partido, estado, proposição).
Roda depois dos módulos (precisa de S.urls) e só linka páginas que existem. Nomes de parlamentares: só nome composto, com fronteira de palavra."""
import re
from .site import E

PROP = re.compile(r"\b(PL|PEC|PLP|PDL|MPV|PRC|PLN)\s*n?[ºo°.]*\s*(\d{1,5})\s*/\s*(\d{4})\b")
SIGLA = re.compile(r"\b([A-Z]{2,}(?:-[A-Z]+)?)\b")

def aplicar(S, posts):
    from nichos.politica.dados import UF
    parl = getattr(S, "parl", {"deps": [], "sens": []})
    nomes = {x["nome"]: x["url"] for x in parl["deps"] + parl["sens"] if len(x["nome"].split()) >= 2 and x["url"] in S.urls}
    ufs = sorted(((n, f"/estados/{k.lower()}/") for k, n in UF.items() if f"/estados/{k.lower()}/" in S.urls), key=lambda x: -len(x[0]))
    total = com = 0
    for p in posts:
        f = S.OUT / p["url"].strip("/") / "index.html"
        if p.get("tipo") == "analise" or not f.exists(): continue
        txt = re.sub(r"<[^>]+>", " ", f"{p['titulo']}. {p.get('resumo', '')}. {p.get('html', '')}")
        lk = []
        for t, n, a in PROP.findall(txt):
            u = f"/proposicoes/{t.lower()}-{n}-{a}/"
            if u in S.urls and (u, f"{t} {n}/{a}") not in lk: lk.append((u, f"{t} {n}/{a} na Câmara"))
        for nome, u in nomes.items():
            if re.search(rf"(?<!\w){re.escape(nome)}(?!\w)", txt): lk.append((u, f"{nome}: perfil, votações e cota"))
        for sg in dict.fromkeys(SIGLA.findall(txt)):
            u = f"/partidos/{sg.lower()}/"
            if sg != "PL" and u in S.urls: lk.append((u, f"{sg}: bancada e votações"))
        usados = txt
        for n, u in ufs:
            if re.search(rf"(?<!\w){re.escape(n)}(?!\w)", usados):
                lk.append((u, f"{n}: bancada, emendas e notícias")); usados = usados.replace(n, " ")  # evita "Mato Grosso" dentro de "Mato Grosso do Sul"
        lk = lk[:6]; total += len(lk); com += bool(lk)
        if not lk: continue
        pre = S.PREFIX
        bloco = '<section class="rel"><h2>Dados relacionados</h2><ul>' + "".join(f'<li><a href="{pre}{u}">{E(t)}</a></li>' for u, t in lk) + "</ul></section>"
        h = f.read_text(encoding="utf-8"); h = h.replace("</article>", bloco + "</article>", 1); f.write_text(h, encoding="utf-8")
    print(f"Notícias: {com} de {len([p for p in posts if p.get('tipo') != 'analise'])} com bloco 'Dados relacionados' ({total} links para páginas de dados)")


def resolver_pendentes(S):
    """Troca @@MUN@@ pelo link do município quando a página existe; remove o marcador caso contrário."""
    n = 0
    for u, (alvo, nome) in getattr(S, "mun_pend", {}).items():
        f = S.OUT / u.strip("/") / "index.html"
        if not f.exists(): continue
        ok = alvo in S.urls; n += ok
        rep = f'o <a href="{S.PREFIX}{alvo}">perfil de {E(nome)}</a>, ' if ok else ""
        f.write_text(f.read_text(encoding="utf-8").replace("@@MUN@@", rep), encoding="utf-8")
    print(f"Emendas por município: {n} link(s) de volta ao perfil do município")
