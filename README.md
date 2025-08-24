# Projeto Spotify — Coleta e Exploração (Data Engineering)

Resumo
-----
Pipeline simples para coletar dados da API do Spotify, salvar respostas raw, normalizar e exportar para análise. Funcionalidades principais atuais:
- Coleta por gênero, com paginação e retry/backoff
- Validação básica via JSON Schema
- Particionamento por `genre/YYYY/MM/DD`
- Checkpoint por gênero para evitar reprocessamento
- Métricas em JSON (fallback) e integração opcional com Prometheus
- Suporte interativo e modo não-interativo (flags CLI)
- Rotação por gêneros (batch) para execução progressiva

Status das alterações realizadas (histórico resumido)
---------------------------------------------------
- Remoção de `.env` com credenciais do repositório (se havia sido criado acidentalmente)
- Harden em `coleta_spotify.py`:
  - `load_dotenv(override=False)` para não sobrescrever variáveis de ambiente
  - `security_check_env()` para checagens heurísticas durante runtime
  - novo suporte CLI: `--genero/-g`, `--qtd/-n`, `--market/-m`, `--force`, `--no-interactive`
  - novos recursos: `get_available_genres()`, `coletar_todos_generos()`, flags `--collect-all`, `--batch-genres`, `--rotation-file`
- Scanner leve de pré-commit: `scripts/precommit_check.py` + `.git/hooks/pre-commit` para bloquear commits acidentais contendo atribuições literais de `SPOTIFY_*` ou tokens sensíveis (configurado com exceções para `data/` e padrões de imagens do Spotify)
- Script helper para agendamento: `scripts/run_batch.sh` (invoca .venv e roda um batch por execução)

Resultado/validações até o momento
---------------------------------
- Suite de testes: 10 passed (suíte local rodando com `.venv`).
- Execuções manuais do coletor:
  - Batch inicial processado: gêneros `rock` e `pop` (rodado com `--batch-genres 2`).
  - `pop` teve vários artistas brasileiros processados (Henrique & Juliano, Jorge & Mateus, Zé Neto & Cristiano, Marília Mendonça, etc.).
  - `data/metrics_*.json` gerados; exemplo: `data/metrics_20250824T225800Z.json`.
  - Banco `data/spotify.db` contém registros (ex.: 100 tracks durante validação).
  - Checkpoints gerados/atualizados: `data/checkpoints/checkpoint_<genre>.json` e `data/checkpoints/genre_rotation.json`.

Instalação rápida
-----------------
Recomendo usar o `.venv` do projeto:

```bash
# criar/ativar venv (se ainda não existir)
python3 -m venv .venv
source .venv/bin/activate

# instalar dependências
pip install -r requirements.txt
```

Configurar credenciais (LOCAL e privado)
---------------------------------------
Nunca comite `.env`. Crie localmente a partir do template e proteja o arquivo:

```bash
cp .env.template .env
# editar .env com SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET
chmod 600 .env
```

Uso — execução e modos
----------------------
- Execução interativa (perguntas por gênero, qtd, market):

```bash
./.venv/bin/python coleta_spotify.py
```

- Execução não-interativa (flags):

```bash
# executar coleta por genero (default rock)
./.venv/bin/python coleta_spotify.py --no-interactive

# coletar 20 artistas do genero pop
SPOTIFY_QTD_ARTISTAS=20 SPOTIFY_GENERO=pop ./.venv/bin/python coleta_spotify.py --no-interactive

# processar 2 generos nesta execução (rotação)
./.venv/bin/python coleta_spotify.py --no-interactive --batch-genres 2
```

Rotação progressiva (agendamento)
---------------------------------
Para executar um batch (1 gênero) a cada 20 minutos cole no `crontab -e` do usuário:

```cron
*/20 * * * * cd /home/rob3rto003/Arquivos/Data Science/Engenheiro de Dados_Azure/projeto_spotify && ./scripts/run_batch.sh
```

O helper `scripts/run_batch.sh` executa o batch, grava logs em `logs/collector_*.log` e usa `.env` local (se existir) para fornecer credenciais.

Arquivos gerados e locais relevantes
----------------------------------
- Raw: `data/raw/` (partitioned)
- Processed: `data/processed/<genre>/YYYY/MM/DD/*.json`
- Rankings/Manifests: `data/processed/top_tracks_<genre>_<ts>.json` (ou parquet manifest)
- DB: `data/spotify.db` (tabela `tracks`)
- Checkpoints: `data/checkpoints/checkpoint_<genre>.json` e `data/checkpoints/genre_rotation.json`
- Métricas: `data/metrics_*.json`
- Logs do helper: `logs/collector_*.log`

Pre-commit / Segurança
----------------------
- `scripts/precommit_check.py` (leightweight) bloqueia commits que contenham atribuições literais `SPOTIFY_CLIENT_ID/SECRET` ou tokens hex longos. Ele foi afinado para ignorar dados em `data/` (ex.: ids de imagem `ab6761...`).
- Se precisar commitar alterações que acionariam o pre-commit localmente, desabilite temporariamente o hook ou rode `git commit --no-verify` (não recomendado por rotina).

Observações operacionais
------------------------
- Rate limits: o coletor tem retry/backoff e lida com 429. Porém, ao rodar muitos gêneros em sequência recomendo espaçar execuções (por exemplo, 20 minutos entre batches).
- Se a API retornar lista de gêneros vazia, o coletor usa uma lista fallback que inclui gêneros brasileiros (sertanejo, forró, samba, MPB etc.).

Próximos passos sugeridos
------------------------
- Adicionar workflow CI (GitHub Actions) que executa `pytest` e o scanner de secrets em PRs.
- Integrar um secrets manager (ex.: Azure Key Vault) para armazenar SPOTIFY_* em produção.
- Monitoramento: push dos logs/metrics para um coletor centralizado.

Histórico curto das ações realizadas por este agente
--------------------------------------------------
1. Removido arquivo `.env` exposto do workspace (se presente) e evitado novas exposições.
2. Atualizado `coleta_spotify.py` com checagens de segurança, prompts interativos e flags CLI.
3. Implementado `scripts/precommit_check.py` e hook `.git/hooks/pre-commit` para evitar commits acidentais de segredos.
4. Criado `scripts/run_batch.sh` e lógica de rotação (`--batch-genres`, `genre_rotation.json`) para execução progressiva por gêneros.
5. Executado batches de teste: `rock` (pulado por checkpoint) e `pop` (processado, com artistas brasileiros). Métricas e checkpoints foram gerados.

Se quiser, eu posso agora:
- A) Instalar a crontab automaticamente (editar o crontab do usuário). 
- B) Gerar um workflow GitHub Actions com testes + secret-scan.
- C) Adicionar integração com Azure Key Vault (esboço/instruções).

---
Arquivo atual: `coleta_spotify.py` (modificado), `scripts/precommit_check.py` (novo), `scripts/run_batch.sh` (novo), `.git/hooks/pre-commit` (novo, se aplicável).

Fique à vontade para pedir para eu aplicar a opção A/B/C acima ou gerar um resumo mais detalhado por item.
