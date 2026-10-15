#!/usr/bin/env python3
"""Simulacao dos filtros anti-opiniao e eleitoral (fontes nao oficiais) sobre titulos reais de 14-15/10/2026 rotulados a mao.
Uso: python tools/teste_filtros.py  (sai com codigo 1 se algum rotulo divergir)."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, ".")
from core import fetch as F
cfg = F._F
G1 = "https://g1.globo.com/"; FO = "https://www1.folha.uol.com.br/"
# (rotulo, link, titulo)  rotulo: P = factual, deve passar; B = opiniao/campanha, deve ser barrado
CASOS = [
 ("P", G1 + "trabalho-e-carreira/noticia/2026/10/14/quando-comeca-a-valer-o-fim-da-escala-6x1.ghtml", "Quando começa a valer o fim da escala 6x1? Entenda etapas até redução da jornada"),
 ("P", G1 + "trabalho-e-carreira/noticia/2026/10/14/escala-6x1-o-que-acontece-agora.ghtml", "Fim da escala 6x1: o que acontece agora? Quais são os próximos passos? Entenda"),
 ("P", G1 + "mundo/noticia/2026/10/14/jornada-outros-paises.ghtml", "Fim da escala 6x1: como é a jornada de trabalho em outros países?"),
 ("P", G1 + "saude/noticia/2026/10/14/analise-dos-linfonodos.ghtml", "Análise dos linfonodos vai confirmar estadiamento do câncer do Papa"),
 ("P", G1 + "mundo/noticia/2026/10/13/video-mostra-medicos.ghtml", "VÍDEO mostra médicos rezando o terço antes de cirurgia do Papa"),
 ("P", G1 + "politica/noticia/2026/10/14/camilo.ghtml", "Após aprovação do fim da escala 6x1, Alcolumbre diz a líder do PT: 'Eu não sabia que era assim?'"),
 ("P", G1 + "politica/blog/valdo-cruz/post/2026/10/14/relatorio-da-pf.ghtml", "Relatório da PF sobre envolvimento de ministros com Daniel Vorcaro fica parado no STF"),
 ("P", G1 + "politica/blog/andreia-sadi/post/2026/10/13/pf-stf-citacoes-ministros.ghtml", "PF vai ao STF pedir orientação sobre citações a ministros em investigações"),
 ("P", FO + "colunas/painel/2026/10/carmen-lucia-rejeita-acao-da-uber.shtml", "Cármen Lúcia rejeita ação da Uber para liberar mototáxi em SP"),
 ("P", FO + "colunas/painel/2026/10/governo-de-sp-lanca-pacote-el-nino.shtml", "Governo de SP lança pacote de medidas para enfrentar efeitos do El Niño"),
 ("P", FO + "blogs/brasilia-hoje/2026/10/mpf-abre-apuracao-big-techs.shtml", "MPF abre apuração sobre 'restrições desproporcionais' de big techs a conteúdo"),
 ("P", FO + "blogs/brasilia-hoje/2026/10/pgr-mendonca.shtml", "PGR diz que não há evidências de que Mendonça foi alvo de arapongagem"),
 ("P", "https://www.bahianoticias.com.br/noticia/1-video-senado-aprova-pec", "VÍDEO: Senado aprova PEC do fim da escala 6x1 em segundo turno e conclui votação"),
 ("P", "https://www.bahianoticias.com.br/noticia/2-camara-aprova-mei", "Câmara aprova projeto que amplia limite de faturamento do MEI e perdoa dívidas"),
 ("P", "https://www.bahianoticias.com.br/noticia/3-peru", "Governo do Peru proíbe cabelo comprido, unhas pintadas e celular nas escolas"),
 ("B", FO + "colunas/eliogaspari/2026/10/kassio-precisa-proteger-a-justica.shtml", "Kassio precisa proteger a Justiça"),
 ("B", FO + "colunas/marcosaugustogoncalves/2026/10/com-flavio-la.shtml", "Com Flávio lá, contrapesos e democracia correm risco"),
 ("B", FO + "colunas/maria-herminia-tavares/2026/10/as-forcas-armadas.shtml", "As Forças Armadas na democracia"),
 ("B", FO + "colunas/painel/2026/10/programa-de-flavio.shtml", "Programa de Flávio promete 'tesouraço' na censura enquanto pede bloqueio de contas"),
 ("B", FO + "colunas/painel/2026/10/flavio-garante.shtml", "Flávio garante a aliados que, se eleito, vai defender revisão da PEC do fim da escala 6x1"),
 ("B", FO + "colunas/painel/2026/10/na-tv-propaganda.shtml", "Na TV, propaganda de Lula diz que só ele garante fim da escala 6x1"),
 ("B", FO + "blogs/brasilia-hoje/2026/10/lula-aconselhado.shtml", "Lula é aconselhado por aliados e avalia ir ao Senado caso fim da 6x1 seja aprovado"),
 ("B", G1 + "politica/blog/andreia-sadi/post/2026/10/14/relatorio-defesa-flavio.ghtml", "Relatório da defesa de Flávio Bolsonaro mostra mensagens que teriam sido apagadas"),
 ("B", G1 + "politica/blog/andreia-sadi/post/2026/10/14/analise-stf-caso-master.ghtml", "Análise: STF tenta dar encaminhamento a caso Master antes da chegada do novo ministro"),
 ("B", G1 + "mundo/blog/sandra-cohen/post/2026/10/14/keiko-fujimori.ghtml", "Keiko Fujimori adota a cartilha de Bukele nas escolas do Peru"),
 ("B", G1 + "mundo/blog/sandra-cohen/post/2026/10/13/transparencia-leao.ghtml", "A transparência de Leão XIV rompe a tradição de silêncio do Vaticano"),
 ("B", G1 + "economia/agronegocios/noticia/2026/10/12/cliente-ou-rival.ghtml", "Cliente ou rival? Como a China pode passar de grande compradora a concorrente"),
 ("B", G1 + "podcast/o-assunto/noticia/2026/10/14/abstencao.ghtml", "A abstenção e o poder do voto de quem não votou - O Assunto #1824"),
 ("B", "https://www.jota.info/opiniao-e-analise/artigos/bets-por-que-o-governo-mudou-de-rumo", "Bets: por que o governo mudou de rumo?"),
 ("B", "https://www.jota.info/opiniao-e-analise/colunas/coluna-flavia-maia/nunes-marques", "Nunes Marques recorre a artifícios que criticava e amplia tensão no TSE"),
 ("B", "https://www.jota.info/trabalho/ao-vivo-senado-vota-pec-do-fim-da-escala-6x1", "AO VIVO – Senado vota PEC do fim da escala 6×1. Acompanhe a sessão"),
 ("B", "https://www.congressoemfoco.com.br/artigo/123257/quando-o-judiciario-entra-na-campanha", "Quando o Judiciário entra na campanha"),
 ("B", "https://jornalggn.com.br/opiniao/bolsonaro-e-tragedia-por-paulo-kliass/", "Bolsonaro é tragédia, por Paulo Kliass"),
 ("B", "https://www.gazetadopovo.com.br/vida-e-cidadania/se-todos-ministros/", "E se todos os ministros do STF fossem investigados? Constituição não prevê"),
 ("B", "https://www.brasildefato.com.br/2026/10/13/por-que-as-mulheres/", "Por que as mulheres estão aderindo ao movimento antifeminista?"),
 ("B", "https://www.pragmatismopolitico.com.br/2026/10/teremos-homens-de-respeito.html", "Teremos homens de respeito?"),
 ("B", "https://apublica.org/2026/10/trumponaro", "Trumponaro: como um governo de Flávio pode imitar a presidência de Trump no Brasil"),
 ("B", "https://www.bahianoticias.com.br/noticia/9-lula", "Lula promete criar versão universitária do Pé de Meia caso seja reeleito"),
 ("B", "https://www.bahianoticias.com.br/noticia/10-pesquisa", "Pesquisa Quaest aponta empate técnico entre Lula e Flávio Bolsonaro no segundo turno"),
]
def veredito(link, titulo, vies=None):
    return F.opiniao(cfg, link, titulo, vies) or ("eleitoral: " + h if (h := F.eleitoral_nao_oficial(cfg, titulo, "")) else None)
EXTRA = [  # (rotulo, vies, titulo): veiculos de linha editorial
 ("B", "esquerda", "Soberania n\u00e3o \u00e9 abstra\u00e7\u00e3o: o que a Am\u00e9rica Latina perde com o corol\u00e1rio Trump"),
 ("B", "esquerda", "\u2018Ningu\u00e9m nasceu para trabalhar at\u00e9 a exaust\u00e3o\u2019, diz deputada"),
 ("B", "direita", "Por que o governo errou na pol\u00edtica fiscal"),
 ("P", "esquerda", "Senado aprova PEC que acaba com a escala 6\u00d71; texto vai \u00e0 promulga\u00e7\u00e3o"),
 ("P", "direita", "Moraes nega pedido de Mauro Cid para viajar ao exterior"),
 ("B", "direita", "PSD de Paes apela ao STF para restabelecer o 2\u00ba turno no Rio de Janeiro"),
]
erros = 0
for r, vz, t in EXTRA:
    v = veredito("https://x.com/a", t, vz) or ("eleitoral: " + h if (h := F.eleitoral_nao_oficial(cfg, t, "")) else None)
    if (v is None) != (r == "P"): erros += 1; print(f"DIVERGE [{r}/{vz}] {t[:80]} -> {v}")
NEXTRA = len(EXTRA)
for r, link, t in CASOS:
    v = veredito(link, t); ok = (v is None) == (r == "P")
    if not ok: erros += 1; print(f"DIVERGE [{r}] {t[:80]} -> {v}")
print(f"{len(CASOS) + NEXTRA - erros}/{len(CASOS) + NEXTRA} casos corretos ({sum(1 for c in CASOS if c[0]=='P')} factuais, {sum(1 for c in CASOS if c[0]=='B')} opiniao/campanha)")
sys.exit(1 if erros else 0)
