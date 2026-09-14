# Connector Components Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the eight fibre-connector components the FS FHD line needs, each
declaring the `optical.positions` capacity plan 1 introduced — and first resolve
a contradiction the library already contains about LC bore pitch.

**Architecture:** A connector is a `class: port` component whose `size` is the
panel aperture and whose `optical.positions` says how many fibres it presents.
Where a governing dimension exists it goes in `spec/schemas/standards.yaml` and
the component declares `conforms:`, which lint enforces. Three connectors are
measured from face-on FS renders; five are estimated from three-quarter renders
plus panel arithmetic, and every estimated figure says so in its own provenance.

**Tech Stack:** Python 3.12, PyYAML, Pillow, pytest. No new dependencies.

**Spec:** `docs/optical-paths-design.md` (section E item 2 — the connector table)

## Global Constraints

- **Gate chain, in this order, after every task touching `library/` or `spec/`:**
  `python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library`
  then `./publish.sh --no-images`
  then `python3 spec/tools/portrayal/devicelock.py --library library`
  then `python3 -m pytest spec/tests -q -p no:randomly`
- **Run every command in the FOREGROUND** with a 600000 ms tool timeout for the
  full suite (~4 minutes). Never background it. Four implementers on the previous
  plan stalled by backgrounding pytest and then blocking on a notification.
- **Lint baseline is `LINT: ok (654 files, 1291 warnings in 22 rules)`** at the
  start of this plan. Each task that adds components will RAISE the file count;
  the warning count must not rise.
- **pytest baseline is 1393 passed, 1 skipped.** Expected totals in tasks are a
  GUIDE, not a gate: the binding check is that nothing FAILED and the total only
  went up.
- **Version bumps happen BEFORE `devicelock.py --update`, never after.**
- **`working/` is never committed.** Reference imagery stays there.
- **Run everything from the worktree root.** Never `cd` to the main checkout.
  Never use bare `git stash`.
- **Every estimated dimension carries `confidence: estimated` and a `source:`
  saying what it was derived from and what would settle it.** This plan builds
  five connectors from imagery that cannot be measured; the honesty of the
  provenance is the deliverable, not a formality.
- Commit messages end with:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

## The evidence, stated once

Face-on FS renders under `working/intake/fs/fhd/photos/`. A face is measurable
when the faceplate — the widest full-width dark band — scales on the known
108.97 mm module width AND reproduces the 35.05 mm height within ~3%.

| connector | modules | image | status |
|---|---:|---|---|
| LC duplex | 42 | `57016.main.jpg` | face-on; 12.90 adapter pitch, scale validated 0.8% |
| MTP/MPO | 48 | `35510.G.jpg` | face-on; scale validated 1.7% |
| SC duplex | 5 | `57058.main.jpg` | face-on |
| MDC | 3 | `147015` page render | three-quarter only |
| ST simplex | 2 | `183380.st-upc-panel.jpg` | three-quarter only |
| FC simplex | 1 | `382881.fc-apc-panel.jpg` | three-quarter only |
| LSH/E2000 | 1 | `336339.lsh-apc-panel.jpg` | three-quarter only |
| keystone | 1 | `143239.keystone-panel.jpg` | three-quarter only |

**Panel arithmetic is real evidence and the five estimated connectors lean on
it.** Each FHD panel is 108.97 mm wide and its adapter count is stated in the
catalogue, so a pitch follows from arithmetic rather than from guessing. It
bounds the connector; it does not measure it, and the contracts must say so.

## File Structure

| file | responsibility |
|---|---|
| `spec/schemas/standards.yaml` | new registry entries: `mpo-adapter`, `sc-duplex-adapter`, `st-adapter`, `fc-adapter`, `lsh-adapter`, `mdc-adapter`. The estimated ones carry `confidence: estimated` |
| `spec/tools/portrayal/lint.py` | rule **L81** — a component composing several instances of a part that `conforms:` to a standard with a `pitch` is checked against it |
| `spec/tests/test_pitch_lint.py` | **new.** L81 fires on a wrong pitch, stays quiet on a right one |
| `spec/tools/intake/panel_measure.py` | **new.** Face-on panel measurement, reused by every connector task. UNDERSCORE, not a hyphen like its siblings there: this one is imported by tests, not only run as a script |
| `library/components/common/lc-duplex-adapter/v3/contract.yaml` | bore pitch reconciled with the standard |
| `library/components/std/mpo/v1/` | the MPO adapter aperture |
| `library/components/common/mpo-adapter/v1/` | the panel-mount MPO adapter that composes it |
| `library/components/common/sc-duplex-adapter/v1/` | SC duplex panel adapter |
| `library/components/common/{st,fc,lsh}-simplex-adapter/v1/` | the three simplex adapters |
| `library/components/common/mdc-adapter/v1/` | MDC 2-port duplex adapter |
| `library/components/common/keystone-clip/v1/` | the multimedia panel's clip opening |

**Why a separate `std/mpo` aperture and `common/mpo-adapter`:** this is the
shape `std/lc-bore@3` and `common/lc-duplex-adapter@3` already use — the `std/`
part is the hole in the panel, governed by a standard; the `common/` part is the
vendor's adapter that composes apertures and adds the body. Following it means
the MPO aperture can be reused by a transceiver face later without dragging a
panel adapter's bezel along.

---

### Task 1: Resolve the LC bore-pitch contradiction

**Files:**
- Modify: `library/components/common/lc-duplex-adapter/v3/contract.yaml`
- Test: `spec/tests/test_optical_resolve.py` (append)

**Interfaces:**
- Consumes: `optical.positions` from plan 1
- Produces: an `lc-duplex-adapter@3` whose composed bore pitch equals the
  standard's `pitch: 6.25`

**The contradiction.** `spec/schemas/standards.yaml` entry
`lc-duplex-receptacle` carries `pitch: 6.25` with `pitch-confidence: verified`,
sourced to IEC 61754-20 / TIA-604-10 FOCIS 10. `common/lc-duplex-adapter@3`
composes two `std/lc-bore@3` at x 0.95 and 7.55; each bore is 4.7 wide, so its
centres sit at 3.30 and 9.90 — **6.60 apart**. Nothing compares the two, so a
verified figure and a vendor-stencil reading have disagreed silently.

