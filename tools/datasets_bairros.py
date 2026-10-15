#!/usr/bin/env python3
"""IBGE Censo 2022, agregados por bairro (FTP aberto, sem chave): populacao, domicilios, area, sexo, faixas etarias, agua, esgoto e lixo.
Fonte: https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Bairro_csv/
Saida: data/bairros/bairros.json.gz {"gerado","fonte","b":[{c,n,m,mn,uf,a,p,d,dp,dpo,mm,h,f,i:[...],ag,es,lx}]}. Dado censitario fixo: so refaz se faltar ou com --force.
Sem cor/raca e sem dados individuais: so totais por bairro."""
import csv, gzip, io, json, pathlib, sys, time, urllib.request, zipfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/bairros/bairros.json.gz"
B = "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Bairro_csv/Agregados_por_bairros_"
ARQ = {"basico": "basico_BR_20260520", "demo": "demografia_BR", "dom1": "caracteristicas_domicilio1_BR", "dom2": "caracteristicas_domicilio2_BR_20250417"}
def baixar(k):
    for t in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(B + ARQ[k] + ".zip", headers={"User-Agent": "Mozilla/5.0 Estrato"}), timeout=180) as r: z = zipfile.ZipFile(io.BytesIO(r.read()))
            return list(csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="latin-1"), delimiter=";"))
        except Exception as e: err = e; time.sleep(5)
    raise RuntimeError(f"{k}: {err}")
def num(v):
    try: return float(str(v).replace(",", "."))
    except Exception: return None
def main():
    if OUT.exists() and "--force" not in sys.argv: print("Bairros: arquivo existe, nada a fazer"); return
    bas = baixar("basico"); dem = {r["CD_BAIRRO"]: r for r in baixar("demo")}; d1 = {r["CD_BAIRRO"]: r for r in baixar("dom1")}; d2 = {r["CD_BAIRRO"]: r for r in baixar("dom2")}
    out = []
    for r in bas:
        c = r["CD_BAIRRO"]; p = num(r["v0001"])
        if not p: continue
        x = dem.get(c, {}); y = d1.get(c, {}); z = d2.get(c, {})
        ida = [num(x.get(f"V{n:05d}")) for n in range(1031, 1042)]
        item = {"c": c, "n": r["NM_BAIRRO"], "m": r["CD_MUN"], "mn": r["NM_MUN"], "uf": r["NM_UF"], "a": num(r["AREA_KM2"]), "p": int(p), "d": num(r["v0002"]), "dp": num(r["v0003"]), "dpo": num(r["v0007"]), "mm": num(r["v0005"]),
                "h": num(x.get("V01007")), "f": num(x.get("V01008")), "i": ida if all(v is not None for v in ida) else None,
                "dm": num(y.get("V00001")), "ag": num(z.get("V00111")), "es": (num(z.get("V00309")) or 0) + (num(z.get("V00310")) or 0) if z.get("V00309") not in (None, ".") else None, "lx": (num(z.get("V00397")) or 0) + (num(z.get("V00398")) or 0) if z.get("V00397") not in (None, ".") else None}
        out.append(item)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as f: json.dump({"gerado": time.strftime("%Y-%m-%d"), "censo": 2022, "b": out}, f, ensure_ascii=False, separators=(",", ":"))
    print("Bairros:", len(out), "em", len({i["m"] for i in out}), "municipios")
if __name__ == "__main__": main()
