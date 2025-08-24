import json
import os
from unittest.mock import MagicMock, patch

import pytest

import coleta_spotify as cs


def make_artist(i):
    return {'id': f'id{i}', 'name': f'Artist {i}'}


@patch('coleta_spotify.requests.request')
def test_buscar_artistas_paginacao(mock_request, tmp_path):
    # simulate two pages: first returns 3 items, second 2 items
    page1 = {'artists': {'items': [make_artist(i) for i in range(3)]}}
    page2 = {'artists': {'items': [make_artist(i) for i in range(3, 5)]}}
    resp1 = MagicMock()
    resp1.status_code = 200
    resp1.json.return_value = page1
    resp2 = MagicMock()
    resp2.status_code = 200
    resp2.json.return_value = page2
    mock_request.side_effect = [resp1, resp2]

    # call with limit 5 and small page_size to force pagination
    result = cs.buscar_artistas_por_genero(
        'rock', token='t', limit=5, page_size=3)
    assert len(result) == 5


def test_processar_e_salvar_particao(tmp_path, monkeypatch):
    # prepare dirs
    monkey_dir = tmp_path / 'data'
    monkey_dir_raw = monkey_dir / 'raw'
    monkey_dir_proc = monkey_dir / 'processed'
    monkey_dir_raw.mkdir(parents=True)
    monkey_dir_proc.mkdir(parents=True)
    monkey_dir_proc_genre = monkey_dir_proc / 'rock'
    # set global base dirs
    cs.RAW_DIR = str(monkey_dir_raw)
    cs.PROCESSED_DIR = str(monkey_dir_proc)

    artista = {'name': 'Teste Banda', 'id': '123'}
    tracks = [{'name': 'Musica 1', 'popularity': 50,
               'preview_url': None, 'id': 't1', 'duration_ms': 180000}]

    out = cs.processar_e_salvar(artista, tracks, 'rock')
    assert os.path.exists(out)
    # assert path contains genre partition
    assert os.path.join('processed', 'rock') in out.replace(
        '\\', '/') or 'rock' in out
