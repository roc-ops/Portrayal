# Pluggables B1: connection points reach the drawing, and an occupant carries depth — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every `connection-points` entry a component declares is emitted into the compiled SVG as a marker that resolves in the chassis frame by the walk `relief.js` already does, an occupant seated by `mate-to` is displaced in depth by the protrusion of the thing it seats into, and the kit exposes one accessor — `cablePoints(svg)` — that a cabling library consumes.

**Architecture:** Two render changes and one kit accessor, all on today's library and with no new parts. `instance_group` gains a loop that emits each declared connection point as an empty `<g data-cp=… data-cp-at=… data-cp-dir=…>` child in the part's own frame, under the group that already carries `data-z-lift` / `data-z-out`; `presented_interface` starts returning the composed aperture's `lift` alongside the point it already forwards, and `draw_placement`'s `mate-to` branch writes that onto the occupant as `data-z-lift`; and `kit/relief.js` gains a pure resolver plus a thin DOM accessor, split that way because the suite's JS tests run under bare `node` with hand-built fakes and no jsdom.

**Tech Stack:** Python 3.12 (`spec/tools/portrayal/*`), JSON Schema (`spec/schemas/component.schema.json`), ES modules (`kit/*.js`, `"type": "module"`), pytest (`spec/tests`, run with `-n auto`), node ≥ 18 for the `.mjs` fixtures.

**Spec:** `docs/pluggables-connectors-design.md` (B) — specifically "Render change 1", "Render change 2" and the `cablePoints()` paragraph — with the shared decisions in `docs/pluggables-design.md`. Both are on `main` as of `cde41dd8`.

## Why this is B1 and not all of B

Spec B delivers a mechanism and four parts. This plan is the **mechanism only**. The parts (`generic/lc-plug`, `generic/lc-boot`, `generic/rj45-plug`, `generic/rj45-boot`) are B2 and have their own plan. The split is the spec's own reasoning: it puts render change 2 first "because it is needed by A's transceivers too … and is testable on today's library". Nothing here depends on a drawing, a fetch or a new contract, so nothing here can be blocked by intake.

**Both B2 sources are already held** (staged 2026-09-19, never committed): SENKO DS-LC-000004 Rev A in `working/intake/fiber-connectors/lc/pdf/` for the LC plug, and CommScope customer drawing 2843005 rev K in `working/intake/standards/rj45/` for the RJ45 plug (11.68 × 7.93 × 22.48, latch 2.77 below the body datum at 88° REF). B2 is unblocked; it is simply not this plan.

## Global Constraints

- **Gates run with this worktree's code:** every command is prefixed `PYTHONPATH=spec/tools`. A bare `python -m portrayal` runs whichever checkout the package was installed from and will silently report on the wrong tree. Use the Bash tool's own `timeout` at 600000, in the FOREGROUND; never `run_in_background`, never shell-level `timeout`.
- **No new parts, no new contracts, no registry entries.** If a task finds itself editing `library/components/**`, it has left this plan.
- **Additive output only.** A marker carries no `data-z-*`, no `data-ref`, no `data-path` and no `data-class`, so it is invisible to `relief.js`'s `RAISED` selector, to `shell.js`'s `querySelector('[data-ref]')` occupancy test, and to `states.js`'s `pathIndex`. If any of those start seeing markers, the attribute set is wrong — fix the marker, not the consumer.
- **The JS tests run under bare `node` with hand-built fakes.** `jsdom` is NOT a dependency and must not become one (`spec/tests/js/character-display.mjs` says so explicitly). Anything whose arithmetic needs testing goes in a pure function, the way `localToFace`, `cavitySeatsOn` and `bodyBoxes` already are.
- **Tests run rules through `lint.collecting()`**, never by clearing `lint.WARNINGS` / `lint.ERRORS` by hand. (There is a known pre-existing offender in `spec/tests/test_faces.py`; it is being fixed separately — do not touch it here.)
- **Stage explicit paths; never `git add -A`** — other agents share this tree. Commit messages contain no backticks: write the message to a file, check with `grep -c '`' <file>`, and `git commit -F <file>`. Every commit ends with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- **Version bumps go in BEFORE `lock --update`**, never after.
- **`working/` is never committed.**

---

## File map

