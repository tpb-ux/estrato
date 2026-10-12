# Plano de dados de transparência — cargo por cargo (Estrato)
Levantamento de 12/10/2026, sem construção. Status = resposta HTTP testada do box nesta data.

## Status das fontes testadas do box
| Fonte | Status | Observação |
|---|---|---|
| API Portal da Transparência (api.portaldatransparencia.gov.br) | 403 sem chave | Precisa da chave gratuita (header `chave-api-dados`), cadastro com conta gov.br |
| Downloads em lote do Portal (servidores SIAPE, viagens, CPGF) | 200/206 | Funcionam sem chave (ZIP mensal ou anual) |
| TSE dados abertos (CKAN) + CDN (bens, candidatos, prestação de contas) | 200 | Sem chave |
| Câmara API v2 (despesas/cota, eventos, votações) | 200 | Sem chave |
| Senado dadosabertos (lista, votações) + adm-dadosabertos (CEAPS) | 200 | Sem chave |
| Senado Transparência (remuneração) | 200 | Portal HTML/CSV, sem API REST documentada |
| Agenda do Presidente (gov.br/planalto) | 200 | HTML diário |
| e-Agendas CGU (agendas de autoridades do Executivo) | 200 | Tem exportação, precisa conferir formato |
| DataJud CNJ | 401 sem chave | A CNJ publica uma APIKey pública na documentação, a configurar |
| portal.stf.jus.br / transparencia.stf.jus.br | 403 | Bloqueio anti-bot; testar pelo navegador ou com outra rede (VPS) |
| TCU (portal) | 200; dadosabertos.tcu.gov.br não respondeu (timeout) | |
| Assembleias (ex.: ALESP) | 405 HEAD | Cada uma é uma fonte diferente; levantar uma a uma |

## Por cargo
Volumes: número de titulares (páginas de perfil). As páginas de detalhe (viagem, despesa) ficam como tabelas dentro do perfil, não como páginas soltas.

### Presidente e vice
- Dados: remuneração (Portal), viagens e cartão corporativo da Presidência (CPGF, Portal; parte é sigilosa), agenda (Planalto), patrimônio e doações/gastos de campanha (TSE 2022).
- Volume: 2 perfis, mais páginas de agenda mensal (cerca de 12 por ano).
- Risco: ALTO. O presidente é pré-candidato ou candidato em 2026. Até 26/10, só dados oficiais neutros, sem adjetivos.

### Ministros de Estado
- Dados: remuneração e jetons (Portal), viagens (Portal), agenda (e-Agendas), patrimônio TSE só se já foram candidatos.
- Volume: cerca de 40 perfis, com histórico de titulares.
- Risco: médio (alguns saíram para concorrer).

### Senadores (81) e deputados federais (513)
- Já existem perfis e votações.
- Faltam: cota CEAP (Câmara API, `/deputados/{id}/despesas`) e CEAPS (Senado adm-dadosabertos), presença (Câmara eventos e votações; Senado votações), emendas parlamentares (Portal: API com chave ou download), patrimônio e campanha (TSE 2022 e 2026), remuneração (valor do subsídio, igual para todos).
- Volume: 594 perfis enriquecidos. Uma página de cota por parlamentar por ano dá cerca de 2.400.
- Risco: ALTO em período eleitoral. Cota e emendas sem ranking até 26/10.

### Governadores (27)
- Dados: patrimônio e campanha (TSE 2022), agenda e remuneração só nos portais estaduais (27 formatos).
- Volume: 27.
- Risco: alto (eleição estadual 2026).

### Deputados estaduais (1.059)
- Dados: TSE (bens, campanha). Cota, verba e presença dependem de cada Assembleia, sem padrão.
- Volume: cerca de 1.059.
- Risco: alto. Custo de integração alto (27 fontes).

### Prefeitos (≈5.570) e vereadores (≈58 mil)
- Dados: TSE 2024 (candidatura, bens, receitas e despesas de campanha) uniformes. Salário e verbas só em portais municipais, sem padrão.
- Volume: muito grande, com risco de páginas finas.
- Risco: médio. Recomendo começar só por prefeitos de capitais e cidades grandes, com dados TSE.

### Ministros do STF (11) e tribunais superiores (STJ 33, TST 27, TSE 7, STM 15)
- Dados: remuneração (páginas de transparência de cada tribunal, padrão CNJ de remuneração da magistratura), processos (DataJud: metadados, sem nomes de partes sensíveis), agenda (sites dos tribunais).
- Volume: cerca de 93 perfis.
- Risco: médio (LGPD em processos; não expor partes ou pessoas físicas).

### TCU (9 ministros)
- Dados: remuneração (portal TCU) e acórdãos por relator.
- Volume: 9.
- Risco: baixo.

### Servidores em cargos em comissão (DAS/CCE/FCE)
- Dados: remuneração (download SIAPE do Portal, mensal), viagens.
- Volume: dezenas de milhares (medir no arquivo).
- Risco: ALTO de LGPD. São servidores comuns. Sugiro só agregados por órgão e cargo, e páginas individuais apenas para os níveis mais altos.

## Riscos LGPD/eleitorais (geral)
- Publicar só o que a fonte oficial já publica, com link para ela. Sem CPF completo, endereço ou dados de familiares.
- Bens declarados ao TSE: mostrar como a fonte mostra. Não somar patrimônio de pessoas diferentes nem criar rankings.
- Até 26/10: nada de "melhor/pior", "mais gastou" ou rankings de candidatos. Só tabelas factuais em ordem alfabética ou cronológica.
- Não incluí artigos de lei específicos. Recomendo revisão jurídica antes da onda de servidores.

## Ordem sugerida
1. Cota CEAP/CEAPS e presença de deputados e senadores (APIs abertas, já testadas, perfis existentes).
2. Patrimônio e campanha TSE para deputados, senadores e governadores (CDN aberta). Publicar depois de 26/10 ou em noindex até lá.
3. Emendas parlamentares (Portal: precisa da chave, ou o download em lote).
4. Ministros: viagens e agenda (Portal com chave, e-Agendas).
5. Presidente e vice: agenda, viagens, CPGF.
6. STF, tribunais superiores e TCU: remuneração e processos (DataJud; STF bloqueia o box).
7. Prefeitos de capitais (TSE) e, por último, assembleias, vereadores e servidores (agregados).

## O que é preciso do Tercio
- A chave da API do Portal da Transparência (cadastro gratuito com conta gov.br no portal; vai como segredo na VPS).
- Decisão sobre publicar patrimônio TSE antes ou depois de 26/10.
- Aprovação do escopo para servidores DAS (só agregados, ou individuais nos níveis altos) e se haverá revisão jurídica.
- Opcional: permissão para testar o STF a partir da VPS, já que bloqueia o box.
