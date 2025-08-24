import json
import os
import tempfile
from unittest.mock import patch

import pytest

import coleta_spotify as cs


def test_autenticar_spotify_missing_env(monkeypatch):
    # Remove env vars
    monkeypatch.delenv('SPOTIFY_CLIENT_ID', raising=False)
    monkeypatch.delenv('SPOTIFY_CLIENT_SECRET', raising=False)
    with pytest.raises(RuntimeError):
        cs.autenticar_spotify(None, None)


@patch('coleta_spotify.requests.request')
def test_autenticar_spotify_success(mock_request, monkeypatch):
    mock_resp = mock_request.return_value
    mock_resp.status_code = 200
    mock_resp.json.return_value = {'access_token': 'fake-token'}
    token = cs.autenticar_spotify('id', 'secret')
    assert token == 'fake-token'


def test_processar_e_salvar(tmp_path):
    # cria um artista e tracks fake e verifica arquivo salvo
    artista = {'name': 'Teste Banda', 'id': '123'}
    tracks = [{'name': 'Musica 1', 'popularity': 50,
               'preview_url': None, 'id': 't1', 'duration_ms': 180000}]
    # redireciona pastas de processados para tmp
    monkey_dir = tmp_path / 'data'
    monkey_dir_raw = monkey_dir / 'raw'
    monkey_dir_proc = monkey_dir / 'processed'
    monkey_dir_raw.mkdir(parents=True)
    monkey_dir_proc.mkdir(parents=True)
    cs.PROCESSED_DIR = str(monkey_dir_proc)
    out = cs.processar_e_salvar(artista, tracks, 'rock')
    assert os.path.exists(out)
    with open(out, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    assert dados[0]['musica'] == 'Musica 1'
