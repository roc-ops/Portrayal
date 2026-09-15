# The Optical DCIM Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Project a module's fibre graph into the two DCIM targets as front and rear ports, plus a third generated artefact — the fibre map — carrying the per-instance front-to-rear bindings the device-type schema no longer holds.

**Architecture:** The exporter reads `library/dist`, never the library, so the fibre graph must reach `components.json` before anything can project it. Once it is there, `optical.capacities()` already answers "which part carries how many fibres, across this module and its rear face", and the projection is a naming layer on top of it: one rear port per rear connector, one front port per front fibre, and one fibre-map row per path leg.

**Tech Stack:** Python 3, JSON Schema (draft 2020-12), PyYAML, pytest.

**Spec:** `docs/optical-paths-design.md` — section C (the DCIM projection) and section D (what the model makes checkable). This is plan 5 of 6.

## Global Constraints

- `working/` is NEVER committed and never published. Reference imagery stays there; transcribe facts into contracts.
- Every dimension not measured is `confidence: estimated` (or `borrowed`, naming the part it came from) with provenance saying what it was derived from. **Never launder an estimate into a measurement.**
- Version bumps go in BEFORE `devicelock --update`, never after.
- **Run every gate in the FOREGROUND**, using the Bash tool's own `timeout` parameter at `600000`. Do not use `run_in_background`, the Monitor tool, TaskOutput, or a shell-level `timeout`. The suite takes about 4 minutes. The chain, in order:
  1. `python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library | tail -3`
  2. `./publish.sh --no-images`
  3. `python3 spec/tools/portrayal/devicelock.py --library library`
  4. `python3 -m pytest spec/tests -q 2>&1 | tail -5`
- Lint baseline: `LINT: ok (665 files, 1291 warnings in 22 rules)`. **The trailing number counts rules that PRODUCED a warning, not rules that exist** (`summary_line`, lint.py) — a new rule finding nothing does not move it. If the WARNING count moves, find out what started warning before continuing.
- **Adding or changing a lint rule means regenerating its docs page**: `python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md`. `test_docs_page_matches_the_generator` compares it byte for byte. Commit the page with the rule.
- Test baseline: `1524 passed, 1 skipped`. Expected totals in tasks are a GUIDE — the binding check is that nothing FAILED and the total only went up.
- Commit messages end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. No backticks in the message text: write it to a file and `git commit -F`.
- Do not dispatch subagents from inside a task.

---

## What is already established, and what blocks this

Measured before the plan was written, against `main` at `2b61aa12`. Every number
below was reproduced by running the code, not read off a docstring.

**The exporter cannot see the fibre graph at all.** `publish.sh` runs
`dcim_export.py --dist`, which "opens nothing under library/devices or
library/components" — its own comment. Everything it knows comes from
`library/dist`. `components_index.py` never mentions `optical`, so
`components.json` carries no `positions`, no `paths`, no `media` and no
`polarity` on any of the 577 entries. Nothing downstream can project what is not
published. **This is why Task 1 is first.**

**The one modelled cassette does not export, for two independent reasons.**
`find library/exports -iname '*FHD*'` returns nothing today.

1. `Dist.modules()` selects `kind == "module"`. `fs/fhd-1mtp6lcd-os2-a` declares
   `kind: component` with `class: module`, which is the two fields the wrong way
   round: every comparable Smartoptics module declares `kind: module` with a
   descriptive class (`filter`, `coupler`, `blank`). `class: module` is carried
   by exactly 2 components in the library — the two FS faces — and is read by
   nothing.
2. `Dist.manufacturer_of(ns)` learns vendors from devices. FS has no device, so
   `manufacturer_of("fs")` is `None` and `export_modules` skips the entry.

**The polish is not in the library and not in the source.** Section C's port-type
enum is `lc-upc, lc-apc, sc-upc, sc-apc, mpo, st, fc-apc, lsh-apc, mdc, splice`
— there is no bare `lc`. Nothing in the library records UPC or APC except
`common/sc-apc`, which carries it in `attrs.media`. FS's own catalogue names the
polish on 19 of its 81 rows (`FHD® Fiber Splice Cassette, LC UPC, OS2, 24
Fibers`) and **does not name one for SKU 57016**, whose row reads `FHD® MTP-12
(Male) to LC Cassette, OS2, 12 Fibers, Type A`.

**RULING (Task 3).** `optical.polish` is added to the vocabulary, L86 requires it
on any module whose connectors have a polish variant, and 57016 is recorded as
`polish: upc` with provenance saying plainly that FS names the polish where it
applies, does not name one here, and that this is the convention default rather
than a sourced fact. This is the same shape as the polarity note plan 4 landed,
and for the same reason: naming a family is not sourcing a variant. A cassette
whose catalogue row DOES name the polish takes it from there and says so.

**The manufacturer fallback changes exactly one namespace.** Adding a
`vendors.yaml` fallback to `manufacturer_of` was checked against every namespace
carrying modules:

```
casa, celestica, cisco, dell, edgecore, juniper, smartoptics, ufispace
                                     -> resolve from DEVICES, unchanged
common, std  -> None in both devices and vendors.yaml, still skipped
fs           -> None from devices, "FS.com" from vendors.yaml   <- the only change
```

**Devices must stay first and that is not incidental.** `dell` reports `Dell`
from its devices and `Dell Technologies` from vendors.yaml; `juniper` reports
`Juniper` and `Juniper Networks`; `edgecore` reports `Edgecore` and `Edgecore
Networks`. A vendors-first lookup would rename the manufacturer on several
hundred existing export files. The fallback runs only when the device lookup
returns nothing.

**`common/` and `std/` stay out for free.** Neither appears in `vendors.yaml`, so
the property `manufacturer_of` documents — "a part with no vendor is not
something a DCIM can order" — is preserved by the data rather than by a special
case.

**The index flattens faces and the optical helpers do not.** A contract spells a
face `faces: {rear: {ref: "fs/x@1"}}`; `components.json` publishes
`faces: {rear: "fs/x@1"}`, flattened deliberately to save bytes on every page
load. `optical.capacities()` calls `face_ref`, which expects the nested form. The
exporter therefore needs a small adapter (Task 1, `contract_view`) rather than a
second copy of the capacity walk — `optical.py` is the single implementation and
stays that way.

