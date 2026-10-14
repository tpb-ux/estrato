#!/usr/bin/env bash
# Teste de alcance das fontes bloqueadas no box (403), rodar NA VPS srv1784225:  bash ops/testar_fontes_vps.sh
# Saída: código HTTP, tamanho, nº de <item>/<entry> e se tem imagem. Resultado vai para /tmp/estrato_teste_fontes.txt
set -u
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
OUT=/tmp/estrato_teste_fontes.txt; : > "$OUT"
URLS=(
 "Viomundo|https://www.viomundo.com.br/feed"
 "TSE notícias|https://www.tse.jus.br/comunicacao/noticias/rss"
 "TSE portal|https://www.tse.jus.br/comunicacao/noticias"
 "STJ notícias|https://www.stj.jus.br/sites/portalp/Paginas/Comunicacao/Noticias.aspx"
 "STJ RSS|https://res.stj.jus.br/hrstp/rss/noticias.xml"
 "STF feed|https://noticias.stf.jus.br/feed/"
 "STF pauta do Plenário|https://portal.stf.jus.br/pauta/"
 "STF calendário de julgamento|https://portal.stf.jus.br/pauta/pautaCalendario.asp"
)
for l in "${URLS[@]}"; do
  n="${l%%|*}"; u="${l#*|}"; f=$(mktemp)
  r=$(curl -sS -L -m 25 -A "$UA" -H 'Accept-Language: pt-BR' -o "$f" -w '%{http_code} %{size_download}' "$u" 2>&1 | tail -1)
  it=$(grep -oiE '<(item|entry)[ >]' "$f" | wc -l); img=$(grep -ciE 'media:content|enclosure|og:image|<img' "$f")
  printf '%-28s %-10s itens=%-4s img=%-4s %s\n' "$n" "$r" "$it" "$img" "$u" | tee -a "$OUT"; rm -f "$f"
done
echo "OK = HTTP 200 com itens>0 (feed) ou HTML com conteúdo (pauta). Mande $OUT para o Tercio/Grok Bot."
