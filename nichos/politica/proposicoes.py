"""Proposicoes relevantes da Camara (2023-2026): uma pagina por proposicao, hubs por tipo e por tema, paginas tema x ano.
Dados: data/proposicoes/proposicoes.json.gz (tools/datasets_proposicoes.py, arquivos em lote oficiais da Camara).
Familia `proposicoes` (noindex ate a onda propria); indexaveis desde o primeiro build: /proposicoes/, /proposicoes/tema/, /proposicoes/tema/<tema>/ e /proposicoes/tipo/<tipo>/.
Periodo eleitoral: so fatos (ementa, autoria, situacao, tramitacao); sem ranking de autores ou de temas (listas em ordem cronologica ou alfabetica)."""
import collections, csv, gzip, json
from core.site import E, slugify
from .dados import data_br, num, pct

TIPOS = {"PEC": ("Proposta de Emenda à Constituição", "pec", "Altera o texto da Constituição. Precisa de três quintos dos votos dos deputados e dos senadores, em dois turnos em cada Casa, e não passa por sanção do presidente."),
         "PLP": ("Projeto de Lei Complementar", "lei-complementar", "Regulamenta temas que a Constituição reserva a lei complementar e exige maioria absoluta dos membros de cada Casa."),
         "PL": ("Projeto de Lei", "projeto-de-lei", "É a proposta de lei ordinária: precisa de maioria simples, passa pelas duas Casas e depende de sanção ou veto do presidente."),
         "MPV": ("Medida Provisória", "medida-provisoria", "Ato do presidente com força de lei desde a publicação. Perde a validade se o Congresso não a votar em até 120 dias."),
         "PLV": ("Projeto de Lei de Conversão", "projeto-de-lei-de-conversao", "Texto em que o Congresso converte uma medida provisória em lei, com ou sem alterações."),
         "PDL": ("Projeto de Decreto Legislativo", "decreto-legislativo", "Trata de matéria de competência exclusiva do Congresso, como acordos internacionais, e não vai à sanção."),
         "PLN": ("Projeto de Lei do Congresso Nacional", "ldo", "Projeto de lei orçamentária ou de crédito, votado em sessão conjunta de deputados e senadores."),
         "REQ": ("Requerimento", "requerimento", "Pedido apresentado a órgão da Câmara, como urgência para uma proposição."),
         "PRC": ("Projeto de Resolução da Câmara", "projeto-de-resolucao", "Altera normas internas da Câmara; não passa pelo Senado nem pela sanção."),
         "PLV ": ("", "", "")}
REGIME = {"Urg": "Tramita em regime de urgência, o que dispensa prazos e etapas regimentais para que o plenário vote mais cedo.", "Prior": "Tramita em regime de prioridade, com prazos reduzidos em relação ao regime ordinário.",
          "Ordin": "Tramita em regime ordinário, com os prazos regimentais normais em cada comissão.", "Espec": "Tramita em regime especial, previsto para tipos como PEC e medida provisória.", "223": "Tramita em regime de medida provisória (art. 62 da Constituição)."}
_C = {}


def carregar(S):
    if "d" in _C: return _C["d"]
    f = S.ROOT / "data/proposicoes/proposicoes.json.gz"
    d = json.loads(gzip.decompress(f.read_bytes())) if f.exists() else {"props": [], "temas": {}, "total": {}, "coletado_em": ""}
    usados = set()
    for p in d["props"]:
        s = f"{p['t'].lower()}-{p['n']}-{p['a']}"; s = s if s not in usados else f"{s}-{p['id']}"; usados.add(s)
        p["slug"], p["url"] = s, f"/proposicoes/{s}/"; p["nome"] = f"{p['t']} {p['n']}/{p['a']}"
    d["ids"] = {p["id"]: p for p in d["props"]}
    por_aut = collections.defaultdict(list)
    for p in d["props"]:
        for a in p["aut"]:
            if a[0]: por_aut[a[0]].append(p)
    d["por_aut"] = por_aut
    _C["d"] = d; return d


