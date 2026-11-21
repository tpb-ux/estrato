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
**Atenção (auditoria 15/10):** `add_header` dentro de um `location` descarta os `add_header` do nível `server`, por isso o modelo antigo repetia `X-Robots-Tag` em 3 pontos (server, `/static/`, `\.(html|xml|json|txt)`). Para não esquecer nenhum no lançamento, o noindex agora vem de **um único snippet** incluído nos 3 pontos. No lançamento basta esvaziá-lo (item 7).
```bash
sudo tee /etc/nginx/snippets/estrato-robots.conf >/dev/null <<'EOF'
# PRÉ-LANÇAMENTO: noindex por cabeçalho. No lançamento deixar este arquivo SÓ com comentário (sem add_header).
add_header X-Robots-Tag "noindex, nofollow" always;
EOF
sudo tee /etc/nginx/snippets/estrato-seguranca.conf >/dev/null <<'EOF'
add_header X-Content-Type-Options nosniff always;
EOF
```
```nginx
# www -> apex. Antes do certbot o destino é http ($scheme); o certbot --nginx (com -d dos dois nomes) cria o bloco 443 e o redirect passa a ir para https.
server {
  listen 80; listen [::]:80;
  server_name www.estrato.com.br;
  return 301 $scheme://estrato.com.br$request_uri;
}
server {
  listen 80; listen [::]:80;
  server_name estrato.com.br;
  root /opt/portais/estrato/public;
  index index.html;
  include snippets/estrato-robots.conf;          # (1) server
  include snippets/estrato-seguranca.conf;
  gzip on; gzip_vary on; gzip_types text/css application/javascript application/json application/xml text/xml text/plain image/svg+xml;
  location / { try_files $uri $uri/ $uri.html =404; }
  error_page 404 /404.html;
  location /static/ { expires 30d; add_header Cache-Control "public, max-age=2592000"; include snippets/estrato-robots.conf; include snippets/estrato-seguranca.conf; }   # (2) static
  location ~* \.(html|xml|json|txt)$ { add_header Cache-Control "no-cache"; include snippets/estrato-robots.conf; include snippets/estrato-seguranca.conf; }                # (3) html/xml/json/txt
}
```
```bash
sudo ln -s /etc/nginx/sites-available/estrato.com.br /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx
for u in / /sitemap.xml /llms.txt /static/og-default.png; do echo -n "$u: "; curl -sI -H 'Host: estrato.com.br' http://127.0.0.1$u | grep -i 'x-robots' || echo vazio; done   # pré-lançamento: 4x "noindex, nofollow"
```
Depois do certbot, conferir que o bloco 443 criado também inclui os snippets nos 3 pontos e que `curl -sI https://www.estrato.com.br/` devolve `301` com `Location: https://estrato.com.br/...`.

## 6. Checklist do DNS de estrato.com.br (registro.br, conta do Tercio)
- [ ] Registro `A` `@` → `2.25.69.172`; `A` `www` → `2.25.69.172` (ou `CNAME www` → `estrato.com.br`); TTL 3600.
- [ ] Remover registros antigos `A`/`AAAA`/`CNAME` de `@` e `www` (ex.: GitHub Pages 185.199.x). Sem IPv6 na VPS, não criar `AAAA`.
- [ ] Manter MX/TXT existentes (e-mail).
- [ ] Conferir: `dig +short estrato.com.br` e `dig +short www.estrato.com.br` = 2.25.69.172.
- [ ] `sudo certbot --nginx -d estrato.com.br -d www.estrato.com.br` e `curl -sI https://estrato.com.br/` (200 + X-Robots-Tag noindex) e `curl -sI https://www.estrato.com.br/` (301 para `https://estrato.com.br/`).
- [ ] Antes do DNS testar com `curl --noproxy '*' --resolve estrato.com.br:443:2.25.69.172 https://estrato.com.br/` (lição do Modal News).
DNS pode ser apontado antes de 26/10 só se o Tercio autorizar; o site continua noindex.

## 7. Lançamento e ondas de indexação (a partir de 27/10/2026, com aval do Tercio)
Onda 0 (27/10): `config.yaml` `noindex_global: false`, remover `aviso_topo`; **tirar os TRÊS pontos do `X-Robots-Tag`** (server, `/static/`, `html|xml|json|txt`): esvaziar `/etc/nginx/snippets/estrato-robots.conf` (deixar só o comentário), `nginx -t && systemctl reload nginx` e validar `for u in / /sitemap.xml /robots.txt /llms.txt /rss.xml /static/og-default.png; do curl -sI https://estrato.com.br$u | grep -i x-robots; done` (esperado: nenhuma linha); liberar IndexNow; `restricao_editoria` e `restricao_nao_oficial` no `feeds.yaml` expiram sozinhas em 26/10 (revisar). Indexáveis: home, editorias, notícias, glossário, perguntas, explica, linha do tempo, calendário, quem é quem, institucionais. Search Console + Bing, enviar `/sitemap.xml`.
Onda 1 (+7 dias, se Search Console sem erro): `familias_noindex` libera deputados, senadores, partidos e votações.
Onda 2 (+14 dias): cota parlamentar, emendas, executivo (viagens/cartão), agenda.
Onda 3 (+21 dias): `mapas.ativo: true` e rankings por estado; patrimônio TSE só depois de revisão humana.
Cada onda = um commit no GitHub; a VPS pega no ciclo seguinte. Critério para avançar: cobertura sem picos de "Rastreada, não indexada" e build sem links quebrados.