**The ruling this task implements: the standard wins.** A figure marked
`verified` against a published interface standard outranks one marked `measured`
off a single vendor's Visio stencil, and the adapter's own provenance admits the
stencil is where 6.6 came from. The bores move to the standard pitch; the
adapter's overall 13.2 width does NOT change, because that was measured from
abutting adapters on a real faceplate and is a different quantity.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_optical_resolve.py`:

```python
def test_the_adapters_bore_pitch_matches_the_verified_standard():
    """The library held two numbers for one physical quantity.

    `standards.yaml`'s `lc-duplex-receptacle` carries `pitch: 6.25` at
    `pitch-confidence: verified`, from IEC 61754-20 / TIA-604-10 FOCIS 10.
    The adapter composed its two bores 6.60 apart, from the Smartoptics DCP-R
    stencil. Nothing compared them, so they disagreed by 5.6% in silence.

    The standard wins: `verified` against a published interface standard
    outranks `measured` off one vendor's Visio artwork.
    """
    import yaml as _yaml
    std = _yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())
    want = std["standards"]["lc-duplex-receptacle"]["pitch"]

    c = contract("common/lc-duplex-adapter@3")
    bore_w = contract("std/lc-bore@3")["size"]["w"]
    xs = [p["at"][0] for p in c["parts"] if p["ref"] == "std/lc-bore@3"]
    assert len(xs) == 2, xs
    centres = sorted(x + bore_w / 2 for x in xs)
    assert round(centres[1] - centres[0], 4) == want, (
        f"bores are {centres[1] - centres[0]:.2f} apart; the standard says {want}")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest spec/tests/test_optical_resolve.py -q`
Expected: FAIL — `bores are 6.60 apart; the standard says 6.25`

- [ ] **Step 3: Move the bores onto the standard pitch**

The pair must stay centred in the 13.2-wide adapter. Centres go at
`13.2/2 ± 6.25/2` = **3.175 and 9.425**; each bore's `at.x` is its centre minus
half the 4.7 bore width, so **0.825 and 7.075**.

In `library/components/common/lc-duplex-adapter/v3/contract.yaml`, bump
`version: 3.3.0` to `3.4.0` and change the two part lines to:

```yaml
  - {ref: std/lc-bore@3, id: tx, at: [0.825, 1.55], lift: 3.175, rotate: 180}
  - {ref: std/lc-bore@3, id: rx, at: [7.075, 1.55], lift: 3.175, rotate: 180}
```

- [ ] **Step 4: Record the reconciliation in provenance**

Replace the `bore-spacing` key under `provenance:` with:

```yaml
  bore-spacing: >-
    THE STANDARD, NOT THE STENCIL. 6.25 between bore centres, from
    standards.yaml's `lc-duplex-receptacle` entry, which carries it at
    `pitch-confidence: verified` sourced to IEC 61754-20 / TIA-604-10 FOCIS 10.
    THIS WAS 6.6 AND THE TWO DISAGREED IN SILENCE. 6.6 was measured off the
    Smartoptics DCP-R stencil - 'the pitch of abutting adapters on the
    DCP-R-34D-CS faceplate', held across 35 adapters - and it is a good reading
    of a drawing that is itself a simplification. A figure marked `verified`
    against a published interface standard outranks one marked `measured` off
    one vendor's Visio artwork, and nothing in the library compared them until
    L81 was written.
    THE 13.2 WIDTH IS UNCHANGED and is a different quantity: the pitch of
    ABUTTING ADAPTERS on a faceplate, not of bores within one. FS's own artwork
    measures that at 12.90 on the FHD cassette face, which is a third reading of
    a third thing and is recorded on the FS parts rather than here.
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 -m pytest spec/tests/test_optical_resolve.py -q`
Expected: PASS

- [ ] **Step 6: Run the gate chain**

```bash
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library
```
Expected tail: `LINT: ok (654 files, 1291 warnings in 22 rules)`. If `[L53]`
names devices composing this adapter, bump each device's `version:` FIRST, then:

```bash
./publish.sh --no-images
python3 spec/tools/portrayal/devicelock.py --library library --update
./publish.sh --no-images
python3 -m pytest spec/tests -q -p no:randomly
```
Expected: devicelock `0 finding(s)` on a re-run; pytest `1394 passed, 1 skipped`.

- [ ] **Step 7: Commit**

```bash
git add library/ spec/tests/test_optical_resolve.py
git commit -m "lc-duplex-adapter: the bores sit at the standard pitch, not the stencil's

standards.yaml carries lc-duplex-receptacle at pitch 6.25, verified against
IEC 61754-20 / TIA-604-10 FOCIS 10. The adapter composed its bores 6.60 apart,
measured off the Smartoptics DCP-R stencil. Two numbers for one physical
quantity, 5.6% apart, and nothing in the library compared them.

The standard wins: verified against a published interface standard outranks
measured off one vendor's Visio artwork. The 13.2 overall width does not move -
that is the pitch of ABUTTING ADAPTERS on a faceplate, a different quantity, and
it stays measured.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: L81 — a composed pitch matches the standard it conforms to

**Files:**
- Modify: `spec/tools/portrayal/lint.py` (RULES table; rule; dispatch in `main`)
- Modify: `docs/lint-rules.md` (regenerated)
- Test: `spec/tests/test_pitch_lint.py` (create)

**Interfaces:**
- Consumes: `_contract(ref, lib_roots)` in `lint.py`, which returns a parsed
  contract for a ref like `std/lc-bore@3`
- Produces: `lint_component_composed_pitch(path, data, lib_roots)`

**Why this rule.** Task 1 fixed one instance of a whole class: a component
composing several copies of a standardised part, at a spacing nothing checks.
Every connector this plan adds is that shape. Without the rule the next one
drifts the same way and nobody notices for a year.

- [ ] **Step 1: Write the failing test**

Create `spec/tests/test_pitch_lint.py`:

```python
"""L81: a composed pitch matches the standard the composed part conforms to.

The library held `lc-duplex-receptacle.pitch: 6.25` at verified confidence and
an adapter composing its bores 6.60 apart, and nothing compared them. This is
the rule that would have caught it, written after the fact so the next connector
cannot repeat it.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))
import lint as L  # noqa: E402

LIB = [str(ROOT / "library")]

# STANDARDS IS EMPTY ON A PLAIN IMPORT, and that would make every test here pass
# for the wrong reason. `lint.py` fills it inside `main()`, so a unit test that
# calls a rule directly sees `{}`, the rule finds no standard for any `conforms`
# key, returns early, and raises nothing - a green suite against a rule that did
# nothing. Load it here, once, the same way main does.
L.STANDARDS.update(
    L.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])


def run(doc, path="t/contract.yaml"):
    L.ERRORS.clear()
    L.lint_component_composed_pitch(path, doc, LIB)
    return [e for e in L.ERRORS if "[L81]" in e]


def test_the_standards_registry_is_loaded_for_these_tests():
    """Guard the guard: without this the rest of the file passes vacuously."""
    assert L.STANDARDS.get("lc-duplex-receptacle", {}).get("pitch") == 6.25


def adapter(xs):
    """A part composing `std/lc-bore@3` (4.7 wide, pitch 6.25) at these x."""
    return {"kind": "component", "size": {"w": 13.2, "h": 11.0},
            "parts": [{"ref": "std/lc-bore@3", "id": i, "at": [x, 1.55]}
                      for i, x in zip(("tx", "rx"), xs)]}


def test_a_composed_pitch_off_the_standard_is_caught():
    hits = run(adapter([0.95, 7.55]))          # 6.60 apart
    assert len(hits) == 1, hits
    assert "6.6" in hits[0] and "6.25" in hits[0]


def test_the_standard_pitch_is_silent():
    assert run(adapter([0.825, 7.075])) == []   # 6.25 apart


def test_one_instance_has_no_pitch_to_check():
    doc = {"kind": "component", "size": {"w": 6.0, "h": 11.0},
           "parts": [{"ref": "std/lc-bore@3", "id": "tx", "at": [0.65, 1.55]}]}
    assert run(doc) == []


def test_a_part_whose_standard_states_no_pitch_is_silent():
    """`conforms` alone is not enough - the standard must carry a `pitch`."""
    doc = {"kind": "component", "size": {"w": 40.0, "h": 20.0},
           "parts": [{"ref": "std/sfp@1", "id": "a", "at": [0.0, 0.0]},
                     {"ref": "std/sfp@1", "id": "b", "at": [20.0, 0.0]}]}
    assert run(doc) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest spec/tests/test_pitch_lint.py -q`
