"""Placar de votações nominais de plenário (Câmara e Senado, 57ª legislatura, desde 2023).

Dados: data/votacoes/<casa>-<ano>.json.gz, gerados por tools/datasets_votacoes.py a partir das APIs oficiais.
Páginas: /votacoes/ (hub com filtros), /votacoes/<casa>/<ano>/ (listas anuais), /votacoes/<casa>/<slug>/ (uma por votação),
/votacoes/metodologia/ e CSVs em /dados/. resumo(S) alimenta o bloco "Como votou" das páginas de deputados e senadores.
Período eleitoral: só dados factuais; nenhuma lista ordena parlamentares por alinhamento ou presença.
"""
import collections, csv, gzip, json, re
from core.site import E, slugify
from .dados import UF, data_br, num, pct

CASA = {"camara": ("Câmara", "Câmara dos Deputados", "deputados", 513), "senado": ("Senado", "Senado Federal", "senadores", 81)}
NA = {"camara": ("na", "da", "a"), "senado": ("no", "do", "o")}
def pl(n, s, p): return f"{n} {s if n == 1 else p}"
NOME_VOTO = {"Sim": "Sim", "Não": "Não", "Abstenção": "Abstenção", "Obstrução": "Obstrução", "Artigo 17": "Art. 17 (presidente da sessão)",
             "Presidente (art. 51 RISF)": "Presidente da sessão", "P-NRV": "Presente, sem voto registrado", "NCom": "Não compareceu", "AP": "Em atividade parlamentar",
             "LS": "Licença saúde", "LP": "Licença particular", "MIS": "Em missão", "REP": "Em representação", "LAP": "Licença à gestante/adotante", "": "Sem descrição do voto"}
CAT = {"Sim": "sim", "Não": "nao", "Abstenção": "abst", "Obstrução": "obst", "NCom": "aus"}
CATN = [("sim", "Sim"), ("nao", "Não"), ("abst", "Abstenção"), ("obst", "Obstrução"), ("outros", "Outros registros"), ("aus", "Ausentes")]
COR = {"sim": "#1f6f43", "nao": "#a32d1c", "abst": "#7a6a2c", "obst": "#5b3f8c", "outros": "#6b7280", "aus": "#c7cbd1"}
_CACHE = {}


def carregar(S):
    if "v" in _CACHE: return _CACHE["v"]
    d = S.ROOT / "data/votacoes"; vs = []
    for f in sorted(d.glob("*.json.gz")) if d.exists() else []:
        vs += json.loads(gzip.decompress(f.read_bytes()))
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8")) if (d / "meta.json").exists() else {}
    for v in vs:
        p = v.get("prop") or {}
        v["titulo"] = (f"{p['sigla']} {p['numero']}/{p['ano']}" if p.get("sigla") and p.get("numero") and p.get("ano") else re.sub(r"\s*\(.*?\)", "", p.get("titulo") or "").strip()) or (v["descricao"][:60] if v["descricao"] else f"Votação {v['id']}")
        base = slugify(f"{v['data']} {p.get('sigla') or ''} {p.get('numero') or ''} {p.get('ano') or ''}".strip()) or v["data"]
        v["slug"] = f"{base}-{slugify(v['id'])}"; v["url"] = f"/votacoes/{v['casa']}/{v['slug']}/"
        a = v.get("aprovacao"); ds = (v["descricao"] or "").lower()
        if a is None: a = 1 if ds.startswith(("aprovad", "aprovação")) else (0 if ds.startswith(("rejeitad", "rejeição")) else None)
        v["res"] = {1: "Aprovado", 0: "Rejeitado"}.get(a, "Ver descrição oficial")
        c = collections.Counter()
        for r in v["votos"]: c[CAT.get(r[1], "outros")] += 1
        if v["casa"] == "camara": c["aus"] = max(0, 513 - len(v["votos"]))
        v["placar"] = c
        g = v["orient"].get("Governo") or v["orient"].get("GOVERNO") or ""
        v["gov"] = g.capitalize().replace("Nao", "Não") if g else ""
        v["temas"] = (p.get("temas") or [])
    vs.sort(key=lambda x: (x["data"], x["hora"], x["id"]))
    seq = collections.Counter(); tot = collections.Counter((v["casa"], v["titulo"], v["data"]) for v in vs)
    for v in vs:  # o que foi votado (texto principal, destaque, emenda, turno) e nº da votação no dia
        o = v.get("abertura") or v["descricao"] or ""
        o = re.sub(r"\s*\([^)]{25,}\)", "", o).strip().rstrip(".")
        o = re.sub(r"^Votação (nominal )?(d[aoe]s? )?", "", o, flags=re.I)
        v["obj"] = (o[:1].upper() + o[1:])[:110] if o else ""
        k = (v["casa"], v["titulo"], v["data"]); seq[k] += 1
        v["seq"] = (seq[k], tot[k])
    vs.reverse()
    _CACHE["v"] = (vs, meta); return _CACHE["v"]