**The numbering rule the faceplate states is prose, not data.** The cassette's
`provenance.face-detail-gap` records "evens along the top, odds along the
bottom", and `provenance.parts` records "2 above 1 at the left end, 12 above 11
at the right". Nothing in the data maps `lc1.1` to the label `1`.

**RULING (Task 4).** Front ports are numbered by placement order: adapters sorted
by `at.x` across the face, and within an adapter by fibre position. For 57016
that yields `lc1.1 -> '1'`, `lc1.2 -> '2'`, ... `lc6.2 -> '12'`, which reproduces
the numbering the contract states in prose. A test asserts that reproduction, so
the derivation is checked against the vendor's own labelling rather than assumed
to match it.

**Rear port naming follows the spec's own example.** Section C's sample rows say
`rear: MTP-1`. The part id is `mtp`, so the rule is the part id uppercased with a
1-based ordinal suffix within its face.

**There is no schema validation of the exports in this repo.** `spec/schemas/`
holds component, device and overlay schemas only, and no test validates an
exported module-type against NetBox's or Nautobot's own schema. Task 6's sweeps
are therefore the only thing checking the projection, which is why they check the
graph against the ports rather than merely that files exist.

---

## File Structure

| file | responsibility |
|---|---|
| `spec/tools/portrayal/components_index.py` | MODIFY — publish `optical` on an index entry |
| `spec/tools/portrayal/artifacts.py` | MODIFY — `manufacturer_of` falls back to vendors.yaml |
| `spec/tools/portrayal/optical_ports.py` | CREATE — the projection: families, port types, port names, fibre-map rows. Pure functions over an index entry; no I/O, no YAML, no paths |
| `spec/tools/portrayal/dcim_export.py` | MODIFY — `contract_view`, front/rear ports in `build_module`, and the fibre-map writer |
| `spec/tools/portrayal/lint.py` | MODIFY — L86 (polish stated) |
| `spec/schemas/component.schema.json` | MODIFY — `optical.polish` |
| `library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml` | MODIFY — `kind`, `class`, `optical.polish` + provenance |
| `library/components/fs/fhd-1mtp6lcd-rear/v1/contract.yaml` | MODIFY — `class` |
| `spec/tests/test_optical_ports.py` | CREATE — unit tests for the projection |
| `spec/tests/test_optical_export.py` | CREATE — section D's sweeps over the built exports |

`optical_ports.py` is a new file rather than more of `dcim_export.py` because
`dcim_export.py` is already 900+ lines and the projection is the one part of this
work that is pure and worth unit-testing without building anything. Files that
change together live together: the naming rules, the type table and the row
builder are one responsibility and move as one.

---

### Task 1: The fibre graph reaches the build

**Files:**
- Modify: `spec/tools/portrayal/components_index.py`
- Modify: `spec/tools/portrayal/dcim_export.py` (add `contract_view`)
- Test: `spec/tests/test_optical_export.py` (create)

**Interfaces:**
- Produces: `components.json` entries carry `optical` verbatim when the contract
  has one, omitted otherwise. `dcim_export.contract_view(entry)` returns a dict
  shaped the way `optical.capacities` expects.

- [ ] **Step 1: Write the failing test**

Create `spec/tests/test_optical_export.py`:

```python
"""The optical projection, checked against the built artefacts.

These read library/dist and library/exports rather than the contracts, because
what a DCIM consumes is the build - and the build is where the fibre graph was
missing entirely until this plan.
"""
import json
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
EXPORTS = ROOT / "library" / "exports"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import optical as O  # noqa: E402


def index():
    f = DIST / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    return {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
            for e in json.loads(f.read_text())["components"]}


def test_the_index_carries_a_connectors_positions():
    """Without this the exporter cannot count a single fibre."""
    idx = index()
    mpo = idx["common/mpo-adapter@1"]
    assert (mpo.get("optical") or {}).get("positions") == 12


def test_the_index_carries_a_modules_paths():
    idx = index()
    c = idx["fs/fhd-1mtp6lcd-os2-a@1"]
    opt = c.get("optical") or {}
    assert opt.get("media") == "os2"
    assert len(opt.get("paths") or []) == 12


def test_an_entry_with_no_optical_omits_the_key():
    """700-odd entries are not fibre; an empty dict on each is bytes for nothing."""
    idx = index()
    assert "optical" not in idx["std/pcie-bracket-fh@1"]


def test_capacities_answers_from_the_built_index():
    """The index flattens `faces` and the optical helpers do not.

    `contract_view` is the adapter. If it stops being applied, this is what
    notices - the rear face's twelve positions simply vanish from the answer.
    """
    import dcim_export as D
    idx = index()
    caps = O.capacities(D.contract_view(idx["fs/fhd-1mtp6lcd-os2-a@1"]),
                        lambda ref: idx.get(ref))
    assert caps == {"lc1": 2, "lc2": 2, "lc3": 2, "lc4": 2, "lc5": 2, "lc6": 2,
                    "rear:mtp": 12}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_optical_export.py -q`
Expected: FAIL — the first three on `KeyError`/assertion because `optical` is
absent from every entry, the fourth on `AttributeError: module 'dcim_export' has
no attribute 'contract_view'`.

- [ ] **Step 3: Publish `optical` on the index entry**

In `spec/tools/portrayal/components_index.py`, beside the `faces` block added by
plan 3:

```python
            # THE FIBRE GRAPH, VERBATIM. The exporter reads this file and never
            # the library - `dcim_export.py --dist` opens nothing under
            # library/components - so a contract's `optical` is invisible to the
            # projection until it is published here. Carried whole rather than
            # summarised: `positions` is what a connector contributes, and
            # `paths`, `media`, `polarity` and `unused` are what a module's
            # projection is built from, so a reduced form would only have to be
            # widened again by the first consumer that wanted the rest.
            if data.get("optical"):
                entry["optical"] = data["optical"]
```

- [ ] **Step 4: Add the adapter in `dcim_export.py`**

Near the other helpers, before `build_module`:

```python
def contract_view(entry):
    """An index entry in the shape `optical.py` expects.

    components.json FLATTENS a face to its ref - `faces: {rear: "fs/x@1"}` -
    because the viewer resolves it against this same index and the nested form
    would cost bytes on every page load. `optical.capacities` goes through
    `face_ref`, which reads the contract's nested `{ref: ...}`. Re-nesting here
    is four lines; teaching the accessor to accept two shapes would put the
    difference into the one place that exists to hide it.
    """
    faces = {k: {"ref": v} for k, v in (entry.get("faces") or {}).items()}
    return {"parts": entry.get("parts") or [],
            "faces": faces,
            "optical": entry.get("optical") or {}}
```

- [ ] **Step 5: Run the tests**

Run: `python3 -m pytest spec/tests/test_optical_export.py -q`
Expected: PASS (4 passed), after `./publish.sh --no-images` has rebuilt dist.

- [ ] **Step 6: Run the gate chain**

Expected: lint unmoved at `665 files, 1291 warnings in 22 rules`; devicelock 0;
tests up by 4. `components.json` grows by one key on the fibre entries only.

- [ ] **Step 7: Commit**

---

### Task 2: The cassette becomes a module the exporter can see

**Files:**
- Modify: `library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml`
- Modify: `library/components/fs/fhd-1mtp6lcd-rear/v1/contract.yaml`
- Modify: `spec/tools/portrayal/artifacts.py`
- Test: `spec/tests/test_optical_export.py` (append)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `fs/fhd-1mtp6lcd-os2-a@1` appears in `Dist.modules()`;
  `Dist.manufacturer_of("fs")` returns `"FS.com"`.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_optical_export.py`:

```python
def test_the_cassette_is_an_orderable_module():
    """`kind` says whether it is orderable; `class` says what it is.

    The cassette declared `kind: component` with `class: module`, which is the
    two fields the wrong way round - every Smartoptics module declares
    `kind: module` with a descriptive class. The cost was silent: `Dist.modules()`
    selects on `kind`, so the part simply never reached the exporter.
    """
    idx = index()
    c = idx["fs/fhd-1mtp6lcd-os2-a@1"]
    assert c["kind"] == "module"
    assert c["class"] != "module", "`class: module` says nothing; name the thing"


def test_the_rear_face_is_not_separately_orderable():
    """A face is a drawing of the part, not a second product to order."""
    idx = index()
    assert idx["fs/fhd-1mtp6lcd-rear@1"]["kind"] == "component"


def test_a_vendor_with_no_device_can_still_ship_modules():
    import sys as _s
    _s.path.insert(0, str(ROOT / "spec/tools/portrayal"))
    from artifacts import Dist
    d = Dist(str(DIST))
    assert d.manufacturer_of("fs") == "FS.com"


def test_the_device_lookup_still_wins_over_the_registry():
    """NOT incidental. `dell` reports `Dell` from its devices and `Dell
    Technologies` from vendors.yaml; `juniper` and `edgecore` differ the same
    way. A vendors-first lookup would rename the manufacturer on several hundred
    existing export files."""
    from artifacts import Dist
    d = Dist(str(DIST))
    assert d.manufacturer_of("dell") == "Dell"
    assert d.manufacturer_of("juniper") == "Juniper"


def test_a_namespace_with_no_vendor_is_still_not_orderable():
    """`common/` and `std/` are absent from vendors.yaml, so the property
    `manufacturer_of` documents holds by data rather than by a special case."""
    from artifacts import Dist
    d = Dist(str(DIST))
    assert d.manufacturer_of("common") is None
    assert d.manufacturer_of("std") is None
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_optical_export.py -q`
Expected: FAIL on `kind == "module"` and on `manufacturer_of("fs")`; the
`dell`/`juniper`/`common`/`std` assertions pass already and must keep passing.

- [ ] **Step 3: Fix the two contracts**

In `library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml`:

```yaml
kind: module
class: cassette
```

In `library/components/fs/fhd-1mtp6lcd-rear/v1/contract.yaml`, the rear stays a
component — it is a face, not a second orderable product — and only its class
changes:

```yaml
kind: component
class: cassette
```

- [ ] **Step 4: Add the fallback in `artifacts.py`**

Replace `manufacturer_of`:

```python
    def manufacturer_of(self, ns):
        """Which manufacturer ships a namespace.

        LEARNED FROM THE DEVICES FIRST, and that order is load-bearing rather
        than incidental: `dell` reports `Dell` from its devices and `Dell
        Technologies` from vendors.yaml, `juniper` reports `Juniper` against
        `Juniper Networks`, `edgecore` the same way. Looking in the registry
        first would rename the manufacturer on several hundred existing export
        files.

        THE REGISTRY IS THE FALLBACK, for a vendor that ships parts before it
        ships a chassis - FS sells cassettes that seat in an enclosure nothing
        has modelled yet, and requiring a device first is an accident of how
        this join was built rather than a statement about what is orderable.
        `common/` and `std/` stay absent because they are absent from
        vendors.yaml, so the rule this docstring used to state as a special case
        now holds by data.
        """
        for d in self._devices:
            if d.get("ns") == ns:
                return d.get("manufacturer")
        return (self.vendors.get(ns) or {}).get("display") or None
