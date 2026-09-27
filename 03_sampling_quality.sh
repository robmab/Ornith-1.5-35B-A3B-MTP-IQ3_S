#!/usr/bin/env bash
# El server tiene que estar YA arrancado -- este NO lo relanza (temperature/
# top_p/top_k se mandan por request, pisan el default del server). Ver
# README.md, paso 3.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY=""
for cand in py python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
done
[ -n "$PY" ] || { echo "ERROR: no encuentro py, python3 ni python en el PATH." >&2; exit 1; }
exec "$PY" "$DIR/03_sampling_quality.py" "$@"
