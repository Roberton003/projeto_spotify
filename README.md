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

Scripts Utilitários de Manutenção
---------------------------------
A pasta `utils/` contém scripts para diagnóstico e manutenção do pipeline.

- **`utils/listar_generos_api.py`**: Este script contata a API do Spotify para obter a lista oficial de "sementes de gênero" (genre seeds). É útil para descobrir novos gêneros ou os nomes exatos que a API reconhece para usar em coletas futuras.
- **`utils/verificar_generos.py`**: Este script inspeciona o banco de dados local (`data/spotify.db`) e lista todos os gêneros para os quais já coletamos dados, ajudando a identificar rapidamente quais gêneros estão faltando ou não retornaram dados.

Resultado/validações até o momento
---------------------------------
- Suite de testes: 10 passed (suíte local rodando com `.venv`).
- Execuções manuais do coletor:
  - Batch inicial processado: gêneros `rock` e `pop` (rodado com `--batch-genres 2`).
  - `pop` teve vários artistas brasileiros processados (Henrique & Juliano, Jorge & Mateus, Zé Neto & Cristiano, Marília Mendonça, etc.).
  - `data/metrics_*.json` gerados; exemplo: `data/metrics_20250824T225800Z.json`.
  - Banco `data/spotify.db` contém registros (ex.: 100 tracks durante validação).
  - Checkpoints gerados/atualizados: `data/checkpoints/checkpoint_<genre>.json` e `data/checkpoints/genre_rotation.json`.

Desafios e Estratégias Adotadas
---------------------------------
### Desafio na Coleta de Gêneros Brasileiros

Durante a coleta dos gêneros mais populares do Brasil, foi observado que a busca padrão da API do Spotify (`q=genre:"..."`) não retornou resultados para alguns gêneros musicais brasileiros importantes, como `sertanejo`, `pagode` e `forro`.

Investigações adicionais mostraram que o endpoint de "sementes de gênero" (`available-genre-seeds`) da API também não era uma fonte confiável, retornando uma lista vazia. Isso indica que a descoberta de artistas para esses gêneros exige uma abordagem mais elaborada.

### Nova Estratégia: Descoberta de Artistas via Playlists

Para contornar essa limitação, foi adotada uma nova estratégia de coleta para os gêneros afetados:

1.  **Busca por Playlists:** Em vez de buscar por gênero, o sistema agora busca por playlists populares usando o nome do gênero como palavra-chave (ex: "Top Sertanejo").
2.  **Extração de Artistas:** O sistema extrai todas as músicas da playlist mais relevante encontrada.
3.  **Compilação de Artistas Únicos:** A partir da lista de músicas, uma lista de artistas únicos é compilada.
4.  **Coleta Padrão:** Com a lista de artistas em mãos, o pipeline segue seu fluxo normal, buscando as top tracks de cada artista e salvando os dados.

### Ciclo de Engenharia de Dados em Ação

A implementação bem-sucedida da nova estratégia demonstrou um ciclo completo de engenharia de dados na prática:

- **Planejamento e Coleta:** Uma coleta inicial foi executada com base nos requisitos.
- **Análise e Validação:** Ao visualizar o resultado (`dashboard_popularidade.html`), foi identificado que dados importantes estavam ausentes.
- **Depuração e Causa Raiz:** A investigação no banco de dados e o teste direto na API revelaram que o método de coleta original não era eficaz para todos os casos de uso.
- **Melhoria e Iteração:** Uma nova abordagem, mais robusta, foi desenhada e implementada no script `coleta_spotify.py`.
- **Entrega e Validação Final:** A nova lógica foi executada com sucesso, os dados faltantes foram coletados e o dashboard final foi gerado, validando a solução e entregando o valor esperado.

Esta abordagem iterativa é fundamental para a construção de pipelines de dados resilientes e confiáveis.