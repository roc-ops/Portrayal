# Optical Vocabulary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a contract state the glass inside a passive optical module - which
fibre runs from which connector position to which - and make lint check it,
proved on six Smartoptics PPMs that already exist.

**Architecture:** A connector component declares how many fibre positions it
presents (`optical.positions`), stated once and inherited by every module that
composes it. A module declares `optical.paths` between `<part-id>.<n>` endpoints;
a path may split into several destinations with ratios. Positions no path reaches
are declared in `optical.unused` with a reason. Five lint rules make every one of
those statements checkable. Nothing renders and nothing exports in this plan -
that is plans 3 and 4.

**Tech Stack:** Python 3.12, PyYAML, jsonschema (draft 2020-12), pytest. No new
dependencies.

**Spec:** `docs/optical-paths-design.md` (sections A and D; C4 and E1 for context)

## Global Constraints

- **Gate chain, in this order, after every task that touches `library/` or
  `spec/`:**
  `python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library`
  then `./publish.sh --no-images`
  then `python3 spec/tools/portrayal/devicelock.py --library library`
  then `python3 -m pytest spec/tests -q`
- **Lint baseline is `LINT: ok (654 files, 1291 warnings in 22 rules)`.** A task
  may add rules; it must not add warnings to existing files.
- **pytest baseline is 1357 passed, 1 skipped.** Tasks only add.
- **Expected totals in each task are a GUIDE, not a gate.** The binding check is
  that nothing FAILED and the total only went up. If a total differs from what a
  task predicts but no test failed, say so in the report and carry on - unrelated
  work can land tests between tasks, and a plan that forces an exact number
  invites someone to make the number right rather than the suite.
- **Version bumps happen BEFORE `devicelock.py --update`, never after.**
- **`working/` is never committed.** Reference material stays there.
- **Run every command from the worktree root.** Do not `cd` to the main checkout.
- **Never use bare `git stash`.** The stash stack is shared across worktrees.
- New lint rules are errors (`err`), not warnings, only when the library already
  satisfies them. Rule L78-L82 below all land clean.
- Commit messages end with:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

## File Structure

| file | responsibility |
|---|---|
| `spec/schemas/component.schema.json` | add `optical` to component properties; validate shape only, not consistency |
| `spec/tools/portrayal/optical.py` | **new.** Resolve a contract's optical graph: expand endpoints, look up connector capacity, return a normalised structure. One module because five lint rules and, later, the exporter all need the same resolution |
| `spec/tools/portrayal/lint.py` | register rules L78-L82, each a thin caller of `optical.py` |
| `spec/tests/test_optical_resolve.py` | **new.** Unit tests for `optical.py` against synthetic contracts |
| `spec/tests/test_optical_lint.py` | **new.** Each rule fires on its defect and stays quiet on the legitimate case |
| `library/components/common/lc-duplex-adapter/v3/contract.yaml` | gains `optical.positions: 2` |
| `library/components/smartoptics/ppm-ocu-50-50/v1/contract.yaml` | gains a split path and a declared dead position |
| `library/components/smartoptics/ppm-ocu-97-3/v1/contract.yaml` | as above, 97/3 |
| `library/components/smartoptics/ppm-dcm-{10,20,40,80}/v1/contract.yaml` | gain a two-ended path |

**Why `optical.py` is its own module:** the rules all need the same three things -
resolve `<part-id>.<n>` to a real composed part, find that part's declared
capacity by reading its contract, and walk the paths. Putting that in `lint.py`
would grow a 5900-line file and leave the exporter (plan 4) duplicating it.

---

### Task 1: The connector declares its fibre capacity

**Files:**
- Modify: `spec/schemas/component.schema.json`
- Modify: `library/components/common/lc-duplex-adapter/v3/contract.yaml`
- Test: `spec/tests/test_optical_resolve.py`

**Interfaces:**
- Consumes: nothing
- Produces: `optical.positions` (integer >= 1) valid on any component contract;
  `common/lc-duplex-adapter@3` declares `2`

- [ ] **Step 1: Write the failing test**

Create `spec/tests/test_optical_resolve.py`:

```python
"""The optical graph, resolved from a contract.

A connector states how many fibre positions it presents, ONCE, and every module
that composes it inherits that. The alternative - restating capacity per module -
is 77 chances to type 12 as 21 on the FS line alone.
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))


def contract(ref):
    """`common/lc-duplex-adapter@3` -> its parsed contract."""
    name, major = ref.split("@")
    return yaml.safe_load(
        (LIB / "components" / name / f"v{major}" / "contract.yaml").read_text())


def test_the_lc_duplex_adapter_presents_two_fibre_positions():
    c = contract("common/lc-duplex-adapter@3")
    assert (c.get("optical") or {}).get("positions") == 2, (
        "an LC DUPLEX adapter is two bores. If this is absent, every module "
        "composing it has no capacity to check its paths against")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest spec/tests/test_optical_resolve.py -q`
Expected: FAIL — `assert None == 2`

- [ ] **Step 3: Add `optical` to the component schema**

In `spec/schemas/component.schema.json`, inside the top-level `"properties"`
object, add this entry (alphabetical placement is not enforced; put it after
`"mates"`):