def _maioria(v):
    """Voto majoritário (Sim/Não) de cada partido na votação; empate = sem maioria."""
    c = collections.defaultdict(collections.Counter)
    for r in v["votos"]:
        if r[1] in ("Sim", "Não"): c[v["partidos"][r[2]]][r[1]] += 1
    out = {}
    for p, k in c.items():
        if k["Sim"] != k["Não"]: out[p] = "Sim" if k["Sim"] > k["Não"] else "Não"
    return out


def resumo(S):
    """Por parlamentar (chave 'camara:<id>' ou 'senado:<id>'): últimas votações e alinhamentos (metodologia em /votacoes/metodologia/)."""
    if "r" in _CACHE: return _CACHE["r"]
    vs, _ = carregar(S); R = {}
    for v in vs:  # mais recentes primeiro
        maj = _maioria(v)
        for pid, voto, pi, uf, nome in v["votos"]:
            k = f"{v['casa']}:{pid}"; x = R.setdefault(k, {"n": 0, "sn": 0, "part_t": 0, "part_a": 0, "gov_t": 0, "gov_a": 0, "ult": []})
            x["n"] += 1; p = v["partidos"][pi]
            if voto in ("Sim", "Não"):
                x["sn"] += 1
                if p in maj: x["part_t"] += 1; x["part_a"] += maj[p] == voto
                if v["gov"] in ("Sim", "Não"): x["gov_t"] += 1; x["gov_a"] += v["gov"] == voto
            if len(x["ult"]) < 10: x["ult"].append((v, voto, p))
    _CACHE["r"] = R; return R


def bloco_parlamentar(S, casa, pid, nome):
    """HTML do bloco "Como votou" para a página do parlamentar (vazio se não há votos)."""
    x = resumo(S).get(f"{casa}:{pid}")
    if not x: return ""
    vs, meta = carregar(S); tot_casa = sum(1 for v in vs if v["casa"] == casa)
    linhas = [[data_br(v["data"]), f'<a href="{v["url"]}">{E(v["titulo"])}</a>', E(NOME_VOTO.get(voto, voto)), E(v["gov"] or "Sem orientação"), E(v["res"])] for v, voto, p in x["ult"]]
    pp = pct(x["part_a"], x["part_t"]); pg = pct(x["gov_a"], x["gov_t"])
    return (f'<h2 id="votacoes">Como votou nas votações nominais do plenário</h2><p>Desde fevereiro de 2023, {E(nome)} tem voto registrado em <strong>{num(x["n"])}</strong> das {num(tot_casa)} votações nominais de plenário {NA[casa][1]} {CASA[casa][1]} compiladas pelo Estrato, '
            f'com {num(x["sn"])} votos “sim” ou “não”. Nesses votos, acompanhou a maioria da própria bancada em <strong>{pp}</strong> ({num(x["part_a"])} de {num(x["part_t"])}) e a orientação do governo em <strong>{pg}</strong> ({num(x["gov_a"])} de {num(x["gov_t"])} votações com orientação “sim” ou “não”).</p>'
            + S.table(["Data", "Votação", "Voto", "Orientação do governo", "Resultado"], linhas, "Últimas 10 votações nominais com voto registrado")
            + '<p class="src">Fonte: dados abertos da Câmara e do Senado. Alinhamento é um dado descritivo, não uma avaliação; veja a <a href="/votacoes/metodologia/">metodologia</a> e o <a href="/votacoes/">placar de votações</a>.</p>')


