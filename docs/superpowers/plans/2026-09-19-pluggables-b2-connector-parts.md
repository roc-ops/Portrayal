# Pluggables B2: the connector parts, and the seat that can hold one — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An LC plug and an RJ45 plug that seat in the bores and jacks the library already draws, a boot for each that seats on its plug, and the one renderer change that makes seating a boot on a seated plug possible at all.

**Architecture:** Two mechanism changes first, because the parts cannot be used without them: `mate-to` resolution becomes order-independent so a seated placement can itself host, and `cablePoints` regroups on `data-for` instead of `data-path` ancestry, because a chained boot is a top-level sibling of its plug. Then four parts — two `generic/` plugs whose envelopes enter `standards.yaml`, and two `common/` boots.

**Tech Stack:** Python 3.12 (`spec/tools/portrayal/*`), YAML contracts, SVG skins, JSON Schema, ES modules (`kit/*.js`), pytest (`spec/tests`, `-n auto`), node for the `.mjs` fixtures.

**Spec:** `docs/pluggables-connectors-design.md` (B), with the shared decisions in `docs/pluggables-design.md`. Both on `main`. B1 (the marker/lift/cablePoints mechanism) landed as `4aec0a3d`.

---

## What the intake established, and why the spec needs amending

Three findings from the source pass changed this plan's shape. All are recorded in
`working/intake/fiber-connectors/lc/COVERAGE.md` (third pass) and
`working/intake/standards/rj45/README.md`.

**1. An LC plug has no class-wide length, and never will.** Three SENKO drawings give
body height 5.65 and latch length 8.6 with tolerances, repeating across products — and
give overall length only in parentheses, a REFERENCE dimension, differing every time:
`(42)` on the 2PC, `(38.6)` on the XP Fit Plus, `(43)` on the LC-HD. The class fixes the
front profile and the latch; the back end is the vendor's. So `generic/lc-plug` ships as
a front face with **no `d`**. That is correct, not a shortfall: 394 of 622 shipped
components already carry no `d`.

**2. Boots are not `generic/`.** Both are now fully dimensioned — the EASE RJ45 boot at
26.4 +/-0.5 x 14.5 +/-0.5 x 10 +/-0.4 (drawing J0072 rev A) and the SENKO 951 LC boot at
15.1 +/-0.1 (DS-LC-000023). Sourcing is not the problem. **No standard governs a boot.**
Its size follows the cable OD and the vendor's tooling: Platinum Tools lists RJ45 boots
for 5.5-8.5 mm cable, the LC 2PC datasheet lists six boot options and the LC-HD four. A
`generic/` part's envelope must be a published standard (`spec/schemas/vendors.yaml`), so
a generic boot would present one vendor's accessory as a class shape — the error L99
refuses for transceivers, one level down. They go in `common/`, which is defined as
"shapes that stand for a class of part rather than one product" and carries no standards
claim. `common/qsfp-pull-tab@1` is the precedent: a class shape, `size: {w, h}` with no
`d`, provenance citing one vendor drawing per quantity.

**3. The renderer cannot seat a boot on a seated plug.** Verified:

    boot: mate-to 'port-4-occupant' is not a placement with an explicit position in this view

`render.py:1705` builds `hosts` from placements that declare an explicit `at`, so a
`mate-to` occupant can never host. Composition is not a way round it: `parts:` entries
have no `optional` and are compile-time flattened, so a composed boot could not be chosen
per connector. Spec B's two-part fit — "a downstream tool chooses boot or no boot per
connector" — therefore requires Task 1.

Task 8 amends the spec to match findings 1 and 2.

## Global Constraints

- **Gates run with this worktree's code:** every command prefixed `PYTHONPATH=spec/tools`.
  A bare `python -m portrayal` runs whichever checkout the package was installed from.
  This bit twice in B1, including on `./publish.sh`. FOREGROUND, `timeout` 600000; never
  `run_in_background`.
- **Never launder an estimate into a measurement.** Every number entering a contract or
  the registry is read off a named figure, and `confidence:` says which. A REFERENCE
  dimension in parentheses is not a measurement and must not be subtracted into one.
