""" /instablog/: posts publicados no Instagram @agenciaestrato.
Fonte: data/instablog.json (gerado por tools/sync_instablog.py a partir do registro de publicação).
Não inventa posts nem métricas. Cada item leva ao post original. Página por post só quando há tema.
"""
import json
from pathlib import Path
from core.site import E
from .dados import data_br, num

PERFIL = "https://www.instagram.com/agenciaestrato/"
HANDLE = "@agenciaestrato"

def carregar(S):
    f = S.ROOT / "data/instablog.json"
    if not f.is_file():
        return {"posts": [], "perfil": PERFIL}
    d = json.loads(f.read_text(encoding="utf-8"))
    posts = []
    seen = set()
    for p in d.get("posts") or []:
        u = (p.get("ig_url") or "").strip()
        if not u.startswith("https://www.instagram.com/") or u in seen:
            continue
        if not (p.get("data") or "").strip():
            continue
        seen.add(u)
        posts.append(p)
    posts.sort(key=lambda x: (x.get("data", ""), x.get("slug", "")), reverse=True)
    return {"posts": posts, "perfil": d.get("perfil") or PERFIL, "gerado_em": d.get("gerado_em")}

def _ext(href):
    if not href:
        return False
    if href.startswith("/"):
        return False
    return href.startswith("http")

def pagina_post(S, p, site):
    tema = (p.get("tema") or "").strip()
    if not tema:
        return None
    slug = p["slug"]
    u = f"/instablog/{slug}/"
    data = p["data"]
    ig = p["ig_url"]
    fonte = (p.get("fonte") or "").strip()
    credito = (p.get("credito") or "").strip()
    materia = (p.get("url_materia") or "").strip()
    collab = (p.get("collab") or "").strip()
    lin = [f'<article class="post"><h1>{E(tema)}</h1>',
           f'<p class="snippet">Post publicado no Instagram {E(HANDLE)} em {data_br(data)}.</p>',
           f'<p>Veja o <a href="{E(ig)}" target="_blank" rel="noopener">post original no Instagram</a>.</p>']
    if fonte:
        lin.append(f"<p>Fonte da pauta: {E(fonte)}.</p>")
    if materia and materia.startswith("http"):
        lin.append(f'<p>Matéria de origem: <a href="{E(materia)}" target="_blank" rel="noopener">{E(materia)}</a>.</p>')
    elif materia and materia.startswith("/"):
        lin.append(f'<p>Página relacionada: <a href="{E(materia)}">{E(materia)}</a>.</p>')
    if credito:
        lin.append(f"<p>Crédito da imagem no pacote: {E(credito)}.</p>")
    if collab:
        lin.append(f"<p>Collab registrada: @{E(collab)}.</p>")
    lin.append(f'<p><a href="/instablog/">Todos os posts do Instablog</a> · <a href="{E(PERFIL)}" target="_blank" rel="noopener">{E(HANDLE)}</a></p></article>')
    desc = f"{tema} Post do Instagram {HANDLE} em {data_br(data)}, com link para o original."
    if len(desc) > 160:
        desc = (tema[:120].rstrip() + f" Post do {HANDLE} em {data_br(data)}.")[:160]
    ld = {"@type": "SocialMediaPosting", "url": S.BASE + u, "headline": tema, "datePublished": data,
          "author": {"@type": "Organization", "name": "Agência Estrato", "url": PERFIL, "sameAs": [PERFIL]},
          "sharedContent": {"@type": "SocialMediaPosting", "url": ig}}
    faqs = [
        ("Onde está o post original?", f'<a href="{E(ig)}" target="_blank" rel="noopener">No Instagram {E(HANDLE)}</a>.'),
        ("Quando foi publicado?", f"Em {data_br(data)}, conforme o registro de publicação do perfil."),
        ("O Estrato reproduz o post inteiro?", "Não. Esta página identifica o post e leva ao original no Instagram."),
        ("De onde veio a pauta?", (f"Da fonte {E(fonte)}." if fonte else "Do registro de publicação do perfil, com link para o original.")),
        ("Onde estão os outros posts?", 'No <a href="/instablog/">Instablog</a>.'),
    ]
    S.write(u, S.page(f"{tema} | Instablog | {site}", desc, u, "".join(lin), faqs=faqs,
                      crumbs=[("Instablog", "/instablog/"), (tema[:80], u)], jsonld=ld, og_type="article"),
            familia="instablog", lastmod=data, faq_min=0)
    return u

