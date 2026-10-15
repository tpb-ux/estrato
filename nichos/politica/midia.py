"""Mapa da Midia ("quem manda em quem"): base factual de propriedade e vinculos dos veiculos de comunicacao.
Dados: data/midia/base.yaml (entidades e afirmacoes com fonte e trecho) + data/midia/verificacao.json (tools/datasets_midia.py: data e revisao da fonte).
Paginas: /midia/ (hub com grafico SVG), /midia/veiculos/, /midia/grupos/, /midia/acionistas/ (hubs), uma pagina por entidade (familia `midia`, noindex ate a onda propria) e /midia/metodologia/ (RASCUNHO, noindex ate revisao humana/juridica).
Regras: so fatos documentados com fonte e data; verbos neutros (detem, controla, pertence a); o que nao foi achado aparece como "nao verificado".
Vies (esquerda/direita), nivel de confianca e historico de posicao ficam no esquema (campos vies, confianca, historico de cada entidade) mas DESLIGADOS: config midia.vies_ativo e so vale a partir de midia.liberar_em."""
import csv, datetime as dt, json, collections
import yaml
from core.site import E
from .dados import data_br, num

TIPOS = {"veiculo": ("veiculos", "Veículos"), "grupo": ("grupos", "Grupos e empresas"), "pessoa": ("acionistas", "Pessoas e famílias")}
CAMADA = {"pessoa": 0, "grupo": 1, "veiculo": 2}
TITULAR_E_SUJEITO = {"deteve participação em", "é proprietário de"}   # nessas relacoes quem detem e o sujeito da afirmacao
SETOR_OUTRO = ("Banco", "financeir", "Telecom", "Gás", "Energia", "empresarial")
NAOVER_PUB = "Publicidade oficial e patrocínio: não verificado. A base ainda não inclui dados documentados de verbas publicitárias de governos nem de patrocinadores deste veículo."


def url_e(k, e): return f"/midia/{TIPOS[e['tipo']][0]}/{k}/"
def lk(k, EN): return f'<a href="{url_e(k, EN[k])}">{E(EN[k]["nome"])}</a>'


def carregar(S):
    b = yaml.safe_load((S.ROOT / "data/midia/base.yaml").read_text(encoding="utf-8"))
    f = S.ROOT / "data/midia/verificacao.json"
    v = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"gerado": "", "fontes": {}, "afirmacoes": []}
    return b, v


def vies_ativo(S):
    c = S.CFG.get("midia") or {}
    lib = str(c.get("liberar_em") or "9999-12-31")[:10]
    return bool(c.get("vies_ativo")) and dt.date.today().isoformat() >= lib


