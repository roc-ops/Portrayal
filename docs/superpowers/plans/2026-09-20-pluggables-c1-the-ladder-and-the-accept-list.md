# Pluggables C1: the ladder registry, and the accept list it derives — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A device's compiled `configs.json` gains a `cages[view][]` list, one entry per placement that presents a pluggable interface, each carrying the set of library parts that could be seated in it — derived, never declared, and vendor-blind by construction.

**Architecture:** A registry in `spec/schemas/pluggables.yaml` names each cage family, its interface, and its rate ladder. A lint rule holds that registry against the corpus in both directions. The build walks each view's placements, resolves the interface each presents (directly or through a wrapper, using the `presented_interface` that already exists), and computes the accept list from the components index.

**Tech Stack:** Python 3.12 (`spec/tools/portrayal/*`), YAML, pytest (`spec/tests`, `-n auto`).

**Spec:** `docs/pluggables-slotting-design.md` (C), with the shared decisions in `docs/pluggables-design.md`. A (`cde41dd8`), B1 (`4aec0a3d`) and B2 (`0e98e2e7`) are all on main.

---

## Why this is C1 and not all of C

Spec C delivers a registry, a derived accept list, a kit seating function, an inspector
select with share-URL plumbing, and a screenshot gate. This plan is the **registry and the
accept list** — everything testable headlessly, and the part a downstream tool actually
consumes. `seatOccupant`, the inspector and the visual gate are C2.

The split is the same one that worked for B, and for the same reason: a visual gate should
not block data work. It carries one risk, learned from B1: `cablePoints` shipped with a
latent defect that nothing caught until B2 consumed it. **So C1's tests must exercise the
accept list against real library parts, not fixtures**, and C2 must be treated as the
first real consumer rather than a formality.

## What the corpus actually says — checked, not assumed

Every number below was read off the tree, not the spec.

**The media vocabulary** (`PLUGGABLE_CAGES`, `lint.py:3514`) has fifteen values: `sfp`,
`sfp-plus`, `sfp28`, `sfp56`, `sfp-dd`, `qsfp`, `qsfp28`, `qsfp56`, `qsfp112`, `qsfp-dd`,
`osfp`, `xfp`, `cfp`, `cfp2`, `cxp`.

**Devices declare ten of them**: sfp28 (87 groups), sfp-plus (63), qsfp28 (46), qsfp-dd (44),
sfp (26), osfp (4), sfp56 (2), qsfp56 (2), xfp (1), qsfp112 (1). Never `sfp-dd`, `cxp`,
`cfp`, `cfp2` or plain `qsfp`.

**Cages exist for every family but one.** `std/cfp`, `std/cfp2`, `std/xfp`, `std/osfp`,
`std/qsfp-dd` and `std/cxp` are all in the library. **`sfp-dd` has no cage.**

**The spec's draft registry is wrong in three places.** It omits `sfp-dd` and `cxp`, and it
invents `qsfp-dd800`, which is in no device and not in `PLUGGABLE_CAGES` — while the spec
itself says the rate names ARE that vocabulary.

**Only four parts can populate any accept list today**: `generic/sfp-lc@1` and
`generic/sfp-lc-simplex@1` (mate `sfp`), `generic/qsfp-lc@1` (mates `qsfp`), and
`generic/qsfp-dd-lc@1` (mates `qsfp-dd`). The two retired parts `common/sfp-lc-duplex@1` and
`common/qsfp-transceiver@1` still carry `behaviour: occupies` and the right `mates`, so they
would be offered unless filtered. The four boots carry `behaviour: occupies` too but mate
`lc-plug`/`rj45-plug`, which are not cage interfaces, so the interface match excludes them.

**`media` is overloaded and must not be read as a rate.** The generics carry `media: fiber`
— a medium. The two retired parts carry `media: sfp` and `media: qsfp` — rates. Reading
`media` as the rate would look for `fiber` on the sfp ladder and find nothing.

## Rulings carried into this plan

