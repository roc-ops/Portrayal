# Component Faces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generalise the component key `plan: {ref}` into `faces: {plan: {ref}, rear: {ref}}`, so a part can name its rear drawing the same way it already names its plan drawing.

**Architecture:** The library already solved "this part seen from another direction" — a component says `plan: {ref: ...}` and a bay says where that projection lands. This adds one more direction under a container that scales, keeps `plan:` working as sugar for `faces.plan`, and routes every reader through one accessor so a third direction later touches one function instead of three call sites. A rear face is an ordinary component and therefore already renders standalone; nothing new draws it.

**Tech Stack:** Python 3, JSON Schema (draft 2020-12), PyYAML, pytest.

**Spec:** `docs/optical-paths-design.md` — section B, "Faces". This is plan 3 of 6.

## Global Constraints

- `working/` is NEVER committed and never published. Reference material stays there; facts get transcribed into contracts.
- Every dimension not measured is `confidence: estimated` with provenance naming what it was derived from. Never launder an estimate into a measurement.
- Version bumps go in BEFORE `devicelock --update`, never after.
- Run every gate in the FOREGROUND, timeout 600000 ms. A backgrounded pytest is a lost pytest. The chain, in order:
  1. `python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library | tail -3`
  2. `./publish.sh --no-images`
  3. `python3 spec/tools/portrayal/devicelock.py --library library`
  4. `python3 -m pytest spec/tests -q 2>&1 | tail -5`
- Lint baseline at the start of this plan: `LINT: ok (662 files, 1291 warnings in 22 rules)`. Test baseline: `1426 passed, 1 skipped`. Expected totals in tasks are a GUIDE, not a gate — the binding check is that nothing FAILED and the total only went up.
- Commit messages end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. Avoid backticks in commit message text: write the message to a file and use `git commit -F`.
- Do not dispatch subagents from inside a task.

---

## Context an implementer needs before touching anything

**`plan:` means two different things in this repo and only one of them changes.**

| where | shape | meaning | changes? |
|---|---|---|---|
| on a COMPONENT | `plan: {ref: dell/riser-card-14g@1}` | *this part seen from above, as another component* | **YES** — becomes `faces.plan`, with `plan:` kept as sugar |
| on a BAY, in a device | `plan: {view, at, in, under, mirror}` | *where the seated part's plan projection lands* | **NO** — untouched, different key, different schema |

Getting these two confused is the single most likely way to break this plan. Every
`b.get("plan")` in the codebase is the bay-side key and must be left exactly as it
is. Only `(component).get("plan")` moves.

**The complete set of component-side readers, verified by grep across `spec/tools` and `viewer`:**

- `spec/tools/portrayal/render.py:1199` — `pref = ((oc or {}).get("plan") or {}).get("ref")`
- `spec/tools/portrayal/render.py:1218` — `sref = ((sc or {}).get("plan") or {}).get("ref")`
- `spec/tools/portrayal/lint.py:5844` — `pref = (c.get("plan") or {}).get("ref")`

Three sites. There is no fourth; `viewer/` has none. If you find one this plan did
not name, stop and report it rather than guessing.

**Who uses `plan:` today:** 13 components — `common/pcie-card-fh/v1`, `common/pcie-card-lp/v1`, and eleven Dell risers (`dell/riser-1a-14g`, `1b`, `1d`, `2a`, `2b`, `2c`, `2d`, `2e`, `2f`, `3a`, `3b`, all `/v1`). One device projects them: `library/devices/dell/r740xd/device.yaml`. Nothing else.

**Why a rear face needs no renderer.** `faces.rear` names another component, and
every component already renders standalone into `dist/components/` via
`components_index.py`. That is where a modeller looks at a part. The spec chose
this deliberately over a device-level interior view, which would be the library's
first non-canonical view name and is its own piece of work.

**What this plan deliberately does NOT do.** It does not build an FS cassette.
The cassette raises a question section B does not answer — whether
`optical.paths` endpoints may reference a part that lives on the rear face
component rather than in the module's own `parts:` — and that is a design
question for the plan that builds one, not something to settle by implication
here. `faces.rear` therefore lands with schema, lint, index support and tests,
and gets its first real user in plan 4.

