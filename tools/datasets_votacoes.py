"""Placar de votações nominais de plenário (Câmara e Senado) desde 2023, incremental com cache.

Rodado pela VPS no ciclo pesado diário (ops/ciclo.sh executa tools/datasets_*.py às PORTAL_DATASETS_HORA).
Fontes oficiais:
  Câmara: arquivos em lote da API Dados Abertos (votacoes, votacoesVotos, votacoesOrientacoes, votacoesProposicoes),
          https://dadosabertos.camara.leg.br/arquivos/<conjunto>/<formato>/<conjunto>-<ano>.<ext> (atualizados diariamente).
  Senado: https://legis.senado.leg.br/dadosabertos/votacao?dataInicio&dataFim (votos nominais) e
          /dadosabertos/plenario/votacao/orientacaoBancada/<AAAAMMDD> (orientações das lideranças).
Cache bruto em data/cache/votacoes (fora do git); saída compacta em data/votacoes/<casa>-<ano>.json.gz (no git).
Incremental: arquivos da Câmara só são baixados de novo se mudaram (If-Modified-Since); meses do Senado
anteriores ao mês passado ficam congelados no cache; orientações por data, uma única vez.
"""
import csv, datetime as dt, email.utils, gzip, io, json, os, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/cache/votacoes"; OUT = ROOT / "data/votacoes"
CACHE.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
INICIO = dt.date(2023, 2, 1)  # 57ª legislatura
HOJE = dt.date.today()
UA = {"User-Agent": "Estrato/1.0 (dados abertos; contato no site)", "Accept": "application/json"}
CAMARA = "https://dadosabertos.camara.leg.br/arquivos/{c}/{f}/{c}-{a}.{f}"
SENADO = "https://legis.senado.leg.br/dadosabertos"


def baixar(url, dest, sempre=True, tentativas=3):
    """Baixa url em dest. Se dest existe, usa If-Modified-Since (sempre=True) ou não baixa (sempre=False)."""
    if dest.exists() and not sempre: return False
    h = dict(UA)
    if dest.exists(): h["If-Modified-Since"] = email.utils.formatdate(dest.stat().st_mtime, usegmt=True)
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=300) as r:
                tmp = dest.with_suffix(dest.suffix + ".tmp"); tmp.write_bytes(r.read()); tmp.replace(dest); return True
        except urllib.error.HTTPError as e:
            if e.code == 304: return False
            if e.code == 404: return False
            err = e
        except Exception as e: err = e
        time.sleep(5 * (i + 1))
    print("falha", url, err, file=sys.stderr); return False


