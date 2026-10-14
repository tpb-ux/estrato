"""/checagem/: estrutura e metodologia de checagem. Nenhuma checagem é publicada sem revisão humana: só entram arquivos de
data/checagens/*.yaml com aprovado: true e revisado_por preenchido. Com checagem publicada, a página leva ClaimReview."""
import yaml
from core.site import E, slugify
from .dados import data_br, num
ESCALA = [("verdadeiro", "Verdadeiro", "A alegação confere com os dados oficiais e o contexto está correto."),
          ("verdadeiro-sem-contexto", "Verdadeiro, mas sem contexto", "O dado existe, mas falta informação que muda a leitura."),
          ("exagerado", "Exagerado", "O número tem base real, mas foi aumentado ou diminuído de forma relevante."),
          ("impreciso", "Impreciso", "Mistura dados corretos e incorretos, ou usa período ou fonte diferentes dos citados."),
          ("falso", "Falso", "A alegação contradiz os dados oficiais disponíveis."),
          ("insustentavel", "Insustentável", "Não há dado público que permita confirmar ou negar a alegação.")]

def build(S):
    pub = []
    for f in sorted((S.ROOT / "data/checagens").glob("*.yaml")):
        c = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        if c.get("aprovado") is True and c.get("revisado_por") and c.get("classificacao") in {k for k, *_ in ESCALA}: c["slug"] = f.stem; pub.append(c)
    urls = []
    for c in pub:
        u = f"/checagem/{c['slug']}/"; nm = dict((k, n) for k, n, _ in ESCALA)[c["classificacao"]]
        b = (f'<article class="post"><h1>{E(c["titulo"])}</h1><p class="snippet"><strong>{E(nm)}.</strong> {E(c["resumo"])}</p><blockquote>{E(c["alegacao"])} — {E(c["autor_alegacao"])}, {data_br(str(c["data_alegacao"]))}</blockquote>'
             f'{c["texto"]}<h2>Fontes</h2><ul>' + "".join(f'<li><a href="{l}" target="_blank" rel="noopener">{E(n)}</a></li>' for n, l in c["fontes"]) + f'</ul><p class="src">Revisado por {E(c["revisado_por"])} em {data_br(str(c["data_revisao"]))}. <a href="/checagem/metodologia/">Metodologia</a>.</p></article>')
        ld = {"@type": "ClaimReview", "url": S.BASE + u, "claimReviewed": c["alegacao"], "datePublished": str(c["data_revisao"]), "author": {"@id": S.BASE + "/#org"},
              "itemReviewed": {"@type": "Claim", "author": {"@type": "Person", "name": c["autor_alegacao"]}, "datePublished": str(c["data_alegacao"]), "appearance": c.get("link_alegacao")},
              "reviewRating": {"@type": "Rating", "ratingValue": [k for k, *_ in ESCALA].index(c["classificacao"]) + 1, "bestRating": 1, "worstRating": len(ESCALA), "alternateName": nm}}
        S.write(u, S.page(f"{c['titulo']} | Checagem | {S.CFG['site_name']}", c["resumo"], u, b, crumbs=[("Checagem", "/checagem/"), (c["titulo"], u)], jsonld=ld, faqs=None), familia="checagem", faq_min=0); urls.append(u)
    esc = "".join(f'<li><strong>{E(n)}</strong>: {E(d)}</li>' for _, n, d in ESCALA)
    m = ('<article class="post"><h1>Metodologia de checagem do Estrato</h1><p class="snippet">Como o Estrato verifica alegações sobre os Três Poderes: só com dado oficial, com revisão humana obrigatória antes da publicação e com correção pública quando houver erro.</p>'
         '<h2>Etapas</h2><ol class="steps"><li>Seleção: alegações públicas sobre dados verificáveis (orçamento, votações, emendas, gastos, leis), feitas por autoridades ou com grande circulação.</li>'
         '<li>Pedido de fonte: quando possível, o autor da alegação é procurado para indicar a origem do dado.</li><li>Apuração: comparação com a fonte oficial primária (APIs da Câmara e do Senado, Portal da Transparência, Diário Oficial, TSE, tribunais), com o mesmo período e o mesmo recorte citados.</li>'
         '<li>Classificação: uso de uma das seis etiquetas da escala abaixo.</li><li>Revisão humana: um editor que não fez a apuração confere dados, contexto e etiqueta. Sem essa revisão, nada é publicado.</li><li>Publicação e correção: a checagem traz todas as fontes com link; erros são corrigidos e registrados na página de <a href="/correcoes/">correções</a>.</li></ol>'
         f'<h2>Escala</h2><ul>{esc}</ul><h2>O que não checamos</h2><ul><li>Opiniões, previsões e juízos de valor.</li><li>Até o fim do período eleitoral (26/10/2026), falas de candidatos e conteúdo de campanha.</li><li>Alegações sem dado público que permita verificação, salvo para registrá-las como insustentáveis.</li></ul>'
         '<h2>Independência</h2><p>As checagens seguem a <a href="/politica-editorial/">política editorial</a> do Estrato. Não há checagem encomendada nem patrocinada, e o mesmo critério vale para governo e oposição.</p></article>')
    S.write("/checagem/metodologia/", S.page(f"Metodologia de checagem | {S.CFG['site_name']}", "Etapas, escala e regras de revisão humana das checagens do Estrato.", "/checagem/metodologia/", m,
            faqs=[("Quem revisa as checagens?", "Um editor diferente de quem apurou. Sem revisão humana nada é publicado."), ("Quais fontes valem?", "Só fontes oficiais primárias, citadas com link."),
                  ("Qual é a escala?", ", ".join(n for _, n, _ in ESCALA) + "."), ("O Estrato checa candidatos?", "Não até o fim do período eleitoral, em 26/10/2026."), ("Como corrigir uma checagem?", 'Pela página de <a href="/correcoes/">correções</a>.')],
            crumbs=[("Checagem", "/checagem/"), ("Metodologia", "/checagem/metodologia/")]), familia="paginas")
    h = ('<section class="blk"><h1>Checagem</h1><p class="lead">Verificação de alegações públicas sobre orçamento, votações, emendas e gastos, com dados oficiais e revisão humana obrigatória.</p>'
         + ("<ul>" + "".join(f'<li><a href="/checagem/{c["slug"]}/">{E(c["titulo"])}</a></li>' for c in pub) + "</ul>" if pub else '<p class="vazio">Ainda não há checagens publicadas. A seção abre quando a primeira passar pela revisão humana.</p>')
         + '<p>Leia a <a href="/checagem/metodologia/">metodologia</a>.</p></section>')
    S.write("/checagem/", S.page(f"Checagem | {S.CFG['site_name']}", "Checagens do Estrato com dados oficiais e revisão humana.", "/checagem/", h,
            faqs=[("Há checagens publicadas?", f"{num(len(pub))} nesta atualização."), ("Como é feita a checagem?", 'Veja a <a href="/checagem/metodologia/">metodologia</a>.'), ("Checagens usam IA?", "A apuração pode usar ferramentas, mas classificação e publicação dependem de revisão humana."),
                  ("Posso sugerir uma checagem?", 'Sim, pela página de <a href="/contato/">contato</a>.'), ("Onde vejo correções?", 'Na página de <a href="/correcoes/">correções</a>.')], crumbs=[("Checagem", "/checagem/")]), idx=bool(pub))
    return {"urls": urls}
