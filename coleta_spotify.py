import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from typing import List, Optional

import requests
from dotenv import load_dotenv
from jsonschema import ValidationError, validate

from db_client import insert_artist_tracks

# Load .env only if present, but do not overwrite existing environment variables.
# We call load_dotenv with override=False to avoid accidentally overwriting variables set
# in the environment by CI or the runtime. We still perform a security check below.
load_dotenv(override=False)


def _file_contains_secret(path: str, varnames: List[str]) -> bool:
    """Check a file for presence of secret variable assignments (basic heuristic)."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return False
    for v in varnames:
        if v in content and '=' in content.split(v, 1)[1].splitlines()[0]:
            return True
    return False


def security_check_env():
    """Run a few lightweight checks to avoid leaking credentials.

    - Ensure SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are provided via environment
      and not present in repository files (basic heuristic).
    - Ensure `.env.template` exists for documentation.
    This function raises RuntimeError when checks fail.
    """
    required = ['SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET']
    # Check environment variables
    missing = [r for r in required if not os.getenv(r)]
    if missing:
        # Do not fail import; allow tests to run. Instead raise at runtime when trying to
        # authenticate. We log an info to remind the developer.
        logger.info(
            'Variaveis de ambiente ausentes: %s. Use .env.template as exemplo.', missing)

    # Basic repository file scan (heuristic) - look for .env or other common files
    repo_candidates = ['.env', '.env.local', '.secrets', 'credentials.txt']
    for p in repo_candidates:
        full = os.path.join(os.path.dirname(__file__), p)
        if os.path.exists(full) and _file_contains_secret(full, required):
            raise RuntimeError(
                f'Arquivo {p} contem possiveis secrets. Remova antes de commitar.')

    # Ensure .env.template exists
    tpl = os.path.join(os.path.dirname(__file__), '.env.template')
    if not os.path.exists(tpl):
        # create a minimal template to help users
        try:
            with open(tpl, 'w', encoding='utf-8') as f:
                f.write('SPOTIFY_CLIENT_ID=\nSPOTIFY_CLIENT_SECRET=\n')
            logger.info('Criado .env.template de exemplo em %s', tpl)
        except Exception:
            logger.warning(
                'Nao foi possivel criar .env.template automaticamente.')


# structured logging (simple JSON-like formatter)
handler = logging.StreamHandler()
json_formatter = logging.Formatter(
    '{"ts":"%(asctime)s","level":"%(levelname)s","module":"%(name)s","msg":"%(message)s"}')
handler.setFormatter(json_formatter)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Config via variaveis de ambiente
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Defaults
GENERO = os.getenv('SPOTIFY_GENERO', 'rock')
QTD_ARTISTAS = int(os.getenv('SPOTIFY_QTD_ARTISTAS', '10'))
DATA_DIR = os.getenv('DATA_DIR', 'data')
RAW_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')
SCHEMA_PATH = os.path.join(os.path.dirname(
    __file__), 'schema', 'top_tracks_schema.json')

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


def _current_date_partition() -> str:
    """Return date partition string YYYY/MM/DD for current UTC date."""
    now = datetime.now(timezone.utc)
    return os.path.join(str(now.year), f"{now.month:02d}", f"{now.day:02d}")


def _ensure_partition_dirs(base_dir: str, genero: str) -> str:
    """Ensure and return partitioned path for given base_dir and genre.

    Example: base_dir/genre/YYYY/MM/DD
    """
    part = _current_date_partition()
    path = os.path.join(base_dir, genero, part)
    os.makedirs(path, exist_ok=True)
    return path


# --- checkpoint and metrics helpers -------------------------------------------------
def _checkpoint_path_for_genre(genero: str) -> str:
    """Return a checkpoint path for the given genre inside DATA_DIR/checkpoints."""
    cp_dir = os.path.join(DATA_DIR, 'checkpoints')
    os.makedirs(cp_dir, exist_ok=True)
    return os.path.join(cp_dir, f'checkpoint_{genero}.json')


def load_checkpoint(genero: str) -> dict:
    path = _checkpoint_path_for_genre(genero)
    if not os.path.exists(path):
        return {'processed_artists': []}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        logger.warning(
            'Falha ao ler checkpoint %s, reiniciando checkpoint', path)
        return {'processed_artists': []}


def save_checkpoint(genero: str, checkpoint: dict) -> str:
    path = _checkpoint_path_for_genre(genero)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)
    logger.info('Checkpoint salvo: %s', path)
    return path


_METRICS = {'api_calls': 0, 'artists_processed': 0, 'tracks_processed': 0}


def _inc_metric(name: str, amount: int = 1):
    if name in _METRICS:
        _METRICS[name] += amount
    else:
        _METRICS[name] = amount


def _save_metrics():
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = os.path.join(DATA_DIR, f'metrics_{ts}.json')
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(_METRICS, f, ensure_ascii=False, indent=2)
        logger.info('Metrics saved: %s', path)
    except Exception as e:
        logger.warning('Falha ao salvar metrics: %s', e)
    # also export to prometheus if available
    try:
        _export_metrics_prometheus()
    except Exception:
        pass


# Prometheus integration (optional)
try:
    from prometheus_client import Counter, Gauge, start_http_server
    PROMETHEUS_AVAILABLE = True
except Exception:
    PROMETHEUS_AVAILABLE = False


if PROMETHEUS_AVAILABLE:
    PROM_API_CALLS = Counter('spotify_api_calls_total',
                             'Total Spotify API calls')
    PROM_ARTISTS_PROCESSED = Counter(
        'spotify_artists_processed_total', 'Artists processed')
    PROM_TRACKS_PROCESSED = Counter(
        'spotify_tracks_processed_total', 'Tracks processed')
    PROM_LAST_RUN = Gauge('spotify_last_run_timestamp',
                          'Last run timestamp (unix)')


def start_metrics_server(port: int = 8000):
    if PROMETHEUS_AVAILABLE:
        start_http_server(port)
        logger.info('Prometheus metrics server started on port %d', port)
    else:
        logger.info(
            'prometheus_client not available; metrics endpoint disabled')


def _export_metrics_prometheus():
    if not PROMETHEUS_AVAILABLE:
        return
    PROM_API_CALLS.inc(_METRICS.get('api_calls', 0))
    PROM_ARTISTS_PROCESSED.inc(_METRICS.get('artists_processed', 0))
    PROM_TRACKS_PROCESSED.inc(_METRICS.get('tracks_processed', 0))
    try:
        PROM_LAST_RUN.set(int(datetime.now(timezone.utc).timestamp()))
    except Exception:
        pass


def autenticar_spotify(client_id: str, client_secret: str) -> str:
    """Autentica na API do Spotify usando Client Credentials.

    Retorna o token de acesso (string) ou levanta RuntimeError se falhar.
    """
    if not client_id or not client_secret:
        raise RuntimeError(
            'SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET devem estar definidas como variaveis de ambiente')

    url = 'https://accounts.spotify.com/api/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'grant_type': 'client_credentials'}
    resp = _request_with_retry(
        method='post', url=url, headers=headers, data=data, auth=(client_id, client_secret))
    if resp and resp.status_code == 200:
        token = resp.json().get('access_token')
        logger.info('Autenticado com sucesso.')
        return token
    else:
        body = getattr(resp, 'text', '<no response>')
        logger.error('Falha na autenticacao: %s', body)
        raise RuntimeError('Falha na autenticacao Spotify')


def get_available_genres(token: str) -> List[str]:
    """Retorna lista de available-genre-seeds da API do Spotify.

    Se falhar, retorna lista vazia.
    """
    url = 'https://api.spotify.com/v1/recommendations/available-genre-seeds'
    headers = {'Authorization': f'Bearer {token}'}
    try:
        resp = _request_with_retry(method='get', url=url, headers=headers)
        if resp and resp.status_code == 200:
            return resp.json().get('genres', [])
    except Exception:
        pass
    return []


def buscar_artistas_por_genero(genero: str, token: str, limit: int = 10, page_size: int = 50) -> List[dict]:
    """Search artists by genre with pagination to collect up to `limit` artists.

    Spotify search supports `limit` and `offset`. We request up to `page_size` per call and loop
    until we have `limit` artists or no more results.
    """
    headers = {'Authorization': f'Bearer {token}'}
    collected = []
    offset = 0
    while len(collected) < limit:
        to_request = min(page_size, limit - len(collected))
        url = f'https://api.spotify.com/v1/search?q=genre:%22{genero}%22&type=artist&limit={to_request}&offset={offset}'
        resp = _request_with_retry(method='get', url=url, headers=headers)
        if not resp:
            logger.warning(
                'Falha na requisicao para buscar artistas, interrompendo paginação')
            break
        if resp.status_code != 200:
            logger.warning('Erro ao buscar artistas: %s',
                           getattr(resp, 'text', '<no response>'))
            break
        items = resp.json().get('artists', {}).get('items', [])
        if not items:
            break
        collected.extend(items)
        # advance offset by how many Spotify returned
        offset += len(items)
        # if returned less than requested, no more pages
        if len(items) < to_request:
            break
    return collected[:limit]


def buscar_top_tracks(artist_id: str, token: str, market: str = 'BR') -> List[dict]:
    url = f'https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market={market}'
    headers = {'Authorization': f'Bearer {token}'}
    resp = _request_with_retry(method='get', url=url, headers=headers)
    if resp and resp.status_code == 200:
        return resp.json().get('tracks', [])
    body = getattr(resp, 'text', '<no response>')
    logger.warning('Erro ao buscar top tracks para %s: %s', artist_id, body)
    return []


def _request_with_retry(method: str, url: str, headers: Optional[dict] = None, data: Optional[dict] = None, auth: Optional[tuple] = None, max_retries: int = 3, backoff_factor: float = 0.5, timeout: int = 10):
    """Simple retry wrapper for requests to handle 429/5xx with exponential backoff.

    Returns the Response object on success or the last Response/None on failure.
    """
    attempt = 0
    while attempt < max_retries:
        try:
            attempt += 1
            resp = requests.request(
                method=method, url=url, headers=headers, data=data, auth=auth, timeout=timeout)
            # Successful
            if resp.status_code < 400:
                _inc_metric('api_calls', 1)
                return resp
            # Rate limited
            if resp.status_code == 429:
                retry_after = resp.headers.get('Retry-After')
                wait = int(retry_after) if retry_after and retry_after.isdigit(
                ) else backoff_factor * (2 ** (attempt - 1))
                logger.warning(
                    'Rate limited (429). Waiting %s seconds before retry (attempt %d/%d)', wait, attempt, max_retries)
                time.sleep(wait)
                continue
            # Server error -> retry
            if 500 <= resp.status_code < 600:
                wait = backoff_factor * (2 ** (attempt - 1))
                logger.warning('Server error %d on %s. Waiting %s seconds before retry (attempt %d/%d)',
                               resp.status_code, url, wait, attempt, max_retries)
                time.sleep(wait)
                continue
            # Client error that won't be retried
            return resp
        except requests.RequestException as e:
            wait = backoff_factor * (2 ** (attempt - 1))
            logger.warning(
                'Request exception: %s. Waiting %s seconds before retry (attempt %d/%d)', e, wait, attempt, max_retries)
            time.sleep(wait)
            last_exc = e
            continue
    # exhausted retries
    logger.error('Exhausted retries for %s %s', method.upper(), url)
    try:
        return resp
    except NameError:
        return None


def salvar_json_raw(prefix: str, obj: object) -> str:
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    # prefix must include genre or identifier; try to extract genre if present
    # default to 'misc' if not provided
    filename = f"{prefix}_{ts}.json"
    # if prefix contains genre-like suffix e.g. artist_{id}, save under misc partition
    part_dir = _ensure_partition_dirs(RAW_DIR, 'misc')
    path = os.path.join(part_dir, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    logger.info('Salvo raw: %s', path)
    return path


def validar_com_schema(obj: object, schema_path: str = SCHEMA_PATH) -> bool:
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        validate(instance=obj, schema=schema)
        return True
    except FileNotFoundError:
        logger.warning(
            'Schema nao encontrado: %s. Pulando validacao.', schema_path)
        return False
    except ValidationError as e:
        logger.error('Validacao falhou: %s', e)
        return False


def processar_e_salvar(artista_obj: dict, tracks: list, genero: str) -> str:
    """Normaliza a saida e salva arquivo processado por artista."""
    nome = artista_obj.get('name') or 'unknown_artist'
    processed = []
    for t in tracks:
        processed.append({
            'artista': nome,
            'musica': t.get('name'),
            'popularidade': t.get('popularity'),
            'preview_url': t.get('preview_url'),
            'id': t.get('id'),
            'duracao_ms': t.get('duration_ms')
        })

    out_name = f"{nome.replace(' ', '_')}_{genero}.json"
    part_dir = _ensure_partition_dirs(PROCESSED_DIR, genero)
    out_path = os.path.join(part_dir, out_name)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)
    logger.info('Salvo processado: %s (%d tracks)', out_path, len(processed))
    # write into sqlite DB for analytics
    try:
        db_path = os.path.join(DATA_DIR, 'spotify.db')
        insert_artist_tracks(db_path, artista_obj, tracks, genero)
    except Exception as e:
        logger.warning('Falha ao gravar no DB: %s', e)
    _inc_metric('artists_processed', 1)
    _inc_metric('tracks_processed', len(processed))
    return out_path


def coletar_por_genero(genero: str = GENERO, qtd_artistas: int = QTD_ARTISTAS, market: str = 'BR'):
    # valida e chama autenticao
    cid = str(CLIENT_ID or os.getenv('SPOTIFY_CLIENT_ID') or '')
    csecret = str(CLIENT_SECRET or os.getenv('SPOTIFY_CLIENT_SECRET') or '')
    token = autenticar_spotify(cid, csecret)
    artistas = buscar_artistas_por_genero(genero, token, limit=qtd_artistas)
    # load checkpoint
    checkpoint = load_checkpoint(genero)
    processed_ids = set(checkpoint.get('processed_artists', []))
    resultado = []
    for artista in artistas:
        artist_id = str(artista.get('id') or '')
        if artist_id in processed_ids:
            logger.info('Pulando artista ja processado: %s', artist_id)
            continue
        logger.info('Coletando artista: %s', artista.get('name'))
        salvar_json_raw(f"artist_{artist_id}", artista)
        top_tracks = buscar_top_tracks(artist_id, token, market=market)
        salvar_json_raw(f"toptracks_{artist_id}", top_tracks)
        proc_path = processar_e_salvar(artista, top_tracks, genero)
        resultado.append({'artist_id': artist_id, 'processed_path': proc_path})
        # update checkpoint
        processed_ids.add(artist_id)
        checkpoint['processed_artists'] = list(processed_ids)
        save_checkpoint(genero, checkpoint)
    # save metrics summary
    _save_metrics()
    return resultado


if __name__ == '__main__':
    # Execucao via linha de comando com suporte a prompt interativo e flags
    def _prompt_filters() -> dict:
        """Pergunta interativamente genero, qtd e market. Retorna dicionario com escolhas."""
        try:
            # tentar recuperar lista de generos via API se creds disponiveis
            genero = GENERO
            try:
                cid = str(CLIENT_ID or os.getenv('SPOTIFY_CLIENT_ID') or '')
                csecret = str(CLIENT_SECRET or os.getenv(
                    'SPOTIFY_CLIENT_SECRET') or '')
                if cid and csecret:
                    token = autenticar_spotify(cid, csecret)
                    genres = get_available_genres(token)
                    if genres:
                        # mostrar lista numerada e pedir indice
                        print('\nGeneros disponiveis:')
                        for i, g in enumerate(genres):
                            print(f"  [{i}] {g}")
                        idx_raw = input(
                            f'Selecione o numero do genero (enter para {GENERO}): ').strip()
                        if idx_raw != '':
                            try:
                                idx = int(idx_raw)
                                if 0 <= idx < len(genres):
                                    genero = genres[idx]
                                else:
                                    logger.info(
                                        'Indice fora do range, usando default %s', GENERO)
                            except ValueError:
                                logger.info(
                                    'Entrada invalida, usando default %s', GENERO)
                    else:
                        genero = input(
                            f'Genero [{GENERO}]: ').strip() or GENERO
                else:
                    genero = input(f'Genero [{GENERO}]: ').strip() or GENERO
            except Exception:
                genero = input(f'Genero [{GENERO}]: ').strip() or GENERO
            qtd_raw = input(f'Quantidade de artistas [{QTD_ARTISTAS}]: ').strip() or str(
                QTD_ARTISTAS)
            try:
                qtd = int(qtd_raw)
            except ValueError:
                logger.info(
                    'Entrada invalida para quantidade, usando default %s', QTD_ARTISTAS)
                qtd = QTD_ARTISTAS
            market = input('Market (ex: BR) [BR]: ').strip() or 'BR'
            force = input(
                'Remover checkpoint existente e forcar reprocessamento? (s/N): ').strip().lower() in ('s', 'y')
            return {'genero': genero, 'qtd': qtd, 'market': market, 'force': force}
        except (EOFError, KeyboardInterrupt):
            logger.info('Entrada interativa cancelada pelo usuario')
            sys.exit(1)

    parser = argparse.ArgumentParser(
        description='Coletor Spotify (com prompt interativo)')
    parser.add_argument('--genero', '-g', help='Genero musical (ex: rock)')
    parser.add_argument('--qtd', '-n', type=int,
                        help='Quantidade de artistas a coletar')
    parser.add_argument(
        '--market', '-m', help='Market para top-tracks (ex: BR)')
    parser.add_argument('--force', action='store_true',
                        help='Remover checkpoint e forcar reprocessamento')
    parser.add_argument('--no-interactive', action='store_true',
                        help='Nao perguntar, usar defaults/flags')
    parser.add_argument('--collect-all', action='store_true',
                        help='Coletar todos os generos disponiveis (ate --qtd por genero)')
    parser.add_argument('--batch-genres', type=int, default=0,
                        help='Processar este numero de generos nesta execucao (rota em lista de generos)')
    parser.add_argument('--rotation-file', default=os.path.join(DATA_DIR, 'checkpoints',
                        'genre_rotation.json'), help='Arquivo para guardar estado da rotacao de generos')
    args = parser.parse_args()

    # decidir parametros: flags > env vars/defaults > interactive
    if args.no_interactive:
        genero = args.genero or GENERO
        qtd = args.qtd or QTD_ARTISTAS
        market = args.market or 'BR'
        force = bool(args.force)
    else:
        # se alguma flag foi passada, usar ela como valor inicial
        if args.genero or args.qtd or args.market or args.force:
            genero = args.genero or GENERO
            qtd = args.qtd or QTD_ARTISTAS
            market = args.market or 'BR'
            force = bool(args.force)
        else:
            choices = _prompt_filters()
            genero = choices['genero']
            qtd = choices['qtd']
            market = choices['market']
            force = choices['force']

    # opcao de forcar reprocessamento: mover checkpoint para backup
    if force:
        cp = _checkpoint_path_for_genre(genero)
        if os.path.exists(cp):
            bak = cp + '.bak'
            try:
                shutil.move(cp, bak)
                logger.info(
                    'Checkpoint movido para %s (forcando reprocessamento)', bak)
            except Exception as e:
                logger.warning('Falha ao mover checkpoint: %s', e)

    def coletar_todos_generos(max_per_genre: int = 20, market: str = 'BR', force_each: bool = False):
        """Coleta para todos os generos retornados por get_available_genres.

        Para cada genero: coleta até `max_per_genre` artistas e salva resultados.
        Gera um arquivo de ranking por genero em `data/processed/top_tracks_{genero}_{ts}.parquet`.
        """
        cid = str(CLIENT_ID or os.getenv('SPOTIFY_CLIENT_ID') or '')
        csecret = str(CLIENT_SECRET or os.getenv(
            'SPOTIFY_CLIENT_SECRET') or '')
        if not cid or not csecret:
            raise RuntimeError(
                'Credenciais ausentes para coletar todos generos')
        token = autenticar_spotify(cid, csecret)
        genres = get_available_genres(token)
        if not genres:
            logger.warning(
                'Nenhum genero retornado pela API; abortando coleta por generos')
            return
        for g in genres:
            logger.info('Iniciando coleta para genero: %s', g)
            # opcao de forcar por genero
            if force_each:
                cp = _checkpoint_path_for_genre(g)
                if os.path.exists(cp):
                    try:
                        shutil.move(cp, cp + '.bak')
                        logger.info(
                            'Checkpoint movido para %s (forcando reprocessamento)', cp + '.bak')
                    except Exception as e:
                        logger.warning(
                            'Falha ao mover checkpoint para genero %s: %s', g, e)
            try:
                # coletar e processar
                resultado = coletar_por_genero(g, max_per_genre, market)
                # criar ranking simples: agregando arquivos processados por esse genero hoje
                part_dir = _ensure_partition_dirs(PROCESSED_DIR, g)
                # coletar todos jsons recentes para esse genero (não usar pandas para evitar dependência extra aqui)
                ranked = []
                for fn in os.listdir(part_dir):
                    if fn.endswith(f'_{g}.json'):
                        p = os.path.join(part_dir, fn)
                        try:
                            with open(p, 'r', encoding='utf-8') as f:
                                arr = json.load(f)
                                for item in arr:
                                    ranked.append(item)
                        except Exception:
                            continue
                # rankear por popularidade desc
                ranked = [r for r in ranked if r.get(
                    'popularidade') is not None]
                ranked.sort(key=lambda x: x.get(
                    'popularidade', 0), reverse=True)
                # limitar a top 20
                ranked = ranked[:20]
                ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                out_path = os.path.join(
                    PROCESSED_DIR, f'top_tracks_{g}_{ts}.json')
                try:
                    with open(out_path, 'w', encoding='utf-8') as f:
                        json.dump(ranked, f, ensure_ascii=False, indent=2)
                    logger.info('Ranking salvo: %s (top %d)',
                                out_path, len(ranked))
                except Exception as e:
                    logger.warning('Falha ao salvar ranking para %s: %s', g, e)
            except Exception as e:
                logger.warning('Erro no genero %s: %s', g, e)

    try:
        coletar_por_genero(genero, qtd, market)
    except Exception as e:
        logger.exception('Erro durante a coleta: %s', e)

    # --- Batch rotation support -------------------------------------------------
    def _load_rotation_state(path: str) -> dict:
        if not os.path.exists(path):
            return {'genres': [], 'index': 0}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {'genres': [], 'index': 0}

    def _save_rotation_state(path: str, state: dict):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def _fallback_genres() -> List[str]:
        # lista com generos comuns e alguns generos brasileiros
        return [
            'rock', 'pop', 'hiphop', 'electronic', 'jazz', 'classical', 'metal', 'reggae', 'blues', 'folk',
            'country', 'latin', 'soul', 'punk', 'disco', 'funk', 'rnb', 'indie', 'dance', 'samba', 'mpb', 'sertanejo', 'forro', 'pagode', 'bossa nova'
        ]

    def run_batch_genres(batch_size: int, rotation_path: str, market: str = 'BR', force_each: bool = False):
        """Processa `batch_size` generos por execucao, mantendo estado em rotation_path."""
        if batch_size <= 0:
            return
        cid = str(CLIENT_ID or os.getenv('SPOTIFY_CLIENT_ID') or '')
        csecret = str(CLIENT_SECRET or os.getenv(
            'SPOTIFY_CLIENT_SECRET') or '')
        genres = []
        if cid and csecret:
            try:
                token = autenticar_spotify(cid, csecret)
                genres = get_available_genres(token)
            except Exception:
                genres = []
        if not genres:
            genres = _fallback_genres()

        state = _load_rotation_state(rotation_path)
        # if state genres empty, initialize
        if not state.get('genres'):
            state['genres'] = genres
            state['index'] = 0

        current = state.get('index', 0)
        total = len(state['genres'])
        if total == 0:
            logger.warning('Nenhum genero disponivel para rotacao')
            return

        to_process = []
        for i in range(batch_size):
            idx = (current + i) % total
            to_process.append(state['genres'][idx])

        # processar cada genero
        for g in to_process:
            logger.info('Batch coletando genero: %s', g)
            try:
                if force_each:
                    cp = _checkpoint_path_for_genre(g)
                    if os.path.exists(cp):
                        shutil.move(cp, cp + '.bak')
                coletar_por_genero(g, QTD_ARTISTAS, market)
            except Exception as e:
                logger.warning('Erro ao processar genero %s: %s', g, e)

        # advance index
        state['index'] = (current + batch_size) % total
        _save_rotation_state(rotation_path, state)
        logger.info('Rotacao atualizada: index=%d total_genres=%d',
                    state['index'], total)

    # se o usuario solicitou processamento em batch, executa e sai
    if args.batch_genres and args.batch_genres > 0:
        run_batch_genres(args.batch_genres, args.rotation_file,
                         market=market, force_each=force)
