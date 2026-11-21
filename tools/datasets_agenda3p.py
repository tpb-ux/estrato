"""Agenda dos Três Poderes: Câmara (API v2 /eventos), Senado (plenário e reuniões de comissões, Dados Abertos) e STF (pauta, se acessível).
Fontes públicas sem chave. Saída: data/agenda/tres_poderes.json (mescla por id; guarda ~120 dias). Uso: python tools/datasets_agenda3p.py [--dias-antes 7 --dias-depois 21]"""
import argparse, datetime as dt, json, pathlib, sys, urllib.request
R = pathlib.Path(__file__).resolve().parents[1]; OUT = R / "data/agenda/tres_poderes.json"
UA = {"Accept": "application/json", "User-Agent": "Estrato/1.0 (+https://estrato.com.br)"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r: return json.loads(r.read().decode("utf-8"))
def lista(x): return x if isinstance(x, list) else [x] if x else []

def camara(a, b):
    out, u = [], f"https://dadosabertos.camara.leg.br/api/v2/eventos?dataInicio={a}&dataFim={b}&itens=100&ordem=ASC&ordenarPor=dataHoraInicio"
    while u:
        j = get(u)
        for e in j["dados"]:
            org = e.get("orgaos") or [{}]
            out.append({"id": f"cd-{e['id']}", "poder": "Legislativo", "casa": "Câmara", "data": e["dataHoraInicio"][:10], "hora": e["dataHoraInicio"][11:16], "tipo": e.get("descricaoTipo") or "",
                        "orgao": org[0].get("sigla") or "", "orgao_nome": org[0].get("nome") or "", "titulo": (e.get("descricao") or "").strip()[:300], "situacao": e.get("situacao") or "",
                        "local": (e.get("localCamara") or {}).get("nome") or e.get("localExterno") or "", "url": f"https://www.camara.leg.br/evento-legislativo/{e['id']}"})
        u = next((l["href"] for l in j.get("links", []) if l["rel"] == "next"), None)
    return out

def senado(a, b):
    out = []; d0 = dt.date.fromisoformat(a[:8] + "01"); meses = []
    while d0.isoformat() <= b: meses.append(d0.isoformat()[:7]); d0 = (d0 + dt.timedelta(days=32)).replace(day=1)
    for m in meses:
        j = get(f"https://legis.senado.leg.br/dadosabertos/plenario/agenda/mes/{m.replace('-', '')}01")
        for s in lista(((j.get("AgendaPlenario") or {}).get("Sessoes") or {}).get("Sessao")):
            if not a <= s["Data"] <= b: continue
            out.append({"id": f"sf-{s['CodigoSessao']}", "poder": "Legislativo", "casa": "Senado" if s.get("Casa") == "SF" else "Congresso", "data": s["Data"], "hora": s.get("Hora") or "",
                        "tipo": (s.get("TipoSessao") or "").strip().capitalize(), "orgao": "Plenário", "orgao_nome": s.get("LocalSessao") or "", "titulo": ((s.get("Evento") or {}).get("DescricaoTipoEvento") or s.get("TipoSessao") or "").strip(),
                        "situacao": s.get("SituacaoSessao") or "", "local": s.get("LocalSessao") or "", "url": "https://www25.senado.leg.br/web/atividade/sessao-plenaria"})
    j = get(f"https://legis.senado.leg.br/dadosabertos/agendareuniao/{a.replace('-', '')}/{b.replace('-', '')}")
    for r in lista((((j.get("AgendaReuniao") or {}).get("reunioes")) or {}).get("reuniao")):
        c = r.get("colegiadoCriador") or {}; pt = lista((r.get("partes") or {}))
        out.append({"id": f"sfr-{r['codigo']}", "poder": "Legislativo", "casa": "Senado" if c.get("siglaCasa") == "SF" else "Congresso", "data": r["dataInicio"][:10], "hora": r["dataInicio"][11:16], "tipo": "Reunião de comissão",
                    "orgao": c.get("sigla") or "", "orgao_nome": c.get("nome") or "", "titulo": (r.get("titulo") or "") + (f" — {pt[0].get('nome')}" if pt and pt[0].get("nome") else ""),
                    "situacao": r.get("situacao") or "", "local": r.get("local") or "", "url": f"https://legis.senado.leg.br/comissoes/reuniao?reuniao={r['codigo']}"})
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dias-antes", type=int, default=7); ap.add_argument("--dias-depois", type=int, default=21); x = ap.parse_args()
    h = dt.date.today(); a, b = (h - dt.timedelta(days=x.dias_antes)).isoformat(), (h + dt.timedelta(days=x.dias_depois)).isoformat()
    D = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"itens": {}, "fontes": {}}
    st = {}
    for nome, f in (("camara", camara), ("senado", senado)):
        try:
            it = f(a, b); st[nome] = len(it)
            for e in it: D["itens"][e["id"]] = e
        except Exception as ex: st[nome] = f"erro: {ex}"; print(nome, "falhou:", ex, file=sys.stderr)
    try: urllib.request.urlopen(urllib.request.Request("https://portal.stf.jus.br/pauta/", headers=UA), timeout=30); st["stf"] = "acessível (parser pendente)"
    except Exception as ex: st["stf"] = f"inacessível: {ex}"
    corte = (h - dt.timedelta(days=120)).isoformat(); D["itens"] = {k: v for k, v in D["itens"].items() if v["data"] >= corte}
    D["fontes"] = {"camara": "https://dadosabertos.camara.leg.br/api/v2/eventos", "senado_plenario": "https://legis.senado.leg.br/dadosabertos/plenario/agenda/mes/<AAAAMMDD>",
                   "senado_comissoes": "https://legis.senado.leg.br/dadosabertos/agendareuniao/<ini>/<fim>", "planalto": "data/agenda/presidente.json.gz e vice.json.gz", "stf": "https://portal.stf.jus.br/pauta/"}
    D["coletado_em"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"); D["status"] = st; D["janela"] = [a, b]
    OUT.write_text(json.dumps(D, ensure_ascii=False, indent=0), encoding="utf-8"); print(st, len(D["itens"]))
if __name__ == "__main__": main()