Expected: FAIL — `AttributeError: ... 'lint_component_composed_pitch'`

- [ ] **Step 3: Add the rule**

In `spec/tools/portrayal/lint.py`, add to `RULES` after the `"L80"` entry:

```python
    "L81": ("component",  "a composed pitch matches the standard the part conforms to", "move the parts onto the standard's pitch, or say in provenance why this part differs"),
```

Add this function immediately after `lint_component_optical_coverage`:

```python
def lint_component_composed_pitch(path, data, lib_roots):
    """L81: a composed pitch matches the standard the composed part conforms to.

    THE LIBRARY HELD BOTH NUMBERS AND COMPARED NEITHER. standards.yaml carried
    `lc-duplex-receptacle.pitch: 6.25` at verified confidence, from IEC 61754-20
    / TIA-604-10 FOCIS 10, while common/lc-duplex-adapter@3 composed its two
    bores 6.60 apart from a vendor stencil. 5.6% apart, both written down, for as
    long as both existed.

    A component composing SEVERAL copies of one part that `conforms:` to a
    standard carrying a `pitch` is making a claim about that pitch whether it
    means to or not. This checks it. Only the evenly-spaced case is checked -
    parts at irregular spacing are a different drawing, not a pitch.

    The escape hatch is deliberate and narrow: a part that really does space its
    connectors off-standard says so in `provenance.pitch-note`, and the rule
    stands down. Silence is not an escape hatch.
    """
    parts = [p for p in (data.get("parts") or []) if isinstance(p, dict)]
    if len(parts) < 2:
        return
    if (data.get("provenance") or {}).get("pitch-note"):
        return
    by_ref = {}
    for p in parts:
        if p.get("ref") and p.get("at"):
            by_ref.setdefault(p["ref"], []).append(float(p["at"][0]))
    for ref, xs in sorted(by_ref.items()):
        if len(xs) < 2:
            continue
        sub = _contract(ref, lib_roots) or {}
        key = sub.get("conforms")
        if not key:
            continue
        std = STANDARDS.get(key) or {}
        want = std.get("pitch")
        if not want:
            continue
        xs = sorted(xs)
        gaps = [round(xs[i] - xs[i - 1], 4) for i in range(1, len(xs))]
        if len(set(gaps)) != 1:
            continue                      # irregular spacing is not a pitch
        got = gaps[0]
        if abs(got - float(want)) > 0.01:
            err(path, "L81", f"composes {len(xs)} x {ref} at a pitch of {got:g} "
                             f"and {key} states {want:g}. Move them onto the "
                             "standard, or record `provenance.pitch-note` saying "
                             "why this part differs")
```

Register it in `main`, immediately after the
`lint_component_optical_coverage(f, d, args.library)` line:

```python
                lint_component_composed_pitch(f, d, args.library)
```

- [ ] **Step 4: Know what `STANDARDS` is before you trust it**

`lint.py` declares `STANDARDS = {}` at module level (line 604) and fills it
inside `main()` with
`STANDARDS.update(load_yaml(std_file)["standards"])` (around line 6023). Two
consequences, both already handled above and both worth understanding:

- It holds the standards **directly**, not nested under a `"standards"` key, so
  the rule reads `STANDARDS.get(key)`.
- It is **empty after a plain import**, so the test file loads it itself. Without
  that, every test in Task 2 would pass for the wrong reason: the rule would find
  no standard for any `conforms` key, return early, and raise nothing.
  `test_the_standards_registry_is_loaded_for_these_tests` is the guard against
  that, and it is why that test exists.

Verify both before continuing:

```bash
python3 -c "import sys; sys.path.insert(0,'spec/tools/portrayal'); import lint; print(len(lint.STANDARDS))"
```
Expected: `0` — confirming the test file must load it.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest spec/tests/test_pitch_lint.py -q`
Expected: PASS (4 passed)

- [ ] **Step 6: Regenerate the rules page and run the gate chain**

```bash
python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md
python3 -m pytest spec/tests/test_lint_rules_catalogue.py -q
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library
python3 -m pytest spec/tests -q -p no:randomly
```
Expected: catalogue test 7 passed; lint tail unchanged at
`LINT: ok (654 files, 1291 warnings in 22 rules)` — Task 1 already moved the one
part that would have fired; pytest `1398 passed, 1 skipped`.

**If lint reports L81 errors on parts this plan has not touched**, do not silence
them. Read each: it is either a real drift worth its own commit, or a part whose
spacing genuinely differs and needs a `provenance.pitch-note`. Report what you
found before continuing.

- [ ] **Step 7: Commit**

```bash
git add spec/tools/portrayal/lint.py spec/tests/test_pitch_lint.py docs/lint-rules.md
git commit -m "lint: L81 - a composed pitch matches the standard it conforms to

The library held lc-duplex-receptacle.pitch 6.25 at verified confidence and an
adapter composing its bores 6.60 apart, 5.6% adrift, both written down and
neither compared. This is the rule that would have caught it.

Every connector this plan adds is the same shape - several copies of a
standardised aperture at a spacing nothing checks - so the rule lands before
they do rather than after the next drift.

The escape hatch is narrow on purpose: a part that really does space its
connectors off-standard writes provenance.pitch-note and the rule stands down.
Silence is not an escape hatch.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: The panel measurement tool

**Files:**
- Create: `spec/tools/intake/panel-measure.py`
- Test: `spec/tests/test_panel_measure.py`

**Interfaces:**
- Produces:
  - `plate(im) -> (x0, y0, x1, y1, mm_per_px)` — the faceplate's bounds in the
    image and the scale from the known 108.97 mm module width
  - `validate(mm_per_px, y0, y1) -> float` — the percentage by which the scaled
    plate height misses the known 35.05 mm; the caller decides the threshold
  - `openings(im, box, mm, band, test) -> [(x0_mm, x1_mm, centre_mm)]`

**Why a tool.** Six connector tasks below each measure a face the same way, and
the measurement is the evidence their provenance rests on. Written once it can be
tested; written six times inline it is six chances to scale on the wrong edge.

- [ ] **Step 1: Write the failing test**

Create `spec/tests/test_panel_measure.py`:

```python
"""The panel measurer, checked against a face whose answer is already known.

35510.G.jpg is the 12x MTP adapter panel, face-on. Its faceplate must scale to
108.97 x 35.05 within a few percent, and its openings must come out as two rows
of six at a consistent pitch. If the tool cannot reproduce that, no connector
measured with it can be trusted.
"""
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
IMG = pathlib.Path("/Volumes/External/Network-Device-Visualization/working/"
                   "intake/fs/fhd/photos")
sys.path.insert(0, str(ROOT / "spec/tools/intake"))


@pytest.fixture(scope="module")
def pm():
    return pytest.importorskip("panel_measure")


def _im(pm, name):
    Image = pytest.importorskip("PIL.Image")
    p = IMG / name
    if not p.exists():
        pytest.skip(f"{name} not staged - reference imagery lives in working/")
    return Image.open(p).convert("RGB")


def test_the_mtp_panel_scales_true_on_both_axes(pm):
    im = _im(pm, "35510.G.jpg")
    x0, y0, x1, y1, mm = pm.plate(im)
    off = pm.validate(mm, y0, y1)
    assert off < 3.0, (
        f"the plate scales to {(y1 - y0 + 1) * mm:.2f} mm tall against a known "
        f"35.05 - {off:.1f}% out. Either the image is not face-on or `plate` "
        "found the wrong band")


def test_the_mtp_panel_has_six_openings_per_row(pm):
    im = _im(pm, "35510.G.jpg")
    box = pm.plate(im)
    top = pm.openings(im, box, band=(0.10, 0.45), min_mm=4.0)
    assert len(top) == 6, [round(c, 2) for _a, _b, c in top]
    pitches = [top[i][2] - top[i - 1][2] for i in range(1, 6)]
    spread = max(pitches) - min(pitches)
    assert spread < 2.0, f"pitches {pitches} spread {spread:.2f} - not a pitch"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest spec/tests/test_panel_measure.py -q`
Expected: SKIP or FAIL — module `panel_measure` does not exist.

Note the module is imported as `panel_measure` but the file is
`panel-measure.py`; create it as **`panel_measure.py`** so it is importable. The
sibling tools in that directory use hyphens because they are only ever run as
scripts; this one is imported, so it uses an underscore.

- [ ] **Step 3: Write the tool**

Create `spec/tools/intake/panel_measure.py`:

```python
#!/usr/bin/env python3
"""Measure an FHD module face from a face-on product render.

THE SCALE COMES FROM THE FACEPLATE AND IS CHECKED AGAINST THE OTHER AXIS. Every
FHD cassette and adapter panel is 108.97 x 35.05 mm, dimensioned on FS's own
render of SKU 57016. So a face-on image can be scaled on its plate width and then
VERIFIED by asking whether that scale reproduces the plate height. A
three-quarter render fails that check, which is the whole point: it is what
separates a measurement from a guess, and five of the eight connectors in this
plan have only three-quarter renders and are therefore estimated instead.

The faceplate is the widest full-width dark band in the image - the module body
behind it is narrower and sits above it in these renders.
"""
W_MM = 108.97
H_MM = 35.05


def _dark(p):
    return sum(p) < 690


def plate(im):
    """(x0, y0, x1, y1, mm_per_px) for the faceplate in a face-on render."""
    px, py = im.size
    rows = []
    for y in range(py):
        xs = [x for x in range(px) if _dark(im.getpixel((x, y)))]
        rows.append((y, (xs[-1] - xs[0] + 1) if xs else 0, xs[0] if xs else 0))
    wmax = max(w for _y, w, _x in rows)
    band = [(y, x0) for y, w, x0 in rows if w > wmax * 0.97]
    y0, y1, x0 = band[0][0], band[-1][0], band[0][1]
    return x0, y0, x0 + wmax - 1, y1, W_MM / wmax


def validate(mm, y0, y1):
    """Percent by which the scaled plate height misses the known 35.05 mm."""
    return abs((y1 - y0 + 1) * mm - H_MM) / H_MM * 100


def runs(mask, gap=3):
    out, start, hole = [], None, 0
    for i, v in enumerate(mask):
        if v:
            if start is None:
                start = i
            hole = 0
        elif start is not None:
            hole += 1
            if hole > gap:
                out.append((start, i - hole))
                start = None
    if start is not None:
        out.append((start, len(mask) - 1))
    return out


def _pale(p):
    r, g, b = p
    return b > 120 and r > 90 and abs(b - r) < 90 and sum(p) > 330


def openings(im, box, band=(0.10, 0.90), min_mm=4.0, test=_pale):
    """Adapter openings across a horizontal band, as (x0_mm, x1_mm, centre_mm).

    `band` is the fraction of the plate height to scan between. The default
    `test` finds the pale interior of an adapter against a black plate; pass
    another for a panel whose adapters are not pale.

    `min_mm` DISCARDS THE THUMB-KNOBS. Every FHD panel carries two of them, one
    at each end, and they are round, dark-edged and about 2.5 mm of pale in these
    renders - narrow enough to separate from a real opening by width alone, and
    wide enough to wreck a pitch if left in. Measured on 35510.G they turned a
    13.8 mm pitch into a 14.5 mm mean with a 7.9 spread.
    """
    x0, y0, x1, y1, mm = box
    ya = y0 + int((y1 - y0) * band[0])
    yb = y0 + int((y1 - y0) * band[1])
    col = []
    for x in range(x0, x1 + 1):
        n = sum(1 for y in range(ya, yb) if test(im.getpixel((x, y))))
        col.append(n > (yb - ya) * 0.30)
    out = []
    for a, b in runs(col):
        w = (b + 1 - a) * mm
        if w < min_mm:
            continue
        out.append((a * mm, (b + 1) * mm, ((a + b + 1) / 2) * mm))
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest spec/tests/test_panel_measure.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add spec/tools/intake/panel_measure.py spec/tests/test_panel_measure.py
git commit -m "intake: measure an FHD face, and check the scale against both axes

Six connector contracts rest on measurements of FS product renders, and the
measurement is the evidence. Written once it can be tested; written inline six
times it is six chances to scale on the wrong edge.

The validation is the point: scaling on the 108.97 plate width and then asking
whether that scale reproduces the 35.05 height is what separates a face-on
render from a three-quarter one. Five of this plan's eight connectors fail that
check and are estimated instead, and the tool is how we know which is which.

min_mm discards the thumb-knobs - two per panel, about 2.5 mm of pale each,
which turned the MTP panel's 13.8 pitch into a 14.5 mean with a 7.9 spread.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: The MPO aperture and its panel adapter

**Files:**
- Modify: `spec/schemas/standards.yaml`
- Create: `library/components/std/mpo/v1/contract.yaml`, `.../skins/default.svg`
- Create: `library/components/common/mpo-adapter/v1/contract.yaml`, `.../skins/default.svg`
- Test: `spec/tests/test_connector_family.py` (create)

**Interfaces:**
- Consumes: `panel_measure.plate/validate/openings` from Task 3
- Produces: `std/mpo@1` (the aperture, `conforms: mpo-adapter`) and
  `common/mpo-adapter@1` (the panel-mount adapter, `optical.positions` set per
  fibre count)

**The measurement, already taken.** `35510.G.jpg` is the 12× MTP panel, face-on,
scale validated at 1.7%. Excluding the two thumb-knobs it gives:

```
top row    6 openings, centres 18.50 32.78 45.95 59.81 73.66 87.34
           pitches 14.28 13.17 13.86 13.85 13.68 -> mean 13.77, spread 1.11
bottom row 6 openings, centres 19.68 33.79 47.30 61.16 74.84 88.70
           pitches 14.11 13.51 13.86 13.68 13.86 -> mean 13.80, spread 0.60
