#!/usr/bin/env bash
# Helper para rodar um batch de coleta (um genero) — seguro para ser chamado por cron
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGDIR="$DIR/logs"
mkdir -p "$LOGDIR"

# Se existir .env local, exporta as variaveis (permitir credenciais locais por segurança)
if [ -f "$DIR/.env" ]; then
  # exporta as variaveis definidas em .env
  set -a
  # shellcheck disable=SC1090
  . "$DIR/.env"
  set +a
fi

PY="$DIR/.venv/bin/python"
SCRIPT="$DIR/coleta_spotify.py"
ROTATION_FILE="$DIR/data/checkpoints/genre_rotation.json"

TS=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$LOGDIR/collector_${TS}.log"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting batch_genres=1" >> "$OUT"
"$PY" "$SCRIPT" --no-interactive --batch-genres 1 --rotation-file "$ROTATION_FILE" >> "$OUT" 2>&1 || echo "Batch failed (see $OUT)" >> "$OUT"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Finished" >> "$OUT"

# Optional: keep just the last 100 logs
ls -1t "$LOGDIR"/collector_*.log | sed -n '101,$p' | xargs -r rm -f

exit 0