def _sync_se_houver_fonte(S):
    """Atualiza data/instablog.json se o registro de publicações estiver no disco."""
    script = S.ROOT / "tools/sync_instablog.py"
    if not script.is_file():
        return
    import runpy
    try:
        runpy.run_path(str(script), run_name="__main__")
    except Exception as e:
        print(f"instablog: sync ignorado ({e})")

def build(S):
    site = S.CFG["site_name"]
    _sync_se_houver_fonte(S)
    d = carregar(S)
    posts, perfil = d["posts"], d["perfil"]
    com_tema = [p for p in posts if (p.get("tema") or "").strip()]
    urls = []
    for p in com_tema:
        u = pagina_post(S, p, site)
        if u:
            urls.append(u)
    # hub: lista todos os posts com URL (os sem tema entram só como data + link)
    lis = []
    for p in posts:
        data = data_br(p["data"])
        ig = p["ig_url"]
        tema = (p.get("tema") or "").strip()
        if tema:
            href = f"/instablog/{p['slug']}/"
            lis.append(f'<li><time datetime="{E(p["data"])}">{E(data)}</time> · <a href="{E(href)}">{E(tema)}</a> · <a href="{E(ig)}" target="_blank" rel="noopener">Instagram</a></li>')
        else:
            lis.append(f'<li><time datetime="{E(p["data"])}">{E(data)}</time> · <a href="{E(ig)}" target="_blank" rel="noopener">Post no Instagram</a></li>')
    body = (
        f'<article class="post"><h1>Instablog: posts do {E(HANDLE)}</h1>'
        f'<p class="snippet">Os {num(len(posts))} posts publicados no Instagram {E(HANDLE)}, com link para o original. '
        f"O Estrato não reproduz o conteúdo inteiro do Instagram.</p>"
        f'<p>Perfil: <a href="{E(perfil)}" target="_blank" rel="noopener">{E(HANDLE)}</a>.</p>'
        f'<ol class="instablog">' + "".join(lis) + "</ol>"
        f'<p class="src">Fonte: registro de publicação do perfil {E(HANDLE)}. Atualizado em {E(d.get("gerado_em") or "")}.</p></article>'
    )
    faqs = [
        ("O que é o Instablog?", f"Uma lista dos posts publicados no Instagram {E(HANDLE)}, cada um com link para o original."),
        ("O portal copia o post inteiro?", "Não. Cada item identifica o post e leva à publicação original no Instagram."),
        ("De onde vêm os itens?", f"Do registro de publicação do perfil {E(HANDLE)}, sincronizado no arquivo de dados do portal."),
        ("Com que frequência a lista muda?", "Quando o arquivo de publicações é sincronizado e o site é gerado de novo."),
        ("Como falar com a agência?", 'Pela página de <a href="/contato/">contato</a> ou pelo próprio perfil no Instagram.'),
    ]
    ld = {"@type": "CollectionPage", "name": f"Instablog {HANDLE}", "url": S.BASE + "/instablog/",
          "mainEntity": S.itemlist([(p.get("tema") or p["data"], f"/instablog/{p['slug']}/") for p in com_tema[:50]])}
    S.write("/instablog/", S.page(f"Instablog: posts do {HANDLE} | {site}",
                                  f"{num(len(posts))} posts do Instagram {HANDLE}, com link para cada publicação original.",
                                  "/instablog/", body, faqs=faqs, crumbs=[("Instablog", "/instablog/")], jsonld=ld),
            familia="paginas", lastmod=d.get("gerado_em") or (posts[0]["data"] if posts else None))
    return {"urls": ["/instablog/"] + urls, "n": len(posts)}
