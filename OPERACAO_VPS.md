# Estrato na VPS srv1784225 (2.25.69.172), instruções para o Chefe de gabinete

Mesmo modelo do Modal News: código só no GitHub (`tpb-ux/estrato`, público, sem token); a cada ciclo `git fetch` + `git merge origin/main`, coleta, build; nginx serve `/opt/portais/estrato/public`.
**Até 26/10/2026: noindex global LIGADO, mapas DESLIGADOS, DNS NÃO apontado.** Lançamento só com aval do Tercio.

## 1. Clone e venv (usuário `portais`)
```bash
sudo mkdir -p /opt/portais/estrato /var/log/portais && sudo chown -R portais:portais /opt/portais/estrato
sudo touch /var/log/portais/estrato.log && sudo chown portais:portais /var/log/portais/estrato.log   # lição do Modal News: log gravável
sudo -u portais git clone https://github.com/tpb-ux/estrato.git /opt/portais/estrato
sudo -u portais python3 -m venv /opt/portais/estrato/venv
sudo -u portais /opt/portais/estrato/venv/bin/pip install -r /opt/portais/estrato/requirements.txt
```
(`venv/` e `public/` estão fora do git.)

## 2. run.sh
Usar o mesmo `/opt/portais/run.sh` do Modal News: `run.sh estrato` faz `cd /opt/portais/estrato`, `git fetch` + `git merge origin/main`, `fetch.py`, `build.py` (gera `public/`) e IndexNow.
- **IndexNow NÃO pode rodar para o Estrato antes do lançamento.** Se o run.sh chama IndexNow, pular quando `portal=estrato` até 26/10 (ou checar `"noindex_global": true` no `public/saude.json`).
- Ciclo pesado diário (06 UTC): `tools/datasets_*.py`, igual ao Modal News.
- Alternativa pronta no repo: `ops/ciclo.sh` (flock, pull, coleta, build, datasets às 06), lê `ops/portal.env.example`.

## 3. Primeiro ciclo manual e teste das fontes
```bash
sudo -u portais /opt/portais/run.sh estrato
grep -o '"noindex_global": *[a-z]*' /opt/portais/estrato/public/saude.json    # deve ser true
grep -c 'noindex' /opt/portais/estrato/public/index.html                   # >= 1
ls /opt/portais/estrato/public/mapas 2>/dev/null | head -1                  # mapas: sem links nem sitemap (config mapas.ativo: false)
sudo -u portais bash /opt/portais/estrato/ops/testar_fontes_vps.sh         # Viomundo, TSE, STJ, pauta do STF
```
Mandar a saída de `/tmp/estrato_teste_fontes.txt` (do box todas deram 403, exceto feed do STF e calendário do STF).

## 4. Cron (crontab do `portais`)
```
12,42 * * * * /opt/portais/run.sh estrato >> /var/log/portais/estrato.log 2>&1
```
(Defasado do Modal News, que roda em 7,37, para não disputar CPU.)

## 5. nginx: /etc/nginx/sites-available/estrato.com.br
```nginx
server {
  listen 80; listen [::]:80;
  server_name estrato.com.br www.estrato.com.br;
  root /opt/portais/estrato/public;
  index index.html;
  if ($host = www.estrato.com.br) { return 301 https://estrato.com.br$request_uri; }
  location / { try_files $uri $uri/ $uri.html =404; }
  error_page 404 /404.html;
  location /static/ { expires 30d; add_header Cache-Control "public, max-age=2592000"; }
  location ~* \.(html|xml|json|txt)$ { add_header Cache-Control "no-cache"; add_header X-Robots-Tag "noindex, nofollow" always; }
  gzip on; gzip_types text/css application/javascript application/json application/xml text/xml text/plain image/svg+xml;
  add_header X-Content-Type-Options nosniff;
  # PRÉ-LANÇAMENTO (remover só no lançamento):
  add_header X-Robots-Tag "noindex, nofollow" always;
}
```
```bash
sudo ln -s /etc/nginx/sites-available/estrato.com.br /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx
curl -sI -H 'Host: estrato.com.br' http://127.0.0.1/ | grep -i 'x-robots'     # noindex, nofollow
```
Pode já emitir o certificado depois do DNS (item 6); o noindex continua.

## 6. Checklist do DNS de estrato.com.br (registro.br, conta do Tercio)
- [ ] Registro `A` `@` → `2.25.69.172`; `A` `www` → `2.25.69.172` (ou `CNAME www` → `estrato.com.br`); TTL 3600.
- [ ] Remover registros antigos `A`/`AAAA`/`CNAME` de `@` e `www` (ex.: GitHub Pages 185.199.x). Sem IPv6 na VPS, não criar `AAAA`.
- [ ] Manter MX/TXT existentes (e-mail).
- [ ] Conferir: `dig +short estrato.com.br` e `dig +short www.estrato.com.br` = 2.25.69.172.
- [ ] `sudo certbot --nginx -d estrato.com.br -d www.estrato.com.br` e `curl -sI https://estrato.com.br/` (200 + X-Robots-Tag noindex).
- [ ] Antes do DNS testar com `curl --noproxy '*' --resolve estrato.com.br:443:2.25.69.172 https://estrato.com.br/` (lição do Modal News).
DNS pode ser apontado antes de 26/10 só se o Tercio autorizar; o site continua noindex.

## 7. Lançamento e ondas de indexação (a partir de 27/10/2026, com aval do Tercio)
Onda 0 (27/10): `config.yaml` `noindex_global: false`, remover `aviso_topo`; tirar `X-Robots-Tag` do nginx; liberar IndexNow; `restricao_editoria` e `restricao_nao_oficial` no `feeds.yaml` expiram sozinhas em 26/10 (revisar). Indexáveis: home, editorias, notícias, glossário, perguntas, explica, linha do tempo, calendário, quem é quem, institucionais. Search Console + Bing, enviar `/sitemap.xml`.
Onda 1 (+7 dias, se Search Console sem erro): `familias_noindex` libera deputados, senadores, partidos e votações.
Onda 2 (+14 dias): cota parlamentar, emendas, executivo (viagens/cartão), agenda.
Onda 3 (+21 dias): `mapas.ativo: true` e rankings por estado; patrimônio TSE só depois de revisão humana.
Cada onda = um commit no GitHub; a VPS pega no ciclo seguinte. Critério para avançar: cobertura sem picos de "Rastreada, não indexada" e build sem links quebrados.
