"""/quem-e-quem/: ministros do STF (cms.stf.jus.br), ministros de Estado (gov.br/planalto), líderes partidários na Câmara
(API da Câmara, data/partidos.json) e presidentes de comissões da Câmara (API da Câmara, órgãos de cada deputado).
Dados oficiais coletados por tools/datasets_quem.py; sameAs para Wikidata (STF) e páginas oficiais. Listas em ordem alfabética."""
import json, re
from core.site import E, slugify
from .dados import data_br, num, UF

# posse no STF, conforme a composição do portal do STF (portal.stf.jus.br/ostf); Wikidata para sameAs
STF = {"Edson Fachin": ("2015-06-16", "Q10320705"), "Gilmar Mendes": ("2002-06-20", "Q2362405"), "Cármen Lúcia": ("2006-06-21", "Q83019"), "Dias Toffoli": ("2009-10-23", "Q10266077"),
       "Luiz Fux": ("2011-03-03", "Q3624733"), "Alexandre de Moraes": ("2017-03-22", "Q22294946"), "Nunes Marques": ("2020-11-05", "Q99831978"), "André Mendonça": ("2021-12-16", "Q60396070"),
       "Cristiano Zanin": ("2023-08-03", "Q85870824"), "Flávio Dino": ("2024-02-22", "Q10283063")}

