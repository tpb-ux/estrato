"""Executivo federal desde 2023: viagens de ministros e da Vice-Presidência e cartão de pagamento (CPGF) por órgão. Incremental com cache.

Rodado pela VPS no ciclo pesado diário (ops/ciclo.sh executa tools/datasets_*.py às PORTAL_DATASETS_HORA).
Fontes oficiais, públicas e sem chave (downloads em lote do Portal da Transparência, CGU):
  viagens: https://portaldatransparencia.gov.br/download-de-dados/viagens/<ano>   (<ano>_Viagem.csv)
  CPGF:    https://portaldatransparencia.gov.br/download-de-dados/cpgf/<AAAAMM>   (<AAAAMM>_CPGF.csv)
A API do Portal (que exige chave) NÃO é usada. O e-Agendas exige token pessoal e também não é usado.
Viagens individuais: só autoridades com Função CNE-0001 (Cargo de Natureza Especial, nível de ministro de Estado) e o cargo
VICE-PRESIDENTE DA REPUBLICA. Demais servidores (inclusive DAS/CCE/FCE): só totais agregados por órgão. CPF (já mascarado na fonte) é descartado.
CPGF: só agregados por órgão superior; nomes de portadores NÃO são guardados; favorecidos só pessoa jurídica (CNPJ).
Saída: data/executivo/executivo.json.gz + meta.json (no git); bruto em data/cache/executivo (fora do git).
"""
import collections, csv, datetime as dt, email.utils, gzip, io, json, re, sys, time, urllib.request, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/cache/executivo"; OUT = ROOT / "data/executivo"
CACHE.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
HOJE = dt.date.today(); ANOS = list(range(2023, HOJE.year + 1))
UA = {"User-Agent": "Estrato/1.0 (dados abertos; contato no site)"}
BASE = "https://portaldatransparencia.gov.br/download-de-dados"


def baixar(url, dest, sempre=True):
    if dest.exists() and not sempre: return False
    h = dict(UA)
    if dest.exists(): h["If-Modified-Since"] = email.utils.formatdate(dest.stat().st_mtime, usegmt=True)
    err = None
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=900) as r:
                b = r.read()
                if not b.startswith(b"PK"): return False
                tmp = dest.with_suffix(".tmp"); tmp.write_bytes(b); tmp.replace(dest); return True
        except urllib.error.HTTPError as e:
            if e.code in (304, 403, 404): return False
            err = e
        except Exception as e: err = e
        time.sleep(15 * (i + 1))
    print("falha", url, err, file=sys.stderr); return False


def val(s):
    try: return float((s or "0").replace(".", "").replace(",", "."))
    except ValueError: return 0.0


def dbr(s):
    try: return dt.datetime.strptime(s, "%d/%m/%Y").date().isoformat()
    except ValueError: return ""


def linhas(z, sufixo):
    zf = zipfile.ZipFile(z); n = [x for x in zf.namelist() if x.endswith(sufixo)][0]
    return csv.DictReader(io.TextIOWrapper(zf.open(n), encoding="latin1"), delimiter=";")


def main():
    viag = []; org = {}; orgv = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0.0]))
    for ano in ANOS:
        z = CACHE / f"viagens-{ano}.zip"; baixar(f"{BASE}/viagens/{ano}", z, sempre=ano >= HOJE.year - 1)
        if not z.exists(): continue
        for r in linhas(z, "_Viagem.csv"):
            cs = r["Código do órgão superior"].strip(); org[cs] = r["Nome do órgão superior"].strip()
            v = val(r["Valor diárias"]) + val(r["Valor passagens"]) + val(r["Valor outros gastos"]) - val(r["Valor devolução"])
            a = orgv[cs][str(ano)]; a[0] += 1; a[1] += v
            cargo = r["Cargo"].strip().upper(); fun = r["Função"].strip()
            if fun != "CNE-0001" and cargo not in ("VICE-PRESIDENTE DA REPUBLICA", "PRESIDENTE DA REPUBLICA"): continue
            viag.append({"id": r["Identificador do processo de viagem"].strip(), "nome": r["Nome"].strip(), "cargo": cargo, "funcao": fun, "org": cs, "sol": r["Nome órgão solicitante"].strip(),
                         "ini": dbr(r["Período - Data de início"]), "fim": dbr(r["Período - Data de fim"]), "dest": r["Destinos"].strip(), "motivo": re.sub(r"\s+", " ", r["Motivo"]).strip()[:400],
                         "sit": r["Situação"].strip(), "urg": r["Viagem Urgente"].strip(), "diarias": round(val(r["Valor diárias"]), 2), "passagens": round(val(r["Valor passagens"]), 2),
                         "outros": round(val(r["Valor outros gastos"]), 2), "devol": round(val(r["Valor devolução"]), 2)})
        print("viagens", ano, len(viag))
    cp = {}; meses = []
    for ano in ANOS:
        for m in range(1, 13):
            if dt.date(ano, m, 1) > HOJE: break
            am = f"{ano}{m:02d}"; z = CACHE / f"cpgf-{am}.zip"
            recente = (HOJE.year * 12 + HOJE.month) - (ano * 12 + m) <= 3
            baixar(f"{BASE}/cpgf/{am}", z, sempre=recente)
            if not z.exists(): continue
            meses.append(am)
            for r in linhas(z, "_CPGF.csv"):
                cs = r["CÓDIGO ÓRGÃO SUPERIOR"].strip(); v = val(r["VALOR TRANSAÇÃO"]); t = r["TRANSAÇÃO"].strip(); a = r["ANO EXTRATO"].strip() or str(ano)
                o = cp.setdefault(cs, {"nome": r["NOME ÓRGÃO SUPERIOR"].strip(), "anos": {}, "tipo": collections.Counter(), "fav": collections.Counter(), "fav_n": {}, "sig": collections.Counter(), "ug": collections.Counter()})
                y = o["anos"].setdefault(a, [0, 0.0]); y[0] += 1; y[1] += v; o["tipo"][t] += v; o["ug"][r["NOME UNIDADE GESTORA"].strip()] += v
                if "sigilo" in t.lower(): o["sig"][a] += v
                d = re.sub(r"\D", "", r["CNPJ OU CPF FAVORECIDO"])
                if len(d) == 14: o["fav"][d] += v; o["fav_n"][d] = r["NOME FAVORECIDO"].strip()
    r2 = lambda c: {k: round(v, 2) for k, v in c.items()}
    for o in cp.values():
        o["anos"] = {k: [n, round(v, 2)] for k, (n, v) in o["anos"].items()}; o["tipo"] = r2(o["tipo"]); o["sig"] = r2(o["sig"]); o["ug"] = r2(dict(o["ug"].most_common(15)))
        top = dict(o["fav"].most_common(25)); o["fav"] = r2(top); o["fav_n"] = {k: o["fav_n"][k] for k in top}
    out = {"viagens": viag, "orgaos": org, "viag_org": {k: {a: [n, round(v, 2)] for a, (n, v) in d.items()} for k, d in orgv.items()}, "cpgf": cp}
    (OUT / "executivo.json.gz").write_bytes(gzip.compress(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode(), 9, mtime=0))
    meta = {"coletado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "anos": ANOS, "cpgf_meses": [meses[0], meses[-1]] if meses else [],
            "viagens_autoridades": len(viag), "orgaos": len(org), "fontes": [f"{BASE}/viagens/<ano>", f"{BASE}/cpgf/<AAAAMM>"]}
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8"); print(meta)
if __name__ == "__main__": main()
