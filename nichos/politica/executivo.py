"""Executivo federal desde 2023: viagens de ministros (CNE-0001), viagens agregadas por órgão e cartão de pagamento (CPGF) por órgão.

Dados: data/executivo/executivo.json.gz (tools/datasets_executivo.py), downloads em lote públicos do Portal da Transparência (sem chave).
Páginas: /executivo/ (hub), /executivo/autoridades/<slug>/, /executivo/orgaos/<slug>/, /executivo/metodologia/.
Servidores (inclusive DAS/CCE/FCE): só números agregados por órgão. CPGF: sem nome de portador; favorecidos só pessoa jurídica.
Período eleitoral: só fatos, listas em ordem alfabética, sem ranking.
"""
import collections, csv, gzip, json, re
from core.site import E, slugify
from .dados import brl, brl0, data_br, num, pct, MESES
from .emendas import tit

_C = {}
FONTE_V = '<a href="https://portaldatransparencia.gov.br/download-de-dados/viagens" target="_blank" rel="noopener">download de viagens a serviço do Portal da Transparência (CGU)</a>'
FONTE_C = '<a href="https://portaldatransparencia.gov.br/download-de-dados/cpgf" target="_blank" rel="noopener">download do Cartão de Pagamento do Governo Federal (CPGF) do Portal da Transparência</a>'


def carregar(S):
    if "d" in _C: return _C["d"]
    f = S.ROOT / "data/executivo/executivo.json.gz"
    d = json.loads(gzip.decompress(f.read_bytes())) if f.exists() else {"viagens": [], "orgaos": {}, "viag_org": {}, "cpgf": {}}
    m = S.ROOT / "data/executivo/meta.json"; meta = json.loads(m.read_text(encoding="utf-8")) if m.exists() else {}
    for v in d["viagens"]: v["valor"] = round(v["diarias"] + v["passagens"] + v["outros"] - v["devol"], 2)
    _C["d"] = (d, meta); return _C["d"]


def art(n, p="em"):
    """Preposição + artigo para nome de órgão: no Ministério, na Presidência, no Banco Central."""
    fem = n.startswith(("Presid", "Advoc", "Control", "Casa", "Secretaria", "Vice"))
    return {"em": "na" if fem else "no", "de": "da" if fem else "do"}[p] + " " + n


def _ano(v): return (v["ini"] or "0000")[:4]


def tabela_viagens(S, vs, mostrar_nome=False, limite=60):
    rows = []
    for v in sorted(vs, key=lambda x: x["ini"], reverse=True)[:limite]:
        per = data_br(v["ini"]) + (f" a {data_br(v['fim'])}" if v["fim"] and v["fim"] != v["ini"] else "")
        m = v["motivo"]; m = (m[:160].rsplit(" ", 1)[0] + "…") if len(m) > 160 else m
        rows.append(([E(tit(v["nome"]))] if mostrar_nome else []) + [per, E(v["dest"]), E(m), brl(v["valor"])])
    return S.table((["Autoridade"] if mostrar_nome else []) + ["Período", "Destino", "Motivo (como registrado)", "Valor"], rows, f"Viagens realizadas mais recentes (até {limite})")