```json
"optical": {
 "type": "object",
 "additionalProperties": false,
 "description": "THE GLASS. A connector states `positions` - how many fibre positions it presents, 2 for an LC duplex, 12 for an MPO-12 - and states nothing else. A module that CONTAINS fibre states `paths` between `<part-id>.<n>` endpoints, and `unused` for any position no path reaches. See docs/optical-paths-design.md: the reason to model strands rather than a port-to-port table is that a table cannot express a tap, a splice, a conversion or a mesh, which are two thirds of the FS FHD catalogue.",
 "properties": {
  "positions": {
   "type": "integer",
   "minimum": 1,
   "description": "fibre positions this CONNECTOR presents. Stated once here and inherited by every module that composes it; a module never restates it."
  },
  "media": {
   "$ref": "#/$defs/segment",
   "description": "fibre type every path uses unless it overrides: os2, om3, om4, om5"
  },
  "polarity": {
   "$ref": "#/$defs/segment",
   "description": "the vendor's polarity name (a, af, b, universal). CHECKED against the paths, never a substitute for them - it is the claim, the paths are the evidence."
  },
  "paths": {
   "type": "array",
   "minItems": 1,
   "items": {
    "type": "object",
    "additionalProperties": false,
    "required": ["from", "to"],
    "properties": {
     "from": {"$ref": "#/$defs/optical-endpoint"},
     "to": {
      "oneOf": [
       {"$ref": "#/$defs/optical-endpoint"},
       {
        "type": "array",
        "minItems": 2,
        "items": {
         "type": "object",
         "additionalProperties": false,
         "required": ["at", "ratio"],
         "properties": {
          "at": {"$ref": "#/$defs/optical-endpoint"},
          "ratio": {"type": "number", "exclusiveMinimum": 0, "maximum": 100}
         }
        }
       }
      ],
      "description": "one endpoint, or a list of endpoints with ratios summing to 100 - which is what a tap or a coupler is"
     },
     "media": {"$ref": "#/$defs/segment"},
     "band": {
      "type": "object",
      "additionalProperties": false,
      "required": ["centre-nm"],
      "description": "this path carries only this band; absent means it carries whatever is left. An add/drop filter is two paths off one endpoint, one banded and one not.",
      "properties": {
       "centre-nm": {"type": "number", "exclusiveMinimum": 0},
       "width-nm": {"type": "number", "exclusiveMinimum": 0}
      }
     }
    }
   }
  },
  "unused": {
   "type": "object",
   "propertyNames": {"$ref": "#/$defs/optical-endpoint"},
   "additionalProperties": {"type": "string", "minLength": 20},
   "description": "positions no path reaches, and WHY - prose long enough that a bare marker will not validate, because the claim is about the hardware. L80 checks both ways: an unreached position with no entry is an error, and an entry for a position a path DOES reach is an error."
  }
 }
}
```

And in the `"$defs"` object, add:

```json
"optical-endpoint": {
 "type": "string",
 "pattern": "^[a-z0-9-]+\\.[1-9][0-9]*$",
 "description": "`<part-id>.<n>` - a composed part's id and a 1-based fibre position within it"
}
```

- [ ] **Step 4: Declare the adapter's capacity**

In `library/components/common/lc-duplex-adapter/v3/contract.yaml`, bump
`version: 3.2.0` to `3.3.0`, and add before `parts:`:

```yaml
optical:
  # TWO BORES, SO TWO FIBRE POSITIONS, and position order is the order the bores
  # are composed below: 1 is `tx`, 2 is `rx`. Stated here so no module composing
  # this adapter has to restate it - on the FS FHD line that would be 77 chances
  # to mistype a number the adapter already knows.
  positions: 2
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python3 -m pytest spec/tests/test_optical_resolve.py -q`
Expected: PASS (1 passed)

- [ ] **Step 6: Run the gate chain**

```bash
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library | tail -1
```
Expected: `LINT: ok (654 files, 1291 warnings in 22 rules)` — unchanged.

```bash
./publish.sh --no-images | tail -1
python3 spec/tools/portrayal/devicelock.py --library library | tail -1
```
Expected: devicelock reports findings for devices composing the adapter. If it
does, bump those devices' versions, then re-run with `--update`. Then:

```bash
python3 -m pytest spec/tests -q | tail -1
```
Expected: `1358 passed, 1 skipped`

- [ ] **Step 7: Commit**

```bash
git add spec/schemas/component.schema.json spec/tests/test_optical_resolve.py library/
git commit -m "optical: a connector states its fibre positions once

An LC duplex adapter is two bores. Saying so on the adapter means no module
composing it restates the number - on the FS FHD line that would be 77 chances
to mistype what the adapter already knows.

The schema also gains the rest of the optical vocabulary (paths, splits, bands,
unused) so the shape is fixed before anything uses it; nothing reads it yet.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Resolve a contract's optical graph

**Files:**
- Create: `spec/tools/portrayal/optical.py`
- Test: `spec/tests/test_optical_resolve.py` (append)

**Interfaces:**
- Consumes: `optical.positions` from Task 1
- Produces:
  - `split_endpoint(ep: str) -> tuple[str, int]` — `"mtp-1.3"` -> `("mtp-1", 3)`
  - `capacities(contract: dict, load_ref) -> dict[str, int]` — composed part id ->
    fibre positions, for every part whose contract declares `optical.positions`.
    `load_ref` is a callable taking `"common/lc-duplex-adapter@3"` and returning
    a parsed contract dict, so callers choose how contracts are found.
  - `endpoints(path: dict) -> list[tuple[str, float | None]]` — every endpoint a
    path touches as `(endpoint, ratio)`, source first with ratio `None`
  - `reached(contract: dict) -> set[str]` — every endpoint any path touches

- [ ] **Step 1: Write the failing tests**

Append to `spec/tests/test_optical_resolve.py`:

```python
import optical  # noqa: E402


def test_an_endpoint_splits_into_a_part_id_and_a_position():
    assert optical.split_endpoint("mtp-1.3") == ("mtp-1", 3)
    assert optical.split_endpoint("common.12") == ("common", 12)