---

## File Structure

| file | responsibility |
|---|---|
| `spec/tools/portrayal/faces.py` | **new.** One accessor, `face_ref(contract, name)`, that every reader goes through. Small on purpose: it is the seam a third direction would widen, and a seam only works if there is exactly one. |
| `spec/schemas/component.schema.json` | **modify.** Add `faces`; keep `plan` with a description saying it is sugar. |
| `spec/tools/portrayal/render.py` | **modify** lines 1199 and 1218 — read through the accessor. |
| `spec/tools/portrayal/lint.py` | **modify** line 5844 — read through the accessor. Add L82 (`plan:` and `faces.plan` both present) and L83 (`faces.rear` resolves, and does not chain). |
| `spec/tools/portrayal/components_index.py` | **modify.** Carry `faces` onto the index entry so the viewer can offer a part's rear drawing. |
| `library/components/common/pcie-card-fh/v1/contract.yaml` | **modify.** Migrate to `faces.plan` — one of two real parts proving the new key. |
| `library/components/common/pcie-card-lp/v1/contract.yaml` | **modify.** The second. The eleven risers stay on `plan:`, which is what proves the sugar. |
| `spec/tests/test_faces.py` | **new.** The accessor, both spellings, the two lint rules, and the byte-identical proof. |

---

### Task 1: The accessor, the schema, and the rule against saying it twice

**Files:**
- Create: `spec/tools/portrayal/faces.py`
- Modify: `spec/schemas/component.schema.json`
- Modify: `spec/tools/portrayal/lint.py` (add `lint_component_faces_once`, register it)
- Test: `spec/tests/test_faces.py` (create)

**Interfaces:**
- Produces: `face_ref(contract, name)` -> `str | None`. `contract` is a loaded component dict, `name` is `"plan"` or `"rear"`. Returns the component ref (e.g. `"dell/riser-card-14g@1"`) or `None`. For `"plan"` it reads `faces.plan.ref` and falls back to the legacy top-level `plan.ref`. Tasks 2, 3 and 4 all call this.
- Produces: lint rule id **L82**.

- [ ] **Step 1: Write the failing test**

Create `spec/tests/test_faces.py`:

```python
"""`faces:` - a part naming its own drawings seen from other directions.

The legacy spelling is a top-level `plan: {ref}`. The new one is
`faces: {plan: {ref}, rear: {ref}}`. Both must mean the same thing for `plan`,
and the library must never carry both on one contract, because then a reader has
to guess which the author meant.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import faces as F  # noqa: E402
import lint as L  # noqa: E402

LIB = [str(ROOT / "library")]


def run82(doc, path="t/contract.yaml"):
    L.ERRORS.clear()
    L.lint_component_faces_once(path, doc)
    return [e for e in L.ERRORS if "[L82]" in e]


def test_the_legacy_spelling_still_answers():
    assert F.face_ref({"plan": {"ref": "dell/riser-card-14g@1"}}, "plan") == \
        "dell/riser-card-14g@1"


def test_the_new_spelling_answers_the_same_way():
    assert F.face_ref({"faces": {"plan": {"ref": "dell/riser-card-14g@1"}}},
                      "plan") == "dell/riser-card-14g@1"


def test_a_rear_face_has_no_legacy_spelling_to_fall_back_to():
    """`rear` is new, so it reads `faces` only - there is no top-level `rear:`."""
    assert F.face_ref({"faces": {"rear": {"ref": "fs/x-rear@1"}}}, "rear") == \
        "fs/x-rear@1"
    assert F.face_ref({"rear": {"ref": "fs/x-rear@1"}}, "rear") is None


def test_a_part_with_no_faces_at_all_answers_none():
    assert F.face_ref({}, "plan") is None
    assert F.face_ref({}, "rear") is None


def test_saying_it_both_ways_is_an_error():
    got = run82({"plan": {"ref": "a/b@1"},
                 "faces": {"plan": {"ref": "a/c@1"}}})
    assert len(got) == 1, got
    assert "faces.plan" in got[0]


def test_saying_it_both_ways_is_an_error_even_when_they_agree():
    """Agreeing today is not the point - one of them gets edited tomorrow."""
    got = run82({"plan": {"ref": "a/b@1"},
                 "faces": {"plan": {"ref": "a/b@1"}}})
    assert len(got) == 1, got


def test_one_spelling_or_the_other_is_quiet():
    assert run82({"plan": {"ref": "a/b@1"}}) == []
    assert run82({"faces": {"plan": {"ref": "a/b@1"}}}) == []
    assert run82({"faces": {"rear": {"ref": "a/b@1"}}}) == []
    assert run82({}) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest spec/tests/test_faces.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'faces'`.