- **R1 — a generic has no rate; a vendor optic declares one in `rate`.** `media` means the
  medium (`fiber`, `copper`) and is never consulted for the ladder. A part with no `rate`
  fits every cage of its family, which is exactly what L99 intends by forbidding `speed` on
  a generic. `speed` stays what it is — a bitrate — and is NOT the ladder value; an
  SFP-10G-LR has `speed: 10G` and `rate: sfp-plus`. No vendor optic exists yet, so this plan
  sets the precedent.
- **R2 — superseded parts are excluded, via a NEW structured key.** My first draft of this
  ruling said "a part carrying `unplaced:` is retired". **That is wrong and would have
  emptied every accept list**, because the live generics carry `unplaced:` too — theirs says
  "seated by configurations downstream of this library", which is decision 2 working as
  intended. `unplaced:` answers "why does nothing seat this", and the schema calls it a
  sentence for a human reader (minLength 40). Only prose distinguishes the two retired parts,
  whose text begins "SUPERSEDED by", and nothing in the tree reads that convention.
  So C1 adds a structured `superseded-by` key (Task 0) naming the successor ref, and the
  accept list filters on that.
- **R3 — an empty accept list is legitimate.** `osfp`, `xfp`, `cfp`, `cfp2` and `cxp` cages
  have nothing in the library that mates them. The entry appears with `accepts: []`; the
  test asserts empty, not absent.
- **R4 — the registry covers the vocabulary exactly.** All fifteen values, `qsfp-dd800`
  dropped. `sfp-dd` becomes a family with no cage, so the spec's "a family whose interface
  matches no cage is a lint error" softens to a WARNING — an error would fail the corpus on
  a family the vocabulary requires.

## Global Constraints

- **Gates run with this worktree's code:** every command prefixed `PYTHONPATH=spec/tools`,
  FOREGROUND, `timeout` 600000. `./publish.sh` needs it too; that has bitten three times.
- **Task 0 is the only task that touches `library/`,** and only to add `superseded-by:` to
  two retired contracts. No other task may change anything under `library/components/**` or
  `library/devices/**`.
- **`accepts` is DERIVED, never declared.** Nothing in a device manifest or a cage contract
  may list what it takes. If a task finds itself adding an `accepts:` key to a contract, it
  has left this plan.
- **Vendor-blind by construction.** The computation reads `mates`, the presented interface
  and the ladder. It must never special-case a namespace or a vendor name.
- **Never launder an estimate into a measurement**, and never derive a registry figure.
- **Stage explicit paths; never `git add -A`.** No backticks in commit messages — write to a
  file, check with `grep -c`, `git commit -F`. Every message ends with
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

## File map

| file | responsibility |
|---|---|
| `spec/schemas/component.schema.json` | `superseded-by` (Task 0) |
| `library/components/common/{sfp-lc-duplex,qsfp-transceiver}/v1/contract.yaml` | the key, on the two retired parts (Task 0) |
| `spec/tests/test_superseded_by.py` | the key's shape, and that no live part carries it (Task 0) |
| `spec/schemas/pluggables.yaml` | the ladder registry (Task 1) |
| `spec/tools/portrayal/lint.py` | L101, registry agrees with the corpus both ways (Task 2) |
| `spec/tests/test_pluggable_ladder.py` | the registry's own shape and coverage (Task 1) |
| `spec/tests/test_ladder_lint.py` | L101's cases (Task 2) |
| `spec/tools/portrayal/render.py:2515` | `cages[view][]` beside `bays[view][]` in `cfg_index` (Task 3) |
| `spec/tests/test_cage_accepts.py` | the accept list against REAL library parts (Task 3) |
| `library/dist/**` | regenerated — **gitignored**, never staged (Task 4) |
| `library/components/CATALOGUE.md`, `docs/lint-rules.md`, `library/exports/**` | regenerated if changed (Task 4) |

---

### Task 0: `superseded-by`, so retirement is a fact and not a sentence