## 8. Novas famílias locais, Mapa da Mídia e flags (15/10/2026)
- **Build:** ~5 min e vários GB em `public/` (66,7 mil páginas); precisa de ~3 GB de RAM livre e disco folgado. Rodar fora do ciclo de 12 e 42 min (o ciclo leve não deve disparar build completo ao mesmo tempo).
- **Famílias novas (todas em `familias_noindex`; só hubs e metodologias indexáveis):** `prefeituras`, `verbas`, `representantes`, `eleitorado`, `perguntas_local` (5.570 cada), `bairros` (17.474 em 895 municípios), `midia` (105) e `prefeitos` (desligada). Cada uma sai da lista em onda própria (uma por vez, 2 a 3 semanas), conforme o comentário "onda 8" do `config.yaml`.
- **Datasets (rodados por `ops/ciclo.sh`):** `datasets_bairros.py` (IBGE, só se faltar), `datasets_tse.py` (TSE, refaz com > 25 dias), `datasets_midia.py` (Wikipédia, refaz com > 7 dias), `datasets_prefeitos.py` (só roda com a flag ligada).
- **Flags:** `prefeitos: {ativo: false, liberar_em: 2026-10-27}` (prefeito e vereadores de 2024; ligar só depois de 26/10; `data/tse/prefeitos.json.gz` fica fora do git) e `midia: {vies_ativo: false, liberar_em: 2026-10-27}` (viés, confiança e histórico; só liga depois da revisão humana e jurídica da `/midia/metodologia/`, que está noindex em rascunho).
- **Fontes que bloqueiam o box (testar da VPS):** IBGE Cidades, Portal da Transparência, TREs, vários TCEs, Receita/CNPJ.

## 9. Lançamento em estrato.com.br (onda 1), decisão do Tercio em 21/11/2026

Domínio oficial: **https://estrato.com.br**. `www.estrato.com.br` redireciona 301 para o raiz. `estrato.cc`, `www.estrato.cc` e `estrato.app` (e o www, se existir) redirecionam 301 para `https://estrato.com.br$request_uri`. A prévia `estrato.2-25-69-172.sslip.io` deve **continuar noindex** depois do lançamento.

**DNS em 21/11/2026** (consulta a `dns.google/resolve`, [VERIFICADO]):
- `estrato.com.br`: NS ainda são `val.ns.cloudflare.com` e `vicky.ns.cloudflare.com`. Os registros A de `@` e `www` apontam para `185.158.133.1` (site antigo, atrás da Cloudflare). Enquanto isso não apontar para `2.25.69.172`, o domínio oficial não serve o site novo e o certbot do `.com.br` não valida.
- Caminhos possíveis: (A) no provedor HSTDOMAINS (dominio@hstsupportservices.com ou (48) 3036-1662), trocar os NS para `ns1.dns-parking.com` e `ns2.dns-parking.com` e criar A `@` e `www` para `2.25.69.172` na Hostinger; ou (B) na zona da Cloudflare, trocar o A de `@` e `www` para `2.25.69.172`. Se o certificado for emitido na VPS (certbot HTTP-01), desligar o proxy laranja (DNS only).
- Já na VPS: `estrato.cc` A `2.25.69.172` (NS ns1/ns2.dns-parking.com); `estrato.app` A `2.25.69.172` (NS cosmos/nova.dns-parking.com).

Ordem importa: o cabeçalho `X-Robots-Tag` é a ÚLTIMA trava; só sai depois de conferir o HTML novo e de o DNS do `.com.br` apontar para a VPS. Merge do PR #4 **somente** com o OK do Tercio no chat do Chefe de gabinete.

1. **Variável que trava tudo.** `PORTAL_NOINDEX=1` (em `portal.env`, `run.sh` ou crontab) força noindex mesmo com `noindex_global: false`. Conferir e **remover**:
   `grep -rn NOINDEX /opt/portais/run.sh /opt/portais/estrato/portal.env /var/spool/cron/crontabs/portais 2>/dev/null` (esperado: nada, ou `PORTAL_NOINDEX=0`).