- **A generic carries no per-SKU fact** (umbrella decision 5, enforced by L99). This is
  why the boots are `common/`.
- **`working/` is never committed.** The drawings stay staged; facts are transcribed.
- **Markers are emitted LAST in `instance_group`**, after every `behind_at` insertion.
  `behind_at` at `render.py:789` is an index into the group's children assuming only the
  `<title>` is present. B1 broke draw order by adding children earlier and it cost a fix
  round. If a task adds children to `g`, check that counter first.
- **Stage explicit paths; never `git add -A`.** Commit messages are written to a file and
  applied with `git commit -F`; every message ends with
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- **Version bumps go in BEFORE `lock --update`.**
- **Tests run rules through `lint.collecting()`**, never by clearing the lint globals.

---

## File map

| file | responsibility |
|---|---|
| `spec/tools/portrayal/render.py:1705` | `hosts` grows as placements resolve (Task 1) |
| `spec/tests/test_chained_seats.py` | a boot seats on a seated plug; cycles are refused (Task 1) |
| `kit/relief.js` | `cablePoints` groups on `data-for` (Task 2) |
| `spec/tests/js/cable-points.mjs`, `spec/tests/test_cable_points_js.py` | the regrouped cases (Task 2) |
| `spec/schemas/standards.yaml` | `lc-plug`, `rj45-plug` envelopes (Task 3) |
| `spec/tests/test_plug_envelopes.py` | registry entries complete, and L9 accepts the plugs (Task 3) |
| `library/components/generic/lc-plug/v1/{contract.yaml,skins/default.svg}` | Task 4 |
| `library/components/common/lc-boot/v1/{contract.yaml,skins/default.svg}` | Task 5 |
| `library/components/generic/rj45-plug/v1/{contract.yaml,skins/default.svg}` | Task 6 |
| `library/components/common/rj45-boot/v1/{contract.yaml,skins/default.svg}` | Task 7 |
| `docs/pluggables-connectors-design.md` | amended for findings 1 and 2 (Task 8) |
| `library/exports/**`, `library/components/CATALOGUE.md`, `docs/lint-rules.md` | regenerated (Task 9) |

**`library/dist/` is gitignored** (`library/.gitignore:1`, 0 tracked files). Do not stage it;
B1's plan wrongly listed it and the gates task correctly refused.

---

## Interfaces at a glance

- `hosts` after Task 1: every placement that has an `at`, **or has acquired one** by
  `mate-to` resolution. Resolution is iterative to a fixed point; a cycle is an error.
- `cablePoints(svg)` after Task 2: groups markers by walking `data-for` to a root, not by
  `data-path` prefix. A seated occupant publishes `data-for` naming its host (verified:
  `data-for="port-4"`).
- `generic/lc-plug@1`: `mates: lc`, `interface: lc-plug`, points `mate` (front), `boot`
  (rear), `cable` (rear). No `d`.
- `common/lc-boot@1`: `mates: lc-plug`, `attrs: {boot-length: 15.1}`, points `mate`
  (front), `cable` (rear).
- `generic/rj45-plug@1`: `mates: rj45`, `interface: rj45-plug`, same three points, full `d`.
- `common/rj45-boot@1`: `mates: rj45-plug`, `attrs: {boot-length: 26.4}`, two points.

---

### Task 1: A seated placement can itself host

**Files:**
- Modify: `spec/tools/portrayal/render.py` around `:1705`
- Test: `spec/tests/test_chained_seats.py` (new)

- [ ] **Step 1: Write the failing test**

