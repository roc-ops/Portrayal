# The FS Archetypes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FHD-1UFCE enclosure and one cassette per distinct shape the FS catalogue contains — plus C2's `splice` rear-port type — so every shape is proved before the 62-cassette bulk build.

**Architecture:** The catalogue is 62 cassettes across about twenty descriptions, but only a handful of SHAPES: one rear connector to many front fibres (done, #240), several rear connectors, a second front connector family, a split with ratios, and a rear that is a splice tray rather than a connector. Each archetype here is a real photographed SKU except the splice cassette, for which no imagery exists anywhere in the corpus. The enclosure comes first because it is what the cassettes seat in, and because it gives `fs` its first device.

**Tech Stack:** Python 3, JSON Schema (draft 2020-12), PyYAML, SVG, pytest.

**Spec:** `docs/optical-paths-design.md` — section C2 (`splice`), section C3 (taps and ratios), and section E step 5 (the FS build). This is plan 6; the sequence is longer than the six this document first implied, and Task 1 Step 6 records the new shape.

## Global Constraints

- `working/` is NEVER committed and never published. Reference imagery stays there; transcribe facts into contracts.
- Every dimension not measured is `confidence: estimated` (or `borrowed`, naming the part it came from) with provenance saying what it was derived from. **Never launder an estimate into a measurement.**
- Version bumps go in BEFORE `devicelock --update`, never after.
- **Run every gate in the FOREGROUND**, using the Bash tool's own `timeout` parameter at `600000`. Do not use `run_in_background`, the Monitor tool, TaskOutput, or a shell-level `timeout`. The suite takes about 4.5 minutes. The chain, in order:
  1. `python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library | tail -3`
  2. `./publish.sh --no-images`
  3. `python3 spec/tools/portrayal/devicelock.py --library library`
  4. `python3 -m pytest spec/tests -q 2>&1 | tail -5`
- Lint baseline: `LINT: ok (665 files, 1291 warnings in 22 rules)`. **The trailing number counts rules that PRODUCED a warning, not rules that exist.** The file count rises by one per new contract. If the WARNING count moves, find out what started warning before continuing.
- **Adding or changing a lint rule means regenerating its docs page**: `python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md`. `test_docs_page_matches_the_generator` compares it byte for byte.
- Test baseline: `1557 passed, 1 skipped`. Expected totals are a GUIDE — the binding check is that nothing FAILED and the total only went up.
- Exported-document baseline: `967`. Each new fibre module adds 2 module types + 1 fibre map = 3; a device adds its own documents. Check the number moved by what you expect and no more.
- Commit messages end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. No backticks in the message text: write it to a file and `git commit -F`.
- Do not dispatch subagents from inside a task.

---

## What is established, and what the corpus does not hold

Measured before the plan was written, against `main` at `b851deb3`.

**The enclosure is fully dimensioned and is the one part here that needs no
estimating.** `working/intake/fs/fhd/datasheets/fhd-1ufce-fiber-enclosure-datasheet.pdf`
page 7 carries dimensioned front and top views:

```
body width      17.64 in   448.0 mm
rack width      19 in      482.6 mm
height          1.73 in    44.0 mm      (1U)
body depth      17.04 in   432.8 mm
overall depth   18.39 in   467.2 mm     (including the rear projections)
rear feature    2.8 in     71 mm
```

Four slots at the 108.97 mm module width need 435.88 mm, which fits inside 448.0.
(The FMT-N's unexplained 430.0 mm — still an open question in the spec — does NOT
fit, which is why that enclosure is not the modelling target and is not in this plan.)

**The PDFs in the corpus have never been converted.** There is no `doc.md` anywhere
under `working/intake/fs/fhd/`, though `COVERAGE.md` was written against converted
output that no longer exists. The dimensions above were read directly off page 7 of
the PDF. **A task needing a figure from a PDF must read the PDF**, not look for a
converted sibling.

**Imagery exists for 29 SKUs and no others.** Cross-referencing
`working/intake/fs/fhd/photos/` against `CATALOGUE.tsv`, the photographed set is 2
enclosures, 8 panels and 19 cassettes. The archetypes below were chosen from that
set, not from what would be tidiest.

**NO SPLICE CASSETTE IS PHOTOGRAPHED.** Eleven of the 62 cassettes are splice
cassettes and not one has an image in the corpus, and `COVERAGE.md` records that
per-SKU datasheets were never staged ("one per SKU on ~84 product pages; not
fetched"). So Task 3 cannot measure its subject. It is still worth building, because
the novel part of a splice cassette is its REAR — a splice tray with no connector on
it — and that is a vocabulary question rather than a geometry one. Its front is
derived from family constants that ARE established: the 108.97 x 35.05 faceplate
that `panel_measure` refuses to scale without, and the 12.92 mm adapter pitch floor
recorded as `fhd-lc-cassette`. The plan says so in the contract, in the task, and
here.

**This plan gives `fs` its first device, and that quietly changes a plan-5 test.**
`Dist.manufacturer_of` checks devices first and falls back to `vendors.yaml`. The
fallback exists because FS shipped cassettes before anything modelled a chassis.
Once Task 1 lands, `manufacturer_of("fs")` resolves from the DEVICE, and
`test_a_vendor_with_no_device_can_still_ship_modules` (spec/tests/test_optical_export.py:85)
keeps passing **for the wrong reason** — its name becomes a lie and the fallback is
exercised by nothing in the library. Task 1 re-points it. This is the same shape as
plan 3's `test_the_risers_still_use_the_legacy_spelling`, which watches a fallback
that would otherwise go quiet.

**Archetypes, and what each one proves:**

| task | SKU | shape | what it is the first of |
|---|---|---|---|
| 1 | 70361 | FHD-1UFCE enclosure | the first `fs` device; the thing cassettes seat in |
| 3 | 382907 | Fiber Splice Cassette, LC UPC, OS2, 12F | a rear that is a splice, not a connector (C2) |
| 4 | 57341 | 2x MTP-12 (Male) to LC, OS2, 24F, Type A | **two rear connectors** on one module |
| 5 | 57058 | MTP-12 (Male) to SC, OS2, 12F, Type A | a second front family; first user of `common/sc-duplex-adapter@1` and its pitch floor |
| 6 | 57023 | MTP-24 (Male) to LC, OS2, 24F, Type A | an MPO wider than 12 — the first rear connector `common/mpo-adapter@1` cannot be |

**A tap was the original choice for Task 6 and it was WRONG.** See the finding below.

**THE TAP CASSETTES ARE SINGLE-FACED, AND THAT BLOCKS 19 OF THE 62.** This plan
first chose SKU 68758 (`TAP Cassette, 8x LC Duplex Live, 4x LC Duplex TAP, OS2
70/30`) as the archetype for C3's split-with-ratio. Reading `68758.main.jpg`
settles that it cannot be: the part is an **LC-to-LC** tap carrying twelve LC duplex
adapters in two rows on ONE face, with its wiring diagram printed on the lid
(`OUT`/`IN` for LIVE 1 and LIVE 2, `OUT`/`OUT` for TAP). There is no rear connector
at all.

That makes it the same shape as the six Smartoptics PPMs, and it hits the same gate:
plan 5 gated the port projection and the fibre map on a module declaring a rear face,
because nothing in the vocabulary names which endpoint is a trunk. A tap built today
would export no ports and no map, and the Task 6 tests written against it would have
failed on their first run.

So the tap is deferred, and the blocked population is now SIZED rather than guessed:
**19 tap cassettes, 9 PPMs and the A22 — 29 parts — all waiting on one piece of
vocabulary.** That is a much stronger argument for designing the trunk vocabulary
BEFORE the bulk build than existed when plan 5 deferred it, and the tap's own lid
diagram is new evidence for how to design it: FS labels the roles `LIVE`, `TAP`,
`IN` and `OUT` on the faceplate, and the PPMs spell the same idea `common` and
`split`. **Plan 7 should be the trunk vocabulary, not the bulk build.**

C3's split-with-ratio is therefore proved by no archetype in this plan. It remains
covered only by the constructed unit test plan 5 landed (`test_a_split_carries_its_ratio`),
and that is stated here rather than left to be discovered.

**Deliberately NOT in this plan:** the 15 adapter panels and the remaining 57
cassettes (the bulk build); the PPM retro-fit with its `combine` syntax and trunk vocabulary; the conversion cassettes, which are unphotographed AND many-to-many and
belong with the bulk build's intake.

---

## File Structure

| file | responsibility |
|---|---|
| `docs/optical-paths-design.md` | MODIFY — section E renumbered to 8 plans |
| `library/devices/fs/fhd-1ufce/device.yaml` | CREATE — the enclosure, 4 cassette bays |
| `library/devices/fs/fhd-1ufce/skins/*.svg` | CREATE — its drawing |
| `spec/schemas/component.schema.json` | MODIFY — `optical.rear-kind` |
| `spec/tools/portrayal/optical_ports.py` | MODIFY — `splice` as a rear port type |
| `spec/tools/portrayal/lint.py` | MODIFY — L87 |
| `library/components/fs/fhd-splice-12-lc/v1/` | CREATE — the splice cassette |
| `library/components/fs/fhd-2mtp12-lc-os2-a/v1/` | CREATE — two rear connectors |
| `library/components/fs/fhd-1mtp12-sc-os2-a/v1/` | CREATE — the SC front |
| `library/components/fs/fhd-tap-8lc-4lc-7030/v1/` | CREATE — the tap |
| `spec/tests/test_fs_archetypes.py` | CREATE — one section per archetype |

Each cassette is its own contract plus a rear-face contract plus two skins, following
`fs/fhd-1mtp6lcd-os2-a` exactly. Read that contract before writing any of them: it is
the worked example, and matching its shape is cheaper than inventing four variations.

---

### Task 1: The FHD-1UFCE enclosure, and the fallback it stops exercising

**Files:**
- Create: `library/devices/fs/fhd-1ufce/device.yaml`, `library/devices/fs/fhd-1ufce/skins/front.svg`
- Modify: `spec/tests/test_optical_export.py:85`
- Modify: `docs/optical-paths-design.md` (section E)
- Test: `spec/tests/test_fs_archetypes.py` (create)

**Interfaces:**
- Produces: device `fs/fhd-1ufce`, manufacturer `FS.com`, four bays accepting FHD modules.

- [ ] **Step 1: Read the worked examples before writing anything**

Read `library/devices/smartoptics/dcp-2/device.yaml` for the bay-and-view shape, and
`library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml` for how an FS part records
provenance. Do not invent a device layout from scratch.

- [ ] **Step 2: Write the failing test**

Create `spec/tests/test_fs_archetypes.py`:

```python
"""The FS archetypes - one real part per shape the catalogue contains.

Every figure here is either measured off FS's own dimensioned drawing (the
enclosure) or off a face-on render validated by panel_measure (the cassettes),
except the splice cassette, which no image in the corpus shows at all. Where a
number is estimated the contract says so; these tests check the claims, not the
prose.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))


def device(rel):
    p = LIB / "devices" / rel / "device.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def contract(rel):
    p = LIB / "components" / rel / "contract.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def test_the_enclosure_carries_its_dimensioned_figures():
    """Read off page 7 of FS's own datasheet: front and top views, dimensioned.

    448.0 body in a 482.6 rack, 44.0 high, 432.8 deep. This is the only part in
    this plan whose size needs no estimating at all.

    A DEVICE DECLARES `chassis`, not `size` - `size` is a per-view key. See
    library/devices/smartoptics/dcp-2/device.yaml for the shape.
    """
    d = device("fs/fhd-1ufce")
    assert d is not None, "fs/fhd-1ufce not built"
    assert d["manufacturer"] == "FS.com"
    ch = d["chassis"]
    assert (ch["width"], ch["height"], ch["depth"]) == (448.0, 44.0, 432.8)
    assert ch["ru"] == 1


def test_the_enclosure_holds_four_modules():
    """Four slots at the 108.97 module width need 435.88, inside the 448.0 body."""
    d = device("fs/fhd-1ufce")
    bays = d["views"]["front"]["components"]["bays"]
    assert len(bays) == 4, f"expected 4 cassette slots, found {len(bays)}"
    assert 4 * 108.97 <= 448.0


def test_the_enclosure_accepts_every_fs_cassette_in_the_library():
    """THIS IS WHAT KEEPS THE `accepts` LIST HONEST.

    Four later tasks each add a cassette, and an `accepts` list written once is
    an omission that passes quietly - the enclosure would ship accepting one of
    the five modules that seat in it. Every FHD cassette seats in every FHD
    enclosure; that is what the format is for, so the assertion is total rather
    than a list someone maintains by hand.
    """
    d = device("fs/fhd-1ufce")
    accepted = set()
    for bay in d["views"]["front"]["components"]["bays"]:
        accepted |= set(bay.get("accepts") or [])
    modelled = set()
    for c in (LIB / "components" / "fs").glob("*/v*/contract.yaml"):
        doc = yaml.safe_load(c.read_text()) or {}
        if doc.get("kind") != "module":
            continue                       # a rear face is not a seatable part
        modelled.add(f"fs/{doc['name']}@{c.parent.name[1:]}")
    missing = sorted(modelled - accepted)
    assert not missing, f"cassettes the enclosure does not accept: {missing}"
```

- [ ] **Step 3: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_fs_archetypes.py -q`
Expected: FAIL — `fs/fhd-1ufce not built`.

- [ ] **Step 4: Write the device**

Create `library/devices/fs/fhd-1ufce/device.yaml`. Transcribe these figures and no
others; anything you cannot read off page 7 of
`working/intake/fs/fhd/datasheets/fhd-1ufce-fiber-enclosure-datasheet.pdf` is
estimated and must say so in `provenance`:

```
manufacturer: FS.com          model: FHD-1UFCE
chassis: {width: 448.0, height: 44.0, depth: 432.8, ru: 1}
rack width 482.6 (the 19in ears), overall depth 467.2 including rear projections
four bays, each accepting an FHD module at the 108.97 module width
```

**THE DEVICE SCHEMA GOVERNS, NOT THE COMPONENT ONE.** A device declares `chassis`
with `width`/`height`/`depth`/`ru`; `size` is a per-view key spelled `{w, h}`. A bay
entry looks like
`{id, at, size, accepts, default, group, rel-pos}` — read
`library/devices/smartoptics/dcp-2/device.yaml` and match it.

The bays accept `fs/fhd-1mtp6lcd-os2-a@1` today and gain the rest as this plan adds
them — list every FS cassette that exists at the time you write the file.

- [ ] **Step 5: Re-point the plan-5 fallback test**

`spec/tests/test_optical_export.py:85` reads:

```python
def test_a_vendor_with_no_device_can_still_ship_modules():
    ...
    assert d.manufacturer_of("fs") == "FS.com"
```

FS now has a device, so this passes through the DEVICE lookup and no longer watches
the vendors.yaml fallback at all. Replace it with a test that pins the mechanism
rather than the datum:

```python
def test_the_registry_fallback_still_answers_for_a_deviceless_namespace():
    """PLAN 5'S FALLBACK, AND THIS IS WHAT WATCHES IT.

    `manufacturer_of` checks devices first and falls back to vendors.yaml, so a
    vendor that ships parts before it ships a chassis is still orderable. FS was
    that vendor until the FHD-1UFCE landed; now it resolves from its device, and
    the old test passed through the device path while claiming to prove the
    fallback. This drives the fallback directly instead.
    """
    from artifacts import Dist
    d = Dist(str(DIST))
    assert d.manufacturer_of("fs") == "FS.com"      # now via the device
    # a namespace that exists in vendors.yaml and has no device at all
    deviceless = [ns for ns in d.vendors
                  if not any(x.get("ns") == ns for x in d.devices)]
    assert deviceless, "every vendor now has a device - the fallback is unwatched"
    ns = deviceless[0]
    assert d.manufacturer_of(ns) == d.vendors[ns]["display"]


def test_a_namespace_with_no_vendor_is_still_not_orderable():
    """`common/` and `std/` are absent from vendors.yaml, so the property holds
    by data rather than by a special case."""
    from artifacts import Dist
    d = Dist(str(DIST))
    assert d.manufacturer_of("common") is None
    assert d.manufacturer_of("std") is None
```

If `deviceless` comes back empty, STOP and report it: it means the fallback has no
real subject left, and the right answer is a decision about whether to keep it, not
a test that asserts nothing.

- [ ] **Step 6: Renumber the sequence in the spec**

`docs/optical-paths-design.md` section E ends with a paragraph telling the
implementation plan to stage the work. Append to it:

```
**The staging turned out to be eight plans, not six.** Steps 1-4 landed as plans
1-5 (PRs #236, #237, #239, #240, #242) and proved themselves on one cassette, as
this section asked. Step 5 is then plan 6 (the enclosure and one cassette
per two-faced shape) and the bulk build that follows it; step 6, the PPM retro-fit,
owes the two things this document still records as undesigned - a `combine` syntax,
and a way to name which optical endpoint is a trunk. **The trunk is now the larger
of the two and is not only the PPMs' problem:** every one of the 19 TAP cassettes
carries its live and monitor ports on a single face, so 29 parts in all are waiting
on that vocabulary, and it should be designed before the bulk build rather than
after it.
```

Leave the numbered list itself alone: it describes the order of work, which has not
changed. Only the count of plans did.

- [ ] **Step 7: Run the gate chain and commit**

Expected: lint file count up by one device file; warnings unmoved; devicelock 0;
tests up by 3 (2 new, 1 replaced by 2). The export count rises by the enclosure's own
device-type documents — record what it becomes, since later tasks check against it.

---

### Task 2: `splice` — a rear that is not a connector

**Files:**
- Modify: `spec/schemas/component.schema.json`
- Modify: `spec/tools/portrayal/optical_ports.py`
- Modify: `spec/tools/portrayal/lint.py`, `docs/lint-rules.md`
- Test: `spec/tests/test_optical_ports.py` (append)

**Interfaces:**
- Consumes: `optical_ports.port_type(family, polish)`, `optical_ports.ports(entry, load_ref)`.
- Produces: `optical.rear-kind: splice`; lint rule **L87**.

**Why a key rather than a component.** Every other rear port is a connector this
library draws — an MPO adapter, an LC shell. A splice is the absence of one: the
trunk's fibres are fusion-spliced to the cassette's pigtails and there is nothing on
the back face to draw. Modelling it as a component would mean inventing a part with
no geometry, which is how `common/sc-apc` ended up being a device-specific moulded
bay masquerading as an adapter. `rear-kind` states the fact instead.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_optical_ports.py`:

```python
def test_a_splice_rear_exports_as_one_splice_port():
    """C2, and upstream's own convention: the devicetype-library ships ADC's
    PPP-SC-SM with `rear-ports: [{name, type: splice, positions: 1}]`."""
    entry = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-adapter@3",
                        "at": [0, 0]}],
             "faces": {"rear": {"ref": "t/splice-rear@1"}},
             "optical": {"media": "os2", "polish": "upc", "rear-kind": "splice",
                         "paths": [{"from": "lc1.1", "to": "rear:splice.1"},
                                   {"from": "lc1.2", "to": "rear:splice.2"}]}}
    known = {"common/lc-duplex-adapter@3": {"optical": {"positions": 2}},
             "common/fibre-splice@1": {"optical": {"positions": 2}},
             "t/splice-rear@1": {"parts": [{"id": "splice",
                                            "ref": "common/fibre-splice@1"}]}}
    got = P.ports(entry, known.get)
    assert got["rear"] == [{"name": "SPLICE-1", "type": "splice", "positions": 2}]
    assert len(got["front"]) == 2


def run87(doc, path="t/contract.yaml"):
    L.ERRORS.clear()
    L.lint_component_optical_rear_kind(path, doc)
    return [e for e in L.ERRORS if "[L87]" in e]


def test_declaring_a_splice_rear_without_a_rear_face_is_an_error():
    """`rear-kind` describes a rear face. Saying it with no rear face to describe
    is a claim about a drawing that does not exist."""
    got = run87({"optical": {"rear-kind": "splice",
                             "paths": [{"from": "a.1", "to": "b.1"}]}})
    assert len(got) == 1, got
    assert "rear face" in got[0]


def test_a_splice_rear_with_a_rear_face_is_quiet():
    assert run87({"faces": {"rear": {"ref": "t/x@1"}},
                  "optical": {"rear-kind": "splice",
                              "paths": [{"from": "a.1", "to": "rear:b.1"}]}}) == []


def test_saying_nothing_about_the_rear_kind_is_quiet():
    """Every cassette built so far has a connector on the back and says nothing."""
    assert run87({"faces": {"rear": {"ref": "t/x@1"}},
                  "optical": {"paths": [{"from": "a.1", "to": "rear:b.1"}]}}) == []
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_optical_ports.py -q`
Expected: FAIL — the rear port types as `None` (no family), and
`lint_component_optical_rear_kind` does not exist.

- [ ] **Step 3: Add the schema key**

In `spec/schemas/component.schema.json`, inside `properties.optical.properties`:

```json
   "rear-kind": {
    "enum": ["splice"],
    "description": "WHAT THE BACK OF THIS MODULE IS, when it is not a connector. A splice cassette's trunk fibres are fusion-spliced to its pigtails, so there is nothing on the rear face to draw and no adapter to compose - `splice` is a real rear-port type upstream, shipping in the devicetype-library's ADC PPP-SC-SM. Omitted on every module whose rear carries an adapter, which is all of them so far. L87 checks that a module claiming one has a rear face to claim it about."
   },
```

- [ ] **Step 4: Type the rear port**

In `spec/tools/portrayal/optical_ports.py`, in `ports()`, where the rear port's type
is computed, prefer the declared rear kind over the family lookup:

```python
    rear_kind = (entry.get("optical") or {}).get("rear-kind")
```

and for each rear port use `rear_kind` when set, otherwise
`port_type(family_of(ref), polish)`. A splice rear has no connector component to
resolve a family from, so the family lookup would answer `None` and export
`type: null` — which is the failure this key exists to prevent.

The port NAME still comes from `rear_port_names`, so a splice rear part with id
`splice` names its port `SPLICE-1`. Do not special-case the name.

- [ ] **Step 5: Add L87**

In `RULES`, beside L86:

```python
    "L87": ("component",  "a module naming what its rear IS has a rear face to name", "add `faces.rear`, or drop `optical.rear-kind`"),
```

Beside the other optical rules:

```python
def lint_component_optical_rear_kind(path, data):
    """L87: `optical.rear-kind` describes a rear face, so there must be one.

    The key says what the back of the module IS when it is not a connector. A
    contract that claims a splice rear and declares no rear face is describing a
    drawing that does not exist, and the projection - which is gated on a rear
    face - would ignore the claim entirely and export nothing, silently.
    """
    if not isinstance(data, dict):
        return
    opt = data.get("optical") or {}
    if not opt.get("rear-kind"):
        return
    if not face_ref(data, "rear"):
        err(path, "L87", f"declares optical.rear-kind {opt['rear-kind']!r} but no "
                         "rear face, so there is nothing for it to describe and "
                         "the projection would ignore it")
```

Register it in `main()` beside `lint_component_optical_polish(f, d)`:

```python
                lint_component_optical_rear_kind(f, d)
```

- [ ] **Step 6: Prove L87 fires from the real binary**

This project has shipped a lint rule as unreachable code with a green unit test
beside it twice. Build a throwaway library with a contract declaring
`optical.rear-kind: splice` and no `faces.rear`, run
`python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library <tmpdir>`,
and confirm `[L87]` appears in stdout. Put that output in the report.

- [ ] **Step 7: Regenerate the rules page, run the chain, commit**

```bash
python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md
```

Expected: lint warnings unmoved — L87 finds nothing until Task 3.

---

### Task 3: The splice cassette

**Files:**
- Create: `library/components/common/fibre-splice/v1/contract.yaml` + skin
- Create: `library/components/fs/fhd-splice-12-lc/v1/contract.yaml` + skin
- Create: `library/components/fs/fhd-splice-12-lc-rear/v1/contract.yaml` + skin
- Test: `spec/tests/test_fs_archetypes.py` (append)

**Interfaces:**
- Consumes: `optical.rear-kind` and L87 from Task 2.
- Produces: `fs/fhd-splice-12-lc@1`, exporting one `splice` rear port of 12 positions
  and twelve `lc-upc` front ports.

**THE SUBJECT OF THIS TASK IS NOT PHOTOGRAPHED.** No image in
`working/intake/fs/fhd/photos/` shows any of the eleven splice cassettes, and no
per-SKU datasheet was staged. Every placement in these contracts is therefore
`estimated`, derived from family constants rather than measured, and the provenance
must say that in as many words. The catalogue row is the sourced part:

```
cassette	382907	FHD® Fiber Splice Cassette, LC UPC, OS2, 12 Fibers
```

which gives the connector family, the POLISH (named here, unlike SKU 57016 — record
it as sourced, citing this row), the media and the fibre count. Nothing else about
this part is known.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_fs_archetypes.py`:

```python
SPLICE = "fs/fhd-splice-12-lc/v1"


def test_the_splice_cassette_states_that_nothing_measured_it():
    """Eleven splice cassettes in the catalogue and not one photograph.

    The whole contract is derived from family constants. If a later intake
    fetches imagery and someone measures it, this assertion is what tells them
    the prose needs rewriting too.
    """
    c = contract(SPLICE)
    assert c is not None, "fs/fhd-splice-12-lc@1 not built"
    conf = set(c["size-confidence"].values())
    assert conf <= {"estimated", "borrowed"}, \
        f"claims a measurement the corpus cannot support: {c['size-confidence']}"
    note = (c.get("provenance") or {}).get("size", "")
    assert "no image" in note.lower() or "not photographed" in note.lower(), \
        "provenance must say plainly that no imagery of this part exists"


def test_the_splice_cassettes_polish_is_sourced_not_assumed():
    """Unlike SKU 57016, this row names it: 'Fiber Splice Cassette, LC UPC'."""
    c = contract(SPLICE)
    assert c["optical"]["polish"] == "upc"
    note = (c.get("provenance") or {}).get("optical", "")
    assert "382907" in note, "cite the catalogue row that names the polish"


def test_the_splice_cassette_has_a_splice_rear():
    c = contract(SPLICE)
    assert c["optical"]["rear-kind"] == "splice"
    assert (c.get("faces") or {}).get("rear"), "a rear-kind needs a rear face (L87)"
    assert len(c["optical"]["paths"]) == 12
```

- [ ] **Step 2: Run it to verify it fails**

Expected: FAIL — `fs/fhd-splice-12-lc@1 not built`.

- [ ] **Step 3: Build `common/fibre-splice@1`**

The rear face needs a part for the twelve fibres to terminate on, and it is not a
connector. Give it `optical: {positions: 12}` and a deliberately plain drawing — a
splice tray holder, not an adapter bezel. Its `size-confidence` is `estimated`
throughout and its provenance says it is a placeholder for a tray whose geometry
nothing in the corpus records.

- [ ] **Step 4: Build the rear and front contracts**

Follow `fs/fhd-1mtp6lcd-os2-a` exactly for structure. The front is six
`common/lc-duplex-v-adapter@1` at the 12.92 pitch floor recorded as
`fhd-lc-cassette`, on the 108.97 x 35.05 faceplate. Say in `provenance.parts` that
the placement is the family arrangement and not a measurement of this SKU.

The twelve paths run `lc1.1 -> rear:splice.1` through `lc6.2 -> rear:splice.12`.
A splice cassette has no polarity to declare — the mapping is whatever the splicer
made — so omit `polarity` and say why in `provenance.optical`.

- [ ] **Step 5: Add this cassette to the enclosure**

`library/devices/fs/fhd-1ufce/device.yaml` lists what each bay accepts, and Task 1's
`test_the_enclosure_accepts_every_fs_cassette_in_the_library` fails until this
cassette is in every bay's `accepts`. Add it.

- [ ] **Step 6: Run the chain and commit**

Expected: lint file count up by 6; warnings unmoved; the export count up by 3 (two
module types and one fibre map). Confirm the exported rear port reads
`type: splice`.

---

### Task 4: Two rear connectors

**Files:**
- Create: `library/components/fs/fhd-2mtp12-lc-os2-a/v1/` + its rear + skins
- Test: `spec/tests/test_fs_archetypes.py` (append)

**Interfaces:**
- Produces: `fs/fhd-2mtp12-lc-os2-a@1` — the first module with more than one rear port.

SKU 57341, `FHD® 2x MTP-12 (Male) to LC Cassette, OS2, 24 Fibers, Type A`, five
images in the corpus. Measure its face with
`spec/tools/intake/panel_measure.py`, which refuses unless the 108.97 mm width scale
reproduces the 35.05 mm height — twelve LC duplex adapters across one FHD faceplate.

This is the first part that exercises rear-port NAMING against more than one
connector. Plan 5 left two findings parked in that area, and this task is where they
stop being hypothetical:

- `rear_port_names` keys its collision counter by part id alone, so two rear parts
  sharing an id would collapse. Give the two MTPs DISTINCT ids (`mtp1`, `mtp2`), and
  add a test asserting the two exported rear ports have different names.
- `rows.sort` in `fibre_map` sorts on the rear port name as a string. With two ports
  that is fine; it breaks at ten. Assert the row order is what you expect and leave
  the sort alone — the higher-count cassettes in the bulk build are where it must be fixed.

- [ ] **Step 1: Write the failing test**

```python
TWO_MTP = "fs/fhd-2mtp12-lc-os2-a/v1"


def test_two_rear_connectors_export_as_two_distinct_ports():
    """The first module with more than one rear port.

    `rear_port_names` numbers within a part id, so two parts sharing an id would
    collapse to one name and the fibre map would bind 24 fibres to 12 positions.
    Distinct ids are what prevent that, and this is what checks it.
    """
    import json
    import dcim_export as D
    import optical_ports as P
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    idx = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
           for e in json.loads(f.read_text())["components"]}
    e = idx["fs/fhd-2mtp12-lc-os2-a@1"]
    got = P.ports(D.contract_view(e), idx.get)
    names = [p["name"] for p in got["rear"]]
    assert len(names) == 2, got["rear"]
    assert len(set(names)) == 2, f"two rear ports share one name: {names}"
    assert sum(p["positions"] for p in got["rear"]) == 24
    assert len(got["front"]) == 24


def test_every_one_of_the_24_fibres_is_bound():
    import json
    import dcim_export as D
    import optical_ports as P
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built")
    idx = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
           for e in json.loads(f.read_text())["components"]}
    e = idx["fs/fhd-2mtp12-lc-os2-a@1"]
    m = P.fibre_map(D.contract_view(e), idx.get, "FHD-2X12MTPLCOS2A")
    assert len(m["rows"]) == 24
    assert len({(r["rear"], r["rear_position"]) for r in m["rows"]}) == 24, \
        "two fibres land on one rear position"
```

- [ ] **Step 2: Run it to verify it fails, then build, then re-run**

Build the contracts the same way Task 3 did, with the face MEASURED this time —
record the measured centres in `provenance.parts`, not a pitch multiplied out, the
way `fs/fhd-1mtp6lcd-os2-a` does.

- [ ] **Add this cassette to the enclosure**

`library/devices/fs/fhd-1ufce/device.yaml` lists what each bay accepts, and Task 1's
`test_the_enclosure_accepts_every_fs_cassette_in_the_library` fails until this
cassette is in every bay's `accepts`. Add it before running the chain.

- [ ] **Step 3: Run the chain and commit**

---

### Task 5: A second front connector family

**Files:**
- Create: `library/components/fs/fhd-1mtp12-sc-os2-a/v1/` + its rear + skins
- Test: `spec/tests/test_fs_archetypes.py` (append)

SKU 57058, `FHD® MTP-12 (Male) to SC Cassette, OS2, 12 Fibers, Type A`, photographed.
This is the FIRST COMPONENT TO COMPOSE `common/sc-duplex-adapter@1`, which was
measured in the connector-components work and has been composed by nothing since.
It is therefore also the first part whose `sc-duplex-adapter` pitch floor of 13.0 mm
gets checked by L81 against a real layout.

`57058.main.jpg` is the render its adapter body width was measured from originally,
so the same image serves here.

- [ ] **Step 1: Write the failing test**

```python
SC = "fs/fhd-1mtp12-sc-os2-a/v1"


def test_the_sc_cassette_is_the_first_user_of_the_sc_adapter():
    """`common/sc-duplex-adapter@1` was measured and then composed by nothing.

    Its 13.0 pitch floor has never been checked against a real layout, because
    L81 reads `conforms` off a composed part and nothing composed it.
    """
    c = contract(SC)
    assert c is not None, "fs/fhd-1mtp12-sc-os2-a@1 not built"
    refs = [p["ref"] for p in c["parts"]]
    assert refs.count("common/sc-duplex-adapter@1") == 6, refs


def test_the_sc_adapters_respect_the_registry_floor():
    """L81 checks this on every build; asserting it here names the number."""
    import lint as L
    L.STANDARDS.update(
        L.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])
    assert L.STANDARDS["sc-duplex-adapter"]["pitch"] == 13.0
    c = contract(SC)
    xs = sorted(float(p["at"][0]) for p in c["parts"]
                if p["ref"] == "common/sc-duplex-adapter@1")
    gaps = [round(xs[i] - xs[i - 1], 2) for i in range(1, len(xs))]
    assert min(gaps) >= 13.0 - 0.01, f"tighter than the measured floor: {gaps}"


