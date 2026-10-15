"""Frentes parlamentares (57a legislatura) e comissoes/CPIs/colegiados da Camara, do Senado e do Congresso.
Dados: data/colegiados/colegiados.json.gz (tools/datasets_colegiados.py: arquivos em lote da Camara e API de Dados Abertos do Senado).
Familias `frentes` e `comissoes` (noindex ate a onda propria); hubs /frentes/, /comissoes/, /comissoes/camara/, /comissoes/senado/ e /comissoes/cpis/ indexaveis.
Composicao e listas de membros em ordem alfabetica; sem ranking de parlamentares."""
import collections, csv, gzip, json
from core.site import E, slugify
from .dados import UF, data_br, num, pct

TIPO_TXT = {"Comissão Permanente": "As comissões permanentes são órgãos fixos da Casa, divididos por área temática, que analisam as proposições, fazem audiências públicas e fiscalizam o Executivo.",
            "Comissão Especial": "Comissões especiais são criadas para dar parecer sobre uma proposição específica, como uma PEC ou um projeto de grande alcance, e se extinguem quando a análise termina.",
            "Comissão Externa": "Comissões externas são temporárias e acompanham, fora da Casa, um tema ou um fato de interesse público, como visitas a locais e acompanhamento de obras ou ações do governo.",
            "Comissão Parlamentar de Inquérito": "Uma CPI investiga fato determinado por prazo certo, com poderes de investigação próprios das autoridades judiciais, e precisa de um terço dos membros da Casa para ser criada.",
            "Comissão Temporária Externa": "Comissões temporárias externas acompanham, fora da Casa, um tema ou um fato de interesse público.",
            "Comissão de Medida Provisória": "Cada medida provisória é analisada por uma comissão mista de deputados e senadores, que emite parecer antes da votação em cada Casa.",
            "Subcomissão Permanente": "Subcomissões permanentes aprofundam temas da comissão a que pertencem.", "Conselho": "Conselhos são órgãos consultivos ou de controle ligados à Casa legislativa.",
            "Comissão Mista Permanente": "Comissões mistas permanentes reúnem deputados e senadores para tratar de temas do Congresso Nacional, como o orçamento.", "Grupo de Trabalho": "Grupos de trabalho são colegiados temporários criados para estudar um tema específico."}
_C = {}


def carregar(S):
    if "d" in _C: return _C["d"]
    f = S.ROOT / "data/colegiados/colegiados.json.gz"
    d = json.loads(gzip.decompress(f.read_bytes())) if f.exists() else {"camara": [], "senado": [], "frentes": [], "coletado_em": ""}
    ex = {"Frente Parlamentar", "Grupo Parlamentar", "Plenário", "Mesa", "Relatores Setoriais do PLOA", "Órgãos de Representação Internacional"}
    d["senado"] = [o for o in d["senado"] if o["tipo"] not in ex and (o["fin"] or o["m"])]
    us = set()
    for o in d["camara"]: o["slug"] = (slugify(o["sigla"]) or str(o["id"])); o["url"] = f"/comissoes/camara/{o['slug']}/"; us.add(o["url"])
    for o in d["senado"]:
        s = slugify(o["sigla"]) or str(o["cod"]); u = f"/comissoes/senado/{s}/"
        if u in us: s = f"{s}-{o['cod']}"; u = f"/comissoes/senado/{s}/"
        o["slug"], o["url"] = s, u; us.add(u)
    for f_ in d["frentes"]:
        f_["slug"] = f"{slugify(f_['t'])[:80].strip('-')}-{f_['id']}"; f_["url"] = f"/frentes/{f_['slug']}/"
    dep, sen = collections.defaultdict(lambda: {"fr": [], "co": []}), collections.defaultdict(list)
    for f_ in d["frentes"]:
        for m in f_["m"]: dep[m[0]]["fr"].append(f_)
    for o in d["camara"]:
        for m in o["m"]: dep[m[0]]["co"].append((o, m[4]))
    for o in d["senado"]:
        for m in o["m"]: sen[m[0]].append((o, m[4]))
    d["dep"], d["sen"] = dep, sen; _C["d"] = d; return d


def bloco_deputado(S, did):
    d = carregar(S); x = d["dep"].get(int(did))
    if not x or not (x["fr"] or x["co"]): return ""
    h = ""
    if x["co"]:
        h += f'<h2 id="comissoes">Comissões da Câmara de que participa</h2><ul class="nlist">' + "".join(f'<li><a href="{o["url"]}">{E(o["nome"])}</a> <small>({E(c)})</small></li>' for o, c in sorted(x["co"], key=lambda t: t[0]["nome"])) + "</ul>"
    if x["fr"]:
        fr = sorted(x["fr"], key=lambda f: f["t"]); li = "".join(f'<li><a href="{f["url"]}">{E(f["t"])}</a></li>' for f in fr[:15])
        h += f'<h2 id="frentes">Frentes parlamentares</h2><p>Consta como membro de <strong>{len(fr)}</strong> frentes parlamentares registradas na Câmara na 57ª legislatura{" (primeiras 15, em ordem alfabética)" if len(fr) > 15 else ""}. A adesão a uma frente não indica voto em nenhuma proposição.</p><ul class="nlist">{li}</ul>'
    return h + '<p class="src">Fonte: Dados Abertos da Câmara (órgãos e frentes). Veja <a href="/comissoes/">comissões</a> e <a href="/frentes/">frentes</a>.</p>'


