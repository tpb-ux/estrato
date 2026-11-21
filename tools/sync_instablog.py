"""Gera data/instablog.json a partir do registro de publicações do @agenciaestrato.
Não inventa posts nem métricas. Só entra item com URL real do Instagram.
Fontes, em ordem: INSTABLOG_JSONL, caminhos conhecidos no box, data/raw/.
"""
import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTES = [
    os.environ.get("INSTABLOG_JSONL", ""),
    "/workspace/gazeta-metrics/agenciaestrato/posts.jsonl",
    str(ROOT / "data/raw/agenciaestrato-posts.jsonl"),
]
IG = re.compile(r"https?://(?:www\.)?instagram\.com/(p|reel|tv)/([A-Za-z0-9_-]+)/?")

def norm_ig(s):
    m = IG.search(s or "")
    return f"https://www.instagram.com/{m.group(1)}/{m.group(2)}/" if m else ""

def pick(rs, keys):
    for r in rs:
        for k in keys:
            v = r.get(k)
            if v not in (None, "", []):
                return v
    return ""

def data_de(rs):
    for r in rs:
        for k in ("date", "posted_at", "ts", "ts_brt", "published_at"):
            s = str(r.get(k) or "")[:10]
            if re.match(r"20\d\d-\d\d-\d\d", s):
                return s
        for k in ("id", "package_id"):
            m = re.match(r"(20\d{6})", str(r.get(k) or ""))
            if m:
                d = m.group(1)
                return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    return ""

def caption_txt(rs):
    p = pick(rs, ("caption_ig", "caption"))
    if not p:
        return ""
    s = str(p)
    if s.startswith("/") and Path(s).is_file():
        try:
            return Path(s).read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    if "instagram.com" in s or s.startswith("http"):
        return ""
    if s.startswith("/") or s.endswith(".txt"):
        return ""
    return s.strip()

def main():
    src = next((Path(p) for p in FONTES if p and Path(p).is_file()), None)
    if not src:
        print("sync_instablog: nenhuma fonte encontrada; mantém data/instablog.json se existir")
        return 0
    by = {}
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        u = norm_ig(r.get("ig_url") or r.get("url") or r.get("permalink") or "")
        if not u:
            continue
        by.setdefault(u, []).append(r)
    posts = []
    for u, rs in by.items():
        tema = str(pick(rs, ("tema", "manchete", "theme")) or "").strip()
        d = data_de(rs)
        if not d:
            continue
        slug = IG.search(u).group(2).lower()
        item = {
            "slug": slug,
            "ig_url": u,
            "data": d,
            "tema": tema,
            "fonte": str(pick(rs, ("fonte",)) or "").strip(),
            "credito": str(pick(rs, ("credito",)) or "").strip(),
            "url_materia": str(pick(rs, ("url_materia",)) or "").strip(),
            "collab": str(pick(rs, ("collab",)) or "").strip().lstrip("@"),
            "id": str(pick(rs, ("id", "package_id")) or "").strip(),
        }
        # caption só se for texto (não caminho); não é obrigatório
        cap = caption_txt(rs)
        if cap and len(cap) <= 800:
            item["caption"] = cap
        posts.append(item)
    posts.sort(key=lambda x: (x["data"], x["slug"]), reverse=True)
    out = {
        "fonte": str(src),
        "perfil": "https://www.instagram.com/agenciaestrato/",
        "gerado_em": __import__("datetime").date.today().isoformat(),
        "posts": posts,
    }
    dest = ROOT / "data/instablog.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    com_tema = sum(1 for p in posts if p["tema"])
    print(f"sync_instablog: {len(posts)} posts únicos ({com_tema} com tema) de {src} -> {dest}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
