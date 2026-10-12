"""/dados/: arquivos CSV com os dados que alimentam as páginas (deputados, cota parlamentar, senadores), com fonte,
método e licença. Os dados originais são públicos (Lei de Acesso à Informação / Dados Abertos da Câmara e do Senado)."""
import csv, json
from core.site import E
from .dados import load, data_br

LIC = ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/deed.pt-br")

def _csv(path, head, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(head); w.writerows(rows)
    return len(rows)

def build(S):
    D = load(S, "deputados.json"); SN = load(S, "senadores.json"); C = load(S, "ceap.json"); out = S.OUT / "dados"; sets = []
    deps = {str(d["id"]): d for d in D["deputados"]}
    n = _csv(out / "deputados.csv", ["id_camara", "nome", "partido", "uf", "sexo", "escolaridade", "situacao", "url_camara"],
             [[d["id"], d["nome"], d["partido"], d["uf"], d.get("sexo", ""), d.get("escolaridade", ""), d.get("situacao", ""), f"https://www.camara.leg.br/deputados/{d['id']}"] for d in D["deputados"]])
    sets.append(("deputados", "Deputados federais em exercício", "Lista dos deputados em exercício com partido, UF e dados cadastrais públicos.", n, "API de Dados Abertos da Câmara dos Deputados", "https://dadosabertos.camara.leg.br/",
                 "Coleta diária da API oficial (deputados em exercício na legislatura atual).", D["coletado_em"][:10]))
    rows = []
    for i, v in sorted(C["deputados"].items(), key=lambda x: -x[1]["total"]):
        d = deps.get(str(i), {})
        for cat, val in sorted(v["por_categoria"].items(), key=lambda x: -x[1]):
            rows.append([C["ano"], C["ultimo_mes"], i, d.get("nome", ""), d.get("partido", ""), d.get("uf", ""), cat, round(val, 2)])
    n = _csv(out / "cota-parlamentar-categorias.csv", ["ano", "ate_mes", "id_camara", "nome", "partido", "uf", "categoria", "valor_liquido_r"], rows)
    sets.append(("cota-parlamentar-categorias", f"Cota parlamentar (CEAP) {C['ano']} por deputado e categoria", f"Gasto líquido da cota parlamentar por deputado e categoria de despesa em {C['ano']}, até o mês {C['ultimo_mes']}.", n,
                 "Câmara dos Deputados, arquivo anual da Cota para o Exercício da Atividade Parlamentar", C.get("url", "https://www.camara.leg.br/transparencia/gastos-parlamentares"),
                 "Soma do valor líquido do arquivo anual oficial por deputado (id da Câmara) e categoria. Inclui só parlamentares com lançamentos no ano; o último mês pode estar incompleto.", C["coletado_em"][:10]))
    n = _csv(out / "senadores.csv", ["codigo_senado", "nome", "partido", "uf", "url_senado"], [[x["id"], x["nome"], x["partido"], x["uf"], x.get("pagina", "")] for x in SN["senadores"]])
    sets.append(("senadores", "Senadores em exercício", "Lista dos senadores em exercício com partido e UF.", n, "Dados Abertos do Senado Federal", "https://www12.senado.leg.br/dados-abertos",
                 "Coleta diária da API oficial (senadores em exercício).", SN["coletado_em"][:10]))
    for slug, nome, desc, n in getattr(S, "votacoes_sets", []):
        sets.append((slug, nome, desc, n, "APIs de Dados Abertos da Câmara dos Deputados e do Senado Federal", "https://dadosabertos.camara.leg.br/",
                     "Votações nominais de plenário desde 01/02/2023 compiladas dos arquivos oficiais (Câmara) e da API de votações (Senado); partido e UF da data da votação. Metodologia em /votacoes/metodologia/.", S.votacoes_col))
    for slug, nome, desc, n in getattr(S, "cota_sets", []):
        sets.append((slug, nome, desc, n, "Câmara dos Deputados (arquivo anual da CEAP) e Senado Federal (API de dados administrativos, CEAPS)", "https://www.camara.leg.br/transparencia/gastos-parlamentares",
                     "Despesas reembolsadas desde 2023 somadas por parlamentar, ano, categoria e fornecedor pessoa jurídica (CNPJ). Fornecedores pessoa física não são publicados. Metodologia em /cota/metodologia/.", (S.cota_meta or "")[:10]))
    blocos, graph = "", []
    for slug, nome, desc, n, fonte, furl, metodo, mod in sets:
        blocos += (f'<section class="blk" id="{'votacoes' if slug == 'votacoes' else ('cota' if slug == 'cota-camara' else slug)}"><h2>{E(nome)}</h2><p>{E(desc)}</p>' + S.table(["Item", "Detalhe"], [
            ["Arquivo", f'<a href="/dados/{slug}.csv">{slug}.csv</a> ({n} linhas, UTF-8)'], ["Fonte original", f'<a href="{E(furl)}" target="_blank" rel="noopener">{E(fonte)}</a>'],
            ["Método", E(metodo)], ["Licença", f'<a href="{LIC[1]}" target="_blank" rel="noopener">{LIC[0]}</a> para a compilação; cite "{E(S.CFG["site_name"])}" e a fonte original'], ["Atualizado em", data_br(mod) if mod else ""]]) + "</section>")
        graph.append({"@type": "Dataset", "name": nome, "description": f"{desc} {metodo}", "url": f"{S.BASE}/dados/#{slug}", "license": LIC[1], "isAccessibleForFree": True, "inLanguage": "pt-BR",
                      "creator": {"@id": S.BASE + "/#org"}, "isBasedOn": furl, "dateModified": mod, "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{S.BASE}/dados/{slug}.csv"}]})
    faqs = [("Posso reutilizar os dados do Estrato?", f"Sim. A compilação está sob licença {LIC[0]}: cite o {E(S.CFG['site_name'])} e a fonte oficial indicada em cada arquivo."),
            ("Os arquivos substituem as fontes oficiais?", "Não. São compilações feitas a partir de dados públicos da Câmara e do Senado. Para fins legais, consulte sempre a fonte original."),
            ("Com que frequência os arquivos são atualizados?", "Os de deputados e senadores, a cada coleta diária; o da cota parlamentar, quando a Câmara atualiza o arquivo anual."),
            ("Qual é o formato dos arquivos?", "CSV separado por vírgula, codificação UTF-8, cabeçalho na primeira linha e decimais com ponto."),
            ("Como apontar um erro nos dados?", 'Pela página de <a href="/correcoes/">correções</a>. Erros confirmados são corrigidos e registrados.')]
    b = (f'<article class="post"><h1>Dados abertos do {E(S.CFG["site_name"])}</h1><p class="lead">Arquivos CSV com os dados que alimentam as páginas de deputados, senadores e cota parlamentar, com fonte, método e licença.</p>'
         f'{blocos}<p>Veja também a <a href="/metodologia/">metodologia</a>.</p></article>')
    S.write("/dados/", S.page(f"Dados abertos: deputados, senadores e cota em CSV | {S.CFG['site_name']}", "Baixe em CSV os deputados e senadores em exercício e a cota parlamentar por deputado e categoria, com fonte oficial, método e licença.",
                              "/dados/", b, faqs=faqs, crumbs=[("Dados abertos", "/dados/")], jsonld=graph), lastmod=C["coletado_em"][:10])
    return {"urls": ["/dados/"]}