```python
"""A boot seats on a plug that is itself seated. Spec B's two-part fit needs this.

`hosts` was built once, from placements carrying an explicit `at`, so a `mate-to`
occupant could never host another. The renderer said so outright:

    boot: mate-to 'port-4-occupant' is not a placement with an explicit position

Composition is not a way round it - `parts:` entries have no `optional` and are
compile-time flattened, so a composed boot could not be chosen per connector, which
is what the spec asks for.

Resolution is now iterative: each pass resolves the placements whose hosts are known
and adds them to `hosts`, until a pass resolves nothing. A pass that resolves nothing
while placements remain unresolved is either a dangling `mate-to` (already an error)
or a cycle (a new one).
"""
import pathlib
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC, LIB = ROOT / "spec", ROOT / "library"
SRC = LIB / "devices/ufispace/s9510-28dc"


def _render(tmp_path, extra_placements, occupants):
    d = yaml.safe_load((SRC / "device.yaml").read_text())
    d["configurations"]["dc"]["occupants"] = occupants
    d["views"]["front"]["components"]["placements"].extend(extra_placements)
    dev = tmp_path / "device.yaml"
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp_path / "o"
    out.mkdir()
    return subprocess.run(
        [sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
         "--library", str(LIB), "--out", str(out)],
        capture_output=True, text=True), out


def test_a_boot_seats_on_a_seated_plug(tmp_path):
    r, out = _render(
        tmp_path,
        [{"ref": "std/lc-bore@3", "id": "boot", "mate-to": "port-4-occupant"}],
        {"port-4": "generic/sfp-lc@1"})
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / "s9510-28dc.dc.front.svg").getroot()
    ids = {el.get("id") for el in root.iter() if el.get("id")}
    assert "boot" in ids, (
        "the second seat did not render. A boot seated on a seated plug is the whole "
        "of spec B's two-part fit.")


def test_the_second_seat_lands_on_the_first(tmp_path):
    """Not merely present - positioned by the mate points, like any other seat."""
    r, out = _render(
        tmp_path,
        [{"ref": "std/lc-bore@3", "id": "boot", "mate-to": "port-4-occupant"}],
        {"port-4": "generic/sfp-lc@1"})
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / "s9510-28dc.dc.front.svg").getroot()
    by_id = {el.get("id"): el for el in root.iter() if el.get("id")}
    boot, host = by_id["boot"], by_id["port-4-occupant"]
    assert boot.get("transform") and host.get("transform"), (
        "one of the two carries no transform, so nothing can be compared")
    assert boot.get("transform") != host.get("transform"), (
        "the boot landed exactly on its host's origin, which means it was placed "
        "rather than mated")


def test_a_cycle_is_refused(tmp_path):
    """Two placements mated to each other resolve nothing, forever."""
    r, _ = _render(
        tmp_path,
        [{"ref": "std/lc-bore@3", "id": "a", "mate-to": "b"},
         {"ref": "std/lc-bore@3", "id": "b", "mate-to": "a"}],
        {})
    assert r.returncode != 0, "a mate-to cycle rendered instead of erroring"
    assert "cycle" in r.stderr.lower(), (
        f"the error should name the cycle; got: {r.stderr[-300:]}")


def test_a_dangling_mate_to_still_errors(tmp_path):
    """The existing error must survive the rewrite."""
    r, _ = _render(
        tmp_path,
        [{"ref": "std/lc-bore@3", "id": "x", "mate-to": "nope"}],
        {})
    assert r.returncode != 0
    assert "nope" in r.stderr
```

- [ ] **Step 2: Run it to watch it fail**

```bash
PYTHONPATH=spec/tools python -m pytest spec/tests/test_chained_seats.py -q
```

Expected: the first two FAIL with the "not a placement with an explicit position" error;
`test_a_dangling_mate_to_still_errors` passes already; the cycle test fails on the
message assertion.

- [ ] **Step 3: Make resolution iterative**

In `spec/tools/portrayal/render.py`, replace the single-pass `hosts` construction at
`:1705` and the `mate-to` branch's lookup so that resolution runs to a fixed point
BEFORE drawing. Keep the existing error text for a dangling `mate-to` — a test asserts it.

