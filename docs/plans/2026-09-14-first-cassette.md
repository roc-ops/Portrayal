# The First FS Cassette Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build FHD-1MTP6LCDOS2A — six front LC duplex adapters, one rear MTP-12, twelve fibres between them — and the face-qualified endpoint syntax the two faces need.

**Architecture:** An optical endpoint gains an optional face prefix, so `rear:mtp.1` names a part on the module's rear face while `lc1.1` still means a part on its own. Unprefixed keeps meaning exactly what it means today, so the nine PPMs and every contract already written are untouched. The cassette is then an ordinary component with `faces.rear` pointing at its back, and its twelve paths run between the two.

**Tech Stack:** Python 3, JSON Schema (draft 2020-12), PyYAML, SVG, pytest.

**Spec:** `docs/optical-paths-design.md` — section A (the optical model) and section B (faces). This is plan 4 of 6.

## Global Constraints

- `working/` is NEVER committed and never published. Reference imagery stays there; transcribe facts into contracts.
- Every dimension not measured is `confidence: estimated` (or `borrowed`, naming the part it came from) with provenance saying what it was derived from. **Never launder an estimate into a measurement.**
- Version bumps go in BEFORE `devicelock --update`, never after.
- **Run every gate in the FOREGROUND**, using the Bash tool's own `timeout` parameter at `600000`. Do not use `run_in_background`, the Monitor tool, TaskOutput, or a shell-level `timeout` — all three have lost a task on this project. The suite takes about 4 minutes. The chain, in order:
  1. `python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library | tail -3`
  2. `./publish.sh --no-images`
  3. `python3 spec/tools/portrayal/devicelock.py --library library`
  4. `python3 -m pytest spec/tests -q 2>&1 | tail -5`
- Lint baseline: `LINT: ok (662 files, 1291 warnings in 22 rules)`. **The trailing number counts rules that PRODUCED a warning, not rules that exist** (`summary_line`, lint.py) — a new rule finding nothing does not move it. The file count rises by one per new contract. If the WARNING count moves, find out what started warning before continuing.
- **Adding or changing a lint rule means regenerating its docs page**: `python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md`. `test_docs_page_matches_the_generator` compares it byte for byte. Commit the page with the rule.
- Test baseline: `1465 passed, 1 skipped`. Expected totals in tasks are a GUIDE — the binding check is that nothing FAILED and the total only went up.
- Commit messages end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. No backticks in the message text: write it to a file and `git commit -F`.
- Do not dispatch subagents from inside a task.

---

## What is already measured, and what is not

Everything below was measured by me before this plan was written, with
`spec/tools/intake/panel_measure.py`, which scales on the known 108.97 mm FHD
faceplate width and **refuses** unless that scale reproduces the 35.05 mm height.
Numbers here are transcribed into contracts; the imagery stays in `working/`.

**The front face of SKU 57016 — MEASURED, scale validated at 1.02%.**

```
faceplate           108.97 x 35.05 mm   (and FS's own dimension line on
                                         57016.B.jpg reads 4.29in x 1.38in,
                                         which is 108.97 x 35.05 exactly)
six adapter bodies  9.28 wide x 13.75 tall, BOTH spread 0.00 across all six
centres             20.45  33.34  46.23  59.30  72.19  85.08
pitches             12.89  12.89  13.06  12.89  12.89 -> mean 12.924, spread 0.17
gaps between bodies 3.61 mm (they do NOT abut)
vertical placement  top edge 10.66, bottom 24.41, spread 0.00 on both
```

The vertical figures are worth a sentence. A luminance profile down the centre
of each adapter separates it cleanly from the plate - bare plate reads 44-46,
the adapter 100-247 - and all six give the same top edge and the same bottom
edge to the pixel. Their midpoint lands at **17.53**, and half of 35.05 is
17.525: the adapters are centred on the face, and that is a measurement rather
than the assumption it would otherwise have been.

That mean of 12.924 is the tightest measurement in the whole FS corpus, and it
**settles the open question at `docs/optical-paths-design.md:287`** — "FS's 12.90
adapter pitch vs our 13.2". They were never one part measured two ways:
`common/lc-duplex-adapter@3` is 13.2 mm wide with its two bores SIDE BY SIDE,
and FS's cassette uses a narrower adapter with its two ports STACKED. Task 2
builds the one FS actually uses.

**The stacking is from the render, not inferred.** A 6x crop of the join between
two adapters on 57016.main.jpg shows discrete blue bodies with black plate
between them, each carrying a single white dust cap over two ports arranged one
above the other. The faceplate numbering agrees: 2 top-left and 1 bottom-left,
12 top-right and 11 bottom-right — evens along the top, odds along the bottom.

**The rear face — NOT MEASURED, and it cannot be from what we hold.** `57016.D.jpg`
is the only rear view and it is a top-rear three-quarter: the lid recedes and the
rear face is foreshortened. `panel_measure` refuses it at **3.77% off** the second
axis. It also cannot be scaled on the faceplate, because **the faceplate overhangs
the body** — the rear face IS the body, and the body is narrower by an amount
nobody has measured. What the image does give, which needs no scale: one MTP
adapter, a `1-12` legend to its left, a `Type A` label, a `MALE` warranty seal,
and two captive thumb-screws.

**The depth — MEASURED from FS's own dimension line.** `4.34in` = **110.24 mm**.

**The model name — from FS's own catalogue**, not invented:
`working/images/fhd-fiber-cabling-system-guide/doc.md` Table 3 lists
`FHD-1MTP6LCDOS2A`, OS2, 12F. SKU 57016 is "FHD MTP-12 (Male) to LC Cassette,
OS2, 12 Fibers, Type A". Same part.

**THE POLARITY MAPPING IS THE ONE THING NOT YET SOURCED.** The cabling guide
names polarity TYPES (A / AF / U) in tables and explains Method A and Method B
links in prose, but I did not find a per-fibre diagram for a Type A cassette in
the 34 converted figures. Task 4 handles this explicitly and must not guess
quietly — see that task.

---

## File Structure