def _barra(c, total):
    """Gráfico de barra empilhada em SVG estático (sem JS)."""
    x = 0; r = []
    for k, n in CATN:
        w = 100 * c.get(k, 0) / total if total else 0
        if w > 0: r.append(f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="10" fill="{COR[k]}"><title>{n}: {c.get(k, 0)}</title></rect>'); x += w
    leg = "".join(f'<li><i style="background:{COR[k]}"></i>{n}: <b>{c.get(k, 0)}</b></li>' for k, n in CATN if c.get(k, 0))
    return f'<figure class="vbar"><svg viewBox="0 0 100 10" preserveAspectRatio="none" role="img" aria-label="Distribuição dos votos" width="100%" height="28">{"".join(r)}</svg><ul class="vleg">{leg}</ul></figure>'


def _mini(c, t):
    s = 100 * c.get("sim", 0) / t if t else 0; n = 100 * c.get("nao", 0) / t if t else 0
    return f'<span class="mbar" aria-hidden="true"><i style="width:{s:.0f}%;background:{COR["sim"]}"></i><i style="width:{n:.0f}%;background:{COR["nao"]}"></i></span>'


def _grupo(v, idx):
    g = collections.defaultdict(collections.Counter)
    for r in v["votos"]:
        key = v["partidos"][r[2]] if idx == "p" else r[3]
        g[key][CAT.get(r[1], "outros")] += 1
    return g


def build(S):
    vs, meta = carregar(S)
    if not vs: return {"urls": []}
    ids = {"camara": {d["id"]: d["url"] for d in S.parl["deps"]}, "senado": {int(x["id"]): x["url"] for x in S.parl["sens"]}}
    part_urls = {u for u in S.urls if u.startswith("/partidos/")}
    col = (meta.get("coletado_em") or vs[0]["data"])[:10]
    fam = "votacoes"; urls = []
    gloss = lambda s, n: f'<a href="/glossario/{s}/">{E(n)}</a>' if f"/glossario/{s}/" in S.urls else E(n)
    for v in vs:
        casa = v["casa"]; cn, cl, kind, cad = CASA[casa]; na, da, ar = NA[casa]; c = v["placar"]; p = v.get("prop") or {}
        total = sum(c.values()); reg = len(v["votos"]); quem = "deputados" if casa == "camara" else "senadores"
        ttl = v["titulo"]; dbr = data_br(v["data"])
        lead = (f'<p class="snippet">Em {dbr}{" às " + v["hora"] if v["hora"] else ""}, o plenário {da} {cl} fez votação nominal sobre <strong>{E(ttl)}</strong>. '
                f'Resultado: <strong>{E(v["res"])}</strong>, com {c.get("sim", 0)} votos “sim”, {c.get("nao", 0)} “não”'
                + (f', {pl(c["abst"], "abstenção", "abstenções")}' if c.get("abst") else "") + (f' e {pl(c["obst"], "obstrução", "obstruções")}' if c.get("obst") else "") + f'. {reg} {quem} tiveram voto registrado.</p>')
        info = [("Proposição", E(ttl)), ("Ementa", E(p.get("ementa") or "")), ("O que foi votado", E(v.get("abertura") or v["descricao"])),
                ("Descrição oficial do resultado", E(v["descricao"]) if v.get("abertura") else ""), ("Data", dbr), ("Casa", cl), ("Temas (classificação oficial)", E(", ".join(v["temas"]))),
                ("Orientação do governo", E(v["gov"] or "Sem orientação registrada"))]
        nv = f" (votação {v['seq'][0]} de {v['seq'][1]} no dia)" if v["seq"][1] > 1 else ""
        body = f'<article class="post"><h1>{E(ttl)}: votação {na} {cn} em {dbr}{nv}</h1>{lead}'
        body += '<div class="tw"><table><tbody>' + "".join(f'<tr><th scope="row">{k}</th><td>{x}</td></tr>' for k, x in info if x) + "</tbody></table></div>"
        body += "<h2>Placar</h2>" + _barra(c, total) + '<div class="stats">' + "".join(f'<div class="stat"><b>{c.get(k, 0)}</b><span>{n}</span></div>' for k, n in CATN if k != "aus" or c.get(k)) + "</div>"
        if casa == "camara": body += f'<p>“Ausentes” são as cadeiras sem voto registrado nesta votação, calculadas sobre as {cad} cadeiras da Câmara (inclui licenças e vagas momentâneas). “Outros registros” reúnem o voto do presidente da sessão (art. 17 do Regimento) e registros sem descrição.</p>'
        else: body += '<p>No Senado, “Ausentes” são os senadores registrados como “não compareceu”. “Outros registros” incluem presidente da sessão, licenças, missões, atividade parlamentar e presença sem voto.</p>'
        gp = _grupo(v, "p")
        rows = []
        for pt, k in sorted(gp.items(), key=lambda x: (-sum(x[1].values()), x[0])):
            t = sum(k.values()); pu = f"/partidos/{slugify(pt)}/"
            rows.append([f'<a href="{pu}">{E(pt)}</a>' if pu in part_urls else E(pt), str(k.get("sim", 0)), str(k.get("nao", 0)), str(k.get("abst", 0)), str(k.get("obst", 0)), str(k.get("outros", 0) + k.get("aus", 0)), str(t), _mini(k, t)])
        body += "<h2>Voto por partido</h2>" + S.table(["Partido", "Sim", "Não", "Abst.", "Obstr.", "Outros", "Total", "Sim × Não"], rows, "Votos registrados por partido na data da votação")
        gu = _grupo(v, "u")
        rows = [[f'<a href="/deputados/uf/{u.lower()}/">{UF.get(u, u)}</a>' if casa == "camara" and u in UF else E(UF.get(u, u)), str(k.get("sim", 0)), str(k.get("nao", 0)), str(k.get("abst", 0) + k.get("obst", 0) + k.get("outros", 0) + k.get("aus", 0)), str(sum(k.values())), _mini(k, sum(k.values()))]
                for u, k in sorted(gu.items(), key=lambda x: UF.get(x[0], x[0]))]
        body += "<h2>Voto por estado</h2>" + S.table(["Estado", "Sim", "Não", "Outros", "Total", "Sim × Não"], rows, "Votos registrados por estado")
        if v["orient"]:
            ori = sorted(v["orient"].items(), key=lambda x: (x[0].lower() not in ("governo", "maioria", "minoria", "oposição", "oposicao"), x[0].lower()))
            body += f'<h2>Orientação do governo e das lideranças</h2><p>A {gloss("lider-partidario", "liderança")} de cada partido, bloco ou federação pode orientar o voto da bancada. A tabela reproduz as orientações registradas pel{ar} {cl}.</p>' + S.table(["Liderança", "Orientação"], [[E(a), E(b.capitalize().replace("Nao", "Não"))] for a, b in ori])
        # lista nominal
        grupos = collections.OrderedDict()
        for r in sorted(v["votos"], key=lambda r: slugify(r[4])):
            grupos.setdefault(NOME_VOTO.get(r[1], r[1] or "Sem descrição"), []).append(r)
        ordem = sorted(grupos, key=lambda g: ["Sim", "Não", "Abstenção", "Obstrução"].index(g) if g in ("Sim", "Não", "Abstenção", "Obstrução") else 9)
        body += f'<h2>Como votou cada {"deputado" if casa == "camara" else "senador"}</h2>'
        for g in ordem:
            li = "".join((f'<li><a href="{ids[casa][r[0]]}">{E(r[4])}</a> <small>{E(v["partidos"][r[2]])}-{E(r[3])}</small></li>' if r[0] in ids[casa] else f'<li>{E(r[4])} <small>{E(v["partidos"][r[2]])}-{E(r[3])}</small></li>') for r in grupos[g])
            body += f'<h3>{E(g)} ({len(grupos[g])})</h3><ul class="nlist">{li}</ul>'
        fontes = []
        if casa == "camara":
            if p.get("id"): fontes.append(f'<a href="https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={p["id"]}" target="_blank" rel="noopener">ficha de tramitação na Câmara</a>')
            fontes.append(f'<a href="{E(v["api"])}" target="_blank" rel="noopener">votação na API de Dados Abertos</a>')
            fontes.append(f'<a href="{E(v["api"])}/votos" target="_blank" rel="noopener">votos nominais (API)</a>')
        else:
            if v.get("fonte"): fontes.append(f'<a href="{E(v["fonte"])}" target="_blank" rel="noopener">página da matéria no Senado</a>')
            fontes.append(f'<a href="{E(v["api"])}" target="_blank" rel="noopener">votação na API de Dados Abertos do Senado</a>')
        body += (f'<p class="src">Fonte oficial: {", ".join(fontes)}. Partido e estado são os registrados pel{ar} {cl} na data da votação. Compilação do Estrato em {data_br(col)}; '
                 f'veja a <a href="/votacoes/metodologia/">metodologia</a> e o <a href="/votacoes/{casa}/{v["data"][:4]}/">placar de {v["data"][:4]}</a>.</p></article>')
        big = max(gp.items(), key=lambda x: sum(x[1].values())); bk = big[1]
        uf_big = max(gu.items(), key=lambda x: sum(x[1].values())); uk = uf_big[1]
        faqs = [(f"Qual foi o resultado da votação de {ttl} em {dbr}?", f"{E(v['res'])}. Foram {c.get('sim', 0)} votos “sim”, {c.get('nao', 0)} “não”, {pl(c.get('abst', 0), 'abstenção', 'abstenções')} e {pl(c.get('obst', 0), 'obstrução', 'obstruções')}, segundo o registro oficial {da} {cl}."),
                (f"Quantos {quem} votaram nesta votação?", f"{reg} {quem} tiveram voto registrado" + (f", de {cad} cadeiras. As demais {c.get('aus', 0)} ficaram sem registro de voto." if casa == "camara" else f". Foram registrados {c.get('aus', 0)} senadores como “não compareceu”.")),
                (f"Como votou o {big[0]}?", f"A bancada do {E(big[0])}, a maior nesta votação, registrou {bk.get('sim', 0)} votos “sim”, {bk.get('nao', 0)} “não” e {sum(bk.values()) - bk.get('sim', 0) - bk.get('nao', 0)} outros registros."),
                ("Qual foi a orientação do governo?", (f"A liderança do governo orientou “{E(v['gov'].lower())}”." if v["gov"] else "Não há orientação do governo registrada para esta votação.") + f" Ao todo, {len(v['orient'])} lideranças tiveram orientação registrada."),
                (f"Como votaram os {quem} {('de ' + UF.get(uf_big[0], uf_big[0])) if uf_big[0] in UF else ''}?", f"Dos {sum(uk.values())} {quem} {('de ' + UF.get(uf_big[0], uf_big[0])) if uf_big[0] in UF else ''} com voto registrado, {uk.get('sim', 0)} votaram “sim” e {uk.get('nao', 0)} votaram “não”."),
                ("Onde estão os dados oficiais desta votação?", f"Na API de Dados Abertos {'da Câmara dos Deputados' if casa == 'camara' else 'do Senado Federal'}, com link nesta página. O Estrato compila os registros sem alterar votos.")]
        ld = {"@type": "Dataset", "name": f"Votação nominal: {ttl} ({cl}, {dbr})", "description": f"Votos nominais de {reg} {quem} na votação de {ttl} no plenário {da} {cl} em {dbr}: resultado {v['res'].lower()}, {c.get('sim', 0)} sim e {c.get('nao', 0)} não, com orientação das lideranças.",
              "url": S.BASE + v["url"], "temporalCoverage": v["data"], "spatialCoverage": "Brasil", "isBasedOn": v["api"], "license": "https://creativecommons.org/licenses/by/4.0/deed.pt-br", "isAccessibleForFree": True, "inLanguage": "pt-BR",
              "creator": {"@id": S.BASE + "/#org"}, "keywords": ["votação nominal", cl] + v["temas"][:3], "variableMeasured": ["voto", "partido", "unidade da federação", "orientação de bancada"],
              "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{S.BASE}/dados/votos-{casa}-{v['data'][:4]}.csv"}]}
        tt = (f"{ttl}: votação {v['seq'][0]} de {v['seq'][1]} {na} {cn} em {dbr}" if v["seq"][1] > 1 else f"{ttl}: votação {na} {cn} em {dbr}") + (f" – {v['obj']}" if v["obj"] else "")
        S.write(v["url"], S.page(tt, f"{v['res']} no plenário {da} {cl} em {dbr}: {c.get('sim', 0)} sim, {c.get('nao', 0)} não. Voto por partido, estado, orientação do governo e lista nominal.",
                                 v["url"], body, faqs=faqs, crumbs=[("Votações", "/votacoes/"), (f"{cn} {v['data'][:4]}", f"/votacoes/{casa}/{v['data'][:4]}/"), (ttl, v["url"])], jsonld=ld),
                familia=fam, lastmod=v["data"])
        urls.append(v["url"])
    # listas anuais
    anos = sorted({(v["casa"], v["data"][:4]) for v in vs})
    def linha(v):
        c = v["placar"]
        return [data_br(v["data"]), f'<a href="{v["url"]}">{E(v["titulo"])}</a>', E(v["res"]), f'{c.get("sim", 0)} × {c.get("nao", 0)}', E(v["gov"] or "—")]
    for casa, ano in anos:
        lst = [v for v in vs if v["casa"] == casa and v["data"][:4] == ano]; cn, cl, _, _ = CASA[casa]; na, da, ar = NA[casa]; u = f"/votacoes/{casa}/{ano}/"
        ap = sum(1 for v in lst if v["res"] == "Aprovado"); rj = sum(1 for v in lst if v["res"] == "Rejeitado")
        tp = collections.Counter(t for v in lst for t in v["temas"]).most_common(3)
        props = collections.Counter((v.get("prop") or {}).get("sigla") for v in lst if v.get("prop"))
        body = (f'<section class="blk"><h1>Votações nominais no plenário {da} {cn} em {ano}</h1><p class="snippet">Em {ano}, o plenário {da} {cl} fez <strong>{len(lst)} votações nominais</strong> com voto individual registrado: {ap} com resultado “aprovado” e {rj} “rejeitado”, segundo os dados oficiais.</p>'
                + S.table(["Data", "Votação", "Resultado", "Sim × Não", "Governo"], [linha(v) for v in lst], f"Votações nominais de {ano} ({cn}), da mais recente para a mais antiga")
                + f'<p class="src">Fonte: dados abertos {da} {cl}. Veja todas as casas e anos no <a href="/votacoes/">placar de votações</a>.</p></section>')
        faqs = [(f"Quantas votações nominais {ar} {cn} fez em {ano}?", f"{len(lst)} votações nominais de plenário com voto individual registrado, segundo a compilação de {data_br(col)}."),
                (f"Quantas foram aprovadas em {ano}?", f"{ap} tiveram resultado “aprovado” e {rj} “rejeitado”; as demais têm resultado descrito de outra forma no registro oficial."),
                (f"Quais temas mais apareceram em {ano}?", (", ".join(f"{E(t)} ({n})" for t, n in tp) + ", segundo a classificação temática oficial das proposições.") if tp else "As proposições deste período não têm classificação temática registrada."),
                (f"Que tipos de proposição foram votados em {ano}?", ", ".join(f"{E(k)}: {n}" for k, n in props.most_common(5) if k) + "."),
                ("O que conta como votação nominal?", "É a votação em que o voto de cada parlamentar fica registrado no painel eletrônico. Votações simbólicas não entram no placar porque não têm voto individual.")]
        S.write(u, S.page(f"Votações nominais {da} {cn} em {ano}: placar e resultados", f"As {len(lst)} votações nominais de plenário {da} {cl} em {ano}, com resultado, placar e orientação do governo, a partir dos dados oficiais.", u, body, faqs=faqs,
                          crumbs=[("Votações", "/votacoes/"), (f"{cn} {ano}", u)], jsonld=S.itemlist([(v["titulo"], v["url"]) for v in lst])), familia=fam, lastmod=lst[0]["data"])
        urls.append(u)
    # índice JSON para os filtros do hub
    idx = [{"u": v["url"], "t": v["titulo"], "d": v["data"], "c": v["casa"], "r": v["res"], "s": v["placar"].get("sim", 0), "n": v["placar"].get("nao", 0), "g": v["gov"], "m": v["temas"][:3], "e": ((v.get("prop") or {}).get("ementa") or "")[:160]} for v in vs]
    (S.OUT / "votacoes").mkdir(parents=True, exist_ok=True)
    (S.OUT / "votacoes/indice.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temas = sorted({t for v in vs for t in v["temas"]})
    tc = {k: sum(1 for v in vs if v["casa"] == k) for k in CASA}
    opt = lambda xs: "".join(f'<option value="{E(a)}">{E(b)}</option>' for a, b in xs)
    form = (f'<form class="vfil" role="search" onsubmit="return false"><label>Ano<select id="fa"><option value="">Todos</option>{opt([(a, a) for a in sorted({v["data"][:4] for v in vs}, reverse=True)])}</select></label>'
            f'<label>Casa<select id="fc"><option value="">Ambas</option>{opt([("camara", "Câmara"), ("senado", "Senado")])}</select></label>'
            f'<label>Tema<select id="ft"><option value="">Todos</option>{opt([(t, t) for t in temas])}</select></label>'
            f'<label>Resultado<select id="fr"><option value="">Todos</option>{opt([("Aprovado", "Aprovado"), ("Rejeitado", "Rejeitado"), ("Ver descrição oficial", "Outros")])}</select></label>'
            f'<label class="vq">Buscar<input id="fq" type="search" placeholder="Ex.: PEC 45, reforma tributária, arcabouço" autocomplete="off"></label></form><p id="fn" aria-live="polite"></p><a id="vidx" href="/votacoes/indice.json" hidden>índice</a>')
    ult = vs[:40]
    lista = '<ul class="vlist" id="vl">' + "".join(f'<li><a href="{v["url"]}">{E(v["titulo"])}</a><small>{CASA[v["casa"]][0]} · {data_br(v["data"])} · {E(v["res"])} · {v["placar"].get("sim", 0)} × {v["placar"].get("nao", 0)}</small></li>' for v in ult) + "</ul>"
    js = ("<script>(function(){var X=document.getElementById('vidx'),P=X.getAttribute('href').replace('/votacoes/indice.json',''),I=null,L=document.getElementById('vl'),N=document.getElementById('fn'),F=['fa','fc','ft','fr','fq'].map(function(i){return document.getElementById(i)});"
          "function n(s){return(s||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'')}"
          "function e(s){return String(s).replace(/[&<>\"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]})}"
          "function d(s){return s.slice(8,10)+'/'+s.slice(5,7)+'/'+s.slice(0,4)}"
          "function r(){var a=F[0].value,c=F[1].value,t=F[2].value,s=F[3].value,q=n(F[4].value),o=I.filter(function(x){return(!a||x.d.slice(0,4)==a)&&(!c||x.c==c)&&(!t||x.m.indexOf(t)>=0)&&(!s||x.r==s)&&(!q||n(x.t+' '+x.e).indexOf(q)>=0)});"
          "N.textContent=o.length+' votação(ões) encontrada(s)'+(o.length>200?'; mostrando as 200 mais recentes':'');"
          "L.innerHTML=o.slice(0,200).map(function(x){return'<li><a href=\"'+P+x.u+'\">'+e(x.t)+'</a><small>'+(x.c=='camara'?'Câmara':'Senado')+' · '+d(x.d)+' · '+e(x.r)+' · '+x.s+' × '+x.n+'</small></li>'}).join('')}"
          "function g(){if(I)return r();fetch(X.href).then(function(x){return x.json()}).then(function(j){I=j;r()})}"
          "F.forEach(function(f){f.addEventListener(f.tagName=='INPUT'?'input':'change',g)})})();</script>")
    anos_links = "".join(f'<a class="chip" href="/votacoes/{c}/{a}/">{CASA[c][0]} {a} ({sum(1 for v in vs if v["casa"] == c and v["data"][:4] == a)})</a>' for c, a in sorted(anos, key=lambda x: (x[0], x[1]), reverse=True))
    body = (f'<section class="blk"><h1>Placar de votações nominais da Câmara e do Senado</h1><p class="snippet">O Estrato reúne <strong>{num(tc["camara"])} votações nominais</strong> do plenário da Câmara e <strong>{num(tc["senado"])}</strong> do plenário do Senado desde fevereiro de 2023 (57ª legislatura), com placar, voto por partido e estado, orientação do governo e o voto de cada parlamentar.</p>'
            f'<h2>Filtrar votações</h2>{form}<h2>Votações mais recentes</h2>{lista}{js}<h2>Por casa e ano</h2><div class="chips">{anos_links}</div>'
            f'<h2>Como ler o placar</h2><p>Cada página mostra o que foi votado, o resultado oficial e a contagem de votos “sim”, “não”, abstenções e obstruções. Só entram {gloss("votacao-nominal", "votações nominais")}, em que o voto de cada parlamentar fica registrado; votações simbólicas e secretas (como as de autoridades no Senado) não têm voto individual público. '
            f'Partido e estado são os da data da votação. O placar não classifica parlamentares nem partidos.</p><p>Veja a <a href="/votacoes/metodologia/">metodologia</a> e baixe os dados em <a href="/dados/#votacoes">CSV</a>.</p>'
            f'<p class="src">Fontes: <a href="https://dadosabertos.camara.leg.br/" target="_blank" rel="noopener">Dados Abertos da Câmara</a> e <a href="https://legis.senado.leg.br/dadosabertos" target="_blank" rel="noopener">Dados Abertos do Senado</a>. Atualização diária; compilação de {data_br(col)}.</p></section>')
    ult_c = next(v for v in vs if v["casa"] == "camara"); ult_s = next((v for v in vs if v["casa"] == "senado"), None)
    faqs = [("Quantas votações nominais estão no placar?", f"{num(tc['camara'])} da Câmara e {num(tc['senado'])} do Senado, de fevereiro de 2023 até {data_br(vs[0]['data'])}."),
            ("Qual foi a votação nominal mais recente da Câmara?", f"{E(ult_c['titulo'])}, em {data_br(ult_c['data'])}, com resultado “{E(ult_c['res'].lower())}” ({ult_c['placar'].get('sim', 0)} sim e {ult_c['placar'].get('nao', 0)} não)."),
            ("Qual foi a votação nominal mais recente do Senado?", (f"{E(ult_s['titulo'])}, em {data_br(ult_s['data'])}, com resultado “{E(ult_s['res'].lower())}” ({ult_s['placar'].get('sim', 0)} sim e {ult_s['placar'].get('nao', 0)} não)." if ult_s else "Ainda não há votações do Senado compiladas.")),
            ("Por que algumas votações não aparecem?", "Votações simbólicas não registram voto individual, e votações secretas, como as de indicação de autoridades no Senado, não divulgam o voto de cada senador."),
            ("Com que frequência o placar é atualizado?", "Uma vez por dia, a partir dos arquivos oficiais da Câmara e da API do Senado, com cache para baixar só o que mudou."),
            ("O placar avalia os parlamentares?", "Não. As páginas mostram dados factuais dos registros oficiais, sem ranking. O alinhamento exibido nas páginas dos parlamentares segue uma metodologia descrita e publicada.")]
    S.write("/votacoes/", S.page("Placar de votações nominais: Câmara e Senado desde 2023", f"Placar das {num(tc['camara'] + tc['senado'])} votações nominais do plenário da Câmara e do Senado desde 2023: resultado, voto por partido e estado, orientação do governo e lista nominal.",
                                 "/votacoes/", body, faqs=faqs, crumbs=[("Votações", "/votacoes/")], jsonld=[S.itemlist([(v["titulo"], v["url"]) for v in vs[:50]]),
                                 {"@type": "Dataset", "name": "Placar de votações nominais da Câmara e do Senado (57ª legislatura)", "description": "Votos nominais de deputados e senadores em votações de plenário desde fevereiro de 2023, com partido, estado, orientação das lideranças e resultado, compilados das APIs oficiais.",
                                  "url": S.BASE + "/votacoes/", "temporalCoverage": f"2023-02-01/{vs[0]['data']}", "license": "https://creativecommons.org/licenses/by/4.0/deed.pt-br", "isAccessibleForFree": True, "creator": {"@id": S.BASE + "/#org"}, "inLanguage": "pt-BR",
                                  "isBasedOn": ["https://dadosabertos.camara.leg.br/", "https://legis.senado.leg.br/dadosabertos"], "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{S.BASE}/dados/votacoes.csv"}]}]),
            familia="paginas", lastmod=vs[0]["data"])
    urls.append("/votacoes/")
    # metodologia
    body = ('<article class="post"><h1>Metodologia do placar de votações</h1><p class="snippet">Como o Estrato coleta, organiza e resume as votações nominais de plenário da Câmara e do Senado, e como calcula os percentuais de alinhamento exibidos nas páginas dos parlamentares.</p>'
            '<h2>Fontes e coleta</h2><p>Câmara: arquivos anuais oficiais de votações, votos, orientações, proposições e temas da API de Dados Abertos. Senado: serviço de votações e de orientação de bancadas da API de Dados Abertos. A coleta roda uma vez por dia e baixa de novo apenas os arquivos que mudaram.</p>'
            '<h2>O que entra</h2><p>Votações do plenário (Câmara: órgão PLEN; Senado: Plenário) a partir de 1º de fevereiro de 2023, início da 57ª legislatura, com voto individual registrado. Votações simbólicas e secretas ficam de fora porque não têm voto individual público. Uma mesma proposição pode ter várias votações (texto principal, destaques, emendas, turnos).</p>'
            '<h2>Categorias do placar</h2><p>“Sim”, “Não”, “Abstenção” e “Obstrução” seguem o registro oficial. Na Câmara, “Ausentes” são as cadeiras sem voto registrado, calculadas sobre 513; “Outros registros” incluem o voto do presidente da sessão (art. 17 do Regimento Interno). No Senado, “Ausentes” são os registros “não compareceu”; licenças, missões, atividade parlamentar e presença sem voto entram em “Outros registros”.</p>'
            '<h2>Alinhamento ao partido</h2><p>Para cada votação, calcula-se o voto majoritário (“sim” ou “não”) da bancada do partido do parlamentar na data da votação; empates não contam. O percentual é a fração dos votos “sim” ou “não” do parlamentar que coincidiram com essa maioria. Abstenções, obstruções e ausências não entram no cálculo.</p>'
            '<h2>Alinhamento à orientação do governo</h2><p>Consideram-se só as votações em que a liderança do governo orientou “sim” ou “não”. O percentual é a fração dos votos “sim” ou “não” do parlamentar iguais à orientação. Orientações “liberado”, “obstrução” ou ausentes não entram.</p>'
            '<h2>Limites</h2><p>Os percentuais descrevem votos registrados e não medem qualidade de mandato, presença em comissões nem outras atividades. Mudanças de partido são respeitadas porque se usa o partido da data de cada votação. Durante o período eleitoral, o Estrato não publica rankings de parlamentares.</p>'
            '<p>Os dados completos estão em <a href="/dados/#votacoes">CSV</a>. Erros podem ser comunicados pela página de <a href="/correcoes/">correções</a>.</p></article>')
    faqs = [("De onde vêm os votos?", "Das APIs oficiais de Dados Abertos da Câmara dos Deputados e do Senado Federal."),
            ("Como é calculado o alinhamento ao partido?", "Pela fração dos votos “sim” ou “não” do parlamentar que coincidiram com a maioria da própria bancada em cada votação."),
            ("Abstenção conta como desalinhamento?", "Não. Abstenções, obstruções e ausências ficam fora do cálculo."),
            ("O que acontece se o parlamentar mudou de partido?", "Cada votação usa o partido registrado na data em que ocorreu."),
            ("Por que não há ranking?", "O placar é factual. Durante o período eleitoral, o Estrato não publica classificações de melhor ou pior parlamentar.")]
    S.write("/votacoes/metodologia/", S.page("Metodologia do placar de votações e do alinhamento", "Como o Estrato coleta as votações nominais da Câmara e do Senado e calcula o alinhamento de cada parlamentar ao partido e ao governo.",
                                             "/votacoes/metodologia/", body, faqs=faqs, crumbs=[("Votações", "/votacoes/"), ("Metodologia", "/votacoes/metodologia/")]), familia="paginas", lastmod=col)
    urls.append("/votacoes/metodologia/")
    # CSV
    out = S.OUT / "dados"; out.mkdir(parents=True, exist_ok=True); sets = []
    with (out / "votacoes.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["casa", "id_votacao", "data", "proposicao", "ementa", "resultado", "sim", "nao", "abstencao", "obstrucao", "outros", "ausentes", "orientacao_governo", "temas", "url_estrato", "url_api"])
        for v in vs:
            c = v["placar"]; w.writerow([v["casa"], v["id"], v["data"], v["titulo"], (v.get("prop") or {}).get("ementa") or "", v["res"], c.get("sim", 0), c.get("nao", 0), c.get("abst", 0), c.get("obst", 0), c.get("outros", 0), c.get("aus", 0), v["gov"], "|".join(v["temas"]), S.BASE + v["url"], v["api"]])
    sets.append(("votacoes", "Votações nominais de plenário (Câmara e Senado)", "Uma linha por votação nominal desde 2023, com resultado, placar e orientação do governo.", len(vs)))
    for casa, ano in anos:
        lst = [v for v in vs if v["casa"] == casa and v["data"][:4] == ano]; n = 0
        with (out / f"votos-{casa}-{ano}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(["casa", "id_votacao", "data", "id_parlamentar", "nome", "partido", "uf", "voto", "orientacao_governo"])
            for v in reversed(lst):
                for r in v["votos"]: w.writerow([casa, v["id"], v["data"], r[0], r[4], v["partidos"][r[2]], r[3], r[1], v["gov"]]); n += 1
        sets.append((f"votos-{casa}-{ano}", f"Votos nominais: {CASA[casa][1]}, {ano}", f"Uma linha por parlamentar e votação nominal de plenário em {ano}.", n))
    S.votacoes_sets = sets; S.votacoes_col = col
    return {"urls": urls}