def test_capacities_come_from_the_composed_parts_contracts():
    """The module names parts; the PARTS know how many fibres they hold."""
    c = {"parts": [{"ref": "common/lc-duplex-adapter@3", "id": "common"},
                   {"ref": "common/lc-duplex-adapter@3", "id": "split"},
                   {"ref": "common/led-dot@1", "id": "lamp"}]}
    loaded = {"common/lc-duplex-adapter@3": {"optical": {"positions": 2}},
              "common/led-dot@1": {}}
    assert optical.capacities(c, loaded.get) == {"common": 2, "split": 2}, (
        "a part with no optical block is not a connector and must not appear")


def test_a_two_ended_path_yields_its_two_endpoints():
    p = {"from": "dcm.2", "to": "dcm.1"}
    assert optical.endpoints(p) == [("dcm.2", None), ("dcm.1", None)]


def test_a_split_path_yields_every_destination_with_its_ratio():
    p = {"from": "common.1",
         "to": [{"at": "split.1", "ratio": 97}, {"at": "split.2", "ratio": 3}]}
    assert optical.endpoints(p) == [
        ("common.1", None), ("split.1", 97), ("split.2", 3)]


def test_reached_is_every_endpoint_any_path_touches():
    c = {"optical": {"paths": [
        {"from": "common.1", "to": [{"at": "split.1", "ratio": 50},
                                    {"at": "split.2", "ratio": 50}]}]}}
    assert optical.reached(c) == {"common.1", "split.1", "split.2"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest spec/tests/test_optical_resolve.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'optical'`

- [ ] **Step 3: Write the implementation**

Create `spec/tools/portrayal/optical.py`:

```python
#!/usr/bin/env python3
"""Resolve the optical graph a contract declares.

WHY A MODULE AND NOT A LINT RULE. Five rules and, later, the DCIM exporter all
need the same three things: turn `<part-id>.<n>` into a part and a position, ask
that part's own contract how many positions it has, and walk the paths. Written
once here, that is a hundred lines; written per consumer it is the same hundred
lines diverging.

Nothing here validates. These functions answer questions; lint decides which
answers are errors. That split is what lets the exporter reuse them without
inheriting lint's opinions.
"""
import re

ENDPOINT = re.compile(r"^([a-z0-9-]+)\.([1-9][0-9]*)$")


def split_endpoint(ep):
    """`mtp-1.3` -> `('mtp-1', 3)`. Raises ValueError on anything else."""
    m = ENDPOINT.match(ep or "")
    if not m:
        raise ValueError(f"not an optical endpoint: {ep!r}")
    return m.group(1), int(m.group(2))


def capacities(contract, load_ref):
    """Composed part id -> fibre positions, for parts that declare them.

    A part with no `optical.positions` is not a connector - a lamp, a latch, a
    silkscreen - and is absent from the result rather than present with zero.
    The difference matters: absent means "not a connector", zero would mean "a
    connector with no fibres", and only one of those is a thing.
    """
    out = {}
    for part in contract.get("parts") or []:
        if not isinstance(part, dict) or not part.get("id"):
            continue
        ref = load_ref(part["ref"]) or {}
        n = (ref.get("optical") or {}).get("positions")
        if n:
            out[str(part["id"])] = int(n)
    return out


def endpoints(path):
    """Every endpoint a path touches, source first, as `(endpoint, ratio)`.

    The source carries ratio None because it is not a share of anything; a
    two-ended path's destination carries None for the same reason.
    """
    out = [(path["from"], None)]
    to = path["to"]
    if isinstance(to, str):
        out.append((to, None))
    else:
        out += [(d["at"], d["ratio"]) for d in to]
    return out


def reached(contract):
    """Every endpoint any path in this contract touches."""
    out = set()
    for path in ((contract.get("optical") or {}).get("paths") or []):
        out.update(ep for ep, _ in endpoints(path))
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest spec/tests/test_optical_resolve.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add spec/tools/portrayal/optical.py spec/tests/test_optical_resolve.py
git commit -m "optical: resolve a contract's graph, once, for every consumer

Five lint rules and the DCIM exporter all need the same three answers: what part
and position is this endpoint, how many positions does that part have, and what
does this path touch. Written once here; written per consumer it is the same
hundred lines diverging.

Nothing here validates - these functions answer questions and lint decides which
answers are errors, which is what lets the exporter reuse them without
inheriting lint's opinions.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: L78 - every endpoint is real

**Files:**
- Modify: `spec/tools/portrayal/lint.py` (RULES table; new rule function; dispatch in `main`)
- Modify: `docs/lint-rules.md` (regenerated)
- Test: `spec/tests/test_optical_lint.py` (create)

**Interfaces:**
- Consumes: `optical.split_endpoint`, `optical.capacities`, `optical.endpoints`
- Produces: `lint_component_optical_endpoints(path, data, lib_roots)` raising
  `err(..., "L78", ...)`

- [ ] **Step 1: Write the failing test**

Create `spec/tests/test_optical_lint.py`:

```python
"""The optical rules fire on their defect and stay quiet on the real thing.

Each rule gets both halves. A rule that only ever fires is as useless as one
that never does, and the quiet half is the one that breaks silently when a
predicate is tightened - which is how a fixture that could not tell `!seen` from
`!seen && named` shipped in this repo before.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))
import lint as L  # noqa: E402

LIB = [str(ROOT / "library")]


def run(rule, doc, code=None, path="t/contract.yaml"):
    """Call ONE rule and return ONLY its errors.

    Every optical rule takes `(path, data, lib_roots)` - the ones that do not
    need the roots accept and ignore them - so one call shape serves all three.

    Filtering on a substring like "L8" would also catch L80 while testing L81,
    and would quietly pass if a rule started raising under the wrong code, so
    `code` narrows to one rule when a test cares which fired.
    """
    L.ERRORS.clear()
    rule(path, doc, LIB)
    return [e for e in L.ERRORS
            if code is None or f"[{code}]" in e]


def module(paths, parts=None, unused=None):
    """A module composing two LC duplex adapters, which hold 2 positions each."""
    doc = {"kind": "module", "size": {"w": 55.4, "h": 19.5},
           "parts": parts if parts is not None else [
               {"ref": "common/lc-duplex-adapter@3", "id": "common"},
               {"ref": "common/lc-duplex-adapter@3", "id": "split"}],
           "optical": {"media": "os2", "paths": paths}}
    if unused:
        doc["optical"]["unused"] = unused
    return doc


def test_a_position_past_the_connectors_capacity_is_caught():
    hits = run(L.lint_component_optical_endpoints,
               module([{"from": "common.3", "to": "split.1"}]))
    assert len(hits) == 1, hits
    assert "common.3" in hits[0] and "2" in hits[0]


def test_an_endpoint_naming_no_composed_part_is_caught():
    hits = run(L.lint_component_optical_endpoints,
               module([{"from": "mtp-1.1", "to": "split.1"}]))
    assert len(hits) == 1 and "mtp-1" in hits[0], hits


def test_a_path_within_capacity_is_silent():
    assert run(L.lint_component_optical_endpoints,
               module([{"from": "common.1", "to": "split.2"}])) == []


def test_a_split_destination_is_checked_like_any_other_endpoint():
    """The ratio form must not be a hole the checker walks past."""
    hits = run(L.lint_component_optical_endpoints,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 50},
                               {"at": "split.9", "ratio": 50}]}]))
    assert len(hits) == 1 and "split.9" in hits[0], hits
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest spec/tests/test_optical_lint.py -q`
Expected: FAIL — `AttributeError: module 'lint' has no attribute 'lint_component_optical_endpoints'`

- [ ] **Step 3: Add the rule**

In `spec/tools/portrayal/lint.py`, add to the `RULES` dict after the `"L77"`
entry:

```python
    "L78": ("component",  "an optical endpoint names a composed connector and a position it has", "fix the part id or the position number"),
```

Add the import. `lint.py` already imports three sibling modules in one block -
`import attrsections as attrs_mod`, `import capability`, `import devicelock`,
around line 102. Put it in that block, after `import devicelock`:

```python
import optical
```

(A sibling import works because the tool's own directory is on `sys.path` when
it runs as a script, and the tests put it there explicitly before importing
`lint`.)

Add this function immediately before `def lint_component_fields(`:

```python
def _optical_load_ref(lib_roots):
    """A `load_ref` for optical.capacities that reads from the library roots."""
    def load(ref):
        return _contract(ref, lib_roots) or {}
    return load


def lint_component_optical_endpoints(path, data, lib_roots):
    """L78: an optical endpoint names a composed connector and a position it has.

    `mtp-1.13` on an MPO-12 is not a near miss, it is a fibre that does not
    exist - and without this rule it is also silent, because nothing downstream
    looks up a position it was never told about. The capacity comes from the
    CONNECTOR's own contract, so this also catches an endpoint naming a part
    that is not a connector at all: a path into a status lamp.
    """
    opt = data.get("optical") or {}
    paths = opt.get("paths") or []
    if not paths:
        return
    caps = optical.capacities(data, _optical_load_ref(lib_roots))
    for p in paths:
        for ep, _ratio in optical.endpoints(p):
            try:
                part, pos = optical.split_endpoint(ep)
            except ValueError:
                err(path, "L78", f"{ep!r} is not an optical endpoint - they are "
                                 "`<part-id>.<n>` with n from 1")
                continue
            if part not in caps:
                err(path, "L78", f"{ep} names {part!r}, which this part either "
                                 "does not compose or which declares no "
                                 "`optical.positions` - only a connector can "
                                 "carry a fibre")
            elif pos > caps[part]:
                err(path, "L78", f"{ep} asks for position {pos} and {part} "
                                 f"presents {caps[part]}")
```

Register it in `main`, immediately before the `lint_component_sink_context(f, d)`
line:

```python
                lint_component_optical_endpoints(f, d, args.library)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest spec/tests/test_optical_lint.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Regenerate the rules page and check the catalogue tests**

```bash
python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md
python3 -m pytest spec/tests/test_lint_rules_catalogue.py -q
```
Expected: PASS (7 passed)

- [ ] **Step 6: Run the gate chain**

```bash
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library | tail -1
```
Expected: `LINT: ok (654 files, 1291 warnings in 22 rules)` — no contract declares
`optical.paths` yet, so the rule finds nothing.

```bash
python3 -m pytest spec/tests -q | tail -1
```
Expected: `1367 passed, 1 skipped`

- [ ] **Step 7: Commit**

```bash
git add spec/tools/portrayal/lint.py spec/tests/test_optical_lint.py docs/lint-rules.md
git commit -m "lint: L78 - an optical endpoint names a connector and a position it has

mtp-1.13 on an MPO-12 is not a near miss, it is a fibre that does not exist, and
without this it is silent: nothing downstream looks up a position it was never
told about. Because capacity comes from the connector's own contract, the same
rule catches a path routed into a status lamp.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: L79 - no position is claimed twice, and split ratios sum to 100

**Files:**
- Modify: `spec/tools/portrayal/lint.py`
- Modify: `docs/lint-rules.md` (regenerated)
- Test: `spec/tests/test_optical_lint.py` (append)

**Interfaces:**
- Consumes: `optical.endpoints`
- Produces: `lint_component_optical_conflicts(path, data, _lib_roots=None)` -
  takes `_lib_roots` and ignores it, so `run()` in the test file can call every
  rule the same way

- [ ] **Step 1: Write the failing tests**

Append to `spec/tests/test_optical_lint.py`:

```python
def test_two_paths_landing_on_one_position_are_caught():
    hits = run(L.lint_component_optical_conflicts,
               module([{"from": "common.1", "to": "split.1"},
                       {"from": "common.2", "to": "split.1"}]))
    assert len(hits) == 1 and "split.1" in hits[0], hits


def test_one_source_feeding_two_destinations_is_NOT_a_conflict():
    """That is a split, which is the whole point of the graph form."""
    assert run(L.lint_component_optical_conflicts,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 50},
                               {"at": "split.2", "ratio": 50}]}])) == []


def test_ratios_that_do_not_sum_to_100_are_caught():
    hits = run(L.lint_component_optical_conflicts,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 70},
                               {"at": "split.2", "ratio": 40}]}]))
    assert len(hits) == 1 and "110" in hits[0], hits


def test_a_97_3_split_sums_and_is_silent():
    assert run(L.lint_component_optical_conflicts,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 97},
                               {"at": "split.2", "ratio": 3}]}])) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest spec/tests/test_optical_lint.py -q`
Expected: FAIL — `AttributeError: ... 'lint_component_optical_conflicts'`

- [ ] **Step 3: Add the rule**

Add to `RULES` after `"L78"`:

```python
    "L79": ("component",  "no fibre position is claimed twice, and a split's ratios sum to 100", "remove the duplicate path, or fix the ratios"),
```

Add after `lint_component_optical_endpoints`:

```python
def lint_component_optical_conflicts(path, data, _lib_roots=None):
    """L79: no position is claimed twice, and a split's ratios sum to 100.

    A DESTINATION IS EXCLUSIVE, A SOURCE IS NOT. Two strands landing in one bore
    is a contradiction - a bore takes one ferrule. One source reaching several
    destinations is a SPLIT, which is exactly what a tap and a coupler are, so
    counting sources as conflicts would reject the parts this vocabulary exists
    for. The check is therefore on destinations only.

    Ratios are checked here rather than in the schema because the schema can say
    a ratio is a number and cannot say two of them add up. 70/40 validates and
    is wrong.
    """
    paths = (data.get("optical") or {}).get("paths") or []
    seen = {}
    for i, p in enumerate(paths):
        eps = optical.endpoints(p)
        for ep, _r in eps[1:]:
            if ep in seen:
                err(path, "L79", f"{ep} is the destination of two paths "
                                 f"({seen[ep]} and {i}) - a fibre position "
                                 "takes one ferrule")
            seen[ep] = i
        ratios = [r for _e, r in eps[1:] if r is not None]
        if ratios:
            total = round(sum(ratios), 6)
            if total != 100:
                err(path, "L79", f"path {i} from {p['from']} splits into ratios "
                                 f"summing to {total:g}, not 100")
```

Register it in `main` immediately after the `lint_component_optical_endpoints`
line:

```python
                lint_component_optical_conflicts(f, d)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest spec/tests/test_optical_lint.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Regenerate the rules page**

```bash
python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md
python3 -m pytest spec/tests/test_lint_rules_catalogue.py -q
```
Expected: PASS (7 passed)

- [ ] **Step 6: Run the gate chain**

```bash
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library | tail -1
python3 -m pytest spec/tests -q | tail -1
```
Expected: lint unchanged at the baseline; `1371 passed, 1 skipped`

- [ ] **Step 7: Commit**

```bash
git add spec/tools/portrayal/lint.py spec/tests/test_optical_lint.py docs/lint-rules.md
git commit -m "lint: L79 - a position is claimed once, and a split's ratios sum

A destination is exclusive and a source is not: two strands in one bore is a
contradiction, one source reaching several destinations is a split, and counting
sources as conflicts would reject the taps and couplers this vocabulary exists
for.

Ratios are checked here and not in the schema because a schema can say a ratio
is a number and cannot say two of them add up. 70/40 validates and is wrong.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: L80 - every position is reached or declared unused

**Files:**
- Modify: `spec/tools/portrayal/lint.py`
- Modify: `docs/lint-rules.md` (regenerated)
- Test: `spec/tests/test_optical_lint.py` (append)

**Interfaces:**
- Consumes: `optical.capacities`, `optical.reached`
- Produces: `lint_component_optical_coverage(path, data, lib_roots)`

- [ ] **Step 1: Write the failing tests**

Append to `spec/tests/test_optical_lint.py`:

```python
def test_a_position_no_path_reaches_and_no_entry_declares_is_caught():
    """ppm-ocu-97-3's dead bore, which is currently a sentence in provenance."""
    hits = run(L.lint_component_optical_coverage,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 97},
                               {"at": "split.2", "ratio": 3}]}]))
    assert len(hits) == 1 and "common.2" in hits[0], hits


def test_declaring_it_unused_silences_it():
    assert run(L.lint_component_optical_coverage,
               module([{"from": "common.1",
                        "to": [{"at": "split.1", "ratio": 97},
                               {"at": "split.2", "ratio": 3}]}],
                      unused={"common.2": "three-port coupler in a four-bore "
                                          "faceplate"})) == []


def test_declaring_a_position_unused_that_a_path_DOES_reach_is_caught():
    """The rule has to bite both ways or `unused` becomes a way to silence it."""
    hits = run(L.lint_component_optical_coverage,
               module([{"from": "common.1", "to": "split.1"},
                       {"from": "common.2", "to": "split.2"}],
                      unused={"common.2": "this claim contradicts path 1 above"}))
    assert len(hits) == 1 and "common.2" in hits[0], hits
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest spec/tests/test_optical_lint.py -q`
Expected: FAIL — `AttributeError: ... 'lint_component_optical_coverage'`

- [ ] **Step 3: Add the rule**

Add to `RULES` after `"L79"`:

```python
    "L80": ("component",  "every fibre position is reached by a path or declared unused with a reason", "route it, or add an `optical.unused` entry saying why it terminates nothing"),
```

Add after `lint_component_optical_conflicts`:

```python
def lint_component_optical_coverage(path, data, lib_roots):
    """L80: every position is reached by a path or declared unused, with a reason.

    smartoptics/ppm-ocu-97-3@1 carries this in provenance today:

        THE SECOND BORE IS DEAD. It is captioned NA and terminates nothing.

    True, and unverifiable. A four-bore faceplate on a three-port coupler leaves
    one position with nothing behind it, and the difference between "nothing
    behind it" and "somebody forgot a path" is the whole question. Declaring it
    turns a sentence into a claim.

    IT BITES BOTH WAYS. An entry for a position a path DOES reach is also an
    error - otherwise `unused` becomes a way to silence the rule rather than a
    statement about the hardware, and the first person under time pressure finds
    that out.
    """
    opt = data.get("optical") or {}
    if not (opt.get("paths") or []):
        return
    caps = optical.capacities(data, _optical_load_ref(lib_roots))
    hit = optical.reached(data)
    unused = opt.get("unused") or {}
    for part, n in sorted(caps.items()):
        for pos in range(1, n + 1):
            ep = f"{part}.{pos}"
            if ep in hit and ep in unused:
                err(path, "L80", f"{ep} is declared unused and a path reaches "
                                 "it - one of the two is wrong")
            elif ep not in hit and ep not in unused:
                err(path, "L80", f"{ep} is a fibre position no path reaches and "
                                 "nothing declares. Route it, or add an "
                                 "`optical.unused` entry saying what terminates "
                                 "there")
```

Register it in `main` immediately after the `lint_component_optical_conflicts`
line:

```python
                lint_component_optical_coverage(f, d, args.library)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest spec/tests/test_optical_lint.py -q`
Expected: PASS (11 passed)

- [ ] **Step 5: Regenerate the rules page**

```bash
python3 spec/tools/portrayal/lint.py --list-rules --markdown > docs/lint-rules.md
python3 -m pytest spec/tests/test_lint_rules_catalogue.py -q
```
Expected: PASS (7 passed)

- [ ] **Step 6: Run the gate chain**

```bash
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library | tail -1
python3 -m pytest spec/tests -q | tail -1
```
Expected: lint at the baseline; `1374 passed, 1 skipped`

- [ ] **Step 7: Commit**

```bash
git add spec/tools/portrayal/lint.py spec/tests/test_optical_lint.py docs/lint-rules.md
git commit -m "lint: L80 - a position is reached, or declared unused with a reason

ppm-ocu-97-3 says in provenance that its second bore terminates nothing. True,
and unverifiable: the difference between 'nothing is behind it' and 'somebody
forgot a path' is the entire question, and prose cannot answer it.

The rule bites both ways. An entry for a position a path DOES reach is also an
error, because otherwise `unused` is a way to silence the rule rather than a
statement about the hardware, and the first person under time pressure finds
that out.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: The two OCU couplers state their glass

**Files:**
- Modify: `library/components/smartoptics/ppm-ocu-50-50/v1/contract.yaml`
- Modify: `library/components/smartoptics/ppm-ocu-97-3/v1/contract.yaml`
- Test: `spec/tests/test_optical_resolve.py` (append)

**Interfaces:**
- Consumes: everything above
- Produces: two library parts carrying `optical.paths` and `optical.unused`

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_optical_resolve.py`:

```python
def test_the_97_3_coupler_splits_its_common_port_in_that_ratio():
    """The part's function, which was the string `coupling-ratio: '97/3'`."""
    c = contract("smartoptics/ppm-ocu-97-3@1")
    paths = (c.get("optical") or {}).get("paths") or []
    assert len(paths) == 1, paths
    dests = {d["at"]: d["ratio"] for d in paths[0]["to"]}
    assert paths[0]["from"] == "common.1"
    assert dests == {"split.1": 97, "split.2": 3}


def test_the_couplers_dead_bore_is_a_declared_claim_not_a_sentence():
    c = contract("smartoptics/ppm-ocu-97-3@1")
    unused = (c.get("optical") or {}).get("unused") or {}
    assert "common.2" in unused and len(unused["common.2"]) >= 20


def test_the_50_50_coupler_splits_evenly():
    c = contract("smartoptics/ppm-ocu-50-50@1")
    dests = {d["at"]: d["ratio"] for d in c["optical"]["paths"][0]["to"]}
    assert dests == {"split.1": 50, "split.2": 50}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest spec/tests/test_optical_resolve.py -q`
Expected: FAIL — `assert 0 == 1` (no paths)

- [ ] **Step 3: Add the optical block to ppm-ocu-97-3**

In `library/components/smartoptics/ppm-ocu-97-3/v1/contract.yaml`, bump
`version: 1.0.0` to `1.1.0` and add immediately before `relief:`:

```yaml
optical:
  # THE PART'S FUNCTION, WHICH USED TO BE A STRING. `coupling-ratio: '97/3'` is
  # still in attrs for a reader; this is the same fact in a form lint can check
  # against the bores it actually has.
  media: os2
  paths:
    - from: common.1
      to:
        - {at: split.1, ratio: 97}
        - {at: split.2, ratio: 3}
  unused:
    common.2: >-
      a three-port coupler in a four-bore faceplate - the plate takes duplex
      adapters and the optics need one common port and two legs, so this bore
      exists because of the connector and terminates nothing. ds-ppm-r4.0
      captions it NA.
```

- [ ] **Step 4: Add the optical block to ppm-ocu-50-50**

Same file structure in
`library/components/smartoptics/ppm-ocu-50-50/v1/contract.yaml`: bump
`version: 1.0.0` to `1.1.0` and add before `relief:`:

```yaml
optical:
  # THE PART'S FUNCTION, WHICH USED TO BE A STRING. See ppm-ocu-97-3@1 - the same
  # coupler at the symmetric ratio, which is why neither leg is the main path and
  # ds-ppm-r4.0 prints both with the same number.
  media: os2
  paths:
    - from: common.1
      to:
        - {at: split.1, ratio: 50}
        - {at: split.2, ratio: 50}
  unused:
    common.2: >-
      a three-port coupler in a four-bore faceplate - the plate takes duplex
      adapters and the optics need one common port and two legs, so this bore
      exists because of the connector and terminates nothing. ds-ppm-r4.0
      captions it NA.
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest spec/tests/test_optical_resolve.py -q`
Expected: PASS (9 passed)

- [ ] **Step 6: Run the gate chain, bumping versions before the lock**

```bash
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library | tail -1
```
Expected: `LINT: ok (654 files, 1291 warnings in 22 rules)`. If L53 reports a
device composing these parts is stale, bump that device's `version:` first.

```bash
./publish.sh --no-images | tail -1
python3 spec/tools/portrayal/devicelock.py --library library --update | tail -1
python3 -m pytest spec/tests -q | tail -1
```
Expected: `1377 passed, 1 skipped`

- [ ] **Step 7: Commit**

```bash
git add library/ spec/tests/test_optical_resolve.py
git commit -m "smartoptics: the OCU couplers state their glass

A 97/3 tap is one common port splitting into two legs. That was the string
coupling-ratio: '97/3' and a sentence saying the fourth bore terminates nothing;
it is now one path with two ratios and a declared dead position, and L79 and L80
check both against the bores the part actually has.

The attrs stay for a reader. What changes is that the claim is now testable.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: The four DCMs state their pass-through

**Files:**
- Modify: `library/components/smartoptics/ppm-dcm-{10,20,40,80}/v1/contract.yaml`
- Test: `spec/tests/test_optical_resolve.py` (append)

**Interfaces:**
- Consumes: everything above
- Produces: four library parts carrying a two-ended `optical.path`

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_optical_resolve.py`:

```python
import pytest  # noqa: E402


@pytest.mark.parametrize("km", [10, 20, 40, 80])
def test_each_dcm_passes_rx_through_to_tx(km):
    """ds-ppm-r4.0's own flow figure: Rx in, dispersion applied, Tx out.

    Bore 1 is Tx and bore 2 is Rx, which is the order the faceplate captions
    them and the order lc-duplex-adapter composes its bores.
    """
    c = contract(f"smartoptics/ppm-dcm-{km}@1")
    paths = c["optical"]["paths"]
    assert len(paths) == 1
    assert paths[0]["from"] == "dcm.2" and paths[0]["to"] == "dcm.1"


@pytest.mark.parametrize("km", [10, 20, 40, 80])
def test_a_dcm_declares_no_unused_positions(km):
    """Both bores carry light, so `unused` would be a false claim."""
    c = contract(f"smartoptics/ppm-dcm-{km}@1")
    assert not (c["optical"].get("unused") or {})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest spec/tests/test_optical_resolve.py -q`
Expected: FAIL — `KeyError: 'optical'`

- [ ] **Step 3: Add the optical block to all four DCMs**

In each of `ppm-dcm-10`, `ppm-dcm-20`, `ppm-dcm-40`, `ppm-dcm-80`, bump
`version: 1.0.0` to `1.1.0` and add immediately before `relief:`, with `NN`
replaced by that part's kilometres:

```yaml
optical:
  # RX IN, TX OUT, THROUGH THE GRATING. ds-ppm-r4.0's flow figure for these
  # modules draws Rx entering and Tx leaving, and says so in prose: "Signals
  # entering the module are denoted Rx. Signals exiting the module are denoted
  # Tx." Bore 1 is Tx and bore 2 is Rx - the order the faceplate captions them
  # and the order common/lc-duplex-adapter@3 composes its bores.
  #
  # ONE PATH, NOT TWO. A DCM is not a duplex pass-through; it is a single fibre
  # path through a Bragg grating that applies NNkm of opposite dispersion. Both
  # bores are ends of that one path.
  media: os2
  paths:
    - {from: dcm.2, to: dcm.1}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest spec/tests/test_optical_resolve.py -q`
Expected: PASS (17 passed)

- [ ] **Step 5: Run the gate chain**

```bash
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library | tail -1
./publish.sh --no-images | tail -1
python3 spec/tools/portrayal/devicelock.py --library library --update | tail -1
python3 -m pytest spec/tests -q | tail -1
```
Expected: lint at the baseline; `1385 passed, 1 skipped`

- [ ] **Step 6: Commit**

```bash
git add library/ spec/tests/test_optical_resolve.py
git commit -m "smartoptics: the four DCMs state their pass-through

Rx in, Tx out, through the grating - ds-ppm-r4.0's own flow figure and its own
sentence. One path, not two: a DCM is not a duplex pass-through but a single
fibre path through a Bragg grating, and both bores are ends of it.

The four differ in the dispersion they apply and in nothing else, which is why
the blocks are identical apart from a comment.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: A library sweep, so the rules cannot go quiet

**Files:**
- Create: `spec/tests/test_optical_library.py`

**Interfaces:**
- Consumes: `optical.capacities`, `optical.reached`
- Produces: nothing — a guard

- [ ] **Step 1: Write the test**

Create `spec/tests/test_optical_library.py`:

```python
"""Every optical contract in the library resolves, and the sweep is not vacuous.

The lint rules run over the library on every build, so in principle this adds
nothing. In practice a rule that stops being dispatched goes quiet and the build
stays green - which is exactly how a fixture that could not tell `!seen` from
`!seen && named` shipped here. A sweep that asserts it FOUND something is the
cheap guard against that.
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library" / "components"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))
import optical  # noqa: E402


def contracts():
    for f in sorted(LIB.rglob("contract.yaml")):
        d = yaml.safe_load(f.read_text()) or {}
        if d.get("optical", {}).get("paths"):
            yield f, d


def load_ref(ref):
    name, major = ref.split("@")
    p = LIB / name / f"v{major}" / "contract.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else {}


def test_the_sweep_finds_optical_contracts_at_all():
    found = list(contracts())
    assert len(found) >= 6, (
        f"only {len(found)} contracts declare optical paths. Six were added by "
        "this plan (2 OCU couplers, 4 DCMs); fewer means one lost its block or "
        "this sweep stopped finding them")


def test_every_optical_endpoint_resolves_to_a_real_position():
    bad = []
    for f, d in contracts():
        caps = optical.capacities(d, load_ref)
        for ep in optical.reached(d):
            part, pos = optical.split_endpoint(ep)
            if part not in caps:
                bad.append(f"{f.parent.parent.name}: {ep} names no connector")
            elif pos > caps[part]:
                bad.append(f"{f.parent.parent.name}: {ep} exceeds {caps[part]}")
    assert not bad, "unresolvable optical endpoints:\n  " + "\n  ".join(bad)


def test_every_declared_position_is_reached_or_declared_unused():
    bad = []
    for f, d in contracts():
        caps = optical.capacities(d, load_ref)
        hit = optical.reached(d)
        unused = (d.get("optical") or {}).get("unused") or {}
        for part, n in caps.items():
            for pos in range(1, n + 1):
                ep = f"{part}.{pos}"
                if ep not in hit and ep not in unused:
                    bad.append(f"{f.parent.parent.name}: {ep} unaccounted for")
    assert not bad, "fibre positions nothing accounts for:\n  " + "\n  ".join(bad)
```

- [ ] **Step 2: Run the test to verify it passes**

Run: `python3 -m pytest spec/tests/test_optical_library.py -q`
Expected: PASS (3 passed)

- [ ] **Step 3: Prove the sweep can fail**

Temporarily delete the `unused:` block from
`library/components/smartoptics/ppm-ocu-97-3/v1/contract.yaml`, then:

Run: `python3 -m pytest spec/tests/test_optical_library.py -q`
Expected: FAIL — `ppm-ocu-97-3: common.2 unaccounted for`

Restore the block with `git checkout -- library/components/smartoptics/ppm-ocu-97-3/v1/contract.yaml`
and re-run.
Expected: PASS (3 passed)

- [ ] **Step 4: Run the gate chain**

```bash
python3 -m pytest spec/tests -q | tail -1
```
Expected: `1388 passed, 1 skipped`

- [ ] **Step 5: Commit**

```bash
git add spec/tests/test_optical_library.py
git commit -m "test: sweep every optical contract, and assert the sweep found some

The lint rules already run over the library on every build, so in principle this
adds nothing. In practice a rule that stops being dispatched goes quiet and the
build stays green - which is how a fixture that could not tell one predicate from
another shipped here before. Asserting the sweep FOUND something is the cheap
guard, and the coverage half was checked by deleting an `unused` block and
watching it fail.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-review

**Spec coverage.** Section A: `positions` Task 1, `paths` Task 1 schema + Tasks
6-7 use, splits Tasks 1/4/6, `unused` Tasks 1/5/6, `media` Task 1. Section D:
endpoints-are-real L78 Task 3, no-double-claim L79 Task 4, reached-or-unused L80
Task 5, ratios-sum L79 Task 4, library sweeps Task 8.

**Deliberately NOT in this plan, and where each goes:**
- **`band:`** is in the schema (Task 1) and used by nothing. Its consumers are
  `ppm-ad1-1510` and `ppm-ad1-1625`, which are plan 6. Declared now so the shape
  is fixed before six PPMs are written against it; a rule checking it belongs
  with its first user.
- **Polarity checked against the paths** (spec D, row 5). Its only subjects are
  FS cassettes, which are plan 5. Writing the rule here would mean writing it
  against no data.
- **Fibre counts balance** (spec D, row 4). Meaningless until a part has both a
  front and a rear connector - the first is an FS cassette, plan 5.
- **Rear connectors sit on the rear face** (spec D, row 7). Needs `faces:`, which
  is plan 3.
- **`faces:`, the DCIM projection, the fibre-map export, connector components,
  the FS build.** Plans 2-6.

That leaves L81 and L82 unallocated in this plan; they are the polarity and
balance rules, and they are numbered when written so the catalogue stays
contiguous.

**Placeholder scan:** no TBD/TODO; every code step carries the code; no step says
"similar to Task N".

**Type consistency:** `split_endpoint`, `capacities`, `endpoints`, `reached` are
defined in Task 2 and used under those names in Tasks 3, 4, 5 and 8.
`_optical_load_ref` is defined in Task 3 and reused in Task 5. Test counts are
cumulative: 1357 baseline -> 1358 (T1), 1363 (T2, file only), 1367, 1371,
1374, 1377, 1385, 1388 - and each is a guide, not a gate.

**One thing an executor must not assume:** Task 1 step 6 says devicelock *may*
report stale devices when the adapter's version bumps. Whether it does depends on
what composes `lc-duplex-adapter@3` at that moment. Follow what the tool says;
bump versions before `--update`, never after.