| file | responsibility |
|---|---|
| `spec/tools/portrayal/optical.py` | **modify.** `split_endpoint` returns a face as well; `capacities` walks the module's faces; `part_key` joins them back. The one place endpoint spelling is decided. |
| `spec/schemas/component.schema.json` | **modify.** The `optical-endpoint` pattern accepts an optional `<face>:` prefix. |
| `spec/tools/portrayal/lint.py` | **modify.** L78 and L80 unpack the new tuple; L81 stops treating a stacked pair as a rotated column; **L84** is new — a face-qualified endpoint names a face this part actually declares. |
| `library/components/common/lc-duplex-v-adapter/v1/` | **new.** The vertically-stacked LC duplex adapter FS uses. Contract + skin. |
| `library/components/fs/fhd-1mtp6lcd-os2-a/v1/` | **new.** The cassette: front face, six adapters, twelve paths, `faces.rear`. |
| `library/components/fs/fhd-1mtp6lcd-rear/v1/` | **new.** The rear face: the body, one MTP-12, the legends. |
| `spec/schemas/standards.yaml` | **modify.** A registry entry for the FS cassette adapter pitch — the measured 12.92. |
| `spec/tests/test_optical_faces.py` | **new.** The endpoint syntax, the resolution across faces, and L84. |
| `spec/tests/test_first_cassette.py` | **new.** The cassette as built: geometry, capacity, and that all twelve fibres are routed. |

---

### Task 1: Face-qualified endpoints

**Files:**
- Modify: `spec/tools/portrayal/optical.py`
- Modify: `spec/schemas/component.schema.json`
- Modify: `spec/tools/portrayal/lint.py` (L78 and L80 call sites)
- Test: `spec/tests/test_optical_faces.py` (create)

**Interfaces:**
- Produces: `split_endpoint(ep)` -> `(face, part, pos)`. `face` is `None` for an unqualified endpoint. **This changes the return arity from 2 to 3** — every caller in `lint.py` must be updated in this task.
- Produces: `part_key(face, part)` -> `str`. `"rear", "mtp"` -> `"rear:mtp"`; `None, "lc1"` -> `"lc1"`. This is the spelling `capacities()` keys its result by, so a caller can look an endpoint up without reassembling it by hand.
- Produces: `capacities(contract, load_ref)` now also walks every component named in `contract["faces"]`, keying those parts `"<face>:<id>"`.
- Produces: L81 falls back to measuring a pitch down `at`'s y only when the placements are ROTATED, not merely when they share an x. Task 2 depends on this — see Step 6.

- [ ] **Step 1: Write the failing tests**

Create `spec/tests/test_optical_faces.py`:

```python
"""An optical path that reaches a part on another face of the same module.

A cassette's fibres run from six front LC adapters to one rear MTP. The MTP is a
part of the REAR FACE component, not of the cassette's own `parts:` - so an
endpoint has to be able to say which face it means. `rear:mtp.1` does;
unprefixed still means this face, which is why the nine PPMs and everything else
already written need no change.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import optical as O  # noqa: E402


def test_an_unqualified_endpoint_has_no_face():
    assert O.split_endpoint("lc1.2") == (None, "lc1", 2)


def test_a_qualified_endpoint_carries_its_face():
    assert O.split_endpoint("rear:mtp.12") == ("rear", "mtp", 12)


def test_a_part_key_is_how_capacities_spells_it():
    assert O.part_key(None, "lc1") == "lc1"
    assert O.part_key("rear", "mtp") == "rear:mtp"


def test_an_endpoint_round_trips_through_its_key():
    face, part, pos = O.split_endpoint("rear:mtp.7")
    assert O.part_key(face, part) == "rear:mtp"


@pytest.mark.parametrize("bad", [
    "mtp", "mtp.0", "rear:mtp", ":mtp.1", "rear:.1", "REAR:mtp.1",
    "rear:mtp.1.2", "a:b:c.1", "", None,
])
def test_what_is_not_an_endpoint(bad):
    with pytest.raises(ValueError):
        O.split_endpoint(bad)


def test_capacities_reaches_a_part_on_another_face():
    """The whole point: a cassette's rear MTP must be findable from the front."""
    front = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@1"}],
             "faces": {"rear": {"ref": "fs/x-rear@1"}}}
    rear = {"parts": [{"id": "mtp", "ref": "common/mpo-adapter@1"}]}
    known = {
        "common/lc-duplex-v-adapter@1": {"optical": {"positions": 2}},
        "common/mpo-adapter@1": {"optical": {"positions": 12}},
        "fs/x-rear@1": rear,
    }
    caps = O.capacities(front, known.get)
    assert caps == {"lc1": 2, "rear:mtp": 12}


def test_a_face_that_names_nothing_resolvable_contributes_nothing():
    """A broken `faces.rear` is L83's error to report, not a crash here.

    `optical.py` answers questions and never validates - that split is what lets
    the exporter reuse it without inheriting lint's opinions - so a face whose
    component will not load simply adds no capacities.
    """
    front = {"parts": [], "faces": {"rear": {"ref": "fs/nope@1"}}}
    assert O.capacities(front, lambda ref: None) == {}
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python3 -m pytest spec/tests/test_optical_faces.py -q`
Expected: FAIL — `split_endpoint` returns a 2-tuple and `part_key` does not exist.

- [ ] **Step 3: Change `optical.py`**

Replace the `ENDPOINT` constant and `split_endpoint`:

```python
# The optional `<face>:` prefix is what lets one module's paths reach a part
# drawn on another of its faces - a cassette's rear MTP lives in the rear face
# component's `parts:`, not in the cassette's own. Unprefixed means THIS face
# and is the spelling every contract written before faces existed uses, so the
# group is optional rather than the pattern being replaced.
ENDPOINT = re.compile(r"^(?:([a-z0-9-]+):)?([a-z0-9-]+)\.([1-9][0-9]*)$")


def split_endpoint(ep):
    """`rear:mtp.3` -> `('rear', 'mtp', 3)`; `lc1.1` -> `(None, 'lc1', 1)`.

    Raises ValueError on anything else. The face comes back separately rather
    than glued to the part id because the DCIM export's whole job is to say
    which side a port is on, and deriving that from a string later is how it
    gets derived differently in two places.
    """
    m = ENDPOINT.match(ep or "")
    if not m:
        raise ValueError(f"not an optical endpoint: {ep!r}")
    return m.group(1), m.group(2), int(m.group(3))


def part_key(face, part):
    """How `capacities` spells a part, so a caller need not reassemble it."""
    return f"{face}:{part}" if face else str(part)
```

Then replace `capacities` with:

```python
def capacities(contract, load_ref):
    """Part key -> fibre positions, across this module and all of its faces.

    A part with no `optical.positions` is not a connector - a lamp, a latch, a
    silkscreen - and is absent from the result rather than present with zero.
    The difference matters: absent means "not a connector", zero would mean "a
    connector with no fibres", and only one of those is a thing.

    Faces are walked ONE LEVEL. A face is a drawing of this part from another
    direction, so its parts are this module's parts seen from there; a face of a
    face is not a thing, and L83 already rejects one.
    """
    out = {}

    def collect(doc, face):
        for part in doc.get("parts") or []:
            if not isinstance(part, dict) or not part.get("id"):
                continue
            ref = load_ref(part["ref"]) or {}
            n = (ref.get("optical") or {}).get("positions")
            if n:
                out[part_key(face, part["id"])] = int(n)

    collect(contract, None)
    for face, spec in (contract.get("faces") or {}).items():
        doc = load_ref((spec or {}).get("ref")) or {}
        collect(doc, face)
    return out
```