**Files:** modify `spec/schemas/component.schema.json`; modify the two retired contracts;
modify `spec/tools/portrayal/lint.py`; create `spec/tests/test_superseded_by.py`

The library can say WHY nothing seats a part (`unplaced:`, free prose, for a reader). It
cannot say a part is RETIRED in favour of another. Two parts are — `common/sfp-lc-duplex@1`
and `common/qsfp-transceiver@1`, both superseded by generics in spec A for baking in a
specific 30 km single-mode SKU — and the only record is the opening word of a sentence.

- [ ] Add `superseded-by` to the component schema: a string, the successor's `ns/name@major`
  ref, optional, with a description saying it means THIS PART IS RETIRED, that `unplaced:`
  answers a different question (why nothing seats it, which is also true of live parts), and
  that a consumer offering parts to a user must not offer a superseded one.
- [ ] Add it to the two contracts, naming `generic/sfp-lc@1` and `generic/qsfp-lc@1`. Leave
  their `unplaced:` prose alone — it is still true and still for a reader.
- [ ] Extend lint: a `superseded-by` must name a component major that EXISTS. An error, not a
  warning — a dangling successor is worse than none, because it reads as a working pointer.
- [ ] `spec/tests/test_superseded_by.py`: the two retired parts carry it and it resolves; NO
  part under `generic/` carries it; a part carrying it still carries its `unplaced:` sentence.
  The docstring must say why the two fields are not the same question, because the next
  person will ask.
- [ ] Commit. Subject: `schema: a retired part says so, instead of starting a sentence with it`

---

### Task 1: The ladder registry

**Files:** create `spec/schemas/pluggables.yaml`; create `spec/tests/test_pluggable_ladder.py`

- [ ] **Step 1: Write the registry.** Eight families covering all fifteen values of
  `PLUGGABLE_CAGES`. Ascending rates; a cage at rate N takes N and below.

```yaml
format: 1
families:
  sfp:
    interface: sfp
    rates: [sfp, sfp-plus, sfp28, sfp56]
    source: 'SFF-8432 envelope; one cage interface, the rate is electrical'
  sfp-dd:
    interface: sfp-dd
    rates: [sfp-dd]
    also-accepts: [sfp]
    source: 'SFP-DD MSA - an SFP-DD cage accepts a single-row SFP. NO CAGE IN THE LIBRARY YET; the family exists because sfp-dd is in the media vocabulary'
  qsfp:
    interface: qsfp
    rates: [qsfp, qsfp28, qsfp56, qsfp112]
    source: 'SFF-8661 envelope; SFF-8663 governs qsfp28 and qsfp56; QSFP-DD HW 6.3 section 9 - a QSFP112 cage is backward compatible to QSFP28 and QSFP+'
  qsfp-dd:
    interface: qsfp-dd
    rates: [qsfp-dd]
    also-accepts: [qsfp]
    source: 'QSFP-DD HW 6.3 section 1 - QSFP-DD cages are compatible with 4-lane QSFP28/QSFP112'
  osfp: {interface: osfp, rates: [osfp], source: 'OSFP MSA - not held; the family is here because osfp is in the media vocabulary and std/osfp exists'}
  xfp:  {interface: xfp,  rates: [xfp],  source: 'XFP MSA - not held; std/xfp exists'}
  cfp:  {interface: cfp,  rates: [cfp],  source: 'CFP MSA - not held; std/cfp exists'}
  cfp2: {interface: cfp2, rates: [cfp2], source: 'CFP MSA - not held; std/cfp2 exists'}
  cxp:  {interface: cxp,  rates: [cxp],  source: 'CXP - not held; std/cxp exists'}
```

**`qsfp-dd800` is deliberately absent** — no device declares it and it is not in
`PLUGGABLE_CAGES`, and the spec says the rate names ARE that vocabulary. Add it the day a
device needs it.

Every `source` says what it rests on. Four of them say the MSA is NOT HELD, because it is
not, and a registry that implied otherwise would be the laundering this library refuses.

