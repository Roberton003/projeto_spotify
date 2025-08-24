import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List


def init_db(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS tracks (
        artist_id TEXT,
        artist_name TEXT,
        genre TEXT,
        track_id TEXT,
        track_name TEXT,
        popularity INTEGER,
        preview_url TEXT,
        duration_ms INTEGER,
        collected_at TEXT,
        PRIMARY KEY (artist_id, track_id)
    )
    ''')
    conn.commit()
    conn.close()


def insert_artist_tracks(db_path: str, artista: Dict, tracks: List[Dict], genero: str):
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    collected_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    artist_id = str(artista.get('id') or '')
    artist_name = artista.get('name') or ''
    rows = []
    for t in tracks:
        rows.append((artist_id, artist_name, genero, t.get('id'), t.get('name'), t.get(
            'popularity'), t.get('preview_url'), t.get('duration_ms'), collected_at))
    cur.executemany('''
        INSERT OR REPLACE INTO tracks (artist_id, artist_name, genre, track_id, track_name, popularity, preview_url, duration_ms, collected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', rows)
    conn.commit()
    conn.close()
