#!/usr/bin/env python3
"""IBGE SIDRA (sem chave): Censo 2022 (tab. 4714: populacao, area, densidade) e PIB a precos correntes (tab. 5938), municipios e UFs.
Saida: data/ibge/ibge.json.gz  {"censo": 2022, "pib_ano": N, "m": {cod7: {pop, area, dens, pib}}, "uf": {cod2: {...}}}. Atualiza se > 30 dias."""
import gzip, json, sys, time, pathlib, urllib.request
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/ibge/ibge.json.gz"
def sidra(path):
    for t in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request("https://apisidra.ibge.gov.br/values/" + path, headers={"User-Agent": "Mozilla/5.0 Estrato"}), timeout=120) as r:
                return json.load(r)[1:]
        except Exception as e: time.sleep(3 * (t + 1)); err = e
    raise RuntimeError(f"{path}: {err}")
def fl(v):
    try: return float(v)
    except Exception: return None
def main():
    if OUT.exists() and "--force" not in sys.argv and time.time() - OUT.stat().st_mtime < 30 * 86400: print("IBGE: < 30 dias, nada a fazer"); return
    out = {"censo": 2022, "gerado": time.strftime("%Y-%m-%d"), "m": {}, "uf": {}}
    K = {"93": "pop", "614": "dens", "6318": "area"}
    for nivel, dest in (("n6", "m"), ("n3", "uf")):
        for r in sidra(f"t/4714/{nivel}/all/v/93,614,6318/p/2022"):
            v = fl(r["V"])
            if v is not None: out[dest].setdefault(r["D1C"], {})[K[r["D2C"]]] = v
        for r in sidra(f"t/5938/{nivel}/all/v/37/p/last"):
            v = fl(r["V"])
            if v is not None: out[dest].setdefault(r["D1C"], {})["pib"] = v * 1000; out["pib_ano"] = int(r["D3C"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as f: json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("IBGE:", len(out["m"]), "municipios;", len(out["uf"]), "UFs; PIB", out.get("pib_ano"))
if __name__ == "__main__": main()