```

- [ ] **Step 5: Run the tests and the gate chain**

Run the full chain. Expected: lint unmoved; `publish.sh` now writes two new
files, `library/exports/{netbox,nautobot}/module-types/FS.com/FHD-1MTP6LCDOS2A.yaml`;
devicelock 0; tests up by 5.

**Check the export count moved by exactly two.** `publish.sh` prints
`exported N documents`; N was 964 and must now be 966. If it moved by more, a
namespace you did not intend started resolving — find out which before
continuing.

- [ ] **Step 6: Commit**

---

### Task 3: `optical.polish`, and the rule that it is stated

**Files:**
- Modify: `spec/schemas/component.schema.json`
- Modify: `spec/tools/portrayal/lint.py`
- Modify: `docs/lint-rules.md` (regenerate)
- Modify: `library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml`
- Test: `spec/tests/test_optical_ports.py` (create)

**Interfaces:**
- Produces: `optical.polish` with enum `["upc", "apc"]`; lint rule **L86**;
  `optical_ports.POLISHED` naming the families that have a variant.

- [ ] **Step 1: Write the failing test**

Create `spec/tests/test_optical_ports.py`:

```python
"""The projection from a fibre graph to DCIM ports.

Pure functions over an index entry - no I/O here, so these run without a build.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import lint as L  # noqa: E402
import optical_ports as P  # noqa: E402

LIB = [str(ROOT / "library")]


def run86(doc, path="t/contract.yaml"):
    L.ERRORS.clear()
    L.lint_component_optical_polish(path, doc)
    return [e for e in L.ERRORS if "[L86]" in e]


def test_a_polished_family_needs_a_polish():
    """An LC adapter is sold UPC and APC and the enum has no bare `lc`."""
    doc = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@1"}],
           "optical": {"paths": [{"from": "lc1.1", "to": "lc1.2"}]}}
    got = run86(doc)
    assert len(got) == 1, got
    assert "polish" in got[0]


def test_stating_the_polish_is_quiet():
    doc = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@1"}],
           "optical": {"polish": "upc",
                       "paths": [{"from": "lc1.1", "to": "lc1.2"}]}}
    assert run86(doc) == []


def test_an_unpolished_family_needs_nothing():
    """MPO, ST, MDC and splice have one form in the enum, so there is nothing
    for a contract to state and demanding it would be noise."""
    doc = {"parts": [{"id": "mtp", "ref": "common/mpo-adapter@1"}],
           "optical": {"paths": [{"from": "mtp.1", "to": "mtp.2"}]}}
    assert run86(doc) == []


def test_a_module_with_no_paths_is_not_this_rules_business():
    assert run86({"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@1"}]}) == []


def test_the_real_cassette_states_its_polish():
    c = yaml.safe_load(
        (ROOT / "library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml").read_text())
    assert (c["optical"]).get("polish") == "upc"
    assert run86(c) == []


def test_the_cassettes_polish_is_marked_as_the_assumption_it_is():
    """FS names the polish on 19 of its 81 catalogue rows and does NOT name one
    for 57016. Recording `upc` is the convention default, not a sourced fact,
    and the contract has to say which - the same distinction plan 4 drew for the
    polarity map."""
    c = yaml.safe_load(
        (ROOT / "library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml").read_text())
    note = (c.get("provenance") or {}).get("optical") or ""
    assert "polish" in note.lower(), "provenance says nothing about the polish"
    assert "ASSUM" in note.upper() or "not name" in note.lower(), \
        "the polish must be marked as an assumption, not stated flatly"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_optical_ports.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'optical_ports'`.

- [ ] **Step 3: Create `optical_ports.py` with the family tables**

Create `spec/tools/portrayal/optical_ports.py`:

```python
"""A module's fibre graph, projected into DCIM ports and fibre-map rows.

PURE. Everything here takes an index entry and returns data; nothing opens a
file or writes one. That is what lets the projection be unit-tested without a
build, and it is why the naming rules live here rather than inside
`dcim_export.py`, which is already 900 lines of I/O.