def test_the_sc_front_ports_type_as_sc():
    c = contract(SC)
    assert c["optical"]["polish"] in ("upc", "apc")
```

- [ ] **Add this cassette to the enclosure**

`library/devices/fs/fhd-1ufce/device.yaml` lists what each bay accepts, and Task 1's
`test_the_enclosure_accepts_every_fs_cassette_in_the_library` fails until this
cassette is in every bay's `accepts`. Add it before running the chain.

- [ ] **Step 2: Build it, run the chain, commit**

The catalogue row does not name this SKU's polish, the same silence as 57016 — so
record it as the convention default, MARKED AS AN ASSUMPTION, citing the row. Do not
copy 57016's note verbatim; this is a different SKU and a different connector family.

If L81 reports the composed pitch as narrower than 13.0, STOP and report it rather
than widening the placement to satisfy the rule: the measurement would be telling you
the registry floor is wrong, and that is a finding about the standard, not about this
cassette.

---

### Task 6: An MPO wider than twelve

**Files:**
- Create: `library/components/common/mpo24-adapter/v1/contract.yaml` + skin
- Create: `library/components/fs/fhd-1mtp24-lc-os2-a/v1/` + its rear + skins
- Test: `spec/tests/test_fs_archetypes.py` (append)

**Interfaces:**
- Consumes: everything above.
- Produces: `common/mpo24-adapter@1` (24 positions) and `fs/fhd-1mtp24-lc-os2-a@1`.

SKU 57023, `FHD® MTP-24 (Male) to LC Cassette, OS2, 24 Fibers, Type A`, photographed.

`common/mpo-adapter@1` declares `optical.positions: 12` and cannot serve an MTP-24.
The spec's own connector table asks for `MTP/MPO -8/-12/-16/-24` across 48 modules, and
this is the first part that needs one of the other three. It proves the MPO family
scales rather than being a one-off, which is what the bulk build will rely on.

The front is twelve `common/lc-duplex-v-adapter@1` — TWICE the count of SKU 57016 on
the same 108.97 x 35.05 faceplate, so they do not sit in one row. Measure the actual
arrangement with `spec/tools/intake/panel_measure.py`; do not assume it is 57016's row
doubled. The 12.92 pitch floor recorded as `fhd-lc-cassette` applies along a row, and
if the measured arrangement is two rows the spacing DOWN is a different number that
this plan does not have — record it as measured and say which axis it is.

- [ ] **Step 1: Write the failing test**

```python
MTP24 = "fs/fhd-1mtp24-lc-os2-a/v1"


