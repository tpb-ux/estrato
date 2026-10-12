# Estrato (estrato.com.br)

Portal apartidário sobre os Três Poderes com dados oficiais abertos e resumos de agências públicas. Construído sobre o [portal-core](https://github.com/tpb-ux/portal-core) (cópia do núcleo em `core/`).

- **Prévia** (noindex): https://tpb-ux.github.io/estrato/ — publicada pelo workflow `preview.yml` a cada push.
- **Produção**: VPS srv1784225, `/opt/portais/estrato`, cron nos minutos 7 e 37 (`ops/ciclo.sh`). Ver `OPERACAO_VPS.md`.
- **Lançamento público só depois de 25/10/2026** (2º turno): até lá `noindex_global: true` e restrições eleitorais no `feeds.yaml`.

Dados: `tools/camara_senado.py` (Câmara e Senado), `tools/ceap.py` (cota parlamentar, arquivo anual oficial), `tools/fotos.py` (fotos oficiais em WebP), todos rodados por `tools/datasets_diario.py` uma vez por dia.
