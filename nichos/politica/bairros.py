"""Bairros do Censo 2022 (IBGE, agregados por bairro): populacao, domicilios, area, sexo, faixas etarias, agua, esgoto e lixo.
Dados: data/bairros/bairros.json.gz (tools/datasets_bairros.py). So ha bairros em municipios com delimitacao oficial do IBGE (895 municipios).
Paginas: /bairros/ (hub), /bairros/<uf>/ (hub), /bairros/<uf>/<municipio>/ (hub com lista alfabetica) e /bairros/<uf>/<municipio>/<bairro>/ (familia `bairros`, noindex ate a onda propria).
Paginas com menos de 300 palavras ou muito parecidas viram noindex automaticamente (core). Sem ranking, sem cor/raca, so totais."""
import collections, csv, gzip, json
from core.site import E, slugify
from .dados import UF, PREP, data_br, num, pct
from .financas import n1, FONTE_I

SIG = {v: k for k, v in UF.items()}
FX = ["0 a 4", "5 a 9", "10 a 14", "15 a 19", "20 a 24", "25 a 29", "30 a 39", "40 a 49", "50 a 59", "60 a 69", "70 ou mais"]
FONTE = '<a href="https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Bairro_csv/" target="_blank" rel="noopener">Censo Demográfico 2022, agregados por bairro (IBGE)</a>'


def carregar(S):
    f = S.ROOT / "data/bairros/bairros.json.gz"
    return json.loads(gzip.decompress(f.read_bytes())) if f.exists() else {"b": [], "gerado": ""}


def _hbar(v, mx): return f'<span class="mbar" aria-hidden="true"><i style="width:{100 * max(v, 0) / mx if mx else 0:.0f}%;background:#1f4e79"></i></span>'
def _p(a, b): return pct(a, b) if a is not None and b else "—"


