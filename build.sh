#!/usr/bin/env bash
# Build the publishable artifacts: rendered device SVGs + the JSON indexes.
set -euo pipefail
cd "$(dirname "$0")"
# `--fast` renders only what changed. FULL IS THE DEFAULT and stays that way:
# a staleness check that is wrong produces a drawing that looks fresh and is
# believed, which is worse than a slow build, so the gate does not depend on it.
# The dependency walk errs the other way - all of a component's skins count,
# and so does the renderer itself - so `--fast` rebuilds more than it must.
#
# `--device NAME` is the edit-check loop: lint that device against only the
# components it reaches, re-render just it, and refresh the indexes so the
# viewer is consistent. It does NOT run the DCIM export, which is a consumer
# artifact nothing on the page reads. Repeatable.
FAST=0
DEVSEL=()
while [ $# -gt 0 ]; do
  case "$1" in
    --fast|-f) FAST=1; shift ;;
    --device) DEVSEL+=("$2"); FAST=1; shift 2 ;;
    --) shift; break ;;
    *) break ;;
  esac
done
OUT="${1:-library/dist}"

# Lint first. A broken manifest used to render as an empty or partial dist that
# looked like a successful build - failing here instead means that cannot happen.
LINTSEL=()
for d in ${DEVSEL+"${DEVSEL[@]}"}; do LINTSEL+=(--device "$d"); done
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library \
  ${LINTSEL+"${LINTSEL[@]}"}
STALE=()
if [ "$FAST" = 1 ]; then
  STALE=(--if-stale)
else
  rm -rf "$OUT"
fi
# ONE PROCESS PER DEVICE, RUN IN PARALLEL. Each device renders from its own
# manifest and writes its own files, so nothing here shares state and the loop
# was serial only because it was written as one. 21 devices went 9.3s -> 1.5s on
# a 12-core box; the gap widens with every device added.
#
# `-P 0` would use as many workers as there is work, which on a few hundred
# devices means a few hundred interpreters at once. Capped at the core count.
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}"
device_list() {
  if [ ${#DEVSEL[@]} -eq 0 ]; then
    ls library/devices/*/*/device.yaml
  else
    for d in "${DEVSEL[@]}"; do ls library/devices/*/*/device.yaml | grep -- "$d"; done
  fi
}
device_list \
  | xargs -P "$JOBS" -I{} python3 spec/tools/portrayal/render.py {} \
      --library library --out "$OUT" ${STALE+"${STALE[@]}"} >/dev/null
# The five index passes each walk the whole library and each writes its own
# file - devices.json, components.json, labs.json, gaps.json, and vendors.json
# + overlays.json - and none of them reads another's output, so they were serial
# only by habit. Together they were 8.5s of a 17.8s build, the largest single
# block once lint was fixed.
#
# `wait` without a guard would report success even if one of them failed, so
# each pid is waited on by hand and the first non-zero exit stops the build.
pids=()
for ix in devices_index components_index labs_index gaps_index registry_index; do
  python3 "spec/tools/portrayal/$ix.py" --library library --out "$OUT" &
  pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
# DCIM exports: Portrayal is the source of truth, a DCIM is one consumer.
#
# One device type per SKU, for NetBox and Nautobot alike, with elevation images
# rendered from the compiled faces. Errors are NOT swallowed: the old loop hid
# every failure behind `2>/dev/null || true`, which is how a device silently
# stopped exporting.
#
# Runs one process per device under the same worker cap as the render pass, and
# skips entirely on a --device build: the exports are a whole-library artefact
# and half of one is worse than yesterday's.
#
# IT READS THE BUILD, NOT THE LIBRARY. The export takes `--dist` and opens
# nothing under library/devices or library/components: the compiled SVG carries
# the device manifest, components.json the contract fields, vendors.json and
# overlays.json the registries. That is what lets it move out of this repository
# without moving the library with it.
if [ ${#DEVSEL[@]} -eq 0 ]; then
  rm -rf library/exports
  python3 spec/tools/portrayal/dcim_export.py --dist "$OUT" \
    --out library/exports --nos arcos --nos sonic --images >/dev/null
  # Module types are per component, not per device: one pass over the index.
  # --images for the same reason the device pass takes it: it also renders each
  # card's faceplate into module-images/. *.png is gitignored, so this costs the
  # repository nothing and gives a local build the pictures.
  python3 spec/tools/portrayal/dcim_export.py --dist "$OUT" --modules \
    --out library/exports --images >/dev/null
fi
echo "built $(ls "$OUT" | wc -l | tr -d ' ') files -> $OUT"