def bloco_parlamentar(S, pid):
    """Bloco "Proposicoes de autoria" na pagina do deputado (so as relevantes da selecao)."""
    L = carregar(S).get("por_aut", {}).get(int(pid), [])
    if not L: return ""
    L = sorted(L, key=lambda p: p["d"], reverse=True)
    li = "".join(f'<li><a href="{p["url"]}">{E(p["nome"])}</a>: {E(p["e"][:150])}{"…" if len(p["e"]) > 150 else ""} <small>({E(p["sit"] or "situação não informada")})</small></li>' for p in L[:8])
    return (f'<h2 id="proposicoes">Proposições relevantes de que é autor ou coautor</h2><p>Entre as proposições de maior alcance compiladas pelo Estrato (PEC, medidas provisórias, projetos de lei complementar, projetos em urgência, aprovados ou votados nominalmente), '
            f'{num(len(L))} têm este parlamentar na lista de autores. Coautoria não indica relatoria nem posição na votação.</p><ul class="nlist">{li}</ul>'
            f'<p class="src">Fonte: arquivos em lote da Câmara (proposições e autores). Veja o <a href="/proposicoes/">painel de proposições</a>.</p>')


def _sit(p): return p["sit"] or "situação não informada"
def _aut_txt(p, n=3):
    nomes = [a[1] for a in p["aut"]]
    if not nomes: return "autoria não informada"
    return ", ".join(nomes[:n]) + (f" e mais {len(nomes) - n}" if len(nomes) > n else "")
def _curto(s, n=95): return s if len(s) <= n else s[:n].rsplit(" ", 1)[0].rstrip(",;:") + "…"
def _regime_txt(rg):
    for k, v in REGIME.items():
        if k in rg: return v
    return ""


