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
# Every stage below runs a tool by path, and by path the tools import whichever
# checkout was pip-installed, not this one. This pins them here and stops the
# build if anything still resolves elsewhere (#561).
. spec/tools/toolchain.sh
IMAGES=(--images)
if [ "${1:-}" = "--no-images" ]; then IMAGES=(--images --no-raster); shift; fi
OUT="${1:-library/dist}"

# PICTURES WITHOUT CAIROSVG FAIL HERE, ONCE (#462), rather than once per device
# inside the parallel export below, and before the build is spent. The exporter
# refuses the same way when it is run on its own.
if [ "${IMAGES[*]}" = "--images" ] && ! python3 -c "import cairosvg" 2>/dev/null; then
  echo "publish.sh: the pictures need cairosvg - pip install -e \".[render]\", or run" >&2
  echo "  ./publish.sh --no-images to write the exports without them" >&2
  exit 1
fi

./build.sh "$OUT"

# From an empty directory, so a file the exporter no longer produces cannot
# survive as a leftover - which is how a renamed device type used to linger.
rm -rf library/exports
# ONE PROCESS PER DEVICE, IN PARALLEL, THE WAY build.sh RENDERS. The YAML is
# under two seconds for the whole library; the pictures behind it were 136
# seconds in one process on 84 devices (#37), because cairosvg rasterises one
# elevation at a time and the loop was serial only because it was written as
# one. Each device reads the build and writes its own files under its own
# manufacturer, so nothing here shares state. Capped at the core count, as in
# build.sh. `xargs` exits non-zero if any device does, and `set -e` stops here.
#
# The module pass is per component rather than per device and writes to
# module-types/ and module-images/, which the device pass never touches - so it
# runs alongside rather than after, and is waited on by pid so its failure is
# not lost behind the device pass succeeding.
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}"
python3 spec/tools/portrayal/dcim_export.py --dist "$OUT" --modules \
  --out library/exports ${IMAGES+"${IMAGES[@]}"} >/dev/null &
modules_pid=$!
python3 -c "import json,sys; print('\n'.join(d['name'] for d in json.load(open(sys.argv[1]))['devices']))" "$OUT/devices.json" \
  | xargs -P "$JOBS" -I{} python3 spec/tools/portrayal/dcim_export.py --dist "$OUT" \
      --out library/exports --device {} ${IMAGES+"${IMAGES[@]}"} >/dev/null
wait "$modules_pid"

# The exports leave with a DCIM the same way dist leaves with a page; the
# licence and NOTICE go with them for the same reason build.sh copies them.
cp LICENSE NOTICE library/exports/
echo "exported $(find library/exports -name '*.yaml' | wc -l | tr -d ' ') documents -> library/exports"
