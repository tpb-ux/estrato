"""Cota parlamentar (CEAP da Câmara e CEAPS do Senado) desde 2023, incremental com cache.

Rodado pela VPS no ciclo pesado diário (ops/ciclo.sh executa tools/datasets_*.py às PORTAL_DATASETS_HORA).
Fontes oficiais, públicas e sem chave:
  Câmara: https://www.camara.leg.br/cotas/Ano-<ano>.csv.zip (arquivo anual, atualizado diariamente)
  Senado: https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/<ano>
Privacidade: fornecedores pessoa física (CPF) NÃO são publicados nem guardados; entram só no total agregado
"pessoa física". Nome de passageiro, trecho e número de documento são descartados.
Saída: data/cotas/<casa>.json.gz e data/cotas/meta.json (no git); bruto em data/cache/cotas (fora do git).
"""
import csv, datetime as dt, email.utils, gzip, io, json, re, sys, time, urllib.request, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/cache/cotas"; OUT = ROOT / "data/cotas"
CACHE.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
HOJE = dt.date.today(); ANOS = list(range(2023, HOJE.year + 1))
UA = {"User-Agent": "Estrato/1.0 (dados abertos; contato no site)"}


def baixar(url, dest, sempre=True):
    if dest.exists() and not sempre: return False
    h = dict(UA)
    if dest.exists(): h["If-Modified-Since"] = email.utils.formatdate(dest.stat().st_mtime, usegmt=True)
    err = None
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=300) as r:
                tmp = dest.with_suffix(dest.suffix + ".tmp"); tmp.write_bytes(r.read()); tmp.replace(dest); return True
        except urllib.error.HTTPError as e:
            if e.code in (304, 404): return False
            err = e
        except Exception as e: err = e
        time.sleep(10 * (i + 1))
    print("falha", url, err, file=sys.stderr); return False


def cat_nome(s):
    s = re.sub(r"\s+", " ", (s or "").strip()); s = s[:1].upper() + s[1:].lower() if s.isupper() else s
    s = re.sub(r"\s+,", ",", s).replace(",", ", ").replace(",  ", ", ").rstrip(" .")
    return s or "Não informada"


class Agg:
    def __init__(s): s.parl = {}; s.forn = {}; s.pf = {}
    def add(s, pid, nome, uf, partido, ano, mes, cat, doc, fnome, v):
        p = s.parl.setdefault(pid, {"nome": nome, "uf": uf, "partido": partido, "anos": {}, "forn": {}})
        if partido: p["partido"] = partido
        a = p["anos"].setdefault(str(ano), {"tot": 0.0, "n": 0, "cat": {}, "mes": {}})
        a["tot"] += v; a["n"] += 1; a["cat"][cat] = a["cat"].get(cat, 0) + v; a["mes"][str(mes)] = a["mes"].get(str(mes), 0) + v
        d = re.sub(r"\D", "", doc or "")
        if len(d) == 14:
            p["forn"][d] = p["forn"].get(d, 0) + v
            f = s.forn.setdefault(d, {"nome": fnome.strip(), "tot": 0.0, "n": 0, "cat": {}, "parl": {}, "anos": {}})
            f["tot"] += v; f["n"] += 1; f["cat"][cat] = f["cat"].get(cat, 0) + v
            f["parl"][pid] = f["parl"].get(pid, 0) + v; f["anos"][str(ano)] = f["anos"].get(str(ano), 0) + v
        elif len(d) == 11:  # pessoa física: só soma agregada, sem identificação
            k = f"{ano}|{cat}"; s.pf[k] = s.pf.get(k, 0) + v
    def dump(s):
        r2 = lambda d: {k: round(v, 2) for k, v in d.items()}
        for p in s.parl.values():
            for a in p["anos"].values(): a["tot"] = round(a["tot"], 2); a["cat"] = r2(a["cat"]); a["mes"] = r2(a["mes"])
            p["forn"] = r2(p["forn"])
        for f in s.forn.values(): f["tot"] = round(f["tot"], 2); f["cat"] = r2(f["cat"]); f["parl"] = r2(f["parl"]); f["anos"] = r2(f["anos"])
        return {"parl": s.parl, "forn": s.forn, "pf": r2(s.pf)}


def camara():
    A = Agg()
    for ano in ANOS:
        z = CACHE / f"camara-{ano}.zip"; baixar(f"https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip", z, sempre=ano >= HOJE.year - 1)
        if not z.exists(): continue
        zf = zipfile.ZipFile(z); nm = [n for n in zf.namelist() if n.endswith(".csv")][0]
        for r in csv.DictReader(io.TextIOWrapper(zf.open(nm), encoding="utf-8-sig"), delimiter=";"):
            i = (r.get("ideCadastro") or "").strip()
            if not i.isdigit(): continue  # lideranças e órgãos ficam de fora
            try: v = float((r["vlrLiquido"] or "0").replace(",", "."))
            except ValueError: continue
            A.add(i, r["txNomeParlamentar"].strip(), r["sgUF"], r["sgPartido"], int(r["numAno"] or ano), int(r["numMes"] or 0), cat_nome(r["txtDescricao"]), r["txtCNPJCPF"], r["txtFornecedor"], v)
    return A.dump()


def senado():
    A = Agg()
    for ano in ANOS:
        f = CACHE / f"senado-{ano}.json"; baixar(f"https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/{ano}", f, sempre=ano >= HOJE.year - 1)
        if not f.exists(): continue
        for r in json.loads(f.read_text(encoding="utf-8")):
            A.add(str(r["codSenador"]), r["nomeSenador"].strip().title(), "", "", int(r["ano"]), int(r["mes"]), cat_nome(r["tipoDespesa"]), r.get("cpfCnpj"), r.get("fornecedor") or "", float(r.get("valorReembolsado") or 0))
    return A.dump()


def main():
    meta = {"coletado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "anos": ANOS,
            "fontes": {"camara": "https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip", "senado": "https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/{ano}"}}
    for casa, fn in (("camara", camara), ("senado", senado)):
        d = fn(); (OUT / f"{casa}.json.gz").write_bytes(gzip.compress(json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode(), 9, mtime=0))
        meta[casa] = {"parlamentares": len(d["parl"]), "fornecedores_pj": len(d["forn"])}; print(casa, meta[casa])
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
if __name__ == "__main__": main()