See docs/optical-paths-design.md section C.
"""

# WHICH CONNECTOR FAMILY EACH PART IS. The ref is the fact; the family is what
# the port-type enum is keyed on. A part absent from this table carries no
# fibre as far as the projection is concerned, which is the same answer
# `optical.capacities` gives for a part with no `optical.positions`.
FAMILY = {
    "common/lc-duplex-adapter": "lc",
    "common/lc-duplex-v-adapter": "lc",
    "common/sc-duplex-adapter": "sc",
    "common/mpo-adapter": "mpo",
    "common/st-simplex-adapter": "st",
    "common/fc-simplex-adapter": "fc",
    "common/lsh-simplex-adapter": "lsh",
    "common/mdc-adapter": "mdc",
}

# WHICH FAMILIES THE ENUM SPELLS TWO WAYS. Section C's enum is `lc-upc, lc-apc,
# sc-upc, sc-apc, mpo, st, fc-apc, lsh-apc, mdc, splice`. So `lc` and `sc` need
# a polish to name a type at all; `fc` and `lsh` appear only as APC, and the
# rest have one form. A contract states the polish only where it changes the
# answer - demanding it everywhere would be noise, and inventing it where the
# enum has no second form would be a fact nobody asked for.
POLISHED = ("lc", "sc")
FIXED_POLISH = {"fc": "apc", "lsh": "apc"}


def family_of(ref):
    """`common/mpo-adapter@1` -> `mpo`, or None for a part that is not fibre."""
    return FAMILY.get(str(ref).split("@")[0])


def port_type(family, polish):
    """The DCIM port type for a family, or None when the family is unknown."""
    if family is None:
        return None
    if family in POLISHED:
        return f"{family}-{polish}" if polish else None
    if family in FIXED_POLISH:
        return f"{family}-{FIXED_POLISH[family]}"
    return family
```

- [ ] **Step 4: Add `polish` to the schema**

In `spec/schemas/component.schema.json`, inside `properties.optical.properties`,
beside `polarity`:

```json
   "polish": {
    "enum": ["upc", "apc"],
    "description": "THE FERRULE END FACE, where the port-type enum spells a family two ways. `lc` and `sc` have both a `-upc` and an `-apc` form and cannot name a type without this; `fc` and `lsh` appear only as APC; `mpo`, `st`, `mdc` and `splice` have one form and want nothing here. L86 asks for it exactly where it changes the answer. It is a claim about the connector this module presents, not about the glass - `media` is the glass."
   },
```

- [ ] **Step 5: Add L86**

In `spec/tools/portrayal/lint.py`, add to `RULES` beside L85:

```python
    "L86": ("component",  "a module composing a connector the enum spells two ways states its polish", "add `optical.polish: upc` or `apc`, and say in provenance where it came from"),
```

Add `import optical_ports` beside lint.py's existing `import optical`, then,
beside the other optical rules:

```python
def lint_component_optical_polish(path, data):
    """L86: a module states the polish where the port type depends on it.

    Section C's enum has `lc-upc` and `lc-apc` and no bare `lc`, so a cassette
    composing LC adapters cannot be projected at all without this. It is asked
    for ONLY where it changes the answer: `mpo`, `st`, `mdc` and `splice` have
    one form each, and `fc` and `lsh` appear only as APC, so demanding a polish
    on those would be a field with one legal value.

    A polish is a CLAIM and belongs in provenance like any other. FS names it on
    19 of its 81 catalogue rows and leaves it unstated on the rest, so the note
    matters: `upc` by convention and `upc` because the vendor said so are
    different facts, and only one of them survives a correction.
    """
    if not isinstance(data, dict):
        return
    opt = data.get("optical") or {}
    if not (opt.get("paths") or []):
        return
    if opt.get("polish"):
        return
    for part in (data.get("parts") or []):
        if not isinstance(part, dict):
            continue
        fam = optical_ports.family_of(part.get("ref") or "")
        if fam in optical_ports.POLISHED:
            err(path, "L86",
                f"composes {part.get('ref')}, whose port type is spelled "
                f"{fam}-upc or {fam}-apc, but states no `optical.polish` - so "
                "there is no type to export. Add it, and say in provenance "
                "whether the vendor named it or it is the convention default")
            return
```

Register it in `main()` beside `lint_component_optical_face_capacity`:

```python
                lint_component_optical_polish(f, d)
```

- [ ] **Step 6: Record the polish on the cassette**

In `library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml`, add to the
`optical:` block:

```yaml
  polish: upc
```

and append to `provenance.optical`, after the polarity paragraph:

```
    THE POLISH IS THE SAME KIND OF ASSUMPTION AND IS MARKED THE SAME WAY. FS's
    catalogue names the polish where it applies - 19 of its 81 rows read "LC
    UPC" or "LC APC", including four other FHD cassettes - and SKU 57016's row
    does not: it reads "FHD MTP-12 (Male) to LC Cassette, OS2, 12 Fibers, Type
    A" and stops. `polish: upc` is therefore the convention for an OS2 cassette
    with no APC stated, not a fact read off FS's own description of this part.
    An APC variant of the same cassette would be a different SKU and FS would
    say so; that is the evidence for the default rather than a source for it.
    A catalogue row, a datasheet, or a green ferrule in a face-on photograph
    settles it.
```

- [ ] **Step 7: Regenerate the lint rules page and run everything**

```bash
python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md
```

Run the gate chain. Expected: lint `665 files, 1291 warnings in 22 rules` —
unmoved, because the one module with paths now states its polish. Tests up by 6.

- [ ] **Step 8: Commit**

---

### Task 4: Front and rear ports on the module type

**Files:**
- Modify: `spec/tools/portrayal/optical_ports.py`
- Modify: `spec/tools/portrayal/dcim_export.py`
- Test: `spec/tests/test_optical_ports.py` (append)

**Interfaces:**
- Consumes: `contract_view` (Task 1), `family_of`/`port_type` (Task 3).
- Produces: `optical_ports.ports(entry, load_ref)` returning
  `{"front": [...], "rear": [...]}`, each a list of
  `{"name": str, "type": str, "positions": int}`;
  `optical_ports.rear_port_names(entry, load_ref)` returning `{part id: port
  name}`; and
  `optical_ports.front_label(entry, endpoint, load_ref)` returning the vendor
  number as a string.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_optical_ports.py`:

```python
def cassette_entry():
    """The real cassette and its rear, as the index publishes them."""
    import json
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    idx = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
           for e in json.loads(f.read_text())["components"]}
    return idx["fs/fhd-1mtp6lcd-os2-a@1"], idx


def test_the_rear_mtp_is_one_port_with_twelve_positions():
    """C1: a rear MPO-12 exports as ONE rear port, not twelve."""
    import dcim_export as D
    e, idx = cassette_entry()
    got = P.ports(D.contract_view(e), idx.get)
    assert got["rear"] == [{"name": "MTP-1", "type": "mpo", "positions": 12}]


def test_every_front_fibre_is_its_own_port():
    """C1: per-fibre granularity is what makes the projection lossless for the
    22 breakouts, 4 conversions and 4 mesh cassettes."""
    import dcim_export as D
    e, idx = cassette_entry()
    got = P.ports(D.contract_view(e), idx.get)
    assert len(got["front"]) == 12
    assert got["front"][0] == {"name": "1", "type": "lc-upc", "positions": 1}
    assert got["front"][-1] == {"name": "12", "type": "lc-upc", "positions": 1}


def test_the_front_numbering_reproduces_the_faceplate():
    """The DERIVATION is placement order; the faceplate is the check on it.

    The contract records the numbering only in prose - "2 above 1 at the left
    end, 12 above 11 at the right" - so the projection derives it from the
    adapters' x order and each adapter's fibre positions. This asserts the
    derivation lands where the vendor's labels do: adapter lc1 carries 1 and 2,
    lc6 carries 11 and 12.
    """
    import dcim_export as D
    e, idx = cassette_entry()
    view = D.contract_view(e)
    assert P.front_label(view, "lc1.1", idx.get) == "1"
    assert P.front_label(view, "lc1.2", idx.get) == "2"
    assert P.front_label(view, "lc6.1", idx.get) == "11"
    assert P.front_label(view, "lc6.2", idx.get) == "12"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_optical_ports.py -q`
Expected: FAIL — `AttributeError: module 'optical_ports' has no attribute 'ports'`.

- [ ] **Step 3: Implement the projection**

Append to `spec/tools/portrayal/optical_ports.py`:

```python
import optical


def _front_parts(entry):
    """This module's own fibre parts, left to right.

    ORDER IS THE NUMBERING. The faceplate's labels are recorded in the
    cassette's provenance as prose and nowhere in the data, so the projection
    derives them: adapters across the face by `at.x`, and within an adapter by
    fibre position. A test checks that derivation against the numbering the
    contract states, rather than trusting that they agree.
    """
    out = []
    for part in (entry.get("parts") or []):
        if not isinstance(part, dict) or not part.get("id"):
            continue
        if family_of(part.get("ref") or "") is None:
            continue
        at = part.get("at") or [0, 0]
        out.append((float(at[0]), str(part["id"]), part["ref"]))
    return sorted(out)


def front_label(entry, endpoint, load_ref):
    """The vendor's number for a front endpoint, as a string.

    `load_ref` IS NOT OPTIONAL. `capacities` learns a connector's width by
    resolving its ref, so a lookup that answers None makes every width zero and
    every label off by the whole face - silently, because the result is still a
    plausible string.
    """
    face, part, pos = optical.split_endpoint(endpoint)
    if face:
        return None                      # a rear endpoint has no front label
    caps = optical.capacities(entry, load_ref)
    n = 0
    for _x, pid, ref in _front_parts(entry):
        width = caps.get(pid) or 0
        if pid == part:
            return str(n + pos)
        n += width
    return None


def ports(entry, load_ref):
    """`{"front": [...], "rear": [...]}` for one module entry.

    A REAR CONNECTOR IS ONE PORT CARRYING MANY POSITIONS; a front fibre is one
    port carrying one. That asymmetry is section C1, and it is what makes the
    projection lossless for a cassette whose front and rear do not correspond
    one to one.
    """
    caps = optical.capacities(entry, load_ref)
    polish = (entry.get("optical") or {}).get("polish")

    front, n = [], 0
    for _x, pid, ref in _front_parts(entry):
        t = port_type(family_of(ref), polish)
        for i in range(1, (caps.get(pid) or 0) + 1):
            n += 1
            front.append({"name": str(n), "type": t, "positions": 1})

    rear = []
    names = rear_port_names(entry, load_ref)
    for key in sorted(k for k in caps if ":" in k):
        face, pid = key.split(":", 1)
        ref = _face_part_ref(entry, face, pid, load_ref)
        rear.append({"name": names[pid], "type": port_type(family_of(ref), polish),
                     "positions": caps[key]})
    return {"front": front, "rear": rear}


def rear_port_names(entry, load_ref):
    """`{part id: port name}` for this module's rear connectors.

    BUILT ONCE AND SHARED, because the fibre map needs the same mapping and the
    obvious way to get it there - splitting the port name back on "-" - is wrong
    for a part id that contains one. `optical.py`'s own docstring uses `mtp-1.3`
    as its example endpoint, so hyphenated ids are not hypothetical, and
    `"MTP-1-1".split("-")[0]` recovers `mtp` rather than `mtp-1`: every row for
    such a part would name a rear port that does not exist.
    """
    caps = optical.capacities(entry, load_ref)
    out, seen = {}, {}
    for key in sorted(k for k in caps if ":" in k):
        pid = key.split(":", 1)[1]
        seen[pid] = seen.get(pid, 0) + 1
        out[pid] = f"{pid.upper()}-{seen[pid]}"
    return out


def _face_part_ref(entry, face, pid, load_ref):
    """The component ref of a part drawn on one of this module's faces."""
    ref = ((entry.get("faces") or {}).get(face) or {}).get("ref")
    doc = load_ref(ref) if ref else None
    for part in ((doc or {}).get("parts") or []):
        if isinstance(part, dict) and str(part.get("id")) == pid:
            return part.get("ref")
    return None
