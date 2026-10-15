#!/usr/bin/env python3
"""SICONFI/Tesouro (API datalake, sem chave): DCA Anexo I-C (receitas) e I-E (despesas por função) de União, estados, DF e municípios.
Coleta uma vez (cache jsonl em data/cache/siconfi/, retomável) e só refaz se o resultado tiver > 30 dias (ou --force).
Saída compacta: data/siconfi/siconfi.json.gz  {"anos": [...], "entes": {ibge: {...}}}. Valores em reais (brutos, sem ajuste)."""
import gzip, json, re, sys, time, pathlib, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
ROOT = pathlib.Path(__file__).resolve().parent.parent
B = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
ANOS = [2023, 2024]
OUT = ROOT / "data/siconfi/siconfi.json.gz"; CACHE = ROOT / "data/cache/siconfi"
REC = {"ReceitasExcetoIntraOrcamentarias": "rec", "RO1.0.0.0.00.0.0": "rc", "RO1.1.1.0.00.0.0": "imp", "RO1.7.0.0.00.0.0": "tc", "RO2.0.0.0.00.0.0": "rk"}

def get(path, **q):
    url = f"{B}/{path}?" + urllib.parse.urlencode(q)
    for t in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Estrato"}), timeout=45) as r:
                return json.load(r)["items"]
        except Exception as e:
            time.sleep(1.5 * (t + 1)); err = e
    raise RuntimeError(f"{url}: {err}")

def ente(cod, ano):
    out = {}
    for it in get("dca", an_exercicio=ano, id_ente=cod, no_anexo="DCA-Anexo I-C"):
        if it["coluna"] == "Receitas Brutas Realizadas" and it["cod_conta"] in REC and it["valor"] is not None:
            out[REC[it["cod_conta"]]] = it["valor"]
    fun = {}
    for it in get("dca", an_exercicio=ano, id_ente=cod, no_anexo="DCA-Anexo I-E"):
        if it["coluna"] != "Despesas Empenhadas" or it["valor"] is None: continue
        c = it["conta"]
        if c.startswith("Despesas Exceto Intra"): out["desp"] = it["valor"]
        elif re.match(r"^\d\d - ", c): fun[c[:2]] = [c[5:], it["valor"]]
    if fun: out["fun"] = fun
    return out

def main():
    force = "--force" in sys.argv; lim = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--limite=")), None)
    if OUT.exists() and not force and not lim and time.time() - OUT.stat().st_mtime < 30 * 86400:
        print("SICONFI: resultado com menos de 30 dias, nada a fazer"); return
    CACHE.mkdir(parents=True, exist_ok=True)
    entes = get("entes"); entes = [e for e in entes if e["esfera"] in "MEUD"]
    if lim: entes = entes[:lim]
    res = {}
    for ano in ANOS:
        cf = CACHE / f"{ano}.jsonl"; feito = {}
        if cf.exists():
            for l in cf.open(encoding="utf-8"):
                try: o = json.loads(l); feito[o["c"]] = o["d"]
                except Exception: pass
        falta = [e for e in entes if str(e["cod_ibge"]) not in feito]
        print(f"{ano}: {len(feito)} em cache, {len(falta)} a coletar", flush=True)
        with cf.open("a", encoding="utf-8") as fh, ThreadPoolExecutor(8) as ex:
            def job(e):
                try: return str(e["cod_ibge"]), ente(e["cod_ibge"], ano)
                except Exception as x: return str(e["cod_ibge"]), None
            for i, (c, d) in enumerate(ex.map(job, falta)):
                if d is None: continue
                feito[c] = d; fh.write(json.dumps({"c": c, "d": d}, ensure_ascii=False) + "\n")
                if i % 500 == 0: fh.flush(); print(f"  {i}/{len(falta)}", flush=True)
        res[ano] = feito
    out = {"anos": ANOS, "gerado": time.strftime("%Y-%m-%d"), "entes": {}}
    for e in entes:
        c = str(e["cod_ibge"]); an = {str(a): res[a][c] for a in ANOS if res[a].get(c)}
        out["entes"][c] = {"n": e["ente"], "uf": e["uf"] if e["esfera"] == "M" else None, "e": e["esfera"], "pop": e["populacao"], "cap": e["capital"].strip() == "1", "an": an}
    if not lim:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(OUT, "wt", encoding="utf-8") as f: json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("SICONFI:", len(out["entes"]), "entes;", {a: len(res[a]) for a in ANOS})

if __name__ == "__main__": main()