def camara(ano):
    ext = {"votacoes": "json", "votacoesOrientacoes": "json", "votacoesProposicoes": "json", "votacoesVotos": "csv"}
    novos = [baixar(CAMARA.format(c=c, f=f, a=ano), CACHE / f"{c}-{ano}.{f}", sempre=ano >= HOJE.year - 1) for c, f in ext.items()]
    saida = OUT / f"camara-{ano}.json.gz"
    if saida.exists() and not any(novos): return json.loads(gzip.decompress(saida.read_bytes()))
    vs = json.loads((CACHE / f"votacoes-{ano}.json").read_text(encoding="utf-8"))["dados"]
    votos = {}
    with open(CACHE / f"votacoesVotos-{ano}.csv", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            votos.setdefault(r["idVotacao"], []).append(r)
    ori = {}
    for o in json.loads((CACHE / f"votacoesOrientacoes-{ano}.json").read_text(encoding="utf-8"))["dados"]:
        if o.get("siglaOrgao") == "PLEN": ori.setdefault(o["idVotacao"], {})[o["siglaBancada"]] = o["orientacao"]
    props = {}
    for p in json.loads((CACHE / f"votacoesProposicoes-{ano}.json").read_text(encoding="utf-8"))["dados"]:
        props.setdefault(p["idVotacao"], []).append(p["proposicao_"])
    out = []
    for v in vs:
        if v.get("siglaOrgao") != "PLEN" or v["id"] not in votos or v["data"] < INICIO.isoformat(): continue
        pid = v["id"].split("-")[0]; ps = props.get(v["id"], [])
        p = next((x for x in ps if str(x.get("id")) == pid), ps[0] if ps else None)
        if not p and v.get("ultimaApresentacaoProposicao", {}).get("idProposicao"): p = None
        partidos = []; lin = []
        for r in votos[v["id"]]:
            sp = r["deputado_siglaPartido"] or "S.PART."
            if sp not in partidos: partidos.append(sp)
            lin.append([int(r["deputado_id"]), r["voto"], partidos.index(sp), r["deputado_siglaUf"], r["deputado_nome"]])
        out.append({"id": v["id"], "casa": "camara", "data": v["data"], "hora": (v.get("dataHoraRegistro") or "")[11:16],
                    "descricao": v.get("descricao") or "", "abertura": (v.get("ultimaAberturaVotacao") or {}).get("descricao") or "",
                    "aprovacao": v.get("aprovacao"), "prop": ({"id": p["id"], "titulo": p.get("titulo"), "ementa": p.get("ementa"), "sigla": p.get("siglaTipo"), "numero": p.get("numero"), "ano": p.get("ano")} if p else None),
                    "partidos": partidos, "votos": lin, "orient": ori.get(v["id"], {}),
                    "fonte": f"https://www.camara.leg.br/presenca-comissoes/votacao-portal?reuniao={v.get('idEvento')}&itemVotacao={v['id'].split('-')[1]}" if v.get("idEvento") else "",
                    "api": f"https://dadosabertos.camara.leg.br/api/v2/votacoes/{v['id']}"})
    anos = sorted({x["prop"]["ano"] for x in out if x["prop"] and x["prop"].get("ano")})
    temas = temas_camara(anos)
    for x in out:
        if x["prop"]: x["prop"]["temas"] = temas.get(str(x["prop"]["id"]), [])
    out.sort(key=lambda x: (x["data"], x["hora"], x["id"]))
    saida.write_bytes(gzip.compress(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode(), mtime=0))
    return out


_TEMAS = {}
def temas_camara(anos):
    """Temas oficiais das proposições (arquivo proposicoesTemas-<ano de apresentação>.csv)."""
    for a in anos:
        if a in _TEMAS: continue
        f = CACHE / f"proposicoesTemas-{a}.csv"
        baixar(CAMARA.format(c="proposicoesTemas", f="csv", a=a), f, sempre=a >= HOJE.year - 1)
        m = {}
        if f.exists():
            with open(f, encoding="utf-8-sig") as fh:
                for r in csv.DictReader(fh, delimiter=";"):
                    pid = r.get("uriProposicao", "").rsplit("/", 1)[-1]
                    if pid and r.get("tema"): m.setdefault(pid, []).append(r["tema"])
        _TEMAS[a] = m
    out = {}
    for a in anos: out.update(_TEMAS[a])
    return out


def temas_senado(id_processo):
    if not id_processo: return []
    f = CACHE / f"senproc-{id_processo}.json"
    baixar(f"{SENADO}/processo/{id_processo}", f, sempre=False)
    try: d = json.loads(f.read_text(encoding="utf-8"))
    except Exception: return []
    return list(dict.fromkeys((c.get("descricaoHierarquia") or c.get("descricao") or "").split("/")[0].strip() for c in d.get("classificacoes") or [] if c.get("descricao")))


def senado(ano):
    meses = []
    for m in range(1, 13):
        a = dt.date(ano, m, 1)
        if a > HOJE: break
        b = (dt.date(ano + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1))
        recente = (HOJE - b).days < 40
        f = CACHE / f"senado-{ano}-{m:02d}.json"
        baixar(f"{SENADO}/votacao?dataInicio={a}&dataFim={b}", f, sempre=recente)
        if f.exists():
            try: meses += json.loads(f.read_text(encoding="utf-8"))
            except Exception: print("senado json inválido", f, file=sys.stderr)
    out = []
    for v in meses:
        if v.get("votacaoSecreta") == "S" or not v.get("votos") or v["dataSessao"] < INICIO.isoformat(): continue
        d = v["dataSessao"]; fo = CACHE / f"senori-{d}.json"
        baixar(f"{SENADO}/plenario/votacao/orientacaoBancada/{d.replace('-', '')}", fo, sempre=(HOJE - dt.date.fromisoformat(d)).days < 3)
        ori, hora = {}, ""
        try:
            for x in json.loads(fo.read_text(encoding="utf-8")).get("votacoes", []):
                if x.get("sequencialVotacao") == v.get("sequencialVotacao"):
                    ori = {o["partido"]: o["voto"].capitalize().replace("Nao", "Não") for o in x.get("orientacoesLideranca") or []}
                    hora = (x.get("dataInicioVotacao") or "")[11:16]
        except Exception: pass
        partidos = []; lin = []
        for r in v["votos"]:
            sp = r.get("siglaPartidoParlamentar") or "S.PART."
            if sp not in partidos: partidos.append(sp)
            lin.append([int(r["codigoParlamentar"]), r.get("siglaVotoParlamentar") or "", partidos.index(sp), r.get("siglaUFParlamentar") or "", r.get("nomeParlamentar") or ""])
        res = v.get("resultadoVotacao")
        out.append({"id": f"{v['codigoSessaoVotacao']}", "casa": "senado", "data": d, "hora": hora, "descricao": v.get("descricaoVotacao") or "",
                    "abertura": "", "aprovacao": 1 if res == "A" else (0 if res == "R" else None),
                    "prop": {"id": v.get("codigoMateria"), "titulo": v.get("identificacao"), "ementa": v.get("ementa"), "sigla": v.get("sigla"), "numero": v.get("numero"), "ano": v.get("ano"), "temas": temas_senado(v.get("idProcesso"))},
                    "partidos": partidos, "votos": lin, "orient": ori,
                    "fonte": f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{v['codigoMateria']}" if v.get("codigoMateria") else "",
                    "api": f"{SENADO}/votacao?dataInicio={d}&dataFim={d}"})
    out.sort(key=lambda x: (x["data"], x["hora"], x["id"]))
    (OUT / f"senado-{ano}.json.gz").write_bytes(gzip.compress(json.dumps(out, ensure_ascii=False, separators=(",", ":")).encode(), mtime=0))
    return out


if __name__ == "__main__":
    tot = {"camara": 0, "senado": 0}
    for ano in range(INICIO.year, HOJE.year + 1):
        tot["camara"] += len(camara(ano)); tot["senado"] += len(senado(ano))
    (OUT / "meta.json").write_text(json.dumps({"coletado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **tot}, ensure_ascii=False), encoding="utf-8")
    print("votações nominais:", tot)
