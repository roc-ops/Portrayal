#!/usr/bin/env bash
# Build the full demo bundle: rendered device SVGs + the two JSON indexes.
set -euo pipefail
cd "$(dirname "$0")"
OUT="${1:-library/dist}"

# Lint first. A broken manifest used to render as an empty or partial dist that
# looked like a successful build - failing here instead means that cannot happen.
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library
rm -rf "$OUT"
# ONE PROCESS PER DEVICE, RUN IN PARALLEL. Each device renders from its own
# manifest and writes its own files, so nothing here shares state and the loop
# was serial only because it was written as one. 21 devices went 9.3s -> 1.5s on
# a 12-core box; the gap widens with every device added.
#
# `-P 0` would use as many workers as there is work, which on a few hundred
# devices means a few hundred interpreters at once. Capped at the core count.
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}"
ls library/devices/*/*/device.yaml \
  | xargs -P "$JOBS" -I{} python3 spec/tools/portrayal/render.py {} \
      --library library --out "$OUT" >/dev/null
# The four index passes each walk the whole library and each writes its own
# file - devices.json, components.json, labs.json, gaps.json - and none of them
# reads another's output, so they were serial only by habit. Together they were
# 8.5s of a 17.8s build, the largest single block once lint was fixed.
#
# `wait` without a guard would report success even if one of them failed, so
# each pid is waited on by hand and the first non-zero exit stops the build.
pids=()
for ix in devices_index components_index labs_index gaps_index; do
  python3 "spec/tools/portrayal/$ix.py" --library library --out "$OUT" &
  pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
# DCIM exports: Portrayal is the source of truth, a DCIM is one consumer
# Two NOS profiles x every device is 42 interpreter starts for about 3 seconds
# of actual work, so the same cap applies. `|| true` per item is kept: a device
# that exports nothing is not a build failure.
ls library/devices/*/*/device.yaml \
  | xargs -P "$JOBS" -I{} sh -c '\
      for nos in arcos sonic; do \
        python3 spec/tools/portrayal/nautobot_export.py "$1" --nos "$nos" \
          --out library/exports/nautobot 2>/dev/null || true; \
      done' _ {}
echo "built $(ls "$OUT" | wc -l | tr -d ' ') files -> $OUT"
