"""Proposicoes relevantes da Camara (2023-2026) e contagem por tema, a partir dos arquivos em lote oficiais (sem chave).
Rodado pela VPS no ciclo pesado diario (ops/ciclo.sh). Cache bruto em data/cache/proposicoes (fora do git);
saida compacta em data/proposicoes/proposicoes.json.gz (no git).
Fonte: https://dadosabertos.camara.leg.br/arquivos/{proposicoes,proposicoesAutores,proposicoesTemas}/csv/<conjunto>-<ano>.csv (ano de apresentacao).
Selecao ("relevantes"): PEC, MPV e PLV (todas); PLP e PL nao arquivados com regime de urgencia, aprovada
ou transformada em norma; qualquer proposicao com votacao nominal no plenario (data/votacoes); PDL apenas se votada ou transformada em norma.
Proposicoes votadas anteriores a 2023 vem da API v2 (uma chamada por proposicao, com cache)."""
import csv, collections, datetime as dt, email.utils, glob, gzip, json, sys, time, urllib.request
from pathlib import Path
csv.field_size_limit(10**9)
ROOT = Path(__file__).resolve().parents[1]; CACHE = ROOT / "data/cache/proposicoes"; OUT = ROOT / "data/proposicoes"
CACHE.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
HOJE = dt.date.today(); ANOS = [2023, 2024, 2025, 2026]
UA = {"User-Agent": "Estrato/1.0 (dados abertos; contato no site)", "Accept": "application/json"}
URL = "https://dadosabertos.camara.leg.br/arquivos/{c}/csv/{c}-{a}.csv"; API = "https://dadosabertos.camara.leg.br/api/v2"


def baixar(url, dest, dias=1):
    """Baixa se nao existe ou se o cache tem mais de `dias` dias (If-Modified-Since)."""
    if dest.exists() and time.time() - dest.stat().st_mtime < dias * 86400: return
    h = dict(UA)
    if dest.exists(): h["If-Modified-Since"] = email.utils.formatdate(dest.stat().st_mtime, usegmt=True)
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=300) as r:
                tmp = dest.with_suffix(".tmp"); tmp.write_bytes(r.read()); tmp.replace(dest); return
        except urllib.error.HTTPError as e:
            if e.code == 304: dest.touch(); return
            if e.code == 404: return
        except Exception as e: err = e
        time.sleep(5 * (i + 1))
    print("falha", url, file=sys.stderr)


def api(path):
    f = CACHE / ("api-" + path.strip("/").replace("/", "_") + ".json")
    if f.exists(): return json.loads(f.read_text(encoding="utf-8"))
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(API + path, headers=UA), timeout=60) as r: d = json.loads(r.read().decode("utf-8")); f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8"); return d
        except Exception: time.sleep(3 * (i + 1))
    return None


def lerr(f):
    with open(f, encoding="utf-8-sig", newline="") as fh:
        yield from csv.DictReader(fh, delimiter=";")


def votadas():
    ids = set()
    for f in glob.glob(str(ROOT / "data/votacoes/camara-*.json.gz")):
        for v in json.loads(gzip.decompress(Path(f).read_bytes())):
            p = v.get("prop") or {}
            if p.get("id"): ids.add(str(p["id"]))
    return ids


def relevante(r, vot):
    t, s, rg = r["siglaTipo"], r["ultimoStatus_descricaoSituacao"], r["ultimoStatus_regime"]
    norma = "norma jur" in s.lower(); arq = s.startswith("Arquivada") or s.startswith("Tramitação Finalizada") and not norma
    if r["id"] in vot or norma: return True
    if t in ("PEC", "MPV", "PLV"): return True
    if t in ("PLP", "PL") and not arq and ("Urg" in rg or "Aprovad" in s or "Sanção" in s): return True
    return False


def linha(r):
    return {"id": int(r["id"]), "t": r["siglaTipo"], "tn": r["descricaoTipo"], "n": int(r["numero"] or 0), "a": int(r["ano"] or 0) or int(r["dataApresentacao"][:4]), "e": r["ementa"].strip(), "ed": r["ementaDetalhada"].strip(),
            "k": r["keywords"].strip(), "d": r["dataApresentacao"][:10], "it": r["urlInteiroTeor"], "pp": r["uriPropPrincipal"].rsplit("/", 1)[-1] if r["uriPropPrincipal"] else "",
            "dst": r["ultimoStatus_dataHora"][:10], "org": r["ultimoStatus_siglaOrgao"], "rg": r["ultimoStatus_regime"], "tr": r["ultimoStatus_descricaoTramitacao"], "sit": r["ultimoStatus_descricaoSituacao"],
            "desp": r["ultimoStatus_despacho"].strip()[:400], "ap": r["ultimoStatus_apreciacao"], "aut": [], "tem": []}