| file | responsibility |
|---|---|
| `spec/tools/portrayal/render.py:637-690` | `instance_group` gains the connection-point marker loop (Task 1) |
| `spec/schemas/component.schema.json:604-630` | a `cable` point must declare `direction` (Task 1) |
| `spec/tests/test_connection_point_markers.py` | markers exist, carry the right frame, and stay invisible to the other consumers (Task 1) |
| `spec/tools/portrayal/manifest.py:130-179` | `presented_interface` also returns the presenting part's `lift` (Task 2) |
| `spec/tools/portrayal/render.py:1766-1789` | `draw_placement`'s `mate-to` branch writes that lift onto the occupant (Task 2) |
| `spec/tests/test_occupant_carries_depth.py` | a seated occupant's effective lift is the host's protrusion (Task 2) |
| `kit/relief.js` | `resolveCablePoint` (pure) + `cablePoints(svg)` (DOM), both exported (Task 3) |
| `kit/package.json` | `node --check relief.js` already covered; no change expected (Task 3) |
| `spec/tests/js/cable-points.mjs` | the pure resolver's arithmetic, under bare node (Task 3) |
| `spec/tests/test_cable_points_js.py` | runs the `.mjs` and asserts its JSON (Task 3) |
| `spec/tests/test_connection_points_resolve.py` | the compiled-output check against hand arithmetic (Task 4) |
| `library/dist/**`, `library/exports/**`, `library/components/CATALOGUE.md`, `docs/lint-rules.md` | regenerated (Task 5) |

---

## Interfaces at a glance

Task 2 and Task 3 both depend on names Task 1 fixes. They are stated once, here, and every task below repeats the ones it needs.

- Marker element: `<g data-cp="NAME" data-cp-at="X Y" data-cp-dir="DIR"/>`, a direct child of the part's instance group, `X`/`Y` in the part's own frame formatted `%g`, `data-cp-dir` omitted when the contract omits `direction`.
- `presented_interface(contract, resolve) -> (interface, mate_at, lift)` — a THREE-tuple after Task 2. Every existing caller unpacks two and must be updated.
- `resolveCablePoint(marker, ancestors) -> {name, at: [x, y], dir, lift, out}` — pure, no DOM.
- `cablePoints(svg) -> [{name, path, at, dir, z}]` — DOM, outermost `cable` per connector.

---

### Task 1: Connection points reach the compiled drawing

Spec B, "Render change 2". Today `render.py` reads `mate` to position an occupant and drops every other point: 94 components declare `connection-points` — `mate` ×41, `power` ×22, `optical` ×10, `optical-tx` and `optical-rx` ×4 each — and none of them reach a consumer. This is the task the spec puts first because it pays A's transceivers back immediately.

**Files:**
- Modify: `spec/tools/portrayal/render.py` — inside `instance_group`, after the attribute block that ends at the `data-states` line (currently `:690`) and BEFORE the `parts:` loop
- Modify: `spec/schemas/component.schema.json:604-630` — the `connection-points` definition
- Test: `spec/tests/test_connection_point_markers.py` (new)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: the marker element shape above. Tasks 2, 3 and 4 all read it.

- [ ] **Step 1: Write the failing test**

Create `spec/tests/test_connection_point_markers.py`:

```python
"""Every declared connection point reaches the drawing, and none of them is a feature.

render.py read `mate` to place an occupant and dropped the rest, so a part's
optical-tx, power or cable point existed in the contract and nowhere a consumer
could see it. The cabling library in spec B needs the `cable` point; A's
transceivers get optical-tx/rx back for free.

A marker is deliberately INERT: no data-z-*, no data-ref, no data-path, no
data-class. relief.js decides what exists in 3D by querying the DOM for
attributes, and its own comment warns that every query is a chance to see data
it should not. A marker that carried data-z-out would become a raised box.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist" / "components"
SVG = "{http://www.w3.org/2000/svg}"

# generic/sfp-lc declares three points and composes two bores that declare one
# each - the richest small fixture in the library.
FIXTURE = "generic--sfp-lc--v1--default.svg"


def markers(root):
    return [el for el in root.iter(f"{SVG}g") if el.get("data-cp")]


def test_a_parts_own_points_are_emitted():
    f = DIST / FIXTURE
    if not f.exists():
        pytest.skip(f"{FIXTURE} not built")
    root = ET.parse(f).getroot()
    got = {m.get("data-cp") for m in markers(root)}
    assert {"mate", "optical-tx", "optical-rx"} <= got, (
        f"generic/sfp-lc declares mate, optical-tx and optical-rx; the drawing "
        f"carries {sorted(got)}")


def test_a_point_carries_its_position_and_direction():
    f = DIST / FIXTURE
    if not f.exists():
        pytest.skip(f"{FIXTURE} not built")
    root = ET.parse(f).getroot()
    parent = {c: p for p in root.iter() for c in p}
    # THE PART'S OWN POINTS, not a composed bore's. There are three `mate`
    # markers in this drawing - sfp-lc's own and one inside each lc-bore - so
    # selecting by name alone reads whichever came last. A point belongs to the
    # part whose instance group is its DIRECT parent.
    own = {m.get("data-cp"): m for m in markers(root)
           if (parent.get(m) is not None
               and parent[m].get("data-ref", "").startswith("generic/sfp-lc@"))}
    assert set(own) == {"mate", "optical-tx", "optical-rx"}, (
        f"sfp-lc's own points are {sorted(own)}; a composed bore's mate has "
        "leaked into the selection")
    # the contract's own numbers, in the part's own frame
    assert own["mate"].get("data-cp-at") == "6.775 4.275"
    assert own["mate"].get("data-cp-dir") == "front"
    assert own["optical-tx"].get("data-cp-at") == "3.6 5.7"


def test_a_composed_parts_points_come_too():
    """The two std/lc-bore@3 cores inside sfp-lc each declare a `mate`."""
    f = DIST / FIXTURE
    if not f.exists():
        pytest.skip(f"{FIXTURE} not built")
    root = ET.parse(f).getroot()
    mates = [m for m in markers(root) if m.get("data-cp") == "mate"]
    assert len(mates) == 3, (
        "expected the part's own mate plus one from each composed bore, got "
        f"{len(mates)}")


def test_a_marker_is_inert():
    """It must be invisible to relief.js, shell.js and states.js alike."""
    f = DIST / FIXTURE
    if not f.exists():
        pytest.skip(f"{FIXTURE} not built")
    root = ET.parse(f).getroot()
    for m in markers(root):
        for bad in ("data-ref", "data-path", "data-class", "data-depth",
                    "data-body-depth", "data-behaviour"):
            assert m.get(bad) is None, (
                f"marker {m.get('data-cp')} carries {bad}; shell.js reads "
                "[data-ref] as occupancy and states.js indexes [data-path]")
        for k in m.attrib:
            assert not k.startswith("data-z-"), (
                f"marker {m.get('data-cp')} carries {k}; relief.js would build "
                "a box out of it")
        assert len(list(m)) == 0, "a marker draws nothing"


def test_every_built_component_with_points_has_markers():
    """Not just the fixture - the whole library, so a regression is loud."""
    if not DIST.exists():
        pytest.skip("components not built")
    seen = 0
    for f in sorted(DIST.glob("*--default.svg")):
        root = ET.parse(f).getroot()
        seen += len(markers(root))
    assert seen > 100, (
        f"only {seen} connection-point markers across the whole built library; "
        "94 components declare connection-points, so the loop is not running")
```

