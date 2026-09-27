#!/usr/bin/env bash
# El server tiene que estar YA arrancado. Ver README.md.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY=""
for cand in py python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
done
[ -n "$PY" ] || { echo "ERROR: no encuentro py, python3 ni python en el PATH." >&2; exit 1; }
exec "$PY" "$DIR/benchmark_quick.py" "$@"
