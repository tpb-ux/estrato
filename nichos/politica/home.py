"""Home do Estrato: core.home + faixa de números do Congresso (dados oficiais)."""
import json
from core import home as core_home
from core.site import E
def build(S, posts, card, sec, img):
    m = S.modulos.get("parlamentares", {})
    stats = ""
    if m:
        stats = ('<section class="blk"><h2 class="st"><span>Dados oficiais</span><strong>O Congresso em números</strong></h2><div class="stats">'
                 f'<a class="stat" href="/deputados/"><b>{m["n_dep"]}</b><span>deputados federais em exercício</span></a>'
                 f'<a class="stat" href="/senadores/"><b>{m["n_sen"]}</b><span>senadores em exercício</span></a>'
                 f'<a class="stat" href="/partidos/"><b>{m["n_part"]}</b><span>partidos com bancada no Congresso</span></a>'
                 f'<a class="stat" href="/deputados/cota-parlamentar/"><b>{m["ceap_total_fmt"]}</b><span>em cota parlamentar declarada em {m["ceap_ano"]} (até {m["ceap_mes"]})</span></a>'
                 f'</div><p class="upd">Fonte: Câmara dos Deputados e Senado Federal, Dados Abertos. Coleta em {E(m["coleta"])}.</p></section>')
    core_home.build(S, posts, card, sec, img, extra_html=stats)