row pitch  15.97
opening    about 7.8 wide
```

**Take 13.8 as the pitch** — the two rows agree to 0.03 and the bottom row's
spread is 0.60, which is render noise rather than a second figure. The opening
width is softer: the detection catches a bevelled interior and reads 5.4 to 8.5
across the rows, so **7.8 is an estimate inside a measured pitch**.

- [ ] **Step 1: Write the failing test**

Create `spec/tests/test_connector_family.py`:

```python
"""The connector components this plan adds, checked against their own claims.

Each connector declares a fibre capacity that plan 1's `optical` rules read, and
a size that is the panel aperture. These tests pin the facts other contracts will
compose against - a wrong `positions` silently mis-models every module using it.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def contract(ref):
    name, major = ref.split("@")
    p = LIB / "components" / name / f"v{major}" / "contract.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def test_the_mpo_aperture_exists_and_conforms():
    c = contract("std/mpo@1")
    assert c is not None, "std/mpo@1 not built"
    assert c["conforms"] == "mpo-adapter"
    assert c["class"] == "port"


def test_the_mpo_adapter_presents_twelve_fibres_by_default():
    c = contract("common/mpo-adapter@1")
    assert c is not None, "common/mpo-adapter@1 not built"
    assert (c.get("optical") or {}).get("positions") == 12, (
        "an MPO-12 is twelve fibres; every module composing it inherits this")


def test_the_mpo_standard_records_the_measured_pitch():
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())
    s = std["standards"]["mpo-adapter"]
    assert s["pitch"] == 13.8
    assert s["pitch-confidence"] == "measured"
    assert "35510" in s["registry"], (
        "the registry entry must name the image the pitch was measured from")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest spec/tests/test_connector_family.py -q`
Expected: FAIL — `std/mpo@1 not built`

- [ ] **Step 3: Add the standards entry**

In `spec/schemas/standards.yaml`, add under `standards:` (alphabetical placement
is not enforced; put it after `lc-duplex-receptacle`):

```yaml
  mpo-adapter:
    registry: >-
      MEASURED, NOT READ FROM A STANDARD. IEC 61754-7 governs the MPO interface
      and is not held here, so the pitch comes from FS's own face-on render of
      SKU 35510 (FHD 12x MTP-8/12/24 adapter panel), scaled on the 108.97 mm FHD
      module width and validated against the 35.05 mm height to 1.7%.
    w: 7.8
    h: 5.6
    confidence: estimated
    pitch: 13.8
    pitch-confidence: measured
    notes: >-
      The panel APERTURE for an MPO/MTP adapter, which uses the SC-duplex
      footprint - that compatibility is why an MPO adapter drops into an SC
      opening and why the pitch lands near an SC's.
      THE PITCH IS THE STRONG HALF AND THE APERTURE IS THE WEAK ONE. Two rows of
      six on 35510 give 13.77 and 13.80 with spreads of 1.11 and 0.60, so 13.8 is
      a measurement. The 7.8 x 5.6 opening is not: the detection catches a
      bevelled interior and reads 5.4 to 8.5 across the rows, so the aperture is
      an estimate sitting inside a measured pitch. A caliper on one adapter, or
      IEC 61754-7, settles it.
      Fibre count is a property of the FERRULE, not the adapter: MPO-8, -12, -16
      and -24 share this opening. The component carries the count in
      `optical.positions`.
```

- [ ] **Step 4: Create the aperture component**

Create `library/components/std/mpo/v1/contract.yaml`:

```yaml
format: 1
kind: component
name: mpo
version: 1.0.0
class: port
profile: networking
conforms: mpo-adapter
description: >-
  One MPO/MTP adapter opening in a panel - the aperture, not the adapter. The
  panel-mount part that carries a bezel and a latch is common/mpo-adapter@1;
  this is the hole it sits in, and is shared by MPO-8, -12, -16 and -24 because
  fibre count is a property of the ferrule rather than of the opening.
size: {w: 7.8, h: 5.6, d: 9.0}
attrs: {media: fiber, connector: mpo}
provenance:
  size: >-
    ESTIMATED - see standards.yaml's `mpo-adapter` entry. Measured off FS's
    face-on render of SKU 35510 with the plate scale validated to 1.7% on the
    second axis, but the opening's own edges are bevelled and read 5.4 to 8.5
    across the two rows. The PITCH from that render is a measurement; this
    aperture is an estimate inside it. IEC 61754-7 would settle it and is not
    held here.
  depth: >-
    ESTIMATED at 9.0. No document held here gives an MPO adapter's recess depth.
    Stated so the part has a solid in 3D rather than a plane; replace it the
    moment anything states one.
elements:
  opening: {at: [0, 0], size: [7.8, 5.6], class: cutout}
relief:
  # CAVITY ALONE, NO POCKET. `relief.cavity` names the skin node whose art is the
  # recess, and render.py then puts `data-depth` on this component's own instance
  # group using `size.d`. Adding a `pocket` on that SAME node would put a second
  # `data-depth` inside the first, and relief.js builds only the innermost cavity
  # of a nest - so the aperture would delete itself. Plan 1 landed
  # `test_a_pocket_does_not_swallow_the_cavity_it_sits_in` for exactly that, and
  # no component in the library sets both on one node. std/lc-bore@3 is the
  # precedent: `cavity: bore`, depth from `size.d`, pockets only on other nodes.
  wall: '#2a2f35'
  cavity: opening
skins: [default]
```

Create `library/components/std/mpo/v1/skins/default.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="7.8mm" height="5.6mm" viewBox="0 0 7.8 5.6">
  <!-- One MPO/MTP adapter opening, 7.8 x 5.6.

       THE APERTURE, NOT THE ADAPTER. What is drawn is the hole: a rounded
       rectangle with the bevel FS's renders show around the interior. The
       bezel, latch and body belong to common/mpo-adapter@1, which composes
       this.

       The opening is drawn pale because that is what the renders show - an MPO
       adapter's interior is a light grey sleeve against a black plate, which is
       how the openings were found by colour when the panel was measured. -->
  <rect id="opening" x="0" y="0" width="7.8" height="5.6" rx="0.4"
        fill="#8e97a4" stroke="#1b1e22" stroke-width="0.25"/>
  <rect id="bevel" x="0.55" y="0.5" width="6.7" height="4.6" rx="0.25"
        fill="#aab3bf"/>
</svg>
```

- [ ] **Step 5: Create the panel adapter component**

Create `library/components/common/mpo-adapter/v1/contract.yaml`:

```yaml
format: 1
kind: component
name: mpo-adapter
version: 1.0.0
class: port
profile: networking
description: >-
  Panel-mount MPO/MTP adapter - one opening in a bezel, as fitted to an FS FHD
  adapter panel. Twelve fibres by default; an MPO-8, -16 or -24 is the same
  adapter with a different ferrule, and says so by overriding
  `optical.positions` on its placement.
size: {w: 13.8, h: 9.4}
attrs: {media: fiber, connector: mpo, fibres: '12'}
optical:
  # TWELVE FIBRES IN ONE FERRULE, which is the whole point of the connector and
  # the reason a cassette needs only one of these on its rear. MPO-8, -16 and
  # -24 share this adapter and this opening - the count is a property of the
  # ferrule - so a module using another count overrides this on its placement
  # rather than composing a different part.
  positions: 12
provenance:
  size: >-
    MEASURED for the width, ESTIMATED for the height. 13.8 is the adapter pitch
    on FS's face-on render of SKU 35510, where two rows of six give 13.77 and
    13.80 with spreads of 1.11 and 0.60 - abutting adapters, so the pitch IS the
    width. The 9.4 height is inferred from the panel's 15.97 row pitch less a
    plausible divider and is not measured.
  fibre-count: >-
    catalogue - FS's FHD panels are sold as `12 x MTP-8/12/24`, one opening
    taking any of the three ferrules. 12 is the default because it is the count
    the FHD cassettes' rear connectors use; see the FS catalogue at
    working/intake/fs/fhd/CATALOGUE.tsv.
  face-detail-gap: >-
    no orthographic photograph of an MPO adapter exists here; the reading is off
    a product RENDER. The latch, the key orientation and any keying mark are not
    modelled, and the key direction matters - FS sells `Up-Down Type A` and
    `Up-Up Type B` panels as different SKUs, which this part does not yet
    distinguish.
parts:
  - {ref: std/mpo@1, id: bore, at: [3.0, 1.9]}
relief:
  wall: '#22262a'
  features:
    - node: bezel
      out: 1.2
      confidence: estimated
      source: >-
        the adapter's flange stands slightly proud of the panel, as the renders
        show. 1.2 is not measured; nothing in the corpus dimensions it.
skins: [default]
```

Create `library/components/common/mpo-adapter/v1/skins/default.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="13.8mm" height="9.4mm" viewBox="0 0 13.8 9.4">
  <!-- Panel-mount MPO/MTP adapter, 13.8 x 9.4.

       THE APERTURE IS NOT DRAWN HERE. std/mpo@1 is composed by the contract at
       3.0, 1.9; this skin is the bezel it sits in.

       13.8 IS A PITCH USED AS A WIDTH, and that is sound because the adapters
       abut: on FS's 12x MTP panel the six across a row are edge to edge, so the
       centre-to-centre distance and the body width are the same number. The
       9.4 height is not measured - see the contract's `size` provenance. -->
  <defs>
    <linearGradient id="bez" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#3c4248"/>
      <stop offset="1" stop-color="#23272c"/>
    </linearGradient>
  </defs>
  <rect id="bezel" x="0" y="0" width="13.8" height="9.4" rx="0.5"
        fill="url(#bez)" stroke="#15181a" stroke-width="0.2"/>
</svg>
```

- [ ] **Step 6: Run the tests**

Run: `python3 -m pytest spec/tests/test_connector_family.py -q`
Expected: PASS (3 passed)

- [ ] **Step 7: Run the gate chain**

```bash
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library
./publish.sh --no-images
python3 spec/tools/portrayal/devicelock.py --library library
python3 -m pytest spec/tests -q -p no:randomly
```
Expected: lint file count rises by 4 (two contracts, two skins) to
`658 files`; the warning count must stay at `1291 warnings in 22 rules`. If lint
reports new warnings against these parts, read them — a connector is a small
contract and the rules that fire on one are usually L35 (confidence) or L9
(size against the standard), both of which mean a real omission.

- [ ] **Step 8: Commit**

```bash
git add spec/schemas/standards.yaml library/ spec/tests/test_connector_family.py
git commit -m "std/mpo and common/mpo-adapter: the connector 48 FS modules need

The library had no MPO part at all - every MTP mention across 62 cassettes and
15 panels was prose in a description. This is the aperture and the panel adapter
that composes it, following std/lc-bore and common/lc-duplex-adapter's split
between the hole and the vendor's part around it.

The pitch is measured and the aperture is not, and the contracts say which is
which. FS's face-on render of SKU 35510 gives two rows of six at 13.77 and 13.80
with spreads of 1.11 and 0.60, so 13.8 is a measurement; the opening's bevelled
edges read 5.4 to 8.5 across those rows, so 7.8 x 5.6 is an estimate sitting
inside it. IEC 61754-7 would settle the aperture and is not held here.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: SC duplex adapter

**Files:**
- Modify: `spec/schemas/standards.yaml`
- Create: `library/components/common/sc-duplex-adapter/v1/contract.yaml`, `.../skins/default.svg`
- Test: `spec/tests/test_connector_family.py` (append)

**Interfaces:**
- Consumes: `panel_measure` from Task 3
- Produces: `common/sc-duplex-adapter@1` with `optical.positions: 2`

**Measure it first.** `57058.main.jpg` is the MTP-12 → SC cassette, face-on. Run
this and use the numbers it prints:

```bash
python3 - <<'PY'
import sys, pathlib
sys.path.insert(0, 'spec/tools/intake')
import panel_measure as pm
from PIL import Image
im = Image.open(pathlib.Path('/Volumes/External/Network-Device-Visualization/'
                             'working/intake/fs/fhd/photos/57058.main.jpg')).convert('RGB')
box = pm.plate(im)
print('scale check: %.2f%% off on the second axis' % pm.validate(box[4], box[1], box[3]))
for a, b, c in pm.openings(im, box, band=(0.25, 0.75), min_mm=4.0):
    print('  opening %6.2f .. %6.2f  centre %6.2f  (w %.2f)' % (a, b, c, b - a))
PY
```

**If the scale check is above 3%, stop and report BLOCKED** — the render is not
face-on and this connector joins the estimated five instead. Otherwise the
printed centres give the pitch; record it as `measured` with the SKU named, and
the opening width as `estimated` for the same bevel reason as the MPO.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_connector_family.py`:

```python
def test_the_sc_duplex_adapter_presents_two_fibres():
    c = contract("common/sc-duplex-adapter@1")
    assert c is not None, "common/sc-duplex-adapter@1 not built"
    assert (c.get("optical") or {}).get("positions") == 2


def test_the_sc_standard_names_where_its_pitch_came_from():
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())
    s = std["standards"]["sc-duplex-adapter"]
    assert s["pitch-confidence"] in ("measured", "estimated")
    assert "57058" in s["registry"] or "61754-4" in s["registry"], (
        "name the image or the standard the pitch came from")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest spec/tests/test_connector_family.py -q`
Expected: FAIL — `common/sc-duplex-adapter@1 not built`

- [ ] **Step 3: Add the standards entry**

Add to `spec/schemas/standards.yaml` under `standards:`, filling `w`, `h` and
`pitch` from the measurement you just ran:

```yaml
  sc-duplex-adapter:
    registry: >-
      MEASURED, NOT READ FROM A STANDARD. IEC 61754-4 governs the SC interface
      and is not held here. The pitch comes from FS's face-on render of SKU
      57058 (FHD MTP-12 to SC cassette), scaled on the 108.97 mm FHD module
      width and validated against the 35.05 mm height.
    w: <opening width from the measurement>
    h: <opening height, estimated - see notes>
    confidence: estimated
    pitch: <measured pitch>
    pitch-confidence: measured
    notes: >-
      The panel APERTURE for an SC duplex adapter. As with the MPO entry the
      pitch is the strong half and the aperture the weak one: the opening's
      edges are bevelled in the render and read across a range, so w and h are
      estimates inside a measured pitch. IEC 61754-4 settles them.
```

- [ ] **Step 4: Create the component**

Create `library/components/common/sc-duplex-adapter/v1/contract.yaml` following
the shape of `common/mpo-adapter@1` from Task 4 — same keys, same provenance
discipline — with `optical.positions: 2`, `attrs: {media: fiber, connector: sc}`,
and the measured pitch as the width. Write its `provenance.size` naming SKU
57058 and the validated scale percentage you measured, and a
`provenance.face-detail-gap` recording that the reading is off a render rather
than a photograph.

Create the skin as a bezel rect in the same style as `mpo-adapter`'s, sized to
the contract's `size`, with a comment saying which SKU the geometry came from.

- [ ] **Step 5: Run the tests and the gate chain**

```bash
python3 -m pytest spec/tests/test_connector_family.py -q
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library
./publish.sh --no-images
python3 spec/tools/portrayal/devicelock.py --library library
python3 -m pytest spec/tests -q -p no:randomly
```
Expected: connector tests 5 passed; lint warning count unchanged at 1291.

- [ ] **Step 6: Commit**

```bash
git add spec/schemas/standards.yaml library/ spec/tests/test_connector_family.py
git commit -m "common/sc-duplex-adapter: the SC panel adapter, measured off 57058

Five FS modules take SC duplex and the library had no panel-mount SC adapter -
common/sc-apc@1 is a device-specific moulded bay off an HLX-TGV, not this.

Measured the same way as the MPO: face-on render, scaled on the 108.97 plate
width, validated against the 35.05 height. The pitch is a measurement and the
aperture is an estimate inside it, and the contract says which is which.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: The five estimated connectors

**Files:**
- Modify: `spec/schemas/standards.yaml`
- Create: `library/components/common/st-simplex-adapter/v1/`,
  `.../fc-simplex-adapter/v1/`, `.../lsh-simplex-adapter/v1/`,
  `.../mdc-adapter/v1/`, `.../keystone-clip/v1/` — contract and skin each
- Test: `spec/tests/test_connector_family.py` (append)

**Interfaces:**
- Produces: five components, each with `optical.positions` and every dimension
  marked `confidence: estimated`

**This task is different from 4 and 5 and must not pretend otherwise.** None of
these five has a face-on render. Jason's decision, taken with the provenance cost
stated, was to build them anyway from three-quarter renders plus panel
arithmetic. **The honesty of the provenance is this task's deliverable.**

**Panel arithmetic — the one piece of real evidence.** Each FHD panel is
108.97 mm wide and its adapter count is in the catalogue, so a pitch follows:

| part | panel SKU | adapters | usable span | derived pitch |
|---|---|---:|---|---|
| ST simplex | 183380 / 183381 | 6 / 8 | 108.97 less ~20 for the two thumb-knobs and margins | ~14.8 / ~11.1 |
| FC simplex | 382881 | 8 | as above | ~11.1 |
| LSH/E2000 | 336339 | 12 | as above | ~7.4 |
| MDC 2-port duplex | 147015 | 12 | as above | ~7.4 |
| keystone | 143239 | 6 | as above | ~14.8 |

Use the MPO panel to calibrate the "usable span" rather than guessing it: on
35510 the six openings per row span 18.50 to 87.34 mm centre to centre, so the
outermost centres sit 18.5 mm from one edge and 21.6 mm from the other. Take the
usable span as **the same 88.8 mm centre-to-centre envelope**, and the pitch as
`88.8 / (n - 1)` for n adapters in a row. State that derivation in every entry.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_connector_family.py`:

```python
import pytest  # noqa: E402


ESTIMATED = [
    ("common/st-simplex-adapter@1", 1),
    ("common/fc-simplex-adapter@1", 1),
    ("common/lsh-simplex-adapter@1", 1),
    ("common/mdc-adapter@1", 2),
    ("common/keystone-clip@1", 0),
]


@pytest.mark.parametrize("ref,positions", ESTIMATED)
def test_each_estimated_connector_exists_with_its_fibre_count(ref, positions):
    c = contract(ref)
    assert c is not None, f"{ref} not built"
    got = (c.get("optical") or {}).get("positions")
    if positions == 0:
        assert got is None, (
            "a keystone clip is a mechanical opening, not a fibre connector - "
            "it must declare no optical positions at all")
    else:
        assert got == positions


@pytest.mark.parametrize("ref,_positions", ESTIMATED)
def test_every_estimated_connector_says_it_is_estimated(ref, _positions):
    """The whole point of this task.

    These five were built from three-quarter renders because no face-on image
    exists. A dimension that does not say so reads exactly like one that was
    measured, and the next person cannot tell them apart.
    """
    c = contract(ref)
    prov = c.get("provenance") or {}
    assert prov.get("size"), f"{ref} states no size provenance"
    blob = " ".join(str(v) for v in prov.values()).upper()
    assert "ESTIMATE" in blob, (
        f"{ref}'s provenance never says its dimensions are estimated")
    assert "FACE-ON" in blob or "THREE-QUARTER" in blob or "RENDER" in blob, (
        f"{ref}'s provenance does not say what imagery it rests on")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest spec/tests/test_connector_family.py -q`
Expected: FAIL — `common/st-simplex-adapter@1 not built`

- [ ] **Step 3: Add five standards entries**

For each of the five, add an entry to `spec/schemas/standards.yaml` with
`confidence: estimated` and `pitch-confidence: estimated`, and a `registry` that
names the governing standard **as not held** plus the panel the pitch was derived
from. Use this shape, with the real numbers from the table above:

```yaml
  st-adapter:
    registry: >-
      NOT MEASURED AND NOT READ FROM A STANDARD. IEC 61754-2 governs the ST/BFOC
      interface and is not held here, and no face-on render of an FS ST panel
      exists - only a three-quarter product shot (SKU 183380). The pitch is
      DERIVED: FS sells this panel with 6 adapters, and the 12x MTP panel
      (35510, face-on) puts its outermost adapter centres 88.8 mm apart, so six
      across that envelope gives 88.8 / 5.
    w: 10.0
    h: 10.0
    confidence: estimated
    pitch: 17.76
    pitch-confidence: estimated
    notes: >-
      EVERY FIGURE HERE IS AN ESTIMATE AND THE APERTURE IS THE WEAKEST. The pitch
      at least follows from a count FS publishes and an envelope measured off a
      sibling panel; the 10.0 x 10.0 opening is a plausible round number for a
      bayonet adapter's bulkhead and rests on nothing. What settles it: a face-on
      photograph of SKU 183380, a caliper on one adapter, or IEC 61754-2.
```

Repeat for `fc-adapter` (IEC 61754-13, SKU 382881, 8 adapters),
`lsh-adapter` (IEC 61754-15, SKU 336339, 12 adapters),
`mdc-adapter` (no IEC part held; US Conec/Senko originate MDC, SKU 147015,
12 adapters) and `keystone-opening` (no fibre standard; the keystone form is a
de-facto ~14.8 x 19.3 mm opening, SKU 143239, 6 clips).

- [ ] **Step 4: Create the five components**

Each is a small contract in the shape of `common/mpo-adapter@1` from Task 4,
with:
- `class: port` for the four fibre adapters; **`class: mechanical` for
  `keystone-clip`**, which is a clip opening rather than a connector
- `optical.positions`: 1 for ST, FC and LSH (simplex, one fibre each), 2 for MDC
  (a 2-port duplex adapter presents two fibres), and **no `optical` block at all
  for `keystone-clip`** — it carries no fibre
- `provenance.size` that says ESTIMATED, names the SKU whose three-quarter render
  it rests on, states the derived pitch and its arithmetic, and says what would
  settle it
- a `provenance.face-detail-gap` recording that no face-on imagery exists

Each skin is a bezel rect in `mpo-adapter`'s style, sized to its contract's
`size`, with a comment naming the SKU and saying the geometry is estimated.

- [ ] **Step 5: Run the tests**

Run: `python3 -m pytest spec/tests/test_connector_family.py -q`
Expected: PASS (15 passed — 5 from Tasks 4 and 5, plus 10 parametrised here)

- [ ] **Step 6: Run the gate chain**

```bash
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library
./publish.sh --no-images
python3 spec/tools/portrayal/devicelock.py --library library
python3 -m pytest spec/tests -q -p no:randomly
```
Expected: lint file count up by 10; warning count still `1291 warnings in 22
rules`.

- [ ] **Step 7: Commit**

```bash
git add spec/schemas/standards.yaml library/ spec/tests/test_connector_family.py
git commit -m "five estimated connectors: ST, FC, LSH, MDC and the keystone clip

Eight FS modules take these between them and none has a face-on render - only
three-quarter product shots. Jason's call, made with the provenance cost stated,
was to build them anyway rather than leave those eight unbuildable.

So the honesty is the deliverable. Every dimension carries confidence:
estimated; every registry entry names the governing standard AS NOT HELD and the
SKU whose render it rests on; and each says what would settle it - a face-on
photograph, a caliper, or the IEC part.

The one piece of real evidence is arithmetic: FS publishes the adapter count per
panel, and the face-on MTP panel puts its outermost centres 88.8 mm apart, so a
pitch follows from a count rather than from a guess. That is recorded as the
derivation it is, not dressed up as a measurement.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: A sweep over the connector family

**Files:**
- Create: `spec/tests/test_connector_sweep.py`

**Interfaces:**
- Consumes: every component built in Tasks 4-6

- [ ] **Step 1: Write the test**

Create `spec/tests/test_connector_sweep.py`:

```python
"""Every fibre connector in the library states a capacity and its confidence.