```python
    # A SEATED PLACEMENT CAN ITSELF HOST. `hosts` was built once, from placements
    # carrying an explicit `at`, so an occupant could never host another and a boot
    # could not sit on a seated plug - which is the whole of spec B's two-part fit.
    # Composition is not an alternative: `parts:` entries have no `optional` and are
    # compile-time flattened, so a composed boot could not be chosen per connector.
    #
    # Resolution runs to a FIXED POINT: each pass places the occupants whose hosts are
    # known and adds them to `hosts`, until a pass places nothing. A pass that places
    # nothing while occupants remain is a dangling `mate-to` (the existing error) or a
    # cycle (a new one) - and without the cycle check the loop would not terminate.
    hosts = {q["id"]: q for q in parts["placements"] if q.get("at")}
    pending = [q for q in parts["placements"] if q.get("mate-to") and not q.get("at")]
    resolved = {}
    while pending:
        progressed = []
        for p in pending:
            host = hosts.get(p["mate-to"])
            if host is None:
                progressed.append(p)
                continue
            hc, _ = lib.resolve(host["ref"])
            oc, _ = lib.resolve(p["ref"])
            def _res(ref):
                try:
                    return lib.resolve(ref)[0]
                except Exception:
                    return None
            _, hm_at, hm_lift = presented_interface(hc, _res)
            om = (oc.get("connection-points") or {}).get("mate")
            if hm_at is None or om is None:
                raise ValueError(
                    f"{p['id']}: mate-to needs a 'mate' connection-point on both "
                    f"{p['ref']} and {host['ref']} - the host may also present one "
                    "through a composed aperture")
            seated = dict(p, at=[round(host["at"][0] + hm_at[0] - om["at"][0], 4),
                                 round(host["at"][1] + hm_at[1] - om["at"][1], 4)])
            if hm_lift:
                seated["seat-lift"] = (seated.get("seat-lift") or 0) + hm_lift
            resolved[p["id"]] = seated
            hosts[p["id"]] = seated
        if len(progressed) == len(pending):
            unresolved = [p["id"] for p in progressed]
            missing = [p["id"] for p in progressed
                       if p["mate-to"] not in {q["id"] for q in parts["placements"]}]
            if missing:
                bad = next(p for p in progressed if p["id"] == missing[0])
                raise ValueError(
                    f"{bad['id']}: mate-to {bad['mate-to']!r} is not a placement with "
                    "an explicit position in this view")
            raise ValueError(
                "mate-to cycle among placements: " + ", ".join(sorted(unresolved)))
        pending = progressed
```

Then in `draw_placement`, replace the inline `mate-to` resolution with a lookup of the
already-resolved placement:

```python
    def draw_placement(p):
        if p.get("mate-to") and not p.get("at"):
            p = resolved[p["id"]]
        seat_lift = p.get("seat-lift") or 0.0
```

and use `seat_lift` where the old code used the locally computed `hm_lift`, leaving B1's
trio (`z_inset -= seat_lift`, `z_group_lift=seat_lift`, and the `data-z-lift` block after
the `in:`/`sink()` block) exactly as it is.

- [ ] **Step 4: Run the new test, then the whole suite**

```bash
PYTHONPATH=spec/tools python -m pytest spec/tests/test_chained_seats.py -q
PYTHONPATH=spec/tools python -m portrayal build
PYTHONPATH=spec/tools python -m pytest spec/tests -q -n auto
```

Watch `spec/tests/test_occupant_carries_depth.py` and
`spec/tests/test_composed_lift_not_doubled.py` — they hold B1's lift trio, which this
task moves the input of. If either fails, the lift is being applied twice or lost.

- [ ] **Step 5: Commit**

Subject: `feat: a seated placement can itself host, so a boot sits on a plug`

---

### Task 2: cablePoints groups on data-for

**Files:**
- Modify: `kit/relief.js`
- Modify: `spec/tests/js/cable-points.mjs`, `spec/tests/test_cable_points_js.py`

B1's shadow rule groups by `data-path` ancestry, and recorded that it cannot relate a
`mate-to` occupant to its host because such an occupant is a top-level sibling with its
own top-level path. Task 1 makes chained seats real, so that limit now bites: a plug and
the boot seated on it would return TWO cable points for one connector.

