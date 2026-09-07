#!/usr/bin/env bash
# Build what the tests, the linter and the viewer read: rendered device SVGs
# and the JSON indexes. NOT the DCIM exports - see publish.sh.
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
# viewer is consistent. Repeatable.
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
# The six index passes each walk the whole library and each writes its own
# file - devices.json, components.json, labs.json, gaps.json, comparable-facts.json, and
# vendors.json + overlays.json - and none reads another's output, so they were serial
# only by habit. Together they were 8.5s of a 17.8s build, the largest single
# block once lint was fixed.
#
# `wait` without a guard would report success even if one of them failed, so
# each pid is waited on by hand and the first non-zero exit stops the build.
pids=()
for ix in devices_index components_index labs_index gaps_index registry_index comparable_index; do
  python3 "spec/tools/portrayal/$ix.py" --library library --out "$OUT" &
  pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
# THE DCIM EXPORT IS NOT PART OF THIS BUILD, and used to be half of it: 39
# seconds against 41 for everything else, on a stage whose output exactly one
# test reads and nothing on the page does. `./publish.sh` is this plus the
# exports, and is what runs when the artifacts are published.
# The dist is the artifact set a consumer takes without a checkout, and
# Apache-2.0 asks a redistribution to carry the NOTICE. So it travels with it.
cp LICENSE NOTICE "$OUT"/
echo "built $(ls "$OUT" | wc -l | tr -d ' ') files -> $OUT"
