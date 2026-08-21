#!/usr/bin/env bash
# Build the full demo bundle: rendered device SVGs + the two JSON indexes.
set -euo pipefail
cd "$(dirname "$0")"
OUT="${1:-ndv-library/dist}"

# Lint first. A broken manifest used to render as an empty or partial dist that
# looked like a successful build - failing here instead means that cannot happen.
python3 ndv-spec/tools/ndv/lint.py --schemas ndv-spec/schemas --library ndv-library
rm -rf "$OUT"
for d in ndv-library/devices/*/*/device.yaml; do
  python3 ndv-spec/tools/ndv/render.py "$d" --library ndv-library --out "$OUT" >/dev/null
done
python3 ndv-spec/tools/ndv/devices_index.py    --library ndv-library --out "$OUT"
python3 ndv-spec/tools/ndv/components_index.py --library ndv-library --out "$OUT"
python3 ndv-spec/tools/ndv/labs_index.py       --library ndv-library --out "$OUT"
# DCIM exports: NDV is the source of truth, a DCIM is one consumer
for d in ndv-library/devices/*/*/device.yaml; do
  for nos in arcos sonic; do
    python3 ndv-spec/tools/ndv/nautobot_export.py "$d" --nos "$nos" \
      --out ndv-library/exports/nautobot 2>/dev/null || true
  done
done
echo "built $(ls "$OUT" | wc -l | tr -d ' ') files -> $OUT"
