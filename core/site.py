"""Motor do site: configuração, layout, page()/write(), registro de URLs, validações de qualidade."""
import datetime as dt, hashlib, html, json, os, re, unicodedata
from pathlib import Path
from urllib.parse import urlparse
import yaml
from .qualidade import INDEX_ROBOTS, set_robots

E = html.escape

def slugify(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def words(h):
    return len(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.S)).split())

def fit(t, n):
    return t if len(t) <= n else t[:n - 1].rsplit(" ", 1)[0].rstrip(",;:-–") + "…"

_STOP = {"de", "da", "do", "das", "dos", "e", "em", "a", "o", "as", "os", "para", "com", "que", "no", "na", "nos", "nas", "por", "ao", "à"}

def fit_clean(t, n, minimo=0):
    """Corta em fronteira natural (vírgula, dois-pontos, travessão, ponto) sem deixar conectivo pendurado; só usa '…' se não houver fronteira."""
    if len(t) <= n: return t
    head = t[:n]
    cuts = [m.start() for m in re.finditer(r"(?:,|;|:| –| -|\.)\s|\s(?:e|ou)\s", head + " ") if m.start() >= minimo]
    if cuts: return head[:cuts[-1]].rstrip(",;:-– ")
    w = t[:n - 1].rsplit(" ", 1)[0].split(" ")
    while len(w) > 1 and w[-1].lower().strip(",;:") in _STOP: w.pop()
    return " ".join(w).rstrip(",;:-–") + "…"

def fit_title(title, site, n=65):
    """Título final: base + ' | Marca', nunca cortado no separador nem sem a marca. Aceita modelos antigos que já trazem '| Marca'."""
    parts = [x.strip() for x in title.split(" | ")]
    if len(parts) > 1 and parts[-1] == site: parts.pop()
    suf = f" | {site}"
    while len(parts) > 1 and len(" | ".join(parts)) + len(suf) > n: parts.pop(-1 if len(parts) > 2 else 1)  # descarta o segmento intermediário/de seção
    base = " | ".join(parts)
    if len(base) + len(suf) > n:
        c = fit_clean(base, n - len(suf), minimo=25)
        if not c.endswith("…") and len(c) >= 0.75 * len(base): return c + suf  # corte em fronteira natural que preserva o essencial, com marca
        if len(base) <= n: return base  # título completo e distinto vale mais que a marca (o buscador reaplica a marca); nunca cortar o que distingue a página
        base = c
    return base + suf

class QualityError(SystemExit): pass