def build(S):
    f = S.ROOT / "data/midia/base.yaml"
    if not f.exists(): return {"urls": []}
    B, V = carregar(S); EN = B["entidades"]; site = S.CFG["site_name"]; col = V.get("gerado") or dt.date.today().isoformat(); urls = []
    ativo = vies_ativo(S)
    ver = V.get("afirmacoes") or []; fontes = V.get("fontes") or {}
    A = []
    for i, a in enumerate(B["afirmacoes"]):
        r = ver[i] if len(ver) == len(B["afirmacoes"]) else {}
        fo = fontes.get(a["w"]) or {}
        A.append(dict(a, ok=bool(r.get("ok")), data=r.get("data"), revid=r.get("revid"), ftit=fo.get("titulo") or a["w"], furl=fo.get("url"), perm=fo.get("perm")))
    OK = [a for a in A if a["ok"]]
    # arestas titular -> detido (so afirmacoes verificadas)
    arestas = []
    for a in OK:
        if not a["o"]: continue
        t, d = (a["s"], a["o"]) if a["r"] in TITULAR_E_SUJEITO else (a["o"], a["s"])
        arestas.append((t, d, a))
    acima = collections.defaultdict(list); abaixo = collections.defaultdict(list)
    for t, d, a in arestas: acima[d].append((t, a)); abaixo[t].append((d, a))

    def subir(k, vistos=None):
        vistos = vistos if vistos is not None else []
        for t, _ in acima.get(k, []):
            if t not in vistos and t != k: vistos.append(t); subir(t, vistos)
        return vistos
    def descer(k, vistos=None):
        vistos = vistos if vistos is not None else []
        for d, _ in abaixo.get(k, []):
            if d not in vistos and d != k: vistos.append(d); descer(d, vistos)
        return vistos

    def fonte_html(a): return f'<a href="{E(a["perm"] or a["furl"] or "#")}" target="_blank" rel="noopener">Wikipédia: {E(a["ftit"])}</a>' + (f' (revisão {a["revid"]})' if a["revid"] else "")
    def verif_html(a): return f'Verificado em {data_br(a["data"])}' if a["ok"] else "Não verificado"
    def frase(a):
        s, o = a["s"], a["o"]
        return f'{lk(s, EN)} {E(a["r"])} {lk(o, EN)}' if o else f'{lk(s, EN)} {E(a["r"])}'
    def tab_claims(L):
        return S.table(["Afirmação documentada", "Fonte", "Verificação"], [[E(a["t"]), fonte_html(a), verif_html(a)] for a in L], "Cada afirmação cita a fonte e a data em que o trecho foi localizado na revisão indicada")
    aviso = ('<aside class="mm-aviso"><strong>Encontrou erro ou quer responder?</strong> Todas as afirmações desta página têm fonte e data de verificação. '
             'Para pedir correção, use a página de <a href="/correcoes/">correções</a>; para exercer direito de resposta, veja <a href="/direito-de-resposta/">direito de resposta</a>. '
             'Metodologia (rascunho em revisão): <a href="/midia/metodologia/">como a base é montada</a>.</aside>')
    q = S.CFG.setdefault("qualidade", {}).setdefault("faq_pseo", {}); ex = q.setdefault("hubs_exatos", [])
    ex.extend(["/midia/", "/midia/veiculos/", "/midia/grupos/", "/midia/acionistas/", "/midia/metodologia/"])
    nv = sum(1 for e in EN.values() if e["tipo"] == "veiculo"); ng = sum(1 for e in EN.values() if e["tipo"] == "grupo"); npess = sum(1 for e in EN.values() if e["tipo"] == "pessoa")
    n_ok = len(OK); n_no = len(A) - n_ok

    # ---------- paginas por entidade ----------
    def vies_bloco(k):
        if not ativo: return ""
        e = EN[k]; h = e.get("historico") or []
        return ("<h2>Classificação editorial</h2>" + S.table(["Critério", "Valor"], [["Posição (critérios da metodologia)", E(str(e.get("vies") or "não classificado"))], ["Nível de confiança da classificação", E(str(e.get("confianca") or "não classificado"))]], "Conforme metodologia aprovada")
                + ("<h3>Histórico de mudanças</h3><ul>" + "".join(f'<li>{E(str(x))}</li>' for x in h) + "</ul>" if h else ""))
    for k, e in EN.items():
        tp = e["tipo"]; u = url_e(k, e); nome = e["nome"]
        prop = [a for a in OK if a["s"] == k or a["o"] == k]
        nao = [a for a in A if (a["s"] == k or a["o"] == k) and not a["ok"]]
        cima = subir(k); baixo = descer(k)
        body = f'<article class="post"><h1>{E(nome)}: {"quem é o dono e vínculos societários" if tp == "veiculo" else ("propriedade, controle e veículos ligados" if tp == "grupo" else "veículos e empresas ligados")}</h1>'
        direto = [(t, a) for t, a in acima.get(k, [])]
        if tp == "veiculo":
            if direto:
                cad = "; ".join(frase(a) for _, a in direto[:3])
                body += f'<p class="snippet">Vínculo de propriedade documentado: {cad}.' + (f' Subindo a cadeia, constam ainda {", ".join(lk(x, EN) for x in cima[len(direto):][:5])}.' if len(cima) > len(direto) else "") + f' Fonte e data de verificação abaixo; o que não foi encontrado aparece como "não verificado".</p>'
            else:
                body += f'<p class="snippet">A base do Estrato ainda não tem afirmação verificada sobre a propriedade de <strong>{E(nome)}</strong>. Controlador, acionistas e grupo econômico: <strong>não verificado</strong>.</p>'
        else:
            n_det = len(baixo)
            body += (f'<p class="snippet"><strong>{E(nome)}</strong> aparece na base com {len(prop)} afirmação(ões) verificada(s)'
                     + (f' e {n_det} entidade(s) ligada(s) a jusante (veículos, empresas)' if n_det else "") + (f', e {len(cima)} titular(es) a montante' if cima else "") + f'. Cada afirmação cita a fonte e a data da verificação; lacunas aparecem como "não verificado".</p>')
        meta = [["Tipo", {"veiculo": "Veículo de comunicação", "grupo": "Grupo ou empresa", "pessoa": "Pessoa ou família"}[tp]]]
        if e.get("formato"): meta.append(["Formato", E(e["formato"])])
        if e.get("setor"): meta.append(["Setor", E(e["setor"])])
        if tp == "veiculo": meta.append(["Feed lido pelo Estrato", "Sim: o Estrato lê o feed público deste veículo para a seção de notícias, sem vínculo comercial" if e.get("in_feeds") else "Não"])
        body += "<h2>Ficha</h2>" + S.table(["Campo", "Dado"], meta)
        if prop: body += "<h2>Afirmações verificadas</h2>" + tab_claims(prop)
        if cima:
            body += "<h2>Quem detém ou controla (cadeia documentada)</h2><ul>" + "".join(f'<li>{lk(x, EN)}' + (f' ({E(EN[x]["setor"])})' if EN[x].get("setor") else "") + "</li>" for x in cima) + "</ul>"
        if baixo:
            body += "<h2>Veículos e empresas ligados</h2><ul>" + "".join(f'<li>{lk(x, EN)} <small>({TIPOS[EN[x]["tipo"]][1].lower()})</small></li>' for x in baixo) + "</ul>"
        if tp == "veiculo" and cima:
            irmaos = []
            for t in cima:
                for d in descer(t):
                    if d != k and d not in cima and d not in irmaos and d not in baixo: irmaos.append(d)
            if irmaos: body += "<h2>Outros veículos e empresas dos mesmos titulares</h2><p>Segundo a base, os titulares acima também detêm ou controlam: " + ", ".join(lk(x, EN) for x in irmaos[:20]) + ".</p>"
            outros = [(x, EN[x]["setor"]) for x in cima if any(w in (EN[x].get("setor") or "") for w in SETOR_OUTRO)]
            if outros:
                body += ("<h2>Setores de atuação dos titulares</h2>" + S.table(["Titular documentado", "Setor"], [[lk(x, EN), E(s)] for x, s in outros], "Dado de propriedade; não indica, por si, influência sobre o conteúdo editorial")
                         + "<p>A tabela mostra apenas o setor econômico em que o titular atua, para que o leitor saiba de quem se trata. Um vínculo societário não prova interferência editorial, e o Estrato não faz essa afirmação.</p>")
        if tp == "veiculo":
            body += f'<h2>Publicidade, patrocínio e vínculos com governos</h2><p>{NAOVER_PUB} Vínculo com governos: ' + ("documentado acima, pois a fonte descreve controle ou gestão pública." if any("pública" in (EN[x].get("setor") or "") for x in cima) else "não verificado.") + "</p>"
        if nao: body += "<h2>Não verificado</h2>" + tab_claims(nao) + "<p>O trecho citado não foi localizado na revisão atual da fonte; a afirmação não é usada no mapa até nova verificação.</p>"
        body += vies_bloco(k) + aviso
        fontes_u = {}
        for a in prop: fontes_u[a["w"]] = a
        body += '<p class="src">Fontes: ' + (" · ".join(fonte_html(a) for a in fontes_u.values()) or "nenhuma verificada") + f'. Compilação em {data_br(col)}. <a href="/midia/">Mapa da Mídia</a> · <a href="/midia/{TIPOS[tp][0]}/">{TIPOS[tp][1]}</a> · <a href="/midia/metodologia/">Metodologia</a>.</p></article>'
        fa = [(f"Quem é o dono de {nome}?" if tp == "veiculo" else f"O que {nome} detém ou controla na base?",
               (f"Segundo a fonte citada, {frase(direto[0][1])}. Veja a data de verificação na tabela." if direto else f"Não verificado: a base não tem afirmação verificada sobre isso.") if tp == "veiculo" else (f"Constam {len(baixo)} entidade(s) ligada(s): " + ", ".join(lk(x, EN) for x in baixo[:6]) + "." if baixo else "Nenhuma entidade ligada foi verificada.")),
              ("De onde vêm as informações?", "De artigos da Wikipédia em português com revisão identificada, conferidos por trecho, com a data da verificação. Registros oficiais (CVM, Receita Federal) entram quando houver fonte aberta citável."),
              ("Posso pedir correção ou responder?", 'Sim, pela página de <a href="/correcoes/">correções</a> e de <a href="/direito-de-resposta/">direito de resposta</a>.')]
        ld = {"@type": "NewsMediaOrganization" if tp == "veiculo" else ("Organization" if tp == "grupo" else "Person"), "name": nome, "url": S.BASE + u}
        if prop and prop[0]["furl"]: ld["sameAs"] = [prop[0]["furl"]]
        S.write(u, S.page({"veiculo": f"{nome}: dono e vínculos (Mapa da Mídia)", "grupo": f"{nome}: o que detém (Mapa da Mídia)", "pessoa": f"{nome}: veículos ligados (Mapa da Mídia)"}[tp] + f" | {site}",
                          f"{nome} no Mapa da Mídia do Estrato: propriedade, controle e vínculos documentados, com fonte e data de verificação por afirmação. O que não foi achado aparece como não verificado.", u, body, faqs=fa,
                          crumbs=[("Mapa da Mídia", "/midia/"), (TIPOS[tp][1], f"/midia/{TIPOS[tp][0]}/"), (nome, u)], jsonld=ld), familia="midia", lastmod=col); urls.append(u)

    # ---------- grafico SVG ----------
    nos = {k for t, d, _ in arestas for k in (t, d)}
    cols = {0: [], 1: [], 2: []}
    for k in EN:
        if k in nos: cols[CAMADA[EN[k]["tipo"]]].append(k)
    pos = {}
    def ordena(c, ref):
        def bari(k):
            vs = [pos[x] for x in set([t for t, _ in acima.get(k, [])] + [d for d, _ in abaixo.get(k, [])]) if x in pos]
            return sum(vs) / len(vs) if vs else 0.5
        cols[c].sort(key=bari)
        for i, k in enumerate(cols[c]): pos[k] = i / max(1, len(cols[c]) - 1)
    for k in cols[0]: pos[k] = cols[0].index(k) / max(1, len(cols[0]) - 1)
    for c in (1, 2, 0, 1, 2): ordena(c, None)
    GAP = 24; H = max(len(v) for v in cols.values()) * GAP + 20; X = {0: 8, 1: 372, 2: 736}; Wn = 256; Y = {}
    for c, L in cols.items():
        passo = (H - 20) / max(1, len(L)) if len(L) > 1 else GAP
        for i, k in enumerate(L): Y[k] = 10 + i * passo + passo / 2 if len(L) * GAP < H else 10 + i * GAP + GAP / 2
    cor = {0: "#8a5a00", 1: "#1f4e79", 2: "#2f6f4f"}
    svg = [f'<svg class="mm-svg" viewBox="0 0 1000 {H}" role="img" aria-labelledby="mmt" xmlns="http://www.w3.org/2000/svg"><title id="mmt">Vínculos de propriedade documentados entre pessoas, grupos e veículos</title>']
    for t, d, a in arestas:
        ct, cd = CAMADA[EN[t]["tipo"]], CAMADA[EN[d]["tipo"]]
        if ct < cd: x1, x2 = X[ct] + Wn, X[cd]; m = (x1 + x2) / 2; p = f"M{x1},{Y[t]:.0f} C{m},{Y[t]:.0f} {m},{Y[d]:.0f} {x2},{Y[d]:.0f}"; dash = ""
        elif ct > cd: x1, x2 = X[ct], X[cd] + Wn; m = (x1 + x2) / 2; p = f"M{x1},{Y[t]:.0f} C{m},{Y[t]:.0f} {m},{Y[d]:.0f} {x2},{Y[d]:.0f}"; dash = ""
        else: x1 = X[ct] + Wn; p = f"M{x1},{Y[t]:.0f} C{x1 + 60},{Y[t]:.0f} {x1 + 60},{Y[d]:.0f} {x1},{Y[d]:.0f}"; dash = ' stroke-dasharray="4 3"'
        svg.append(f'<path d="{p}" fill="none" stroke="#9aa5b1" stroke-width="1.2" opacity=".75"{dash}><title>{E(EN[t]["nome"])} → {E(EN[d]["nome"])}: {E(a["r"])}</title></path>')
    for c, L in cols.items():
        for k in L:
            nm = EN[k]["nome"]; cur = nm if len(nm) <= 38 else nm[:37] + "…"
            svg.append(f'<a href="{url_e(k, EN[k])}"><rect x="{X[c]}" y="{Y[k] - 10:.0f}" width="{Wn}" height="20" rx="4" fill="{cor[c]}" opacity=".12" stroke="{cor[c]}"/><text x="{X[c] + 8}" y="{Y[k] + 4:.0f}" font-size="11.5" fill="#1a1a1a">{E(cur)}<title>{E(nm)}</title></text></a>')
    svg.append("</svg>")
    leg = '<p class="mm-leg"><span style="color:#8a5a00">■</span> Pessoas e famílias &nbsp; <span style="color:#1f4e79">■</span> Grupos e empresas &nbsp; <span style="color:#2f6f4f">■</span> Veículos &nbsp; Linhas: vínculo documentado, do titular ao detido (tracejadas: entre empresas). Passe o mouse para ver a relação; clique para abrir a página.</p>'
    isol = [k for k, e in EN.items() if e["tipo"] == "veiculo" and k not in nos]

    # ---------- tabela geral de vinculos ----------
    tab_vinc = S.table(["Vínculo documentado", "Fonte", "Verificado em"], [[frase(a), fonte_html(a), data_br(a["data"])] for _, _, a in arestas], "Todos os vínculos entre entidades com afirmação verificada")

    # ---------- hubs ----------
    def faq_comuns(extra):
        return extra + [("O Estrato classifica veículos como de esquerda ou de direita?", "Não por enquanto. O esquema de dados prevê posição editorial, nível de confiança e histórico de mudanças, mas esses campos estão desligados até 26/10/2026 e dependem de metodologia com critérios objetivos, revisada por pessoas e por assessoria jurídica."),
                        ("Como o Estrato verifica cada afirmação?", "Cada afirmação cita um artigo da Wikipédia em português com a revisão identificada. Uma rotina procura o trecho citado no texto da revisão atual e registra a data; se não encontrar, a afirmação aparece como não verificada."),
                        ("O que significa “não verificado”?", "Que a base não encontrou fonte aberta que sustente o dado nesta data. Não significa que o dado seja falso nem que seja verdadeiro."),
                        ("Posso pedir correção ou exercer direito de resposta?", 'Sim. Use a página de <a href="/correcoes/">correções</a> ou a de <a href="/direito-de-resposta/">direito de resposta</a>. Correções confirmadas são feitas e registradas.'),
                        ("O mapa mostra patrocinadores e verbas de publicidade?", "Ainda não. Só entram dados com fonte aberta citável e verificada; patrocínio e publicidade oficial estão como não verificados até haver base documentada.")]
    nome_c = lambda L: ", ".join(E(EN[x]["nome"]) for x in L)
    # hub principal
    corpo = (f'<article class="post"><h1>Mapa da Mídia: quem é dono de quem no jornalismo brasileiro</h1>'
             f'<p class="snippet">O Mapa da Mídia reúne, com fonte e data de verificação, quem detém, controla ou administra {num(nv)} veículos de comunicação, {num(ng)} grupos e empresas e {num(npess)} pessoas e famílias. '
             f'São {num(n_ok)} afirmações verificadas em {len(fontes)} fontes; {num(n_no)} aparecem como não verificadas. Só fatos documentados, sem acusação nem juízo de valor.</p>'
             '<h2>Como ler o mapa</h2><p>O gráfico liga pessoas e famílias (à esquerda) a grupos e empresas (centro) e a veículos (à direita). Cada linha é um vínculo de propriedade, controle ou administração com fonte. '
             'Os verbos são neutros: detém, controla, pertence a, é administrada por. Onde a base não encontrou fonte, a página diz “não verificado”.</p>'
             + "".join(svg) + leg +
             f'<p>Veículos ainda sem vínculo verificado na base: {nome_c(isol) if isol else "nenhum"}.</p>'
             '<h2>Veículos, grupos e pessoas</h2><ul>' + "".join(f'<li><a href="/midia/{TIPOS[t][0]}/">{TIPOS[t][1]}</a>: {n}</li>' for t, n in (("veiculo", nv), ("grupo", ng), ("pessoa", npess))) + '</ul>'
             '<h2>Todos os vínculos documentados</h2>' + tab_vinc +
             '<h2>Classificação editorial, confiança e histórico</h2><p>Estão previstos no esquema de dados, mas <strong>desligados</strong>: dependem de metodologia com critérios objetivos e auditáveis, ainda em revisão humana e jurídica. Veja o <a href="/midia/metodologia/">rascunho da metodologia</a>.</p>'
             + aviso + f'<p class="src">Fontes: artigos da Wikipédia em português com revisão identificada. Última verificação: {data_br(col)}. Dados abertos: <a href="/dados/midia-afirmacoes.csv">midia-afirmacoes.csv</a>.</p></article>')
    fa = faq_comuns([("O que é o Mapa da Mídia do Estrato?", f"Uma base aberta de propriedade e vínculos de {num(nv)} veículos de comunicação, com fonte e data por afirmação, para o leitor saber quem está por trás de cada veículo."),
                     ("Quem manda em quem na mídia brasileira?", "O mapa mostra os vínculos documentados: por exemplo, o Grupo Globo, de propriedade da Família Marinho, e a Exame, que pertence à Editora e Comércio Valongo, administrada pelo BTG Pactual Holding. Cada vínculo tem sua fonte nas páginas dos veículos.")])
    ld = {"@type": "Dataset", "name": "Mapa da Mídia: propriedade e vínculos de veículos de comunicação", "url": S.BASE + "/midia/", "isAccessibleForFree": True, "inLanguage": "pt-BR", "dateModified": col}
    S.write("/midia/", S.page(f"Mapa da Mídia: quem é dono de quem | {site}", f"Quem detém, controla e administra {nv} veículos de comunicação do Brasil, com fonte e data de verificação por afirmação. Só fatos documentados.", "/midia/", corpo, faqs=fa, crumbs=[("Mapa da Mídia", "/midia/")], jsonld=ld), familia="paginas", lastmod=col); urls.append("/midia/")
    # hubs por tipo
    for tp, (sl, rot) in TIPOS.items():
        L = sorted((k for k, e in EN.items() if e["tipo"] == tp), key=lambda k: EN[k]["nome"].lower()); rows = []
        for k in L:
            e = EN[k]; dono = ", ".join(lk(t, EN) for t, _ in acima.get(k, [])[:3]) or "não verificado"
            nc = sum(1 for a in OK if a["s"] == k or a["o"] == k)
            if tp == "veiculo": rows.append([lk(k, EN), E(e.get("formato", "")), dono, "Sim" if e.get("in_feeds") else "Não", str(nc)])
            elif tp == "grupo": rows.append([lk(k, EN), E(e.get("setor", "")), dono, str(len(descer(k))), str(nc)])
            else: rows.append([lk(k, EN), ", ".join(lk(x, EN) for x in descer(k)[:6]) or "—", str(nc)])
        head = {"veiculo": ["Veículo", "Formato", "Dono ou controlador documentado", "Feed lido pelo Estrato", "Afirmações verificadas"], "grupo": ["Grupo ou empresa", "Setor", "Titular documentado", "Entidades ligadas", "Afirmações verificadas"], "pessoa": ["Pessoa ou família", "Veículos e empresas ligados", "Afirmações verificadas"]}[tp]
        corpo = (f'<article class="post"><h1>{rot} no Mapa da Mídia</h1><p class="snippet">Lista de {num(len(L))} {rot.lower()} do Mapa da Mídia do Estrato, com o titular documentado e o número de afirmações verificadas. Cada nome leva à página com fontes e datas; o que não foi encontrado consta como “não verificado”.</p>'
                 + S.table(head, rows, f"{rot}: dados verificados em {data_br(col)}") + aviso + '<p class="src"><a href="/midia/">Mapa da Mídia</a> · <a href="/midia/metodologia/">Metodologia (rascunho)</a>.</p></article>')
        fa = faq_comuns([(f"O que aparece na lista de {rot.lower()}?", f"{num(len(L))} entradas, com titular documentado e contagem de afirmações verificadas por entrada."),
                         ("A lista é completa?", "Não. A primeira base cobre os maiores veículos e os que o Estrato já lê nos feeds. Novos veículos entram conforme houver fonte verificável.")])
        S.write(f"/midia/{sl}/", S.page(f"{rot} no Mapa da Mídia | {site}", f"{num(len(L))} {rot.lower()} do Mapa da Mídia do Estrato, com titular documentado, fonte e data de verificação. Dados abertos e sem juízo de valor.", f"/midia/{sl}/", corpo, faqs=fa, crumbs=[("Mapa da Mídia", "/midia/"), (rot, f"/midia/{sl}/")]), familia="paginas", lastmod=col); urls.append(f"/midia/{sl}/")
    # metodologia (RASCUNHO)
    c = S.CFG.get("midia") or {}
    corpo = ('<article class="post"><h1>Mapa da Mídia: metodologia (rascunho em revisão)</h1>'
             '<aside class="mm-aviso mm-rev"><strong>Rascunho em revisão humana e jurídica.</strong> Esta página ainda não foi aprovada, não é indexada e não vale como política publicada. Os critérios de viés, confiança e histórico abaixo são propostas e permanecem desligados.</aside>'
             '<p class="snippet">O Mapa da Mídia publica só fatos documentados sobre propriedade, controle e vínculos de veículos de comunicação, cada um com fonte, revisão da fonte e data de verificação. Não publica acusações, opiniões nem inferências sobre intenção.</p>'
             '<h2>Objetivo</h2><p>Informar o leitor sobre quem está por trás de cada veículo, com critérios iguais para todos e dados auditáveis por terceiros.</p>'
             '<h2>O que entra</h2><ul><li>Proprietário, controlador, acionistas e grupo econômico, quando constam de fonte aberta citável.</li><li>Empresas ligadas aos mesmos titulares, também com fonte.</li><li>Patrocínio e publicidade, apenas quando houver dado documentado (hoje: não verificado).</li><li>Vínculos com governos, apenas quando a fonte descrever controle ou gestão pública.</li></ul>'
             '<h2>O que não entra</h2><ul><li>Acusações, suspeitas, alegações não decididas e inferências sobre intenção.</li><li>Dados pessoais sensíveis, patrimônio declarado ao TSE e vida privada.</li><li>Opinião do Estrato sobre qualidade ou linha editorial dos veículos.</li></ul>'
             '<h2>Hierarquia de fontes</h2><ol><li>Registros oficiais abertos: CVM e relações com investidores, Receita Federal (CNPJ, quadro societário), diários oficiais.</li><li>Sites institucionais dos próprios grupos.</li><li>Wikipédia e Wikidata, sempre com a revisão identificada.</li><li>Reportagens citadas, com veículo, data e link.</li></ol>'
             '<p>Na primeira base, todas as afirmações vêm da Wikipédia em português, porque a Receita Federal, a CVM e vários sites oficiais bloqueiam o acesso automatizado a partir do ambiente do Estrato. A troca por fonte primária é a próxima etapa.</p>'
             '<h2>Como cada afirmação é verificada</h2><ol><li>A afirmação é escrita com verbo neutro e liga duas entidades.</li><li>Guarda-se um trecho literal da fonte.</li><li>Uma rotina procura o trecho na revisão atual do artigo e grava a data e o número da revisão.</li><li>Se o trecho não for achado, a afirmação passa a “não verificado” e sai do gráfico.</li></ol>'
             '<h2>Verbos permitidos</h2><p>Detém, controla, pertence a, é administrada por, é presidida por, é financiada por, patrocinado por (só com documento). Não se usam termos como “dono oculto”, “manipula” ou “alinhado a”.</p>'
             '<h2>Critérios propostos (desligados)</h2><ul><li><strong>Posição editorial:</strong> só a partir de linha editorial publicada pelo próprio veículo e de ao menos duas classificações independentes citadas (estudos acadêmicos ou observatórios), sem opinião da equipe. Escala e fontes serão listadas por veículo.</li>'
             '<li><strong>Nível de confiança:</strong> mede a completude e a qualidade das fontes da base sobre aquele veículo (quantas afirmações, de que hierarquia, quão recentes). Não mede a qualidade do jornalismo.</li>'
             '<li><strong>Histórico:</strong> mudanças de propriedade ou de posição, cada uma com data e fonte.</li></ul>'
             f'<p>Chave de configuração: <code>midia.vies_ativo</code> (hoje {"ligada" if c.get("vies_ativo") else "desligada"}); mesmo ligada, só vale a partir de <code>midia.liberar_em</code> ({E(str(c.get("liberar_em", "26/10/2026")))}).</p>'
             '<h2>Para revisão humana e jurídica</h2><ul><li>Texto dos avisos e verbos neutros.</li><li>Critérios e escala de posição editorial.</li><li>Prazo e rito de resposta a pedidos de correção.</li><li>Se pessoas físicas (acionistas) podem aparecer com nome, e com que limites.</li></ul>'
             '<h2>Correção e direito de resposta</h2><p>Toda página tem aviso com link para <a href="/correcoes/">correções</a> e <a href="/direito-de-resposta/">direito de resposta</a>. Correções confirmadas são feitas e registradas.</p>'
             f'<p class="src">Última verificação das fontes: {data_br(col)}. <a href="/midia/">Voltar ao Mapa da Mídia</a>.</p></article>')
    fa = faq_comuns([("Por que a metodologia está em rascunho?", "Porque envolve critérios sobre pessoas e empresas e precisa de revisão humana e jurídica antes de valer como política publicada."),
                     ("Quem aprova os critérios?", "A direção editorial do Estrato, depois de revisão jurídica. Até lá, os campos de viés, confiança e histórico ficam desligados.")])
    S.write("/midia/metodologia/", S.page(f"Mapa da Mídia: metodologia (rascunho) | {site}", "Rascunho da metodologia do Mapa da Mídia: fontes, verificação por trecho, verbos neutros e critérios propostos, em revisão humana e jurídica.", "/midia/metodologia/", corpo, faqs=fa, crumbs=[("Mapa da Mídia", "/midia/"), ("Metodologia", "/midia/metodologia/")]), idx=False, familia="paginas", lastmod=col); urls.append("/midia/metodologia/")
    # CSV
    out = S.OUT / "dados"; out.mkdir(parents=True, exist_ok=True)
    with (out / "midia-afirmacoes.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh); w.writerow(["entidade", "tipo_entidade", "relacao", "objeto", "afirmacao", "fonte", "fonte_url", "fonte_revisao_url", "revisao", "verificado_em", "verificado"])
        for a in A: w.writerow([EN[a["s"]]["nome"], EN[a["s"]]["tipo"], a["r"], EN[a["o"]]["nome"] if a["o"] else "", a["t"], "Wikipédia: " + a["ftit"], a["furl"] or "", a["perm"] or "", a["revid"] or "", a["data"] or "", "sim" if a["ok"] else "não verificado"])
    S.extra_sets = getattr(S, "extra_sets", []) + [("midia-afirmacoes", "Mapa da Mídia: afirmações verificadas", "Uma linha por afirmação sobre propriedade e vínculos de veículos de comunicação, com fonte, revisão e data de verificação.", len(A), "Wikipédia em português (revisão identificada por afirmação)", "https://pt.wikipedia.org/", "Trecho literal da fonte procurado na revisão atual; sem achado = não verificado.", col)]
    S.midia_stats = {"veiculos": nv, "grupos": ng, "pessoas": npess, "afirmacoes": len(A), "verificadas": n_ok, "paginas": len(urls)}
    return {"urls": urls}
