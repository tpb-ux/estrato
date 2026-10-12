"""CEAP (cota parlamentar) da Câmara a partir do arquivo oficial anual: camara.leg.br/cotas/Ano-<ano>.csv.zip -> data/ceap.json
Agrega por deputado (ideCadastro), categoria (txtDescricao) e mês, usando vlrLiquido. Não publica fornecedores nem CPF/CNPJ."""
import csv, datetime as dt, io, json, sys, urllib.request, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
def main():
    ano = int(sys.argv[sys.argv.index("--ano") + 1]) if "--ano" in sys.argv else dt.date.today().year
    url = f"https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip"
    if "--zip" in sys.argv: raw = Path(sys.argv[sys.argv.index("--zip") + 1]).read_bytes()
    else:
        import time
        for i in range(5):
            try: raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; EstratoBot/1.0)"}), timeout=180).read(); break
            except Exception as e:
                if i == 4: raise
                print("retry", e); time.sleep(30 * (i + 1))
    z = zipfile.ZipFile(io.BytesIO(raw)); name = [n for n in z.namelist() if n.endswith(".csv")][0]
    rd = csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig"), delimiter=";")
    dep, ult = {}, 0
    for r in rd:
        i = r.get("ideCadastro") or r.get("nuDeputadoId")
        if not i or not i.strip().isdigit(): continue
        try: v = float(r["vlrLiquido"].replace(",", "."))
        except Exception: continue
        m = int(r["numMes"] or 0); ult = max(ult, m)
        d = dep.setdefault(i.strip(), {"total": 0.0, "lancamentos": 0, "por_categoria": {}, "por_mes": {}})
        d["total"] += v; d["lancamentos"] += 1
        c = r["txtDescricao"].strip().capitalize(); d["por_categoria"][c] = d["por_categoria"].get(c, 0) + v
        d["por_mes"][str(m)] = d["por_mes"].get(str(m), 0) + v
    for d in dep.values():
        d["total"] = round(d["total"], 2); d["por_categoria"] = {k: round(v, 2) for k, v in sorted(d["por_categoria"].items(), key=lambda x: -x[1])}
        d["por_mes"] = {k: round(v, 2) for k, v in sorted(d["por_mes"].items(), key=lambda x: int(x[0]))}
    out = {"fonte": "Câmara dos Deputados, Cota para o Exercício da Atividade Parlamentar (arquivo anual)", "url": url, "ano": ano, "ultimo_mes": ult,
           "coletado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "deputados": dep}
    (ROOT / "data/ceap.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8"); print("ceap", ano, len(dep), "deputados, último mês", ult)
if __name__ == "__main__": main()