- [ ] **Step 4: Widen the schema pattern**

In `spec/schemas/component.schema.json`, `$defs.optical-endpoint`, replace the
pattern and description:

```json
    "optical-endpoint": {
      "type": "string",
      "pattern": "^(?:[a-z0-9-]+:)?[a-z0-9-]+\\.[1-9][0-9]*$",
      "description": "`<part-id>.<n>`, or `<face>:<part-id>.<n>` - a composed part's id and a 1-based fibre position within it. The optional face prefix names a key of this component's `faces:`, so a module's paths can reach a part drawn on its rear: a cassette's rear MTP is a part of the rear face component, not of the cassette's own `parts:`. Unprefixed means this face."
    },
```

- [ ] **Step 5: Update the three call sites in `lint.py`**

`split_endpoint` now returns three values. Find every call — there are three,
in `lint_component_optical_endpoints` (L78) and `lint_component_optical_coverage`
(L80) — with:

```bash
grep -n 'split_endpoint' spec/tools/portrayal/lint.py
```

Each currently reads `part, pos = optical.split_endpoint(ep)`. Change each to:

```python
                face, part, pos = optical.split_endpoint(ep)
```

and wherever the unpacked `part` is then used as a key into `caps`, use
`optical.part_key(face, part)` instead. Read each site and make the smallest
change that keeps its existing message text accurate — if a message names the
part, it should now name the key, so `rear:mtp` appears in the error rather than
a bare `mtp` that the reader cannot find in `parts:`.

- [ ] **Step 6: Teach L81 the difference between a rotated column and a stacked pair**

**This is a prerequisite for Task 2 and the plan will not gate without it.**
`std/lc-bore@3` declares `conforms: lc-duplex-receptacle`, whose pitch is 6.25
with `pitch-kind: target`. Task 2's adapter composes two of those bores stacked,
6.75 apart. L81 would compare 6.75 against 6.25 and error.

It errors because of this, in `lint_component_composed_pitch`:

```python
        if len({x for x, _y in pts}) == 1:
            vals = sorted(y for _x, y in pts)
```

The comment above it says the fallback is for "a cage rotated 90 degrees", whose
whole column shares one x. That is a real case and it must keep working. But a
STACKED DUPLEX SHELL also shares one x and is not a rotation: a rotated part is
the same part turned, so its interface pitch is preserved, while a stacked pair
is genuinely a different distance apart. The proof is arithmetic — a
`std/lc-bore@3` is 6.3 mm tall, so two of them 6.25 apart would OVERLAP. 6.25
cannot describe a stacked pair, which means the standard's pitch does not govern
this arrangement at all.

**The fix is to gate the fallback on the thing that actually distinguishes them.**
A rotated column's placements carry `rotate: 90` — verified on all three of the
rotated Juniper columns (`mic-3d-4xge-xfp-v`, `mic6-100g-cfp2`, `mic6-100g-cxp`).
A stacked pair carries no rotation. So:

```python
        # A cage rotated 90 degrees runs its array down `at`'s y, not its x - a
        # whole rotated column shares one x, and reading x alone would see every
        # gap as zero and call that a matched pitch.
        #
        # SHARING AN X IS NOT ENOUGH TO MEAN ROTATED, though, and that is what
        # this used to test. A duplex shell with its two ports STACKED shares one
        # x too, and it is not the same part turned: a rotated part keeps its
        # interface pitch, where a stacked pair is genuinely further apart. The
        # arithmetic settles it - a std/lc-bore@3 is 6.3 tall, so two of them at
        # lc-duplex-receptacle's 6.25 would overlap, which means 6.25 never
        # described a stacked pair in the first place. Reading the y of one would
        # compare a vertical spacing against a horizontal standard and call the
        # difference a violation.
        #
        # So fall back to y only when the placements SAY they are rotated.
        # Anything else - including a genuinely irregular x layout - is left to
        # the x path and its own irregular-spacing exit below.
        if len({x for x, _y in pts}) == 1 and rotated:
            vals = sorted(y for _x, y in pts)
```

`pts` currently collects `(x, y)` pairs. Widen it to carry each placement's
rotation so `rotated` can be computed — read the `by_ref` loop above and make
the smallest change that does it, keeping the existing `float()` conversions.
`rotated` is true when EVERY placement of that ref is rotated; a mixed group is
not a rotated column and belongs on the x path.

**Verified before this plan was written: the change is a no-op on today's
library.** Both readings produce zero L81 hits across all 662 contracts, because
the three rotated columns all carry `rotate: 90` and all three already carry a
`provenance.pitch-note` besides. So this widens nothing and silences nothing; it
stops a rule firing on a part that does not exist yet.

Append these to **`spec/tests/test_pitch_lint.py`**, where L81's existing tests
live:

```python
def test_a_stacked_pair_is_not_a_rotated_column():
    """Sharing an x does not make two parts a rotated column.

    A std/lc-bore@3 is 6.3 tall, so a stacked pair cannot sit at
    lc-duplex-receptacle's 6.25 without overlapping - which means that pitch
    never described this arrangement. Before this, L81 read the y of any
    single-x group and reported the difference as a violation.
    """
    doc = {"parts": [
        {"id": "tx", "ref": "std/lc-bore@3", "at": [2.29, 0.35]},
        {"id": "rx", "ref": "std/lc-bore@3", "at": [2.29, 7.10]},
    ]}
    assert run(doc) == []


def test_a_rotated_column_is_still_measured_down_its_y():
    """The case the fallback exists for, and it must keep working."""
    doc = {"parts": [
        {"id": "a", "ref": "std/lc-bore@3", "at": [0.0, 0.0], "rotate": 90},
        {"id": "b", "ref": "std/lc-bore@3", "at": [0.0, 9.0], "rotate": 90},
    ]}
    got = run(doc)
    assert len(got) == 1, got
    assert "9.0" in got[0] or "9.00" in got[0]
```

Match the helper name and import style that file already uses — it will have a
`run`-style wrapper around `lint_component_composed_pitch` and will already
populate `L.STANDARDS`, which is empty after a plain import.

- [ ] **Step 7: Run the tests and the gate chain**