def bloco_senador(S, code):
    x = carregar(S)["sen"].get(int(code))
    if not x: return ""
    return ('<h2 id="comissoes">Comissões e colegiados de que participa</h2><ul class="nlist">' + "".join(f'<li><a href="{o["url"]}">{E(o["nome"])}</a> <small>({E(c or "membro")})</small></li>' for o, c in sorted(x, key=lambda t: t[0]["nome"]))
            + '</ul><p class="src">Fonte: Dados Abertos do Senado (colegiados em atividade). Veja <a href="/comissoes/">comissões</a>.</p>')


def _comp(membros, ix_p, ix_u):
    p = collections.Counter(m[ix_p] for m in membros if m[ix_p]); u = collections.Counter(m[ix_u] for m in membros if m[ix_u])
    return p, u


def _tab_comp(S, p, u):
    pr = [[E(k), str(v)] for k, v in sorted(p.items())]; ur = [[E(UF.get(k, k)), str(v)] for k, v in sorted(u.items(), key=lambda t: UF.get(t[0], t[0]))]
    return "<h2>Composição por partido</h2>" + S.table(["Partido", "Membros"], pr, "Membros por partido (ordem alfabética)") + "<h2>Composição por estado</h2>" + S.table(["Estado", "Membros"], ur, "Membros por estado (ordem alfabética)")