def test_the_library_has_an_mpo_wider_than_twelve():
    """`common/mpo-adapter@1` is 12 positions and the catalogue needs 8, 12, 16
    and 24 across 48 modules. This is the first part that needs another."""
    a = contract("common/mpo24-adapter/v1")
    assert a is not None, "common/mpo24-adapter@1 not built"
    assert a["optical"]["positions"] == 24
    twelve = contract("common/mpo-adapter/v1")
    assert twelve["optical"]["positions"] == 12, "the 12 must stay a 12"


def test_the_mtp24_cassette_carries_24_fibres_on_one_rear_port():
    """One rear connector, 24 positions - the count is on the port, not the
    number of ports. This is C1's asymmetry at a width nothing has exercised."""
    import json
    import dcim_export as D
    import optical_ports as P
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    idx = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
           for e in json.loads(f.read_text())["components"]}
    e = idx["fs/fhd-1mtp24-lc-os2-a@1"]
    got = P.ports(D.contract_view(e), idx.get)
    assert len(got["rear"]) == 1, got["rear"]
    assert got["rear"][0]["positions"] == 24
    assert got["rear"][0]["type"] == "mpo"
    assert len(got["front"]) == 24


def test_the_front_numbering_covers_all_24_without_a_gap():
    """The front-label derivation walks adapters by `at.x`. Twelve adapters do
    not fit one row on a 108.97 face, so if the real arrangement is two rows the
    x-order alone may not reproduce the vendor's numbering - which is exactly the
    soft spot plan 5's self-review named. This is where it gets tested."""
    import json
    import dcim_export as D
    import optical_ports as P
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built")
    idx = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
           for e in json.loads(f.read_text())["components"]}
    e = idx["fs/fhd-1mtp24-lc-os2-a@1"]
    m = P.fibre_map(D.contract_view(e), idx.get, "FHD-1X24MTPLCOS2A")
    assert sorted(int(r["front"]) for r in m["rows"]) == list(range(1, 25))
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_fs_archetypes.py -q`
Expected: FAIL — `common/mpo24-adapter@1 not built`.

- [ ] **Step 3: Build the MPO-24 adapter**

Model it on `common/mpo-adapter@1`, which is the worked example for this family — read
that contract first. An MTP-24 adapter body is the same MPO shell as the 12; what
changes is `optical.positions: 24` and, if the imagery supports it, the ferrule
detail. If the body dimensions cannot be measured from `57023.main.jpg`, borrow them
from `common/mpo-adapter@1` and record `confidence: borrowed` NAMING that part — do
not restate them as measured.

- [ ] **Step 4: Build the cassette**

Front, rear and skins, following `fs/fhd-1mtp6lcd-os2-a`. Twelve LC duplex adapters,
one MPO-24 on the rear, twenty-four straight-through Type A paths.

**If the measured front arrangement is two rows**, `test_the_front_numbering_covers_all_24_without_a_gap`
is the test that will tell you whether the x-order derivation still reproduces FS's
numbering. If it does not, STOP and report it rather than renumbering the contract to
suit the code: plan 5's self-review named this as the weakest link in the projection,
and a second real cassette disagreeing with it is a finding about `_front_parts`, not
about this SKU.

- [ ] **Add this cassette to the enclosure**

`library/devices/fs/fhd-1ufce/device.yaml` lists what each bay accepts, and Task 1's
`test_the_enclosure_accepts_every_fs_cassette_in_the_library` fails until this
cassette is in every bay's `accepts`. Add it before running the chain.

- [ ] **Step 5: Run the chain and commit**

Expected: lint file count up by 6; warnings unmoved; export count up by 3.

---

## Self-Review

**1. Spec coverage.** C2 `splice` — Tasks 2 and 3, and it is a real rear port type on
a real contract rather than a table entry. **C3 taps and the description-ratio — NOT
COVERED, and the reason is a finding rather than an omission**: every tap in the
catalogue is single-faced, so none can be built until the trunk vocabulary exists.
Task 6 was a tap and is now an MPO-24; the split path stays covered only by plan 5's
constructed unit test. Section E step 5 (the FS build) — this plan covers the enclosure and one cassette per
two-faced shape; the 15 panels and the remaining cassettes follow it. Step 6 (the PPM
retro-fit, `combine`, the trunk) — NOT here, but this plan's tap finding argues it
should come next rather than last, because 29 parts are waiting on it.

**2. Placeholder scan.** No TBDs. The one place a task says "follow the worked
example" rather than reproducing a contract is Task 3 Step 4 and Task 4 Step 2 —
because `fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml` is 88 lines of measured provenance
that would be actively harmful to paste into a plan as a template, since an
implementer would then be copying another SKU's measurements into a new part. Naming
the file to read is the safer instruction, and the tasks state exactly which figures
are theirs to establish.

**3. Type consistency.** `optical.rear-kind` is the key everywhere; `rear_kind` is the
local variable in Task 2 Step 4. `lint_component_optical_rear_kind(path, data)` takes
two arguments at its definition and its registration, matching L84 and L86 which are
also purely structural. `contract(rel)` and `device(rel)` are defined once in Task 1
and used by Tasks 3-6. `P.ports(entry, load_ref)` and
`P.fibre_map(entry, load_ref, model)` keep the signatures plan 5 shipped.

**4. Known soft spots, named rather than hidden.**

- **The splice cassette is the weakest contract in the plan and the most likely to be
  wrong.** Nothing measured it, its rear part is a placeholder for a tray nobody has
  seen, and its front layout is the family arrangement rather than this SKU's. It is
  here because `splice` needs a real user, not because the corpus supports it. If
  a later intake fetches splice imagery, this contract should be remeasured before
  the other ten splice cassettes are built from it.
- **Task 2 is the only production-code change in this plan.** Everything else is
  contracts, skins and tests. That is deliberate after plan 5, where a single
  exporter change rippled into six PPM exports nobody had considered — the archetypes
  here exercise the projection rather than altering it.
- **Task 6 may falsify the front-numbering derivation.** Twelve LC adapters do not
  fit one row on a 108.97 mm face, and `_front_parts` orders by `at.x` alone. If
  57023's real arrangement is two rows, the x-order may not reproduce FS's labels —
  which plan 5's self-review predicted would surface on the second cassette. The task
  says to report it rather than renumber around it.
- **`rows.sort` is still wrong above ten rear ports** and this plan does not fix it,
  because its widest archetype has two. The 3x and 4x MTP cassettes in the bulk build
  are the first that could hit it, and the finding is recorded in plan 5's review.
- **The enclosure's four bays will need updating** as plans 7 adds cassettes, unless
  the bay `accepts` is written to a pattern rather than a list. Task 1 writes a list
  because that is what the library does today; the bulk build should revisit it rather than
  editing the list 57 times.
