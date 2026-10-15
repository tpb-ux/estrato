#!/usr/bin/env python3
"""Diagnóstico da coleta: por feed, quantos itens e por que cada um é barrado (sem baixar fotos). Uso: python tools/diag_feeds.py [--vies regional] [--img] [--lista]"""
import os, sys, re, collections, datetime as dt, urllib.request
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, ".")
import feedparser
from core import fetch as F
ap = sys.argv[1:]; vies = ap[ap.index("--vies") + 1] if "--vies" in ap else None
cfg = F._F; cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=cfg.get("max_idade_dias", 3))
tot = collections.Counter()
for fd in cfg["feeds"]:
    if vies and fd.get("vies") != vies: continue
    try: d = feedparser.parse(urllib.request.urlopen(urllib.request.Request(fd["url"], headers={"User-Agent": F.UA}), timeout=20).read())
    except Exception as ex: print(f"## {fd['nome']}: ERRO {str(ex)[:60]}"); continue
    c = collections.Counter(); cimg = 0
    for e in d.entries:
        link, title = e.get("link", ""), F.clean(e.get("title", ""))
        tp = e.get("published_parsed") or e.get("updated_parsed")
        when = dt.datetime(*tp[:6], tzinfo=dt.timezone.utc) if tp else dt.datetime.now(dt.timezone.utc)
        if F.feed_image(e): cimg += 1
        summ = F.clean(e.get("summary", ""))
        if len(summ) < 40 or F.norm(summ).startswith(F.norm(title)[:40]): summ = f"{title}. Notícia publicada por {fd['nome']}."
        why = None
        if when < cutoff: why = "antiga"
        elif len(title) < 25: why = "título curto"
        if not why: why = F.blocked(cfg, fd["nome"], link, title, "" if summ.startswith(title) else summ, fd.get("confiavel", False), fd.get("vies"))
        ed = fd.get("editoria") or F.classify(title + " " + summ)
        if not why: why = F.restrito(cfg, ed, title, summ) or F.restrito(cfg, "*", title, summ)
        if not why and fd.get("vies") != "oficial": why = F.opiniao(cfg, link, title, fd.get("vies"))
        if not why and fd.get("vies") != "oficial":
            hit = F.eleitoral_nao_oficial(cfg, title, summ)
            if hit: why = f"eleitoral ({hit})"
        if not why and "--img" in ap:
            import io; from PIL import Image
            u = F.feed_image(e) or F.og_image(link)
            try:
                im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": F.UA, "Referer": u}), timeout=20).read(15_000_000))); ok = im.width >= 300
            except Exception: ok = False
            if not ok: why = "sem foto"
        k = re.sub(r"\(.*", "", why or "PASSA").strip(); c[k] += 1
        if "--lista" in ap: print(f"   {'OK ' if not why else 'x  '} {title[:80]} | {why or ''}")
    tot.update(c)
    print(f"## {fd['nome']} [{fd.get('vies')}]: {len(d.entries)} itens, {cimg} c/ imagem no feed; {dict(c)}")
print(dict(tot))