def build(S):
    f = S.ROOT / "data/quem_e_quem.json"
    if not f.exists(): return {"urls": []}
    Q = json.loads(f.read_text(encoding="utf-8")); urls = []; deps, sens = S.parl["deps"], S.parl["sens"]
    P = json.loads((S.ROOT / "data/partidos.json").read_text(encoding="utf-8")); cd = json.loads((S.ROOT / "data/deputados.json").read_text(encoding="utf-8"))["coletado_em"][:10]
    dn = {slugify(d["nome"]): d for d in deps}
    def fonte(k): x = Q[k]; return f'<a href="{x["fonte"]}" target="_blank" rel="noopener">{"STF, Composição atual" if k == "stf" else "Planalto, Ministros e Ministras"}</a> (atualizada pela fonte em {E(x.get("atualizado_fonte") or "data não informada")}; coleta em {data_br(x["coletado_em"][:10])})'
    pages = {}
    # STF
    st = Q.get("stf", {}).get("itens", [])
    st_sorted = sorted(st, key=lambda x: STF.get(x["nome"], ("9999",))[0])
    rows = [[E(x["tratamento"] + " " + x["nome"]), E(x["funcao"] or "—"), data_br(STF[x["nome"]][0]) if x["nome"] in STF else "—"] for x in st_sorted]
    pessoas = [{"@type": "Person", "name": x["nome"], "jobTitle": f'{x["tratamento"]} do Supremo Tribunal Federal' + (f' ({x["funcao"]})' if x["funcao"] else ""), "worksFor": {"@type": "GovernmentOrganization", "name": "Supremo Tribunal Federal", "url": "https://portal.stf.jus.br/"},
                **({"sameAs": [f"https://www.wikidata.org/wiki/{STF[x['nome']][1]}"]} if x["nome"] in STF else {})} for x in st_sorted]
    pres = next((x["nome"] for x in st if x["funcao"] == "Presidente"), ""); dec = next((x["nome"] for x in st if x["funcao"] == "Decano"), "")
    b = (f'<article class="post"><h1>Ministros do STF: composição atual</h1><p class="snippet">O Supremo Tribunal Federal tem {num(len(st))} ministros em exercício na composição oficial publicada pelo tribunal, das 11 cadeiras previstas na Constituição. '
         f'{"Preside o tribunal " + E(pres) + "; o decano é " + E(dec) + "." if pres and dec else ""}</p>'
         + S.table(["Ministro(a)", "Função", "Posse no STF"], rows, "Em ordem de antiguidade no tribunal")
         + '<h2>Como o tribunal é composto</h2><p>Pela Constituição (art. 101), o STF tem 11 ministros, escolhidos entre brasileiros natos com mais de 35 e menos de 70 anos, de notável saber jurídico e reputação ilibada. O presidente da República indica o nome, que passa por sabatina na Comissão de Constituição e Justiça do Senado e precisa da aprovação da maioria absoluta dos senadores. Não há mandato fixo: o ministro fica no cargo até a aposentadoria, compulsória aos 75 anos, ou até deixar o tribunal por outro motivo. A presidência é ocupada em rodízio por dois anos, e o decano é o integrante com mais tempo de tribunal.</p>'
         + '<h2>Como as decisões são tomadas</h2><p>O tribunal julga em plenário, com todos os ministros, e em duas turmas. Boa parte dos casos é decidida no plenário virtual, em que os votos são registrados por sistema eletrônico durante um período definido. Decisões individuais do relator podem ser levadas ao colegiado por recurso.</p>'
         + f'<p class="src">Fonte oficial: {fonte("stf")}. Datas de posse: portal do STF. Identificadores: Wikidata.</p>'
         + '<p>Entenda: <a href="/glossario/stf/">STF</a> · <a href="/explica/como-o-stf-julga/">como o STF julga</a> · <a href="/explica/como-funciona-a-sabatina/">como funciona a sabatina</a> · <a href="/justica/stf/">notícias do STF</a></p></article>')
    pages["/quem-e-quem/stf/"] = ("Ministros do STF: composição atual", f"Os {len(st)} ministros em exercício no STF, com função e data de posse, pela composição oficial do tribunal.", b,
        [("Quantos ministros tem o STF hoje?", f"{num(len(st))} em exercício, segundo a composição oficial publicada pelo STF; a Constituição prevê 11."),
         ("Quem preside o STF?", E(pres) or "Ver fonte oficial."), ("Quem é o decano?", (E(dec) + ", o ministro há mais tempo no tribunal.") if dec else "Ver fonte oficial."),
         ("Como um ministro chega ao STF?", 'Indicado pelo presidente da República e aprovado pela maioria absoluta do Senado após sabatina. Veja <a href="/explica/como-funciona-a-sabatina/">como funciona a sabatina</a>.'),
         ("De onde vêm os dados?", "Da página oficial de composição do STF, coletada automaticamente.")], pessoas)
    # ministros
    mi = Q.get("ministros", {}).get("itens", [])
    rows = []
    for x in sorted(mi, key=lambda x: x["cargo"]):
        c = x["cargo"]; resto = c.split(" de Estado ", 1)[1] if " de Estado " in c else ""
        mint = resto and not resto.startswith(("Chefe", "da Casa", "da Secretaria"))
        pasta = ("Ministério " + resto) if mint else (re.sub(r"^(Chefe do |da |do )", "", resto) if resto else c)
        cand = [f"/executivo/orgaos/{slugify('Ministério ' + resto)}/"] if resto and not resto.startswith(("Chefe", "da Casa", "da Secretaria")) else [f"/executivo/orgaos/{slugify(c)}/"]
        lk_ = next((u for u in cand if u in S.urls), None)
        rows.append([f'<a href="{lk_}">{E(pasta)}</a>' if lk_ else E(pasta), E(x["nome"])])
    b = (f'<article class="post"><h1>Ministros de Estado do governo federal</h1><p class="snippet">O governo federal tem {num(len(mi))} titulares com status de ministro na lista oficial do Planalto, entre ministérios, secretarias da Presidência, Advocacia-Geral da União e Controladoria-Geral da União.</p>'
         + S.table(["Pasta", "Titular"], rows, "Em ordem alfabética do cargo") + f'<p class="src">Fonte oficial: {fonte("ministros")}. Base legal da estrutura: Lei nº 14.600/2023, arts. 17 e 18.</p>'
         + '<p>Veja também: <a href="/executivo/">viagens e cartão corporativo por órgão</a> · <a href="/glossario/ministro-de-estado/">o que é ministro de Estado</a> · <a href="/governo/ministerios/">notícias dos ministérios</a></p></article>')
    pages["/quem-e-quem/ministros/"] = ("Ministros de Estado: quem são", f"Os {len(mi)} ministros de Estado na lista oficial do Planalto, por pasta.", b,
        [("Quantos ministros tem o governo?", f"{num(len(mi))} titulares com status de ministro na lista oficial do Planalto."), ("Quem nomeia os ministros?", "O presidente da República, livremente."),
         ("Qual lei organiza os ministérios?", "A Lei nº 14.600/2023, que lista os ministérios no art. 17 e os cargos com status de ministro no art. 18."),
         ("A lista é atualizada?", f"Sim, a cada coleta da página oficial; a fonte informa atualização em {E(Q['ministros'].get('atualizado_fonte') or '—')}."),
         ("Onde ver os gastos de cada ministério?", 'Em <a href="/executivo/">viagens e cartão corporativo do Executivo</a>.')], [{"@type": "Person", "name": x["nome"], "jobTitle": x["cargo"], "worksFor": {"@type": "GovernmentOrganization", "name": "Governo Federal"}} for x in mi])
    # líderes
    ld = sorted((p for p in P["partidos"] if p.get("lider")), key=lambda p: p["sigla"])
    def lk(n): d = dn.get(slugify(n)); return f'<a href="{d["url"]}">{E(n)}</a>' if d else E(n)
    bc = {}
    for d in deps: bc[d["partido"]] = bc.get(d["partido"], 0) + 1
    b = (f'<article class="post"><h1>Líderes partidários na Câmara dos Deputados</h1><p class="snippet">{num(len(ld))} partidos têm líder registrado na API de dados abertos da Câmara dos Deputados. O líder orienta a bancada nas votações e representa o partido no Colégio de Líderes.</p>'
         + S.table(["Partido", "Líder", "UF", "Deputados em exercício"], [[f'<a href="/partidos/{slugify(p["sigla"])}/">{E(p["sigla"])}</a>' if f'/partidos/{slugify(p["sigla"])}/' in S.urls else E(p["sigla"]), lk(p["lider"]), E(p.get("lider_uf") or ""), num(bc.get(p["sigla"], 0))] for p in ld], "Em ordem alfabética do partido")
         + f'<p class="src">Fonte oficial: <a href="https://dadosabertos.camara.leg.br/" target="_blank" rel="noopener">Câmara dos Deputados, API Dados Abertos</a> (partidos), coleta em {data_br(json.loads((S.ROOT / "data/partidos.json").read_text(encoding="utf-8"))["coletado_em"][:10])}.</p>'
         + '<h2>O papel do líder</h2><p>Cada partido ou bloco indica seu líder à Mesa da Câmara. O líder fala em nome da bancada no plenário, orienta o voto nas votações nominais, indica os integrantes do partido nas comissões e participa do Colégio de Líderes, que negocia a pauta com o presidente da Câmara. A orientação de cada liderança aparece no placar de cada votação do Estrato, ao lado do voto individual dos deputados.</p>'
         + '<p>Entenda: <a href="/glossario/colegio-de-lideres/">Colégio de Líderes</a> · <a href="/partidos/">partidos</a></p></article>')
    pages["/quem-e-quem/lideres/"] = ("Líderes partidários na Câmara", f"Os líderes de {len(ld)} partidos na Câmara dos Deputados, pela API oficial.", b,
        [("O que faz um líder partidário?", "Orienta o voto da bancada, indica membros de comissões e representa o partido no Colégio de Líderes."), ("Quantos partidos têm líder?", f"{num(len(ld))} na última coleta."),
         ("De onde vêm os dados?", "Da API de dados abertos da Câmara dos Deputados."), ("A lista tem ranking?", "Não. Está em ordem alfabética do partido."), ("Onde ver a bancada de cada partido?", 'Na página de <a href="/partidos/">partidos</a>.')], [])
    # presidentes de comissões
    pc = sorted(((o, d) for d in deps for o in d["orgaos"] if o.get("cargo") == "Presidente"), key=lambda x: x[0]["nome"])
    b = (f'<article class="post"><h1>Presidentes de comissões da Câmara</h1><p class="snippet">{num(len(pc))} colegiados da Câmara dos Deputados têm presidente registrado na API oficial, entre comissões permanentes, especiais, temporárias, frentes, grupos de trabalho e conselhos.</p>'
         + S.table(["Colegiado", "Presidente", "Partido-UF"], [[E(o["nome"]), f'<a href="{d["url"]}">{E(d["nome"])}</a>', f'{E(d["partido"])}-{d["uf"]}'] for o, d in pc], "Em ordem alfabética do colegiado")
         + f'<p class="src">Fonte oficial: <a href="https://dadosabertos.camara.leg.br/" target="_blank" rel="noopener">Câmara dos Deputados, API Dados Abertos</a> (órgãos de cada deputado), coleta em {data_br(cd)}.</p>'
         + '<p>Entenda: <a href="/glossario/comissao-permanente/">comissão permanente</a> · <a href="/explica/como-funciona-uma-cpi/">como funciona uma CPI</a> · <a href="/congresso/comissoes-e-cpis/">notícias das comissões</a></p></article>')
    pages["/quem-e-quem/presidentes-de-comissoes/"] = ("Presidentes de comissões da Câmara", f"Quem preside cada um dos {len(pc)} colegiados da Câmara, pela API oficial.", b,
        [("Quantos colegiados têm presidente registrado?", f"{num(len(pc))} na última coleta."), ("Como o presidente de comissão é escolhido?", "Por eleição entre os membros, conforme acordo partidário e o princípio da proporcionalidade."),
         ("O que faz o presidente de comissão?", "Define a pauta, conduz as reuniões e designa relatores."), ("De onde vêm os dados?", "Da API de dados abertos da Câmara, pelo cargo de cada deputado em cada órgão."),
         ("O Senado está incluído?", "Ainda não; a lista do Senado entra quando houver fonte estruturada com o cargo.")], [])
    for u, (t, d, b, faqs, pes) in pages.items():
        S.write(u, S.page(f"{t} | {S.CFG['site_name']}", d, u, b, faqs=faqs, crumbs=[("Quem é quem", "/quem-e-quem/"), (t, u)], jsonld=({"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": k + 1, "item": p} for k, p in enumerate(pes)]} if pes else None)), familia="quem_e_quem"); urls.append(u)
    hub = '<section class="blk"><h1>Quem é quem nos Três Poderes</h1><p class="lead">Quem ocupa os principais cargos do Judiciário, do Executivo e do Legislativo, com dados das fontes oficiais coletados automaticamente.</p><ul>' + "".join(f'<li><a href="{u}">{E(t)}</a>: {E(d)}</li>' for u, (t, d, *_r) in pages.items()) + '<li><a href="/deputados/">Deputados federais</a> e <a href="/senadores/">senadores</a></li></ul></section>'
    S.write("/quem-e-quem/", S.page(f"Quem é quem | {S.CFG['site_name']}", "STF, ministros de Estado, líderes partidários e presidentes de comissões, com dados oficiais.", "/quem-e-quem/", hub,
            faqs=[("O que esta seção reúne?", "Ocupantes dos principais cargos dos Três Poderes."), ("De onde vêm os dados?", "Do STF, do Planalto e da API da Câmara."), ("Com que frequência atualiza?", "A cada coleta automática."),
                  ("Há ranking?", "Não. Listas em ordem alfabética ou de antiguidade."), ("Como avisar de um erro?", 'Pela página de <a href="/correcoes/">correções</a>.')], crumbs=[("Quem é quem", "/quem-e-quem/")]))
    return {"urls": urls}
