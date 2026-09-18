# Pluggables A: `generic/` transceivers — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One drawn transceiver per form factor and face under a new `generic/` namespace, sourced from the MSA that governs its envelope, carrying no rate and no vendor fact, seating in every cage of its family through the mating mechanism the library already has — with the two `common/` generics retired and the five device configurations that ship seated optics made bare.

**Architecture:** Module envelopes become `standards.yaml` entries so L9 holds each generic's drawn size to its spec exactly as it holds a cage's. Generics are `class: transceiver` / `behaviour: occupies` / `mates: <interface>` / `conforms: <module entry>` parts whose latch colour and label are `fields` and whose face bores are composed `std/` parts. A new lint rule (L99) refuses any rate or wattage on a `generic/` transceiver. Vendor optics wrap a generic via `parts:`; nothing in the mating, rendering or export paths changes.

**Tech Stack:** Python 3.12 (`spec/tools/portrayal/*`), YAML contracts, SVG skins, pytest (`spec/tests`, run with `-n auto`), the OKF knowledge base (MCP `okf-kb`, bundle `ndv-standards`) for the MSAs.

**Spec:** `docs/pluggables-generics-design.md` (A), with the shared decisions in `docs/pluggables-design.md`. Both are on branch `pluggables-specs` (roc-ops/Portrayal#393).

## Global Constraints

- **Never launder an estimate into a measurement.** No number enters a contract or the registry that was not read off a named figure or table; every `confidence:` token says which. (spec A §2: "No number is written in this design that has not been read off the page.")
- **A generic carries no rate, reach, wavelength, mode or wattage** — `generic/sfp-lc` is SFP, SFP+ and SFP28 alike. (umbrella decision 5; enforced by L99 in Task 2)
- **The face is in the name; colour and label are fields.** `sfp-lc`, `sfp-sc`, `sfp-rj45`; `fields: {latch-color, label}`. (umbrella decision 4)
- **Every generic ships with `relief.features`** from its MSA — protrusion is not a later pass. (umbrella decision 9)
- **Every generic declares `attrs: {power-absent: not-applicable}` with a `provenance.power` sentence** — L27 exempts by that attr and requires the sentence. (existing doctrine on both `common/` generics)
- **Shipped device models stay bare.** No `occupants:` remains in any `library/devices/**/device.yaml` after Task 7. (umbrella decision 2)
- **`working/` is never committed.** Fetched PDFs and datasheets go under `working/intake/...` with a `SOURCES.md`; facts are transcribed, files are not.
- **Gates run with this worktree's code:** `PYTHONPATH=spec/tools python -m portrayal <lock|lint|build>` — a bare `python -m portrayal` runs whichever checkout it was installed from. Use the Bash tool's own `timeout` at 600000; never `run_in_background`.
- **Version bumps go in BEFORE `lock --update`.** Check what L53 asks for and bump first.
- **Stage explicit paths; never `git add -A`.** Commit messages contain no backticks — write to a file and `git commit -F`. Every commit ends with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- **Tests run rules through `lint.collecting()`**, never by clearing `lint.WARNINGS` / `lint.ERRORS` by hand.
- **Naming:** component names are `[a-z0-9._-]+` (`MAJOR_REF` in lint.py); `mpo12` is legal, `sfp28` is a rate and is refused by L99 (Task 2).

---

## File map

| file | responsibility |
|---|---|
| `spec/schemas/vendors.yaml` | `namespaces.generic` (Task 1) |
| `spec/tools/portrayal/components_catalogue.py:98` | namespace order gains `generic` (Task 1) |
| `library/components/README.md` | namespace row, body-skin correction, "Adding an optic" section (Tasks 1, 9) |
| `spec/tools/portrayal/lint.py` | L99 registration + `lint_component_generic` + call site (Task 2) |
| `spec/tests/test_generic_stays_generic.py` | L99 unit tests (Task 2) |
| `spec/schemas/standards.yaml` | `sfp-module`, `qsfp-module`, `qsfp-dd-module`, `sc-simplex-receptacle` (Tasks 3, 4) |
| `spec/tests/test_module_envelopes.py` | registry entries are complete and L9 accepts the generics (Task 3) |
| `library/components/std/sc-bore/v1/{contract.yaml,skins/default.svg}` | the SC face (Task 4) |
| `spec/tools/portrayal/dcim_export.py:401,441` | `PART_SKIP` and `NOT_A_DCIM_PORT` gain `std/sc-bore` (Task 4) |
| `library/components/generic/sfp-lc/v1/{contract.yaml,skins/default.svg}` | Task 5 |
| `library/components/generic/qsfp-lc/v1/{contract.yaml,skins/default.svg}` | Task 6 |
| `library/devices/ufispace/{s9600-32x,s9600-28dx,s9600-64x,s9510-28dc,s9501-28smt}/device.yaml` | occupants stripped, descriptions reworded, versions bumped (Task 7) |
| `library/components/common/sfp-lc-duplex/v1/contract.yaml`, `common/qsfp-transceiver/v1/contract.yaml` | `unplaced:` pointing at successors (Task 7) |
| `spec/tests/test_occupants.py` | copy-and-inject idiom, generic parts (Task 8) |
| `spec/tests/test_mate_forwarding.py` | last test seats `generic/qsfp-lc` (Task 8) |
| `library/components/generic/{sfp-lc-simplex,sfp-sc,sfp-rj45,qsfp-dd-lc}/v1/…` | Tasks 10–12 |
| `working/intake/optic/msa/SOURCES.md`, `working/intake/fiber-connectors/sc/SOURCES.md` | fetch logs, never committed (Tasks 3, 4) |

---

### Task 1: The `generic/` namespace

**Files:**
- Modify: `spec/schemas/vendors.yaml:37-39`
- Modify: `spec/tools/portrayal/components_catalogue.py:98`
- Modify: `library/components/README.md:35-45` (namespace table) and `:237-239` (body-skin sentence)
- Test: `spec/tests/test_artifact_sufficiency.py` (existing `test_the_namespaces_ship_too`) and `spec/tests/test_components_catalogue.py` (existing)

**Interfaces:**
- Produces: the namespace string `generic`, recognised by L55 through `vendors.yaml` `namespaces:` and ordered third in `CATALOGUE.md`.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_artifact_sufficiency.py`:

```python
def test_the_generic_namespace_ships():
    """`generic/` is the third non-vendor namespace (docs/pluggables-design.md,
    decision 3) and a consumer resolving `generic/sfp-lc@1` must find it in the
    published registry beside `common` and `std`."""
    ns = load("vendors.json")["namespaces"]
    assert "generic" in ns, sorted(ns)
    assert "representative of a class under a spec" in ns["generic"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_artifact_sufficiency.py::test_the_generic_namespace_ships -q`
Expected: FAIL — `assert 'generic' in ns`

- [ ] **Step 3: Add the namespace line**

In `spec/schemas/vendors.yaml`, after line 39 (`  std: apertures and cages conforming to spec/schemas/standards.yaml`), add:

```yaml
  generic: >-
    representative of a class under a spec. The envelope is a published standard -
    it is what makes the part seat everywhere its family does - and the appearance
    stands for every product of its kind rather than any one of them. A vendor's
    product wraps a generic and adds its facts; a vendor's outlier draws its own.
    Transceivers and connectors first; DIMMs, PCIe cards and CPUs belong here when
    they arrive. Nothing already in common/ moves here in the work that creates it.
```

- [ ] **Step 4: Order it in the catalogue**

In `spec/tools/portrayal/components_catalogue.py` line 98, change:

```python
    order = ["std", "common"] + sorted(k for k in groups if k not in ("std", "common"))
```

to:

```python
    order = ["std", "common", "generic"] + sorted(
        k for k in groups if k not in ("std", "common", "generic"))
```

- [ ] **Step 5: README — the namespace row and the stale body-skin claim**

In `library/components/README.md`, in the Namespaces table after the `common/` row, add:

```markdown
| `generic/` | a representative of a class under a spec: the envelope conforms to a standard (so lint checks it as `std/` is checked) and the appearance stands for every product of its kind; a vendor's product wraps one via `parts:` and adds its facts | `generic/sfp-lc`, `generic/qsfp-lc` |
```

Replace lines 237-239:

```markdown
- `body-left.svg`, `body-right.svg`, `body-top.svg`, `body-bottom.svg`,
  `body-rear.svg` are optional side views for parts that have a 3D body
  (modules, PSUs, fans); the viewer uses them to texture the box.
```

with:

```markdown
- `body-left.svg`, `body-right.svg`, `body-top.svg`, `body-bottom.svg`,
  `body-rear.svg` are optional side views for parts that have a 3D body. NOTHING
  READS THEM TODAY: `relief.js` extrudes a box from the face skin and `data-z-*`,
  and whether these should texture that box is decided in
  docs/pluggables-3d-design.md. Do not add them to a new part.
```

- [ ] **Step 6: Publish and run the tests**

Run: `./publish.sh --no-images && PYTHONPATH=spec/tools python3 spec/tools/portrayal/components_catalogue.py --library library > library/components/CATALOGUE.md && PYTHONPATH=spec/tools python -m pytest spec/tests/test_artifact_sufficiency.py spec/tests/test_components_catalogue.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

Write the message to a file, then:

```bash
git add spec/schemas/vendors.yaml spec/tools/portrayal/components_catalogue.py library/components/README.md library/components/CATALOGUE.md library/exports spec/tests/test_artifact_sufficiency.py
git commit -F /path/to/msg.txt
```

Message: `the generic namespace: representative of a class under a spec` + a paragraph quoting decision 3 + the attribution line.

---

### Task 2: L99 — a generic stays generic

**Files:**
- Modify: `spec/tools/portrayal/lint.py:241` (registration, after L98) and `:1230` region (new function before `lint_component_cage_rate`) and `:7102` (call site)
- Test: `spec/tests/test_generic_stays_generic.py`

**Interfaces:**
- Produces: `lint.lint_component_generic(path, data, _lib_roots=None)`; rule id `"L99"`; error text contains `"is a generic and carries"` for attr hits and `"names a rate"` for name hits.

- [ ] **Step 1: Write the failing tests**

```python
"""L99: a generic stays generic.

A `generic/` transceiver stands for every module of its kind, so a rate, a reach,
a wavelength, a mode or a wattage on it is a specific product wearing a generic's
name - the defect `common/sfp-lc-duplex` carried for a year (`mode: single-mode,
reach: 30km, speed: 100m` on a shape that stands for every SFP). Decision 5 of
docs/pluggables-design.md says the rate lives on the vendor wrapper; this is what
keeps that true after the people who decided it have moved on.
"""
import pathlib

from portrayal import lint

GEN = pathlib.Path("library/components/generic/sfp-lc/v1/contract.yaml")
VEN = pathlib.Path("library/components/cisco/sfp-10g-lr/v1/contract.yaml")


def run(path, doc):
    with lint.collecting() as got:
        lint.lint_component_generic(path, doc)
        return [e for e in got.errors if "[L99]" in e]


def base(**attrs):
    return {"kind": "component", "name": "sfp-lc", "class": "transceiver",
            "behaviour": "occupies", "mates": "sfp",
            "attrs": {"power-absent": "not-applicable", **attrs}}


def test_a_clean_generic_passes():
    assert run(GEN, base()) == []


def test_a_rate_attr_on_a_generic_is_an_error():
    errs = run(GEN, base(speed="10g"))
    assert len(errs) == 1 and "is a generic and carries" in errs[0] and "speed" in errs[0]


def test_each_forbidden_attr_is_named():
    for key in ("speed", "reach", "wavelength", "mode",
                "power-draw-max-w", "power-draw-typical-w"):
        errs = run(GEN, base(**{key: "x"}))
        assert errs and key in errs[0], key


def test_a_rate_in_the_name_is_an_error():
    doc = dict(base(), name="sfp28-lc")
    errs = run(GEN, doc)
    assert len(errs) == 1 and "names a rate" in errs[0]


def test_the_same_attrs_on_a_vendor_wrapper_are_fine():
    """The rule is about the namespace, not the class: a vendor optic is SUPPOSED
    to carry these."""
    assert run(VEN, base(speed="10g", reach="10km", **{"power-draw-max-w": 1.0})) == []


def test_a_generic_that_is_not_a_transceiver_is_not_asked():
    doc = dict(base(speed="fast"), **{"class": "connector"})
    assert run(GEN, doc) == []
```

- [ ] **Step 2: Run to verify they fail**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_generic_stays_generic.py -q`
Expected: FAIL — `AttributeError: module 'portrayal.lint' has no attribute 'lint_component_generic'`

- [ ] **Step 3: Register and implement**

In `spec/tools/portrayal/lint.py`, after the `"L98": (...)` line (241):

```python
    "L99": ("component",  "a generic stays generic - no rate, reach, wavelength or wattage under generic/", "move the figure to the vendor wrapper's attrs; a generic/ part stands for every module of its kind"),
```

Before `def lint_component_cage_rate`:

```python
GENERIC_FORBIDDEN_ATTRS = ("speed", "reach", "wavelength", "mode",
                           "power-draw-max-w", "power-draw-typical-w")
GENERIC_RATE_TOKENS = re.compile(
    r"(^|-)(sfp28|sfp56|sfp-plus|qsfp28|qsfp56|qsfp112|qsfp-dd800|"
    r"\d+g|\d+gbase[a-z0-9-]*|\d+km|\d+m)(-|$)")


def lint_component_generic(path, data, _lib_roots=None):
    """L99 - a generic stays generic.

    A `generic/` transceiver stands for every module of its kind, which is the
    whole reason it exists: `generic/sfp-lc` is an SFP, an SFP+ and an SFP28
    alike, and the rate, the reach, the wavelength and the watts are facts about
    the vendor's product that the WRAPPER carries (docs/pluggables-design.md,
    decision 5). `common/sfp-lc-duplex` carried `mode: single-mode, reach: 30km,
    speed: 100m` for a year - a specific module wearing a generic's name - and
    nothing could say so. This can.

    Namespace, not class: a vendor optic is SUPPOSED to carry these attrs, so the
    rule reads the path and asks only under `generic/`.
    """
    if not isinstance(data, dict) or data.get("class") != "transceiver":
        return
    if Path(path).parts[-4:-3] != ("generic",) and "/generic/" not in str(path):
        return
    attrs = data.get("attrs") or {}
    hit = [k for k in GENERIC_FORBIDDEN_ATTRS if k in attrs]
    if hit:
        err(path, "L99", f"{data.get('name')} is a generic and carries "
                         f"{', '.join(hit)}. A generic stands for every module of "
                         "its kind; the figure belongs on the vendor wrapper's attrs")
    name = str(data.get("name") or "")
    if GENERIC_RATE_TOKENS.search(name):
        err(path, "L99", f"{name} names a rate. A generic is named by form factor "
                         "and face - sfp-lc, qsfp-mpo12 - never by what runs in it")
```

(`re` and `Path` are already imported at the top of lint.py.)

At the call site (line 7102), after `lint_component_display(f, d)`:

```python
                lint_component_generic(f, d)
```

- [ ] **Step 4: Run to verify they pass**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_generic_stays_generic.py -q`
Expected: 6 passed

- [ ] **Step 5: Regenerate the rules page and run the catalogue test**

Run: `python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md && PYTHONPATH=spec/tools python -m pytest spec/tests/test_lint_rules_catalogue.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add spec/tools/portrayal/lint.py docs/lint-rules.md spec/tests/test_generic_stays_generic.py
git commit -F /path/to/msg.txt
```

---

### Task 3: Module envelopes in `standards.yaml`

**Files:**
- Modify: `spec/schemas/standards.yaml` (under `standards:`)
- Create: `working/intake/optic/msa/SOURCES.md` (not committed)
- Test: `spec/tests/test_module_envelopes.py`

**Interfaces:**
- Produces: registry keys `sfp-module`, `qsfp-module`, `qsfp-dd-module`, each with `w`, `h`, `depth`, `confidence`, `depth-confidence`, `registry`, `notes`. A generic declares `conforms: <key>` and `size: {w, h, d}` and L9 (lint.py:700-731) compares `w`/`h` to the entry's `w`/`h` and `d` to `depth`, within 0.05.

- [ ] **Step 1: Read the figures out of OKF**

Use the `okf-kb` MCP `get_concept` on bundle `ndv-standards`:

- `sff-8432/4-4-ipf-module-dimensions.md` — Table 4-3 "Dimension Table for IPF Module": the designators for module width, module height and overall length, with tolerance. Also `sff-8432/table-4-3-dimension-table-for-ipf-module-continued.md`.
- `sff-8661/5-1-dimensions.md` — Figure 5-1 Basic Views; the PDF is also on disk at `working/specs/sff-8661-r2.5.pdf` (read with the Read tool, `pages`) if OKF's recovered text does not carry the numbers.
- `qsfp-dd-hw/7-3-module-form-factors-for-qsfp-dd-qsfp-dd800.md` — Figure 47, Type 1 module outline.

Record in `working/intake/optic/msa/SOURCES.md` which figure/table each number came from and its tolerance. If a number is not legible in OKF's text and the PDF is not held, the entry's `confidence` is `registry` and `notes` says which figure to read — do not estimate.

- [ ] **Step 2: Write the failing test**

```python
"""Module envelopes are registry entries, so L9 holds a generic's drawn size to
its MSA the way it holds a cage's (docs/pluggables-generics-design.md section 2).
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]

MODULES = {
    "sfp-module": "SFF-8432",
    "qsfp-module": "SFF-8661",
    "qsfp-dd-module": "QSFP-DD",
}


def test_every_module_envelope_is_in_the_registry():
    for key, spec in MODULES.items():
        e = REG.get(key)
        assert e, f"{key} missing"
        assert spec in e["registry"], (key, e["registry"])
        for f in ("w", "h", "depth", "confidence", "depth-confidence", "notes"):
            assert f in e, (key, f)
        assert e["confidence"] in ("verified", "measured", "registry"), key


def test_each_entry_names_its_figure():
    for key in MODULES:
        e = REG[key]
        assert re.search(r"(Fig(ure)? \d|Table \d)", e["registry"]), (key, e["registry"])
        assert "depth-notes" in e, key
```

(`import re` at the top.) Whether L9 accepts a generic against these entries is
tested on the real parts in Tasks 5, 6, 10, 11 and 12 - L9 is a branch of
`lint.lint_component(path, validator)`, not a function of its own, so it is
exercised on a contract on disk, not on a dict.

- [ ] **Step 3: Run to verify it fails**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_module_envelopes.py -q`
Expected: FAIL — `sfp-module missing`

- [ ] **Step 4: Add the three entries**

Under `standards:` in `spec/schemas/standards.yaml`, in the registry's existing shape (compare the `qsfp28` entry). Numbers come from Step 1 — the placeholders below are the FIELDS, not values to copy:

```yaml
sfp-module:
  registry: 'SFF-8432 Rev 5.2a, Table 4-3 Dimension Table for IPF Module and Figure 4-1 IPF Module'
  w: <module width, Table 4-3>
  h: <module height, Table 4-3>
  radius: 0.0
  confidence: verified
  depth: <overall module length, Table 4-3>
  depth-confidence: verified
  depth-notes: 'overall length of the module including the latch, Table 4-3 designator <X>; the protrusion past a bezel is this less the cage depth (std/sfp registry 41.0)'
  notes: >-
    THE MODULE ENVELOPE, not a panel aperture - the first registry entry that
    governs an occupant rather than a hole. w and h are the body a cage accepts,
    Table 4-3 with tolerances; docs/pluggables-generics-design.md section 2.
    Shared by SFP, SFP+ and SFP28 - the rate is electrical and never in this
    entry. SFF-8402 (SFP28) is not held and not needed: it inherits this envelope.
qsfp-module:
  registry: 'SFF-8661 Rev 2.5, Figure 5-1 Basic Views'
  w: <Fig 5-1>
  h: <Fig 5-1>
  radius: 0.0
  confidence: verified
  depth: <overall length, Fig 5-1>
  depth-confidence: verified
  depth-notes: 'overall module length, Fig 5-1; protrusion is this less SFF-8663 Fig 4-1 37 REF (std/qsfp28 registry depth)'
  notes: >-
    Shared by QSFP+, QSFP28, QSFP56 and QSFP112 - one envelope, one cage
    interface (qsfp), the rate never in this entry. common/qsfp-transceiver@1's
    18.35 x 8.5 came from a vendor drawing; this is the MSA that drawing follows.
qsfp-dd-module:
  registry: 'QSFP-DD/QSFP-DD800/QSFP112 Hardware Specification Rev 6.3, section 7.3, Figure 47 (Type 1 module)'
  w: <Fig 47>
  h: <Fig 47>
  radius: 0.0
  confidence: verified
  depth: <Fig 47>
  depth-confidence: verified
  notes: >-
    Type 1. Types 2, 2A and 2B differ behind the bezel (section 7.3) and are
    not separate envelopes here. Same width as qsfp-module by design - the
    QSFP-DD cage accepts a QSFP module (section 1).
```

- [ ] **Step 5: Run the tests and the registry's own checks**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_module_envelopes.py spec/tests/test_schema_hygiene.py -q && PYTHONPATH=spec/tools python -m portrayal lint 2>&1 | grep -E "ERROR|LINT: ok"`
Expected: tests PASS; `LINT: ok`

- [ ] **Step 6: Commit**

```bash
git add spec/schemas/standards.yaml spec/tests/test_module_envelopes.py
git commit -F /path/to/msg.txt
```

Message names the figure and table each number came from. `working/` is not staged.

---

### Task 4: `std/sc-bore` and its registry entry — GATED at execution (no free source dimensions the SC keyed opening; the search is recorded in spec A section 4 and in working/intake/fiber-connectors/sc/COVERAGE.md; the part, registry entry, test and dcim entries are NOT built)

**Files:**
- Create: `library/components/std/sc-bore/v1/contract.yaml`, `library/components/std/sc-bore/v1/skins/default.svg`
- Modify: `spec/schemas/standards.yaml` (`sc-simplex-receptacle`)
- Modify: `spec/tools/portrayal/dcim_export.py:401` (`PART_SKIP`) and `:441` (`NOT_A_DCIM_PORT`)
- Create: `working/intake/fiber-connectors/sc/SOURCES.md` + the fetched datasheet (not committed)
- Test: `spec/tests/test_sc_bore.py`

**Interfaces:**
- Produces: `std/sc-bore@1` with `interface: sc`, `conforms: sc-simplex-receptacle`, `connection-points.mate`, `elements.bore` (class cutout), `relief.cavity: bore`. Consumed by `generic/sfp-sc` (Task 10) and by B's SC plug.

- [ ] **Step 1: Fetch the source**

Fetch SENKO's SC simplex adapter datasheet (public; search "SENKO SC adapter datasheet DS-SC") into `working/intake/fiber-connectors/sc/pdf/`, and write `working/intake/fiber-connectors/sc/SOURCES.md` in the shape of `working/intake/fiber-connectors/lc/SOURCES.md`: what was fetched, from where, what it dimensions (the keyed simplex opening width and height, the key width), what it does not. FOCIS 3 / IEC 61754-4 is paywalled; record that.

- [ ] **Step 2: Write the failing test**

```python
"""std/sc-bore is the SC simplex face a generic/sfp-sc composes. The library had
no SC face - common/sc-apc is a 24 x 26 moulded PON bay - and the LC bore is the
template: keyed opening, one bore element, a cavity, a mate point."""
import json
import pathlib

import jsonschema
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
P = ROOT / "library/components/std/sc-bore/v1/contract.yaml"

COMPONENT_SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())


def component_errors(path):
    """The rules a part test cares about, run the way the CLI runs them. L9 is a
    branch of `lint.lint_component`, not a function of its own; L11 and L99 are
    separate functions the CLI's component loop calls after it, so they are
    called here too - `lint_component` alone would never raise them."""
    d = yaml.safe_load(pathlib.Path(path).read_text())
    with lint.collecting() as got:
        lint.lint_component(path, jsonschema.Draft202012Validator(COMPONENT_SCHEMA))
        lint.lint_component_mating(path, d, [str(ROOT / "library")])
        lint.lint_component_generic(path, d)
        return list(got.errors)


def rule_errors(path, *rules):
    errs = component_errors(path)
    return [e for e in errs if any(f"[{r}]" in e for r in rules)]


def test_the_bore_exists_and_is_shaped_like_the_lc_bore():
    d = yaml.safe_load(P.read_text())
    assert d["class"] == "port" and d["interface"] == "sc"
    assert d["conforms"] == "sc-simplex-receptacle"
    assert d["elements"]["bore"]["class"] == "cutout"
    assert d["relief"]["cavity"] == "bore"
    assert d["connection-points"]["mate"]["direction"] == "front"
    assert "size" in d["provenance"] and "keyway" in d["provenance"]


def test_the_bore_lints_clean():
    assert rule_errors(P, "L9", "L11", "L26") == []


def test_the_exporter_knows_it_is_not_a_port():
    from portrayal import dcim_export as dx
    assert "std/sc-bore" in dx.PART_SKIP
    assert "std/sc-bore" in dx.NOT_A_DCIM_PORT
```

- [ ] **Step 3: Run to verify it fails**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_sc_bore.py -q`
Expected: FAIL — `FileNotFoundError`

- [ ] **Step 4: Registry entry and contract**

`spec/schemas/standards.yaml`:

```yaml
sc-simplex-receptacle:
  registry: 'TIA-604-3 (FOCIS 3) / IEC 61754-4 governs the SC interface and is not held. w/h are read from the SENKO SC simplex adapter datasheet front view (working/intake/fiber-connectors/sc/SOURCES.md)'
  w: <opening width>
  h: <opening height incl. key>
  radius: 0.0
  confidence: measured
  depth: <recess>
  depth-confidence: estimated
  notes: >-
    The keyed SC simplex opening a plug enters - the transceiver receptacle,
    not the bulkhead adapter, same distinction std/lc-bore@3 draws. APC and UPC
    share this opening; polish is `optical.polish` on the part, never a second
    aperture (docs/pluggables-design.md decision 10).
```

`library/components/std/sc-bore/v1/contract.yaml` — copy `std/lc-bore/v3/contract.yaml` and change: `name: sc-bore`, `version: 1.0.0`, `interface: sc`, `conforms: sc-simplex-receptacle`, `attrs: {media: fiber, connector: sc}`, `size:` to the registry's w/h/d, `elements.bore.size` to `[w, h]`, `connection-points.mate` to the bore's centre, `provenance.ferrule: standard (SC uses a 2.5mm ferrule)`, and rewrite `provenance.size` / `keyway` / `gap` to name the SENKO SC datasheet and FOCIS 3 instead of the LC documents. Delete `short-keyway` (it is an LC-specific note). Keep `relief` with a `ferrule` feature marked `estimated` citing the LC bore's own unsourced 3.6.

`skins/default.svg` — a keyed rectangle at the registry size with `id="bore"`, one `id="ferrule"` circle at the centre, following `std/lc-bore/v3/skins/default.svg`'s structure.

`dcim_export.py`: add `"std/sc-bore"` to `PART_SKIP` (line 401) and to `NOT_A_DCIM_PORT` beside the `std/lc-bore` line:

```python
    "std/sc-bore": "the bore of an SC-faced transceiver, not a port on anything - see PART_SKIP",
```

- [ ] **Step 5: Run the tests, then lint**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_sc_bore.py spec/tests/test_dcim_interfaces.py -q && PYTHONPATH=spec/tools python -m portrayal lint 2>&1 | grep -E "sc-bore|ERROR|LINT: ok"`
Expected: PASS; the only sc-bore lines are L89 (unplaced) until Task 10 composes it — add `unplaced: composed by generic/sfp-sc@1 (Task 10 of the pluggables A plan); a bore is never placed on a panel` to the contract for now.

- [ ] **Step 6: Commit**

```bash
git add library/components/std/sc-bore spec/schemas/standards.yaml spec/tools/portrayal/dcim_export.py spec/tests/test_sc_bore.py
git commit -F /path/to/msg.txt
```

---

### Task 5: `generic/sfp-lc`

**Files:**
- Create: `library/components/generic/sfp-lc/v1/contract.yaml`, `library/components/generic/sfp-lc/v1/skins/default.svg`
- Test: `spec/tests/test_generic_sfp_lc.py`

**Interfaces:**
- Consumes: `sfp-module` (Task 3), L99 (Task 2).
- Produces: `generic/sfp-lc@1` — `mates: sfp`, `fields: {latch-color, label}`, `connection-points: {mate, optical-tx, optical-rx}`, `relief.features` `body` and `bail`. Consumed by Task 7 (`unplaced:` pointers), Task 8 (tests), Task 9 (README example).

- [ ] **Step 1: Write the failing test**

```python
"""generic/sfp-lc: one SFP with an LC duplex face, standing for every SFP, SFP+
and SFP28 with one (docs/pluggables-generics-design.md section 3)."""
import json
import pathlib

import jsonschema
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/generic/sfp-lc/v1/contract.yaml"

COMPONENT_SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())


def component_errors(path):
    """The rules a part test cares about, run the way the CLI runs them. L9 is a
    branch of `lint.lint_component`, not a function of its own; L11 and L99 are
    separate functions the CLI's component loop calls after it, so they are
    called here too - `lint_component` alone would never raise them."""
    d = yaml.safe_load(pathlib.Path(path).read_text())
    with lint.collecting() as got:
        lint.lint_component(path, jsonschema.Draft202012Validator(COMPONENT_SCHEMA))
        lint.lint_component_mating(path, d, [str(ROOT / "library")])
        lint.lint_component_generic(path, d)
        return list(got.errors)


def rule_errors(path, *rules):
    errs = component_errors(path)
    return [e for e in errs if any(f"[{r}]" in e for r in rules)]


def contract():
    return yaml.safe_load(P.read_text())


def test_shape():
    d = contract()
    assert d["class"] == "transceiver" and d["behaviour"] == "occupies"
    assert d["mates"] == "sfp" and d["conforms"] == "sfp-module"
    assert d["attrs"]["power-absent"] == "not-applicable"
    assert set(d["fields"]) == {"latch-color", "label"}
    assert {p["ref"] for p in d["parts"]} == {"std/lc-bore@3"}
    assert {p["id"] for p in d["parts"]} == {"tx", "rx"}
    for k in ("mate", "optical-tx", "optical-rx"):
        assert d["connection-points"][k]["direction"] == "front"


def test_no_rate_anywhere():
    d = contract()
    for k in ("speed", "reach", "wavelength", "mode", "power-draw-max-w"):
        assert k not in d["attrs"], k


def test_it_protrudes_from_day_one():
    feats = {f["node"]: f for f in contract()["relief"]["features"]}
    assert feats["body"]["out"] > 0
    assert feats["body"]["confidence"] in ("drawing", "verified", "measured")
    assert "SFF-8432" in feats["body"]["source"]


def test_the_skin_takes_the_colour_and_label_as_fields():
    svg = (P.parent / "skins/default.svg").read_text()
    assert 'data-fill-from="latch-color"' in svg
    assert 'data-from="label"' in svg


def test_it_lints_clean_alone():
    """L9 (size against the registry), L11 (mating) and L99 (stays generic)."""
    assert rule_errors(P, "L9", "L11", "L99") == []


def test_the_bores_are_lifted_to_the_module_face():
    """The bores recess from the transceiver face, which stands proud of the
    panel by the body's `out`; a bore at lift 0 would be a hole in the panel."""
    d = contract()
    out = next(f for f in d["relief"]["features"] if f["node"] == "body")["out"]
    for p in d["parts"]:
        assert abs(p["lift"] - out) < 0.01, p
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_generic_sfp_lc.py -q`
Expected: FAIL — `FileNotFoundError`

- [ ] **Step 3: Write the contract**

Start from `library/components/common/sfp-lc-duplex/v1/contract.yaml` (read it whole first) and produce `library/components/generic/sfp-lc/v1/contract.yaml`:

```yaml
format: 1
kind: component
name: sfp-lc
version: 1.0.0
class: transceiver
behaviour: occupies
mates: sfp
conforms: sfp-module
profile: networking
description: >-
  A generic SFP with an LC duplex face - the shape every SFP, SFP+ and SFP28
  optic with two LC bores has, standing for all of them. Two keyed bores with
  the ferrules standing in them, and a bail latch lying flat because the module
  is seated. Which module it is - rate, reach, wavelength, watts - is a fact
  about a vendor's product and lives on the wrapper that composes this
  (docs/pluggables-design.md, decision 5), never here.
size: {w: <sfp-module w>, h: <sfp-module h>, d: <sfp-module depth>}
attrs: {power-absent: not-applicable, form-factor: sfp, face: lc-duplex, media: fiber}
fields:
  latch-color:
    label: Latch colour
    type: text
    default: '#2f5fa8'
  label:
    label: Module label
    type: text
    default: ''
provenance:
  size: >-
    registry - sfp-module, which is SFF-8432 Rev 5.2a Table 4-3 (w, h, overall
    length). common/sfp-lc-duplex@1 carried 13.5 x 8.5 from the AutomationDirect
    SFP-30K-FSF drawing confirmed by its STEP solid at 13.46 x 8.48; that figure
    and the MSA's agree, which is the check, and the MSA is what is cited.
  power: >-
    NOT APPLICABLE, because this contract is a GENERIC and not a part. It is a
    shape that stands in for every module of its kind, so there is no one figure
    to state: a 1000BASE-SX is under 1 W and a 25G-ER several, and this single
    drawing is both. Any wattage here would be a fiction dressed as a fact. The
    figure belongs on the wrapper, which knows which module it is. L27 exempts
    by `power-absent` and this sentence is why.
  lc-spacing: <copy common/sfp-lc-duplex@1's lc-spacing sentence verbatim - it is the SFP-30K-FSF STEP measurement and still the source>
  optical-axis: <copy common/sfp-lc-duplex@1's optical-axis sentence verbatim>
  bores: <copy common/sfp-lc-duplex@1's bores sentence verbatim>
  protrusion: >-
    derived - the registry's overall length (SFF-8432 Table 4-3) less the cage
    depth std/sfp conforms to (41.0, measured), so <value> stands proud of the
    faceplate. Two sourced numbers subtracted; common/sfp-lc-duplex@1 made the
    same subtraction from a vendor drawing and a TE cage and landed near this,
    which is the cross-check.
  bail-colour: >-
    A FIELD, not a fact. Vendors colour the bail by reach (blue is commonly
    single-mode) and the wrapper sets `latch-color`; the default here is a
    colour, not a claim.
  latch: <copy common/sfp-lc-duplex@1's length sentence about the bail extended height, and mark the bail's reach estimated as that contract does>
parts:
  - {ref: std/lc-bore@3, id: tx, at: [1.225, 1.75], lift: <protrusion>, rotate: 180}
  - {ref: std/lc-bore@3, id: rx, at: [7.575, 1.75], lift: <protrusion>, rotate: 180}
relief:
  features:
    - node: body
      out: <protrusion>
      color: '#6e747c'
      confidence: drawing
      source: 'SFF-8432 Rev 5.2a Table 4-3 overall length, less std/sfp registry depth 41.0 - see provenance.protrusion'
    - node: bail
      lift: <protrusion>
      out: <bail reach>
      color: '#2f5fa8'
      confidence: estimated
      source: 'common/sfp-lc-duplex@1 - unsourced; 0.4 past the body was that contract''s guess and no MSA dimensions a bail''s reach'
connection-points:
  mate: {at: [<w/2>, <h/2>], direction: front}
  optical-tx: {at: [3.575, 5.7], direction: front}
  optical-rx: {at: [9.925, 5.7], direction: front}
skins: [default]
```

The `<...>` are values transcribed from the registry entry and its arithmetic. If `sfp-module`'s `w`/`h` differ from 13.5/8.5 by more than 0.05, keep the registry values (L9 requires it) and move the bore `at` values proportionally, recording the move in `provenance.bores`.

- [ ] **Step 4: Write the skin**

Start from `library/components/common/sfp-lc-duplex/v1/skins/default.svg` and change: the `viewBox`/`width`/`height` to the registry size; the `bail` rect gains `data-fill-from="latch-color"` (keep its literal `fill` as the default); add a label text node:

```xml
  <text id="label" x="6.75" y="7.9" font-family="sans-serif" font-size="0.9"
        text-anchor="middle" fill="#2a2f34" data-from="label"></text>
```

- [ ] **Step 5: Run the tests, lint, and render beside the MSA**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_generic_sfp_lc.py -q && PYTHONPATH=spec/tools python -m portrayal lint 2>&1 | grep -E "generic/sfp-lc|ERROR|LINT: ok"`
Expected: PASS; only an L89 line for `generic/sfp-lc` (nothing seats it until Task 8's test copies a device — add `unplaced: seated by configurations downstream of this library; see docs/pluggables-design.md decision 2` and re-run; L89 accepts the sentence).

Gate 5: render the part's compiled face (`PYTHONPATH=spec/tools python -m portrayal build` then rasterise `library/dist/components/generic/sfp-lc*.svg` or the components index entry) beside SFF-8432 Figure 4-1 at matched scale, and write the sentence "I put the render beside the figure at matched scale, and here is what it showed" in the commit message.

- [ ] **Step 6: Commit**

```bash
git add library/components/generic/sfp-lc spec/tests/test_generic_sfp_lc.py
git commit -F /path/to/msg.txt
```

---

### Task 6: `generic/qsfp-lc`

**Files:**
- Create: `library/components/generic/qsfp-lc/v1/contract.yaml`, `library/components/generic/qsfp-lc/v1/skins/default.svg`
- Test: `spec/tests/test_generic_qsfp_lc.py`

**Interfaces:**
- Consumes: `qsfp-module` (Task 3), L99 (Task 2).
- Produces: `generic/qsfp-lc@1` — `mates: qsfp`, same fields and connection-points as Task 5, `relief.features` `body` and `tab`.

- [ ] **Step 1: Write the failing test**

Copy `spec/tests/test_generic_sfp_lc.py` to `spec/tests/test_generic_qsfp_lc.py`, change `P` to `components/generic/qsfp-lc/v1/contract.yaml`, `mates` to `"qsfp"`, `conforms` to `"qsfp-module"`, and the protrusion assertion's source to `"SFF-8661"`. Add:

```python
def test_the_pull_tab_is_a_relief_feature_that_takes_the_colour():
    d = contract()
    feats = {f["node"]: f for f in d["relief"]["features"]}
    assert "tab" in feats and feats["tab"]["out"] > feats["body"]["out"]
    svg = (P.parent / "skins/default.svg").read_text()
    assert 'id="tab"' in svg and 'data-fill-from="latch-color"' in svg
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_generic_qsfp_lc.py -q`
Expected: FAIL — `FileNotFoundError`

- [ ] **Step 3: Write the contract**

Start from `library/components/common/qsfp-transceiver/v1/contract.yaml` (read it whole first). Differences from Task 5's shape:

- `name: qsfp-lc`, `mates: qsfp`, `conforms: qsfp-module`, `size:` from the registry, `attrs: {power-absent: not-applicable, form-factor: qsfp, face: lc-duplex, media: fiber}`.
- `parts:` — the two `std/lc-bore@3` at `[3.70, 0.95]` and `[9.95, 0.95]`, `rotate: 180`, each with `lift: <protrusion>`. Do NOT compose `common/qsfp-pull-tab@1`: a composed part cannot take the generic's `latch-color` field (render passes only a `parts:` entry's own static `attrs` into a composed part), so the tab is drawn in this part's own skin. Copy `common/qsfp-pull-tab@1`'s `size` provenance (19.00 MAX across, 3.40 MAX thick, 34.80 MAX reach from the ProLabs drawing) into `provenance.tab` and say why it is drawn here rather than composed.
- `relief.features`: `body` with `out` = registry overall length less `std/qsfp28`'s registry depth 37.0 (SFF-8663 Fig 4-1, `verified`), `confidence: drawing`, source naming both; `tab` with `lift: <body out>`, `out: <34.80 reach from the drawing>`, `confidence: drawing`, source `common/qsfp-pull-tab@1's provenance - ProLabs drawing 34.80 MAX reach`.
- `provenance.size`, `power`, `face-lc`, `optical-axis`, `silkscreen`, `receptacle-housing` copied from `common/qsfp-transceiver@1` verbatim where they still hold; `size` re-pointed at the registry with the vendor drawing as the cross-check.
- `provenance.face-mpo` becomes: `the MPO faces are their own parts - generic/qsfp-mpo12 - because a face is in the name (docs/pluggables-design.md decision 4)`.
- `connection-points`: `mate` at the module centre, `optical-tx: [6.05, 4.9]`, `optical-rx: [12.30, 4.9]`.
- `unplaced:` as in Task 5.

- [ ] **Step 4: Write the skin**

Start from `library/components/common/qsfp-transceiver/v1/skins/lc.svg`. Rename to `default.svg`. Add the tab as a rounded rect straddling the face at the drawing's 19.00 width (x −0.325, width 19.0, height 3.40 centred on the face's vertical middle — the position `common/qsfp-pull-tab@1` is composed at in the old contract, `at: [-0.325, 2.55]`), `id="tab"`, `fill="#f2f2f2"` `data-fill-from="latch-color"`. Add the `label` text node with `data-from="label"` under the T/R silkscreen. Delete the `body-*.svg` skins — do not copy them.

- [ ] **Step 5: Run the tests, lint, render**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_generic_qsfp_lc.py -q && PYTHONPATH=spec/tools python -m portrayal lint 2>&1 | grep -E "generic/qsfp-lc|ERROR|LINT: ok"`
Expected: PASS; `LINT: ok`. Gate 5 against SFF-8661 Figure 5-1, sentence in the commit message.

- [ ] **Step 6: Commit**

```bash
git add library/components/generic/qsfp-lc spec/tests/test_generic_qsfp_lc.py
git commit -F /path/to/msg.txt
```

---

### Task 7: Strip the five configurations; retire the two `common/` generics

**Files:**
- Modify: `library/devices/ufispace/s9600-32x/device.yaml:825-833`, `s9600-28dx/device.yaml:748-753`, `s9600-64x/device.yaml:953-961`, `s9510-28dc/device.yaml:647-655`, `s9501-28smt/device.yaml:766-774` (+ each `version:` line and `device.lock.json`)
- Modify: `library/components/common/sfp-lc-duplex/v1/contract.yaml`, `library/components/common/qsfp-transceiver/v1/contract.yaml` (`unplaced:`)
- Test: `spec/tests/test_shipped_devices_are_bare.py`

**Interfaces:**
- Produces: no `occupants:` in any shipped device; `common/sfp-lc-duplex@1` and `common/qsfp-transceiver@1` carry `unplaced:` naming their successors.

- [ ] **Step 1: Write the failing test**

```python
"""Portrayal ships its device models bare. Populating is a downstream tool's job
(docs/pluggables-design.md, decision 2); five UfiSpace configurations shipped
fitted with optics before this and were the only ones that did."""
import pathlib

import yaml

from portrayal import libwalk

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def test_no_shipped_configuration_seats_an_optic():
    fitted = []
    for man in libwalk.iter_devices([LIB]):
        d = yaml.safe_load(man.read_text()) or {}
        for name, cfg in (d.get("configurations") or {}).items():
            if (cfg or {}).get("occupants"):
                fitted.append(f"{man.parent.name}:{name}")
    assert fitted == [], fitted
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_shipped_devices_are_bare.py -q`
Expected: FAIL listing the five

- [ ] **Step 3: Strip, and delete what is then a duplicate**

Once the optics are gone, the four `dc-populated` configurations (`s9600-28dx`,
`s9600-64x`, `s9510-28dc`, `s9501-28smt`) are byte-for-byte their `dc` sibling -
same bays, same `component-attrs` - and a configuration that draws the same
thing twice is noise. DELETE those four configuration blocks entirely (from the
`  dc-populated:` key through the last `occupants` line). `test_config_kind.py`
names `dc-populated` only in its docstring; nothing else references the name.

`s9600-32x breakout` is a real state and stays. Delete only its `occupants:`
mapping (lines 829-833) and change line 826 from
`The AC build with the four SFP28 breakout ports fitted with 25G optics. QSFP28`
to `The AC build with the four SFP28 breakout ports enabled. QSFP28`.

Add to each device's `dc` configuration a `source:` line if it lacks one:
`bare by policy - what is plugged in is a downstream configuration, docs/pluggables-design.md decision 2`.

- [ ] **Step 4: Bump, relock, lint**

Run `PYTHONPATH=spec/tools python -m portrayal lint --new-only 2>&1 | grep L53` — bump each device's `version:` by what L53 asks (at least minor: drawn parts were removed). Then `PYTHONPATH=spec/tools python -m portrayal lock --update`.

L89 will now report `common/sfp-lc-duplex@1` unreached. Add to its contract, after `description:`:

```yaml
unplaced: >-
  SUPERSEDED by generic/sfp-lc@1, which carries the same measured face without
  this part's baked-in mode, reach and speed - a specific 30 km single-mode
  module wearing a generic's name was the defect. Nothing references this major;
  it is deleted in a later sweep once B and C have landed on the successor.
```

and change `common/qsfp-transceiver@1`'s existing `unplaced:` to name `generic/qsfp-lc@1` as its successor in the same words.

- [ ] **Step 5: Run the suite**

Run: `PYTHONPATH=spec/tools python -m portrayal lint 2>&1 | grep -E "ERROR|LINT: ok" && PYTHONPATH=spec/tools python -m portrayal build && ./publish.sh --no-images && PYTHONPATH=spec/tools python -m pytest spec/tests -q -n auto`
Expected: `LINT: ok`; `test_occupants.py` FAILS (it renders `dc-populated`, which no longer exists) — that is Task 8's job; everything else passes.

- [ ] **Step 6: Commit**

```bash
git add library/devices/ufispace/s9600-32x library/devices/ufispace/s9600-28dx library/devices/ufispace/s9600-64x library/devices/ufispace/s9510-28dc library/devices/ufispace/s9501-28smt library/components/common/sfp-lc-duplex library/components/common/qsfp-transceiver library/exports spec/tests/test_shipped_devices_are_bare.py
git commit -F /path/to/msg.txt
```

---

### Task 8: The seating tests seat a generic, on a copy

**Files:**
- Modify: `spec/tests/test_occupants.py` (whole file)
- Modify: `spec/tests/test_mate_forwarding.py:180-215` (`test_a_component_with_one_skin_does_not_need_it_named`)

**Interfaces:**
- Consumes: `generic/sfp-lc@1` (Task 5), `generic/qsfp-lc@1` (Task 6).

- [ ] **Step 1: Rewrite `test_occupants.py`**

Replace the file. The idiom is `test_mate_forwarding.py`'s last test: copy the device to `tmp_path`, inject `occupants:`, render the copy. The corpus is never a scratch pad.

```python
"""What is plugged in is a configuration, not a different device.

A populated port is the same cage with an optic in it. `occupants:` sits beside
`bays:` so a switch can be drawn bare or fitted without either being a separate
model, and it is sugar: the renderer expands it into the `mate-to` placements
that already existed, so there is one positioning path and one interface check.

THE LIBRARY SHIPS NO FITTED DEVICE (docs/pluggables-design.md decision 2), so
these tests seat a generic on a COPY of a device in tmp_path - the idiom
test_mate_forwarding already uses, because a corpus other tests read is not a
scratch pad. They test the two halves that can rot independently: that the sugar
really is sugar (the optic lands where the mate points meet, not near them), and
that the check reaches it (a QSFP in an SFP cage is an error wherever it was
declared).
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"

from portrayal import lint
from portrayal import libwalk

SRC = LIB / "devices/ufispace/s9510-28dc"
PORTS = ["port-4", "port-5", "port-6", "port-7"]


def fitted_copy(tmp_path, occupants):
    """The DC build of the S9510-28DC with `occupants` injected, on a copy."""
    dev = tmp_path / "s9510-28dc" / "device.yaml"
    shutil.copytree(SRC, dev.parent)
    d = yaml.safe_load(dev.read_text())
    d["configurations"]["dc"]["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


def render(dev, out):
    r = subprocess.run([sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-600:]
    return (out / "s9510-28dc.dc.front.svg").read_text()


def errors_for(dev, data):
    with lint.collecting() as got:
        lint.lint_device_occupants(dev, data, [str(LIB)])
    return [e for e in got.errors if "[L12]" in e]


def test_bare_and_fitted_are_the_same_device(tmp_path):
    """One manifest, two drawings."""
    bare = render(SRC / "device.yaml", tmp_path / "bare")
    fitted = render(fitted_copy(tmp_path, {p: "generic/sfp-lc@1" for p in PORTS}),
                    tmp_path / "fitted")
    assert bare.count('data-ref="generic/sfp-lc@1') == 0
    assert fitted.count('data-ref="generic/sfp-lc@1') == 4


def test_the_optic_lands_where_the_mate_points_meet(tmp_path):
    """Not "near the port" - ON it. If this drifts, occupants grew their own
    positioning path and the whole reason for the sugar is gone."""
    svg = render(fitted_copy(tmp_path, {"port-4": "generic/sfp-lc@1"}), tmp_path / "o")
    grab = lambda p: [float(v) for v in re.search(
        rf'<g[^>]*data-path="{p}"[^>]*transform="translate\(([^)]+)\)"', svg).group(1).split(",")]
    hx, hy = grab("port-4")
    ox, oy = grab("port-4-occupant")
    hm = yaml.safe_load((LIB / "components/std/sfp-ganged/v1/contract.yaml")
                        .read_text())["connection-points"]["mate"]["at"]
    om = yaml.safe_load((LIB / "components/generic/sfp-lc/v1/contract.yaml")
                        .read_text())["connection-points"]["mate"]["at"]
    assert abs((hx + hm[0]) - (ox + om[0])) < 0.01
    assert abs((hy + hm[1]) - (oy + om[1])) < 0.01


def test_the_interface_check_reaches_a_configuration(tmp_path):
    """A QSFP generic declared into an SFP cage is an error wherever it was
    declared - right about position, silent about fit would be the worse half."""
    dev = fitted_copy(tmp_path, {"port-4": "generic/qsfp-lc@1"})
    errs = errors_for(dev, yaml.safe_load(dev.read_text()))
    assert any("mates 'qsfp'" in e and "presents 'sfp'" in e for e in errs), errs


def test_an_occupant_must_plug_into_something(tmp_path):
    dev = fitted_copy(tmp_path, {"port-999": "generic/sfp-lc@1"})
    errs = errors_for(dev, yaml.safe_load(dev.read_text()))
    assert any("names no placement in any view" in e for e in errs), errs


def test_the_library_is_clean():
    for man in libwalk.iter_devices([LIB]):
        assert not errors_for(man, yaml.safe_load(man.read_text())), man
```

The S9510-28DC's bare DC build is the configuration named `dc` (its siblings are `ac` and, until Task 7, `dc-populated`); the rendered filename `s9510-28dc.dc.front.svg` follows it.

- [ ] **Step 2: Repoint the mate-forwarding test**

In `spec/tests/test_mate_forwarding.py`'s last test, replace `common/qsfp-transceiver@1` with `generic/qsfp-lc@1` in the injected line and rewrite the docstring's first paragraph to: `generic/qsfp-lc declares one skin and no default; seating it must not depend on a skin being named.`

- [ ] **Step 3: Run**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_occupants.py spec/tests/test_mate_forwarding.py -q`
Expected: PASS

- [ ] **Step 4: Full suite**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests -q -n auto`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add spec/tests/test_occupants.py spec/tests/test_mate_forwarding.py
git commit -F /path/to/msg.txt
```

---

### Task 9: README — adding an optic

**Files:**
- Modify: `library/components/README.md` (new `## Adding an optic` section before `## What lint will say`, line 244)

**Interfaces:**
- Consumes: `generic/sfp-lc@1`.

- [ ] **Step 1: Write the section**

````markdown
## Adding an optic

A transceiver in this library is a GENERIC - one drawn part per form factor and
face under `generic/`, standing for every module of its kind and carrying no
rate. A vendor's optic is a WRAPPER around one: it composes the generic, sets the
generic's colour and label, and carries the facts that make it that product.

```yaml
# library/components/cisco/sfp-10g-lr/v1/contract.yaml
format: 1
kind: component
name: sfp-10g-lr
version: 1.0.0
class: transceiver
behaviour: occupies
mates: sfp                      # must equal the generic's
profile: networking
description: Cisco SFP-10G-LR, 10GBASE-LR, 1310 nm, 10 km over OS2.
size: {w: <the generic's w>, h: <the generic's h>, d: <the generic's d>}
attrs: {model: SFP-10G-LR, media: sfp-plus, speed: 10g, reach: 10km,
        wavelength: 1310nm, power-draw-max-w: 1.0}
provenance:
  size: 'the generic it wraps - generic/sfp-lc@1 - which conforms to sfp-module'
  power: 'datasheet - Cisco SFP-10G-LR data sheet, maximum power consumption 1 W'
parts:
  - {ref: generic/sfp-lc@1, id: body, at: [0, 0],
     attrs: {latch-color: '#2f5fa8', label: SFP-10G-LR}}
skins: [default]
```

What goes where:

- **On the wrapper:** `model`, `media` (the rate family the port group speaks -
  `sfp-plus`, `sfp28`, `qsfp28` ...), `speed`, `reach`, `wavelength`,
  `power-draw-max-w`, and a `provenance.power` sentence naming the datasheet.
  L99 refuses every one of these on a `generic/` part, which is how the split
  stays true.
- **Passed to the generic:** `latch-color` and `label`, as `attrs` on the
  `parts:` entry. They are `fields` on the generic and the skin reads them; a
  colour is a field, not a second drawing (#177).
- **Never on either:** a rate in a component NAME. `sfp28-lr` is refused; the
  name is the vendor's part number.

The wrapper seats exactly where the generic would - a composed part presents the
mate point of what it wraps (#54) - so nothing about cages, `occupants:` or L12
changes for a vendor part. An optic whose shape is NOT the generic's (a long-body
SC SFP+, a module with a nose heat sink) draws its own contract in the vendor
namespace with the same `mates:` and the same connection-points, and seats the
same way.
````

- [ ] **Step 2: Run the README-reading tests**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_components_catalogue.py spec/tests/test_device_template.py -q`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add library/components/README.md
git commit -F /path/to/msg.txt
```

---

### Task 10: `generic/sfp-lc-simplex` (sfp-sc GATED — see the Task 4 ruling in the ledger: no free document dimensions the SC keyed opening, so the SC face waits for a drawing exactly as the MPO faces do; every `sfp-sc` step below is skipped)

**Files:**
- Create: `library/components/generic/sfp-lc-simplex/v1/{contract.yaml,skins/default.svg}`
- Create: `library/components/generic/sfp-sc/v1/{contract.yaml,skins/default.svg}`
- Modify: `library/components/std/sc-bore/v1/contract.yaml` (remove `unplaced:`)
- Test: `spec/tests/test_generic_sfp_faces.py`

**Interfaces:**
- Consumes: `generic/sfp-lc@1` (Task 5) as the template, `std/sc-bore@1` (Task 4).

- [ ] **Step 1: Write the failing test**

```python
"""The SFP faces that are not LC duplex: one LC (bidi) and SC simplex. Same
envelope, same latch, a different face - and the face is in the name
(docs/pluggables-design.md decision 4)."""
import json
import pathlib

import jsonschema
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

COMPONENT_SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())


def component_errors(path):
    """The rules a part test cares about, run the way the CLI runs them. L9 is a
    branch of `lint.lint_component`, not a function of its own; L11 and L99 are
    separate functions the CLI's component loop calls after it, so they are
    called here too - `lint_component` alone would never raise them."""
    d = yaml.safe_load(pathlib.Path(path).read_text())
    with lint.collecting() as got:
        lint.lint_component(path, jsonschema.Draft202012Validator(COMPONENT_SCHEMA))
        lint.lint_component_mating(path, d, [str(ROOT / "library")])
        lint.lint_component_generic(path, d)
        return list(got.errors)


def rule_errors(path, *rules):
    errs = component_errors(path)
    return [e for e in errs if any(f"[{r}]" in e for r in rules)]


def contract(name):
    return yaml.safe_load((LIB / f"components/generic/{name}/v1/contract.yaml").read_text())


def test_bidi_has_one_lc_bore_and_one_optical_point():
    d = contract("sfp-lc-simplex")
    assert d["mates"] == "sfp" and d["conforms"] == "sfp-module"
    assert [p["ref"] for p in d["parts"]] == ["std/lc-bore@3"]
    assert "optical" in d["connection-points"]
    assert "optical-tx" not in d["connection-points"]


def test_sc_composes_the_sc_bore():
    d = contract("sfp-sc")
    assert [p["ref"] for p in d["parts"]] == ["std/sc-bore@1"]
    assert d["attrs"]["face"] == "sc-simplex"


def test_both_share_the_sfp_envelope_and_protrude():
    lc = contract("sfp-lc")
    for name in ("sfp-lc-simplex", "sfp-sc"):
        d = contract(name)
        assert d["size"] == lc["size"], name
        body = next(f for f in d["relief"]["features"] if f["node"] == "body")
        assert body["out"] == next(f for f in lc["relief"]["features"] if f["node"] == "body")["out"]


def test_both_lint_clean():
    for name in ("sfp-lc-simplex", "sfp-sc"):
        p = LIB / f"components/generic/{name}/v1/contract.yaml"
        assert rule_errors(p, "L9", "L11", "L99") == [], name
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_generic_sfp_faces.py -q`
Expected: FAIL — `FileNotFoundError`

- [ ] **Step 3: Write the two parts**

Both copy `generic/sfp-lc/v1/contract.yaml` and its skin, then:

`sfp-lc-simplex`: `name`, `description` (one LC bore on the face's optical axis — a bidi carries transmit and receive on one fibre), `attrs.face: lc-simplex`, one part `{ref: std/lc-bore@3, id: bore, at: [<w/2 - 2.35>, 1.75], lift: <protrusion>, rotate: 180}`, `connection-points.optical` at the bore centre in place of `optical-tx`/`optical-rx`, `provenance.bores` rewritten: the bore is centred because no drawing of a bidi SFP face in the intake places it otherwise - `estimated`, and the sentence says what would settle it (a bidi module drawing). Skin: one keyed hole.

`sfp-sc`: `name`, `description` (one SC simplex bore - PON ONTs and the long-body OLT modules put an SC on an SFP), `attrs.face: sc-simplex`, one part `{ref: std/sc-bore@1, id: bore, at: [<centred>, <fits under the bail>], lift: <protrusion>}`, `connection-points.optical` at the bore centre, `provenance.bores`: centred, `estimated`, same caveat. Skin: one SC hole at `std/sc-bore`'s size.

Remove `unplaced:` from `std/sc-bore/v1/contract.yaml` - it is composed now.

- [ ] **Step 4: Run tests and lint**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_generic_sfp_faces.py spec/tests/test_sc_bore.py -q && PYTHONPATH=spec/tools python -m portrayal lint 2>&1 | grep -E "ERROR|LINT: ok"`
Expected: PASS; `LINT: ok`

- [ ] **Step 5: Commit**

```bash
git add library/components/generic/sfp-lc-simplex library/components/generic/sfp-sc library/components/std/sc-bore spec/tests/test_generic_sfp_faces.py
git commit -F /path/to/msg.txt
```

---

### Task 11: `generic/sfp-rj45`

**Files:**
- Create: `library/components/generic/sfp-rj45/v1/{contract.yaml,skins/default.svg}`
- Test: `spec/tests/test_generic_sfp_rj45.py`

**Interfaces:**
- Consumes: `generic/sfp-lc@1` as the template; `std/rj45-ganged@2` as the face.

- [ ] **Step 1: Write the failing test**

```python
"""A copper SFP: the SFP envelope with an RJ45 jack for a face."""
import json
import pathlib

import jsonschema
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/generic/sfp-rj45/v1/contract.yaml"

COMPONENT_SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())


def component_errors(path):
    """The rules a part test cares about, run the way the CLI runs them. L9 is a
    branch of `lint.lint_component`, not a function of its own; L11 and L99 are
    separate functions the CLI's component loop calls after it, so they are
    called here too - `lint_component` alone would never raise them."""
    d = yaml.safe_load(pathlib.Path(path).read_text())
    with lint.collecting() as got:
        lint.lint_component(path, jsonschema.Draft202012Validator(COMPONENT_SCHEMA))
        lint.lint_component_mating(path, d, [str(ROOT / "library")])
        lint.lint_component_generic(path, d)
        return list(got.errors)


def rule_errors(path, *rules):
    errs = component_errors(path)
    return [e for e in errs if any(f"[{r}]" in e for r in rules)]


def test_it_is_an_sfp_with_a_jack_for_a_face():
    d = yaml.safe_load(P.read_text())
    assert d["mates"] == "sfp" and d["conforms"] == "sfp-module"
    assert d["attrs"]["face"] == "rj45" and d["attrs"]["media"] == "copper"
    assert [p["ref"] for p in d["parts"]] == ["std/rj45-ganged@2"]
    assert "optical-tx" not in d["connection-points"]
    assert d["connection-points"]["net"]["direction"] == "front"


def test_it_lints_clean():
    assert rule_errors(P, "L9", "L11", "L99") == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_generic_sfp_rj45.py -q`
Expected: FAIL — `FileNotFoundError`

- [ ] **Step 3: Write the part**

Copy `generic/sfp-lc`; `name: sfp-rj45`; `attrs: {power-absent: not-applicable, form-factor: sfp, face: rj45, media: copper}`; one part `{ref: std/rj45-ganged@2, id: jack, at: [<centred in w>, <under the bail>], lift: <protrusion>}` - `std/rj45-ganged@2` is 12.7 x 11.0 and the SFP face is 8.5 tall, so read the jack's own `size` and decide with the spec's open question: if it does not fit under the bail, compose it at the face's own centre and record in `provenance.face` that a copper SFP's jack opening is the module's full height and the bail sits above it in the module body, `estimated`, with what would settle it (a copper SFP drawing - e.g. a 10GBASE-T SFP+ datasheet's mechanical page). `connection-points.net` at the jack's centre in place of the optical points. Skin: the jack opening as a hole, no bores.

- [ ] **Step 4: Run tests and lint**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_generic_sfp_rj45.py -q && PYTHONPATH=spec/tools python -m portrayal lint 2>&1 | grep -E "sfp-rj45|ERROR|LINT: ok"`
Expected: PASS; `LINT: ok` (L76's RJ45-family rule reads placements on DEVICES, not a jack composed inside a transceiver; if it fires here, record the finding in the contract's `lint:` block with the reason and do not silence the rule).

- [ ] **Step 5: Commit**

```bash
git add library/components/generic/sfp-rj45 spec/tests/test_generic_sfp_rj45.py
git commit -F /path/to/msg.txt
```

---

### Task 12: `generic/qsfp-dd-lc`

**Files:**
- Create: `library/components/generic/qsfp-dd-lc/v1/{contract.yaml,skins/default.svg}`
- Test: `spec/tests/test_generic_qsfp_dd_lc.py`

**Interfaces:**
- Consumes: `qsfp-dd-module` (Task 3), `generic/qsfp-lc@1` (Task 6) as the template.

- [ ] **Step 1: Write the failing test**

Copy `spec/tests/test_generic_qsfp_lc.py` to `test_generic_qsfp_dd_lc.py`; `P` → `components/generic/qsfp-dd-lc/v1/contract.yaml`; `mates` → `"qsfp-dd"`; `conforms` → `"qsfp-dd-module"`; protrusion source → `"QSFP-DD"`.

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_generic_qsfp_dd_lc.py -q`
Expected: FAIL — `FileNotFoundError`

- [ ] **Step 3: Write the part**

Copy `generic/qsfp-lc`; `name: qsfp-dd-lc`; `mates: qsfp-dd`; `conforms: qsfp-dd-module`; `size` from the registry; `attrs.form-factor: qsfp-dd`; `relief.features.body.out` = registry depth less `std/qsfp-dd`'s registry depth (37.0), source naming QSFP-DD HW 6.3 Fig 47 and the cage entry; the LC face positions are `generic/qsfp-lc`'s (same 18.35 width by design - QSFP-DD HW 6.3 section 1) and `provenance.face-lc` says so and says QSFP-DD HW 6.3 Figure 31 draws the duplex LC receptacle and defers its dimensions to TIA-604-10, which is paywalled.

- [ ] **Step 4: Run tests and lint**

Run: `PYTHONPATH=spec/tools python -m pytest spec/tests/test_generic_qsfp_dd_lc.py -q && PYTHONPATH=spec/tools python -m portrayal lint 2>&1 | grep -E "qsfp-dd-lc|ERROR|LINT: ok"`
Expected: PASS; `LINT: ok`. Gate 5 against QSFP-DD HW 6.3 Figure 47.

- [ ] **Step 5: Commit**

```bash
git add library/components/generic/qsfp-dd-lc spec/tests/test_generic_qsfp_dd_lc.py
git commit -F /path/to/msg.txt
```

---

### Task 13: Gates, baseline, PR

**Files:**
- Modify: `library/components/CATALOGUE.md`, `library/lint-baseline.json`, `library/exports/**`, `docs/lint-rules.md` (all generated)

- [ ] **Step 1: Every gate, in order**

```bash
PYTHONPATH=spec/tools python -m portrayal lock
PYTHONPATH=spec/tools python -m portrayal lint
PYTHONPATH=spec/tools python -m portrayal build
./publish.sh --no-images
PYTHONPATH=spec/tools python3 spec/tools/portrayal/components_catalogue.py --library library > library/components/CATALOGUE.md
python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md
PYTHONPATH=spec/tools python -m pytest spec/tests -q -n auto
```

Expected: `devicelock: 0 finding(s)`; lint reports only NEW warnings that are L27 on the generics if any (they carry `power-absent`, so none expected) and nothing else - if a new warning appears, it is a finding to fix, not to baseline; `LINT: ok`; suite passes twice running.

- [ ] **Step 2: Baseline only what the spec says is expected**

Run `PYTHONPATH=spec/tools python -m portrayal lint --new-only`. If the only new lines are warnings the spec anticipates, `--update-baseline`; otherwise fix first.

- [ ] **Step 3: Open the PR**

Base `main`. Title: `generic/ transceivers: one drawn part per form and face, off the MSAs`. Body: what landed per task, the Gate-5 sentences from Tasks 5, 6 and 12, the five devices made bare, and the two `common/` majors marked superseded. Ends with the attribution line.

---

## Self-review notes

- **Spec coverage:** §1 namespace → Task 1; §2 envelopes → Task 3; §3 generics → Tasks 5, 6, 10, 11, 12 (MPO faces and OSFP are gated in the spec and deliberately absent here; XFP/CFP are the spec's second batch); §4 sc-bore → Task 4; §5 L99 → Task 2; §6 README → Task 9; §7 migration → Tasks 7, 8 (fixture idiom is copy-and-inject, which is what `test_mate_forwarding` already does — the spec's "fixture device" is satisfied without a hand-built manifest); §8 DCIM → Task 4; umbrella decision 9 → the `test_it_protrudes_from_day_one` assertion in every generic's test.
- **Type consistency:** `lint.lint_component_generic(path, data, _lib_roots=None)` in Task 2 is what Tasks 5, 6, 10, 11, 12 call; L9 is exercised through `lint.lint_component(path, validator)` via the `rule_errors(path, *rules)` helper repeated in each part's test (an engineer may read tasks out of order). `fields` keys are `latch-color` and `label` everywhere. `fitted_copy(tmp_path, occupants)` and `render(dev, out)` are defined in Task 8 and used only there.
- **Placeholders:** the `<...>` tokens are transcription points from named figures, by design; each names its figure.