Plan 1's optical rules read `optical.positions` off whatever a module composes,
and a connector missing it silently drops out of every coverage check - L80
iterates the parts it can find capacities for, so an absent capacity is not an
error, it is an omission that makes the rule quieter. This catches that.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library" / "components"

FIBRE_CONNECTORS = [
    "common/lc-duplex-adapter/v3", "common/mpo-adapter/v1",
    "common/sc-duplex-adapter/v1", "common/st-simplex-adapter/v1",
    "common/fc-simplex-adapter/v1", "common/lsh-simplex-adapter/v1",
    "common/mdc-adapter/v1",
]


def load(rel):
    p = LIB / rel / "contract.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def test_every_fibre_connector_declares_its_capacity():
    missing = []
    for rel in FIBRE_CONNECTORS:
        c = load(rel)
        if c is None:
            missing.append(f"{rel}: not built")
        elif not (c.get("optical") or {}).get("positions"):
            missing.append(f"{rel}: no optical.positions")
    assert not missing, (
        "a connector with no declared capacity drops out of every optical "
        "coverage check without erroring:\n  " + "\n  ".join(missing))


def test_the_sweep_covers_what_the_library_actually_has():
    """Guard against this list going stale while the library grows.

    Any component whose attrs name a fibre connector belongs in the list above.
    A new one that is not listed is not swept, and the sweep passes anyway.
    """
    found = []
    for f in sorted(LIB.rglob("contract.yaml")):
        d = yaml.safe_load(f.read_text()) or {}
        if (d.get("attrs") or {}).get("media") != "fiber":
            continue
        if not (d.get("optical") or {}).get("positions"):
            continue
        found.append("/".join(f.parts[-4:-1]))
    unlisted = sorted(set(found) - set(FIBRE_CONNECTORS))
    assert not unlisted, (
        "these declare a fibre capacity and are not in FIBRE_CONNECTORS, so "
        f"nothing above sweeps them: {unlisted}")
