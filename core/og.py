"""Imagens OG por seção (1200x630), geradas no build com Pillow: uma por primeiro segmento da URL (ex.: /deputados/ -> static/og/deputados.png).
Sem fonte TTF disponível, não gera nada e as páginas continuam com og-default.png."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONTES = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"]

def _fonte(tam):
    for f in FONTES:
        if Path(f).exists(): return ImageFont.truetype(f, tam)
    return None

def _hex(h, d): h = (h or d).lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def gerar(S):
    secoes = dict((S.CFG.get("og_secoes") or {})); secoes.update({s: e["nome"] for s, e in S.EDS.items()})
    ft, fs, fb = _fonte(72), _fonte(34), _fonte(40)
    if not ft: return set()
    t = S.CFG.get("tema") or {}; bg, ac = _hex(t.get("escuro"), "#1B2430"), _hex(t.get("cor"), "#8A4B08")
    out = S.OUT / "static/og"; out.mkdir(parents=True, exist_ok=True); ok = set()
    for slug, nome in secoes.items():
        im = Image.new("RGB", (1200, 630), bg); d = ImageDraw.Draw(im); d.rectangle([0, 0, 24, 630], fill=ac)
        linhas, atual = [], ""
        for w in nome.split():
            if d.textlength((atual + " " + w).strip(), font=ft) > 980 and atual: linhas.append(atual); atual = w
            else: atual = (atual + " " + w).strip()
        linhas.append(atual)
        y = 250 - 45 * (len(linhas) - 1)
        for l in linhas[:3]: d.text((90, y), l, font=ft, fill=(255, 255, 255)); y += 90
        d.text((90, 90), S.CFG["site_name"].upper(), font=fb, fill=ac if sum(ac) > 200 else (230, 170, 90))
        d.text((90, 520), S.CFG.get("tagline", ""), font=fs, fill=(190, 198, 210))
        im.save(out / f"{slug}.png", optimize=True); ok.add(slug)
    return ok
