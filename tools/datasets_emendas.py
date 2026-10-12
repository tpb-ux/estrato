"""Emendas parlamentares ao Orçamento da União desde 2023, por autor e por município. Incremental com cache.

Rodado pela VPS no ciclo pesado diário (ops/ciclo.sh executa tools/datasets_*.py às PORTAL_DATASETS_HORA).
Fonte oficial, pública e sem chave: download em lote do Portal da Transparência (CGU),
  https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO
  -> EmendasParlamentares.csv (empenhado/liquidado/pago por emenda e localidade)
  -> EmendasParlamentares_PorFavorecido.csv (valor recebido por favorecido, mês, UF e município)
A API do Portal (que exige chave) NÃO é usada.
Privacidade: favorecidos pessoa física e empresários individuais (MEI, cujo nome é o da pessoa) não são guardados por nome;
entram só em totais agregados. Saída: data/emendas/emendas.json.gz + meta.json (no git); bruto em data/cache/emendas.
"""
import collections, csv, datetime as dt, email.utils, gzip, io, json, re, sys, time, urllib.request, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/cache/emendas"; OUT = ROOT / "data/emendas"
CACHE.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
URL = "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO"
ANO0 = 2023
UA = {"User-Agent": "Estrato/1.0 (dados abertos; contato no site)"}


def baixar(url, dest):
    h = dict(UA)
    if dest.exists(): h["If-Modified-Since"] = email.utils.formatdate(dest.stat().st_mtime, usegmt=True)
    err = None
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=600) as r:
                tmp = dest.with_suffix(".tmp"); tmp.write_bytes(r.read()); tmp.replace(dest); return True
        except urllib.error.HTTPError as e:
            if e.code == 304: return False
            err = e
        except Exception as e: err = e
        time.sleep(15 * (i + 1))
    print("falha", url, err, file=sys.stderr); return False


def val(s):
    try: return float((s or "0").replace(".", "").replace(",", "."))
    except ValueError: return 0.0


def main():
    z = CACHE / "EmendasParlamentares.zip"; novo = baixar(URL, z)
    if not z.exists(): print("sem arquivo"); return
    if not novo and (OUT / "emendas.json.gz").exists() and "--forcar" not in sys.argv: print("emendas: sem mudança"); return
    zf = zipfile.ZipFile(z); abre = lambda n: csv.DictReader(io.TextIOWrapper(zf.open(n), encoding="latin1"), delimiter=";")
    dd = lambda: collections.defaultdict(float)
    A = {}; M = {}; FN = {}; tot = collections.Counter()
    def aut(cod, nome): return A.setdefault(cod, {"nome": nome.strip(), "anos": {}, "tipos": dd(), "func": dd(), "loc": dd(), "mun": dd(), "fav": dd(), "n": 0})
    for r in abre("EmendasParlamentares.csv"):
        try: ano = int(r["Ano da Emenda"])
        except ValueError: continue
        if ano < ANO0: continue
        cod = r["Código do Autor da Emenda"].strip()
        if not cod or cod == "S/I": continue
        a = aut(cod, r["Nome do Autor da Emenda"]); a["n"] += 1
        y = a["anos"].setdefault(str(ano), {"emp": 0.0, "liq": 0.0, "pago": 0.0, "rap": 0.0, "n": 0}); e = val(r["Valor Empenhado"])
        y["emp"] += e; y["liq"] += val(r["Valor Liquidado"]); y["pago"] += val(r["Valor Pago"]); y["rap"] += val(r["Valor Restos A Pagar Pagos"]); y["n"] += 1
        a["tipos"][r["Tipo de Emenda"].strip()] += e; a["func"][r["Nome Função"].strip()] += e; a["loc"][r["Localidade de aplicação do recurso"].strip()] += e
        tot[str(ano)] += e
    for r in abre("EmendasParlamentares_PorFavorecido.csv"):
        am = r["Ano/Mês"].strip()
        if am[:4] < str(ANO0): continue
        cod = r["Código do Autor da Emenda"].strip(); v = val(r["Valor Recebido"]); uf = r["UF Favorecido"].strip(); mn = r["Município Favorecido"].strip()
        tf = r["Tipo Favorecido"].strip(); nat = r["Natureza Jurídica"].strip(); doc = re.sub(r"\D", "", r["Código do Favorecido"])
        if cod and cod != "S/I":
            a = aut(cod, r["Nome do Autor da Emenda"])
            if uf and mn and mn != "Sem informação": a["mun"][f"{uf}|{mn}"] += v
        if not (uf and mn) or mn == "Sem informação": continue
        m = M.setdefault(f"{uf}|{mn}", {"anos": dd(), "autores": dd(), "tipos": dd(), "nat": dd(), "fav": dd(), "pf": 0.0})
        m["anos"][am[:4]] += v; m["tipos"][r["Tipo de Emenda"].strip()] += v; m["nat"][nat or "Sem informação"] += v
        if cod and cod != "S/I": m["autores"][cod] += v
        if tf == "Pessoa Jurídica" and len(doc) == 14 and nat != "Empresário (Individual)" and not re.search(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}", r["Favorecido"]):
            m["fav"][doc] += v; FN[doc] = r["Favorecido"].strip()
            if cod and cod != "S/I": A[cod]["fav"][doc] += v
        else: m["pf"] += v
    r2 = lambda d: {k: round(v, 2) for k, v in d.items() if abs(v) >= 0.005}
    for a in A.values():
        for k in ("tipos", "func", "loc", "mun", "fav"): a[k] = r2(a[k])
        for y in a["anos"].values():
            for k in ("emp", "liq", "pago", "rap"): y[k] = round(y[k], 2)
    for m in M.values():
        for k in ("anos", "autores", "tipos", "nat", "fav"): m[k] = r2(m[k])
        m["pf"] = round(m["pf"], 2)
    usados = {d for a in A.values() for d in a["fav"]} | {d for m in M.values() for d in m["fav"]}
    out = {"autores": A, "mun": M, "fav_nomes": {d: FN[d] for d in usados}}
    (OUT / "emendas.json.gz").write_bytes(gzip.compress(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode(), 9, mtime=0))
    info = zf.getinfo("EmendasParlamentares.csv").date_time
    meta = {"coletado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "arquivo_gerado_em": "%04d-%02d-%02d" % info[:3], "fonte": URL, "autores": len(A), "municipios": len(M), "empenhado_por_ano": {k: round(v, 2) for k, v in sorted(tot.items())}}
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"); print("emendas", meta)
if __name__ == "__main__": main()