2. **Ciclo parado desde 01/11.** Conferir e religar a coleta: `tail -50 /var/log/portais/estrato.log; crontab -l -u portais; df -h /; ls -la /opt/portais/estrato/.lock`. Corrigir e rodar `/opt/portais/run.sh estrato` à mão. O crontab deve voltar a `12,42 * * * * /opt/portais/run.sh estrato >> /var/log/portais/estrato.log 2>&1`.
3. **DNS do `.com.br` apontando para a VPS** (passo do Tercio ou do Chefe, conforme o caminho A ou B acima). Conferir: `curl -s "https://dns.google/resolve?name=estrato.com.br&type=A"` deve devolver `2.25.69.172`. Só então o certbot.
4. **Merge do PR #4** (`lancamento-estrato-cc`, https://github.com/tpb-ux/estrato/pull/4), somente com o OK do Tercio no chat do Chefe, e rodar `/opt/portais/run.sh estrato`.
5. **Conferir o HTML novo (ainda com o cabeçalho noindex):**
   ```bash
   cd /opt/portais/estrato/public
   grep -o '"noindex_global": *[a-z]*' saude.json        # false
   grep -o 'rel="canonical" href="[^"]*"' index.html      # https://estrato.com.br/
   grep -c 'name="robots" content="noindex' index.html    # 0
   head -5 robots.txt                                     # Allow, Sitemap: https://estrato.com.br/sitemap.xml
   grep -c 'estrato.cc' sitemap.xml sitemap-*.xml robots.txt llms.txt rss.xml   # 0
   grep -o '<loc>' sitemap-*.xml | wc -l                   # 605 URLs (onda 1)
   ```
6. **nginx e SSL.** `server_name` do site: `estrato.com.br`. Redirects:
   ```nginx
   # www -> raiz
   server {
     listen 80; listen [::]:80;
     server_name www.estrato.com.br;
     return 301 https://estrato.com.br$request_uri;
   }
   # aliases -> domínio oficial (manter o SSL já emitido de .cc e .app para o 301 em HTTPS)
   server {
     listen 80; listen [::]:80;
     listen 443 ssl; listen [::]:443 ssl;
     server_name estrato.cc www.estrato.cc estrato.app www.estrato.app;
     # ssl_certificate dos nomes já existentes; completar com certbot se faltar
     return 301 https://estrato.com.br$request_uri;
   }
   ```
   Depois do DNS do `.com.br` na VPS:
   `sudo certbot --nginx -d estrato.com.br -d www.estrato.com.br`
   Conferir que o bloco 443 de `estrato.com.br` inclui os snippets nos 3 pontos (server, `/static/`, `html|xml|json|txt`).
   Prévia continua noindex: copiar o snippet e trocar só no server do sslip.io.
   ```bash
   sudo cp /etc/nginx/snippets/estrato-robots.conf /etc/nginx/snippets/estrato-robots-previa.conf
   # no server do estrato.2-25-69-172.sslip.io, nos 3 pontos: include snippets/estrato-robots-previa.conf
   printf '# LANCADO: sem X-Robots-Tag no dominio oficial. Previa usa estrato-robots-previa.conf\n' | sudo tee /etc/nginx/snippets/estrato-robots.conf
   sudo nginx -t && sudo systemctl reload nginx
   ```
   Só esvaziar o snippet **depois** de o HTML novo estar no ar e o DNS do `.com.br` apontar para a VPS.
7. **Validar:**
   ```bash
   for u in / /sitemap.xml /robots.txt /llms.txt /rss.xml /static/og-default.png; do echo -n "$u: "; curl -sI https://estrato.com.br$u | grep -i x-robots || echo "(sem X-Robots-Tag, ok)"; done
   curl -sI https://estrato.2-25-69-172.sslip.io/ | grep -i x-robots     # deve continuar noindex
   curl -sI https://www.estrato.com.br/ | head -3                       # 301 para https://estrato.com.br/
   curl -sI https://estrato.cc/ | head -3                               # 301 para https://estrato.com.br/
   curl -sI https://www.estrato.cc/ | head -3
   curl -sI https://estrato.app/ | head -3
   curl -s https://estrato.com.br/robots.txt | grep -i sitemap          # Sitemap: https://estrato.com.br/sitemap.xml
   curl -sI https://estrato.com.br/ | grep -i 'x-robots' || true
   ```
8. **IndexNow e Search Console.** O IndexNow liga sozinho no ciclo seguinte (chave em `https://estrato.com.br/c0f3a1e9b7d24e6f8a5b2c9d1e7f4a30.txt`). Search Console: propriedade de domínio `estrato.com.br` (TXT no DNS, na Cloudflare ou na Hostinger, conforme o caminho escolhido) e enviar `https://estrato.com.br/sitemap.xml`. Bing Webmaster: importar do Search Console.
9. **Ondas seguintes:** um commit por onda em `config.yaml` (`indexacao.familias_noindex`), 2 a 3 semanas entre elas, só se o Search Console mostrar a onda anterior indexada, sem pico de "Rastreada, não indexada".