Run the full chain from Global Constraints.
Expected: lint `LINT: ok (662 files, 1291 warnings in 22 rules)` unchanged — no
contract uses a face-qualified endpoint yet, the widened pattern rejects nothing
that was previously valid, and the L81 change is a no-op on every contract in the
library. devicelock 0. Roughly `1475 passed, 1 skipped`.

- [ ] **Step 8: Commit**

---

### Task 2: The LC duplex adapter FS actually uses

**Files:**
- Modify: `spec/schemas/standards.yaml`
- Create: `library/components/common/lc-duplex-v-adapter/v1/contract.yaml`, `.../skins/default.svg`
- Test: `spec/tests/test_first_cassette.py` (create)

**Interfaces:**
- Produces: `common/lc-duplex-v-adapter@1`, `optical.positions: 2`, `size` 9.28 wide.

**Why a new component and not a variant of `common/lc-duplex-adapter@3`.** That
part is 13.2 mm wide with its two bores side by side at a 6.25 mm pitch — the
IEC 61754-20 duplex receptacle. FS's cassette uses a narrower shell with the two
ports STACKED, one above the other, which is a different footprint and a
different drawing. A different shape is a different component; that is the rule
this library already runs on.

- [ ] **Step 1: Write the failing test**

Create `spec/tests/test_first_cassette.py`:

```python
"""FHD-1MTP6LCDOS2A, and the adapter it is built from.

Measured off FS's own face-on render of SKU 57016, scaled on the 108.97 mm FHD
faceplate and validated against the 35.05 mm height to 1.02%. What makes these
assertions worth making is that they are a measurement and not a guess.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library" / "components"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import optical as O  # noqa: E402


def contract(rel):
    p = LIB / rel / "contract.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def test_the_stacked_lc_adapter_presents_two_fibres():
    c = contract("common/lc-duplex-v-adapter/v1")
    assert c is not None, "common/lc-duplex-v-adapter@1 not built"
    assert (c.get("optical") or {}).get("positions") == 2


def test_the_stacked_lc_adapter_is_the_measured_width():
    """9.28 across all six adapters on 57016, spread 0.00."""
    c = contract("common/lc-duplex-v-adapter/v1")
    assert c["size"]["w"] == 9.28


def test_the_stacked_adapter_is_the_measured_height():
    """13.75 across all six, spread 0.00 - top edge 10.66, bottom 24.41."""
    c = contract("common/lc-duplex-v-adapter/v1")
    assert c["size"]["h"] == 13.75


def test_the_stacked_adapter_says_which_of_its_dimensions_were_measured():
    c = contract("common/lc-duplex-v-adapter/v1")
    sc = c.get("size-confidence") or {}
    assert sc.get("w") == "photo-measured", \
        "the width IS measured - six bodies, spread 0.00 - and must say so"
    assert sc.get("h") == "photo-measured", \
        "so is the height - same six bodies, same spread"
    assert sc.get("d") == "estimated", \
        "the DEPTH is the one nobody can see in a face-on render"


def test_two_stacked_bores_actually_fit_in_the_body():
    """A 6.3-tall bore twice over needs 12.6, and the body is 13.75.

    An earlier draft of this plan sized the body at 12.0, borrowed from the SC
    shell - which would have put 12.6 mm of bore into 12.0 mm of adapter and
    drawn two apertures overlapping. Measuring the height instead of borrowing
    it is what caught that, so this is the assertion that keeps it caught.
    """
    c = contract("common/lc-duplex-v-adapter/v1")
    bores = [p for p in (c.get("parts") or []) if "lc-bore" in str(p.get("ref"))]
    ys = sorted(float(p["at"][1]) for p in bores)
    assert ys[1] >= ys[0] + 6.3, f"the bores overlap: {ys}"
    assert ys[1] + 6.3 <= c["size"]["h"], \
        f"the lower bore hangs out of the body: {ys[1]} + 6.3 > {c['size']['h']}"


def test_its_two_ports_are_stacked_not_side_by_side():
    """THE REASON THIS COMPONENT EXISTS.

    `common/lc-duplex-adapter@3` puts its bores side by side. A 6x crop of
    57016.main.jpg shows one dust cap over two ports one ABOVE the other, and
    the faceplate numbers agree - evens along the top, odds along the bottom.
    If a later edit lays these out abreast, this is what says so.
    """
    c = contract("common/lc-duplex-v-adapter/v1")
    bores = [p for p in (c.get("parts") or []) if "lc-bore" in str(p.get("ref"))]
    assert len(bores) == 2, [p.get("ref") for p in c.get("parts") or []]
    xs = {round(float(p["at"][0]), 3) for p in bores}
    ys = {round(float(p["at"][1]), 3) for p in bores}
    assert len(xs) == 1, f"the two bores are at different x - abreast, not stacked: {xs}"
    assert len(ys) == 2, f"the two bores share a y - abreast, not stacked: {ys}"


def test_the_fs_cassette_pitch_is_in_the_registry_as_measured():
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())
    s = std["standards"]["fhd-lc-cassette"]
    assert s["pitch"] == 12.92
    assert s["pitch-confidence"] == "measured"
    assert "57016" in s["registry"], \
        "the registry entry must name the render the pitch came from"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_first_cassette.py -q`
Expected: FAIL — `common/lc-duplex-v-adapter@1 not built`.

- [ ] **Step 3: Add the standards entry**

Append to `spec/schemas/standards.yaml`, in the same shape as the neighbouring
entries. **No `w`/`h`** — the file header defines those as the faceplate
aperture, and no cutout dimension is held for this part; putting a body size in
those slots is the category error `mpo-adapter` was corrected for.

```yaml
  fhd-lc-cassette:
    registry: >-
      MEASURED, NOT READ FROM A STANDARD. No published figure governs how FS
      spaces the adapters on an FHD cassette face. The pitch comes from FS's own
      face-on render of SKU 57016 (FHD-1MTP6LCDOS2A), scaled on the 108.97 mm
      FHD module width and validated against the 35.05 mm height to 1.02%: six
      bodies 9.28 wide, centres 20.45 33.34 46.23 59.30 72.19 85.08, pitches
      12.89 12.89 13.06 12.89 12.89.
    pitch: 12.92
    pitch-confidence: measured
    pitch-kind: floor
    pitch-kind-note: >-
      A FLOOR, not a target. The bodies do NOT abut - each is 9.28 wide on a
      12.92 pitch, leaving a real 3.61 mm gap visible in the render - so 12.92
      is not a physical minimum the way an abutting pitch would be. It is
      recorded as a floor because nothing in any standard fixes an FHD cassette
      pitch, so a layout WIDER than the one vendor arrangement measured here is
      unremarkable while a narrower one is worth a question.
    notes: >-
      THIS IS NOT THE IEC 61754-20 LC DUPLEX PITCH and must not be confused with
      it. `lc-duplex-receptacle` records 6.25 mm, which is the spacing of the two
      BORES INSIDE one duplex adapter; this is the spacing BETWEEN adapters on a
      cassette face. The parts are different too: FS's cassette adapter is 9.28
      wide with its ports stacked vertically, where common/lc-duplex-adapter@3 is
      13.2 wide with its bores side by side. This entry closes the open question
      at docs/optical-paths-design.md:287, which read 12.90 against our 13.2 as
      though one part had been measured two ways.
```

