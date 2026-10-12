"""Baixa as fotos oficiais (Câmara/Senado) e grava WebP 240x320 em static/img/parl/. Idempotente."""
import io, json, urllib.request, concurrent.futures as cf
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "static/img/parl"; OUT.mkdir(parents=True, exist_ok=True)
def one(a):
    nome, url = a; f = OUT / f"{nome}.webp"
    if f.exists() or not url: return f.exists()
    try:
        d = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; EstratoBot/1.0)"}), timeout=30).read()
        im = Image.open(io.BytesIO(d)).convert("RGB"); w, h = im.size; r = 3 / 4
        if w / h > r: nw = int(h * r); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else: nh = int(w / r); im = im.crop((0, 0, w, nh))
        im.resize((240, 320), Image.LANCZOS).save(f, "WEBP", quality=78, method=6); return True
    except Exception as e: print("falhou", nome, e); return False
def main():
    deps = json.loads((ROOT / "data/deputados.json").read_text())["deputados"]; sens = json.loads((ROOT / "data/senadores.json").read_text())["senadores"]
    jobs = [(f"dep-{d['id']}", d["foto"]) for d in deps] + [(f"sen-{s['id']}", s["foto"]) for s in sens]
    with cf.ThreadPoolExecutor(2) as ex: ok = sum(ex.map(one, jobs))
    print(f"fotos ok: {ok}/{len(jobs)}")
if __name__ == "__main__": main()