- [ ] **Step 3: Write the accessor**

Create `spec/tools/portrayal/faces.py`:

```python
"""Where a part keeps its other drawings.

A component's face is its own art. Seen from ANOTHER direction it is a different
drawing at a different size, so it is a different part: a riser's face is a
bracket plate, and from above it is a thin PCB with connectors. The library has
said that for a long time with a top-level `plan: {ref}`.

`faces:` is the same idea with room in it. A bare `rear:` sibling would handle
one more direction and then stop, and the third one would be a third top-level
key nobody thinks to look for. Readers go through `face_ref` so that adding a
direction is a change to this file rather than a hunt through render.py and
lint.py for the places that spell it out.

`plan:` stays legal and means exactly `faces.plan`. 13 components use it and one
device projects it; there is no value in a migration that only moves words.
"""

# `plan` is the only direction with a legacy spelling, because it is the only
# one that existed before `faces`. A new direction added here gets no fallback
# and needs none.
LEGACY = {"plan": "plan"}


def face_ref(contract, name):
    """The component ref for this part seen from `name`, or None.

    `name` is a key of `faces:` - "plan" or "rear" today. Reads the new spelling
    first so that a contract carrying both is resolved consistently with
    whatever L82 reports about it, rather than differently in each reader.
    """
    ref = (((contract.get("faces") or {}).get(name) or {}).get("ref"))
    if ref:
        return ref
    legacy = LEGACY.get(name)
    if legacy:
        return ((contract.get(legacy) or {}).get("ref")) or None
    return None
```

- [ ] **Step 4: Add `faces` to the component schema**

In `spec/schemas/component.schema.json`, inside `properties`, add a `faces`
block alongside the existing `plan` block (the file's `properties` are not
alphabetised; put `faces` immediately before `fields`):

```json
    "faces": {
      "type": "object",
      "additionalProperties": false,
      "description": "THIS PART SEEN FROM ANOTHER DIRECTION, each as its own component. A face is a drawing, and a drawing from another direction is a different drawing at a different size - so it is a different part, not a variant of this one. `plan` is the top view, which a device bay lands with its own `plan:` key; `rear` is the back of the part, which renders as a component preview rather than in any device view. The legacy top-level `plan:` means exactly `faces.plan` and stays legal; declaring both is an error (L82).",
      "properties": {
        "plan": {"$ref": "#/$defs/face"},
        "rear": {"$ref": "#/$defs/face"}
      }
    },
```

and add to `$defs`:

```json
    "face": {
      "type": "object",
      "additionalProperties": false,
      "required": ["ref"],
      "properties": {
        "ref": {
          "type": "string",
          "pattern": "^[a-z0-9-]+/[a-z0-9-]+@\\d+$",
          "description": "the component that IS this part seen from that direction"
        }
      }
    },
```

Then replace the existing top-level `plan` block's `description` with:

```
"SUGAR FOR `faces.plan`, kept because 13 components and one device use it. THIS PART SEEN FROM ABOVE, as another component. A riser's face is its bracket plate; from above it is a thin PCB with connectors, which is a different drawing at a different size, so it is its own part - dell/riser-card-14g@1 for the full-height risers. A device bay that seats this part says where the plan lands in its top view (`plan:` on the bay). Do not declare this and `faces.plan` together - L82 reports it."
```

Leave the rest of the `plan` block exactly as it is.

- [ ] **Step 5: Write the L82 rule**

In `spec/tools/portrayal/lint.py`, next to the other component rules, add:

```python
def lint_component_faces_once(path, data):
    """L82: a part names its plan drawing one way or the other, never both.

    `plan:` is sugar for `faces.plan`. A contract carrying both leaves every
    reader to pick one, and the two will agree right up until somebody edits a
    face and does not notice there is a second copy of it three lines away.
    """
    if not isinstance(data, dict):
        return
    if (data.get("plan") or {}).get("ref") and \
            ((data.get("faces") or {}).get("plan") or {}).get("ref"):
        err(path, "L82", "declares both `plan:` and `faces.plan` - they mean the "
                         "same thing, so keep one. `plan:` is the legacy spelling")
```

Register it wherever the other component rules are called on a loaded contract —
find the call site of an existing component rule that takes `(path, data)` only,
such as `lint_component_optical_endpoints`, and add
`lint_component_faces_once(path, doc)` beside it, matching the argument names
already in use at that site.

- [ ] **Step 6: Run the tests**

Run: `python3 -m pytest spec/tests/test_faces.py -q`
Expected: PASS, 7 tests.

- [ ] **Step 7: Run the gate chain**

```bash
python3 spec/tools/portrayal/lint.py --schemas spec/schemas --library library | tail -3
./publish.sh --no-images
python3 spec/tools/portrayal/devicelock.py --library library
python3 -m pytest spec/tests -q 2>&1 | tail -5
```

Expected: lint `LINT: ok (662 files, 1291 warnings in **23** rules)` — the rule
count goes up by one because L82 is new, and the file and warning counts do not
move because nothing in the library declares `faces` yet. devicelock 0 findings.
Roughly `1433 passed, 1 skipped`.

- [ ] **Step 8: Commit**

Write the message to a file and commit `spec/tools/portrayal/faces.py`,
`spec/schemas/component.schema.json`, `spec/tools/portrayal/lint.py` and
`spec/tests/test_faces.py`.

---

### Task 2: Route the three readers through the accessor

**Files:**
- Modify: `spec/tools/portrayal/render.py:1199`, `:1218`
- Modify: `spec/tools/portrayal/lint.py:5844`
- Test: `spec/tests/test_faces.py` (append)

**Interfaces:**
- Consumes: `face_ref(contract, name)` from Task 1.

**The thing that must not change.** Eleven Dell risers and two PCIe cards carry
`plan:`, and `library/devices/dell/r740xd/device.yaml` projects them into its top
view. After this task that device's rendered SVG must be **byte-identical** to
what it was before. The accessor falls back to the legacy spelling, so it will
be — but "it should be" is not the same as having watched it.

- [ ] **Step 1: Capture the before-picture**

```bash
./publish.sh --no-images
shasum -a 256 dist/dell/r740xd/*.svg | sort > /tmp/r740xd-before.txt
wc -l /tmp/r740xd-before.txt
```

Keep that file. Do not commit it.

- [ ] **Step 2: Write the failing test**

Append to `spec/tests/test_faces.py`:

```python
def test_render_reads_a_plan_through_the_accessor():
    """render.py must not spell out `.get("plan")` for a COMPONENT any more.

    The bay-side `plan:` - where a projection LANDS - is a different key and
    keeps its literal reads; this only checks the two component-side ones.
    """
    src = (ROOT / "spec/tools/portrayal/render.py").read_text()
    assert 'oc or {}).get("plan")' not in src, \
        "render.py:~1199 still reads a component's plan directly"
    assert 'sc or {}).get("plan")' not in src, \
        "render.py:~1218 still reads a component's plan directly"
    assert "face_ref(" in src, "render.py does not use the accessor at all"


def test_lint_reads_a_plan_through_the_accessor():
    src = (ROOT / "spec/tools/portrayal/lint.py").read_text()
    assert 'c.get("plan") or {}).get("ref")' not in src, \
        "lint.py:~5844 still reads a component's plan directly"


def test_a_component_using_the_new_spelling_projects():
    """The accessor is what makes `faces.plan` land in a device's top view.

    Reads the real library rather than a fixture: if the two migrated PCIe cards
    ever lose their `faces.plan`, this says so.
    """
    p = ROOT / "library/components/common/pcie-card-fh/v1/contract.yaml"
    c = yaml.safe_load(p.read_text())
    assert F.face_ref(c, "plan"), "pcie-card-fh@1 names no plan drawing"
```