- [ ] **Step 4: Create the component**

`library/components/common/lc-duplex-v-adapter/v1/contract.yaml`:

```yaml
format: 1
kind: component
name: lc-duplex-v-adapter
version: 1.0.0
class: port
description: >-
  LC duplex panel adapter with its two ports STACKED VERTICALLY - the shell FS
  fits to FHD cassettes and adapter panels. Not the same part as
  common/lc-duplex-adapter@3, which is wider and puts its bores side by side.
size: {w: 9.28, h: 13.75, d: 12.0}
size-confidence: {w: photo-measured, h: photo-measured, d: estimated}
size-notes: >-
  WIDTH AND HEIGHT ARE BOTH MEASURED, each with a spread of 0.00 across all six
  adapters on FS's face-on render of SKU 57016 - scaled on the 108.97 mm FHD
  faceplate and validated against its 35.05 mm height to 1.02%. The width is
  9.28. The height comes from a luminance profile down the centre of each
  adapter, which separates it cleanly from the plate (bare plate 44-46, adapter
  100-247): top edge 10.66, bottom edge 24.41, height 13.75, identical to the
  pixel on all six. The DEPTH is the one dimension a face-on render cannot give;
  12.0 is borrowed from common/sc-duplex-adapter@1, whose shell is the same
  family and the same width, and a caliper on one real adapter settles it.
attrs: {media: fiber}
optical:
  positions: 2
parts:
  - {id: tx, ref: std/lc-bore@3, at: [2.29, 0.35]}
  - {id: rx, ref: std/lc-bore@3, at: [2.29, 7.10]}
connection-points:
  optical:
    at: [4.64, 6.875]
    direction: front
provenance:
  size: >-
    see size-notes. Width measured, height and depth borrowed.
  parts: >-
    THE TWO BORES ARE STACKED, WHICH IS THE WHOLE POINT OF THIS PART. A 6x crop
    of the join between two adapters on 57016.main.jpg shows one white dust cap
    over two ports arranged one above the other, and the faceplate numbering
    agrees - 2 above 1 at the left end, 12 above 11 at the right. Their x is
    shared and their y is not, which is the opposite of
    common/lc-duplex-adapter@3. WHERE they sit inside the body is ESTIMATED and
    the body itself is not: a std/lc-bore@3 is 4.7 x 6.3, so two of them need
    12.6 of the measured 13.75, leaving 1.15 to share between three margins.
    0.35 top, 0.45 between and 0.35 bottom is that share spent evenly, and
    x = (9.28 - 4.7) / 2 centres them. The dust caps hide the bores themselves,
    so a caliper or a drawing settles it.
  face-detail-gap: >-
    No dimensioned drawing of this adapter has been obtained. The 9.28 x 13.75
    outline is measured; the depth and the bore positions inside it are not.
skins: [default]
```

The skin at `library/components/common/lc-duplex-v-adapter/v1/skins/default.svg`
follows `common/sc-duplex-adapter@1`'s — read that file and match its structure,
sized `9.28 x 13.75`, with its bezel rect and its two bore cutouts stacked at the
`at` positions above. Its header comment must say the outline is measured and the
bore positions inside it are not, and name SKU 57016.

- [ ] **Step 5: Run the tests and the gate chain**

Expected: lint `LINT: ok (663 files, 1291 warnings in 22 rules)` — one more file,
warnings unmoved. devicelock 0. Roughly `1478 passed, 1 skipped`.

- [ ] **Step 6: Commit**

---

### Task 3: The cassette's front face

**Files:**
- Create: `library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml`, `.../skins/default.svg`
- Test: `spec/tests/test_first_cassette.py` (append)

**Interfaces:**
- Consumes: `common/lc-duplex-v-adapter@1` from Task 2.
- Produces: `fs/fhd-1mtp6lcd-os2-a@1` with six parts `lc1`..`lc6`. Task 4 adds its `faces.rear` and its `optical.paths`.

**The six `at.x` values.** Each adapter is 9.28 wide and its measured CENTRE is
listed below, so its left edge is `centre - 4.64`:

| id | centre | at.x |
|---|---:|---:|
| lc1 | 20.45 | 15.81 |
| lc2 | 33.34 | 28.70 |
| lc3 | 46.23 | 41.59 |
| lc4 | 59.30 | 54.66 |
| lc5 | 72.19 | 67.55 |
| lc6 | 85.08 | 80.44 |

Use those `at.x` values verbatim — they are the measurement, not a pitch
multiplied out, which is why lc4 is 13.07 from lc3 rather than 12.92.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_first_cassette.py`:

```python
CASSETTE = "fs/fhd-1mtp6lcd-os2-a/v1"
CENTRES = [20.45, 33.34, 46.23, 59.30, 72.19, 85.08]


def test_the_cassette_is_an_fhd_module():
    c = contract(CASSETTE)
    assert c is not None, "fs/fhd-1mtp6lcd-os2-a@1 not built"
    assert c["size"]["w"] == 108.97 and c["size"]["h"] == 35.05


def test_the_cassette_carries_six_stacked_lc_adapters():
    c = contract(CASSETTE)
    lcs = [p for p in c["parts"] if p["ref"] == "common/lc-duplex-v-adapter@1"]
    assert len(lcs) == 6, [p["ref"] for p in c["parts"]]


def test_the_adapters_sit_on_their_measured_centres():
    """Not a pitch multiplied out - the six centres as measured, each to 0.01.

    lc4 sits 13.07 from lc3 where every other gap is 12.89. That asymmetry is in
    the render, and rounding it away to a tidy 12.92 everywhere would turn a
    measurement into a model of one.
    """
    c = contract(CASSETTE)
    lcs = [p for p in c["parts"] if p["ref"] == "common/lc-duplex-v-adapter@1"]
    got = sorted(round(float(p["at"][0]) + 4.64, 2) for p in lcs)
    assert got == CENTRES


