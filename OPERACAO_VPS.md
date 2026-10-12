# Estrato na VPS srv1784225 (instruções para o Chefe de gabinete)

Mesmo padrão do Modal News: código no GitHub (`tpb-ux/estrato`, público, sem token), puxado a cada ciclo. **Não apontar o DNS nem desligar o noindex antes do aval do Tercio (lançamento só depois de 25/10/2026).**

## 1. Pasta, clone e venv (usuário `portais`)
```bash
sudo mkdir -p /opt/portais/estrato /var/www/estrato /var/log/portais
sudo chown -R portais:portais /opt/portais/estrato /var/www/estrato
sudo touch /var/log/portais/estrato.log && sudo chown portais:portais /var/log/portais/estrato.log   # lição do Modal News: log gravável pelo usuário do cron
sudo -u portais git clone https://github.com/tpb-ux/estrato.git /opt/portais/estrato/repo
sudo -u portais python3 -m venv /opt/portais/estrato/venv
sudo -u portais /opt/portais/estrato/venv/bin/pip install -r /opt/portais/estrato/repo/requirements.txt
```

## 2. /opt/portais/estrato/portal.env
```bash
PORTAL_DIR=/opt/portais/estrato
PORTAL_WEBROOT=/var/www/estrato
PORTAL_VENV=/opt/portais/estrato/venv
PORTAL_BRANCH=main
PORTAL_DATASETS_HORA=06
# 1 = pré-lançamento (noindex,nofollow em tudo, robots Disallow, IndexNow desligado). Mudar para 0 só no lançamento.
PORTAL_NOINDEX=1
```

## 3. Primeiro ciclo manual (teste)
```bash
sudo -u portais bash -c 'cd /opt/portais/estrato/repo && /opt/portais/estrato/venv/bin/python tools/datasets_diario.py'
sudo -u portais /opt/portais/estrato/repo/ops/ciclo.sh /opt/portais/estrato
cat /opt/portais/estrato/ALERTA.txt; head -c 600 /var/www/estrato/saude.json
```
Conferir: `saude.json` com `"noindex_global": true`, `feeds.ok` = 6 (retestar da VPS: TSE e STJ deram 403 do box), build sem `ERRO`.

## 4. Cron (crontab do usuário `portais`)
```
7,37 * * * * /opt/portais/estrato/repo/ops/ciclo.sh /opt/portais/estrato >> /var/log/portais/estrato.log 2>&1
```
O `ciclo.sh` usa `flock` por portal, então não colide com o próprio ciclo anterior. Os datasets (Câmara, Senado, CEAP, fotos) rodam no ciclo das 06:07 UTC.

## 5. nginx: /etc/nginx/sites-available/estrato.com.br
```nginx
server {
  listen 80; listen [::]:80;
  server_name estrato.com.br www.estrato.com.br;
  root /var/www/estrato;
  index index.html;
  if ($host = www.estrato.com.br) { return 301 https://estrato.com.br$request_uri; }
  location / { try_files $uri $uri/ =404; }
  error_page 404 /404.html;
  location /static/ { expires 30d; add_header Cache-Control "public, max-age=2592000"; }
  location ~* \.(html|xml|json|txt)$ { add_header Cache-Control "no-cache"; }
  gzip on; gzip_types text/css application/javascript application/json application/xml text/xml text/plain image/svg+xml;
  add_header X-Content-Type-Options nosniff; add_header Referrer-Policy strict-origin-when-cross-origin;
  # Pré-lançamento (remover no lançamento):
  add_header X-Robots-Tag "noindex, nofollow" always;
}
```
```bash
sudo ln -s /etc/nginx/sites-available/estrato.com.br /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx
```
Teste sem DNS: `curl -H 'Host: estrato.com.br' http://127.0.0.1/saude.json`.

## 6. Lançamento (depois de 25/10/2026, com aval do Tercio)
1. DNS do estrato.com.br (A `@` e `www` para o IP da VPS) e `certbot --nginx -d estrato.com.br -d www.estrato.com.br`.
2. `config.yaml`: `noindex_global: false`, remover `aviso_topo`, revisar `restricao_editoria` no `feeds.yaml` (commit no GitHub).
3. `portal.env`: `PORTAL_NOINDEX=0`; remover a linha `X-Robots-Tag` do nginx.
4. Search Console e Bing (meta em `config.yaml > verificacao`), enviar `https://estrato.com.br/sitemap.xml`.
