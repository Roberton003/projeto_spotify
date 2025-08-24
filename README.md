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

