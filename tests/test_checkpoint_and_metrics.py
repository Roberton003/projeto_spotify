import json
import os
from unittest.mock import MagicMock, patch

import coleta_spotify as cs


@patch('coleta_spotify.buscar_artistas_por_genero')
@patch('coleta_spotify.buscar_top_tracks')
@patch('coleta_spotify.autenticar_spotify')
def test_checkpoint_and_metrics(mock_auth, mock_top, mock_busca, tmp_path, monkeypatch):
    # Setup: two artists, simulate first run processes both, second run skips processed
    a1 = {'id': 'a1', 'name': 'A1'}
    a2 = {'id': 'a2', 'name': 'A2'}
    mock_auth.return_value = 'token'
    mock_busca.return_value = [a1, a2]
    mock_top.return_value = [{'name': 't1', 'popularity': 10,
                              'preview_url': None, 'id': 't1', 'duration_ms': 1000}]

    # point data dir to tmp
    monkey_dir = tmp_path / 'data'
    monkey_dir.mkdir()
    monkeypatch.setenv('DATA_DIR', str(monkey_dir))
    cs.DATA_DIR = str(monkey_dir)
    cs.RAW_DIR = os.path.join(str(monkey_dir), 'raw')
    cs.PROCESSED_DIR = os.path.join(str(monkey_dir), 'processed')

    os.makedirs(cs.RAW_DIR, exist_ok=True)
    os.makedirs(cs.PROCESSED_DIR, exist_ok=True)

    # first run
    res1 = cs.coletar_por_genero('rock', qtd_artistas=2, market='BR')
    # checkpoint file exists
    cp = cs._checkpoint_path_for_genre('rock')
    assert os.path.exists(cp)
    with open(cp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert set(data.get('processed_artists', [])) == {'a1', 'a2'}

    # second run: buscar_artistas_por_genero returns same artists, but they should be skipped
    res2 = cs.coletar_por_genero('rock', qtd_artistas=2, market='BR')
    # res2 should be empty because all were already processed
    assert res2 == []
