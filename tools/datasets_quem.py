"""Quem é quem: composição do STF (cms.stf.jus.br, página oficial "Composição atual") e ministros de Estado (gov.br/planalto,
"Ministros e Ministras"). Fontes públicas sem chave. Saída: data/quem_e_quem.json. Se uma fonte falhar, mantém a versão anterior."""
import datetime as dt, html, json, pathlib, re, sys, urllib.request
R = pathlib.Path(__file__).resolve().parents[1]; OUT = R / "data/quem_e_quem.json"
UA = {"User-Agent": "Mozilla/5.0 (compatible; Estrato/1.0; +https://estrato.com.br)"}
F_STF = "https://cms.stf.jus.br/post-sobreostf/composicao-atual/"
F_MIN = "https://www.gov.br/planalto/pt-br/conheca-a-presidencia/ministros-e-ministras"
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r: return r.read().decode("utf-8", "replace")
def txt(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

def stf():
    t = get(F_STF); out = []
    for m in re.finditer(r"Ministr([oa]) ([^<]{3,80}?)</", t):
        nome, _, fun = txt(m.group(2)).partition(" – ")
        if nome and nome not in [x["nome"] for x in out]: out.append({"nome": nome, "funcao": fun or "", "tratamento": "Ministra" if m.group(1) == "a" else "Ministro"})
    at = re.search(r"Última atualização:\s*(?:</span>)?\s*([0-9/]{10})", t)
    if not 8 <= len(out) <= 11: raise ValueError(f"STF: {len(out)} nomes lidos")
    return out, at.group(1) if at else ""

def ministros():
    t = get(F_MIN); c = t.split('id="content-core"', 1)[-1].split("Compartilhe:", 1)[0]
    partes = [txt(x) for x in re.split(r"</(?:p|h\d|strong|div|span|a)>", c)]; partes = [p for p in partes if p]
    partes = [p.lstrip("> ").strip() for p in partes]
    out = []; i = 0
    while i + 1 < len(partes):
        a, b = partes[i], partes[i + 1]
        if re.match(r"^(Ministr[oa] de Estado|Advocacia-Geral|Controladoria-Geral)", a) and not re.match(r"^(Ministr[oa] de Estado|Advocacia|Controladoria)", b): out.append({"cargo": a, "nome": b}); i += 2
        else: i += 1
    at = re.search(r"Atualizado em(?:\s|<[^>]+>)*([0-9/]{10})", t)
    if len(out) < 30: raise ValueError(f"ministros: {len(out)} lidos")
    return out, at.group(1) if at else ""

def main():
    D = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    for k, f, u in (("stf", stf, F_STF), ("ministros", ministros, F_MIN)):
        try: it, at = f(); D[k] = {"itens": it, "atualizado_fonte": at, "fonte": u, "coletado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}; print(k, len(it), at)
        except Exception as ex: print(k, "falhou:", ex, file=sys.stderr)
    OUT.write_text(json.dumps(D, ensure_ascii=False, indent=1), encoding="utf-8")
if __name__ == "__main__": main()