def test_the_adapter_row_is_measured_as_centred_not_drawn_as_centred():
    """10.66 is the measured top edge of all six, not a number chosen to centre.

    That it ALSO centres - 10.66 + 13.75/2 = 17.53 against 35.05/2 = 17.525 - is
    the corroboration, not the source. If a later edit rounds `at.y` to make the
    arithmetic tidier, it has replaced a measurement with a model of one.
    """
    c = contract(CASSETTE)
    lcs = [p for p in c["parts"] if p["ref"] == "common/lc-duplex-v-adapter@1"]
    assert {round(float(p["at"][1]), 2) for p in lcs} == {10.66}


def test_the_cassette_names_the_render_it_was_measured_from():
    c = contract(CASSETTE)
    blob = yaml.safe_dump(c.get("provenance") or {})
    assert "57016" in blob, "provenance must name the SKU it was measured from"
    assert "1.02" in blob, "and the scale check that makes it a measurement"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_first_cassette.py -q`
Expected: FAIL — `fs/fhd-1mtp6lcd-os2-a@1 not built`.

- [ ] **Step 3: Create the contract**

`library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml`. Use the `at.x`
table above for the six parts, `at.y` **10.66** for all six — that is
MEASURED, not chosen: the top edge of every one of the six reads 10.66 with a
spread of 0.00, and 10.66 + 13.75/2 is 17.53 against a face half-height of
17.525, so the adapters really are centred rather than merely looking it.

```yaml
format: 1
kind: component
name: fhd-1mtp6lcd-os2-a
version: 1.0.0
class: module
description: >-
  FS FHD-1MTP6LCDOS2A - MTP-12 (male) to six LC duplex, 12 fibres, OS2, Type A
  polarity. FS SKU 57016.
size: {w: 108.97, h: 35.05, d: 110.24}
size-confidence: {w: photo-measured, h: photo-measured, d: drawing}
size-notes: >-
  The faceplate is MEASURED off FS's face-on render of SKU 57016, scaled on the
  108.97 mm FHD module width and validated against the 35.05 mm height to 1.02%
  - and corroborated independently by FS's own dimension line on 57016.B.jpg,
  which reads 4.29in x 1.38in, exactly 108.97 x 35.05. The 110.24 depth is the
  4.34in on that same dimension line.
attrs: {media: fiber, vendor-sku: '57016'}
body:
  depth: 110.24
parts:
  - {id: lc1, ref: common/lc-duplex-v-adapter@1, at: [15.81, 10.66]}
  - {id: lc2, ref: common/lc-duplex-v-adapter@1, at: [28.70, 10.66]}
  - {id: lc3, ref: common/lc-duplex-v-adapter@1, at: [41.59, 10.66]}
  - {id: lc4, ref: common/lc-duplex-v-adapter@1, at: [54.66, 10.66]}
  - {id: lc5, ref: common/lc-duplex-v-adapter@1, at: [67.55, 10.66]}
  - {id: lc6, ref: common/lc-duplex-v-adapter@1, at: [80.44, 10.66]}
provenance:
  size: >-
    see size-notes.
  parts: >-
    THE SIX CENTRES ARE THE MEASUREMENT, not a pitch multiplied out. Measured on
    57016.main.jpg at 20.45, 33.34, 46.23, 59.30, 72.19 and 85.08, with body
    widths of 9.28 and a spread of 0.00 across the six. Five gaps of 12.89,
    12.89, 13.07, 12.89, 12.89 - mean 12.924, spread 0.17. The one wide gap is in
    the render and is kept rather than averaged away. `at.y` of 10.66 is MEASURED
    too - the top edge of all six, spread 0.00 - and 10.66 + 13.75/2 = 17.53
    against a face half-height of 17.525, so the row really is centred rather
    than drawn to look centred.
  face-detail-gap: >-
    The faceplate legends - the FS logo, the port numbers 1 through 12 - are not
    drawn. The numbering is known from the render (evens along the top, odds
    along the bottom) and is recorded in the optical paths rather than the art.
skins: [default]
```

The skin is a 108.97 x 35.05 faceplate in the style of the other FHD parts: read
`library/components/common/mpo-adapter/v1/skins/default.svg` for the house
treatment of a black FS plate, and give this one its six adapter cutouts at the
`at` positions. Two thumb-knobs at the ends are visible in the render; draw them
or record them in `face-detail-gap`, and say which you did.

- [ ] **Step 4: Run the tests and the gate chain**

Expected: lint `LINT: ok (664 files, 1291 warnings in 22 rules)`. devicelock 0.
Roughly `1482 passed, 1 skipped`.

**L81 will look at this contract** — it composes six instances of one part. That
part declares no `conforms:`, so L81 stays silent. If it speaks, read what it
says before changing anything.

- [ ] **Step 5: Commit**

---

### Task 4: The rear face, and the twelve fibres

**Files:**
- Create: `library/components/fs/fhd-1mtp6lcd-rear/v1/contract.yaml`, `.../skins/default.svg`
- Modify: `library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml` (add `faces.rear` and `optical`)
- Test: `spec/tests/test_first_cassette.py` (append)

**Interfaces:**
- Consumes: `common/mpo-adapter@1` (built in plan 2, `optical.positions: 12`), and face-qualified endpoints from Task 1.
- Produces: `fs/fhd-1mtp6lcd-rear@1`; and the cassette's twelve paths.

**THE POLARITY MAPPING — READ THIS BEFORE WRITING ANY PATH.**

This is the one fact in this plan that is not yet sourced, and it is the fact the
whole component exists to record. Do not guess it quietly.

**Step 1 is to go and look.** The converted cabling guide is at
`working/images/fhd-fiber-cabling-system-guide/` — `doc.md` plus 34 figures as
`fig-*.png`. Table 2 (around line 179) and Table 3 (around line 195) list the
polarity types, and there is an `<!-- image -->` marker immediately after Table 2
where docling dropped a figure it could not caption. Open the figures and look
for a per-fibre diagram showing which MTP position lands on which LC port.
`working/images/modular-cabling-system-portfolio/` is a second place to look.

**If you find it:** transcribe it exactly, name the figure file and the document
in `provenance.optical`, and mark the mapping `measured`.

**If you do not find it:** record the Method A straight-through mapping — MTP
position *n* to fibre *n*, so `rear:mtp.1` to `lc1.1`, `rear:mtp.2` to `lc1.2`,
`rear:mtp.3` to `lc2.1`, and so on in order — and say in `provenance.optical`, in
plain words, that **the mapping is an assumption and not a source**: that FS's
guide names the polarity TYPE but the per-fibre diagram was not found in the
corpus, that this is the standard Type A straight-through arrangement, and that a
Type A cassette's own datasheet or a fibre trace on real hardware settles it.
Mark it `confidence: estimated`. Do not write "Type A" as though naming the type
were the same as sourcing the map.

**Either way, say which happened in your report.**

**The rear face's geometry is ESTIMATED and must say so.** `57016.D.jpg` is a
top-rear three-quarter, not a face-on view: `panel_measure` refuses it at 3.77%
off the second axis. It also cannot be scaled on the faceplate, because the
faceplate overhangs the body — the rear face IS the body. What the image gives
without a scale: one MTP adapter roughly centred, a `1-12` legend to its left, a
`Type A` label, a `MALE` warranty seal, and two captive thumb-screws.

Size the rear face at `{w: 99.0, h: 31.0}` as an ESTIMATE — narrower and shorter
than the 108.97 x 35.05 faceplate by the overhang visible in the render — and say
in `size-notes` that both numbers are proportion, that the render refuses the
scale check at 3.77%, and that a face-on rear photograph settles it.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_first_cassette.py`:

```python
def test_the_cassette_has_a_rear_face():
    c = contract(CASSETTE)
    assert ((c.get("faces") or {}).get("rear") or {}).get("ref") == \
        "fs/fhd-1mtp6lcd-rear@1"


def test_the_rear_face_carries_one_mtp():
    c = contract("fs/fhd-1mtp6lcd-rear/v1")
    assert c is not None, "fs/fhd-1mtp6lcd-rear@1 not built"
    mtps = [p for p in c["parts"] if p["ref"] == "common/mpo-adapter@1"]
    assert len(mtps) == 1, [p["ref"] for p in c["parts"]]


def test_the_rear_face_admits_it_was_never_measured():
    """The one render of this face is a three-quarter; the tool refuses it.

    An estimate that does not say it is one is the failure this whole library is
    built to avoid, and a rear face is where it would be easiest to hide.
    """
    c = contract("fs/fhd-1mtp6lcd-rear/v1")
    sc = c.get("size-confidence") or {}
    assert sc.get("w") == "estimated" and sc.get("h") == "estimated"
    assert "3.77" in (c.get("size-notes") or ""), \
        "say how far off the render actually is, not just that it is off"


def test_all_twelve_fibres_are_routed():
    """Twelve MTP positions, twelve LC ports, and no position left dark."""
    c = contract(CASSETTE)
    paths = (c.get("optical") or {}).get("paths") or []
    assert len(paths) == 12, f"{len(paths)} paths for a 12-fibre cassette"
    rear = {e for p in paths for e, _ in O.endpoints(p) if e.startswith("rear:")}
    assert rear == {f"rear:mtp.{n}" for n in range(1, 13)}
    front = {e for p in paths for e, _ in O.endpoints(p)
             if not e.startswith("rear:")}
    assert front == {f"lc{a}.{b}" for a in range(1, 7) for b in (1, 2)}


def test_the_cassette_says_where_its_polarity_map_came_from():
    """Sourced or assumed, it must say which. Naming the type is not sourcing it."""
    c = contract(CASSETTE)
    note = ((c.get("provenance") or {}).get("optical") or "")
    assert note, "no provenance for the fibre mapping at all"
    assert ("fig-" in note) or ("ASSUMPTION" in note.upper()), \
        "either name the figure it was read from, or say plainly it is assumed"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_first_cassette.py -q`
Expected: FAIL — the cassette has no `faces` and the rear component does not exist.

- [ ] **Step 3: Create the rear face component**

`library/components/fs/fhd-1mtp6lcd-rear/v1/contract.yaml`:

```yaml
format: 1
kind: component
name: fhd-1mtp6lcd-rear
version: 1.0.0
class: module
description: >-
  The back of FS FHD-1MTP6LCDOS2A (SKU 57016): the cassette body seen from
  behind, carrying its single MTP-12 trunk adapter.
size: {w: 99.0, h: 31.0, d: 2.0}
size-confidence: {w: estimated, h: estimated, d: estimated}
size-notes: >-
  NOT MEASURED, AND NOT MEASURABLE FROM WHAT IS HELD. 57016.D.jpg is the only
  rear view and it is a top-rear three-quarter: the lid recedes and the face is
  foreshortened, so panel_measure refuses it at 3.77% off the second axis
  against a face-on figure of under 2%. It also cannot be scaled on the
  faceplate, because the faceplate OVERHANGS the body - the rear face is the
  body, and the body is narrower by an amount nobody has measured. 99.0 x 31.0
  is proportion read off that render against the known 108.97 x 35.05 front. A
  face-on photograph of the back settles it.
attrs: {media: fiber}
parts:
  - {id: mtp, ref: common/mpo-adapter@1, at: [42.6, 10.8]}
provenance:
  size: >-
    see size-notes.
  parts: >-
    ONE MTP-12, roughly centred. Its position is ESTIMATED from the same
    three-quarter render - the adapter reads as sitting on the horizontal centre
    line and slightly below the vertical one, beside a 1-12 legend. `at` places
    a 13.8 x 9.4 mpo-adapter accordingly. Nothing here is a measurement.
  face-detail-gap: >-
    The legends visible on the render are not drawn: a `1-12` port-range label to
    the left of the adapter, a `Type A` polarity label to the right, a `MALE`
    warranty seal above it, and two captive thumb-screws at the outer edges.
    They are recorded here because they identify the part in a photograph and
    somebody will want them later.
skins: [default]
```

Its skin is a 99.0 x 31.0 plate with one aperture at the `at` position. Match the
house treatment of the other FS plates and say in the header comment that every
dimension in the file is an estimate.

- [ ] **Step 4: Wire the front to the rear**

Add to `library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml`:

```yaml
faces:
  rear: {ref: fs/fhd-1mtp6lcd-rear@1}
optical:
  media: os2
  polarity: a
  paths:
    - {from: lc1.1, to: 'rear:mtp.1'}
    - {from: lc1.2, to: 'rear:mtp.2'}
    - {from: lc2.1, to: 'rear:mtp.3'}
    - {from: lc2.2, to: 'rear:mtp.4'}
    - {from: lc3.1, to: 'rear:mtp.5'}
    - {from: lc3.2, to: 'rear:mtp.6'}
    - {from: lc4.1, to: 'rear:mtp.7'}
    - {from: lc4.2, to: 'rear:mtp.8'}
    - {from: lc5.1, to: 'rear:mtp.9'}
    - {from: lc5.2, to: 'rear:mtp.10'}
    - {from: lc6.1, to: 'rear:mtp.11'}
    - {from: lc6.2, to: 'rear:mtp.12'}
```

**and its provenance**, written to whichever of the two cases above actually
happened when you went and looked. Add it under `provenance.optical`.

- [ ] **Step 5: Run the tests and the gate chain**