def build(S):
    D, meta = carregar(S)
    if not D["viagens"]: return {"urls": []}
    col = (meta.get("coletado_em") or "")[:10]; fam = "executivo"; urls = []; O = D["orgaos"]
    real = [v for v in D["viagens"] if v["sit"] == "Realizada"]
    pessoas = collections.defaultdict(list)
    for v in real:
        if v["funcao"] == "CNE-0001": pessoas[v["nome"]].append(v)
    ourl = {k: f"/executivo/orgaos/{slugify(n)}/" for k, n in O.items() if k in D["cpgf"] or any(v["org"] == k for v in real)}
    purl = {n: f"/executivo/autoridades/{slugify(n)}/" for n in pessoas}
    S.exec_purl = purl
    anos = sorted({_ano(v) for v in real})
    med = {}
    for a in anos:
        por = collections.Counter(); qt = collections.Counter()
        for n, vs in pessoas.items():
            for v in vs:
                if _ano(v) == a: por[n] += v["valor"]; qt[n] += 1
        med[a] = (sum(por.values()) / len(por) if por else 0, sum(qt.values()) / len(qt) if qt else 0)
    # ---------- autoridades ----------
    for n, vs in pessoas.items():
        u = purl[n]; nome = tit(n); orgs = collections.Counter(O.get(v["org"], v["org"]) for v in vs); ks = sorted({v["org"] for v in vs})
        tot = sum(v["valor"] for v in vs); ini = min(v["ini"] for v in vs); fim = max(v["ini"] for v in vs)
        olinks = ", ".join((art(O.get(k, k)).split(" ", 1)[0] + " " + (f'<a href="{ourl[k]}">{E(O[k])}</a>' if k in ourl else E(O.get(k, k)))) for k in ks)
        lead = (f'<p class="snippet"><strong>{E(nome)}</strong>, com Cargo de Natureza Especial (CNE-0001, nível de ministro de Estado), {olinks}, tem <strong>{num(len(vs))} viagens a serviço realizadas</strong> registradas entre {data_br(ini)} e {data_br(fim)}, '
                f'somando {brl(tot)} em diárias, passagens e outros gastos, já descontadas devoluções.</p>')
        body = f'<article class="post"><h1>Viagens oficiais de {E(nome)} desde 2023</h1>{lead}'
        pa = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0])
        for v in vs: x = pa[_ano(v)]; x[0] += 1; x[1] += v["diarias"]; x[2] += v["passagens"]; x[3] += v["valor"]
        body += "<h2>Por ano</h2>" + S.table(["Ano", "Viagens", "Diárias", "Passagens", "Total", "Média das autoridades CNE (viagens / total)"],
                                             [[a, num(x[0]), brl(x[1]), brl(x[2]), brl(x[3]), f"{med[a][1]:.0f} / {brl0(med[a][0])}".replace(".", ",") if False else f"{round(med[a][1])} / {brl0(med[a][0])}"] for a, x in sorted(pa.items())], "Viagens realizadas por ano de início")
        ds = collections.Counter()
        for v in vs:
            for d_ in re.split(r",\s*", v["dest"]):
                if d_: ds[d_] += 1
        inter = sum(1 for v in vs if any("/" in d_ and not re.search(r"/[A-Z]{2}$", d_) for d_ in re.split(r",\s*", v["dest"])))
        body += f"<h2>Destinos mais frequentes</h2><p>{num(inter)} das {num(len(vs))} viagens incluíram destino no exterior.</p>" + S.table(["Destino", "Viagens"], [[E(d_), num(c)] for d_, c in ds.most_common(10)])
        body += "<h2>Viagens recentes</h2>" + tabela_viagens(S, vs)
        nr = sum(1 for v in D["viagens"] if v["nome"] == n and v["sit"] != "Realizada")
        if nr: body += f'<p>Além dessas, {num(nr)} propostas de viagem constam como “não realizada”.</p>'
        body += f'<p class="src">Fonte oficial: {FONTE_V}. Motivo e destino como registrados pelo órgão; valores não indicam irregularidade. Compilação em {data_br(col)}. Veja a <a href="/executivo/metodologia/">metodologia</a>.</p></article>'
        ua = max(pa); top = ds.most_common(1)[0] if ds else ("—", 0)
        faqs = [(f"Quantas viagens oficiais {nome} fez desde 2023?", f"{num(len(vs))} viagens a serviço realizadas, segundo o Portal da Transparência."),
                (f"Quanto custaram as viagens de {nome}?", f"{brl(tot)} em diárias, passagens e outros gastos, descontadas devoluções."),
                (f"Quantas viagens em {ua}?", f"{num(pa[ua][0])}, com custo de {brl(pa[ua][3])}. A média das autoridades com Cargo de Natureza Especial no ano foi de {round(med[ua][1])} viagens."),
                ("Qual o destino mais frequente?", f"{E(top[0])}, em {num(top[1])} viagens."),
                ("O que é Cargo de Natureza Especial (CNE)?", "É a classificação usada no sistema de viagens para ministros de Estado e autoridades de mesmo nível. O Estrato usa a função CNE-0001 registrada na fonte."),
                ("Viajar muito é irregular?", "Não. A página só reproduz os registros oficiais, sem juízo sobre eles.")]
        S.write(u, S.page(f"Viagens oficiais de {nome} desde 2023", f"{nome}: {len(vs)} viagens a serviço desde 2023, {brl0(tot)} em diárias e passagens. Por ano, destino e motivo, com dados do Portal da Transparência.", u, body, faqs=faqs,
                            crumbs=[("Executivo", "/executivo/"), (nome, u)], jsonld={"@type": "Dataset", "name": f"Viagens a serviço de {nome} (desde 2023)", "description": f"Viagens a serviço de {nome} registradas no Portal da Transparência: datas, destinos, motivos e valores.",
                            "url": S.BASE + u, "license": "https://creativecommons.org/licenses/by/4.0/deed.pt-br", "isAccessibleForFree": True, "creator": {"@id": S.BASE + "/#org"}, "inLanguage": "pt-BR", "isBasedOn": "https://portaldatransparencia.gov.br/download-de-dados/viagens",
                            "temporalCoverage": f"{ini}/{fim}", "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{S.BASE}/dados/viagens-autoridades.csv"}]}), familia=fam, lastmod=col)
        urls.append(u)
    # ---------- órgãos ----------
    for k, u in ourl.items():
        nome = O[k]; vo = D["viag_org"].get(k, {}); c = D["cpgf"].get(k)
        aut = sorted({v["nome"] for v in real if v["org"] == k and v["nome"] in purl}, key=slugify)
        tv = sum(x[1] for x in vo.values()); nv = sum(x[0] for x in vo.values())
        lead = f'<p class="snippet">Servidores e autoridades {E(art(nome, "de"))} registraram <strong>{num(nv)} propostas de viagem</strong> desde 2023, somando {brl(tv)}.'
        if c: lead += f' No cartão de pagamento do governo (CPGF), o órgão teve {brl(sum(x[1] for x in c["anos"].values()))} em transações de {meta.get("cpgf_meses", ["", ""])[0][:4]} a {meta.get("cpgf_meses", ["", ""])[-1][:4]}.'
        body = f'<article class="post"><h1>{E(nome)}: viagens e cartão corporativo desde 2023</h1>{lead}</p>'
        body += "<h2>Viagens a serviço (todos os servidores, agregado)</h2>" + S.table(["Ano", "Propostas de viagem", "Valor líquido"], [[a, num(x[0]), brl(x[1])] for a, x in sorted(vo.items())], "Inclui viagens não realizadas registradas com valor")
        if aut:
            body += f'<h2>Autoridades com Cargo de Natureza Especial (ordem alfabética)</h2><ul class="nlist">' + "".join(f'<li><a href="{purl[a]}">{E(tit(a))}</a> <small>{num(sum(1 for v in pessoas[a] if v["org"] == k))} viagens</small></li>' for a in aut) + "</ul>"
            body += "<h2>Viagens recentes das autoridades</h2>" + tabela_viagens(S, [v for v in real if v["org"] == k and v["nome"] in purl], mostrar_nome=True, limite=20)
        if c:
            ct = sum(x[1] for x in c["anos"].values())
            body += "<h2>Cartão de pagamento do governo federal (CPGF)</h2>" + S.table(["Ano", "Transações", "Valor", "Sob sigilo"], [[a, num(x[0]), brl(x[1]), brl(c["sig"].get(a, 0))] for a, x in sorted(c["anos"].items())], "Transações por ano do extrato")
            body += S.table(["Tipo de transação", "Valor", "%"], [[E(t), brl(v), pct(v, ct)] for t, v in sorted(c["tipo"].items(), key=lambda x: -x[1])])
            if c["fav"]: body += "<h3>Principais favorecidos pessoa jurídica</h3>" + S.table(["Favorecido", "Valor"], [[E(c["fav_n"].get(d_, d_)), brl(v)] for d_, v in sorted(c["fav"].items(), key=lambda x: -x[1])[:15]], "Pessoas físicas e portadores do cartão não são exibidos")
            body += "<h3>Unidades gestoras com maior uso</h3>" + S.table(["Unidade", "Valor"], [[E(tit(x)), brl(v)] for x, v in sorted(c["ug"].items(), key=lambda x: -x[1])[:10]])
        body += f'<p class="src">Fontes oficiais: {FONTE_V}' + (f" e {FONTE_C}" if c else "") + f'. Compilação em {data_br(col)}. Veja a <a href="/executivo/metodologia/">metodologia</a>.</p></article>'
        faqs = [(f"Quantas viagens a serviço {nome} registrou desde 2023?", f"{num(nv)} propostas de viagem, somando {brl(tv)}."),
                ("Quais autoridades do órgão têm viagens listadas?", (", ".join(tit(a) for a in aut[:8]) + ("." if len(aut) <= 8 else ", entre outras.")) if aut else "Nenhuma autoridade com Cargo de Natureza Especial tem viagem registrada no órgão."),
                ("Quanto o órgão gastou no cartão corporativo?", f"{brl(sum(x[1] for x in c['anos'].values()))} em transações desde 2023, das quais {brl(sum(c['sig'].values()))} sob sigilo." if c else "Não há transações do CPGF registradas para o órgão no período."),
                ("Por que há gastos sob sigilo?", "A fonte marca como protegidas por sigilo as transações cuja divulgação foi restringida pelo órgão. O Estrato só informa o total."),
                ("Os nomes dos servidores aparecem?", "Não. Viagens de servidores e uso do cartão aparecem só em totais. Apenas autoridades com Cargo de Natureza Especial têm viagens listadas.")]
        S.write(u, S.page(f"{nome}: viagens e cartão corporativo desde 2023", f"{nome}: {num(nv)} viagens a serviço e gastos com cartão corporativo desde 2023, com dados do Portal da Transparência.", u, body, faqs=faqs,
                            crumbs=[("Executivo", "/executivo/"), (nome, u)]), familia=fam, lastmod=col)
        urls.append(u)
    # ---------- hub e metodologia ----------
    rows = []
    for k in sorted(ourl, key=lambda k: slugify(O[k])):
        vo = D["viag_org"].get(k, {}); c = D["cpgf"].get(k)
        rows.append([f'<a href="{ourl[k]}">{E(O[k])}</a>', num(sum(x[0] for x in vo.values())), brl0(sum(x[1] for x in vo.values())), brl0(sum(x[1] for x in c["anos"].values())) if c else "—"])
    li = "".join(f'<li><a href="{purl[n]}">{E(tit(n))}</a> <small>{E(O.get(pessoas[n][-1]["org"], ""))}</small></li>' for n in sorted(pessoas, key=slugify))
    tv = sum(v["valor"] for vs in pessoas.values() for v in vs); nvp = sum(len(vs) for vs in pessoas.values())
    body = (f'<section class="blk"><h1>Executivo federal: viagens de ministros e cartão corporativo</h1><p class="snippet">Desde 2023, {num(len(pessoas))} autoridades com Cargo de Natureza Especial (nível de ministro de Estado) registraram <strong>{num(nvp)} viagens a serviço realizadas</strong>, somando {brl(tv)}, segundo o Portal da Transparência.</p>'
            f'<h2>Autoridades (ordem alfabética)</h2><ul class="nlist">{li}</ul>'
            '<h2>Órgãos (ordem alfabética)</h2>' + S.table(["Órgão", "Viagens (todos os servidores)", "Valor das viagens", "Cartão (CPGF)"], rows, "Desde 2023")
            + ('<p>Agendas oficiais do presidente e do vice-presidente estão em <a href="/executivo/presidencia/">Presidência e Vice-Presidência</a>.</p>' if (S.ROOT / "data/agenda/presidente.json.gz").exists() else "")
            + '<h2>Como ler</h2><p>Viagens individuais aparecem só para autoridades com Cargo de Natureza Especial. Viagens dos demais servidores e o uso do cartão corporativo aparecem só em totais por órgão. O Estrato não classifica autoridades.</p>'
            + f'<p>Baixe os dados em <a href="/dados/#viagens-autoridades">CSV</a> e veja a <a href="/executivo/metodologia/">metodologia</a>.</p><p class="src">Fontes: {FONTE_V}; {FONTE_C}.</p></section>')
    faqs = [("Quantas viagens os ministros fizeram desde 2023?", f"{num(nvp)} viagens a serviço realizadas por {num(len(pessoas))} autoridades com Cargo de Natureza Especial, somando {brl(tv)}."),
            ("De onde vêm os dados?", "Dos downloads em lote públicos de viagens e do cartão de pagamento do Portal da Transparência, sem uso de chave de API."),
            ("Por que a agenda dos ministros não aparece?", "A API do e-Agendas exige token pessoal de acesso; o Estrato usa só fontes públicas sem chave."),
            ("Os servidores aparecem pelo nome?", "Não. Servidores, inclusive em cargos em comissão, aparecem só em totais por órgão."),
            ("Há ranking de ministros?", "Não. As listas estão em ordem alfabética.")]
    S.write("/executivo/", S.page("Executivo federal: viagens de ministros e cartão corporativo desde 2023", f"{num(nvp)} viagens a serviço de {len(pessoas)} ministros e autoridades desde 2023 e gastos do cartão corporativo por órgão, com dados do Portal da Transparência.", "/executivo/", body, faqs=faqs,
                                  crumbs=[("Executivo", "/executivo/")]), familia="paginas", lastmod=col)
    urls.append("/executivo/")
    body = ('<article class="post"><h1>Metodologia: viagens e cartão do Executivo federal</h1><p class="snippet">Como o Estrato organiza as viagens a serviço e o cartão de pagamento do governo federal.</p>'
            '<h2>Fontes</h2><p>Downloads em lote públicos do Portal da Transparência (CGU): viagens a serviço por ano e Cartão de Pagamento do Governo Federal por mês. Nenhuma chave de API é usada. A coleta é diária e só baixa de novo os arquivos recentes.</p>'
            '<h2>Quem aparece pelo nome</h2><p>Só autoridades registradas com a função CNE-0001 (Cargo de Natureza Especial), nível de ministros de Estado e equivalentes, e o cargo de vice-presidente da República. Servidores, inclusive DAS, CCE e FCE, aparecem apenas em totais por órgão. O CPF, já mascarado na fonte, não é guardado.</p>'
            '<h2>Valores</h2><p>Valor de cada viagem = diárias + passagens + outros gastos − devoluções. Só viagens com situação “realizada” entram nas páginas das autoridades. A média anual considera as autoridades com ao menos uma viagem no ano.</p>'
            '<h2>Cartão de pagamento</h2><p>Totais por órgão superior e ano do extrato, por tipo de transação, unidade gestora e favorecido pessoa jurídica. Nomes de portadores e favorecidos pessoa física não são publicados. Transações marcadas como sigilosas na fonte aparecem só em total.</p>'
            '<h2>O que ficou de fora</h2><p>Agendas de ministros: a API do e-Agendas exige token pessoal. Cartão por autoridade: a fonte identifica o portador do cartão, não a autoridade que gerou a despesa.</p>'
            '<h2>Limites</h2><p>Registros oficiais, sem juízo sobre sua regularidade. Durante o período eleitoral, as listas ficam em ordem alfabética, sem ranking.</p></article>')
    faqs = [("Quem aparece pelo nome?", "Ministros e autoridades com Cargo de Natureza Especial (CNE-0001) e o vice-presidente."), ("Como é calculado o valor da viagem?", "Diárias + passagens + outros gastos − devoluções."),
            ("O cartão corporativo mostra quem gastou?", "Não. O Estrato publica só totais por órgão e favorecidos pessoa jurídica."), ("Por que não há agenda de ministros?", "A API do e-Agendas exige token pessoal."), ("Há ranking?", "Não. As listas estão em ordem alfabética.")]
    S.write("/executivo/metodologia/", S.page("Metodologia: viagens e cartão do Executivo federal", "Fontes, regras de privacidade e cálculos das páginas de viagens de ministros e cartão corporativo do Estrato.", "/executivo/metodologia/", body, faqs=faqs,
                                              crumbs=[("Executivo", "/executivo/"), ("Metodologia", "/executivo/metodologia/")]), familia="paginas", lastmod=col)
    urls.append("/executivo/metodologia/")
    out = S.OUT / "dados"; out.mkdir(parents=True, exist_ok=True); n = 0
    with (out / "viagens-autoridades.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["id_viagem", "nome", "cargo", "funcao", "orgao_superior", "orgao_solicitante", "inicio", "fim", "destinos", "motivo", "situacao", "diarias", "passagens", "outros", "devolucao", "valor_liquido"])
        for v in sorted(D["viagens"], key=lambda x: x["ini"]): w.writerow([v["id"], v["nome"], v["cargo"], v["funcao"], O.get(v["org"], v["org"]), v["sol"], v["ini"], v["fim"], v["dest"], v["motivo"], v["sit"], v["diarias"], v["passagens"], v["outros"], v["devol"], v["valor"]]); n += 1
    sets = [("viagens-autoridades", "Viagens a serviço de ministros e do vice-presidente", "Uma linha por viagem de autoridade com Cargo de Natureza Especial ou vice-presidente desde 2023.", n)]; n = 0
    with (out / "cpgf-orgaos.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["codigo_orgao_superior", "orgao_superior", "ano", "transacoes", "valor", "valor_sigiloso"])
        for k, c in sorted(D["cpgf"].items()):
            for a, x in sorted(c["anos"].items()): w.writerow([k, O.get(k, c["nome"]), a, x[0], f"{x[1]:.2f}", f'{c["sig"].get(a, 0):.2f}']); n += 1
    sets.append(("cpgf-orgaos", "Cartão de pagamento do governo federal por órgão", "Uma linha por órgão superior e ano: transações, valor e valor sob sigilo.", n))
    S.exec_sets = sets; S.exec_meta = col; S.exec_ourl = ourl
    return {"urls": urls}
