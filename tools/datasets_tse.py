#!/usr/bin/env python3
"""TSE (CDN de dados abertos, sem chave): perfil do eleitorado atual e locais de votacao 2024, agregados por municipio (codigo TSE).
Fontes: cdn.tse.jus.br/estatistica/sead/odsele/perfil_eleitorado/perfil_eleitorado_ATUAL.zip e eleitorado_locais_votacao/eleitorado_local_votacao_2024.zip
Saida: data/tse/eleitorado.json.gz {"gerado","m": {cod_tse: {uf, n, tot, bio, def, mas, fem, fx:{faixa:n}, ins:{grau:n}, fac, zonas:[...]}}, "locais": {cod_tse: {z, l, s, e}}}
Apenas totais agregados (sem raca/cor, identidade de genero ou dado individual). Refaz se > 25 dias; locais 2024 so se faltar."""
import csv, gzip, io, json, pathlib, sys, tempfile, time, urllib.request, zipfile, collections
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/tse/eleitorado.json.gz"
B = "https://cdn.tse.jus.br/estatistica/sead/odsele/"
def baixar(rel):
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    for t in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(B + rel, headers={"User-Agent": "Mozilla/5.0 Estrato"}), timeout=300) as r:
                while True:
                    b = r.read(1 << 20)
                    if not b: break
                    tmp.write(b)
            tmp.close(); return pathlib.Path(tmp.name)
        except Exception as e: err = e; time.sleep(5); tmp.seek(0); tmp.truncate()
    raise RuntimeError(f"{rel}: {err}")
def linhas(p):
    z = zipfile.ZipFile(p); n = [x for x in z.namelist() if x.lower().endswith(".csv")][0]
    return csv.DictReader(io.TextIOWrapper(z.open(n), encoding="latin-1"), delimiter=";")
FX = {"1600": "16 a 17", "1700": "16 a 17", "1800": "18 a 24", "1900": "18 a 24", "2000": "18 a 24", "2124": "18 a 24", "2529": "25 a 34", "3034": "25 a 34", "3539": "35 a 44", "4044": "35 a 44", "4549": "45 a 59", "5054": "45 a 59", "5559": "45 a 59", "6064": "60 a 69", "6569": "60 a 69", "7074": "70 ou mais", "7579": "70 ou mais", "8084": "70 ou mais", "8589": "70 ou mais", "9094": "70 ou mais", "9599": "70 ou mais", "100": "70 ou mais"}
def faixa(cod, desc):
    c = cod.strip()
    if c in FX: return FX[c]
    d = desc.lower()
    import re
    m = re.match(r"(\d+)", d)
    if not m: return "Não informado"
    a = int(m.group(1))
    return "16 a 17" if a < 18 else "18 a 24" if a < 25 else "25 a 34" if a < 35 else "35 a 44" if a < 45 else "45 a 59" if a < 60 else "60 a 69" if a < 70 else "70 ou mais"
def main():
    old = json.loads(gzip.open(OUT, "rt", encoding="utf-8").read()) if OUT.exists() else None
    if old and "--force" not in sys.argv and time.time() - OUT.stat().st_mtime < 25 * 86400: print("TSE: < 25 dias, nada a fazer"); return
    p = baixar("perfil_eleitorado/perfil_eleitorado_ATUAL.zip"); m = {}; ger = ""
    try:
        for r in linhas(p):
            c = r["CD_MUNICIPIO"]; q = int(r["QT_ELEITORES"]); x = m.get(c)
            if x is None: x = m[c] = {"uf": r["SG_UF"], "n": r["NM_MUNICIPIO"], "tot": 0, "bio": 0, "def": 0, "mas": 0, "fem": 0, "fac": 0, "fx": collections.Counter(), "ins": collections.Counter(), "zonas": set()}
            x["tot"] += q; x["bio"] += int(r["QT_ELEITORES_BIOMETRIA"]); x["def"] += int(r["QT_ELEITORES_DEFICIENCIA"])
            g = r["DS_GENERO"]
            if g == "MASCULINO": x["mas"] += q
            elif g == "FEMININO": x["fem"] += q
            if r["TP_OBRIGATORIEDADE_VOTO"] == "Facultativo": x["fac"] += q
            x["fx"][faixa(r["CD_FAIXA_ETARIA"], r["DS_FAIXA_ETARIA"])] += q; x["ins"][r["DS_GRAU_INSTRUCAO"].capitalize()] += q; x["zonas"].add(int(r["NR_ZONA"])); ger = r["DT_GERACAO"]
    finally: p.unlink(missing_ok=True)
    for x in m.values(): x["fx"] = dict(x["fx"]); x["ins"] = dict(x["ins"]); x["zonas"] = sorted(x["zonas"])
    loc = old["locais"] if old and old.get("locais") else None
    if not loc:
        p = baixar("eleitorado_locais_votacao/eleitorado_local_votacao_2024.zip"); L = {}
        try:
            for r in linhas(p):
                if r["NR_TURNO"] != "1": continue
                a = L.setdefault(r["CD_MUNICIPIO"], {"z": set(), "l": set(), "s": set(), "e": 0})
                a["z"].add(r["NR_ZONA"]); a["l"].add((r["NR_ZONA"], r["NR_LOCAL_VOTACAO"])); a["s"].add((r["NR_ZONA"], r["NR_SECAO"])); a["e"] += int(r["QT_ELEITOR_SECAO"] or 0)
        finally: p.unlink(missing_ok=True)
        loc = {c: {"z": len(a["z"]), "l": len(a["l"]), "s": len(a["s"]), "e": a["e"]} for c, a in L.items()}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as f: json.dump({"gerado": time.strftime("%Y-%m-%d"), "base": ger, "m": m, "locais": loc}, f, ensure_ascii=False, separators=(",", ":"))
    print("TSE:", len(m), "municipios (base", ger + "),", len(loc), "com locais de votacao")
if __name__ == "__main__": main()
