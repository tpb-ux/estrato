#!/usr/bin/env python3
"""Prefeitos, vice-prefeitos e vereadores eleitos em 2024 (TSE, CDN de dados abertos, sem chave).
Fontes: cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2024.zip (candidatos e situacao de totalizacao) e votacao_candidato_munzona/votacao_candidato_munzona_2024.zip (votos nominais).
So eleicao ordinaria "Eleicoes Municipais 2024" (suplementares ficam de fora). Guarda apenas: nome de urna, partido, cargo, situacao e votos nominais.
NAO guarda CPF, titulo, e-mail, data de nascimento, cor/raca, bens (patrimonio), nem qualquer dado pessoal sensivel.
DESLIGADO por padrao: so roda se config.yaml prefeitos.ativo: true (e hoje >= liberar_em) ou com --force. Saida: data/tse/prefeitos.json.gz (ignorado pelo git ate a liberacao).
Formato: {"gerado", "m": {SG_UE: {"n": nome_ue, "uf", "p": [nome, partido, votos, turno], "v": [nome, partido, votos], "ve": [[nome, partido, votos], ...]}}}"""
import csv, collections, datetime as dt, gzip, io, json, pathlib, sys, time, urllib.request, zipfile, tempfile
import yaml
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data/tse/prefeitos.json.gz"
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
def linhas(z, nome):
    return csv.DictReader(io.TextIOWrapper(z.open(nome), encoding="latin-1"), delimiter=";")
def ativo():
    c = (yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8")).get("prefeitos") or {})
    return bool(c.get("ativo")) and dt.date.today().isoformat() >= str(c.get("liberar_em") or "9999-12-31")[:10]
def main():
    if "--force" not in sys.argv and not ativo(): print("Prefeitos: desligado por flag (config prefeitos.ativo); nada a fazer"); return
    if OUT.exists() and "--force" not in sys.argv and time.time() - OUT.stat().st_mtime < 20 * 86400: print("Prefeitos: < 20 dias, nada a fazer"); return
    zc = zipfile.ZipFile(baixar("consulta_cand/consulta_cand_2024.zip")); zv = zipfile.ZipFile(baixar("votacao_candidato_munzona/votacao_candidato_munzona_2024.zip"))
    m = {}; sit = {"PREFEITO": "p", "VICE-PREFEITO": "v", "VEREADOR": "ve"}
    for n in zc.namelist():
        if not n.startswith("consulta_cand_2024_") or n.endswith("BRASIL.csv") or not n.endswith(".csv"): continue
        uf = n[-6:-4]; el = {}
        for r in linhas(zc, n):
            if r["DS_ELEICAO"] != "Eleições Municipais 2024" or r["DS_CARGO"] not in sit or not r["DS_SIT_TOT_TURNO"].startswith("ELEITO"): continue
            el[(r["SQ_CANDIDATO"], r["NR_TURNO"])] = (r["SG_UE"], r["NM_UE"], sit[r["DS_CARGO"]], r["NM_URNA_CANDIDATO"].strip().title(), r["SG_PARTIDO"])
        votos = collections.Counter()
        nv = f"votacao_candidato_munzona_2024_{uf}.csv"
        for r in linhas(zv, nv):
            k = (r["SQ_CANDIDATO"], r["NR_TURNO"])
            if k in el: votos[k] += int(r["QT_VOTOS_NOMINAIS"] or 0)
        for k, (ue, nue, cg, nome, part) in el.items():
            e = m.setdefault(ue, {"n": nue.title(), "uf": uf, "p": None, "v": None, "ve": []}); v = votos.get(k)
            if cg == "p": e["p"] = [nome, part, v, int(k[1])]
            elif cg == "v": e["v"] = [nome, part, v]
            else: e["ve"].append([nome, part, v])
    for e in m.values(): e["ve"].sort(key=lambda x: (-(x[2] or 0), x[0]))
    OUT.write_bytes(gzip.compress(json.dumps({"gerado": time.strftime("%Y-%m-%d"), "m": m}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")))
    print(f"Prefeitos: {len(m)} municipios, {sum(1 for e in m.values() if e['p'])} prefeitos, {sum(len(e['ve']) for e in m.values())} vereadores")
if __name__ == "__main__": main()