- [ ] **Step 3: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_faces.py -q`
Expected: FAIL on `test_render_reads_a_plan_through_the_accessor` — the literal
read is still there. The third test will also fail until Task 5 migrates the
cards; that is expected and it passes from Task 5 onward.

- [ ] **Step 4: Change render.py**

At the top of `spec/tools/portrayal/render.py`, beside the other local imports,
add `from faces import face_ref` (match the import style already used in that
file for its siblings — check how it imports `instance_group` or similar and
follow it exactly).

Replace line 1199:

```python
            pref = ((oc or {}).get("plan") or {}).get("ref")
```

with:

```python
            pref = face_ref(oc or {}, "plan")
```

Replace line 1218:

```python
                sref = ((sc or {}).get("plan") or {}).get("ref")
```

with:

```python
                sref = face_ref(sc or {}, "plan")
```

Leave `pl = b.get("plan")` at line 1190 and `sp = (sb or {}).get("plan")` at
line 1211 ALONE — those are the bay-side key.

- [ ] **Step 5: Change lint.py**

Import `face_ref` the same way, then replace line 5844:

```python
                pref = (c.get("plan") or {}).get("ref")
```

with:

```python
                pref = face_ref(c, "plan")
```

Leave `pl = b.get("plan")` at line 5823 alone.

- [ ] **Step 6: Prove the render did not move**

```bash
./publish.sh --no-images
shasum -a 256 dist/dell/r740xd/*.svg | sort > /tmp/r740xd-after.txt
diff /tmp/r740xd-before.txt /tmp/r740xd-after.txt && echo "IDENTICAL"
```

Expected: `IDENTICAL`. If it is not, stop — something read the bay-side key by
mistake. Paste the diff into your report and do not proceed.

- [ ] **Step 7: Run the tests and the gate chain**

Run the full chain from Global Constraints.
Expected: lint `LINT: ok (662 files, 1291 warnings in 23 rules)`, devicelock 0,
roughly `1435 passed, 1 skipped` with
`test_a_component_using_the_new_spelling_projects` still FAILING until Task 5.
**If that one test is the only failure, that is expected — note it in your
report and continue.** Anything else failing is not.

- [ ] **Step 8: Commit**

---

### Task 3: L83 — a rear face must exist, and must not chain

**Files:**
- Modify: `spec/tools/portrayal/lint.py`
- Test: `spec/tests/test_faces.py` (append)

**Interfaces:**
- Consumes: `face_ref` from Task 1; `resolve_component(ref, lib_roots)` already in `lint.py`.
- Produces: lint rule id **L83**.

**Why chaining is the thing to forbid.** A rear face is a component, and a
component may declare `faces`. So `a@1`'s rear could be `b@1`, whose rear is
`a@1` — or `c@1`, whose rear is `d@1`. Neither has a meaning: a part has one
back. Forbidding it at depth one is enough and costs a single `if`.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_faces.py`:

```python
def run83(doc, path="t/contract.yaml", name="t/thing@1"):
    L.ERRORS.clear()
    L.lint_component_rear_face(path, doc, LIB, name)
    return [e for e in L.ERRORS if "[L83]" in e]


def test_a_rear_face_must_name_a_component_that_exists():
    got = run83({"faces": {"rear": {"ref": "fs/not-a-real-part@1"}}})
    assert len(got) == 1, got
    assert "not in the library" in got[0]


def test_a_part_may_not_be_its_own_rear():
    got = run83({"faces": {"rear": {"ref": "common/mpo-adapter@1"}}},
                name="common/mpo-adapter@1")
    assert len(got) == 1, got
    assert "its own rear" in got[0]


def test_a_rear_face_may_not_itself_have_a_rear():
    """A part has one back. `a`'s rear being `b` whose rear is `c` means nothing."""
    got = run83({"faces": {"rear": {"ref": "common/lc-duplex-adapter@3"}}})
    # lc-duplex-adapter@3 has no rear today, so this must be QUIET - the test
    # that matters is the synthetic one below, which does not depend on the
    # library staying arranged as it is.
    assert got == [], got


def test_a_real_rear_reference_is_quiet():
    got = run83({"faces": {"rear": {"ref": "common/mpo-adapter@1"}}})
    assert got == [], got


def test_no_rear_at_all_is_quiet():
    assert run83({}) == []
    assert run83({"faces": {"plan": {"ref": "common/mpo-adapter@1"}}}) == []
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_faces.py -q`
Expected: FAIL — `module 'lint' has no attribute 'lint_component_rear_face'`.

- [ ] **Step 3: Write the rule**

In `spec/tools/portrayal/lint.py`, beside `lint_component_faces_once`:

```python
def lint_component_rear_face(path, data, lib_roots, name=None):
    """L83: a rear face names a real component, and that component has no rear.

    The rear face is an ordinary part, so a typo in the ref fails silently -
    nothing draws, and the contract still lints. And because it is an ordinary
    part it could declare `faces.rear` itself, which has no meaning: a part has
    ONE back, and a chain of them says the modeller was drawing something else.
    """
    if not isinstance(data, dict):
        return
    ref = face_ref(data, "rear")
    if not ref:
        return
    if name and ref == name:
        err(path, "L83", f"names itself as its own rear ({ref})")
        return
    cp = resolve_component(ref, lib_roots)
    if not cp:
        err(path, "L83", f"names rear face {ref}, which is not in the library")
        return
    inner = load_yaml(cp) or {}
    if face_ref(inner, "rear"):
        err(path, "L83", f"names rear face {ref}, which declares a rear of its "
                         "own - a part has one back, so this chain says the "
                         "wrong part was drawn")
```

Register it at the same call site as L82. It needs the component's own ref to
check self-reference; that call site already knows the namespace and name it is
linting — pass `f"{ns}/{doc['name']}@{major}"` in whatever local variables that
site already has. If the site does not have them to hand, pass `None` and note
in your report that the self-reference check is unreachable from there, rather
than restructuring the caller.

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest spec/tests/test_faces.py -q`
Expected: PASS.

- [ ] **Step 5: Run the gate chain**

Expected: `LINT: ok (662 files, 1291 warnings in **24** rules)`, devicelock 0,
roughly `1440 passed, 1 skipped` (still with the Task 2 test failing until
Task 5).

- [ ] **Step 6: Commit**

---

### Task 4: Surface `faces` on the components index

**Files:**
- Modify: `spec/tools/portrayal/components_index.py`
- Test: `spec/tests/test_faces.py` (append)

**Interfaces:**
- Consumes: `face_ref` from Task 1.
- Produces: a `faces` key on each index entry that has one, shaped `{"plan": "<ref>", "rear": "<ref>"}`, absent entirely when the part declares neither.

**Why flatten it to refs.** The index is fetched on every page load, and the
file already strips `at` from parts for that reason. A reader only needs to know
which part to fetch; `{"rear": "fs/x-rear@1"}` says that in a third of the bytes
of the nested form, and the viewer looks the ref up in the same index anyway.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_faces.py`:

```python
def test_the_index_carries_a_parts_other_faces():
    """The viewer offers a rear drawing only if the index says there is one."""
    src = (ROOT / "spec/tools/portrayal/components_index.py").read_text()
    assert "face_ref(" in src, \
        "components_index.py never asks a contract for its faces, so the " \
        "viewer cannot know a part has a rear drawing"


def test_the_index_entry_omits_faces_when_there_are_none(tmp_path):
    """An empty dict on 700-odd entries is bytes on every page load."""
    src = (ROOT / "spec/tools/portrayal/components_index.py").read_text()
    assert 'entry["faces"] = ' not in src or "if faces" in src or \
        "if fc:" in src, \
        "components_index.py must not attach an empty faces object"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_faces.py -q`
Expected: FAIL on the first of the two.

- [ ] **Step 3: Make the change**

In `spec/tools/portrayal/components_index.py`, import `face_ref` the way the
file already imports its siblings, and immediately before `index.append(entry)`
(the same place `entry["body"]` is attached), add:

```python
            # A PART'S OTHER DRAWINGS, flattened to refs. The viewer resolves
            # them against this same index, so the nested `{ref: ...}` form
            # would cost bytes on every page load and buy nothing. Omitted
            # entirely when a part has none, which is all but thirteen of them.
            fc = {k: r for k in ("plan", "rear")
                  if (r := face_ref(data, k))}
            if fc:
                entry["faces"] = fc
```

- [ ] **Step 4: Run the tests, then check the real output**

```bash
python3 -m pytest spec/tests/test_faces.py -q
./publish.sh --no-images
python3 -c "
import json
d = json.load(open('dist/components.json'))
e = d if isinstance(d, list) else d.get('components', d)
n = [x for x in e if x.get('faces')]
print(len(n), 'entries carry faces')
for x in n[:3]: print(' ', x['name'], x['faces'])
"
```

Expected: **13 entries carry faces** — the eleven risers via the legacy
spelling and, from Task 5 onward, the two PCIe cards via the new one. If the
count is not 13, the accessor is not seeing the legacy spelling; stop and report.

- [ ] **Step 5: Run the gate chain, then commit**

Expected: lint unchanged at 24 rules, devicelock 0, roughly `1442 passed, 1
skipped`.

---

### Task 5: Migrate two real parts, and prove the library is quiet either way

**Files:**
- Modify: `library/components/common/pcie-card-fh/v1/contract.yaml`
- Modify: `library/components/common/pcie-card-lp/v1/contract.yaml`
- Test: `spec/tests/test_faces.py` (append)

**Interfaces:**
- Consumes: everything above.

**Why two and not thirteen.** Migrating all thirteen would leave the sugar
untested, and the sugar is the half that thirteen real parts and one device
depend on. Migrating none would leave `faces.plan` untested on anything real.
Two and eleven exercises both paths against the actual library.

**Version bumps.** Both contracts change. Check whether `devicelock` wants a
bump BEFORE running it with `--update`: a component that a locked device
composes needs its version raised first. `common/pcie-card-fh@1` and
`common/pcie-card-lp@1` are composed by `library/devices/dell/r740xd`, so
expect to bump the patch version in each contract's `version:` field before
`devicelock --update`, never after. If devicelock reports no drift, do not bump.

- [ ] **Step 1: Write the failing test**

Append to `spec/tests/test_faces.py`:

```python
CARDS = ["common/pcie-card-fh/v1", "common/pcie-card-lp/v1"]


@pytest.mark.parametrize("rel", CARDS)
def test_the_migrated_cards_use_the_new_spelling(rel):
    c = yaml.safe_load(
        (ROOT / "library/components" / rel / "contract.yaml").read_text())
    assert "plan" not in c, f"{rel} still carries the legacy top-level `plan:`"
    assert ((c.get("faces") or {}).get("plan") or {}).get("ref"), \
        f"{rel} lost its plan drawing in the migration"


def test_the_risers_still_use_the_legacy_spelling():
    """THE SUGAR IS LOAD-BEARING and this is what watches it.

    Eleven risers and one device depend on `plan:` continuing to mean
    `faces.plan`. If a later sweep migrates them all, the fallback in
    `faces.face_ref` stops being exercised by anything real - so this test
    fails loudly rather than letting that happen silently.
    """
    lib = ROOT / "library/components/dell"
    legacy = [p.parent.parent.name for p in lib.glob("riser-*/v1/contract.yaml")
              if "plan" in (yaml.safe_load(p.read_text()) or {})]
    assert len(legacy) == 11, \
        f"expected 11 risers on the legacy spelling, found {len(legacy)}: {legacy}"


