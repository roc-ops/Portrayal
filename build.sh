#!/usr/bin/env bash
# Build the full demo bundle: rendered device SVGs + the two JSON indexes.
set -euo pipefail
cd "$(dirname "$0")"
OUT="${1:-ndv-library/dist}"
rm -rf "$OUT"
for d in ndv-library/devices/*/*/device.yaml; do
  python3 ndv-spec/tools/ndv/render.py "$d" --library ndv-library --out "$OUT" >/dev/null
done
python3 ndv-spec/tools/ndv/devices_index.py    --library ndv-library --out "$OUT"
python3 ndv-spec/tools/ndv/components_index.py --library ndv-library --out "$OUT"
echo "built $(ls "$OUT" | wc -l | tr -d ' ') files -> $OUT"