- [ ] **Step 2: Write the test** `spec/tests/test_pluggable_ladder.py`:
  - every value in `lint.PLUGGABLE_CAGES` appears as a rate in exactly one family
  - every family's rates are a subset of `PLUGGABLE_CAGES` (this is what catches a
    `qsfp-dd800` creeping back)
  - every family's rates are ascending and contain its own `interface` name where the
    interface is itself a rate
  - every `also-accepts` names a family that exists
  - every family carries a non-empty `source`
  Docstring says WHY: the registry can be wrong and must be caught by the corpus.

- [ ] **Step 3: Run, then commit.** Subject: `registry: the pluggable ladder, one family per cage vocabulary`

---

### Task 2: L101 — the registry agrees with the corpus, both ways

**Files:** modify `spec/tools/portrayal/lint.py`; create `spec/tests/test_ladder_lint.py`

The registry can be wrong. Three checks, all against the real tree:

1. **A device's pluggable `media` names a family's rate.** ERROR — a device declaring a
   media the registry cannot place is a gap in one of them.
2. **A family's `interface` matches at least one component's `interface`.** WARNING, not an
   error — `sfp-dd` has no cage today and the vocabulary requires the family anyway.
3. **A part's `rate` attr, if present, is a rate of the family its `mates` names.** ERROR.
   Nothing declares `rate` yet; this is the rule that makes R1 real rather than aspirational,
   and it must ship with the registry rather than after the first vendor optic.

- [ ] Register L101 in the rules table with a one-line fix hint, implement the three checks,
  and write `spec/tests/test_ladder_lint.py` driving each through `lint.collecting()` — the
  repo's idiom; never clear the lint globals by hand.
- [ ] Run `lint --new-only` over the whole corpus. **Expect zero new findings.** If check 1
  or 3 fires on a real device or part, that is a genuine disagreement between registry and
  corpus — report it, do not silence it.
- [ ] Commit. Subject: `lint: L101, the ladder registry answers to the corpus`

---

### Task 3: `cages[]` in configs.json

**Files:** modify `spec/tools/portrayal/render.py` around `:2515`; create `spec/tests/test_cage_accepts.py`

`cfg_index` assembles `"bays": {view: [...]}` at `render.py:2515-2522`, from
`view_parts(device["views"][v])["bays"]`. `cages` goes beside it, same shape, keyed by view.

- [ ] **Step 1: Resolve each placement's presented interface.** Use
  `manifest.presented_interface`, which already looks through a wrapper's `parts:` — that is
  what makes this work on a vendor cage and not only on a bare `std/` one. It returns a
  THREE-tuple `(interface, mate_at, lift)` since B1.
- [ ] **Step 2: Emit one entry per placement whose presented interface names a family.**

```json
{"id": "port-7", "at": [72.86, 27.77], "interface": "sfp", "media": "sfp28",
 "group": "sfp-plus", "rel-pos": 7, "rotate": null, "accepts": [...], "occupant": null}
```

`media` is the port group's declared media — the cage's ceiling on the ladder. A placement
in no group, or a group with no media, has no ceiling: it accepts every rate of its family.
Say that in a comment; it is the case a reader will wonder about.

- [ ] **Step 3: Compute `accepts`.** Every component where ALL of:
  - `behaviour: occupies`
  - `mates` equals the cage's presented interface, **or** equals the interface of a family
    named in this family's `also-accepts`
  - it carries no `superseded-by` (R2 — retired parts are not offered). Do NOT filter on
    `unplaced:`; every generic carries one.
  - if it declares a `rate`, that rate is at or below the cage's `media` on the ladder; if it
    declares none, it fits (R1)

  Sorted generics first, then the rest alphabetically, so the list reads the same on every
  device. **Never special-case a namespace or a vendor name** — the only reason `generic/`
  sorts first is presentation, and it must be done by namespace prefix, not by a list.