- [ ] **Step 2: Run it to make sure it fails**

```bash
PYTHONPATH=spec/tools python -m pytest spec/tests/test_connection_point_markers.py -q
```

Expected: FAIL — every test that does not skip fails, because no `data-cp` attribute exists anywhere in `library/dist`.

- [ ] **Step 3: Emit the markers**

In `spec/tools/portrayal/render.py`, inside `instance_group`, immediately after the `data-states` block (the last of the attribute assignments, currently ending at `:690`) and BEFORE the transform/`parts:` handling, insert:

```python
    # EVERY DECLARED CONNECTION POINT REACHES THE DRAWING, not just `mate`.
    # This function read `mate` to place an occupant and dropped the rest, so a
    # part's optical-tx, power or cable point existed in the contract and in no
    # place a consumer could reach. Spec B's cabling library needs `cable`; A's
    # transceivers get their optical axes back for nothing.
    #
    # THE MARKER IS INERT ON PURPOSE. It carries no data-z-*, no data-ref, no
    # data-path and no data-class, because relief.js decides what exists in 3D
    # by querying the DOM for attributes - its own comment warns that every
    # query is a chance to see data it should not - and shell.js reads
    # `[data-ref]` as "this bay is occupied". A marker that carried either would
    # become a phantom box or a phantom module.
    #
    # The point is in THIS PART'S OWN FRAME, under the group that already
    # carries data-z-lift and data-z-out, so a consumer resolves it with the
    # same walk relief.js uses for every feature: sum the ancestors' lifts, add
    # the part's own out, apply the group transforms. Nothing new to compute.
    for cp_name in sorted(contract.get("connection-points") or {}):
        cp = (contract["connection-points"] or {})[cp_name]
        mk = ET.SubElement(g, f"{{{SVG_NS}}}g")
        mk.set("data-cp", cp_name)
        mk.set("data-cp-at", f"{cp['at'][0]:g} {cp['at'][1]:g}")
        if cp.get("direction"):
            mk.set("data-cp-dir", cp["direction"])
```

- [ ] **Step 4: Constrain a `cable` point in the schema**

Spec B: "a part declaring `cable` must declare `direction` … Small, in the connection-points schema rather than a rule." A cable point without a direction is useless to the consumer — it is the one point whose whole job is to say which way the cable leaves.

The plug/boot half of that spec bullet ("a plug must declare `boot` or be marked as one that takes no boot") is **deliberately NOT in this plan**: there are no plugs yet, and a rule that checks nothing is a rule nobody tests. It belongs in B2 with the parts it constrains.

In `spec/schemas/component.schema.json`, replace the `connection-points` definition (currently `:604-630`) with the same object plus a conditional:

```json
  "connection-points": {
   "type": "object",
   "propertyNames": {
    "$ref": "#/$defs/segment"
   },
   "additionalProperties": {
    "type": "object",
    "required": [
     "at"
    ],
    "additionalProperties": false,
    "properties": {
     "at": {
      "$ref": "#/$defs/xy"
     },
     "direction": {
      "enum": [
       "front",
       "rear",
       "up",
       "down",
       "left",
       "right"
      ]
     }
    }
   },
   "properties": {
    "cable": {
     "required": [
      "at",
      "direction"
     ],
     "description": "Where a cable lands. `direction` is REQUIRED here and optional elsewhere: a cable point whose whole job is to say which way the cable leaves says nothing without it."
    }
   }
  },
```

Note the JSON Schema subtlety this relies on: `additionalProperties` applies to members not matched by `properties`, so naming `cable` under `properties` means the generic constraint no longer applies to it — which is why `at` is repeated in its `required` list. Do not remove it.

- [ ] **Step 5: Rebuild and run the test**

```bash
PYTHONPATH=spec/tools python -m portrayal build
PYTHONPATH=spec/tools python -m pytest spec/tests/test_connection_point_markers.py -q
```

Expected: PASS, 5 passed.

- [ ] **Step 6: Run the whole suite — this changes every built drawing**

```bash
PYTHONPATH=spec/tools python -m pytest spec/tests -q -n auto
```

Expected: PASS. If something fails, the likely cause is a test that counts children of an instance group or compares a drawing byte-for-byte. Report it rather than loosening the assertion; a marker appearing where a test did not expect one is exactly the kind of thing this step is for.

- [ ] **Step 7: Commit**

```bash
git add spec/tools/portrayal/render.py spec/schemas/component.schema.json spec/tests/test_connection_point_markers.py
# write the message to a file first; no backticks
git commit -F <message-file>
```

Subject: `feat: every connection point reaches the compiled drawing`

---

### Task 2: An occupant carries depth

Spec B, "Render change 1". A `mate-to` seat has no z of its own today; only `parts:` composition carries `lift`. A plug in a transceiver's bore is displaced in depth because the bore is already lifted to the module face — and an occupant that ignores that sits at the panel plane behind unbroken metal, which is the `smartoptics/dcp-404` blank-face failure that `spec/tests/test_bay_occupant_lift.py` exists to catch for bays.

