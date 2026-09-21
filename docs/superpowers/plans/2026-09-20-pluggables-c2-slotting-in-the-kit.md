# Pluggables C2: slotting in the kit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A pluggable cage is swappable in the explorer the way a bay is — pick an optic from the derived accept list, and the 2D drawing and the 3D scene both show it seated exactly where the build would seat it; the swap survives a reload.

**Architecture:** The build is the single source of seating geometry: it learns to seat an occupant in a ROTATED cage (it cannot today), and publishes each cage's device-frame mate point, lift and the attributes an occupant inherits, so the kit never re-derives mate forwarding. `swap.js` gains `seatOccupant` beside `seatModule` (one module, two callers — `shell.js` on the live DOM, `viewer3d.js` on fetched face text). The explorer carries one swap map (bays AND cages) in its URL, and the `m1.` share codec gains a trailing slot for it.

**Tech Stack:** Python 3 build (`spec/tools/portrayal/render.py`, `components_index.py`), plain ES-module JS kit (`kit/*.js`, no bundler, no jsdom), pytest driving node scripts under `spec/tests/js/`.

**Spec:** `docs/pluggables-slotting-design.md` (Kit side; Order of work items 3-5). Umbrella: `docs/pluggables-design.md`. C1 (ladder registry, `cages[]`, L101-L104) is merged as roc-ops/Portrayal#435.

## Global Constraints

- `PYTHONPATH=spec/tools` on EVERY portrayal / pytest command. A bare `python -m portrayal` measures a different checkout. Before believing a suspiciously clean gate, check `git -C /Volumes/External/Network-Device-Visualization/.claude/worktrees/toolchain log --oneline -1` against `origin/main`.
- Run the suite with `-n auto`; a single-process run aborts at collection.
- NEVER `git add -A`. Stage explicit paths. Other agents share this tree.
- NO BACKTICKS in commit messages: write the message to a file, check `grep -c`, then `git commit -F <file>`.
- `working/` is NEVER committed.
- NEVER launder an estimate into a measurement.
- Version bumps go in BEFORE `lock --update`.
- Never bare `git stash` / `git stash pop`.
- COMMIT BEFORE running the full suite.
- Commit trailer: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- Do NOT push, open a PR, or merge.
- The kit consumes compiled artifacts only — it never reads YAML (kit/package.json's own description).
- The two-callers-one-home rule (`kit/swap.js` header): seating surgery lives in `swap.js` and nowhere else.
- Nothing about seating is solved twice: where the kit must repeat a formula the build owns, a test holds the two to the same numbers from a REAL build.
- Portrayal ships no populated device. No shipped manifest gains an `occupants:` entry; tests seat on COPIES in `tmp_path` (the `spec/tests/test_occupants.py` idiom).

## Decisions already made (do not relitigate)

- **D1 — swap persistence covers bays AND cages** (Jason, 2026-09-20). The spec says cage swaps go in the share URL "the way bay swaps are"; bay swaps are in fact persisted nowhere today (explorer URL carries only `?device=`; the `m1.` codec carries device/config/view/legend/marks/crop). One swap map, both kinds, in the explorer URL and as a new trailing `m1.` slot.
- **D2 — the build is fixed to seat in a rotated cage first.** Measured: 941 of 3326 cages are rotated (940 at 180 degrees, one at 90 on `juniper/mx304`). The build seats an occupant by `translate(host.at + host_mate - occ_mate)` with no rotation, so on a fitted copy of `ufispace/s9510-28dc`, `port-2` renders `translate(229.8,8.8) rotate(180 9.75 5.09)` and its occupant `translate(230.45,9.94)` — the same offset as the upright `port-0`, un-turned. The kit must match the build, so the build is corrected before the kit copies it.
- **D3 — a seated part turns with its host.** An occupant takes its host's `rotate`, and its position is solved so its own `mate` point lands on the host's ROTATED mate point. A `mate-to` placement that declares its own `rotate` different from its host's is an error ("a seated part turns with its host"). A mirrored host with a seated occupant is an error — none exists today, and handedness of a seated optic is not a question this spec answers.
- **D4 — out of scope:** a cage inside a seated module (spec open question 2 — `cages[]` lists device-level placements only, as C1 built it); the `optics-<media>` tooltip (spec open question 1); plugs and boots seated in optics from the kit (the candidate pool already excludes them, per C1). Because nested cages are out, the spec's third named test file - `nested-bays` - gains NO cage case in C2; that belongs with open question 2.

## File map

| file | change |
|---|---|
| `spec/tools/portrayal/render.py` | `seat_point` / `seat_at` helpers; `mate-to` resolution turns the occupant with its host; `cages[]` entries gain `mate`, `lift`, `occupant-attrs` |
| `spec/tools/portrayal/components_index.py` | each entry gains `mate: [x, y]` when its contract declares `connection-points.mate` |
| `kit/swap.js` | `occupantAt`, `occupantTransform`, `rename` gains a `segment` argument, `seatOccupant`, `applyOccupantOverrides` |
| `kit/viewer3d.js` | `applyBayOverrides` also seats cage overrides |
| `kit/shell.js` | `cageFor`, `state.cfgOccupants`, the occupant select on a cage row, `swapCage`, an occupant row inspects as its host |
| `kit/index.html` | `swapOverrides` covers cages; the explorer URL reads and writes `config`, `view`, `swap` |
| `kit/marks.js` | `normalise` / `encode` / `decode` carry `swaps` in a trailing slot |
| `spec/tests/test_seat_rotation.py` | new — the build seats in a rotated cage |
| `spec/tests/test_occupants.py` | the rotated-cage case |
| `spec/tests/test_cage_accepts.py` | `mate` / `lift` / `occupant-attrs` on published entries |
| `spec/tests/js/cage-seat.mjs` + `spec/tests/test_cage_seat_js.py` | new — kit seating against a real build |
| `spec/tests/js/swap-state.mjs` + `spec/tests/test_swap_state_js.py` | new — URL + codec round trip and back-compat |

---

### Task 1: The build seats an occupant in a rotated cage, and publishes where

**Files:**
- Modify: `spec/tools/portrayal/render.py` (mate-to resolution ~`:1740-1815`; `cage_entries` ~`:2549`; the `cages` key documentation in `main()`)
- Modify: `spec/tools/portrayal/components_index.py`
- Create: `spec/tests/test_seat_rotation.py`
- Modify: `spec/tests/test_occupants.py`, `spec/tests/test_cage_accepts.py`

**Interfaces:**
- Produces (Python, `render.py`):
  - `seat_point(at, size, rotate, local) -> [x, y]` — where a point `local` in a placement's own frame lands in the device frame, for a placement drawn `translate(at) rotate(deg w/2 h/2)` (the `else` branch of `instance_group`'s transform, `render.py:~715`). Rounded to 4 dp.
  - `seat_at(point, rotate, occ_size, occ_mate) -> [x, y]` — the `at` for an occupant drawn the same way that puts its `occ_mate` on `point`.