class Site:
    def __init__(self, root):
        self.ROOT = Path(root)
        self.CFG = yaml.safe_load((self.ROOT / "config.yaml").read_text(encoding="utf-8"))
        c = self.CFG
        self.BASE = (os.environ.get("PORTAL_BASE_URL") or c["base_url"]).rstrip("/")
        self.PREFIX = urlparse(self.BASE).path.rstrip("/")
        self.OUT = self.ROOT / "public"
        self.EDS = {e["slug"]: e for e in c["editorias"]}
        # noindex global (pré-lançamento/prévia): env PORTAL_NOINDEX=1 ou config noindex_global: true
        ev = os.environ.get("PORTAL_NOINDEX", "")
        self.NOINDEX = ev == "1" or (ev != "0" and bool(c.get("noindex_global")))  # PORTAL_NOINDEX=0 força desligado (testes)
        # links só do lançamento (alcançabilidade de /midia/ e /mapas/): entram no menu "Dados" e no rodapé quando noindex_global é desligado
        # (mapas: só com mapas.ativo e data liberada). Pré-lançamento as seções ficam sem links de entrada, de propósito.
        lc = c.get("links_lancamento") or {}; hoje_ = dt.date.today().isoformat(); mp = c.get("mapas") or {}
        for grupo in (["midia"] if not self.NOINDEX else []) + (["mapas"] if not self.NOINDEX and mp.get("ativo") and hoje_ >= str(mp.get("liberar_em", "9999")) else []):
            g = lc.get(grupo) or {}
            (c.setdefault("menu", {}).setdefault("referencia", [])).extend(g.get("menu") or [])
            for col in c.get("rodape", []):
                if col.get("titulo") == g.get("rodape_coluna"): col["links"].extend(g.get("rodape") or [])
        self.urls = {}       # path -> dict(idx, familia, lastmod, image, title, desc)
        self.thin, self.errors, self.ondas = set(), [], set()
        self.faq_stats = {"pseo_paginas": 0, "pseo_faqs": 0, "pseo_removidas": 0}
        self.css_v = ""
        self.nicho = c.get("nicho", "exemplo")
        sf = self.ROOT / "data/subcategorias.yaml"  # submenu de subcategorias no desktop (nichos/*/subcategorias.py)
        sd = yaml.safe_load(sf.read_text(encoding="utf-8")) if sf.exists() else {}
        self.SUBMENU = {k: [(x["nome"], f"/{k}/{x['slug']}/") for x in v] for k, v in sd.items() if isinstance(v, list)}

    # ---------- blocos reutilizáveis ----------
    def faq_html(self, faqs):
        return "".join(f'<details class="faq"><summary><h3>{E(q)}</h3></summary><p>{a}</p></details>' for q, a in faqs)

    def faq_ld(self, faqs):
        strip = lambda s: re.sub(r"<[^>]+>", "", s)
        return {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": strip(a)}} for q, a in faqs]}

    def crumbs(self, items):
        """items: [(nome, url)] sem a home."""
        h = '<nav class="crumbs" aria-label="Trilha"><a href="/">Início</a>' + "".join(f' › <a href="{u}">{E(n)}</a>' for n, u in items) + "</nav>"
        ld = {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": self.BASE + u} for i, (n, u) in enumerate([("Início", "/")] + items)]}
        return h, ld

    def table(self, head, rows, cap=None):
        th = "".join(f"<th>{E(h)}</th>" for h in head)
        tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
        return f'<div class="tw"><table>{f"<caption>{E(cap)}</caption>" if cap else ""}<thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'

    def itemlist(self, items):
        return {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": self.BASE + u, "name": n} for i, (n, u) in enumerate(items[:50])]}

    # ---------- layout ----------
    def site_ld(self):
        c, emp = self.CFG, self.CFG.get("empresa") or {}
        org = {"@type": "NewsMediaOrganization", "@id": self.BASE + "/#org", "name": c["site_name"], "url": self.BASE + "/",
               "logo": {"@type": "ImageObject", "url": self.BASE + c.get("publisher_logo", "/static/logo.png")},
               "publishingPrinciples": self.BASE + "/politica-editorial/", "correctionsPolicy": self.BASE + "/correcoes/", "actionableFeedbackPolicy": self.BASE + "/correcoes/"}
        if emp.get("razao_social"):
            en = emp.get("endereco") or {}
            org.update(legalName=emp["razao_social"], taxID=emp.get("cnpj"), address={"@type": "PostalAddress", "streetAddress": en.get("logradouro"), "addressLocality": en.get("cidade"),
                       "addressRegion": en.get("uf"), "postalCode": en.get("cep"), "addressCountry": "BR"})
        org["masthead"] = self.BASE + "/expediente/"
        if emp.get("email") or emp.get("formulario_url"):
            org["contactPoint"] = {"@type": "ContactPoint", "contactType": "editorial", "availableLanguage": "pt-BR", **({"email": emp["email"]} if emp.get("email") else {}), **({"url": emp["formulario_url"]} if emp.get("formulario_url") else {})}
        if emp.get("encarregado_lgpd") and emp.get("email"):
            cp = org.get("contactPoint"); cp = [cp] if isinstance(cp, dict) else (cp or [])
            org["contactPoint"] = cp + [{"@type": "ContactPoint", "contactType": "data protection", "name": emp["encarregado_lgpd"], "email": emp["email"], "availableLanguage": "pt-BR"}]
        if c.get("responsavel_editorial"): org["employee"] = {"@type": "Person", "name": c["responsavel_editorial"]}   # só renderiza se preenchido
        if emp.get("email"): org["email"] = emp["email"]
        if any(emp.get("redes") or []): org["sameAs"] = [r for r in emp["redes"] if r]
        return [org, {"@type": "WebSite", "@id": self.BASE + "/#site", "name": c["site_name"], "url": self.BASE + "/", "inLanguage": c.get("language", "pt-BR"), "publisher": {"@id": self.BASE + "/#org"},
                      "potentialAction": {"@type": "SearchAction", "target": self.BASE + "/busca/?q={q}", "query-input": "required name=q"}}]

    def faq_pseo(self, path, faqs):
        """Regra de FAQ: em páginas pSEO (prefixos em qualidade.faq_pseo) ficam no máximo N perguntas, só as que
        trazem dado da própria página (número na resposta). Hubs listados em faq_pseo.hubs mantêm o FAQ completo."""
        q = (self.CFG.get("qualidade") or {}).get("faq_pseo") or {}
        if not faqs or path.count("/") < 3 or not path.startswith(tuple(q.get("prefixos", []))) or path.startswith(tuple(q.get("hubs", []))) or path in (q.get("hubs_exatos") or []): return faqs, False
        keep = [(a, b) for a, b in faqs if re.search(r"\d", re.sub(r"<[^>]+>", "", b))][: q.get("max", 3)]
        st = self.faq_stats; st["pseo_paginas"] += 1; st["pseo_faqs"] += len(keep); st["pseo_removidas"] += len(faqs) - len(keep)
        return keep, True

    def page(self, title, desc, path, body, *, faqs=None, crumbs=None, jsonld=None, og_img=None, og_type="website", robots=None, h1=None):
        """Monta a página. faqs=[(pergunta, resposta_html)] vira seção visível + FAQPage idêntico. crumbs=[(nome,url)]."""
        c = self.CFG; graph = []
        faqs, pseo = self.faq_pseo(path, faqs)
        if crumbs is not None:
            ch, cl = self.crumbs(crumbs); body = ch + body; graph.append(cl)
        if faqs:
            body += f'<section class="faqs"><h2>Perguntas frequentes</h2>{self.faq_html(faqs)}</section>'
            if path not in ((c.get("qualidade") or {}).get("faq_sem_schema") or []): graph.append(self.faq_ld(faqs))  # páginas jurídicas: FAQ visível, sem FAQPage
        for j in (jsonld if isinstance(jsonld, list) else [jsonld] if jsonld else []):
            j = {k: v for k, v in j.items() if k != "@context"}
            if j.get("@type") in ("Article", "NewsArticle") and not j.get("image"): j["image"] = og_img or self.BASE + "/static/og-default.png"
            graph.append(j)
        self._last = {"faqs": len(faqs or []), "title": title, "pseo": pseo}
        title, desc = fit_title(title, c["site_name"], 65), (desc if len(desc) <= 160 else fit_clean(desc, 160, minimo=80))
        seg = path.strip("/").split("/")[0]
        canon = self.BASE + path; img = og_img or (f"{self.BASE}/static/og/{seg}.png" if seg in getattr(self, "og_ok", ()) else self.BASE + "/static/og-default.png")
        rb = "noindex,nofollow" if self.NOINDEX else (robots or INDEX_ROBOTS)
        vf = c.get("verificacao") or {}
        meta = f'<meta name="robots" content="{rb}">' if rb else ""
        if path == "/" and not self.NOINDEX:
            meta += (f'<meta name="google-site-verification" content="{E(vf["google"])}">' if vf.get("google") else "") + (f'<meta name="msvalidate.01" content="{E(vf["bing"])}">' if vf.get("bing") else "")
        ld = json.dumps({"@context": "https://schema.org", "@graph": graph + self.site_ld()}, ensure_ascii=False).replace("</", "<\\/")
        menu = c.get("menu") or {}
        sm = lambda s: (f'<div class="sm">' + "".join(f'<a href="{u}">{E(n)}</a>' for n, u in self.SUBMENU[s]) + "</div>") if self.SUBMENU.get(s) else ""
        nav_ed = "".join(f'<span class="edw"><a class="{"on" if path.startswith(f"/{s}/") else ""}" href="/{s}/">{E(e.get("curto", e["nome"]))}</a>{sm(s)}</span>' for s, e in self.EDS.items())
        extra = "".join(f'<a class="xtra {"on" if path.startswith(u) else ""}" href="{u}">{E(n)}</a>' for n, u in menu.get("barra", []))
        refs = "".join(f'<a href="{u}">{E(n)}</a>' for n, u in menu.get("barra", []) + menu.get("referencia", []))
        nav_all = "".join(f'<a href="/{s}/">{E(e["nome"])}</a>' for s, e in self.EDS.items())
        cols = "".join(f'<div><p class="fh">{E(col["titulo"])}</p>' + "".join(f'<a href="{u}">{E(n)}</a>' for n, u in col["links"]) + "</div>" for col in c.get("rodape", []))
        aviso = f'<div class="pre">{E(c["aviso_topo"])}</div>' if c.get("aviso_topo") else ""
        return f"""<!doctype html><html lang="{c.get('language', 'pt-BR')}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{E(title)}</title>{meta}<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{canon}"><link rel="stylesheet" href="/static/style.css?v={self.css_v}"><link rel="icon" href="/favicon.ico">
<link rel="alternate" type="application/rss+xml" title="{E(c['site_name'])}" href="/rss.xml"><meta name="theme-color" content="{E((c.get('tema') or {}).get('escuro', '#222'))}">
<meta property="og:site_name" content="{E(c['site_name'])}"><meta property="og:locale" content="pt_BR"><meta property="og:type" content="{og_type}"><meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canon}"><meta property="og:image" content="{E(img)}"><meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{ld}</script></head><body>{aviso}<header class="top"><div class="wrap hrow"><a class="logo" href="/"><img src="/static/logo.svg" alt="{E(c['site_name'])}" width="200" height="40"></a>
<div class="tag">{E(c['tagline'])}</div><button class="burger" id="mn-btn" aria-label="Abrir menu" aria-expanded="false" aria-controls="mn-drawer"><span></span><span></span><span></span></button></div></header>
<nav class="ed" aria-label="Editorias"><div class="wrap"><a class="{'pill' if path == '/' else ''}" href="/">Início</a>{nav_ed}{extra}{f'<details class="dd"><summary>{E(menu.get("rotulo_dropdown", "Referência"))}</summary><div class="ddm">{refs}</div></details>' if refs else ''}</div></nav>
<div class="drawer" id="mn-drawer" hidden><div class="dpanel" role="dialog" aria-modal="true" aria-label="Menu"><button class="dclose" id="mn-close" aria-label="Fechar menu">×</button>
<p class="fh">Editorias</p><a href="/">Início</a>{nav_all}<p class="fh">{E(menu.get("rotulo_dropdown", "Referência"))}</p>{refs}</div></div>
<script>(function(){{var b=document.getElementById('mn-btn'),d=document.getElementById('mn-drawer'),c=document.getElementById('mn-close');
function o(x){{d.hidden=!x;b.setAttribute('aria-expanded',x);document.body.style.overflow=x?'hidden':'';if(x)c.focus();else b.focus()}}
b.onclick=function(){{o(d.hidden)}};c.onclick=function(){{o(false)}};d.onclick=function(e){{if(e.target===d)o(false)}};
document.addEventListener('keydown',function(e){{if(e.key==='Escape'&&!d.hidden)o(false)}});
var a=document.querySelector('nav.ed a.on,nav.ed a.pill');if(a&&a.scrollIntoView&&innerWidth<860)a.scrollIntoView({{inline:'center',block:'nearest'}});
document.addEventListener('click',function(e){{var x=document.querySelector('details.dd[open]');if(x&&!x.contains(e.target))x.open=false}})}})();</script>
<main class="wrap" id="conteudo">{body}</main><footer><div class="wrap fgrid"><div><p class="fbrand">{E(c['site_name'])}</p><p>{E(c['tagline'])}</p></div>{cols}</div>
<div class="wrap fbot">© {dt.date.today().year} {E(c['site_name'])}{(' · ' + E((c.get('empresa') or {}).get('razao_social', ''))) if (c.get('empresa') or {}).get('razao_social') else ''}{(' · <a href="mailto:' + E(c['empresa']['email']) + '">' + E(c['empresa']['email']) + '</a>') if (c.get('empresa') or {}).get('email') else ''}{(' · <a href="' + E(c['empresa']['instagram']) + '" rel="me noopener" target="_blank">Instagram</a>') if (c.get('empresa') or {}).get('instagram') else ''}</div></footer></body></html>"""

    def write(self, path, txt, *, idx=True, familia="paginas", lastmod=None, image=None, faq_min=None, minw=False):
        """Grava a página e registra a URL. idx=False => noindex,follow (fora de sitemap/busca)."""
        if path in self.urls: self.errors.append(f"URL duplicada: {path}")
        q = self.CFG.get("qualidade") or {}
        minw = q.get("min_palavras_pseo", 300)
        if idx and (minw or familia not in ("paginas", "artigos")) and words(txt.split("<main", 1)[-1].split("</main>")[0]) < minw:
            idx = False; self.thin.add(path)
        ind = self.CFG.get("indexacao") or {}
        exc = ind.get("excecoes") or []
        if idx and os.environ.get("PORTAL_SEM_ONDAS") != "1" and familia in (ind.get("familias_noindex") or []) and not any(path == e or (e.endswith("*") and path.startswith(e[:-1])) for e in exc):  # lançamento em ondas
            idx = False; self.ondas.add(path)
        if not idx and not self.NOINDEX: txt = set_robots(txt, "noindex,follow")
        meta = getattr(self, "_last", {})
        if meta.get("pseo") and faq_min is None: faq_min = 0  # pSEO: 0 a 3 FAQs com dado
        if idx and meta.get("faqs", 0) < (faq_min if faq_min is not None else q.get("min_faqs", 5)):
            self.errors.append(f"{path}: indexável com {meta.get('faqs', 0)} FAQs (mínimo {q.get('min_faqs', 5)})")
        if lastmod and '"Dataset"' in txt: txt = self._dataset_modified(txt, str(lastmod)[:10])
        t = re.search(r"<title>(.*?)</title>", txt, re.S); d = re.search(r'<meta name="description" content="(.*?)"', txt)
        self.urls[path] = {"idx": idx, "familia": familia, "lastmod": lastmod, "image": image, "title": html.unescape(t.group(1)) if t else "", "desc": html.unescape(d.group(1)) if d else ""}
        f = self.OUT / path.lstrip("/"); f = f / "index.html" if path.endswith("/") else f
        al = getattr(self, "autolink", None)
        if al and (familia in self.autolink_familias or path in self.autolink_paths): txt, _n = al.aplicar(txt, path)
        self.urls[path]["h"] = hashlib.sha1(re.sub(r"\d{2}/\d{2}/\d{4}", "", txt.split("<main", 1)[-1].split("</main>")[0]).encode()).hexdigest()[:16]  # lastmod real (ver core/build.lastmods)
        if self.PREFIX: txt = re.sub(r'(href|src|action)="/(?!/)', lambda m: f'{m.group(1)}="{self.PREFIX}/', txt)
        f.parent.mkdir(parents=True, exist_ok=True); f.write_text(txt, encoding="utf-8")

    @staticmethod
    def _dataset_modified(txt, data):
        """Datasets sem dateModified ganham a data de coleta/atualização da página (lastmod do módulo)."""
        m = re.search(r'(<script type="application/ld\+json">)(.*?)(</script>)', txt, re.S)
        if not m: return txt
        try: ld = json.loads(m.group(2).replace("<\\/", "</"))
        except ValueError: return txt
        mud = False
        for n in ld.get("@graph", []):
            if isinstance(n, dict) and n.get("@type") == "Dataset" and not n.get("dateModified"): n["dateModified"] = data; mud = True
        if not mud: return txt
        novo = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
        return txt[:m.start(2)] + novo + txt[m.end(2):]

    def indexaveis(self, familia=None):
        return [u for u, m in self.urls.items() if m["idx"] and (familia is None or m["familia"] == familia)]
