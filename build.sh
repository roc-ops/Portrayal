#!/usr/bin/env bash
# Build the full demo bundle: rendered device SVGs + the two JSON indexes.
set -euo pipefail
cd "$(dirname "$0")"
OUT="${1:-library/dist}"

# Lint first. A broken manifest used to render as an empty or partial dist that
# looked like a successful build - failing here instead means that cannot happen.
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library
rm -rf "$OUT"
for d in library/devices/*/*/device.yaml; do
  python3 spec/tools/portrayal/render.py "$d" --library library --out "$OUT" >/dev/null
done
python3 spec/tools/portrayal/devices_index.py    --library library --out "$OUT"
python3 spec/tools/portrayal/components_index.py --library library --out "$OUT"
python3 spec/tools/portrayal/labs_index.py       --library library --out "$OUT"
python3 spec/tools/portrayal/gaps_index.py       --library library --out "$OUT"
# DCIM exports: Portrayal is the source of truth, a DCIM is one consumer
for d in library/devices/*/*/device.yaml; do
  for nos in arcos sonic; do
    python3 spec/tools/portrayal/nautobot_export.py "$d" --nos "$nos" \
      --out library/exports/nautobot 2>/dev/null || true
  done
done
echo "built $(ls "$OUT" | wc -l | tr -d ' ') files -> $OUT"