Expected: lint `LINT: ok (665 files, 1291 warnings in 22 rules)`. L78, L79, L80
and L83 all have something real to check for the first time — L80 in particular
will confirm every one of the twelve MTP positions and all twelve LC ports is
reached. devicelock 0. Roughly `1487 passed, 1 skipped`.

- [ ] **Step 6: Commit**

---

### Task 5: L84 — a face-qualified endpoint names a face that exists

**Files:**
- Modify: `spec/tools/portrayal/lint.py`
- Modify: `docs/lint-rules.md` (regenerate)
- Test: `spec/tests/test_optical_faces.py` (append)

**Interfaces:**
- Consumes: `split_endpoint` from Task 1, `face_ref` from plan 3.
- Produces: lint rule id **L84**.

**Why this rule.** `rear:mtp.1` on a contract that declares no `faces.rear`
resolves to nothing. L78 would report "unknown part", which is true but sends the
reader hunting through `parts:` for an id that was never going to be there. The
real error is one level up, and naming it is the difference between a five-minute
fix and an hour.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_optical_faces.py`:

```python
import lint as L  # noqa: E402

LIB = [str(ROOT / "library")]


def run84(doc, path="t/contract.yaml"):
    L.ERRORS.clear()
    L.lint_component_optical_faces(path, doc)
    return [e for e in L.ERRORS if "[L84]" in e]


def test_a_path_into_a_face_the_part_does_not_have():
    got = run84({"optical": {"paths": [{"from": "lc1.1", "to": "rear:mtp.1"}]}})
    assert len(got) == 1, got
    assert "rear" in got[0] and "declares no" in got[0]


def test_a_path_into_a_face_the_part_does_have_is_quiet():
    assert run84({
        "faces": {"rear": {"ref": "fs/x-rear@1"}},
        "optical": {"paths": [{"from": "lc1.1", "to": "rear:mtp.1"}]},
    }) == []


def test_unqualified_endpoints_are_not_this_rules_business():
    assert run84({"optical": {"paths": [{"from": "a.1", "to": "b.2"}]}}) == []


def test_a_split_reports_every_bad_leg():
    got = run84({"optical": {"paths": [{
        "from": "c.1",
        "to": [{"at": "rear:x.1", "ratio": 50},
               {"at": "top:y.1", "ratio": 50}]}]}})
    assert len(got) == 2, got


def test_the_real_cassette_passes_this_rule():
    """The one contract in the library that uses a qualified endpoint."""
    c = yaml.safe_load(
        (ROOT / "library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml"
         ).read_text())
    assert run84(c) == []
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_optical_faces.py -q`
Expected: FAIL — `module 'lint' has no attribute 'lint_component_optical_faces'`.

- [ ] **Step 3: Write the rule**

In `spec/tools/portrayal/lint.py`, beside the other optical rules:

```python
def lint_component_optical_faces(path, data):
    """L84: a face-qualified endpoint names a face this part declares.

    `rear:mtp.1` on a contract with no `faces.rear` resolves to nothing, and L78
    would report it as an unknown part - true, but it sends the reader hunting
    through `parts:` for an id that was never going to be there. The error is one
    level up, and saying so is the difference between a five-minute fix and an
    hour.
    """
    if not isinstance(data, dict):
        return
    have = set((data.get("faces") or {}).keys())
    for p in ((data.get("optical") or {}).get("paths") or []):
        for ep, _ratio in optical.endpoints(p):
            try:
                face, _part, _pos = optical.split_endpoint(ep)
            except ValueError:
                continue  # L78's error to report, not this one's
            if face and face not in have:
                err(path, "L84", f"path endpoint {ep} names face {face!r}, but "
                                 "this part declares no such face")
```

Add its `RULES` entry beside L83:

```python
    "L84": ("component",  "a face-qualified optical endpoint names a face the part declares", "add the face to `faces:`, or fix the prefix on the endpoint"),
```

and register it in `main()` beside `lint_component_optical_endpoints`, called as
`lint_component_optical_faces(f, d)`.

- [ ] **Step 4: Regenerate the lint rules page**

```bash
python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md
```

- [ ] **Step 5: Run the tests and the gate chain**

Expected: lint `LINT: ok (665 files, 1291 warnings in 22 rules)` — the file count
does not move (no new contract) and neither does the warning count, because the
one contract using qualified endpoints declares the face it names. devicelock 0.
Roughly `1492 passed, 1 skipped`.

- [ ] **Step 6: Commit**

---

## Self-Review

**1. Spec coverage.** Section A asks that a module state `paths` between
`<part-id>.<n>` endpoints and `unused` for any position no path reaches — Tasks 1
and 4, with L80 confirming full coverage on a real 12-fibre part for the first
time. Section B asks that a rear face be another component named through
`faces.rear` and rendered as a component preview — Task 4, and no renderer is
added because plan 3 established that a rear face is an ordinary component.
Section C (the DCIM projection) is **not** in this plan: it is step 4 of the
spec's own order of work and needs this cassette to exist before it has anything
to export.

**2. Placeholder scan.** Two steps deliberately do not print their content: the
two skin files say "read this sibling and match its structure" rather than
reproducing a house SVG treatment I would be transcribing from memory. Both name
the exact file to copy from and the exact size to draw. Everything else is
literal.

**3. Type consistency.** `split_endpoint` returns `(face, part, pos)` in Task 1
and is unpacked that way in Tasks 1 and 5. `part_key(face, part)` is defined in
Task 1 and used in Task 1's call-site updates. `capacities(contract, load_ref)`
keeps its signature. Component refs `common/lc-duplex-v-adapter@1`,
`fs/fhd-1mtp6lcd-os2-a@1` and `fs/fhd-1mtp6lcd-rear@1` are spelled identically in
every task and every test. Rule id L84 is used once.

**4. Known soft spots, named rather than hidden.**

- **The polarity map is not sourced.** Task 4 makes going to look for it Step 1,
  and makes the contract say which of the two cases happened. This is the single
  most likely thing in the plan to be recorded wrongly, because naming a polarity
  type feels like sourcing a mapping and is not.
- **The entire rear face is estimated**, including where the MTP sits on it. The
  render cannot be scaled and the plan says so in three places rather than once.
- **The bore positions inside the adapter are the softest numbers here.** The
  body outline is measured on all six to a spread of 0.00, and where the two
  bores sit inside it is a 1.15 mm margin budget spent evenly, because the dust
  caps hide them. Task 2 asserts they fit rather than asserting where they are.
- **Task 3's skin and Task 4's skin are the least specified work here.** A
  reviewer should look hardest at those two files.
- **Expected test totals are guesses**; only "nothing failed and the total rose"
  is binding.