def build(S):
    D = carregar(S); P = D["props"]
    if not P: return {"urls": []}
    col = D["coletado_em"][:10]; urls = []; fam = "proposicoes"
    dep_url = {a["id"]: a["url"] for a in S.parl["deps"]}
    from . import votacoes as V
    vs, _ = V.carregar(S); por_vot = collections.defaultdict(list)
    for v in vs:
        if v["casa"] == "camara" and (v.get("prop") or {}).get("id"): por_vot[int(v["prop"]["id"])].append(v)
    gl = lambda slug: f"/glossario/{slug}/" in S.urls
    temas = sorted(D["temas"]); tslug = {t: slugify(t) for t in temas}
    por_tema = collections.defaultdict(list)
    for p in P:
        for t in p["tem"]: por_tema[t].append(p)
    anos = D["anos"]
    # ---------------- uma pagina por proposicao ----------------
    for p in P:
        tn, gsl, expl = TIPOS.get(p["t"], (p["tn"], "", "")); tn = tn or p["tn"]; dbr = data_br(p["d"]); dst = data_br(p["dst"])
        auts = []
        for a in p["aut"][:30]:
            u = dep_url.get(a[0]); nome = f"{a[1]}" + (f" ({a[2]}-{a[3]})" if a[2] and a[3] else "")
            auts.append(f'<a href="{u}">{E(nome)}</a>' if u else E(nome))
        aut_html = ", ".join(auts) + (f" e outros {len(p['aut']) - 30} autores" if len(p["aut"]) > 30 else "")
        tem_html = ", ".join(f'<a href="/proposicoes/tema/{tslug[t]}/">{E(t)}</a>' for t in p["tem"])
        princ = D["ids"].get(int(p["pp"])) if p["pp"] and p["pp"].isdigit() else None
        info = [("Tipo", E(tn) + (f' (<a href="/glossario/{gsl}/">saiba mais</a>)' if gsl and gl(gsl) else "")), ("Número e ano", f"{p['n']}/{p['a']}"), ("Apresentada em", dbr), ("Ementa", E(p["e"])), ("Explicação da ementa", E(p["ed"])),
                ("Autoria", aut_html or "Não informada"), ("Temas (classificação oficial)", tem_html), ("Palavras-chave", E(p["k"].rstrip("."))),
                ("Situação atual", E(_sit(p)) + (f" (desde {dst})" if dst else "")), ("Órgão da última movimentação", E(p["org"])), ("Última tramitação", E(p["tr"])), ("Regime", E(p["rg"])), ("Apreciação", E(p["ap"])),
                ("Último despacho", E(p["desp"])), ("Proposição principal", f'<a href="{princ["url"]}">{E(princ["nome"])}</a>' if princ else (E(f"id {p['pp']} (fora da seleção do Estrato)") if p["pp"] else ""))]
        lead = (f'<p class="snippet">A {E(tn)} <strong>{p["n"]}/{p["a"]}</strong> foi apresentada na Câmara dos Deputados em {dbr} por {E(_aut_txt(p, 2))}. '
                f'{E(p["e"])} Situação em {dst or "data não informada"}: <strong>{E(_sit(p))}</strong>' + (f", com a última movimentação em {E(p['org'])}" if p["org"] else "") + ".</p>")
        body = f'<article class="post"><h1>{E(p["nome"])}: {E(_curto(p["e"], 110))}</h1>{lead}'
        body += '<div class="tw"><table><tbody>' + "".join(f'<tr><th scope="row">{k}</th><td>{x}</td></tr>' for k, x in info if x) + "</tbody></table></div>"
        body += f"<h2>Como esse tipo de proposição tramita</h2><p>{E(expl)} {E(_regime_txt(p['rg']))}</p>" if expl else ""
        vl = por_vot.get(p["id"], [])
        if vl:
            body += f'<h2>Votações nominais no plenário</h2><p>Esta proposição teve {len(vl)} votação(ões) nominal(is) no plenário da Câmara desde 2023, com o voto de cada deputado:</p><ul class="nlist">' + "".join(f'<li><a href="{v["url"]}">{data_br(v["data"])}: {E(v["obj"] or v["titulo"])}</a> ({E(v["res"])}, {v["placar"].get("sim", 0)} sim e {v["placar"].get("nao", 0)} não)</li>' for v in vl[:20]) + "</ul>"
        rel = [q for t in p["tem"][:1] for q in por_tema[t] if q["id"] != p["id"] and q["t"] == p["t"]][:6]
        rel_a = [q for a in p["aut"][:1] if a[0] for q in D["por_aut"].get(a[0], []) if q["id"] != p["id"]][:5]
        if rel or rel_a:
            body += "<h2>Para continuar</h2>"
            if rel: body += f'<p>Outras proposições do mesmo tipo e tema ({E(p["tem"][0])}):</p><ul class="nlist">' + "".join(f'<li><a href="{q["url"]}">{E(q["nome"])}</a>: {E(_curto(q["e"], 110))}</li>' for q in rel) + "</ul>"
            if rel_a: body += f'<p>Outras proposições relevantes de {E(p["aut"][0][1])}:</p><ul class="nlist">' + "".join(f'<li><a href="{q["url"]}">{E(q["nome"])}</a>: {E(_curto(q["e"], 110))}</li>' for q in rel_a) + "</ul>"
        fontes = [f'<a href="https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={p["id"]}" target="_blank" rel="noopener">ficha de tramitação na Câmara</a>', f'<a href="https://dadosabertos.camara.leg.br/api/v2/proposicoes/{p["id"]}" target="_blank" rel="noopener">proposição na API de Dados Abertos</a>']
        if p["it"]: fontes.append(f'<a href="{E(p["it"])}" target="_blank" rel="noopener">inteiro teor</a>')
        body += f'<p class="src">Fonte oficial: {", ".join(fontes)}. Dados compilados em {data_br(col)} a partir dos arquivos em lote da Câmara. Veja a <a href="/proposicoes/tipo/{p["t"].lower()}/">lista de {E(p["t"])}</a> e a <a href="/proposicoes/metodologia/">metodologia</a>.</p></article>'
        faqs = [(f"Qual é a situação atual da {p['nome']}?", f"{E(_sit(p))}" + (f", registrada em {dst}" if dst else "") + (f", com a última movimentação em {E(p['org'])}" if p["org"] else "") + ", segundo a ficha de tramitação da Câmara."),
                (f"Quem apresentou a {p['nome']}?", f"{E(_aut_txt(p, 5))}. A proposição foi apresentada em {dbr}."),
                (f"Sobre o que trata a {p['nome']}?", E(p["e"])),
                (f"Quando a {p['nome']} foi apresentada e há quanto tempo tramita?", f"Foi apresentada em {dbr}, no ano {p['a']}."),
                (f"A {p['nome']} já foi votada no plenário?", (f"Sim, houve {len(vl)} votação(ões) nominal(is) no plenário da Câmara desde 2023, com links nesta página." if vl else "Não há votação nominal de plenário compilada pelo Estrato desde 2023. Votações simbólicas não têm voto individual registrado.")),
                ("Onde conferir a tramitação completa?", "Na ficha de tramitação da Câmara dos Deputados, com link nesta página.")]
        ld = {"@type": "Legislation", "name": f"{tn} {p['n']}/{p['a']}", "description": _curto(p["e"], 300), "legislationType": tn, "legislationIdentifier": f"{p['t']} {p['n']}/{p['a']}", "datePublished": p["d"], "inLanguage": "pt-BR",
              "url": S.BASE + p["url"], "legislationJurisdiction": "BR", "isBasedOn": f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{p['id']}"}
        S.write(p["url"], S.page(f"{p['nome']}: {_curto(p['e'], 200)}", f"{tn} {p['n']}/{p['a']}: {_curto(p['e'], 90)} Situação: {_sit(p)}. Autoria, temas, votações no plenário e ficha de tramitação.", p["url"], body, faqs=faqs,
                                 crumbs=[("Proposições", "/proposicoes/"), (tn, f"/proposicoes/tipo/{p['t'].lower()}/"), (p["nome"], p["url"])], jsonld=ld), familia=fam, lastmod=p["dst"] or p["d"])
        urls.append(p["url"])
    # ---------------- hubs por tipo ----------------
    por_tipo = collections.defaultdict(list)
    for p in P: por_tipo[p["t"]].append(p)
    def linha(p): return [data_br(p["d"]), f'<a href="{p["url"]}">{E(p["nome"])}</a>', E(_curto(p["e"], 140)), E(_sit(p))]
    for t, L in sorted(por_tipo.items()):
        tn, gsl, expl = TIPOS.get(t, (L[0]["tn"], "", "")); tn = tn or L[0]["tn"]; u = f"/proposicoes/tipo/{t.lower()}/"; L = sorted(L, key=lambda p: (p["d"], p["id"]), reverse=True)
        sit = collections.Counter(_sit(p) for p in L).most_common(4); porano = collections.Counter(p["a"] for p in L)
        votadas = sum(1 for p in L if p["id"] in por_vot); norma = sum(1 for p in L if "norma jur" in p["sit"].lower())
        body = (f'<section class="blk"><h1>{E(tn)} ({t}) na Câmara: proposições relevantes</h1><p class="snippet">O Estrato acompanha <strong>{num(len(L))} {E(tn.lower())}</strong> ({t}) de maior alcance na Câmara dos Deputados, '
                f'{votadas} delas com votação nominal no plenário e {norma} transformadas em norma jurídica. {E(expl)}</p>'
                + S.table(["Apresentada em", "Proposição", "Ementa", "Situação"], [linha(p) for p in L[:1000]], f"{t}: da mais recente para a mais antiga" + (f" (1.000 de {num(len(L))})" if len(L) > 1000 else ""))
                + "<h2>Distribuição por ano de apresentação</h2>" + S.table(["Ano", "Proposições na seleção"], [[str(a), str(n)] for a, n in sorted(porano.items(), reverse=True)])
                + f'<p>Veja os <a href="/proposicoes/">demais tipos</a>, os <a href="/proposicoes/tema/">temas</a> e a <a href="/proposicoes/metodologia/">metodologia da seleção</a>.</p><p class="src">Fonte: arquivos em lote da Câmara. Compilação de {data_br(col)}.</p></section>')
        faqs = [(f"Quantas {tn.lower()}s o Estrato acompanha?", f"{num(len(L))} proposições do tipo {t} apresentadas desde 2023 ou votadas no plenário desde 2023, segundo a compilação de {data_br(col)}."),
                (f"Como tramita uma {tn.lower()}?", E(expl) or "Segue o rito do Regimento Interno da Câmara."), (f"Quantas {t} tiveram votação nominal?", f"{votadas} das {num(len(L))} têm ao menos uma votação nominal de plenário compilada."),
                (f"Quantas {t} viraram norma jurídica?", f"{norma} estão com a situação “Transformado em Norma Jurídica”."), (f"Qual é a situação mais comum?", ", ".join(f"{E(s)} ({n})" for s, n in sit) + "."),
                ("Por que nem toda proposição está na lista?", "O Estrato seleciona as de maior alcance: PEC, medidas provisórias, projetos de conversão, projetos em urgência, aprovados ou votados nominalmente. A seleção está descrita na metodologia.")]
        S.write(u, S.page(f"{tn} ({t}) na Câmara: lista e situação | {S.CFG['site_name']}", f"{num(len(L))} proposições do tipo {t.upper()} no recorte relevante da Câmara desde 2023, com ementa, situação e votações, da mais recente à mais antiga.", u, body, faqs=faqs,
                          crumbs=[("Proposições", "/proposicoes/"), (t, u)], jsonld=S.itemlist([(p["nome"], p["url"]) for p in L[:50]])), familia="paginas", lastmod=col)
        urls.append(u)
    # ---------------- temas: hub, tema, tema x ano ----------------
    tot = D["total"]; tema_ano = collections.defaultdict(lambda: collections.Counter())
    for t, c in D["temas"].items():
        for k, n in c.items():
            a, s = k.split("|"); tema_ano[t][(int(a), s)] += n
    top_tipos = ["PL", "PLP", "PEC", "PDL", "REQ"]
    rows = []
    for t in temas:
        row = [f'<a href="/proposicoes/tema/{tslug[t]}/">{E(t)}</a>']
        for a in anos: row.append(num(sum(n for (aa, s), n in tema_ano[t].items() if aa == a)))
        rows.append(row)
    body = (f'<section class="blk"><h1>Proposições por tema legislativo</h1><p class="snippet">A Câmara classifica cada proposição em um ou mais dos <strong>{len(temas)} temas legislativos</strong>. A tabela traz, em ordem alfabética, quantas proposições '
            f'de cada tema foram apresentadas por ano desde {anos[0]}, somando todos os tipos (projetos de lei, requerimentos, emendas e outros).</p>'
            + S.table(["Tema"] + [str(a) for a in anos], rows, "Proposições apresentadas por tema e ano de apresentação (ordem alfabética)")
            + '<h2>Como ler a tabela</h2><p>Um mesmo texto pode ter mais de um tema, então a soma das linhas é maior que o total de proposições. A contagem inclui todos os tipos de proposição; as páginas de cada tema listam apenas as de maior alcance. '
              'Em 2026 a contagem é parcial, porque o ano não terminou.</p>'
            f'<p>Veja também os <a href="/proposicoes/">tipos de proposição</a> e a <a href="/proposicoes/metodologia/">metodologia</a>.</p><p class="src">Fonte: arquivos em lote da Câmara (proposicoesTemas). Compilação de {data_br(col)}.</p></section>')
    faqs = [("O que são os temas legislativos da Câmara?", f"Uma classificação oficial por assunto, com {len(temas)} temas, usada para organizar as proposições, como Saúde, Economia e Educação."),
            ("Uma proposição pode ter mais de um tema?", "Sim. Por isso a soma da tabela é maior que o número de proposições."),
            ("Os números incluem todos os tipos de proposição?", "Sim, projetos de lei, requerimentos, emendas, pareceres e outros. As páginas de tema listam só as de maior alcance."),
            ("Por que 2026 tem menos proposições?", "O ano ainda não terminou e o arquivo da Câmara é atualizado diariamente."),
            ("Esta tabela mostra quais temas são mais importantes?", "Não. A ordem é alfabética e o número de proposições não mede a relevância de um tema."),
            ("De onde vêm os dados?", "Dos arquivos em lote de proposições e temas da API de Dados Abertos da Câmara.")]
    S.write("/proposicoes/tema/", S.page("Proposições por tema legislativo da Câmara, 2023 a 2026", f"Quantas proposições a Câmara recebeu por tema legislativo e ano desde {anos[0]}, em ordem alfabética, com acesso à lista de cada tema.", "/proposicoes/tema/", body, faqs=faqs,
                                         crumbs=[("Proposições", "/proposicoes/"), ("Temas", "/proposicoes/tema/")]), familia="paginas", lastmod=col); urls.append("/proposicoes/tema/")
    for t in temas:
        L = sorted(por_tema.get(t, []), key=lambda p: (p["d"], p["id"]), reverse=True); u = f"/proposicoes/tema/{tslug[t]}/"
        ta = tema_ano[t]; tipos_ano = sorted({s for (_, s) in ta}, key=lambda s: (-sum(n for (_, ss), n in ta.items() if ss == s), s))[:6]
        rows = [[str(a)] + [num(ta.get((a, s), 0)) for s in tipos_ano] + [num(sum(n for (aa, _), n in ta.items() if aa == a))] for a in anos]
        sel_ano = collections.Counter(p["a"] for p in L); votadas = sum(1 for p in L if p["id"] in por_vot); norma = sum(1 for p in L if "norma jur" in p["sit"].lower())
        recentes = L[:25]
        body = (f'<section class="blk"><h1>Proposições sobre {E(t)} na Câmara</h1><p class="snippet">Desde {anos[0]}, a Câmara recebeu <strong>{num(sum(ta.values()))} proposições</strong> classificadas no tema {E(t)}. '
                f'O Estrato acompanha {num(len(L))} de maior alcance (PEC, medidas provisórias, projetos em urgência, aprovados ou votados nominalmente), {votadas} com votação nominal e {norma} já transformadas em norma jurídica.</p>'
                + "<h2>Proposições apresentadas por ano e tipo</h2>" + S.table(["Ano"] + tipos_ano + ["Total"], rows, f"{t}: proposições por ano de apresentação e tipo")
                + f"<h2>Proposições relevantes mais recentes</h2>" + S.table(["Apresentada em", "Proposição", "Ementa", "Situação"], [linha(p) for p in recentes], f"{t}: as {len(recentes)} mais recentes da seleção")
                + "<h2>Lista completa por ano</h2><div class=\"chips\">" + "".join(f'<a class="chip" href="{u}{a}/">{a} ({sel_ano.get(a, 0)})</a>' for a in sorted(anos, reverse=True) if sel_ano.get(a)) + "</div>"
                + f'<p>Veja a <a href="/proposicoes/tema/">comparação entre todos os temas</a> e as <a href="/proposicoes/">proposições por tipo</a>.</p><p class="src">Fonte: arquivos em lote da Câmara. Compilação de {data_br(col)}.</p></section>')
        faqs = [(f"Quantas proposições sobre {t} a Câmara recebeu desde {anos[0]}?", f"{num(sum(ta.values()))} proposições de todos os tipos, segundo a classificação temática oficial."),
                (f"Quantas proposições de {t} o Estrato acompanha?", f"{num(len(L))} de maior alcance: PEC, medidas provisórias, projetos em urgência, aprovados ou votados nominalmente."),
                (f"Quantas proposições de {t} já viraram norma?", f"{norma} estão com a situação “Transformado em Norma Jurídica” na seleção."),
                (f"Alguma proposição de {t} teve votação nominal?", f"{votadas} tiveram ao menos uma votação nominal de plenário compilada desde 2023."),
                ("Como a Câmara define o tema de uma proposição?", "A classificação é feita pela própria Câmara; uma proposição pode ter mais de um tema."),
                ("Esta página ordena as proposições por importância?", "Não. A lista está em ordem cronológica, da mais recente para a mais antiga.")]
        S.write(u, S.page(f"Proposições sobre {t} na Câmara: PEC, projetos e MPs | {S.CFG['site_name']}", f"{num(sum(ta.values()))} proposições sobre {t} desde {anos[0]}; {num(len(L))} relevantes, com situação, autoria e votações.", u, body, faqs=faqs,
                          crumbs=[("Proposições", "/proposicoes/"), ("Temas", "/proposicoes/tema/"), (t, u)], jsonld=S.itemlist([(p["nome"], p["url"]) for p in recentes])), familia="paginas", lastmod=col); urls.append(u)
        for a in anos:
            La = [p for p in L if p["a"] == a]; ua = f"{u}{a}/"
            if not La: continue
            tp = collections.Counter(p["t"] for p in La).most_common()
            body = (f'<section class="blk"><h1>Proposições sobre {E(t)} apresentadas em {a}</h1><p class="snippet">Em {a}, o Estrato acompanha <strong>{len(La)} proposições relevantes</strong> do tema {E(t)} na Câmara: '
                    + ", ".join(f"{n} {E(s)}" for s, n in tp) + f". A Câmara recebeu, ao todo, {num(sum(n for (aa, _), n in ta.items() if aa == a))} proposições nesse tema e ano.</p>"
                    + S.table(["Apresentada em", "Proposição", "Ementa", "Situação"], [linha(p) for p in La], f"{t}, {a}: proposições relevantes em ordem cronológica inversa")
                    + f'<p>Voltar ao tema <a href="{u}">{E(t)}</a> ou ver os <a href="/proposicoes/tema/">demais temas</a>.</p><p class="src">Fonte: arquivos em lote da Câmara. Compilação de {data_br(col)}.</p></section>')
            faqs = [(f"Quantas proposições relevantes de {t} foram apresentadas em {a}?", f"{len(La)}, segundo a seleção do Estrato (PEC, MPs, projetos em urgência, aprovados ou votados)."),
                    (f"Quais tipos de proposição aparecem em {t} em {a}?", ", ".join(f"{E(s)}: {n}" for s, n in tp) + "."),
                    (f"Quantas proposições de {t} foram apresentadas em {a}, somando todos os tipos?", f"{num(sum(n for (aa, _), n in ta.items() if aa == a))}, segundo os arquivos em lote da Câmara."),
                    (f"Alguma proposição de {t} de {a} teve votação nominal?", f"{sum(1 for p in La if p['id'] in por_vot)} das {len(La)} listadas têm votação nominal de plenário compilada."),
                    ("A lista está ordenada por importância?", "Não, é cronológica, da mais recente para a mais antiga."),
                    ("O que significa a situação de cada proposição?", "É a situação registrada na última movimentação, conforme a ficha de tramitação da Câmara.")]
            S.write(ua, S.page(f"{t}: proposições apresentadas em {a} na Câmara", f"{len(La)} proposições relevantes sobre {t} apresentadas em {a}, com ementa e situação.", ua, body, faqs=faqs,
                               crumbs=[("Proposições", "/proposicoes/"), (t, u), (str(a), ua)], jsonld=S.itemlist([(p["nome"], p["url"]) for p in La[:50]])), familia=fam, lastmod=col); urls.append(ua)
    # ---------------- hub /proposicoes/ ----------------
    ult = sorted(P, key=lambda p: (p["dst"], p["id"]), reverse=True)[:15]
    tabela = [[f'<a href="/proposicoes/tipo/{t.lower()}/">{E(TIPOS.get(t, (L[0]["tn"],))[0] or L[0]["tn"])} ({t})</a>', num(len(L)), num(sum(1 for p in L if p["id"] in por_vot)), num(sum(1 for p in L if "norma jur" in p["sit"].lower()))] for t, L in sorted(por_tipo.items())]
    body = (f'<section class="blk"><h1>Proposições legislativas na Câmara: PEC, MPs, projetos de lei e mais</h1><p class="snippet">O Estrato reúne <strong>{num(len(P))} proposições de maior alcance</strong> da Câmara dos Deputados desde 2023 '
            f'(PEC, medidas provisórias, projetos de conversão, projetos em urgência, aprovados ou votados nominalmente), com autoria, temas, situação, tramitação e as votações do plenário já publicadas no site.</p>'
            + "<h2>Por tipo de proposição</h2>" + S.table(["Tipo", "Na seleção", "Com votação nominal", "Viraram norma"], tabela)
            + "<h2>Por tema legislativo</h2><p>Veja quantas proposições a Câmara recebe por tema e ano na <a href=\"/proposicoes/tema/\">comparação de temas</a>, ou entre direto em um tema:</p><div class=\"chips\">" + "".join(f'<a class="chip" href="/proposicoes/tema/{tslug[t]}/">{E(t)}</a>' for t in temas) + "</div>"
            + "<h2>Últimas movimentações</h2>" + S.table(["Última movimentação", "Proposição", "Ementa", "Situação"], [[data_br(p["dst"]), f'<a href="{p["url"]}">{E(p["nome"])}</a>', E(_curto(p["e"], 130)), E(_sit(p))] for p in ult], "As 15 proposições da seleção com movimentação mais recente")
            + '<h2>Como a seleção é feita</h2><p>Entram todas as PEC, medidas provisórias e projetos de lei de conversão; os projetos de lei e de lei complementar em regime de urgência, aprovados ou transformados em norma; e qualquer proposição com votação nominal no plenário desde 2023. '
              'As demais, como requerimentos e projetos sem tramitação, ficam de fora para manter a lista útil. Detalhes na <a href="/proposicoes/metodologia/">metodologia</a>. Veja também o <a href="/votacoes/">placar de votações</a>.</p>'
            f'<p class="src">Fonte: <a href="https://dadosabertos.camara.leg.br/" target="_blank" rel="noopener">Dados Abertos da Câmara</a>. Atualização diária; compilação de {data_br(col)}. Dados em <a href="/dados/#proposicoes">CSV</a>.</p></section>')
    faqs = [("Quantas proposições o Estrato acompanha?", f"{num(len(P))} de maior alcance, apresentadas desde 2023 ou votadas no plenário desde 2023, segundo a compilação de {data_br(col)}."),
            ("Quais proposições entram na seleção?", "PEC, medidas provisórias, projetos de conversão, projetos em urgência, aprovados ou transformados em norma e todas com votação nominal de plenário."),
            ("Como saber a situação de uma proposição?", "Cada página mostra a situação, o órgão e a data da última movimentação, com link para a ficha de tramitação oficial da Câmara."),
            ("Os projetos do Senado estão aqui?", "Não. Esta seção usa os dados da Câmara. Proposições do Senado aparecem quando chegam à Câmara."),
            ("Com que frequência os dados são atualizados?", "Uma vez por dia, a partir dos arquivos em lote oficiais da Câmara."),
            ("A lista indica quem trabalha mais ou menos?", "Não. A autoria é mostrada como informação, sem ranking de parlamentares.")]
    ld = [S.itemlist([(p["nome"], p["url"]) for p in ult]), {"@type": "Dataset", "name": "Proposições relevantes da Câmara dos Deputados (2023 a 2026)", "description": "PEC, medidas provisórias, projetos em urgência, aprovados ou votados, com autoria, temas e situação, compilados dos arquivos oficiais da Câmara.",
          "url": S.BASE + "/proposicoes/", "license": "https://creativecommons.org/licenses/by/4.0/deed.pt-br", "isAccessibleForFree": True, "creator": {"@id": S.BASE + "/#org"}, "inLanguage": "pt-BR", "isBasedOn": "https://dadosabertos.camara.leg.br/",
          "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{S.BASE}/dados/proposicoes.csv"}]}]
    S.write("/proposicoes/", S.page("Proposições na Câmara: PEC, MPs e projetos de lei desde 2023", f"{num(len(P))} proposições relevantes da Câmara: autoria, temas, situação, tramitação e votações nominais, por tipo e tema.", "/proposicoes/", body, faqs=faqs,
                                    crumbs=[("Proposições", "/proposicoes/")], jsonld=ld), familia="paginas", lastmod=col); urls.append("/proposicoes/")
    # metodologia
    body = ('<article class="post"><h1>Metodologia das proposições</h1><p class="snippet">Como o Estrato seleciona e compila as proposições da Câmara dos Deputados e o que cada campo da página significa.</p>'
            '<h2>Fonte</h2><p>Arquivos em lote de proposições, autores e temas da API de Dados Abertos da Câmara (um arquivo por ano de apresentação, de 2023 a 2026), atualizados diariamente. Proposições votadas nominalmente antes de 2023 vêm da API v2, uma a uma.</p>'
            '<h2>Seleção</h2><p>Entram todas as PEC, medidas provisórias (MPV) e projetos de lei de conversão (PLV); os projetos de lei (PL) e de lei complementar (PLP) que não estão arquivados e têm regime de urgência, foram aprovados ou transformados em norma; e qualquer proposição, de qualquer tipo, com votação nominal no plenário da Câmara desde fevereiro de 2023. '
            'Requerimentos, pareceres e projetos parados não entram, salvo se votados.</p><h2>Campos</h2><p>Situação, órgão, regime, apreciação e despacho são os do último estado de tramitação registrado pela Câmara. Autoria segue a ordem de assinatura. Temas são a classificação oficial da Câmara. '
            'A contagem por tema considera todas as proposições do ano, não só as da seleção.</p><h2>Limites</h2><p>A página não substitui a ficha de tramitação oficial, que traz o histórico completo. Autoria e coautoria não indicam relatoria ou posição de voto. '
            'Durante o período eleitoral, o Estrato não ordena nem pontua parlamentares por quantidade de proposições.</p><p>Erros podem ser comunicados pela página de <a href="/correcoes/">correções</a>.</p></article>')
    faqs = [("De onde vêm os dados das proposições?", "Dos arquivos em lote oficiais da Câmara dos Deputados."), ("Por que a lista não tem todas as proposições?", "Para manter só as de maior alcance. Há centenas de milhares de requerimentos e emendas que não entram."),
            ("O que é situação?", "A situação registrada na última movimentação, como “Pronta para Pauta” ou “Transformado em Norma Jurídica”."), ("Autoria indica quem relatou?", "Não. Relatoria é outro dado, presente na ficha de tramitação."),
            ("Há ranking de autores?", "Não. Durante o período eleitoral o Estrato não publica rankings de parlamentares."), ("Como corrigir um dado?", "Pela página de correções do Estrato; dados de origem devem ser corrigidos na Câmara.")]
    S.write("/proposicoes/metodologia/", S.page("Metodologia das proposições legislativas", "Como o Estrato seleciona e compila PEC, medidas provisórias e projetos de lei da Câmara dos Deputados.", "/proposicoes/metodologia/", body, faqs=faqs,
                                                crumbs=[("Proposições", "/proposicoes/"), ("Metodologia", "/proposicoes/metodologia/")]), familia="paginas", lastmod=col); urls.append("/proposicoes/metodologia/")
    # CSV
    out = S.OUT / "dados"; out.mkdir(parents=True, exist_ok=True)
    with (out / "proposicoes.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["id_camara", "tipo", "numero", "ano", "apresentacao", "ementa", "situacao", "ultima_movimentacao", "orgao", "regime", "temas", "autores", "url_estrato", "url_camara"])
        for p in P: w.writerow([p["id"], p["t"], p["n"], p["a"], p["d"], p["e"], p["sit"], p["dst"], p["org"], p["rg"], "|".join(p["tem"]), "|".join(a[1] for a in p["aut"]), S.BASE + p["url"], f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={p['id']}"])
    S.extra_sets = getattr(S, "extra_sets", []) + [("proposicoes", "Proposições relevantes da Câmara (2023 a 2026)", "Uma linha por proposição da seleção, com tipo, ementa, situação, temas e autores.", len(P), "Câmara dos Deputados, arquivos em lote de proposições, autores e temas",
                                                  "https://dadosabertos.camara.leg.br/", "Seleção descrita em /proposicoes/metodologia/; situação do último estado de tramitação.", col)]
    return {"urls": urls}
