---
# RASCUNHO para revisão do Tercio. NÃO está em content/, então o build ignora este arquivo.
# Para publicar: preencher autor e revisado_por (slugs de data/autores.yaml, com nome preenchido),
# resolver as marcas [[REVISÃO]], trocar status para "aprovado" e mover para content/.
# Período eleitoral: o texto só usa agregados oficiais e não cita nomes, partidos nem candidaturas.
# Revisao 15/10/2026: percentuais por categoria conferem com data/cotas (37,4%; 24,5%; 17,8%; 12,8%; 2,8%).
# DIVERGENCIA a resolver antes de publicar: o total deste texto (R$ 138,0 mi; 575 parlamentares) vem do CSV bruto de 12/10; a base do site
# (data/cotas/camara.json.gz, coletada em 12/10 18:58 UTC) soma R$ 137,2 mi e 563 parlamentares. Refazer os numeros com a base do site e republicar no mesmo dia.
# Antes de publicar: autor, revisado_por, resolver todas as [[REVISAO]] e a divergencia acima; manter so agregados (sem nomes de partidos ou candidatos).
titulo: "Cota parlamentar soma R$ 138 milhões em 2026, e divulgação lidera os gastos"
data: 2026-10-12T12:00:00-03:00
editoria: congresso
tipo: analise
status: rascunho
autor: ""
revisado_por: ""
resumo: "Os lançamentos da cota parlamentar de 2026 somam R$ 138 milhões até outubro, segundo o arquivo oficial da Câmara. Divulgação da atividade parlamentar responde por 37% do total."
---
Os deputados federais lançaram **R$ 138,0 milhões** na Cota para o Exercício da Atividade Parlamentar (CEAP) em 2026 até 12 de outubro, segundo o arquivo anual oficial da Câmara dos Deputados. A soma inclui 575 parlamentares que tiveram algum lançamento no ano, entre titulares e suplentes que passaram pelo mandato. Os 510 deputados em exercício hoje respondem por R$ 131,6 milhões.

## Para onde vai o dinheiro

Cinco categorias concentram 95% do gasto:

| Categoria | Valor em 2026 | Participação |
|---|---|---|
| Divulgação da atividade parlamentar | R$ 51,4 milhões | 37,2% |
| Locação ou fretamento de veículos | R$ 33,6 milhões | 24,4% |
| Manutenção de escritório de apoio | R$ 24,6 milhões | 17,8% |
| Combustíveis e lubrificantes | R$ 17,5 milhões | 12,7% |
| Hospedagem (fora do Distrito Federal) | R$ 3,8 milhões | 2,8% |

O deputado em exercício que fica no meio da lista (a mediana) lançou R$ 265,8 mil no ano.

## Gasto mês a mês

[[REVISÃO: totais de 575 parlamentares e R$ 138,0 mi divergem da base do site (563 e R$ 137,2 mi); alinhar.]]

Os lançamentos subiram de R$ 17,1 milhões em janeiro para R$ 23,4 milhões em maio e caíram a partir de junho: R$ 12,6 milhões em junho, R$ 11,0 milhões em julho, R$ 8,6 milhões em agosto e R$ 5,0 milhões em setembro. Outubro ainda está incompleto (R$ 0,3 milhão).

[[REVISÃO: os deputados têm prazo para apresentar notas, então os meses mais recentes ainda podem crescer. Confirmar com a Câmara o prazo e se há regra específica do período eleitoral para a categoria "divulgação" antes de explicar a queda. Sem confirmação, manter só os números.]]

## Diferenças entre estados

A média por deputado em exercício varia conforme a bancada: as maiores ficaram no Rio Grande do Norte (R$ 346,2 mil), no Acre (R$ 324,1 mil) e em Mato Grosso do Sul (R$ 319,5 mil); as menores, no Maranhão (R$ 201,0 mil), em Alagoas (R$ 204,2 mil) e no Ceará (R$ 220,7 mil). O valor máximo mensal da cota muda por estado, porque inclui o custo das passagens até Brasília. [[REVISÃO: conferir a tabela de limites mensais por UF no Ato da Mesa vigente e citar a fonte.]]

## Metodologia

Soma do valor líquido de todos os lançamentos do arquivo anual oficial da Câmara (camara.leg.br/cotas/Ano-2026.csv.zip), baixado em 12/10/2026, por deputado e categoria. Valores em reais correntes, sem correção. O detalhamento por deputado está nas páginas de cada parlamentar e no arquivo [cota-parlamentar-categorias.csv](/dados/#cota-parlamentar-categorias). Veja também a [página da cota parlamentar](/deputados/cota-parlamentar/).
