import json
import os
import sqlite3

import coleta_spotify as cs


def test_db_insert(tmp_path, monkeypatch):
    # setup temp data dir
    monkey_dir = tmp_path / 'data'
    monkey_dir.mkdir()
    monkeypatch.setenv('DATA_DIR', str(monkey_dir))
    cs.DATA_DIR = str(monkey_dir)
    cs.PROCESSED_DIR = os.path.join(str(monkey_dir), 'processed')
    cs.RAW_DIR = os.path.join(str(monkey_dir), 'raw')
    os.makedirs(cs.PROCESSED_DIR, exist_ok=True)
    os.makedirs(cs.RAW_DIR, exist_ok=True)

    artista = {'id': 'a1', 'name': 'Artist 1'}
    tracks = [{'id': 't1', 'name': 'Track 1', 'popularity': 10,
               'preview_url': None, 'duration_ms': 1000}]

    out = cs.processar_e_salvar(artista, tracks, 'rock')
    db_path = os.path.join(str(monkey_dir), 'spotify.db')
    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT track_id, track_name FROM tracks WHERE artist_id = ?", ('a1',))
    rows = cur.fetchall()
    conn.close()
    assert ('t1', 'Track 1') in rows