- Produces (published data, consumed by Tasks 2-4):
  - every `cages[view][]` entry gains `"mate": [x, y]` (device frame, rotation applied), `"lift": <float>` (the host's presented lift, what `mate-to` resolution would carry as `host-lift`), and `"occupant-attrs": {<data-attr name>: <string>}` — every attribute the build writes on a seated occupant that comes from the HOST'S side (its port group's attrs, `data-group`, `data-group-role`, and anything else the build merges from the host) rather than from the occupant's own contract.
  - every `components.json` entry whose contract has `connection-points.mate` gains `"mate": [x, y]` (the contract's own `mate.at`, NOT forwarded — an occupant mates with its own point, L11).

The rotation convention (SVG, y down; a positive angle turns clockwise on screen):

```python
import math

def _turn(v, rotate):
    """Rotate vector v by `rotate` degrees, SVG convention (x' = x cos - y sin,
    y' = x sin + y cos). Exact for the right angles the corpus uses."""
    deg = float(rotate or 0) % 360
    exact = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1)}
    c, s = exact.get(deg, (math.cos(math.radians(deg)), math.sin(math.radians(deg))))
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def seat_point(at, size, rotate, local):
    """Where `local` (a point in a placement's own frame) lands in the device
    frame, for a placement drawn translate(at) rotate(deg w/2 h/2)."""
    cx, cy = size["w"] / 2, size["h"] / 2
    dx, dy = _turn((local[0] - cx, local[1] - cy), rotate)
    return [round(at[0] + cx + dx, 4), round(at[1] + cy + dy, 4)]


def seat_at(point, rotate, occ_size, occ_mate):
    """The `at` that lands an occupant's `occ_mate` on `point` when the
    occupant is drawn translate(at) rotate(deg w/2 h/2) - the inverse of
    seat_point for the occupant."""
    cx, cy = occ_size["w"] / 2, occ_size["h"] / 2
    dx, dy = _turn((occ_mate[0] - cx, occ_mate[1] - cy), rotate)
    return [round(point[0] - cx - dx, 4), round(point[1] - cy - dy, 4)]
```

At `rotate` 0 these reduce EXACTLY to today's `host.at + hm_at - om["at"]`, so every unrotated seat in the corpus is byte-identical afterwards — the test in Step 1 asserts that.

- [ ] **Step 1: Write the failing tests** — `spec/tests/test_seat_rotation.py`:
  - unit: `seat_point`/`seat_at` at 0, 90, 180, 270 on a 10x4 box with an off-centre point, each checked against hand arithmetic written in the test (not recomputed with `_turn`), and `seat_point(seat_at(P, r, s, m) ...)` round-trips `m` onto `P` for all four angles.
  - unit: at `rotate` 0 or None, `seat_at(seat_point(at, hs, 0, hm), 0, os, om) == [at[0] + hm[0] - om[0], at[1] + hm[1] - om[1]]` — the no-change guarantee for unrotated seats.
  - integration (fitted copy of `library/devices/ufispace/s9510-28dc`, seating `generic/qsfp-lc@1` in `port-2` — rotate 180 — and `port-0` — upright — via the `dc` configuration's `occupants:`; reuse the `fitted_copy`/`render` shape from `test_occupants.py`): parse both occupants' `transform`; the rotated one carries `rotate(180 ...)`; apply each group's transform to its own `mate` (read from the occupant contract) and to the host's presented mate (`manifest.presented_interface`) and assert the two device-frame points agree to 1e-6 for BOTH ports. Parse transforms numerically — Python prints `9.0` where JS prints `9`, so string comparison is wrong.
  - error cases on a fitted copy: a hand-written `mate-to` placement with a `rotate` different from its host's raises with "turns with its host"; a mirrored host raises.
- [ ] **Step 2: Run to see them fail** — `PYTHONPATH=spec/tools python3 -m pytest spec/tests/test_seat_rotation.py -q`. Expected: ImportError / assertion failures on the rotated case.
- [ ] **Step 3: Implement** the helpers above in `render.py`; in the mate-to loop replace the `at=` computation with `seat_at(seat_point(host["at"], hc["size"], host.get("rotate"), hm_at), host.get("rotate"), oc["size"], om["at"])` and carry `rotate=host.get("rotate")` onto `seated` (omit the key when the host has none, so unrotated output does not change). Raise the D3 errors. A chained seat (boot on a plug on a rotated cage) inherits through `hosts`, which already holds the seated dict with its new `rotate`.
- [ ] **Step 4: Publish.** In `cage_entries`, use the `_mate_at` / `_lift` already returned by `presented_interface` (`render.py:~2580`): `"mate": seat_point(p["at"], contract["size"], p.get("rotate"), mate_at)`, `"lift": float(lift or 0.0)`, and `"occupant-attrs"` computed by the SAME code the build uses to put host-side attributes on a seated occupant — find where `draw_placement` hands a placement's group attrs to `instance_group` and factor it so both call one function. Document the three keys where `main()` documents `cages`. In `components_index.py` add `mate` per the interface above.
- [ ] **Step 5: Extend the existing tests.** `test_occupants.py`: the rotated-cage case (the optic lands where the mate points meet on `port-2` too). `test_cage_accepts.py`: every published entry carries `mate` (2 numbers), `lift` (a number) and `occupant-attrs` (a dict); for the fitted `s9510-28dc`, the published `mate` of `port-0` and `port-2` equals the device-frame mate point measured in Step 1; and a census assertion that RECORDS the lift distribution across all published cages — assert the exact count of non-zero lifts you measure, and state it in your report. Do not assume it is zero.
- [ ] **Step 6: Commit, then gates.** Commit the source + tests. Then `lock` (no device changes, expect 0), `build`, `./publish.sh --no-images`, `lint --new-only` (expect no change), full suite. Commit any regenerated tracked files (exports should not move; if they do, find out why before committing). Report: the non-zero-lift census, and the numbers from the two integration ports.

### Task 2: `seatOccupant` in `swap.js`, held to the build

**Files:**
- Modify: `kit/swap.js`
- Create: `spec/tests/js/cage-seat.mjs`, `spec/tests/test_cage_seat_js.py`

**Interfaces:**
- Consumes: `cages[]` `mate`, `lift`, `occupant-attrs`, `rotate`; `components.json` `mate`, `size`, `version` (Task 1).
- Produces (JS, exported from `kit/swap.js`):
  - `occupantAt(cage, comp) -> [x, y]` — `seat_at` in JS: `cage.mate`, `cage.rotate`, `comp.size`, `comp.mate`.
  - `occupantTransform(cage, comp) -> string` — `translate(x,y)` plus ` rotate(deg w/2 h/2)` when `cage.rotate` is truthy — the same shape as `render.py`'s placement transform.
  - `rename(wrap, name, idBase, pathBase = idBase, segment = 'module')` — `segment` is the inserted namespace word; `''` means none, so an occupant's children become `port-4-occupant--tx` / `port-4-occupant/tx` exactly as the build names them. Default keeps every existing caller byte-identical.
  - `seatOccupant(ownerDoc, cage, ref, comp, skinText, occId = cage.id + '-occupant') -> Element` — builds the occupant `<g>`: `id` = `data-path` = `occId`; `data-ref` = `${ref}:${comp.version}`; `data-for` = `cage.id`; the skin root's `data-*` copied as `seatModule` does; `cage['occupant-attrs']` overlaid; `data-z-lift` set only when `cage.lift` is non-zero; `transform` = `occupantTransform`. Children imported and renamed with `segment = ''`.
  - `applyOccupantOverrides(rootEl, cages, overrides, loadSkin) -> number` — for each cage whose id is an OWN key of `overrides` (an emptied cage, `null`, is a real override — the `applyOverrides` rule): remove any existing `[data-for="<id>"]` occupant group (the build's or a previous swap's — match on `data-for` AND `data-behaviour="occupies"` so an LED `for` the port is never removed), then, if a ref is given and `loadSkin` returns one, insert the new occupant as the host element's NEXT SIBLING. Returns how many cages it touched.

`occupantAt` is the one formula repeated from the build; its parity with `seat_at` is proved against a real build, not against itself:

```js
function turn([x, y], rotate) {
  const deg = (((+rotate || 0) % 360) + 360) % 360;
  const exact = {0: [1, 0], 90: [0, 1], 180: [-1, 0], 270: [0, -1]};
  const [c, s] = exact[deg] || [Math.cos(deg * Math.PI / 180), Math.sin(deg * Math.PI / 180)];
  return [x * c - y * s, x * s + y * c];
}
export function occupantAt(cage, comp) {
  const cx = comp.size.w / 2, cy = comp.size.h / 2;
  const [dx, dy] = turn([comp.mate[0] - cx, comp.mate[1] - cy], cage.rotate);
  const r4 = v => Math.round(v * 1e4) / 1e4;
  return [r4(cage.mate[0] - cx - dx), r4(cage.mate[1] - cy - dy)];
}
```

- [ ] **Step 1: Write the failing test.** `test_cage_seat_js.py` builds a fitted copy of `s9510-28dc` (occupants `generic/qsfp-lc@1` in `port-0` and `port-2`, `generic/sfp-lc@1` in one upright and one rotated SFP cage — pick them from the built `cages[]`, do not hard-code), renders it AND the bare device to `tmp_path`, and extracts from the fitted face every built occupant's open-tag attributes (`transform` parsed to numbers, every `data-*`), plus the bare build's `cages[]` entries and the `components.json` entries for the refs. It passes that JSON to `node cage-seat.mjs` on stdin. The node script imports `kit/swap.js` and, per port, computes `occupantTransform(cage, comp)` and the attribute set `seatOccupant` would write (factor the attribute assembly into an exported pure helper, `occupantAttrs(cage, ref, comp, skinRootAttrs)`, so it is testable without a DOM; `seatOccupant` calls it). The test asserts: transform numbers equal the build's to 1e-6; the `data-*` set is EQUAL to the build's (same keys, same values), except `data-z-*` values if the build writes any from the seated context — if it does, stop and report rather than exempting them. A second node case uses the fake-DOM idiom of `spec/tests/js/nested-bays.mjs` to check `applyOccupantOverrides`: an override replaces a build-seated occupant (one `data-for` occupant before, one after, new ref), `null` empties it, an unknown ref leaves the cage empty, an LED carrying `data-for` on the same port survives, and a key absent from the map touches nothing. A third case checks `rename(..., segment='')` names `port-4-occupant--tx` / `port-4-occupant/tx` and that a default-`segment` call is unchanged (run the existing `spec/tests/js/swap-url-refs.mjs` assertions unmodified). The spec asks `swap-url-refs` for a cage case of its own: add one to `spec/tests/js/swap-url-refs.mjs` (and its pytest driver) - a skin carrying a `url(#...)` reference renamed with `segment = ''` still names a definition that exists.
- [ ] **Step 2: Run to see it fail** — `PYTHONPATH=spec/tools python3 -m pytest spec/tests/test_cage_seat_js.py -q`.
- [ ] **Step 3: Implement** the interfaces above in `kit/swap.js`, with a header paragraph beside `seatModule`'s explaining why an occupant is placed by mate points and not by a bay box (the spec: "the bay transform is the wrong tool for a part that is larger than its opening on purpose") and why it is a SIBLING and not a child (the build's shape; `cablePoints` walks `data-for`).
- [ ] **Step 4: Run** the new test, `spec/tests/test_swap_url_refs*.py`, `spec/tests/test_nested_bay*.py`, `spec/tests/test_cable_points*.py`, and `cd kit && npm test` (syntax checks). All pass.
- [ ] **Step 5: Commit**, then the full suite.

### Task 3: A cage swap reaches the 3D scene

**Files:**
- Modify: `kit/viewer3d.js` (`applyBayOverrides`, ~`:406-460`)
- Modify: `spec/tests/js/relief-scope.mjs` or create `spec/tests/js/cage-overrides-3d.mjs` + a pytest driver

**Interfaces:**
- Consumes: `applyOccupantOverrides` (Task 2); `devIndex.cages` (the loaded `configs.json`); `COMP_INDEX` entries' `mate`/`size`/`version`.
- Produces: the override map `OVERRIDES` (already `{path: ref|null}`) is honoured for cage ids as well as bay ids — nothing new in `load()`'s signature.

- [ ] **Step 1: Write the failing test.** The cheap guard in `applyBayOverrides` skips a view unless one of ITS BAYS is named in the map (and returns early when `devIndex.bays` is empty) — so a cage-only override never reaches the scene. Extract the per-view decision into an exported pure function in `viewer3d.js`, `viewsToRewrite(devIndex, overrides) -> [view]`, and test it in node: a cage-only override names that cage's view; a bay-only override behaves exactly as before; a device with no bays but with cages is not skipped; a nested (`/module/`) override still rewrites every view with bays. The spec asks `relief-scope` for a cage case: add one to `spec/tests/js/relief-scope.mjs` - two viewers, a cage override set in one, and the other's face text for that view is unaffected (the per-scope override map, #302's lesson). (`viewer3d.js` imports three — follow `spec/tests/js/relief-scope.mjs` for how an existing test imports a kit module that needs shims.)
- [ ] **Step 2: Run to see it fail.**
- [ ] **Step 3: Implement.** Use `viewsToRewrite`; for each rewritten view run `applyAllOverrides` for bays (unchanged) and then `applyOccupantOverrides(doc.documentElement, devIndex.cages?.[view] || [], OVERRIDES, loadSkin)`; count both into `applied`. `loadSkin` is shared.
- [ ] **Step 4: Run** the new test plus every `spec/tests/test_*js*.py` and `test_relief_scope*.py`; `cd kit && npm test`.
- [ ] **Step 5: Commit.**

### Task 4: The inspector offers the optic, and the choice survives a reload

**Files:**
- Modify: `kit/shell.js`, `kit/index.html`, `kit/marks.js`
- Create: `spec/tests/js/swap-state.mjs`, `spec/tests/test_swap_state_js.py`

**Interfaces:**
- Consumes: `seatOccupant`, `applyOccupantOverrides` (Task 2); `cages[]`, `configs[].occupants` (C1 + Task 1).
- Produces:
  - `shell.js`: `state.meta.cages` (from `configs.json`), `state.cfgOccupants` (reset from `configs[].occupants` wherever `state.cfgBays` is reset from `configs[].bays`, `shell.js:~1027`), `cageFor(path)` (a cage of the face on screen via `bayView()`; an OCCUPANT's path resolves to its host through the element's `data-for`, so clicking the optic offers the same select as clicking the port), and `swapCage(cageId, ref)` exported beside `swapBay` in the shell's returned API (`shell.js:~1094`).
  - `kit/index.html`: `swapOverrides()` returns bay AND cage changes against what the build put there (`builtOccupant` learns cages: a cage's built occupant is `configs[].occupants[id]`, else none).
  - Explorer URL: `?device=<d>&config=<c>&view=<v>&swap=<k>~<ref>,<k>~` — `~` separates key from ref, `,` separates entries, an empty ref is an emptied bay/cage; each key and ref is `encodeURIComponent`-ed. Pure helpers exported from `kit/swap.js` so they are testable: `encodeSwaps(map) -> string` (keys sorted, the `swapKey` rule), `decodeSwaps(string) -> map` (unknown shapes ignored, never thrown). Read on load (after the device loads: apply `config`, then `view`, then the swaps through `swapBay`/`swapCage`, ignoring keys that name nothing on this device); written with `history.replaceState` on every swap, config change and view change.
  - `marks.js`: the document gains `swaps` (a `{path: ref|null}` map, default `{}`); `normalise` keeps it; `encode` appends it as array slot 7 only when non-empty (`trimTail` convention — an older link and an un-swapped document encode byte-identically to today); `decode` reads slot 7 when present.

- [ ] **Step 1: Write the failing tests** — `swap-state.mjs` (node, no DOM): `encodeSwaps`/`decodeSwaps` round-trip a map with a bay path containing `/module/`, a cage id, a ref with `@` and `/`, and an emptied entry; `decodeSwaps` of garbage returns `{}`; `marks.encode` of a document without swaps equals the value today's code produces for the same document (hard-code one known-good `m1.` string produced from the CURRENT `marks.js` before you edit it); a document with swaps round-trips through `encode`/`decode`; and a pre-existing `m1.` link decodes with `swaps` equal to `{}`.
- [ ] **Step 2: Run to see them fail.**
- [ ] **Step 3: Implement** in `swap.js` (helpers) and `marks.js`, then wire `shell.js` and `index.html`. In `inspect()`, the cage select is built exactly like the bay select (`shell.js:~840`): `— empty —` first, then `cage.accepts`, current value `state.cfgOccupants[id] ?? cage.occupant ?? ''` — except that `cage.occupant` is the DEFAULT configuration's answer (C1 F2), so read `configs[].occupants` for the current configuration, never `cage.occupant`. An empty accept list says why: "no generic modelled for this cage's family yet" (osfp, xfp today). `swapCage` removes the current occupant and seats the new one through `applyOccupantOverrides` on `state.svg` with a single-entry map — ONE code path, not a second copy of the surgery — then `refreshTree(); select(cageId, true); emit('change')`, which already drives `sync3d` for bays; confirm it does for cages.
- [ ] **Step 4: Run** the new test, the full `spec/tests/test_*js*.py` set, `cd kit && npm test`.
- [ ] **Step 5: Commit**, then the full suite.

### Task 5: Gates, and Gate 5 for a UI

- [ ] **Step 1:** `lock`, `build`, `./publish.sh --no-images`, `lint --new-only` (no change against the baseline), full suite `-n auto`. Tree clean.
- [ ] **Step 2 (controller, in the browser pane):** serve the repo root (`python3 -m http.server` from the worktree) and open `kit/index.html?device=ufispace/s9510-28dc` — or whatever `?device=` form `shell.js:~1040` expects. On one UPRIGHT SFP28 cage and one ROTATED one, choose `generic/sfp-lc@1`. Verify in the live DOM with `javascript_tool` that the seated group's transform and `data-*` equal a build-seated occupant's (render the same fitted copy used in Task 2 and compare). Screenshot, per the spec's Gate 5: each port bare and populated, in 2D and 3D. Reload and confirm the swaps come back from the URL.
- [ ] **Step 3:** Put the screenshots on one HTML compare page (bare vs populated, 2D vs 3D, upright vs rotated) for Jason's sign-off — the human-review-page-before-gates practice. Record the verdict in the ledger.
