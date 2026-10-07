#!/usr/bin/env bash
# Build what the tests, the linter and the viewer read: rendered device SVGs
# and the JSON indexes. NOT the DCIM exports - see publish.sh.
set -euo pipefail
cd "$(dirname "$0")"
# Every stage below runs a tool by path, and by path the tools import whichever
# checkout was pip-installed, not this one. This pins them here and stops the
# build if anything still resolves elsewhere (#561).
. spec/tools/toolchain.sh
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
#
# `--no-lint` IS FOR ONE CALLER AND IT SAYS SO. CI runs lint as its own job
# before this one starts, so linting again here is the same answer bought twice
# at 27s a time, and a third time inside `test_lint_green` (#183). Nothing else
# should pass it: locally the whole point is that a bad manifest never reaches
# the renderer, and skipping the check to save half a minute is how the partial
# dist that looked successful came back.
if [ "${NO_LINT:-0}" != 1 ]; then
  LINTSEL=()
  for d in ${DEVSEL+"${DEVSEL[@]}"}; do LINTSEL+=(--device "$d"); done
  python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library \
    ${LINTSEL+"${LINTSEL[@]}"}
fi
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
# WARM THE RENDERS' SHARED CACHES ONCE, BEFORE THE PARALLEL WAVE (#544). Every
# render reads L62's vocabulary (#542) and the pluggable candidate selection
# (#543) from a disk cache keyed by the library's content. From an empty cache -
# CI's, every run, since NO_LINT=1 skips the lint pass that would otherwise
# have filled it - the first $JOBS renders all start before any of them has
# written an entry, so each computes the same answer. This computes it once,
# with the functions the renders call and on the roots they are given. It
# changes no output: a warm cache answers exactly what a cold one computes,
# and if the cache cannot be written the renders simply compute as before.
python3 -c "
import sys
from portrayal import lint, render
lint._id_corpus(sys.argv[1:])
render._pluggable_candidates(sys.argv[1:])
" library
device_list \
  | xargs -P "$JOBS" -I{} python3 spec/tools/portrayal/render.py {} \
      --library library --out "$OUT" ${STALE+"${STALE[@]}"} >/dev/null
# The six index passes each walk the whole library and each writes its own
# file - devices.json, components.json, labs.json, gaps.json, comparable-facts.json, and
# vendors.json + listings.json - and none reads another's output, so they were serial
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
# THE COMPONENT CATALOGUE, beside the indexes because it is one more walk of the
# library that reads nothing they write. It goes to library/components/, where
# the components README sends a contributor, and not into "$OUT": it is a page
# for whoever is about to draw a part, not something a consumer of the dist
# reads. Gitignored, so a build is what keeps it current.
python3 spec/tools/portrayal/components_catalogue.py --library library \
  --out library/components/CATALOGUE.md &
pids+=("$!")
for pid in "${pids[@]}"; do wait "$pid"; done
# THE RACK CATALOGUE reads devices.json and the compiled faces, so it runs
# after both exist: rack.json, which the kit's rack/catalog.js loads.
python3 spec/tools/portrayal/rack_index.py --dist "$OUT"
# THE LOCK, ASSEMBLED. Each device carries its own `device.lock.json` beside its
# manifest (#182); this is the one-file view, for a consumer outside the
# checkout that wants the whole picture in one fetch - the same reason
# devices.json is here. Derived, so it cannot drift from the sources.
python3 -c "
import pathlib, sys
from portrayal import devicelock
devicelock.aggregate(pathlib.Path('library'), pathlib.Path(sys.argv[1]) / 'devices.lock.json')
" "$OUT"
# THE DCIM EXPORT IS NOT PART OF THIS BUILD, and used to be half of it: 39
# seconds against 41 for everything else, on a stage whose output exactly one
# test reads and nothing on the page does. `./publish.sh` is this plus the
# exports, and is what runs when the artifacts are published.
# The dist is the artifact set a consumer takes without a checkout, and
# Apache-2.0 asks a redistribution to carry the NOTICE. So it travels with it.
cp LICENSE NOTICE "$OUT"/
echo "built $(ls "$OUT" | wc -l | tr -d ' ') files -> $OUT"