def build(S):
    D = carregar(S); col = D["coletado_em"][:10]; urls = []
    if not (D["camara"] or D["senado"] or D["frentes"]): return {"urls": []}
    dep_url = {a["id"]: a["url"] for a in S.parl["deps"]}; dep_p = {a["id"]: a["partido"] for a in S.parl["deps"]}; sen_url = {int(a["id"]): a["url"] for a in S.parl["sens"]}
    gl = lambda s, n: f'<a href="/glossario/{s}/">{E(n)}</a>' if f"/glossario/{s}/" in S.urls else E(n)
    # ---------- comissoes da Camara ----------
    for o in D["camara"]:
        m = o["m"]; tit = [x for x in m if x[4] == "Titular"]; sup = [x for x in m if x[4] == "Suplente"]; cg = [x for x in m if x[4] not in ("Titular", "Suplente")]
        pres = next((x for x in m if x[4] == "Presidente"), None); p, u = _comp(m, 2, 3); nomes_membros = sorted({x[0]: x for x in m}.values(), key=lambda x: slugify(x[1]))
        who = lambda x: (f'<a href="{dep_url[x[0]]}">{E(x[1])}</a>' if x[0] in dep_url else E(x[1])) + f" <small>({E(x[2])}-{E(x[3])})</small>"
        lead = (f'<p class="snippet">{E(o["nome"])}{" (" + E(o["sigla"]) + ")" if o["sigla"] else ""} é um órgão da Câmara dos Deputados do tipo <strong>{E(o["tipo"].lower())}</strong>, com situação “{E(o["sit"] or "em funcionamento")}”'
                + (f', instalado em {data_br(o["inst"])}' if o["inst"] else "") + f'. Tem <strong>{len(nomes_membros)} deputados</strong> registrados, entre {len(tit)} titulares e {len(sup)} suplentes' + (f"; a presidência é de {E(pres[1])} ({E(pres[2])}-{E(pres[3])})" if pres else "") + ".</p>")
        info = [("Tipo", E(o["tipo"])), ("Sigla", E(o["sigla"])), ("Situação", E(o["sit"])), ("Criação", data_br(o["ini"])), ("Instalação", data_br(o["inst"])), ("Local", E(o["sala"])), ("Site", f'<a href="{E(o["site"])}" target="_blank" rel="noopener">{E(o["site"])}</a>' if o["site"] else "")]
        body = f'<article class="post"><h1>{E(o["nome"])}: composição e membros</h1>{lead}<div class="tw"><table><tbody>' + "".join(f'<tr><th scope="row">{k}</th><td>{x}</td></tr>' for k, x in info if x) + "</tbody></table></div>"
        body += f"<h2>O que faz esse tipo de órgão</h2><p>{E(TIPO_TXT.get(o['tipo'], 'Órgão colegiado da Câmara dos Deputados.'))} Veja também: {gl('comissao-permanente', 'comissão permanente')}, {gl('comissao-especial', 'comissão especial')} e {gl('relator', 'relator')}.</p>"
        if cg: body += "<h2>Direção e relatoria</h2><ul class=\"nlist\">" + "".join(f"<li>{E(x[4])}: {who(x)}</li>" for x in sorted(cg, key=lambda x: (x[4], slugify(x[1])))) + "</ul>"
        body += _tab_comp(S, p, u) + f"<h2>Membros ({len(nomes_membros)})</h2><ul class=\"nlist\">" + "".join(f"<li>{who(x)} <small>{E(x[4])}</small></li>" for x in nomes_membros) + "</ul>"
        body += f'<p class="src">Fonte: Dados Abertos da Câmara (órgãos e membros da 57ª legislatura), compilação de {data_br(col)}. Veja todas as <a href="/comissoes/camara/">comissões da Câmara</a> e a <a href="/comissoes/metodologia/">metodologia</a>.</p></article>'
        mp = max(p.items(), key=lambda t: (t[1], t[0])) if p else None
        faqs = [(f"Quantos deputados integram {o['sigla'] or o['nome']}?", f"{len(nomes_membros)} deputados registrados, sendo {len(tit)} titulares e {len(sup)} suplentes, segundo a Câmara em {data_br(col)}."),
                (f"Quem preside {o['sigla'] or o['nome']}?", f"{E(pres[1])} ({E(pres[2])}-{E(pres[3])})." if pres else "A Câmara não informa presidente para o órgão na data da coleta."),
                (f"Que tipo de órgão é {o['sigla'] or o['nome']}?", E(o["tipo"]) + ". " + E(TIPO_TXT.get(o["tipo"], ""))), (f"Quais partidos têm mais membros em {o['sigla'] or o['nome']}?", f"O partido com mais membros é o {E(mp[0])}, com {mp[1]}; a composição completa está nesta página em ordem alfabética." if mp else "Sem dados."),
                ("Quando o órgão foi instalado?", (f"Em {data_br(o['inst'])}." if o["inst"] else "A Câmara não informa a data de instalação.")), ("Os membros mudam?", "Sim. Titulares e suplentes podem ser trocados pelos partidos e blocos; a página é atualizada diariamente.")]
        S.write(o["url"], S.page(f"{o['nome']}: composição e membros na Câmara", f"{o['nome']} ({o['sigla']}): {len(nomes_membros)} deputados, presidência, composição por partido e estado. Dados oficiais da Câmara.", o["url"], body, faqs=faqs,
                                 crumbs=[("Comissões", "/comissoes/"), ("Câmara", "/comissoes/camara/"), (o["sigla"] or o["nome"], o["url"])], jsonld={"@type": "GovernmentOrganization", "name": o["nome"], "alternateName": o["sigla"], "url": S.BASE + o["url"], "parentOrganization": {"@type": "GovernmentOrganization", "name": "Câmara dos Deputados"}}),
                familia="comissoes", lastmod=col); urls.append(o["url"])
    # ---------- colegiados do Senado e do CN ----------
    CASA = {"SF": "Senado Federal", "CN": "Congresso Nacional"}
    for o in D["senado"]:
        m = o["m"]; tit = [x for x in m if x[4] == "Titular"]; sup = [x for x in m if x[4] == "Suplente"]; p, u = _comp(m, 2, 3); nomes = sorted({x[0]: x for x in m}.values(), key=lambda x: slugify(x[1]))
        who = lambda x: (f'<a href="{sen_url[x[0]]}">{E(x[1])}</a>' if x[0] in sen_url else E(x[1])) + (f" <small>({E(x[2])}-{E(x[3])})</small>" if x[2] else "")
        pres = next((c for c in o["cargos"] if c[0] == "PRESIDENTE"), None); casa = CASA.get(o["casa"], o["casa"])
        lead = (f'<p class="snippet">{E(o["nome"])}{" (" + E(o["sigla"]) + ")" if o["sigla"] else ""} é um colegiado do {casa} do tipo <strong>{E(o["tipo"].lower())}</strong>' + (f", em atividade desde {data_br(o['ini'])}" if o["ini"] else "")
                + (f'. Tem <strong>{len(nomes)} senadores</strong> registrados, entre {len(tit)} titulares e {len(sup)} suplentes' if nomes else "") + (f"; a presidência é de {E(pres[1])} {E(pres[3])}" if pres else "") + ".</p>")
        info = [("Tipo", E(o["tipo"])), ("Casa", casa), ("Sigla", E(o["sigla"])), ("Em atividade desde", data_br(o["ini"])), ("Finalidade", E(o["fin"])), ("Reuniões públicas", "Sim" if o["pub"] == "S" else ("Não" if o["pub"] == "N" else ""))]
        body = f'<article class="post"><h1>{E(o["nome"])}: finalidade e membros</h1>{lead}<div class="tw"><table><tbody>' + "".join(f'<tr><th scope="row">{k}</th><td>{x}</td></tr>' for k, x in info if x) + "</tbody></table></div>"
        body += f"<h2>O que faz esse tipo de colegiado</h2><p>{E(TIPO_TXT.get(o['tipo'], 'Colegiado do Poder Legislativo federal.'))} Veja também: {gl('comissao-permanente', 'comissão permanente')} e {gl('comissao-mista', 'comissão mista')}.</p>"
        if o["cargos"]: body += "<h2>Direção</h2><ul class=\"nlist\">" + "".join(f"<li>{E(c[0].capitalize())}: " + (f'<a href="{sen_url[c[2]]}">{E(c[1])}</a>' if c[2] in sen_url else E(c[1])) + f" <small>{E(c[3])}</small></li>" for c in o["cargos"]) + "</ul>"
        if nomes: body += _tab_comp(S, p, u) + f"<h2>Membros ({len(nomes)})</h2><ul class=\"nlist\">" + "".join(f"<li>{who(x)} <small>{E(x[4])}</small></li>" for x in nomes) + "</ul>"
        body += f'<p class="src">Fonte: Dados Abertos do Senado (colegiados em atividade), compilação de {data_br(col)}. Veja todos os <a href="/comissoes/senado/">colegiados do Senado e do Congresso</a> e a <a href="/comissoes/metodologia/">metodologia</a>.</p></article>'
        mp = max(p.items(), key=lambda t: (t[1], t[0])) if p else None
        faqs = [(f"Para que serve {o['sigla'] or o['nome']}?", E(o["fin"]) if o["fin"] else E(TIPO_TXT.get(o["tipo"], "Colegiado do Poder Legislativo federal."))),
                (f"Quantos senadores integram {o['sigla'] or o['nome']}?", f"{len(nomes)} senadores registrados, sendo {len(tit)} titulares e {len(sup)} suplentes, segundo o Senado em {data_br(col)}." if nomes else "O Senado não informa membros para o colegiado na data da coleta."),
                (f"Quem preside {o['sigla'] or o['nome']}?", f"{E(pres[1])} {E(pres[3])}." if pres else "O Senado não informa presidente na data da coleta."), (f"Que tipo de colegiado é {o['sigla'] or o['nome']}?", f"{E(o['tipo'])} do {casa}."),
                (f"Quais partidos têm mais membros em {o['sigla'] or o['nome']}?", f"O partido com mais membros é o {E(mp[0])}, com {mp[1]}; a composição completa está nesta página em ordem alfabética." if mp else "Sem dados."),
                ("Desde quando funciona?", (f"Desde {data_br(o['ini'])}." if o["ini"] else "O Senado não informa a data."))]
        S.write(o["url"], S.page(f"{o['nome']}: finalidade e membros no {casa.split()[0]}", f"{o['nome']} ({o['sigla']}): {('finalidade, ' if o['fin'] else '')}{len(nomes)} senadores, presidência e composição. Dados oficiais do Senado.", o["url"], body, faqs=faqs,
                                 crumbs=[("Comissões", "/comissoes/"), ("Senado e Congresso", "/comissoes/senado/"), (o["sigla"] or o["nome"], o["url"])], jsonld={"@type": "GovernmentOrganization", "name": o["nome"], "alternateName": o["sigla"], "url": S.BASE + o["url"], "parentOrganization": {"@type": "GovernmentOrganization", "name": casa}}),
                familia="comissoes", lastmod=col); urls.append(o["url"])
    # ---------- hubs de comissoes ----------
    def tab_o(L, casa):
        return S.table(["Órgão", "Tipo", "Situação" if casa == "camara" else "Casa", "Membros"], [[f'<a href="{o["url"]}">{E(o["nome"])}</a>', E(o["tipo"]), E(o["sit"] or "em funcionamento") if casa == "camara" else E(o["casa"]), str(len({x[0] for x in o["m"]}))]
                                                                                                  for o in sorted(L, key=lambda o: slugify(o["nome"]))], "Em ordem alfabética")
    cam, sen = D["camara"], D["senado"]; tc = collections.Counter(o["tipo"] for o in cam); ts = collections.Counter(o["tipo"] for o in sen)
    cpis = [o for o in sen if "Inquérito" in o["tipo"]] + [o for o in cam if "Inquérito" in o["tipo"]]
    def hub(path, titulo, h1, snippet, corpo, faqs, desc, crumbs, ld=None):
        body = f'<section class="blk"><h1>{h1}</h1><p class="snippet">{snippet}</p>{corpo}<p class="src">Fonte: Dados Abertos da Câmara e do Senado. Compilação de {data_br(col)}. Veja a <a href="/comissoes/metodologia/">metodologia</a>.</p></section>'
        S.write(path, S.page(titulo, desc, path, body, faqs=faqs, crumbs=crumbs, jsonld=ld), familia="paginas", lastmod=col); urls.append(path)
    f_com = [("O que é uma comissão permanente?", E(TIPO_TXT["Comissão Permanente"])), ("O que é uma CPI?", E(TIPO_TXT["Comissão Parlamentar de Inquérito"])), ("Quantos colegiados há em atividade?", f"{len(cam)} órgãos da Câmara com membros e {len(sen)} colegiados do Senado e do Congresso na compilação de {data_br(col)}."),
             ("Como saber quem integra uma comissão?", "Cada página traz a composição por partido e estado e a lista de membros, com link para o perfil de cada parlamentar."), ("As listas mostram qual comissão é mais importante?", "Não. A ordem é alfabética e o número de membros não mede a importância de um órgão."),
             ("Com que frequência os dados são atualizados?", "Uma vez por dia, a partir dos dados abertos da Câmara e do Senado.")]
    hub("/comissoes/", f"Comissões, CPIs e colegiados do Congresso: composição e membros | {S.CFG['site_name']}", "Comissões, CPIs e colegiados do Congresso",
        f"O Estrato lista <strong>{len(cam)} órgãos da Câmara</strong> e <strong>{len(sen)} colegiados do Senado e do Congresso Nacional</strong> em atividade, com tipo, composição por partido e estado, presidência e lista de membros.",
        "<h2>Câmara dos Deputados</h2><p>" + ", ".join(f"{n} {E(t.lower())}" for t, n in tc.most_common()) + f'. <a href="/comissoes/camara/">Ver a lista da Câmara</a>.</p>' + "<h2>Senado e Congresso Nacional</h2><p>" + ", ".join(f"{n} {E(t.lower())}" for t, n in ts.most_common(8))
        + f'. <a href="/comissoes/senado/">Ver a lista do Senado e do Congresso</a>.</p><h2>CPIs</h2><p>As comissões parlamentares de inquérito em funcionamento estão em <a href="/comissoes/cpis/">CPIs</a>.</p>'
        f'<h2>Como ler</h2><p>Comissões são o lugar onde as proposições são analisadas antes do plenário. Veja {gl("comissao-permanente", "comissão permanente")}, {gl("comissao-especial", "comissão especial")}, {gl("comissao-mista", "comissão mista")} e {gl("cpi", "CPI")} no glossário. Veja ainda as <a href="/frentes/">frentes parlamentares</a> e a <a href="/agenda/">agenda</a>.</p>',
        f_com, f"{len(cam)} órgãos da Câmara e {len(sen)} colegiados do Senado e do Congresso: tipo, composição, presidência e membros, com dados oficiais.", [("Comissões", "/comissoes/")])
    hub("/comissoes/camara/", f"Comissões e órgãos da Câmara dos Deputados: lista e membros | {S.CFG['site_name']}", "Comissões e órgãos da Câmara dos Deputados",
        f"São <strong>{len(cam)} órgãos</strong> da Câmara com membros registrados na 57ª legislatura: " + ", ".join(f"{n} {E(t.lower())}" for t, n in tc.most_common(5)) + ".", tab_o(cam, "camara"),
        [("Quantas comissões permanentes a Câmara tem?", f"{tc.get('Comissão Permanente', 0)} comissões permanentes com membros registrados."), ("Quais são as comissões especiais?", f"{tc.get('Comissão Especial', 0)} comissões especiais em funcionamento, criadas para analisar proposições específicas."),
         ("O que é uma comissão externa?", E(TIPO_TXT["Comissão Externa"])), ("Como são escolhidos os membros?", "Os partidos e blocos indicam titulares e suplentes de acordo com a proporcionalidade das bancadas."), ("A lista traz CPIs?", 'As CPIs em funcionamento ficam em <a href="/comissoes/cpis/">CPIs</a>.'), ("De onde vêm os dados?", "Dos arquivos em lote de órgãos e membros da Câmara.")],
        f"{len(cam)} órgãos da Câmara com membros: comissões permanentes, especiais e externas, em ordem alfabética.", [("Comissões", "/comissoes/"), ("Câmara", "/comissoes/camara/")])
    hub("/comissoes/senado/", f"Comissões e colegiados do Senado e do Congresso: lista | {S.CFG['site_name']}", "Comissões e colegiados do Senado e do Congresso Nacional",
        f"São <strong>{len(sen)} colegiados</strong> em atividade no Senado e no Congresso Nacional: " + ", ".join(f"{n} {E(t.lower())}" for t, n in ts.most_common(5)) + ".", tab_o(sen, "senado"),
        [("Quantas comissões permanentes o Senado tem?", f"{ts.get('Comissão Permanente', 0)} comissões permanentes do Senado e {sum(1 for o in sen if o['tipo'] == 'Comissão Permanente' and o['casa'] == 'CN')} do Congresso."), ("O que é uma comissão de medida provisória?", E(TIPO_TXT["Comissão de Medida Provisória"])),
         ("Quais colegiados têm CPI?", 'As CPIs em funcionamento estão em <a href="/comissoes/cpis/">CPIs</a>.'), ("Todas as reuniões são públicas?", "Cada página informa se as reuniões do colegiado são públicas, quando o Senado registra essa informação."), ("O que é um conselho do Senado?", E(TIPO_TXT["Conselho"])), ("De onde vêm os dados?", "Da API de Dados Abertos do Senado, que lista os colegiados em atividade.")],
        f"{len(sen)} colegiados em atividade no Senado e no Congresso Nacional, com finalidade, composição e membros.", [("Comissões", "/comissoes/"), ("Senado e Congresso", "/comissoes/senado/")])
    f_cpi = [("O que é uma CPI?", E(TIPO_TXT["Comissão Parlamentar de Inquérito"])), ("Quantas CPIs estão em funcionamento?", f"{len(cpis)} na compilação de {data_br(col)}."), ("Quem pode pedir uma CPI?", "É preciso o apoio de um terço dos membros da Casa, ou seja, 171 deputados ou 27 senadores, e um fato determinado."),
             ("Uma CPI pode punir alguém?", "Não. Ela investiga e envia as conclusões ao Ministério Público ou a outros órgãos, que decidem se há ação."), ("Qual a diferença entre CPI e CPMI?", "A CPMI é mista: reúne deputados e senadores. A CPI é de uma só Casa."), ("Onde ver a composição de uma CPI?", "Na página de cada CPI, com a lista de membros em ordem alfabética.")]
    hub("/comissoes/cpis/", f"CPIs em funcionamento no Congresso: membros e composição | {S.CFG['site_name']}", "CPIs em funcionamento no Congresso",
        f"Na data da compilação, há <strong>{len(cpis)} comissões parlamentares de inquérito</strong> em funcionamento registradas nos dados abertos do Senado e da Câmara. Uma CPI investiga um fato determinado por prazo certo.",
        (tab_o(cpis, "senado") if cpis else "<p>Nenhuma CPI está registrada como em funcionamento nos dados abertos da Câmara e do Senado.</p>") + f'<h2>Como funciona</h2><p>{E(TIPO_TXT["Comissão Parlamentar de Inquérito"])} Veja {gl("cpi", "CPI")} e {gl("comissao-mista", "comissão mista")} no glossário e as <a href="/comissoes/">demais comissões</a>.</p>',
        f_cpi, "CPIs em funcionamento no Congresso Nacional: composição, membros e como uma CPI funciona, com dados oficiais da Câmara e do Senado.", [("Comissões", "/comissoes/"), ("CPIs", "/comissoes/cpis/")])
    # ---------- frentes ----------
    FR = sorted(D["frentes"], key=lambda f: slugify(f["t"]))
    for f_ in FR:
        m = sorted({x[0]: x for x in f_["m"]}.values(), key=lambda x: slugify(x[1])); pc = collections.Counter(dep_p.get(x[0], "") for x in m if dep_p.get(x[0])); uc = collections.Counter(x[2] for x in m if x[2])
        co = f_["co"]; cou = dep_url.get(co[0]) if co else None
        info = [("Criação", data_br(f_["cri"])), ("Coordenação", (f'<a href="{cou}">{E(co[1])}</a> ({E(co[2])}-{E(co[3])})' if cou else f"{E(co[1])} ({E(co[2])}-{E(co[3])})") if co else ""), ("Contato", f'{E(f_["tel"])} {E(f_["email"])}'.strip()),
                ("Site", f'<a href="{E(f_["site"])}" target="_blank" rel="noopener">{E(f_["site"])}</a>' if f_["site"] else ""), ("Palavras-chave", E(f_["kw"]))]
        lead = (f'<p class="snippet">A <strong>{E(f_["t"])}</strong> foi registrada na Câmara dos Deputados em {data_br(f_["cri"])}' + (f" e é coordenada por {E(co[1])} ({E(co[2])}-{E(co[3])})" if co else "")
                + f". Tem <strong>{len(m)} deputados</strong> como membros na 57ª legislatura, de {len(uc)} estados e {len(pc)} partidos.</p>")
        body = f'<article class="post"><h1>{E(f_["t"])}: coordenação e membros</h1>{lead}<div class="tw"><table><tbody>' + "".join(f'<tr><th scope="row">{k}</th><td>{x}</td></tr>' for k, x in info if x) + "</tbody></table></div>"
        body += f'<h2>O que é uma frente parlamentar</h2><p>Frentes são associações de parlamentares, de partidos diferentes, em torno de um tema. São registradas na Câmara quando reúnem assinaturas de pelo menos um terço dos membros do Legislativo e não têm poder de decisão: servem para articular pautas. Veja {gl("frente-parlamentar", "frente parlamentar")} no glossário.</p>'
        body += _tab_comp(S, pc, uc) + f"<h2>Membros ({len(m)})</h2><ul class=\"nlist\">" + "".join(f'<li>{(f"<a href={chr(34)}{dep_url[x[0]]}{chr(34)}>{E(x[1])}</a>" if x[0] in dep_url else E(x[1]))} <small>{E(dep_p.get(x[0], ""))}{"-" if dep_p.get(x[0]) else ""}{E(x[2])}{(", " + E(x[3])) if x[3] and x[3] != "Membro" else ""}</small></li>' for x in m) + "</ul>"
        body += f'<p class="src">Fonte: Dados Abertos da Câmara (frentes e frentes-deputados), compilação de {data_br(col)}. Partido é o atual do parlamentar. Veja todas as <a href="/frentes/">frentes parlamentares</a>.</p></article>'
        mp = max(pc.items(), key=lambda t: (t[1], t[0])) if pc else None
        faqs = [(f"Quantos deputados integram a {f_['t']}?", f"{len(m)} deputados, de {len(uc)} estados e {len(pc)} partidos, segundo a Câmara em {data_br(col)}."), (f"Quem coordena a {f_['t']}?", f"{E(co[1])} ({E(co[2])}-{E(co[3])})." if co else "A Câmara não informa coordenador."),
                (f"Quando a {f_['t']} foi criada?", f"Foi registrada em {data_br(f_['cri'])}."), ("O que uma frente parlamentar pode fazer?", "Articular pautas e reunir parlamentares em torno de um tema. Não tem poder de decisão nem substitui comissões."),
                (f"Qual partido tem mais deputados na {f_['t']}?", f"O {E(mp[0])}, com {mp[1]} membros; a composição completa está nesta página em ordem alfabética." if mp else "Sem dados."), ("Participar de uma frente indica voto em projetos?", "Não. A adesão mostra interesse no tema, não posição em votações.")]
        S.write(f_["url"], S.page(f"{f_['t']}: membros e coordenação", f"{f_['t']}: {len(m)} deputados de {len(uc)} estados, coordenação, composição por partido e contatos. Dados oficiais da Câmara.", f_["url"], body, faqs=faqs,
                                  crumbs=[("Frentes parlamentares", "/frentes/"), (f_["t"], f_["url"])], jsonld={"@type": "Organization", "name": f_["t"], "url": S.BASE + f_["url"], "foundingDate": f_["cri"]}), familia="frentes", lastmod=col); urls.append(f_["url"])
    rows = [[f'<a href="{f_["url"]}">{E(f_["t"])}</a>', data_br(f_["cri"]), E(f_["co"][1]) if f_["co"] else "", str(len({x[0] for x in f_["m"]}))] for f_ in FR]
    tot_m = len({x[0] for f_ in FR for x in f_["m"]})
    body = (f'<section class="blk"><h1>Frentes parlamentares da Câmara dos Deputados</h1><p class="snippet">A Câmara registra <strong>{len(FR)} frentes parlamentares</strong> na 57ª legislatura (2023 a 2027), que reúnem ao todo {num(tot_m)} deputados em torno de temas como agro, saúde, educação e meio ambiente. '
            f'Cada página traz a coordenação, a composição por partido e estado e a lista de membros.</p>' + S.table(["Frente", "Criação", "Coordenação", "Deputados"], rows, "Todas as frentes em ordem alfabética")
            + f'<h2>O que é uma frente</h2><p>Frentes parlamentares são associações suprapartidárias de parlamentares em torno de um tema. Não votam nem decidem; servem para articular pautas. Veja {gl("frente-parlamentar", "frente parlamentar")} no glossário e as <a href="/comissoes/">comissões</a>, onde as proposições são analisadas.</p>'
            f'<p class="src">Fonte: Dados Abertos da Câmara. Compilação de {data_br(col)}. Dados em <a href="/dados/#frentes">CSV</a>.</p></section>')
    faqs = [("Quantas frentes parlamentares existem?", f"{len(FR)} registradas na Câmara na 57ª legislatura, segundo a compilação de {data_br(col)}."), ("O que é uma frente parlamentar?", "Uma associação de parlamentares de diferentes partidos em torno de um tema, sem poder de decisão."),
            ("Como uma frente é criada?", "Precisa ser registrada na Câmara com assinaturas de pelo menos um terço dos membros do Legislativo, ou seja, 171 deputados e senadores."), ("Participar de uma frente indica voto em projetos?", "Não. A adesão mostra interesse no tema."),
            ("A lista ordena as frentes por tamanho ou importância?", "Não. A ordem é alfabética."), ("Os senadores aparecem?", "Esta lista traz os deputados registrados nos dados abertos da Câmara; frentes mistas podem ter senadores que não constam neste conjunto.")]
    S.write("/frentes/", S.page("Frentes parlamentares da Câmara: lista, coordenação e membros", f"{len(FR)} frentes parlamentares da 57ª legislatura com coordenação, composição por partido e estado e membros. Dados oficiais da Câmara.", "/frentes/", body, faqs=faqs,
                                crumbs=[("Frentes parlamentares", "/frentes/")], jsonld=S.itemlist([(f_["t"], f_["url"]) for f_ in FR])), familia="paginas", lastmod=col); urls.append("/frentes/")
    # metodologia
    body = ('<article class="post"><h1>Metodologia: comissões, colegiados e frentes</h1><p class="snippet">Como o Estrato compila órgãos, colegiados e frentes parlamentares do Congresso.</p>'
            '<h2>Fontes</h2><p>Câmara: arquivos em lote de órgãos, membros de órgãos (57ª legislatura), frentes e membros de frentes. Senado e Congresso Nacional: API de Dados Abertos, lista de colegiados em atividade e dados de cada colegiado.</p>'
            '<h2>Seleção</h2><p>Câmara: órgãos com ao menos um membro ativo, excluídos os extintos. Senado e Congresso: colegiados em atividade com finalidade ou membros registrados; frentes e grupos parlamentares do Congresso e órgãos de representação internacional ficam de fora. Frentes: as registradas na 57ª legislatura com membros ativos.</p>'
            '<h2>Composição</h2><p>Contagens por partido e estado usam o partido registrado no órgão (comissões) ou o atual do deputado (frentes). Listas de membros e tabelas seguem ordem alfabética, sem ranking.</p>'
            '<h2>Limites</h2><p>A composição muda com frequência (troca de titulares e suplentes, adesões a frentes). Participar de comissão ou frente não indica voto. Reuniões e pautas estão na <a href="/agenda/">agenda</a>.</p></article>')
    faqs = [("De onde vêm os dados?", "Dos dados abertos da Câmara e do Senado."), ("Por que alguns colegiados não aparecem?", "Entram só os em atividade, com membros ou finalidade registrados."), ("A lista ordena por importância?", "Não. Ordem alfabética."),
            ("Participar de frente indica voto?", "Não."), ("Os dados são atualizados?", "Diariamente."), ("Como corrigir um dado?", 'Pela página de <a href="/correcoes/">correções</a>.')]
    S.write("/comissoes/metodologia/", S.page("Metodologia de comissões, colegiados e frentes", "Como o Estrato compila comissões, CPIs, colegiados e frentes parlamentares a partir de dados abertos da Câmara e do Senado.", "/comissoes/metodologia/", body, faqs=faqs,
                                              crumbs=[("Comissões", "/comissoes/"), ("Metodologia", "/comissoes/metodologia/")]), familia="paginas", lastmod=col); urls.append("/comissoes/metodologia/")
    out = S.OUT / "dados"; out.mkdir(parents=True, exist_ok=True)
    with (out / "comissoes.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["casa", "sigla", "nome", "tipo", "situacao", "membros", "url_estrato"])
        for o in cam: w.writerow(["Câmara", o["sigla"], o["nome"], o["tipo"], o["sit"], len({x[0] for x in o["m"]}), S.BASE + o["url"]])
        for o in sen: w.writerow([o["casa"], o["sigla"], o["nome"], o["tipo"], "em atividade", len({x[0] for x in o["m"]}), S.BASE + o["url"]])
    with (out / "frentes.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["id_camara", "frente", "criacao", "coordenador", "membros", "url_estrato"])
        for f_ in FR: w.writerow([f_["id"], f_["t"], f_["cri"], f_["co"][1] if f_["co"] else "", len({x[0] for x in f_["m"]}), S.BASE + f_["url"]])
    S.extra_sets = getattr(S, "extra_sets", []) + [("comissoes", "Comissões, CPIs e colegiados do Congresso", "Uma linha por órgão da Câmara e colegiado do Senado e do Congresso em atividade.", len(cam) + len(sen), "Dados Abertos da Câmara e do Senado", "https://dadosabertos.camara.leg.br/", "Seleção descrita em /comissoes/metodologia/.", col),
                                                  ("frentes", "Frentes parlamentares da 57ª legislatura", "Uma linha por frente parlamentar registrada na Câmara, com coordenador e número de deputados.", len(FR), "Dados Abertos da Câmara", "https://dadosabertos.camara.leg.br/", "Frentes com membros ativos na 57ª legislatura.", col)]
    return {"urls": urls}