```

- [ ] **Step 2: Run the test**

Run: `python3 -m pytest spec/tests/test_connector_sweep.py -q`
Expected: PASS (2 passed)

- [ ] **Step 3: Prove it can fail**

Temporarily delete the `optical:` block from
`library/components/common/mpo-adapter/v1/contract.yaml`, run the test, and
confirm it fails with `common/mpo-adapter/v1: no optical.positions`. Restore with
`git checkout -- library/components/common/mpo-adapter/v1/contract.yaml` and
confirm it passes again. Paste both outputs into your report.

- [ ] **Step 4: Run the full suite and commit**

```bash
python3 -m pytest spec/tests -q -p no:randomly
git add spec/tests/test_connector_sweep.py
git commit -m "test: every fibre connector declares a capacity, and the sweep is not stale

A connector missing optical.positions does not error - L80 iterates the parts it
can find capacities for, so an absent capacity makes the rule quieter rather
than louder. That is the failure this catches.

The second test guards the guard: any component whose attrs say media: fiber and
which declares a capacity must be in the swept list, so a new connector cannot
be added outside the sweep while the sweep keeps passing.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-review

**Spec coverage.** Section E item 2's connector table has eight rows; Tasks 4, 5
and 6 build all eight. LC already existed and Task 1 reconciles it. The `optical.
positions` requirement from section A is carried by every connector built.