```

- [ ] **Step 4: Emit them from `build_module`**

In `spec/tools/portrayal/dcim_export.py`, inside `build_module`, after the
`powers` block and before the `body` block:

```python
    # THE GLASS, IF THIS MODULE CARRIES ANY. A fibre cassette has no interfaces
    # in the DCIM sense - nothing terminates electrically - so these are its
    # entire port list, and a module with no `optical` adds nothing here.
    if (contract.get("optical") or {}).get("paths"):
        fibre = optical_ports.ports(contract_view(contract), load_ref)
        if fibre["rear"]:
            out["rear-ports"] = fibre["rear"]
        if fibre["front"]:
            out["front-ports"] = fibre["front"]
```

Add `import optical_ports` to dcim_export.py's module-level imports, beside its
existing ones — not inside the function.

`load_ref` IS A PARAMETER, not a global. `build_module` is called from
`export_modules`, which holds the `dist`: change the signature to
`build_module(contract, manufacturer, load_ref=None)`, pass
`dist.component_by_ref` from `export_modules`, and default it to
`lambda _r: None` inside the function so the existing callers keep working
unchanged. A module with no `optical.paths` never reaches the lookup, so the
default is never exercised by a fibre part. Add the accessor to `artifacts.py`:

```python
    def component_by_ref(self, ref):
        """`common/mpo-adapter@1` -> its index entry, or None."""
        if not hasattr(self, "_by_ref"):
            self._by_ref = {
                f"{c.get('ns')}/{c.get('name')}@{str(c.get('major') or '')[1:]}": c
                for c in self._components}
        return self._by_ref.get(ref)
```

- [ ] **Step 5: Run the tests and the gate chain**

Expected: the two module-type files now carry `rear-ports` with one `mpo` entry
of 12 positions and `front-ports` with twelve `lc-upc` entries of 1. Tests up
by 4. Lint unmoved.

- [ ] **Step 6: Commit**

---

### Task 5: The fibre map, the third export

**Files:**
- Modify: `spec/tools/portrayal/optical_ports.py`
- Modify: `spec/tools/portrayal/dcim_export.py`
- Modify: `publish.sh` (the export count line only)
- Test: `spec/tests/test_optical_ports.py`, `spec/tests/test_optical_export.py`

**Interfaces:**
- Consumes: `ports`, `front_label`.
- Produces: `optical_ports.fibre_map(entry, load_ref, model)` returning
  `{"model", "media", "polarity", "rows"}`; files at
  `library/exports/fibre-maps/<Manufacturer>/<Model>.yaml`.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_optical_ports.py`:

```python
def test_the_fibre_map_carries_one_row_per_leg():
    import dcim_export as D
    e, idx = cassette_entry()
    m = P.fibre_map(D.contract_view(e), idx.get, "FHD-1MTP6LCDOS2A")
    assert m["model"] == "FHD-1MTP6LCDOS2A"
    assert m["media"] == "os2"
    assert m["polarity"] == "a"
    assert len(m["rows"]) == 12
    assert m["rows"][0] == {"front": "1", "front_position": 1,
                            "rear": "MTP-1", "rear_position": 1}
    assert m["rows"][-1] == {"front": "12", "front_position": 1,
                             "rear": "MTP-1", "rear_position": 12}


def test_a_split_carries_its_ratio():
    """C3: the ratio has no field in the type format, so it rides the map.

    Built here rather than read from the library, because no modelled part
    splits yet - the taps arrive in plan 6, and a rule with no test until then
    is a rule nobody has run.
    """
    entry = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@1",
                        "at": [0, 0]}],
             "faces": {"rear": {"ref": "t/rear@1"}},
             "optical": {"media": "os2", "polish": "upc",
                         "paths": [{"from": "rear:mtp.1",
                                    "to": [{"at": "lc1.1", "ratio": 50},
                                           {"at": "lc1.2", "ratio": 50}]}]}}
    known = {"common/lc-duplex-v-adapter@1": {"optical": {"positions": 2}},
             "common/mpo-adapter@1": {"optical": {"positions": 12}},
             "t/rear@1": {"parts": [{"id": "mtp", "ref": "common/mpo-adapter@1"}]}}
    m = P.fibre_map(entry, known.get, "TAP")
    assert len(m["rows"]) == 2
    assert all(r["ratio"] == 50 for r in m["rows"])
    assert {r["front"] for r in m["rows"]} == {"1", "2"}
```

- [ ] **Step 2: Run it to verify it fails**

Expected: `AttributeError: module 'optical_ports' has no attribute 'fibre_map'`.

- [ ] **Step 3: Implement `fibre_map`**

Append to `optical_ports.py`:

```python
def fibre_map(entry, load_ref, model):
    """The per-instance front-to-rear bindings, as a flat row list.

    THE DEVICE-TYPE YAML NO LONGER CARRIES THIS. netbox#20564 replaced the
    FrontPort->RearPort FK with a bidirectional M2M, and the front-port schema
    is `{name, type, positions}` with `additionalProperties: false` and no
    `rear_port` key - so the mapping has nowhere to live in the type format and
    ships beside it instead.

    THERE IS NO UPSTREAM SCHEMA FOR THIS ARTEFACT, so this defines one. It is
    generated only and never hand-edited, which keeps the contracts the single
    source; and it is deliberately boring - a flat row list, no nesting - so
    feeding it to a script or an API is a five-line job.
    """
    opt = entry.get("optical") or {}
    rear_name = rear_port_names(entry, load_ref)

    rows = []
    for path in (opt.get("paths") or []):
        legs = optical.endpoints(path)
        src, _ = legs[0]
        for dst, ratio in legs[1:]:
            rows.append(_row(entry, src, dst, ratio, rear_name, load_ref))
    rows = [r for r in rows if r]
    rows.sort(key=lambda r: (r["rear"], r["rear_position"]))
    out = {"model": model}
    if opt.get("media"):
        out["media"] = opt["media"]
    if opt.get("polarity"):
        out["polarity"] = opt["polarity"]
    out["rows"] = rows
    return out


def _row(entry, a, b, ratio, rear_name, load_ref):
    """One leg as a row, whichever end of it is the rear."""
    fa, pa, na = optical.split_endpoint(a)
    fb, pb, nb = optical.split_endpoint(b)
    if fa and not fb:
        rear_ep, front_ep = (fa, pa, na), (fb, pb, nb)
    elif fb and not fa:
        rear_ep, front_ep = (fb, pb, nb), (fa, pa, na)
    else:
        return None                      # front-to-front or rear-to-rear
    _f, rpid, rpos = rear_ep
    _g, _fpid, _fpos = front_ep
    label = front_label(entry, f"{_fpid}.{_fpos}", load_ref)
    row = {"front": label, "front_position": 1,
           "rear": rear_name.get(rpid, rpid.upper()), "rear_position": rpos}
    if ratio is not None:
        row["ratio"] = ratio
    return row
```

- [ ] **Step 4: Write the files**

In `dcim_export.py`, in `export_modules`, after the module type is written:

```python
        if (contract.get("optical") or {}).get("paths"):
            m = optical_ports.fibre_map(contract_view(contract),
                                        dist.component_by_ref, doc["model"])
            d = Path(root) / "fibre-maps" / man
            d.mkdir(parents=True, exist_ok=True)
            (d / (doc["model"].replace("/", "-") + ".yaml")).write_text(
                "---\n" + yaml.dump(m, Dumper=Indented, sort_keys=False,
                                    width=100, default_flow_style=False))
```

The fibre map sits beside `netbox/` and `nautobot/` rather than inside either,
because it is not a document of either schema — it is the artefact this project
defines, and both targets consume the same rows.

- [ ] **Step 5: Append the built-artefact test**

Append to `spec/tests/test_optical_export.py`:

```python
def test_the_fibre_map_is_published_beside_the_two_targets():
    f = EXPORTS / "fibre-maps" / "FS.com" / "FHD-1MTP6LCDOS2A.yaml"
    if not EXPORTS.exists():
        pytest.skip("library/exports not built - run ./publish.sh --no-images")
    assert f.exists(), "no fibre map for the one cassette that has fibres"
    m = yaml.safe_load(f.read_text())
    assert len(m["rows"]) == 12
```

- [ ] **Step 6: Run the gate chain**

`publish.sh`'s final line counts `library/exports -name '*.yaml'`; it will now
include the fibre maps, so the printed total rises by one per fibre module.
Expected 967 after Task 5 (964 + 2 module types + 1 fibre map).

- [ ] **Step 7: Commit**

---

### Task 6: Section D's sweeps

**Files:**
- Test: `spec/tests/test_optical_export.py` (append)

**Interfaces:**
- Consumes: everything above. Produces no code — this task is the check that the
  projection agrees with the graph across the whole library, now and as the 62
  cassettes arrive in plan 6.

- [ ] **Step 1: Write the sweeps**

Append to `spec/tests/test_optical_export.py`:

```python
def fibre_modules(idx):
    return [e for e in idx.values()
            if (e.get("optical") or {}).get("paths") and e.get("kind") == "module"]


def test_the_sweep_finds_fibre_modules_at_all():
    """Guard the guard: every sweep below passes vacuously on an empty list."""
    assert fibre_modules(index()), "no fibre modules found - the sweeps are vacuous"


def test_every_fibre_module_exports_ports_matching_its_graph():
    """Section D: the count a module exports equals the count its graph carries."""
    import dcim_export as D
    import optical_ports as P
    idx = index()
    for e in fibre_modules(idx):
        view = D.contract_view(e)
        caps = O.capacities(view, idx.get)
        got = P.ports(view, idx.get)
        front_fibres = sum(n for k, n in caps.items() if ":" not in k)
        rear_fibres = sum(n for k, n in caps.items() if ":" in k)
        assert len(got["front"]) == front_fibres, e["name"]
        assert sum(p["positions"] for p in got["rear"]) == rear_fibres, e["name"]


def test_every_fibre_map_row_names_ports_that_exist():
    """Section D: a row pointing at a port nobody exported is a silent drop."""
    import dcim_export as D
    import optical_ports as P
    idx = index()
    for e in fibre_modules(idx):
        view = D.contract_view(e)
        model = str((e.get("attrs") or {}).get("model") or e["name"])
        got = P.ports(view, idx.get)
        m = P.fibre_map(view, idx.get, model)
        fronts = {p["name"] for p in got["front"]}
        rears = {p["name"] for p in got["rear"]}
        for r in m["rows"]:
            assert r["front"] in fronts, f"{model}: front {r['front']!r}"
            assert r["rear"] in rears, f"{model}: rear {r['rear']!r}"


def test_no_exported_front_port_is_left_without_a_rear_port():
    """Section D, and netbox#21830: we do not get to omit rear ports."""
    import dcim_export as D
    import optical_ports as P
    idx = index()
    for e in fibre_modules(idx):
        view = D.contract_view(e)
        model = str((e.get("attrs") or {}).get("model") or e["name"])
        got = P.ports(view, idx.get)
        m = P.fibre_map(view, idx.get, model)
        bound = {r["front"] for r in m["rows"]}
        orphans = sorted({p["name"] for p in got["front"]} - bound)
        assert not orphans, f"{model}: front ports bound to nothing: {orphans}"


def test_every_vendor_fibre_module_actually_reaches_the_exports():
    """The failure that started this plan was SILENT.

    The cassette modelled in plan 4 exported nothing at all, because `kind` and
    `class` were the wrong way round and FS had no device to learn a
    manufacturer from. Nothing noticed: the gates were green, the file simply
    did not exist. This is what notices next time.
    """
    if not EXPORTS.exists():
        pytest.skip("library/exports not built - run ./publish.sh --no-images")
    idx = index()
    missing = []
    for e in fibre_modules(idx):
        if e.get("ns") in ("common", "std"):
            continue
        model = str((e.get("attrs") or {}).get("model") or e["name"])
        hits = list((EXPORTS / "netbox" / "module-types").rglob(
            model.replace("/", "-") + ".yaml"))
        if not hits:
            missing.append(model)
    assert not missing, f"modelled, has fibres, exports nothing: {missing}"
```

- [ ] **Step 2: Run them**

Run: `python3 -m pytest spec/tests/test_optical_export.py -q`
Expected: PASS. If `test_the_sweep_finds_fibre_modules_at_all` fails, stop —
every other sweep in the file is passing for the wrong reason.

- [ ] **Step 3: Close the settled open question in the spec**

`docs/optical-paths-design.md`'s "Open questions" still opens with **The LC
pitch**, which plan 4 settled: `fhd-lc-cassette` in `standards.yaml` records the
measured 12.92 floor off SKU 57016, and `common/lc-duplex-v-adapter@1` is the
9.28-wide stacked part FS actually uses, so the 13.2 shared adapter is no longer
being composed at a 12.90 pitch. Replace that entry with one sentence recording
that it was settled and where, and leave the FMT-N and the combine questions
alone — neither has new evidence.

- [ ] **Step 4: Run the full gate chain and commit**

Expected: tests up by 5. Lint unmoved.

---

## Self-Review

**1. Spec coverage.** C1 per-fibre granularity — Task 4, with the rear/front
asymmetry asserted in both directions. C2 `type: splice` — **NOT IMPLEMENTED,
and deliberately**: no splice cassette is modelled, `FAMILY` has no entry that
maps to it, and a branch no contract can reach is the dead code this project has
now shipped twice. The table is the place it goes when SKU 178124 or 258595 is
modelled, which is plan 6. C3 taps and ratios — the `ratio` column is in Task 5
and unit-tested against a constructed tap, since no modelled part splits yet.
The third export — Task 5. Section D's five sweeps — Task 6, four of them plus
the silent-non-export guard the spec does not ask for and this plan needs.

**2. Placeholder scan.** No TBDs, no "handle errors appropriately", no "similar
to Task N". Every code step carries the code. Two defects found in this pass and
fixed inline rather than left for the implementer: `front_label` was called with
a `load_ref` that always answered None, which would have made every connector
zero fibres wide and every front label wrong while still returning a plausible
string; and `fibre_map` carried a dead `for ... pass` loop.

**3. Type consistency.** `contract_view(entry)` is defined in Task 1 and used in
Tasks 4, 5 and 6. `family_of(ref)` and `port_type(family, polish)` are defined in
Task 3 and used in Task 4. `ports(entry, load_ref)` returns
`{"front": [...], "rear": [...]}` in Task 4 and is consumed with those keys in
Tasks 5 and 6. `fibre_map(entry, load_ref, model)` takes three arguments
everywhere. `component_by_ref` is added in Task 4 and used in Task 5.
`load_ref` is a callable taking a ref and returning an entry or None throughout.

**4. Known soft spots, named rather than hidden.**

- **The front-numbering derivation is the weakest link.** The faceplate labels
  exist only as prose, and placement order reproducing them is checked on
  exactly one cassette. A cassette whose vendor numbers its ports differently -
  right to left, or by column - would export a wrong but plausible map, and
  nothing would catch it. The check to add when a second cassette is modelled is
  that same reproduction test against its own stated numbering.
- **`rear_name` is keyed on the part id, not the face.** Two faces carrying
  parts with the same id would collide in `fibre_map`. No modelled part has two
  faces, and L83 forbids a face of a face, but the collision is real and
  unguarded.
- **Nothing validates the exports against NetBox's or Nautobot's own schema.**
  There is no such schema in this repo, so Task 6's sweeps check the projection
  against the graph and not against upstream. A wrong port-type string would pass
  every test here.
- **`splice` is in the enum and nowhere in the code.** Stated above; recorded
  again here because it is the single most likely thing to be read as an
  oversight rather than a decision.
