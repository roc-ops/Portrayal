#!/usr/bin/env bash
# Everything build.sh makes, plus the consumer artifacts: the DCIM exports.
#
# WHY THIS IS A SEPARATE SCRIPT. The export was half of `build.sh` - 39 seconds
# against 41 for the lint, the render and the indexes together - and its output
# is read by exactly one test and by nothing on the page. Paying for it on every
# edit bought nothing; paying for it when the artifacts are published is the
# whole of what it is for.
#
# IT READS THE BUILD, NOT THE LIBRARY. `dcim_export.py --dist` opens nothing
# under library/devices or library/components, so this script is two independent
# steps rather than one long one: anything that can produce a `dist/` can produce
# the exports, here or somewhere else.
#
# `--no-images` SKIPS RENDERING THE PNGs AND NOTHING ELSE. Every one of the 1104
# pictures under library/exports is gitignored, so CI builds them and throws
# them away. It does NOT drop the `front_image: true` lines from the YAML -
# those are tracked, a DCIM reads them, and the first attempt at this deleted
# 692 of them across 346 files because one flag drove both jobs.
# A local run still gets the pictures by default: looking at a card's
# faceplate is the whole reason they exist.
#
#   ./publish.sh [--no-images] [OUT]        default OUT is library/dist
set -euo pipefail
cd "$(dirname "$0")"
IMAGES=(--images)
if [ "${1:-}" = "--no-images" ]; then IMAGES=(--images --no-raster); shift; fi
OUT="${1:-library/dist}"

./build.sh "$OUT"

# From an empty directory, so a file the exporter no longer produces cannot
# survive as a leftover - which is how a renamed device type used to linger.
rm -rf library/exports
python3 spec/tools/portrayal/dcim_export.py --dist "$OUT" \
  --out library/exports --nos arcos --nos sonic ${IMAGES+"${IMAGES[@]}"} >/dev/null
# Module types are per component, not per device: one pass over the index.
# --images for the same reason the device pass takes it - it also renders each
# card's faceplate into module-images/. *.png is gitignored, so this costs the
# repository nothing and gives a local run the pictures.
python3 spec/tools/portrayal/dcim_export.py --dist "$OUT" --modules \
  --out library/exports ${IMAGES+"${IMAGES[@]}"} >/dev/null

echo "exported $(find library/exports -name '*.yaml' | wc -l | tr -d ' ') documents -> library/exports"
