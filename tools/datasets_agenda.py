"""Agendas oficiais do Presidente e do Vice-Presidente da República desde 01/01/2023, uma página por dia em gov.br/planalto. Incremental com cache.

Rodado pela VPS no ciclo pesado diário (ops/ciclo.sh executa tools/datasets_*.py às PORTAL_DATASETS_HORA).
Fontes oficiais e públicas (sem chave):
  presidente: https://www.gov.br/planalto/pt-br/acompanhe-o-planalto/agenda-do-presidente-da-republica-lula/agenda-do-presidente-da-republica/<AAAA-MM-DD>
  vice:       https://www.gov.br/planalto/pt-br/vice-presidencia/agenda-vice-presidente-geraldo-alckmin/agenda-do-vice-presidente-geraldo-alckmin/<AAAA-MM-DD>
Dias com mais de 10 dias ficam congelados no cache; os últimos 10 dias são lidos de novo (a agenda pode ser corrigida).
Limite por execução (--max, padrão 400 dias novos) para não sobrecarregar o site; a carga inicial completa leva algumas execuções.
Saída: data/agenda/<presidente|vice>.json.gz (no git); HTML bruto em data/cache/agenda[/vice] (fora do git).
"""
import datetime as dt, gzip, html, json, re, sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/cache/agenda"; OUT = ROOT / "data/agenda"
CACHE.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
AGENDAS = {"presidente": ("https://www.gov.br/planalto/pt-br/acompanhe-o-planalto/agenda-do-presidente-da-republica-lula/agenda-do-presidente-da-republica/{d}", CACHE),
           "vice": ("https://www.gov.br/planalto/pt-br/vice-presidencia/agenda-vice-presidente-geraldo-alckmin/agenda-do-vice-presidente-geraldo-alckmin/{d}", CACHE / "vice")}
UA = {"User-Agent": "Estrato/1.0 (dados abertos; contato no site)"}
TXT = lambda s: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse(h):
    """Compromissos do dia: horário, título e local. A lista de participantes não é guardada."""
    out = []
    for b in h.split('class="item-compromisso-wrapper"')[1:]:
        b = b.split('class="compromisso-participantes"')[0] + b[b.find('class="compromisso-footer"'):] if 'class="compromisso-participantes"' in b else b
        g = lambda c: TXT((re.search(rf'class="{c}[^"]*"[^>]*>([\s\S]*?)</(?:div|time|span|h\d|p)>', b) or [None, ""])[1])
        t = g("compromisso-titulo")
        if t: out.append({"ini": g("compromisso-inicio"), "fim": g("compromisso-fim"), "titulo": t[:300], "local": g("compromisso-local")[:200]})
    return out


def coletar(qual, mx):
    URL, cache = AGENDAS[qual]; cache.mkdir(parents=True, exist_ok=True)
    hoje = dt.date.today(); d = dt.date(2023, 1, 1); novos = 0
    sv = OUT / f"{qual}.json.gz"; ja = set(json.loads(gzip.decompress(sv.read_bytes())).get("dias", {})) if sv.exists() else set()
    while d <= hoje:
        f = cache / f"{d.isoformat()}.html"; recente = (hoje - d).days <= 10
        if (not (f.exists() or d.isoformat() in ja) or recente) and novos < mx:
            try:
                with urllib.request.urlopen(urllib.request.Request(URL.format(d=d.isoformat()), headers=UA), timeout=60) as r: f.write_bytes(r.read())
            except urllib.error.HTTPError as e:
                if e.code == 404: f.write_bytes(b"")
            except Exception as e: print("falha", d, e, file=sys.stderr)
            novos += 1; time.sleep(1.0)
        d += dt.timedelta(days=1)
    saida = OUT / f"{qual}.json.gz"  # parte do que já está no git: a VPS não perde dias que ainda não tem no cache
    dias = json.loads(gzip.decompress(saida.read_bytes())).get("dias", {}) if saida.exists() else {}
    for f in sorted(cache.glob("*.html")):
        if f.stat().st_size: dias[f.stem] = parse(f.read_text(encoding="utf-8", errors="replace"))
        else: dias.setdefault(f.stem, [])
    dias = dict(sorted(dias.items()))
    out = {"fonte": URL.format(d="<AAAA-MM-DD>"), "coletado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "dias": dias}
    saida.write_bytes(gzip.compress(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode(), 9, mtime=0))
    print("agenda", qual, len(dias), "dias lidos,", sum(len(v) for v in dias.values()), "compromissos;", novos, "requisições")


def main():
    mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 400
    for q in ([sys.argv[sys.argv.index("--so") + 1]] if "--so" in sys.argv else AGENDAS): coletar(q, mx)
if __name__ == "__main__": main()
