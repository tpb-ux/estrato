"""Partidos com bancada no Congresso: composição na Câmara e no Senado, por estado, e líder na Câmara."""
from core.site import E, slugify
from .dados import UF, PREP, MESES, brl, num, pct, data_br, load
from .parlamentares import plist

def build(S):
    P = load(S, "partidos.json"); C = load(S, "ceap.json"); deps, sens = S.parl["deps"], S.parl["sens"]
    meta = {p["sigla"]: p for p in P["partidos"]}
    siglas = sorted({d["partido"] for d in deps} | {s["partido"] for s in sens})
    tot = lambda d: d["c"]["total"]; ano, mes = C["ano"], C["ultimo_mes"]
    fonte = (f'<p class="src">Fonte: Câmara dos Deputados, <a href="https://dadosabertos.camara.leg.br/">API Dados Abertos</a> (/partidos e /deputados, coleta em {data_br(P["coletado_em"])}); '
             f'Senado Federal, <a href="https://legis.senado.leg.br/dadosabertos/">Dados Abertos</a>. Composição na data da coleta.</p>')
    rows = []
    rk_d = {sg: i + 1 for i, sg in enumerate(sorted(siglas, key=lambda g: -sum(1 for d in deps if d["partido"] == g)))}
    for sg in siglas:
        m = meta.get(sg, {}); nome = m.get("nome") or sg; u = f"/partidos/{slugify(sg)}/"
        dp = sorted([d for d in deps if d["partido"] == sg], key=lambda x: slugify(x["nome"])); sn = sorted([s for s in sens if s["partido"] == sg], key=lambda x: slugify(x["nome"]))
        rows.append((sg, nome, u, len(dp), len(sn)))
        ufs = {}
        for d in dp: ufs.setdefault(d["uf"], [0, 0])[0] += 1
        for s in sn: ufs.setdefault(s["uf"], [0, 0])[1] += 1
        td = sum(tot(d) for d in dp)
        lead = (f'<p class="snippet">O <strong>{E(nome)} ({E(sg)})</strong> tem <strong>{len(dp)} deputados federais</strong> ({pct(len(dp), len(deps))} da Câmara) e <strong>{len(sn)} senadores</strong> ({pct(len(sn), len(sens))} do Senado) em exercício, '
                f'com parlamentares em {len(ufs)} unidades da federação.' + (f' O líder na Câmara é {E(m["lider"])} ({E(m.get("lider_uf") or "")}).' if m.get("lider") else "") + "</p>")
        body = (f'<article class="post"><h1>{E(nome)} ({E(sg)}): bancada no Congresso</h1>{lead}<div class="stats"><div class="stat"><b>{len(dp)}</b><span>deputados</span></div><div class="stat"><b>{len(sn)}</b><span>senadores</span></div>'
                f'<div class="stat"><b>{len(ufs)}</b><span>estados com representantes</span></div>' + (f'<div class="stat"><b>{brl(td / len(dp))}</b><span>cota média por deputado em {ano}</span></div>' if dp else "") + "</div>"
                + f'<h2>O que o tamanho da bancada define</h2><p>Com {len(dp)} deputados, o {E(sg)} tem a {rk_d[sg]}ª maior bancada entre os {len(siglas)} partidos com representantes no Congresso. O tamanho da bancada define a proporção de vagas do partido nas comissões, o tempo de fala dos líderes e o número de destaques que podem ser apresentados nas votações. Bancadas mudam ao longo do mandato com trocas de partido nas janelas legais, licenças e posse de suplentes.</p>'
                + S.table(["Estado", "Deputados", "Senadores"], [[f'<a href="/deputados/uf/{uf.lower()}/">{UF[uf]}</a>', str(a), str(b)] for uf, (a, b) in sorted(ufs.items(), key=lambda x: (-x[1][0] - x[1][1], UF[x[0]]))], "Parlamentares por estado")
                + (f"<h2>Deputados federais do {E(sg)} ({len(dp)})</h2>{plist(S, dp, 'dep')}" if dp else "") + (f"<h2>Senadores do {E(sg)} ({len(sn)})</h2>{plist(S, sn, 'sen')}" if sn else "")
                + (f'<p>Somados, os deputados do {E(sg)} declararam {brl(td)} em cota parlamentar de janeiro a {MESES[mes]} de {ano}. Veja a <a href="/deputados/cota-parlamentar/">comparação geral</a>.</p>' if dp else "")
                + '<div class="relbox"><h2>Entenda</h2><ul><li><a href="/glossario/fundo-partidario/">Fundo Partidário</a></li><li><a href="/glossario/federacao-partidaria/">Federação partidária</a></li><li><a href="/glossario/clausula-de-desempenho/">Cláusula de desempenho</a></li><li><a href="/glossario/lider-partidario/">Líder partidário</a></li></ul></div>'
                + fonte + "</article>")
        maior = max(ufs.items(), key=lambda x: x[1][0] + x[1][1]) if ufs else None
        faqs = [(f"Quantos deputados o {sg} tem?", f"{len(dp)} deputados federais em exercício na data da coleta, {pct(len(dp), len(deps))} da Câmara."),
                (f"Quantos senadores o {sg} tem?", f"{len(sn)} senadores em exercício, {pct(len(sn), len(sens))} do Senado."),
                (f"Quem é o líder do {sg} na Câmara?", f"{E(m['lider'])}, segundo a API de Dados Abertos da Câmara." if m.get("lider") else "A API da Câmara não informa líder para o partido na data da coleta."),
                (f"Em qual estado o {sg} tem mais parlamentares?", f"{UF[maior[0]]}, com {maior[1][0]} deputados e {maior[1][1]} senadores." if maior else "Sem dados."),
                ("Os números mudam ao longo do mandato?", "Sim. Trocas de partido nas janelas permitidas, licenças e posse de suplentes alteram as bancadas. As páginas são atualizadas diariamente com os dados oficiais.")]
        S.write(u, S.page(f"{nome} ({sg}): deputados, senadores e bancada", f"Bancada do {nome} ({sg}) no Congresso: {len(dp)} deputados e {len(sn)} senadores em exercício, por estado, com dados oficiais da Câmara e do Senado.",
                          u, body, faqs=faqs, crumbs=[("Partidos", "/partidos/"), (sg, u)], jsonld={"@type": "PoliticalParty", "name": nome, "alternateName": sg, "url": S.BASE + u}), familia="partidos", lastmod=P["coletado_em"][:10])
    rows.sort(key=lambda r: (-(r[3] + r[4]), r[0]))
    body = (f'<section class="blk"><h1>Partidos com bancada no Congresso</h1><p class="snippet"><strong>{len(rows)} partidos</strong> têm deputados ou senadores em exercício na data da coleta ({data_br(P["coletado_em"])}).</p>'
            + '<p>A tabela mostra o tamanho de cada bancada na Câmara dos Deputados e no Senado Federal, do maior para o menor total. Cada página de partido traz a lista de parlamentares, a distribuição por estado e o líder na Câmara. Partidos que formam uma <a href="/glossario/federacao-partidaria/">federação</a> atuam juntos nas eleições e no Legislativo, mas aparecem aqui separadamente, como no cadastro oficial. O acesso ao Fundo Partidário depende da <a href="/glossario/clausula-de-desempenho/">cláusula de desempenho</a>, calculada a partir da eleição para a Câmara.</p>'
            + S.table(["Partido", "Deputados", "Senadores", "Total"], [[f'<a href="{u}">{E(sg)}</a> <small>{E(n)}</small>', str(a), str(b), str(a + b)] for sg, n, u, a, b in rows], "Bancadas por partido") + fonte + "</section>")
    faqs = [("Quantos partidos têm representantes no Congresso?", f"{len(rows)} partidos, na data da coleta."),
            ("Qual partido tem a maior bancada no Congresso?", f"O {E(rows[0][0])}, com {rows[0][3]} deputados e {rows[0][4]} senadores."),
            ("O que é federação partidária?", "É a união de partidos que atuam como um só por pelo menos quatro anos. Veja o verbete no glossário."),
            ("Os dados incluem partidos sem parlamentares?", "Não. Esta lista mostra só os partidos com deputados ou senadores em exercício."),
            ("Com que frequência a lista é atualizada?", "Diariamente, a partir das bases oficiais da Câmara e do Senado.")]
    S.write("/partidos/", S.page("Partidos no Congresso: bancadas na Câmara e no Senado", f"Os {len(rows)} partidos com deputados ou senadores em exercício e o tamanho de cada bancada, com dados oficiais da Câmara e do Senado.", "/partidos/", body,
                                 faqs=faqs, crumbs=[("Partidos", "/partidos/")], jsonld=S.itemlist([(r[0], r[2]) for r in rows])), familia="partidos", lastmod=P["coletado_em"][:10])
    return {"n": len(rows)}