def main():
    for a in ANOS:
        for c in ("proposicoes", "proposicoesAutores", "proposicoesTemas"): baixar(URL.format(c=c, a=a), CACHE / f"{c}-{a}.csv", dias=1 if a >= HOJE.year - 1 else 7)
    vot = votadas(); sel = {}; total = collections.Counter(); tipos = {}
    for a in ANOS:
        f = CACHE / f"proposicoes-{a}.csv"
        if not f.exists(): continue
        for r in lerr(f):
            if not r["siglaTipo"] or not r["numero"]: continue
            ano = int(r["ano"] or 0) or int(r["dataApresentacao"][:4] or a)
            total[(ano, r["siglaTipo"])] += 1
            if relevante(r, vot): sel[r["id"]] = linha(r)
    falt = [i for i in vot if i not in sel]
    for i in falt:  # votadas antes de 2023: API v2
        d = api(f"/proposicoes/{i}")
        if not d: continue
        p = d["dados"]; st = p.get("statusProposicao") or {}
        sel[i] = {"id": int(i), "t": p["siglaTipo"], "tn": p["descricaoTipo"], "n": p["numero"], "a": p["ano"], "e": (p.get("ementa") or "").strip(), "ed": (p.get("ementaDetalhada") or "").strip(), "k": (p.get("keywords") or "").strip(),
                  "d": (p.get("dataApresentacao") or "")[:10], "it": p.get("urlInteiroTeor") or "", "pp": (p.get("uriPropPrincipal") or "").rsplit("/", 1)[-1], "dst": (st.get("dataHora") or "")[:10], "org": st.get("siglaOrgao") or "",
                  "rg": st.get("regime") or "", "tr": st.get("descricaoTramitacao") or "", "sit": st.get("descricaoSituacao") or "", "desp": (st.get("despacho") or "").strip()[:400], "ap": st.get("apreciacao") or "", "aut": [], "tem": []}
    uri2id = {}
    # autores e temas
    for a in ANOS:
        f = CACHE / f"proposicoesAutores-{a}.csv"
        if f.exists():
            for r in lerr(f):
                p = sel.get(r["idProposicao"])
                if p: p["aut"].append([int(r["idDeputadoAutor"] or 0), r["nomeAutor"], r["siglaPartidoAutor"], r["siglaUFAutor"], r["tipoAutor"], int(r["ordemAssinatura"] or 0)])
    for i in falt:
        p = sel.get(i)
        if p and not p["aut"]:
            d = api(f"/proposicoes/{i}/autores")
            for x in (d or {}).get("dados", []):
                idd = x["uri"].rsplit("/", 1)[-1] if "/deputados/" in (x.get("uri") or "") else "0"
                p["aut"].append([int(idd), x["nome"], "", "", x.get("tipo") or "", int(x.get("ordemAssinatura") or 0)])
    temas = collections.defaultdict(lambda: collections.Counter())
    for a in ANOS:
        f = CACHE / f"proposicoesTemas-{a}.csv"
        if not f.exists(): continue
        for r in lerr(f):
            if r["tema"]: temas[r["tema"]][(int(r["ano"] or a), r["siglaTipo"])] += 1
            pid = r["uriProposicao"].rsplit("/", 1)[-1]
            if pid in sel and r["tema"] not in sel[pid]["tem"]: sel[pid]["tem"].append(r["tema"])
    for i in falt:
        p = sel.get(i)
        if p and not p["tem"]:
            d = api(f"/proposicoes/{i}/temas"); p["tem"] = [x["tema"] for x in (d or {}).get("dados", [])]
    for p in sel.values(): p["aut"].sort(key=lambda x: x[5])
    props = sorted(sel.values(), key=lambda p: (-p["a"], p["t"], -p["n"]))
    out = {"coletado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "anos": ANOS, "props": props,
           "temas": {t: {f"{a}|{s}": n for (a, s), n in c.items()} for t, c in temas.items()}, "total": {f"{a}|{s}": n for (a, s), n in total.items()}}
    (OUT / "proposicoes.json.gz").write_bytes(gzip.compress(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9))
    print(f"{len(props)} proposicoes relevantes; {sum(1 for p in props if not p['aut'])} sem autor; {len(temas)} temas; votadas fora do lote: {len(falt)}", collections.Counter(p["t"] for p in props).most_common(8))


if __name__ == "__main__": main()