def test_every_contract_in_the_library_passes_l82():
    """Nobody, anywhere, says it both ways."""
    bad = []
    for p in (ROOT / "library/components").glob("*/*/v*/contract.yaml"):
        c = yaml.safe_load(p.read_text()) or {}
        if (c.get("plan") or {}).get("ref") and \
                ((c.get("faces") or {}).get("plan") or {}).get("ref"):
            bad.append(str(p.relative_to(ROOT)))
    assert not bad, bad
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m pytest spec/tests/test_faces.py -q`
Expected: FAIL on both parametrised cases — the cards still carry `plan:`.

- [ ] **Step 3: Migrate the two cards**

In each of the two contracts, replace:

```yaml
plan:
  ref: <whatever ref it names>
```

with:

```yaml
faces:
  plan:
    ref: <the same ref, unchanged>
```

Do not change the ref. Do not touch anything else in either file. Add no
comment: the schema carries the explanation and a comment here would be a
second copy of it.

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest spec/tests/test_faces.py -q`
Expected: PASS, including
`test_a_component_using_the_new_spelling_projects` from Task 2, which has been
failing since then and now passes.

- [ ] **Step 5: Prove the r740xd render STILL did not move**

```bash
./publish.sh --no-images
shasum -a 256 dist/dell/r740xd/*.svg | sort > /tmp/r740xd-after5.txt
diff /tmp/r740xd-before.txt /tmp/r740xd-after5.txt && echo "IDENTICAL"
```

