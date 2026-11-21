"""Coleta dados oficiais da Câmara (API v2) e do Senado (dadosabertos) -> data/*.json.
Idempotente, com cache em data/cache (gitignored). Uso: python tools/camara_senado.py [--ano 2026]"""
import json, sys, time, urllib.request, concurrent.futures as cf, datetime as dt, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; C = ROOT / "data/cache"; C.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (compatible; EstratoBot/1.0; +https://estrato.com.br)"
CAM = "https://dadosabertos.camara.leg.br/api/v2"; SEN = "https://legis.senado.leg.br/dadosabertos"

def get(url, ttl_h=20):
    f = C / (hashlib.md5(url.encode()).hexdigest() + ".json")
    if f.exists() and time.time() - f.stat().st_mtime < ttl_h * 3600: return json.loads(f.read_text())
    for i in range(4):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"}), timeout=40)
            d = json.loads(r.read()); f.write_text(json.dumps(d)); return d
        except Exception as e:
            if i == 3: print("ERRO", url, e); return None
            time.sleep(2 + 3 * i)

def paged(url):
    out, p = [], 1
    while True:
        d = get(f"{url}{'&' if '?' in url else '?'}itens=100&pagina={p}")
        if not d or not d.get("dados"): break
        out += d["dados"]
        if not any(l.get("rel") == "next" for l in d.get("links", [])): break
        p += 1
    return out

def deputado(d, ano):
    det = (get(f"{CAM}/deputados/{d['id']}") or {}).get("dados", {})
    us = det.get("ultimoStatus", {})
    desp = paged(f"{CAM}/deputados/{d['id']}/despesas?ano={ano}&ordem=ASC&ordenarPor=mes")
    cat, mes = {}, {}
    for x in desp:
        v = float(x.get("valorLiquido") or 0); cat[x["tipoDespesa"]] = cat.get(x["tipoDespesa"], 0) + v; mes[x["mes"]] = mes.get(x["mes"], 0) + v
    org = [o for o in paged(f"{CAM}/deputados/{d['id']}/orgaos") if not o.get("dataFim")]
    return {"id": d["id"], "nome": d["nome"], "partido": d["siglaPartido"], "uf": d["siglaUf"], "foto": d["urlFoto"], "email": d.get("email") or us.get("email"),
            "nome_civil": det.get("nomeCivil"), "sexo": det.get("sexo"), "nascimento": det.get("dataNascimento"), "municipio_nascimento": det.get("municipioNascimento"),
            "uf_nascimento": det.get("ufNascimento"), "escolaridade": det.get("escolaridade"), "situacao": us.get("situacao"), "condicao": us.get("condicaoEleitoral"),
            "gabinete": {k: (us.get("gabinete") or {}).get(k) for k in ("predio", "sala", "andar", "telefone")},
            "ceap": {"ano": ano, "total": round(sum(cat.values()), 2), "lancamentos": len(desp), "por_categoria": {k: round(v, 2) for k, v in sorted(cat.items(), key=lambda x: -x[1])}, "por_mes": {str(k): round(v, 2) for k, v in sorted(mes.items())}},
            "orgaos": [{"sigla": o.get("siglaOrgao"), "nome": o.get("nomeOrgao"), "cargo": o.get("titulo")} for o in org][:30]}

def main():
    ano = int(sys.argv[sys.argv.index("--ano") + 1]) if "--ano" in sys.argv else dt.date.today().year
    ref = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    lst = paged(f"{CAM}/deputados?ordem=ASC&ordenarPor=nome")
    print("deputados", len(lst))
    with cf.ThreadPoolExecutor(4) as ex: deps = list(ex.map(lambda d: deputado(d, ano), lst))
    (ROOT / "data/deputados.json").write_text(json.dumps({"fonte": "Câmara dos Deputados, API Dados Abertos v2", "url": CAM, "coletado_em": ref, "ano_ceap": ano, "deputados": deps}, ensure_ascii=False, indent=0))
    sl = get(f"{SEN}/senador/lista/atual.json")["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"]
    sens = []
    def sen(p):
        i = p["IdentificacaoParlamentar"]; cod = i["CodigoParlamentar"]
        det = ((get(f"{SEN}/senador/{cod}.json") or {}).get("DetalheParlamentar", {}).get("Parlamentar", {}))
        db = det.get("DadosBasicosParlamentar", {})
        com = ((get(f"{SEN}/senador/{cod}/comissoes.json") or {}).get("MembroComissaoParlamentar", {}).get("Parlamentar", {}).get("MembroComissoes", {}).get("Comissao", []))
        com = [c for c in (com if isinstance(com, list) else [com]) if not c.get("DataFim")]
        m = p.get("Mandato", {})
        return {"id": cod, "nome": i["NomeParlamentar"], "nome_civil": i.get("NomeCompletoParlamentar"), "sexo": i.get("SexoParlamentar"), "partido": i.get("SiglaPartidoParlamentar"),
                "uf": i.get("UfParlamentar"), "foto": i.get("UrlFotoParlamentar"), "pagina": i.get("UrlPaginaParlamentar"), "email": i.get("EmailParlamentar"),
                "nascimento": db.get("DataNascimento"), "naturalidade": db.get("Naturalidade"), "uf_naturalidade": db.get("UfNaturalidade"),
                "participacao": m.get("DescricaoParticipacao"), "legislaturas": [m.get("PrimeiraLegislaturaDoMandato", {}).get("NumeroLegislatura"), m.get("SegundaLegislaturaDoMandato", {}).get("NumeroLegislatura")],
                "mandato_inicio": m.get("PrimeiraLegislaturaDoMandato", {}).get("DataInicio"), "mandato_fim": m.get("SegundaLegislaturaDoMandato", {}).get("DataFim"),
                "comissoes": [{"sigla": c.get("IdentificacaoComissao", {}).get("SiglaComissao"), "nome": c.get("IdentificacaoComissao", {}).get("NomeComissao"), "cargo": c.get("DescricaoParticipacao")} for c in com][:30]}
    with cf.ThreadPoolExecutor(4) as ex: sens = list(ex.map(sen, sl))
    (ROOT / "data/senadores.json").write_text(json.dumps({"fonte": "Senado Federal, Dados Abertos", "url": SEN, "coletado_em": ref, "senadores": sens}, ensure_ascii=False, indent=0))
    ps = paged(f"{CAM}/partidos?ordem=ASC&ordenarPor=sigla")
    parts = []
    for p in ps:
        det = (get(f"{CAM}/partidos/{p['id']}") or {}).get("dados", {}); st = det.get("status", {})
        parts.append({"id": p["id"], "sigla": p["sigla"], "nome": p["nome"], "numero": det.get("numeroEleitoral"), "logo": det.get("urlLogo"), "site": det.get("urlWebSite"),
                      "situacao": st.get("situacao"), "lider": (st.get("lider") or {}).get("nome"), "lider_uf": (st.get("lider") or {}).get("uf"), "membros_camara_api": st.get("totalMembros")})
    (ROOT / "data/partidos.json").write_text(json.dumps({"fonte": "Câmara dos Deputados, API Dados Abertos v2 (/partidos)", "coletado_em": ref, "partidos": parts}, ensure_ascii=False, indent=0))
    print("ok", len(deps), len(sens), len(parts))
if __name__ == "__main__": main()
