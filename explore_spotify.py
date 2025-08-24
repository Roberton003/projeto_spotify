"""Script de exploracao: coleta um snapshot pequeno e gera um parquet processado.

Uso: copiar `.env.template` -> `.env` com suas credenciais Spotify e rodar:
  python explore_spotify.py

O script:
 - chama `coleta_spotify.coletar_por_genero` para obter raw + processados (por artista)
 - combina arquivos JSON em `data/processed/` em um único Parquet com timestamp
 - gera `data/processed/manifest_{ts}.json` com contagens
"""
import glob
import json
import logging
import os
from datetime import datetime

import pandas as pd

import coleta_spotify as cs

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def combinar_processados(genero: str) -> str:
    files = glob.glob(os.path.join(cs.PROCESSED_DIR, f'*_{genero}.json'))
    if not files:
        logger.warning(
            'Nenhum arquivo processado encontrado para o genero: %s', genero)
        return ''

    rows = []
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            for r in data:
                r['_source_file'] = os.path.basename(f)
                rows.append(r)
        except Exception as e:
            logger.exception('Falha ao ler %s: %s', f, e)

    if not rows:
        logger.warning('Nenhuma linha combinada para %s', genero)
        return ''

    df = pd.DataFrame(rows)
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    out_path = os.path.join(
        cs.PROCESSED_DIR, f'top_tracks_{genero}_{ts}.parquet')
    df.to_parquet(out_path, index=False)
    logger.info('Parquet gerado: %s (linhas=%d)', out_path, len(df))
    # salvar manifest
    manifest = {'generated_at': ts, 'genre': genero, 'rows': len(
        df), 'files': [os.path.basename(x) for x in files]}
    manifest_path = os.path.join(
        cs.PROCESSED_DIR, f'manifest_{genero}_{ts}.json')
    with open(manifest_path, 'w', encoding='utf-8') as mf:
        json.dump(manifest, mf, ensure_ascii=False, indent=2)
    logger.info('Manifest salvo: %s', manifest_path)
    return out_path


def main():
    genero = os.getenv('SPOTIFY_GENERO', 'rock')
    qtd = int(os.getenv('SPOTIFY_QTD_ARTISTAS', '10'))
    logger.info('Iniciando snapshot: genero=%s qtd_artistas=%d', genero, qtd)

    # coleta (salva raw + processed por artista)
    try:
        cs.coletar_por_genero(genero, qtd, market='BR')
    except Exception as e:
        logger.exception('Coleta falhou: %s', e)
        return

    # combina processados em parquet
    out = combinar_processados(genero)
    if out:
        logger.info('Snapshot completo. Parquet: %s', out)
    else:
        logger.warning('Snapshot finalizado sem parquet gerado.')


if __name__ == '__main__':
    main()