**Beyond the spec, and deliberately:** Tasks 1 and 2 are not in the spec's item 2.
They are here because building seven more connectors on top of an unreconciled
contradiction would multiply it, and because L81 is the rule that makes the
reconciliation stick. If that reads as scope creep, the argument against it is
that the next connector's pitch is unchecked without it.

**Not in this plan, and where each goes:** the FS adapter panels themselves
(plan 5 — they are modules, not connectors); the key-direction distinction FS
sells as separate SKUs (`Up-Down Type A` vs `Up-Up Type B`), recorded as a gap on
`mpo-adapter` and properly a plan 5 concern since it is a property of the panel;
`faces:` and the DCIM export (plans 3 and 4).

**Placeholder scan.** Task 5 step 3 and Task 6 step 3 contain `<angle brackets>`
for values the implementer measures in the step immediately before. That is a
measurement procedure with its output named, not a placeholder — the method, the
image, the validation threshold and the failure action are all specified. Task 5
step 4 and Task 6 step 4 describe contracts "in the shape of `mpo-adapter`"
rather than repeating 60 lines six times; the shape is fully written out in Task
4 and the per-part differences are enumerated.

**Type consistency.** `plate`, `validate`, `openings` are defined in Task 3 and
used under those names in Tasks 4 and 5. `contract(ref)` is defined in Task 4's
test file and reused by Tasks 5 and 6. `lint_component_composed_pitch` is defined
in Task 2 and referenced nowhere else. Test totals are cumulative: 1393 baseline
→ 1394, 1398, 1400, 1403, 1405, 1415, 1417.

**One thing checked while writing this plan, and worth knowing.** `STANDARDS` in
`lint.py` is empty after a plain import — it is filled in `main()`. The first
draft of Task 2 would therefore have shipped four tests that all passed against a
rule doing nothing, which is the exact defect class this repo treats as a test
failure. Task 2's test file now loads the registry itself and carries a guard
test for it; Task 2 step 4 explains why.

**Test counts assume the estimated five land as written.** Task 6 adds ten
parametrised cases over five components; if a connector is dropped or split the
totals shift, and the totals are guides.