A seated occupant publishes `data-for` naming its host — verified on a rendered drawing:
`data-for="port-4"`. Walking `data-for` to a root groups a chain of seats correctly, and
still groups composed parts, because a composed part's owner is found the same way.

- [ ] **Step 1: Add the failing fixture cases**

In `spec/tests/js/cable-points.mjs`, add a connector modelled as a CHAIN OF SEATS rather
than nested paths: three elements with distinct top-level `data-path` values (`cage`,
`cage-plug`, `cage-plug-boot`) where the second carries `data-for="cage"` and the third
`data-for="cage-plug"`. Assert ONE point comes back, the outermost. Under the shadow rule
this returns three, because no path is a prefix of another.

Keep every existing case. The composed cases (`sfp-lc/tx`, `sfp-lc/rx`, `port/plug/boot`)
must still behave identically — that is the regression risk of this task.

- [ ] **Step 2: Run to watch it fail**

```bash
node spec/tests/js/cable-points.mjs
PYTHONPATH=spec/tools python -m pytest spec/tests/test_cable_points_js.py -q
```

Expected: the new chain case returns 3 points, not 1.

- [ ] **Step 3: Group on data-for**

Replace the `shadowed` helper's path-prefix test with a walk: a marker's connector is the
root reached by following its owner's `data-for` until an element has none. A marker is
shadowed when another marker's chain passes THROUGH its owner — i.e. the other marker is
further from the root. Keep the trailing-`/` path test as a fallback for composed parts,
which have no `data-for`.

State in the comment that this replaced the path-prefix rule, and why: a chained seat is a
top-level sibling, so path ancestry cannot see the relationship that `data-for` records.

- [ ] **Step 4: Verify, including that composed grouping is unchanged**

```bash
node spec/tests/js/cable-points.mjs
node --check kit/relief.js
PYTHONPATH=spec/tools python -m pytest spec/tests -q -n auto
```

- [ ] **Step 5: Commit**

Subject: `feat: a cable point belongs to the connector its seat chain names`

---

### Task 3: The plug envelopes enter the registry

**Files:**
- Modify: `spec/schemas/standards.yaml`
- Test: `spec/tests/test_plug_envelopes.py` (new)

Add two entries. Every number below is read off a named figure; do not round, do not
average, and do not derive a depth for the LC plug — it has none (see the findings above).

```yaml
lc-plug:
  w: 5.58
  h: 10.43
  confidence: drawing
  source: >-
    SENKO DS-LC-000004 Rev A p.3, Connector Drawing, Front View. 5.58 is the
    body width; 10.43 is the overall silhouette height including the latch.
    The latch stack widths are 4.3 +/-0.1 (shoulder), 3.3 +0.05 -0.10 (neck)
    and 2.3 +/-0.1 (tip); the side view gives body height 5.65 and latch
    length 8.6 +/-0.1.
  notes: >-
    NO DEPTH, DELIBERATELY. An LC plug has no class-wide overall length. Three
    SENKO drawings give it only as a REFERENCE dimension in parentheses and
    differ every time - (42) on the 2PC 911/912, (38.6) on the XP Fit Plus 951,
    (43) on the LC-HD 913/914 - while body height 5.65 and latch length 8.6
    repeat across all three WITH tolerances. The class fixes the front profile
    and the latch; the back end is the vendor's. See
    working/intake/fiber-connectors/lc/COVERAGE.md, third pass.
rj45-plug:
  w: 11.68
  h: 7.93
  d: 22.48
  confidence: drawing
  source: >-
    CommScope customer drawing 2843005 rev K, sheet 1, UNSHIELDED MOD PLUG 8
    POSITION. .460 [11.68] front view width, .312 [7.93] side view body height,
    .885 [22.48] overall length. The latch stands .109 [2.77] below the body
    datum at 88 degrees REF with its root .232 [5.89] from the front.
  notes: >-
    THE UNSHIELDED PLUG. Sheet 2 dimensions the SHIELDED variant of the same
    family and it is a different shape - .325 [8.26] high by .895 [22.73] long.
    A generic must not average two real shapes; the shielded plug is its own
    part when someone needs it.
```