Expected: `IDENTICAL`. The two cards now declare their plan the new way and the
device draws exactly what it drew before. If this differs, the migration changed
a ref — stop and report.

- [ ] **Step 6: Version bumps, then devicelock**

```bash
python3 spec/tools/portrayal/devicelock.py --library library
```

If it reports drift on `r740xd`, raise the patch version in each migrated
contract's `version:` field, re-run `./publish.sh --no-images`, then
`python3 spec/tools/portrayal/devicelock.py --library library --update`. Bumps
go in BEFORE `--update`. Say in your report what you decided and why.

- [ ] **Step 7: Run the full gate chain, then commit**

Expected: lint `LINT: ok (662 files, 1291 warnings in 24 rules)`, devicelock 0,
roughly `1446 passed, 1 skipped`, nothing failing.

---

## Self-Review

**1. Spec coverage.** Section B asks for three things and each has a task:
`faces: {plan, rear}` with `plan:` as sugar (Task 1, schema and accessor;
Task 2, readers); a rear face rendering as a **component preview** rather than
a device view (Task 4 — no renderer is added, because a rear face is an
ordinary component and already renders; the index is what lets a viewer find
it); and the small blast radius the spec claims, which Task 2 and Task 5 verify
by byte-identical output rather than by assertion. Section B's note about an
interior view being possible-but-unprecedented is deliberately not implemented —
it is flagged there as its own piece of work.