- [ ] **Step 4: The test, against REAL parts** — `spec/tests/test_cage_accepts.py`. This is
  the test that matters, and B1's lesson is why: a mechanism with only fixture tests shipped
  a latent defect nothing caught until a real consumer arrived.
  - a known **sfp28** cage accepts `generic/sfp-lc@1` and `generic/sfp-lc-simplex@1`
  - a known **qsfp-dd** cage accepts `generic/qsfp-dd-lc@1` AND `generic/qsfp-lc@1`, the
    latter through `also-accepts: [qsfp]` — this is the only case that exercises
    `also-accepts` and it must not be dropped
  - a known **osfp** cage accepts `[]` — empty, not absent (R3)
  - **no** cage accepts `common/sfp-lc-duplex@1` or `common/qsfp-transceiver@1` (R2), and
    none accepts a boot (`mates: lc-plug` is not a cage interface)
  - the order is stable: generics first, then alphabetical

  Name the devices you pick, and pick ones whose media you have checked rather than assumed.

- [ ] **Step 5:** `build`, then run the suite, then commit.
  Subject: `feat: a cage publishes what the library could seat in it`

---

### Task 4: Gates

Same sequence as B1 and B2. **Commits but does NOT push or open a PR.**

- [ ] `lock` — expect `devicelock: 0 finding(s)`. No contract changed, so no device should
  want a bump. If L53 asks for one, stop and report.
- [ ] `lint --new-only` — expect no change against the baseline. L101 firing on a real device
  is a finding to understand, never to baseline away.
- [ ] `build`, then `PYTHONPATH=spec/tools ./publish.sh --no-images` — note the prefix.
- [ ] Regenerate `library/components/CATALOGUE.md` and `docs/lint-rules.md`. The catalogue
  should NOT change (no new components) but `lint-rules.md` WILL, because L101 is new.
- [ ] Suite twice with `-n auto`.
- [ ] Commit only tracked files that actually changed. `library/dist/` is gitignored — never
  stage it, and do not create an empty commit.

---

## Self-review

**1. Spec coverage.** `superseded-by` → Task 0, which the spec does not mention because the gap only appears when something first has to CHOOSE between parts. The registry → Task 1, amended per R4 against the real vocabulary. Its
lint → Task 2. `cages[]` with derived accepts → Task 3, with the spec's own three test cases
(SFP28, QSFP-DD, OSFP) as Step 4's first three bullets. `seatOccupant`, the inspector select,
share-URL plumbing and the screenshot gate → **C2, deliberately**. The spec's two open
questions — whether to carry `optics-<media>` prose as a tooltip, and whether a cage inside a
seated module is offered — are **C2 questions**: the first is a UI affordance, the second is
about the inspector resolving paths through a seated module. Neither affects the data C1
emits, and both should be decided with the consumer in hand.

**2. Placeholder scan.** Task 1 carries the complete registry. Task 3 carries the entry shape
and the full accept predicate. Task 2 states three checks precisely but does not dictate the
code, because it must fit `lint.py`'s existing rule idiom, which the implementer should read
first. Task 3 Step 4 deliberately does not name the devices — the implementer must pick them
by checking declared media rather than trusting a name in a brief, which is the single
correction that recurred most often across B1 and B2.

**3. Type consistency.** `interface` is the string `presented_interface` returns and the
string a family's `interface` holds. `media` is a member of `PLUGGABLE_CAGES` and of exactly
one family's `rates`. `rate` (R1) is the same vocabulary, on a part rather than a group.
`accepts` holds `ns/name@major` refs, the same form `bays[].accepts` already uses.

**Known risk, stated rather than hidden:** the accept list is derived from three inputs that
have each been wrong in this project before — a part's `mates`, a wrapper's presented
interface, and a group's declared media. Task 3's tests run against the real library for that
reason. If a device's media and its cage's interface disagree, L101 check 1 should catch it
before the accept list does; if it does not, the accept list will be quietly wrong rather
than empty, which is the failure mode to watch for.