- [ ] **Steps:** write `spec/tests/test_plug_envelopes.py` asserting both entries exist,
  carry `confidence: drawing` and a `source`, that `lc-plug` has NO `d` (with the reason
  in the test's docstring so nobody helpfully adds one), and that `rj45-plug`'s three
  figures are exactly 11.68 / 7.93 / 22.48. Run it, then the suite, then commit.

Subject: `registry: the LC and RJ45 plug envelopes, read off their drawings`

---

### Tasks 4-7: the four parts

Each follows the same five steps: write the contract, write the skin, write a part test
that lints it clean and checks its points, run `build`, commit. The values are fixed
below; the skin geometry is the implementer's drawing work.

**Task 4 — `generic/lc-plug@1`.** `kind: component`, `class: port`, `behaviour: occupies`,
`mates: lc`, `interface: lc-plug`, `conforms: lc-plug`, `size: {w: 5.58, h: 10.43}` and
**no `d`**. The face is the four-tier silhouette; `working/intake/fiber-connectors/lc/SOURCES.md`
carries the tier table (body 5.58, shoulder 4.3, neck 3.3, tip 2.3) and records that the
plug's tiers and the adapter aperture's agree tier-for-tier across two independent
documents, which is what makes the profile citable. Points: `mate` front, `boot` rear,
`cable` rear. `provenance.size` must say why there is no depth.

**Task 5 — `common/lc-boot@1`.** `class: boot`, `mates: lc-plug`, `size: {w: 5.58, h: 5.65}` taken from the plug
body it wraps, `attrs: {boot-length: 15.1}`. Points: `mate` front, `cable` rear.
`provenance` cites SENKO DS-LC-000023 Rev A p.3 (XP Fit Plus 951): boot 15.1 +/-0.1 long,
I.D. 1.60 +/-0.05, O.D. 2 +/-0.1 — AND states plainly that boots are not standardised,
that this is one vendor's option, and that the part is `common/` for exactly that reason.

**Task 6 — `generic/rj45-plug@1`.** `mates: rj45`, `interface: rj45-plug`,
`conforms: rj45-plug`, `size: {w: 11.68, h: 7.93, d: 22.48}`. Relief: the latch stands
2.77 below the body datum at 88 degrees REF, root 5.89 from the front. Points as Task 4.
`provenance` names sheet 1 and records that the shielded variant is a different shape.

**Task 7 — `common/rj45-boot@1`.** `mates: rj45-plug`, `size: {w: 14.5, h: 10.0}`,
`attrs: {boot-length: 26.4}`. `provenance` cites EASE drawing J0072 rev A: 26.4 +/-0.5
overall, 14.5 +/-0.5 x 10 +/-0.4 body, inner 11.9 +/-0.5, cable exit 6.0 +/-0.4, material
PVC 80P, and notes the nine part numbers differ only in colour. Same "not standardised"
sentence as Task 5.

**All four:** check `lint --new-only` after each. An L76-style warning about which jack or
bore the part composes is a finding to understand, not to baseline.

**The `boot` class does not exist yet, and adding it is part of Task 5.** `class` is not a
schema enum — it is a closed vocabulary in `spec/schemas/power-roles.yaml`, and **L51
refuses a class that sits in no power role**. Add `boot` to the `passive` role, in
alphabetical position, in the same commit as the first boot part. The vocabulary already
carries passive classes of comparable specificity — `ear`, `tab`, `screw`, `sticker`,
`marking` — so `boot` is consistent with its grain rather than an expansion of it, and the
spec names the part a boot throughout. The schema's own warning is about admitting
SYNONYMS (`fastener` became `screw`); `boot` is not a synonym of anything in the list.
Run `lint --new-only` immediately after adding it: an L51 error means the entry did not
land where lint reads it.

---

### Task 8: The spec says what was actually built

**Files:** `docs/pluggables-connectors-design.md`

- [ ] Change the Parts table: the boots are `common/lc-boot` and `common/rj45-boot`, not
  `generic/`. Add a short paragraph giving the reason — no standard governs a boot, its
  size follows cable OD and vendor tooling, and `generic/` requires a published-standard
  envelope. Name the two drawings that DO dimension them, so nobody reads the change as a
  sourcing failure.
- [ ] Add to the Sources paragraph that the SENKO technical brochure carries no geometry
  and that TE 2271178 is an ODVA bulkhead receptacle kit — neither gives a boot length,
  and the spec named both. Point at the COVERAGE.md third pass.
- [ ] Record that an LC plug has no class-wide overall length, with the three reference
  dimensions as evidence, and that `generic/lc-plug` therefore carries no `d`.
- [ ] Note that the two-part fit required the renderer change in Task 1, and that the
  limit B1 recorded (a chained seat is a top-level sibling) is resolved by Task 2's
  `data-for` grouping rather than by nesting boots via `parts:`.

Subject: `docs: spec B says what B2 built, and why the boots are not generic`

---

### Task 9: Gates

Same sequence as B1's gates task. **Commits but does NOT push or open a PR.**

- [ ] `PYTHONPATH=spec/tools python -m portrayal lock` — four new components, so expect
  version work only if an existing contract changed. If L53 asks for a device bump, stop
  and report: no device should have changed.
- [ ] `PYTHONPATH=spec/tools python -m portrayal lint --new-only` — new parts will raise
  new warnings. Each is a finding to understand and record in the part's provenance, or a
  real defect. Do NOT `--update-baseline` without a recorded reason per warning.
- [ ] `PYTHONPATH=spec/tools python -m portrayal build`
- [ ] `PYTHONPATH=spec/tools ./publish.sh --no-images` — note the prefix; without it this
  runs a different checkout and fails on the `presented_interface` signature.
- [ ] Regenerate `library/components/CATALOGUE.md` and `docs/lint-rules.md`.
- [ ] Suite twice with `-n auto`.
- [ ] Commit the regenerated tracked artifacts. `library/dist` is gitignored — do not
  stage it, and do not create an empty commit if nothing tracked changed.

---

## Self-review

**1. Spec coverage.** Parts table: all four built (two `generic/`, two `common/`, with
Task 8 amending the naming). "The two-part fit": Task 1 delivers the seating the spec
describes; the `boot` and `cable` points are in Tasks 4 and 6. "Boot": `boot-length` is an
attr on both boots (Tasks 5, 7); `boot-bend` is explicitly reserved by the spec and is not
built. "Lint": L12 already holds `mates` against the presented `interface` and needs no
change; the `optical.gender`/`polish` comparisons are NOT in this plan — no part here
declares those keys, and a rule that checks nothing is a rule nobody tests. "Order of
work": the spec's steps 1 and 2 landed in B1; its steps 3 and 4 are Tasks 4-7; step 5's
`cablePoints` landed in B1 and is regrouped here in Task 2. Second batch (SC, MPO,
DAC/AOC) is explicitly out of scope.

**2. Placeholder scan.** Tasks 1-3 carry complete code and complete test files. Tasks 4-7
carry every value but leave skin geometry to the implementer, which is drawing work that
cannot be dictated as text; each names its source figure so nothing is invented. Task 5's one unknown — whether a `boot` class exists — was resolved while
writing this plan: it does not, `class` is a vocabulary in `power-roles.yaml` rather than
a schema enum, and L51 refuses a class with no power role. Adding it to `passive` is now
a concrete step with the reasoning, not an instruction to investigate.

**3. Type consistency.** `seat-lift` is the name in Task 1's resolution and in
`draw_placement`. The interface names `lc-plug` and `rj45-plug` are used identically in the
registry keys (Task 3), the plugs' `interface:` (Tasks 4, 6) and the boots' `mates:`
(Tasks 5, 7). The registry keys and the `conforms:` values match.

**Known risk, stated rather than hidden:** Task 1 rewrites the `mate-to` resolution that
B1's occupant-lift trio feeds. `test_occupant_carries_depth.py` and
`test_composed_lift_not_doubled.py` are the two tests that will catch a mistake, and both
are named in Task 1's Step 4.