**2. Placeholder scan.** Three steps say "match the import style already used in
that file" rather than printing an import line. That is deliberate: `render.py`,
`lint.py` and `components_index.py` do not import their siblings the same way,
and prescribing one would be wrong in at least one of the three. Every other
step carries its literal content.

**3. Type consistency.** `face_ref(contract, name)` is defined in Task 1 and
called with that exact signature in Tasks 2, 3 and 4. `lint_component_faces_once(path, data)`
and `lint_component_rear_face(path, data, lib_roots, name=None)` are defined in
Tasks 1 and 3 and called with those signatures from their tests. Rule ids L82
and L83 are each used once.

**4. Known soft spots, named rather than hidden.**

- **`faces.rear` gets no real user in this plan.** Schema, two lint rules,
  index support and tests, and nothing in the library declares one. This repo
  has a recorded lesson that a feature nothing builds is a feature nothing
  checks, so this is a debt, not a completion: plan 4 builds the first FS
  cassette and is where `faces.rear` earns its keep. An executor should not
  invent a rear face to close the gap.
- **Task 3's registration step may not have the component's own ref to hand.**
  The plan says what to do in that case — pass `None`, report it — rather than
  pretending the call site is known. The self-reference check is the least
  valuable of the three L83 checks if it is lost.
- **Expected test totals are guesses.** Only "nothing failed and the total rose"
  is binding, per Global Constraints.
- **Task 2 leaves one test failing on purpose** until Task 5. That is called out
  in both tasks. An executor who "fixes" it by migrating the cards early has
  merged Task 5 into Task 2, which is acceptable if they say so.