def build(S):
    D = carregar(S); B = D["b"]
    if not B or not getattr(S, "mun", None): return {"urls": []}
    m = S.mun; M, URL = m["M"], m["URL"]; col = D.get("gerado") or m["col"]; site = S.CFG["site_name"]; urls = []
    q = S.CFG.setdefault("qualidade", {}).setdefault("faq_pseo", {}); ex = q.setdefault("hubs_exatos", [])
    por_m = collections.defaultdict(list)
    for b in B:
        if b["m"] in M: por_m[b["m"]].append(b)
    por_uf = collections.defaultdict(list)
    for c in por_m: por_uf[M[c]["uf"]].append(c)
    S.bairros_ufs = set()
    for c, L in por_m.items():
        S.bairros_ufs.add(M[c]["uf"])
        L.sort(key=lambda b: (slugify(b["n"]), b["c"])); usados = set()
        for b in L:
            s = slugify(b["n"]) or b["c"][-3:]
            if s in usados: s = f"{s}-{b['c'][-3:]}"
            usados.add(s); b["s"] = s; b["nt"] = b["n"] if s == slugify(b["n"]) else f'{b["n"]} (setor {b["c"][-3:]})'
    SLM = lambda c: URL[c].rstrip("/").rsplit("/", 1)[1]
    for uf in por_uf:
        ex.append(f"/bairros/{uf.lower()}/")
        ex.extend(f"/bairros/{uf.lower()}/{SLM(c)}/" for c in por_uf[uf])
    tot_b = len(B)
    # ---------- paginas de bairro ----------
    for c, L in por_m.items():
        e = M[c]; uf = e["uf"]; mn = e["n"]; sl = SLM(c); pop_m = int(m["POP"][c])
        agg = {k: sum(b[k] or 0 for b in L) for k in ("p", "h", "f", "dm", "ag", "es", "lx", "d", "a")}
        agg_i = [sum((b["i"] or [0] * 11)[j] for b in L) for j in range(11)]
        for i, b in enumerate(L):
            u = f"/bairros/{uf.lower()}/{sl}/{b['s']}/"; p = b["p"]; nome = b["nt"]
            dens = p / b["a"] if b.get("a") else None
            body = f'<article class="post"><h1>Bairro {E(nome)}, {E(mn)} ({uf}): população, domicílios e saneamento</h1>'
            body += (f'<p class="snippet">O bairro <strong>{E(nome)}</strong>, em <a href="{URL[c]}">{E(mn)}</a> ({UF[uf]}), tinha <strong>{num(p)} moradores</strong> e <strong>{num(int(b["d"] or 0))} domicílios</strong> no Censo 2022 do IBGE'
                     + (f', em {n1(b["a"])} km², uma densidade de {n1(dens)} habitantes por km²' if dens else "") + f'. Ele concentra {pct(p, pop_m)} da população do município e {pct(p, agg["p"])} dos moradores dos {num(len(L))} bairros delimitados pelo IBGE em {E(mn)}.</p>')
            rows = [["Moradores", num(p)]]
            if b["h"] is not None and b["f"] is not None: rows += [["Homens", f'{num(int(b["h"]))} ({_p(b["h"], p)})'], ["Mulheres", f'{num(int(b["f"]))} ({_p(b["f"], p)})']]
            rows += [["Domicílios (total)", num(int(b["d"] or 0))]]
            if b.get("dp") is not None: rows.append(["Domicílios particulares", num(int(b["dp"]))])
            if b.get("dpo") is not None: rows.append(["Domicílios particulares ocupados", num(int(b["dpo"]))])
            if b.get("mm"): rows.append(["Média de moradores por domicílio ocupado", n1(b["mm"])])
            if b.get("a"): rows.append(["Área", n1(b["a"]) + " km²"])
            if dens: rows.append(["Densidade demográfica", n1(dens) + " hab./km²"])
            body += "<h2>População e domicílios</h2>" + S.table(["Indicador", "Valor"], rows, "Censo 2022, IBGE")
            if b.get("h") and b.get("f"):
                body += f'<p>Para cada 100 mulheres há {n1(100 * b["h"] / b["f"])} homens no bairro' + (f' (no conjunto dos bairros de {E(mn)}: {n1(100 * agg["h"] / agg["f"])})' if agg["f"] else "") + ".</p>"
            fa = [(f"Quantos moradores tem o bairro {nome}, em {mn}?", f"{num(p)} moradores no Censo 2022, o que equivale a {pct(p, pop_m)} da população de {mn}."), (f"Quantos domicílios há no bairro {nome}?", f"{num(int(b['d'] or 0))} domicílios, dos quais {num(int(b['dpo']))} particulares ocupados." if b.get("dpo") is not None else f"{num(int(b['d'] or 0))} domicílios.")]
            if b["i"]:
                i_ = b["i"]; tot = sum(i_) or 1; jov = sum(i_[:3]); idos = sum(i_[9:]); mx = max(i_)
                body += ("<h2>Moradores por faixa etária</h2>" + S.table(["Faixa etária (anos)", "Moradores", "%", ""], [[FX[j], num(int(v)), pct(v, tot), _hbar(v, mx)] for j, v in enumerate(i_)], "Censo 2022") +
                         f'<p>Crianças e adolescentes de 0 a 14 anos somam {pct(jov, tot)} dos moradores e pessoas com 60 anos ou mais, {pct(idos, tot)}. A faixa com mais moradores é a de {FX[i_.index(mx)]} anos. '
                         + (f'No conjunto dos bairros de {E(mn)}, as proporções são de {pct(sum(agg_i[:3]), sum(agg_i))} e {pct(sum(agg_i[9:]), sum(agg_i))}.' if sum(agg_i) else "") + "</p>")
                fa.append((f"Qual a faixa etária predominante no bairro {nome}?", f"{FX[i_.index(mx)]} anos, com {pct(mx, tot)} dos moradores."))
            if b.get("dm") and b.get("ag") is not None:
                s_ = [["Abastecimento de água por rede geral", _p(b["ag"], b["dm"]), _p(agg["ag"], agg["dm"])]]
                if b.get("es") is not None: s_.append(["Esgoto ligado à rede geral, pluvial ou fossa ligada à rede", _p(b["es"], b["dm"]), _p(agg["es"], agg["dm"])])
                if b.get("lx") is not None: s_.append(["Lixo coletado por serviço de limpeza (direto ou em caçamba)", _p(b["lx"], b["dm"]), _p(agg["lx"], agg["dm"])])
                body += (f"<h2>Água, esgoto e lixo</h2><p>Entre os {num(int(b['dm']))} domicílios particulares permanentes ocupados do bairro, o Censo 2022 registrou:</p>" + S.table(["Serviço", f"Bairro {nome}", f"Bairros de {mn} (conjunto)"], s_, "Percentual dos domicílios particulares permanentes ocupados"))
                fa.append((f"Há esgoto e água encanada no bairro {nome}?", f"Segundo o Censo 2022, {_p(b['ag'], b['dm'])} dos domicílios usam rede geral de água" + (f" e {_p(b['es'], b['dm'])} têm esgoto ligado à rede" if b.get("es") is not None else "") + "."))
            fa.append(("De onde vêm os dados do bairro?", "Dos agregados por bairro do Censo Demográfico 2022, publicados pelo IBGE. Os limites seguem a delimitação do IBGE e podem diferir da divisão oficial da prefeitura."))
            vz = L[max(0, i - 4):i] + L[i + 1:i + 5]
            body += (f'<h2>Outros bairros de {E(mn)}</h2><p>Na ordem alfabética: ' + ", ".join(f'<a href="/bairros/{uf.lower()}/{sl}/{x["s"]}/">{E(x["nt"])}</a>' for x in vz) + f'. Veja todos os <a href="/bairros/{uf.lower()}/{sl}/">{num(len(L))} bairros de {E(mn)}</a>.</p>'
                     f'<h2>Sobre o município</h2><p><a href="{URL[c]}">{E(mn)}: receitas, despesas e indicadores</a> · <a href="/prefeitura/{uf.lower()}/{sl}/">Prefeitura de {E(mn)}</a> · <a href="/eleitorado/{uf.lower()}/{sl}/">eleitorado e locais de votação</a> · <a href="/representantes/{uf.lower()}/{sl}/">quem representa {E(mn)} no Congresso</a>.</p>'
                     f'<p class="src">Fonte oficial: {FONTE}. Compilação em {data_br(col)}. Totais por bairro, sem dados individuais. <a href="/bairros/metodologia/">Metodologia</a>.</p></article>')
            ld = {"@type": "Place", "name": f"{nome}, {mn}", "url": S.BASE + u, "containedInPlace": {"@type": "City", "name": mn, "url": S.BASE + URL[c]}, "address": {"@type": "PostalAddress", "addressLocality": mn, "addressRegion": uf, "addressCountry": "BR"}}
            S.write(u, S.page(f"Bairro {nome}, {mn} ({uf}): população e saneamento | {site}", f"Bairro {nome} em {mn} ({uf}): {num(p)} moradores, domicílios, faixas etárias, água, esgoto e lixo no Censo 2022 do IBGE.", u, body, faqs=fa,
                              crumbs=[("Bairros", "/bairros/"), (UF[uf], f"/bairros/{uf.lower()}/"), (mn, f"/bairros/{uf.lower()}/{sl}/"), (nome, u)], jsonld=ld), familia="bairros", lastmod=col); urls.append(u)
    # ---------- hubs por municipio ----------
    for c, L in por_m.items():
        e = M[c]; uf = e["uf"]; mn = e["n"]; sl = SLM(c); u = f"/bairros/{uf.lower()}/{sl}/"; pop_m = int(m["POP"][c]); tp = sum(b["p"] for b in L)
        rows = [[f'<a href="{u}{b["s"]}/">{E(b["nt"])}</a>', num(b["p"]), num(int(b["d"] or 0)), n1(b["p"] / b["a"]) if b.get("a") else "—"] for b in L]
        body = (f'<section class="blk"><h1>Bairros de {E(mn)} ({uf}): população e domicílios do Censo 2022</h1><p class="snippet">O IBGE delimitou <strong>{num(len(L))} bairros</strong> em <a href="{URL[c]}">{E(mn)}</a>, que somam {num(tp)} moradores, ou {pct(tp, pop_m)} da população do município no Censo 2022.</p>'
                + S.table(["Bairro", "Moradores", "Domicílios", "Densidade (hab./km²)"], rows, "Em ordem alfabética; não é ranking") +
                f'<p>Veja também a <a href="/prefeitura/{uf.lower()}/{sl}/">Prefeitura de {E(mn)}</a>, as <a href="/verbas-federais/{uf.lower()}/{sl}/">emendas e verbas federais</a> e os <a href="/bairros/{uf.lower()}/">bairros {PREP[uf]} {E(UF[uf])}</a>.</p>'
                f'<p class="src">Fonte oficial: {FONTE}. Compilação em {data_br(col)}.</p></section>')
        maxb = max(L, key=lambda b: b["p"])
        fa = [(f"Quantos bairros tem {mn}?", f"O IBGE delimitou {num(len(L))} bairros em {mn} para o Censo 2022."), (f"Quantos moradores vivem nos bairros de {mn}?", f"{num(tp)}, ou {pct(tp, pop_m)} da população do município."), ("A lista é um ranking?", "Não. Os bairros estão em ordem alfabética."),
              (f"Qual o bairro mais populoso de {mn}?", f"{E(maxb['n'])}, com {num(maxb['p'])} moradores no Censo 2022. A informação é descritiva e não classifica bairros."), ("De onde vêm os dados?", "Dos agregados por bairro do Censo 2022 do IBGE."), ("Os limites coincidem com os da prefeitura?", "Nem sempre: seguem a delimitação do IBGE para o Censo.")]
        S.write(u, S.page(f"Bairros de {mn} ({uf}): moradores e domicílios no Censo 2022 | {site}", f"Lista dos {num(len(L))} bairros de {mn} ({uf}) com moradores, domicílios e densidade do Censo 2022 do IBGE.", u, body, faqs=fa, crumbs=[("Bairros", "/bairros/"), (UF[uf], f"/bairros/{uf.lower()}/"), (mn, u)],
                          jsonld={"@type": "ItemList", "name": f"Bairros de {mn}", "itemListElement": [{"@type": "ListItem", "position": k + 1, "url": S.BASE + u + b["s"] + "/", "name": b["n"]} for k, b in enumerate(L[:50])]}), familia="paginas", lastmod=col); urls.append(u)
    # ---------- hubs por UF ----------
    for uf, Cs in por_uf.items():
        Cs.sort(key=lambda c: (slugify(M[c]["n"]), c)); u = f"/bairros/{uf.lower()}/"; nb = sum(len(por_m[c]) for c in Cs)
        rows = [[f'<a href="{u}{SLM(c)}/">{E(M[c]["n"])}</a>', num(len(por_m[c])), num(sum(b["p"] for b in por_m[c]))] for c in Cs]
        body = (f'<section class="blk"><h1>Bairros {PREP[uf]} {E(UF[uf])}: {num(nb)} bairros do Censo 2022</h1><p class="snippet">O IBGE delimitou <strong>{num(nb)} bairros</strong> em <strong>{num(len(Cs))} municípios</strong> {PREP[uf]} {E(UF[uf])}. Escolha o município para ver os bairros, com moradores, domicílios, faixas etárias e saneamento.</p>'
                + S.table(["Município", "Bairros", "Moradores nos bairros"], rows, "Em ordem alfabética") + f'<p>Para todos os municípios {PREP[uf]} {E(UF[uf])}, inclusive os sem bairros delimitados, veja <a href="/municipios/{uf.lower()}/">municípios {PREP[uf]} {E(UF[uf])}</a>.</p><p class="src">Fonte oficial: {FONTE}. Compilação em {data_br(col)}.</p></section>')
        fa = [(f"Quantos bairros {PREP[uf]} {UF[uf]} estão no Estrato?", f"{num(nb)} bairros de {num(len(Cs))} municípios."), ("Por que nem todo município tem bairros?", "O IBGE só delimitou bairros onde a prefeitura enviou limites oficiais para o Censo 2022; os demais têm apenas dados do município."), ("A lista é um ranking?", "Não, é alfabética."),
              ("De onde vêm os dados?", "Dos agregados por bairro do Censo 2022."), ("O que mostra a página de um bairro?", "Moradores, domicílios, área, faixas etárias e percentual de domicílios com água, esgoto e coleta de lixo."), ("Os dados são individuais?", "Não, só totais por bairro.")]
        S.write(u, S.page(f"Bairros {PREP[uf]} {UF[uf]}: municípios e moradores no Censo 2022 | {site}", f"{num(nb)} bairros de {num(len(Cs))} municípios {PREP[uf]} {UF[uf]} com moradores, domicílios e saneamento do Censo 2022 do IBGE.", u, body, faqs=fa, crumbs=[("Bairros", "/bairros/"), (UF[uf], u)]), familia="paginas", lastmod=col); urls.append(u)
    # ---------- hub nacional e metodologia ----------
    rows = [[f'<a href="/bairros/{uf.lower()}/">{UF[uf]}</a>', num(len(por_uf[uf])), num(sum(len(por_m[c]) for c in por_uf[uf]))] for uf in sorted(por_uf, key=lambda k: slugify(UF[k]))]
    body = (f'<section class="blk"><h1>Bairros do Brasil: população, domicílios e saneamento no Censo 2022</h1><p class="snippet">Uma página para cada um dos <strong>{num(tot_b)} bairros</strong> de <strong>{num(len(por_m))} municípios</strong> com limites oficiais no Censo 2022 do IBGE: moradores, domicílios, faixas etárias, água, esgoto e coleta de lixo.</p>'
            + S.table(["Estado", "Municípios com bairros", "Bairros"], rows, "Em ordem alfabética") + f'<p class="src">Fonte oficial: {FONTE}. Compilação em {data_br(col)}. Veja a <a href="/bairros/metodologia/">metodologia</a>.</p></section>')
    fa = [("Que bairros estão no Estrato?", f"Os {num(tot_b)} bairros delimitados pelo IBGE no Censo 2022, em {num(len(por_m))} municípios."), ("Por que não há bairros de todos os municípios?", "O IBGE só publica agregados por bairro onde há limites oficiais; nos demais, só o município."), ("Os dados são do Censo 2022?", "Sim, dos agregados por bairro publicados pelo IBGE."),
          ("Os limites são os da prefeitura?", "Nem sempre. Seguem a delimitação usada pelo IBGE no Censo."), ("Há ranking de bairros?", "Não, as listas são alfabéticas."), ("Posso baixar os dados?", "Sim, em /dados/bairros-censo-2022.csv.")]
    S.write("/bairros/", S.page(f"Bairros do Brasil: população e saneamento, Censo 2022 | {site}", f"{num(tot_b)} bairros de {num(len(por_m))} municípios com moradores, domicílios, faixas etárias, água, esgoto e lixo do Censo 2022 do IBGE.", "/bairros/", body, faqs=fa, crumbs=[("Bairros", "/bairros/")]), familia="paginas", lastmod=col); urls.append("/bairros/")
    body = ('<section class="blk"><h1>Metodologia: páginas de bairros</h1><p class="snippet">Como o Estrato usa os agregados por bairro do Censo 2022: fonte, indicadores, limites e critérios de indexação.</p>'
            f'<h2>Fonte</h2><p>{FONTE}. Arquivos básico, demografia, características do domicílio parte 1 e parte 2.</p><h2>Indicadores</h2><ul><li><strong>Moradores</strong>: total de pessoas residentes (V0001).</li><li><strong>Domicílios</strong>: particulares e coletivos; ocupados são os particulares com morador.</li>'
            '<li><strong>Água, esgoto e lixo</strong>: percentual dos domicílios particulares permanentes ocupados com abastecimento por rede geral; esgoto por rede geral, pluvial ou fossa ligada à rede; e lixo coletado por serviço de limpeza, direto ou em caçamba.</li><li><strong>Faixas etárias</strong>: agrupamentos do próprio IBGE.</li></ul>'
            '<h2>Limites</h2><p>Há bairros apenas em municípios com limites oficiais enviados ao IBGE. Os limites podem diferir da divisão administrativa da prefeitura, e bairros com nomes iguais no mesmo município são distinguidos pelo código. O Estrato não usa cor ou raça nem dados individuais.</p>'
            '<h2>Indexação</h2><p>Páginas de bairro com pouco texto próprio ou muito parecidas com outras ficam fora do índice de busca; as listas por município e estado são indexáveis. Veja a <a href="/municipios/metodologia/">metodologia de finanças municipais</a>.</p></section>')
    fa = [("Por que o bairro tem esses limites?", "Porque seguem a delimitação usada pelo IBGE no Censo 2022."), ("Os percentuais incluem todos os domicílios?", "Só os particulares permanentes ocupados."), ("O que é esgoto ligado à rede?", "Rede geral ou pluvial e fossa séptica ligada à rede."), ("Os dados são atualizados?", "Os agregados do Censo são fixos; o Estrato reprocessa se o IBGE republicar."), ("Há dados individuais?", "Não."), ("Como corrigir um dado?", 'Pela página de <a href="/correcoes/">correções</a>; a fonte primária é o IBGE.')]
    S.write("/bairros/metodologia/", S.page(f"Metodologia: páginas de bairros do Censo 2022 | {site}", "Fonte, indicadores, limites e critérios de indexação das páginas de bairros do Estrato, com base nos agregados do Censo 2022.", "/bairros/metodologia/", body, faqs=fa, crumbs=[("Bairros", "/bairros/"), ("Metodologia", "/bairros/metodologia/")]), familia="paginas", lastmod=col); urls.append("/bairros/metodologia/")
    # ---------- CSV ----------
    out = S.OUT / "dados"; out.mkdir(parents=True, exist_ok=True)
    with (out / "bairros-censo-2022.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["codigo_bairro", "bairro", "codigo_municipio", "municipio", "uf", "moradores", "domicilios", "domicilios_particulares_ocupados", "area_km2", "agua_rede_geral", "esgoto_rede", "lixo_coletado"])
        for b in B:
            if b["m"] in M: w.writerow([b["c"], b["n"], b["m"], M[b["m"]]["n"], M[b["m"]]["uf"], b["p"], int(b["d"] or 0), int(b["dpo"]) if b.get("dpo") is not None else "", b.get("a") or "", int(b["ag"]) if b.get("ag") is not None else "", int(b["es"]) if b.get("es") is not None else "", int(b["lx"]) if b.get("lx") is not None else ""])
    S.extra_sets = getattr(S, "extra_sets", []) + [("bairros-censo-2022", "Bairros do Censo 2022", "Uma linha por bairro delimitado pelo IBGE: moradores, domicílios, área e domicílios com água, esgoto e lixo coletado.", tot_b, "IBGE, Censo Demográfico 2022", "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Bairro_csv/", "Agregados por bairro; contagens de domicílios particulares permanentes ocupados.", col)]
    return {"urls": urls}