**Files:**
- Modify: `spec/tools/portrayal/manifest.py:157-179` (`presented_interface`)
- Modify: `spec/tools/portrayal/render.py:1766-1789` (`draw_placement`'s `mate-to` branch)
- Modify: every other caller of `presented_interface` (find them in Step 2)
- Test: `spec/tests/test_occupant_carries_depth.py` (new)

**Interfaces:**
- Consumes: nothing from Task 1 (independent; ordering is the spec's, not a dependency).
- Produces: `presented_interface(contract, resolve) -> (interface, mate_at, lift)`, a THREE-tuple.

- [ ] **Step 1: Find every caller before changing the signature**

```bash
grep -rn 'presented_interface' spec/ --include=*.py
```

Expected: the definition in `manifest.py`, the call in `render.py:1783`, and at least one in `lint.py` (L11/L12 use it). Every one unpacks two values today and will raise `ValueError: too many values to unpack` after Step 3. Write the list down; Step 4 updates all of them.

- [ ] **Step 2: Write the failing test**

Create `spec/tests/test_occupant_carries_depth.py`:

```python
"""What a bore is off the panel, the plug seated in it is too.

The bay case is already held by test_bay_occupant_lift.py. This is the MATE-TO
case, which had no z at all: only `parts:` composition carried `lift`, so an
occupant positioned by mate points sat at the panel plane no matter how far
forward the thing it seats into stands.

Asserted on the UNIT rather than on a shipped drawing, because no device in the
library seats an optic any more - spec A made them all bare on purpose - so
there is no compiled fixture to read. The invariant is about the function.
"""
from portrayal.manifest import presented_interface


def _res(table):
    return lambda ref: table.get(ref)


def test_a_host_that_presents_its_own_point_lifts_nothing():
    host = {"interface": "sfp", "connection-points": {"mate": {"at": [8.0, 5.0]}}}
    iface, at, lift = presented_interface(host, _res({}))
    assert (iface, at) == ("sfp", [8.0, 5.0])
    assert lift == 0.0, "a host mating on its own face displaces nothing"


def test_a_forwarded_point_carries_the_composed_parts_lift():
    """The whole point: the aperture is the thing that stands forward."""
    bore = {"interface": "lc", "connection-points": {"mate": {"at": [2.35, 2.35]}}}
    host = {"parts": [{"ref": "std/lc-bore@3", "id": "tx",
                       "at": [1.25, 1.75], "lift": 10.0}]}
    iface, at, lift = presented_interface(host, _res({"std/lc-bore@3": bore}))
    assert iface == "lc"
    assert at == [3.6, 4.1]
    assert lift == 10.0, (
        "the bore stands 10.0 off the module face; a plug seated in it that "
        "ignores that is buried in the transceiver body")


def test_a_composed_part_with_no_lift_forwards_zero():
    bore = {"interface": "lc", "connection-points": {"mate": {"at": [2.35, 2.35]}}}
    host = {"parts": [{"ref": "std/lc-bore@3", "id": "tx", "at": [1.25, 1.75]}]}
    _, _, lift = presented_interface(host, _res({"std/lc-bore@3": bore}))
    assert lift == 0.0
```

- [ ] **Step 3: Run it to verify it fails**

```bash
PYTHONPATH=spec/tools python -m pytest spec/tests/test_occupant_carries_depth.py -q
```

Expected: FAIL with `ValueError: not enough values to unpack (expected 3, got 2)`.

- [ ] **Step 4: Return the lift from `presented_interface`**

In `spec/tools/portrayal/manifest.py`, change the three `return` statements. The docstring's first line becomes `Returns (interface, mate_at, lift)`; add to the docstring:

```
    THE LIFT IS THE HOST'S PROTRUSION AT THAT POINT, and it is why this returns
    three things now. A forwarded point belongs to a composed aperture, and that
    aperture's `lift` is how far off the host's own face it stands. An occupant
    positioned by the point and not displaced by the lift is seated at the panel
    plane behind whatever the aperture is mounted on. A host that presents its
    own point forwards nothing and lifts nothing.
```

The three returns:

```python
    if contract.get("interface") and mate:
        return contract["interface"], list(mate["at"]), 0.0
```

```python
        cores.append((core["interface"],
                      [round(at[0] + cm["at"][0], 4), round(at[1] + cm["at"][1], 4)],
                      float(part.get("lift") or 0)))
```

```python
    return contract.get("interface"), (list(mate["at"]) if mate else None), 0.0
```

- [ ] **Step 5: Update every caller found in Step 1**

In `render.py:1783` the unpack becomes:

```python
            _, hm_at, hm_lift = presented_interface(hc, _res)
```

and after the `p = dict(p, at=[...])` line that follows, carry the lift onto the occupant:

```python
            # WHAT THE APERTURE IS OFF THE FACE, THE OCCUPANT IS TOO. Written as
            # data-z-lift on the occupant's own group by the instance_group call
            # below, via `lift`, exactly as a composed part writes it - so
            # relief.js's existing ancestor sum places it and there is one code
            # path, not two. A `mate-to` seat had no z at all before this.
            if hm_lift:
                p["lift"] = (p.get("lift") or 0) + hm_lift
```

In `lint.py`, each call becomes a three-way unpack with `_` for the lift — lint asks about interfaces, not depth. Do NOT change any lint behaviour in this task.

- [ ] **Step 6: Run the new test, then the suite**

```bash
PYTHONPATH=spec/tools python -m pytest spec/tests/test_occupant_carries_depth.py -q
PYTHONPATH=spec/tools python -m portrayal build
PYTHONPATH=spec/tools python -m pytest spec/tests -q -n auto
```

Expected: the new file passes; the suite passes. `test_composed_lift_not_doubled.py` is the one to watch — if it fails, the lift is being applied twice and the `p.get("lift") or 0` addition in Step 5 is the place to look.

- [ ] **Step 7: Commit**

Subject: `feat: an occupant seated by mate-to carries the aperture's depth`

Files: `spec/tools/portrayal/manifest.py spec/tools/portrayal/render.py spec/tools/portrayal/lint.py spec/tests/test_occupant_carries_depth.py`

---

### Task 3: `cablePoints()` in the kit

Spec B: "`kit/states.js`-style accessor, not page code … That function is the contract the cabling library consumes."

**Files:**
- Modify: `kit/relief.js` — add `resolveCablePoint` (pure) and `cablePoints` (DOM), both exported
- Create: `spec/tests/js/cable-points.mjs`
- Create: `spec/tests/test_cable_points_js.py`

**Interfaces:**
- Consumes: the marker shape from Task 1, and `liftOf` from `nodeTools(svg)` in `kit/relief.js:436`.
- Produces: `resolveCablePoint(marker, ancestors)` and `cablePoints(svg)`.

The split is not stylistic. `nodeTools`' `mmRect` calls `svg.getScreenCTM()`, which does not exist under bare `node`, and `jsdom` is not a dependency and must not become one. So the arithmetic goes in a pure function that takes plain objects, tested under node; the DOM query is a thin wrapper tested only by the compiled-output test in Task 4.

- [ ] **Step 1: Write the failing fixture**

Create `spec/tests/js/cable-points.mjs`:

```javascript
// The arithmetic a cabling library depends on, without a DOM.
//
// `cablePoints` itself needs getScreenCTM and so needs a browser; its SUM does
// not, and the sum is the part that can be silently wrong. Same split as
// localToFace, cavitySeatsOn and bodyBoxes, and for the same reason: jsdom is
// not a dependency of this repo.
//
// The `ancestors` array is ordered OUTERMOST-LAST, matching a parentElement
// walk from the marker up to the svg.
const m = await import('../../../kit/relief.js');

const marker = {name: 'cable', at: [6.75, 4.25], dir: 'rear'};

// a plug in a bore on a transceiver: 10.0 of bore lift, 14.3 of body out
const stack = [{lift: 0}, {lift: 10.0, out: 0}, {lift: 0, out: 14.3}];

console.log(JSON.stringify({
  // no ancestors carry anything: the point is where it was declared
  bare: m.resolveCablePoint(marker, []),
  // one lifted ancestor
  lifted: m.resolveCablePoint(marker, [{lift: 10.0}]),
  // the full stack sums every lift on the way up
  stacked: m.resolveCablePoint(marker, stack),
  // a missing direction is null, not undefined and not a throw
  noDir: m.resolveCablePoint({name: 'cable', at: [1, 2]}, []),
  // junk lifts are zero, not NaN - a NaN z silently removes a cable from 3D
  junk: m.resolveCablePoint(marker, [{lift: 'x'}, {}, {lift: null}]),
}));
```

Create `spec/tests/test_cable_points_js.py`:

```python
"""The cable point's arithmetic, checked against hand sums under bare node."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/cable-points.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_resolver_sums_the_ancestor_chain():
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])

    assert out["bare"] == {"name": "cable", "at": [6.75, 4.25],
                           "dir": "rear", "lift": 0, "out": 0, "z": 0}
    assert out["lifted"]["z"] == 10.0
    # 10.0 of lift on the way up, plus 14.3 the outermost body stands proud
    assert out["stacked"]["z"] == 24.3
    assert out["noDir"]["dir"] is None
    assert out["junk"]["z"] == 0, "a junk lift must be 0, never NaN"
```

- [ ] **Step 2: Run it to verify it fails**

```bash
PYTHONPATH=spec/tools python -m pytest spec/tests/test_cable_points_js.py -q
```

Expected: FAIL — `resolveCablePoint is not a function`.

- [ ] **Step 3: Implement both halves in `kit/relief.js`**

Add near `localToFace` and `cavitySeatsOn`, which are grouped as the pure, browser-free part of this module:

```javascript
// WHERE A CABLE LANDS, in the chassis frame. Exported as two halves on purpose:
// the SUM is pure and is tested under bare node, the QUERY needs getScreenCTM
// and is covered by the compiled-output tests. jsdom is not a dependency here.
//
// `ancestors` runs from the marker's parent OUTWARD to the svg, each entry
// contributing its own `lift`; the outermost entry's `out` is how far the body
// it belongs to stands proud. This is the same walk liftOf does, spelled out so
// it can be checked without a document.
export function resolveCablePoint(marker, ancestors = []) {
  const num = v => (Number.isFinite(+v) ? +v : 0);
  const lift = ancestors.reduce((z, a) => z + num(a && a.lift), 0);
  const outer = ancestors.length ? ancestors[ancestors.length - 1] : null;
  const out = num(outer && outer.out);
  return {
    name: marker.name,
    at: [num(marker.at[0]), num(marker.at[1])],
    dir: marker.dir ?? null,
    lift, out, z: lift + out,
  };
}

// Every `cable` marker in a drawing, resolved. Takes the OUTERMOST point per
// connector - the boot's when a boot is seated, the plug's when it is not -
// which is what a cable actually lands on. This is the function the cabling
// library consumes; page code should not walk data-cp itself.
export function cablePoints(svg) {
  const {liftOf} = nodeTools(svg);
  const out = [];
  const byOwner = new Map();
  for (const mk of svg.querySelectorAll('[data-cp="cable"]')) {
    const owner = mk.closest('[data-path]');
    const key = owner ? owner.dataset.path : '';
    const depth = liftOf(mk);
    const prev = byOwner.get(key);
    if (!prev || depth > prev.depth) byOwner.set(key, {mk, depth, owner});
  }
  for (const [path, {mk, depth, owner}] of byOwner) {
    const at = (mk.dataset.cpAt || '').split(/\s+/).map(Number);
    out.push({
      name: 'cable', path,
      at: [at[0] || 0, at[1] || 0],
      dir: mk.dataset.cpDir ?? null,
      z: depth + (+(owner && owner.dataset.zOut) || 0),
    });
  }
  return out;
}
```

- [ ] **Step 4: Run the test**

```bash
PYTHONPATH=spec/tools python -m pytest spec/tests/test_cable_points_js.py -q
node --check kit/relief.js
```

Expected: PASS, and `node --check` silent.

- [ ] **Step 5: Commit**

Subject: `feat: cablePoints, the accessor a cabling library consumes`

Files: `kit/relief.js spec/tests/js/cable-points.mjs spec/tests/test_cable_points_js.py`

---

### Task 4: The resolution is checked against hand arithmetic

Spec B step 5 wants "a JS test that resolves a boot seated on a plug seated in a bore on a transceiver in a cage, and checks the point against hand arithmetic". There are no plugs or boots in B1, so this task checks the deepest stack that EXISTS — and it turns out to be a better test than a synthetic one, because it checks two independently-authored numbers against each other.

In `library/components/generic/sfp-lc/v1/contract.yaml`, the composed `tx` bore is placed at `[1.25, 1.75]` with `lift: 10.0` and `rotate: 180`. `std/lc-bore@3` is `4.7 × 6.3` and declares `mate` at `[2.35, 2.35]`. Rotating that point 180° about the bore's own centre `[2.35, 3.15]` gives `[2.35, 3.95]`; translating by the placement gives **`[3.60, 5.70]`** — which is exactly the value the same contract independently declares for its own `optical-tx`. Nobody arranged that; the author put the optical axis where the bore's mate point actually is. If the marker resolution is right, the two must land on the same spot.

Note what this also proves: `presented_interface` computes the forwarded point as `at + cm.at` and **ignores `rotate`**, which would give `[3.60, 4.10]` — 1.6 mm out. That is a real latent gap for any wrapper composing a rotated aperture. It is OUT OF SCOPE here (no shipped wrapper rotates its aperture today); record it, do not fix it.

**Files:**
- Test: `spec/tests/test_connection_points_resolve.py` (new)

**Interfaces:**
- Consumes: the marker shape (Task 1) and the composed-part lift (Task 2).

- [ ] **Step 1: Write the test**

```python
"""The marker resolves where the geometry actually is, checked by hand.

generic/sfp-lc declares optical-tx at [3.60, 5.70] and, separately, composes
std/lc-bore@3 at [1.25, 1.75] rotated 180 with the bore declaring mate at
[2.35, 2.35] in a 4.7 x 6.3 body. Rotating about the bore's centre [2.35, 3.15]
gives [2.35, 3.95]; translating gives [3.60, 5.70]. The two numbers were written
independently and must agree, so this is a check on the RESOLUTION and not a
restatement of one contract.

It also pins the thing presented_interface gets wrong: that function forwards
`at + cm.at` and ignores `rotate`, which would put the point at [3.60, 4.10].
Nothing shipped composes a rotated aperture, so it is not a live defect - but
if a wrapper ever does, this arithmetic is the record of what correct means.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist" / "components"
SVG = "{http://www.w3.org/2000/svg}"
FIXTURE = "generic--sfp-lc--v1--default.svg"


def _markers(root):
    return [el for el in root.iter(f"{SVG}g") if el.get("data-cp")]


def test_the_bores_mate_point_lands_on_the_declared_optical_axis():
    f = DIST / FIXTURE
    if not f.exists():
        pytest.skip(f"{FIXTURE} not built")
    root = ET.parse(f).getroot()
    parent = {c: p for p in root.iter() for c in p}

    tx = [m for m in _markers(root) if m.get("data-cp") == "optical-tx"]
    assert len(tx) == 1, "sfp-lc declares exactly one optical-tx"
    declared = [float(v) for v in tx[0].get("data-cp-at").split()]
    assert declared == [3.6, 5.7]

    # the bore's own mate marker, inside the `tx` part group
    bore_mates = [m for m in _markers(root) if m.get("data-cp") == "mate"
                  and (parent.get(m) is not None
                       and (parent[m].get("id") or "").endswith("--tx"))]
    assert len(bore_mates) == 1, (
        "expected one mate marker inside the tx bore's group; got "
        f"{len(bore_mates)}")

    # resolve it: the marker is in the BORE's frame, the bore group carries the
    # rotate+translate transform, so the composed transform is what maps it.
    # The bore is 4.7 x 6.3 and the point is [2.35, 2.35]; rotate 180 about
    # [2.35, 3.15] -> [2.35, 3.95]; translate by [1.25, 1.75] -> [3.60, 5.70].
    at = [float(v) for v in bore_mates[0].get("data-cp-at").split()]
    assert at == [2.35, 2.35], "the marker must be in the bore's OWN frame"
    rotated = [2 * 2.35 - at[0], 2 * 3.15 - at[1]]
    resolved = [round(1.25 + rotated[0], 4), round(1.75 + rotated[1], 4)]
    assert resolved == declared, (
        f"the bore's mate resolves to {resolved} but the part declares its "
        f"optical axis at {declared}. Two independently written numbers for the "
        "same physical spot have stopped agreeing.")


def test_the_bore_group_carries_the_lift_that_displaces_it():
    """10.0 of lift is why a plug seated here is not buried in the body."""
    f = DIST / FIXTURE
    if not f.exists():
        pytest.skip(f"{FIXTURE} not built")
    root = ET.parse(f).getroot()
    by_id = {el.get("id"): el for el in root.iter() if el.get("id")}
    tx = next((el for k, el in by_id.items() if k.endswith("--tx")), None)
    assert tx is not None, "no tx bore group in the drawing"
    assert float(tx.get("data-z-lift") or 0) == 10.0
```

- [ ] **Step 2: Run it**

```bash
PYTHONPATH=spec/tools python -m pytest spec/tests/test_connection_points_resolve.py -q
```

Expected: PASS once Tasks 1 and 2 are in. If `test_the_bores_mate_point_lands_on_the_declared_optical_axis` fails on the FRAME assertion (`at == [2.35, 2.35]`), the marker is being emitted with the parent's offset already applied — the point must stay in the part's own frame, per Task 1.

- [ ] **Step 3: Commit**

Subject: `test: a composed bore's mate point resolves onto the axis its parent declares`

---

### Task 5: Gates

Mirrors Task 13 of the A plan. **This task commits but does NOT push and does NOT open a PR** — that is a side effect outside the worktree and goes through `superpowers:finishing-a-development-branch` after the final review, with the base decided there.

- [ ] **Step 1: Check for version bumps BEFORE updating the lock**

```bash
PYTHONPATH=spec/tools python -m portrayal lock
```

Expected: `devicelock: 0 finding(s)`. No contract changed, so nothing should want a bump. If L53 asks for one, stop and report — it means a task edited `library/` and left this plan.

- [ ] **Step 2: Lint, and look at what is new**

```bash
PYTHONPATH=spec/tools python -m portrayal lint --new-only
```

Expected: `LINT: no change against the baseline`. Markers carry no lintable surface, so a new warning here is a finding to understand, not to baseline.

- [ ] **Step 3: Build, publish, regenerate**

```bash
PYTHONPATH=spec/tools python -m portrayal build
./publish.sh --no-images
PYTHONPATH=spec/tools python3 spec/tools/portrayal/components_catalogue.py --library library > library/components/CATALOGUE.md
python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md
```

- [ ] **Step 4: Full suite, twice**

```bash
PYTHONPATH=spec/tools python -m pytest spec/tests -q -n auto
PYTHONPATH=spec/tools python -m pytest spec/tests -q -n auto
```

Expected: green both times. Note the baseline: `main` at `cde41dd8` ran **2441 passed, 1 skipped**; this plan adds roughly 12 tests and no skips.

**If a test fails on one run and passes on the other, do not shrug.** There is one known pre-existing order-dependent flake — `test_lint_collecting.py::test_it_restores_what_was_there_before`, leaked into by `test_faces.py:169`, reproducible on pristine `main` and being fixed separately. If the failure is that one, say so and move on. If it is any other, it is yours: bisect it the same way (`pytest <suspect_file> <failing_file>`).

- [ ] **Step 5: Commit the regenerated artifacts**

Subject: `chore: relock, republish and regenerate after the connection-point markers`

Files: `library/dist library/exports library/components/CATALOGUE.md docs/lint-rules.md` (plus `library/lint-baseline.json` only if Step 2 justified it)

---

## Self-review

**1. Spec coverage.** Spec B's five ordered steps: (1) render change 2 → Task 1. (2) render change 1 → Task 2. (3) `generic/lc-plug` + `lc-boot` → **B2, out of scope**, stated at the top. (4) RJ45 plug + boot → **B2**; the drawing is now held, so B2 is unblocked. (5) `cablePoints()` + a resolution test → Tasks 3 and 4. The lint section: L12's `optical.gender` / `optical.polish` comparisons are **B2** (they need parts that declare those keys); the `cable`-needs-`direction` rule is Task 1 Step 4; the plug-declares-`boot` rule is B2, with the reason given. The "Boot" section (`boot-length`) is B2. Both open questions are answered: boot is seatable but not seated by default (the mechanism supports both, `cablePoints` takes the outermost point either way); the RJ45 latch question is B2/spec-D and untouched here.

**2. Placeholder scan.** No "TBD", no "add error handling", no "similar to Task N". Every code step carries the actual code. The one deliberate omission is the exact commit message bodies, which cannot be pre-written because the no-backtick check runs against the file.

**3. Type consistency.** `presented_interface` returns a 3-tuple in Task 2's definition, its test, and both call-site edits. `resolveCablePoint(marker, ancestors)` has the same shape in the implementation, the `.mjs` fixture and the Python assertions; its return keys (`name`, `at`, `dir`, `lift`, `out`, `z`) match in all three. The marker attribute names `data-cp` / `data-cp-at` / `data-cp-dir` are identical in Task 1's emitter, Task 1's tests, Task 3's `cablePoints`, and Task 4's test.

**Known gap recorded, not fixed:** `presented_interface` ignores a composed part's `rotate` when forwarding a mate point (`manifest.py:171-176`). No shipped wrapper composes a rotated aperture, so it is latent. Task 4's docstring is the record.
