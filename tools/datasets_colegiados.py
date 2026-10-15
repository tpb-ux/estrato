"""Frentes parlamentares (57a legislatura), comissoes/CPIs da Camara e colegiados do Senado e do Congresso, a partir de dados abertos oficiais (sem chave).
Rodado pela VPS no ciclo pesado diario. Cache em data/cache/colegiados (fora do git); saida data/colegiados/colegiados.json.gz.
Camara: arquivos em lote orgaos, orgaosDeputados-L57, frentes e frentesDeputados (dadosabertos.camara.leg.br/arquivos).
Senado: /dadosabertos/comissao/lista/colegiados (em atividade) e /dadosabertos/comissao/<codigo> (cargos e membros)."""
import csv, datetime as dt, email.utils, gzip, json, sys, time, urllib.request
from pathlib import Path
csv.field_size_limit(10**9)
ROOT = Path(__file__).resolve().parents[1]; CACHE = ROOT / "data/cache/colegiados"; OUT = ROOT / "data/colegiados"
CACHE.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Estrato/1.0 (dados abertos; contato no site)", "Accept": "application/json"}
CD = "https://dadosabertos.camara.leg.br/arquivos/{c}/csv/{n}.csv"; SF = "https://legis.senado.leg.br/dadosabertos"
LEG = "57"


def baixar(url, dest, dias=1):
    if dest.exists() and time.time() - dest.stat().st_mtime < dias * 86400: return
    h = dict(UA)
    if dest.exists(): h["If-Modified-Since"] = email.utils.formatdate(dest.stat().st_mtime, usegmt=True)
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=300) as r:
                tmp = dest.with_suffix(".tmp"); tmp.write_bytes(r.read()); tmp.replace(dest); return
        except urllib.error.HTTPError as e:
            if e.code == 304: dest.touch(); return
        except Exception: pass
        time.sleep(5 * (i + 1))
    print("falha", url, file=sys.stderr)


def lerr(f):
    with open(f, encoding="utf-8-sig", newline="") as fh: yield from csv.DictReader(fh, delimiter=";")


def sf(path, dest, dias=1):
    if dest.exists() and time.time() - dest.stat().st_mtime < dias * 86400: return json.loads(dest.read_text(encoding="utf-8"))
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(SF + path, headers=UA), timeout=60) as r: d = json.loads(r.read().decode("utf-8")); dest.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8"); return d
        except Exception: time.sleep(3 * (i + 1))
    return json.loads(dest.read_text(encoding="utf-8")) if dest.exists() else None


def lista(x): return x if isinstance(x, list) else [x] if x else []
def idu(u): return u.rstrip("/").rsplit("/", 1)[-1]


def camara():
    for c, n in (("orgaos", "orgaos"), ("orgaosDeputados", "orgaosDeputados-L57"), ("frentes", "frentes"), ("frentesDeputados", "frentesDeputados")): baixar(CD.format(c=c, n=n), CACHE / f"{n}.csv")
    mem = {}
    for r in lerr(CACHE / "orgaosDeputados-L57.csv"):
        if r["dataFim"]: continue
        mem.setdefault(idu(r["uriOrgao"]), []).append([int(idu(r["uriDeputado"])), r["nomeDeputado"], r["siglaPartido"], r["siglaUF"], r["cargo"]])
    org = []
    for r in lerr(CACHE / "orgaos.csv"):
        i = idu(r["uri"])
        if i not in mem or r["descricaoSituacao"] in ("Extinta", "Desconstituida"): continue
        org.append({"id": int(i), "sigla": r["sigla"], "nome": r["nome"], "apelido": r["apelido"], "tipo": r["tipoOrgao"], "sit": r["descricaoSituacao"], "ini": r["dataInicio"][:10], "inst": r["dataInstalacao"][:10], "fim": r["dataFim"][:10],
                    "casa": r["casa"], "sala": r["sala"], "site": r["urlWebsite"], "m": mem[i]})
    fr = {}
    for r in lerr(CACHE / "frentes.csv"):
        if r["idLegislatura"] != LEG: continue
        fr[r["id"]] = {"id": int(r["id"]), "t": r["titulo"].strip(), "cri": r["dataCriacao"][:10], "tel": r["telefone"], "email": r["email"], "site": r["urlWebsite"], "kw": r["keywords"], "log": r["situacao"].strip()[:1500],
                       "co": [int(r["coordenador_id"]), r["coordenador_nome"], r["coordenador_siglaPartido"], r["coordenador_siglaUf"]] if r["coordenador_id"] else None, "m": []}
    for r in lerr(CACHE / "frentesDeputados.csv"):
        if r["id"] in fr and r["deputado_.idLegislatura"] == LEG and r["deputado_.id"] and not r["dataFim"]: fr[r["id"]]["m"].append([int(r["deputado_.id"]), r["deputado_.nome"], r["deputado_.siglaUf"], r["deputado_.titulo"]])
    return org, list(fr.values())


def senado():
    L = sf("/comissao/lista/colegiados", CACHE / "sf-colegiados.json")
    out = []
    for c in lista(L["ListaColegiados"]["Colegiados"]["Colegiado"]):
        d = sf(f"/comissao/{c['Codigo']}", CACHE / f"sf-{c['Codigo']}.json")
        try: x = lista(d["ComissoesCongressoNacional"]["Colegiados"]["Colegiado"])[0]
        except Exception: x = {}
        membros, cargos = [], []
        for pb in lista((x.get("MembrosBlocoSF") or {}).get("PartidoBloco")):
            for m in lista((pb.get("MembrosSF") or {}).get("Membro")):
                if m.get("CodigoParlamentar"): membros.append([int(m["CodigoParlamentar"]), m["NomeParlamentar"].replace("Senador ", "").replace("Senadora ", ""), m.get("Partido", ""), m.get("SiglaUf", ""), m.get("TipoVaga", "")])
        for k in lista((x.get("Cargos") or {}).get("Cargo")):
            cargos.append([k.get("TipoCargo", ""), k.get("NomeParlamentar", "").replace("Senador ", "").replace("Senadora ", ""), int(k["CodigoParlamentar"]) if k.get("CodigoParlamentar") else 0, k.get("Bancada", "")])
        qm = ((x.get("QuantidadesMembros") or {}).get("Distribuicao") or {})
        out.append({"cod": int(c["Codigo"]), "sigla": c["Sigla"], "nome": c["Nome"], "fin": (c.get("Finalidade") or "").strip(), "ini": c.get("DataInicio", ""), "tipo": c.get("DescricaoTipoColegiado", ""), "casa": c.get("SiglaCasa", ""),
                    "pub": c.get("Publica", ""), "nm": int(qm.get("Senadores") or 0), "m": membros, "cargos": cargos})
    return out


def main():
    org, fr = camara(); sen = senado()
    d = {"coletado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "camara": org, "senado": sen, "frentes": fr}
    (OUT / "colegiados.json.gz").write_bytes(gzip.compress(json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9))
    print(f"{len(org)} orgaos da Camara, {len(sen)} colegiados do Senado/CN, {len(fr)} frentes ({sum(1 for f in fr if f['m'])} com membros)")


if __name__ == "__main__": main()
