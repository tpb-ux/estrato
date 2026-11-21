#!/usr/bin/env python3
"""Mapa da Midia: verifica cada afirmacao de data/midia/base.yaml contra a fonte citada (Wikipedia em portugues, API publica, sem chave).
Para cada afirmacao, procura o trecho (campo q) no texto da versao atual do artigo (campo w). Achou => verificado (data, revisao); nao achou => nao verificado.
Saida: data/midia/verificacao.json {"gerado", "fontes": {titulo: {url, revid, ok}}, "afirmacoes": [{ok, data, revid}]} na mesma ordem de base.yaml.
Uso: python tools/datasets_midia.py [--force]. Refaz se > 7 dias. Nao inventa dado: se a fonte falha, mantem o resultado anterior e marca erro."""
import json, pathlib, re, sys, time, urllib.parse, urllib.request
import yaml
ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = ROOT / "data/midia/base.yaml"; OUT = ROOT / "data/midia/verificacao.json"
UA = {"User-Agent": "EstratoBot/1.0 (https://estrato.com.br; mapa da midia; verificacao de fontes)"}
def limpa(t):
    t = re.sub(r"<ref[^>]*?/>|<ref.*?</ref>", "", t, flags=re.S); t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t); t = re.sub(r"'''?", "", t); t = re.sub(r"<[^>]+>", "", t); return re.sub(r"\s+", " ", t).strip()
def norm(t):
    t = t.replace("\u2013", "-").replace("\u2014", "-").replace("\xa0", " ").replace("’", "'")
    t = re.sub(r"<ref[^>]*?/>|<ref.*?</ref>", "", t, flags=re.S); t = re.sub(r"<br\s*/?>", " ", t); t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"'''?", "", t); t = re.sub(r"\s*=\s*", "=", t); t = re.sub(r"\s+", " ", t)
    return t.strip().lower()
def wikitext(titulo):
    u = "https://pt.wikipedia.org/w/api.php?" + urllib.parse.urlencode({"action": "parse", "page": titulo, "prop": "wikitext", "redirects": 1, "format": "json"})
    for t in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r: j = json.load(r)
            p = j.get("parse") or {}
            if p: return p["title"], p["wikitext"]["*"], p.get("revid")
        except Exception: time.sleep(2 * (t + 1))
    return None, None, None
def main():
    if OUT.exists() and "--force" not in sys.argv and time.time() - OUT.stat().st_mtime < 7 * 86400: print("Midia: < 7 dias, nada a fazer"); return
    base = yaml.safe_load(BASE.read_text(encoding="utf-8")); old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    hoje = time.strftime("%Y-%m-%d"); fontes = {}; res = []
    for i, a in enumerate(base["afirmacoes"]):
        w = a["w"]
        if w not in fontes:
            t, txt, rev = wikitext(w)
            fontes[w] = {"titulo": t, "revid": rev, "url": f"https://pt.wikipedia.org/wiki/{urllib.parse.quote((t or w).replace(' ', '_'))}", "perm": f"https://pt.wikipedia.org/w/index.php?title={urllib.parse.quote((t or w).replace(' ', '_'))}&oldid={rev}" if rev else None,
                         "texto": norm(txt) if txt else None}
        f = fontes[w]
        if f["texto"] is None:
            prev = (old.get("afirmacoes") or [None] * (i + 1))[i] if old else None
            res.append(dict(prev, erro="fonte indisponivel na ultima tentativa") if prev else {"ok": False, "data": None, "revid": None, "erro": "fonte indisponivel"}); continue
        ok = norm(a["q"]) in f["texto"]
        res.append({"ok": ok, "data": hoje if ok else None, "revid": f["revid"]})
    for f in fontes.values(): f.pop("texto", None)
    OUT.write_text(json.dumps({"gerado": hoje, "fontes": fontes, "afirmacoes": res}, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(1 for r in res if r["ok"]); print(f"Midia: {n}/{len(res)} afirmacoes verificadas ({len(fontes)} fontes)")
    for a, r in zip(base["afirmacoes"], res):
        if not r["ok"]: print("  NAO VERIFICADO:", a["s"], "|", a["w"], "|", a["q"][:70])
if __name__ == "__main__": main()
