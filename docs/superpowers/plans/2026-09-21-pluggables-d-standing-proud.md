# Pluggables D: standing proud in 3D — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every pluggable, plug and boot stands proud in 3D by an amount that is sourced or honestly marked estimated; a boot stands BEHIND its plug rather than inside it; latches and tabs take the colour the 2D gives them; and the dead body skins are gone.

**Architecture:** Mostly data (relief features on eight contracts) plus one mechanism: a connection point may name the relief feature it sits on (`on:`), and a contract may say which of its points presents its own interface (`interface-at:`), so `manifest.presented_interface` returns that feature's `out` as the seat lift and a boot lands on the plug's rear face. Everything else rides the lift chain B built.

**Tech Stack:** Python build (`spec/tools/portrayal/render.py`, `manifest.py`, `lint.py`, `component.schema.json`), component contracts under `library/components/`, the kit's `relief.js` (read-only here unless a test proves otherwise), pytest.

**Spec:** `docs/pluggables-3d-design.md`. Umbrella `docs/pluggables-design.md`. A, B, C are merged (#400, #416, #428, #435, #441).

## Global Constraints

- `PYTHONPATH=spec/tools` on EVERY portrayal / pytest command; suite with `-n auto`. Check `git -C /Volumes/External/Network-Device-Visualization/.claude/worktrees/toolchain log --oneline -1` against `origin/main` before believing a clean gate.
- NEVER `git add -A`; stage explicit paths. NO BACKTICKS in commit messages (file + `grep -c` + `git commit -F`). Trailer `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. Commit BEFORE the full suite. Do not push.
- `working/` is NEVER committed. Transcribe facts; never copy a drawing or datasheet into the library.
- NEVER launder an estimate into a measurement. Every new number carries `confidence` and a `source` sentence that says what it rests on — and what was checked and does NOT give it.
- **`relief.features[].out` is ABSOLUTE from the part's own face; `lift` is SUMMED up the ancestor chain** (memory: relief-out-is-absolute-lift-is-summed). A feature with `lift: L` and `out: O` stands from L to O.
- **A module face gets no full-face `out` slab** that buries its detail (memory: relief-full-face-slab-buries-detail) — render every config you touch in 3D.
- Version bumps go in BEFORE `lock --update`; follow the repo's component versioning rule for each contract change and say which bump it required.
- Portrayal ships no populated device; tests seat on copies in `tmp_path` (`spec/tests/test_occupants.py` idiom).
- Verification is compiled and counted, not reasoned about: compile, read `data-z-out` / `data-z-lift` off the output, compare to the source numbers.

## Decisions already made (do not relitigate)

- **D1 — delete the body skins** (Jason, 2026-09-21): `common/qsfp-transceiver`'s five `body-*.svg` skins are deleted, not wired in. The part is retired (`superseded-by: generic/qsfp-lc@1`) and nothing reads them.
- **D2 — SFF-8432 was fetched** (Jason authorised) to `working/specs/sff-8432-r5.2a.pdf`. Controller's reading, recorded so it is not re-derived: Table 4-3 designator **A = 10.00 "Recommended Maximum" — "Module length extending outside of cage … Other lengths are application specific"**; Note 4: "Indicated outline defines maximum envelope outside of cage"; designator D 14.00 max width and L 2.10 max top height outside the cage; **Figure 4-2 "Latch Post Detail" is the cage-retention post, not the bail**. So SFF-8432 does NOT dimension the bail's forward reach. Note 13: an exposed coloured feature is colour-coded "Black or beige for multi-mode, Blue for single mode". The held SFF-8661 Rev 2.5 gives latch STRENGTH only, no pull-tab reach dimension.
- **D3 — seating depth by naming the feature** (Jason, 2026-09-21): a connection point may carry `on: <relief node>`; a boot seated there lifts by that feature's `out`. The RJ45 plug gets a standoff sourced where the documents allow; the LC plug gets an `estimated` standoff with a sentence naming the REFERENCE figures it rests on (B found no toleranced LC plug length: `(42)`, `(38.6)`, `(43)` REF across three SENKO drawings).
- **D4 — out of scope:** 2D side views showing a seated module's protrusion (spec open question); XFP/CFP/CFP2 (no generics exist); the OSFP MSA fetch (no OSFP generic exists); changing the generics' DEFAULT latch colour (see "Raised for Jason" below).

## Raised for Jason (not decided here)

SFF-8432 Note 13 makes an exposed SFP colour a MODE claim (blue = single mode). Both SFP generics default `latch-color` to `#2f5fa8` (blue), so every generic SFP drawn with its default claims single mode — a per-SKU fact L99 keeps off generics. D wires the colour through to 3D faithfully and does not change the default; the ledger carries this to the final report.

## File map

| file | change |
|---|---|
| `library/components/generic/{sfp-lc,sfp-lc-simplex,qsfp-lc,qsfp-dd-lc}/v1/contract.yaml` | re-sourced bail/tab sentences; drop the hard-coded `color` on bail/tab so 3D reads the art |
| `library/components/common/qsfp-transceiver/v*/` | delete `skins/body-*.svg` and every reference to them |
| `spec/schemas/component.schema.json` | `interface-at`; connection-point `on` |
| `spec/tools/portrayal/manifest.py` | `presented_interface` honours `interface-at` and `on` |
| `spec/tools/portrayal/lint.py` | an `on:` must name a relief feature with an `out`; `interface-at` must name a declared point |
| `spec/tools/portrayal/render.py` | a `mate-to` occupant of a host standing `in:` a well sinks with it |
| `library/components/generic/{lc-plug,rj45-plug}/v1/contract.yaml`, `common/{lc-boot,rj45-boot}/v1/contract.yaml` | `relief.features` (body, latch), `interface-at: boot`, `boot: {…, on: body}` |
| `spec/tests/test_pluggable_relief.py` (new), `test_seat_depth.py` (new), `test_sunk_host_occupant.py` (new) | the counted verification |

---

### Task 1: The transceivers — confirm, re-source, colour from the field

**Files:** the four generic transceiver contracts; `spec/tests/test_pluggable_relief.py` (new).

- [ ] **Step 1: Write the failing tests** in `test_pluggable_relief.py`. For each of the four generics, compile the standalone component (the path the build already uses for `library/dist/components/*.svg` — find it in `render.py`/`artifacts.py`, do not reimplement it) and read every `data-z-out` / `data-z-lift` / `data-z-color` off the output. Assert: body `out` is 10.0 (SFP) / 20.0 (QSFP, QSFP-DD) and its source cites the MSA designator verbatim (`SFF-8432 … Table 4-3 designator A`, `SFF-8661 … Figure 5-1`, `QSFP-DD HW … Figure 52`); the bail/tab node carries NO `data-z-color`; and — the colour test — compiling a placement of the generic with `fields: {latch-color: "#c03030"}` on a copy yields a bail/tab node whose fill is `#c03030` in the compiled drawing (so relief.js's `dominantColor` of the node's own art is red, not a hard-coded blue). Every assertion must fail on today's contracts for at least one generic.
- [ ] **Step 2:** run, see them fail.
- [ ] **Step 3: Edit the contracts.**
  - Remove `color` from the `bail` (SFP) and `tab` (QSFP, QSFP-DD) features. Leave the body's `color`.
  - SFP bail `source`: rewrite so it records what D2 found — SFF-8432 Rev 5.2a checked; Table 4-3 A is a 10.00 RECOMMENDED maximum with "other lengths application specific", Figure 4-2 is the cage latch post, so no figure dimensions the bail reach; 14.3 stays `estimated` and says what it was estimated from. Keep `confidence: estimated`.
  - QSFP / QSFP-DD tab `source`: add that SFF-8661 Rev 2.5 was checked and gives latch strength only, so the 34.80 reach rests on one vendor's (ProLabs) drawing — a vendor MAX, not the MSA's. Keep `confidence: drawing`, since it IS read off a drawing; the sentence says whose.
  - Body `source`s: confirm each against the held PDF (SFF-8432 Table 4-3 A; SFF-8661 Figure 5-1 Note 1; QSFP-DD HW 6.3 Figure 52 Note 4) and add the SFF-8432 "Recommended Maximum … other lengths are application specific" qualifier to the SFP body, which today says only "Recommended Maximum". Do not change any number unless the PDF contradicts it — if it does, stop and report.
  - Bump each contract's version per the repo rule.
- [ ] **Step 4:** tests pass; `lock --update` as the rule requires; `build`; `lint --new-only`.
- [ ] **Step 5:** commit; full suite.

### Task 2: Delete the dead body skins

**Files:** `library/components/common/qsfp-transceiver/v*/skins/body-*.svg` (delete), its contract, `spec/tools/portrayal/lint.py:~2996` (the comment that names them), `library/components/README.md` and any doc still claiming the viewer textures a box from them, `library/components/CATALOGUE.md` (regenerate — `publish.sh` does NOT regenerate it; find the generator).

- [ ] **Step 1: Test first:** a test asserting no component under `library/components/` ships a `body-*.svg` skin that nothing references, OR — if that generalises badly — that `common/qsfp-transceiver` has none. Plus a grep-style test that no `.md` under `library/` or `docs/` (excluding `docs/superpowers/plans/`) claims the viewer textures a box from body skins. Both fail today.
- [ ] **Step 2:** delete the files and every reference; decide the version bump by the repo rule (a skin is addressable — say whether removing one from a RETIRED major is a patch, minor or major here, and why); regenerate CATALOGUE.md.
- [ ] **Step 3:** tests pass; `lock`; `build`; `./publish.sh --no-images`; `lint --new-only`.
- [ ] **Step 4:** commit; full suite.

### Task 3: A point names the feature it sits on — the seat-depth mechanism

**Files:** `spec/schemas/component.schema.json`, `spec/tools/portrayal/manifest.py` (`presented_interface`), `spec/tools/portrayal/lint.py`, `spec/tests/test_seat_depth.py` (new).

**Interfaces:**
- Schema: top-level `interface-at: <connection-point name>` (optional; default `mate`), allowed only beside `interface`. A connection point gains optional `on: <relief feature node>`.
- `presented_interface(contract, resolve) -> (interface, at, lift)`: when the contract declares its own `interface`, the point is `connection-points[interface-at or "mate"]`; `lift` is `0.0` unless that point has `on:`, in which case `lift` = the `out` of the relief feature whose `node` equals `on`. The forwarded (composed-aperture) path is unchanged.
- Lint (register a new rule number in `RULES`, regenerate `docs/lint-rules.md`): `interface-at` names a declared connection point; `on:` names a relief feature that has an `out`. Errors, not warnings.

- [ ] **Step 1: Failing tests** (`test_seat_depth.py`): unit — a synthetic contract with `interface: lc-plug`, `interface-at: boot`, `boot: {at: [a,b], direction: rear, on: body}`, relief `body` out 12 → `presented_interface` returns `('lc-plug', [a,b], 12.0)`; without `interface-at`, returns the `mate` point and 0.0 exactly as today; `on` naming a missing node is a lint error; `interface-at` naming a missing point is a lint error. Integration — on a fitted copy of a device (seat `generic/sfp-lc-simplex@1` in an SFP cage, `generic/lc-plug@1` in it, `common/lc-boot@1` on the plug, via `occupants:` including the chained `port-N-occupant` keys), after Task 4 gives the plug a body `out`, the boot group's `data-z-lift` equals (optic's presented lift) + (plug body out), by hand arithmetic written in the test. Mark the integration case `xfail(strict=True)` until Task 4 lands, with a reason naming Task 4.
- [ ] **Step 2:** see them fail.
- [ ] **Step 3: Implement** in the schema, `presented_interface` and lint. Every existing caller of `presented_interface` must behave identically for contracts without the new keys — prove it: after the change, a full `build` must leave every compiled device SVG byte-identical to before (compare against a build of the pre-change tree in a scratch worktree, `git worktree add --detach <scratch> HEAD~0` before editing; remove it after).
- [ ] **Step 4:** tests pass (integration still xfail); regenerate lint docs; commit; full suite.

### Task 4: Plugs and boots stand off

**Files:** `generic/lc-plug`, `generic/rj45-plug`, `common/lc-boot`, `common/rj45-boot` contracts; `spec/tests/test_pluggable_relief.py`, `spec/tests/test_seat_depth.py`.

Sources already staged in `working/` (read them, never copy them): SENKO DS-LC-000004 Rev A (LC plug; body 5.58, silhouette 10.43, body height 5.65, latch 8.6 — toleranced; overall lengths only as `(42)` / `(38.6)` / `(43)` REF); SENKO DS-LC-000023 (LC boot 15.1 ±0.1); CommScope customer drawing 2843005 (RJ45 unshielded plug 11.68 × 7.93 × 22.48, latch 2.77 below datum); EASE J0072 rev A (RJ45 boot 26.4 ±0.5 × 14.5 × 10). The jack side: `std/rj45`'s registry depth in `spec/schemas/standards.yaml` and TE 1734264 (the jack the library already sources) — find what either says about how far a plug enters.

- [ ] **Step 1: Failing tests:** each of the four parts compiles with the features below and the numbers read back; the Task 3 integration case loses its `xfail`.
- [ ] **Step 2: The features.**
  - `generic/rj45-plug`: `body` `out` = the plug's standoff from the jack face. If BOTH the 22.48 length and a jack insertion depth are sourced (plain dimensions, not REF, not estimated), `out` = 22.48 − insertion and `confidence: drawing`, with the subtraction written in the source. Otherwise `estimated` with the sentence naming what is missing. A `latch` feature for the release latch (the eject affordance) with its reach: sourced if CommScope 2843005 dimensions it along the plug axis, else `estimated`. Remember the latch's 2.77 is in-plane Y (below the datum) — it is the skin's; only its Z extent is relief.
  - `generic/lc-plug`: `body` `out` `estimated`, with a sentence naming the REF figures and the reasoning (e.g. the portion of the body standing outside the bore). A `latch` feature: the latch is 8.6 long (toleranced) along the plug axis — use it for the feature's Z extent where it supports that, and say so.
  - Both plugs: `interface-at: boot`; `connection-points.boot` gains `on: body`. Leave `mate` exactly as it is (the plug still seats INTO its bore by `mate`).
  - `common/lc-boot`: `body` `out: 15.1`, `confidence: drawing`, SENKO DS-LC-000023. `common/rj45-boot`: `body` `out: 26.4`, EASE J0072. These are ABSOLUTE from the boot's own face; the chain supplies the lift.
  - The plugs' and boots' `cable` points: the cable lands where the boot ends. If `cablePoints` in `kit/relief.js` reports `z` from `data-z-lift` only (B made it `z === lift`), decide whether the cable point should now carry the boot's `out` as well, prove the answer against the Task 3 integration arithmetic, and change `resolveCablePoint` + its JS test only if the arithmetic says the current `z` is short. Record the decision either way.
  - Version bumps per the rule.
- [ ] **Step 3:** tests pass; `lock`; `build`; `./publish.sh --no-images`; `lint --new-only`.
- [ ] **Step 4:** commit; full suite.

### Task 5: A sunk host's occupant sinks with it

**Files:** `spec/tools/portrayal/render.py` (the mate-to seat lift, ~`:2012-2066`, and the `in:` sink, ~`:2112-2125`); `spec/tests/test_sunk_host_occupant.py` (new).

A placement standing `in:` a well is sunk by the well's floor (`sink(g, floor_of(p["in"]))`); a `mate-to` occupant is a TOP-LEVEL SIBLING of its host, so the sink never reaches it and the occupant sits at the panel above a sunk host.

- [ ] **Step 1: Census first** — count, across the library, `mate-to`/`occupants:` hosts that stand `in:` a well (placements and bays). Record the number in the report; do not assume zero.
- [ ] **Step 2: Failing test** on a fitted copy: a host with `in:` a well of known floor depth, an occupant seated on it; the occupant's effective depth (its `data-z-lift`, and whatever `sink()` writes on the host) must place it on the host's sunk face — by hand arithmetic.
- [ ] **Step 3: Implement** — carry the host's sink into the occupant's seat lift at resolution time, the way `host-lift` already carries the host's own seat (a chained seat inherits the whole stack). Keep the trio intact (`z_inset`, `z_group_lift`, `data-z-lift` — memory: the attribute alone double-counts).
- [ ] **Step 4:** test passes; `build` leaves every device SVG byte-identical EXCEPT any the census found (list them); commit; full suite.

### Task 6: Gates, and the counted 3D check

- [ ] **Step 1:** `lock`, `build`, `./publish.sh --no-images`, `lint --new-only`, full suite. Tree clean.
- [ ] **Step 2 (report):** a table per part — node, `out`, `lift`, confidence, the source figure — read off the COMPILED output (not the contract), beside the source number.
- [ ] **Step 3 (controller, browser pane on screen):** the kit only swaps DEVICE cages (plugs and boots seat through the build's `occupants:` chain), and the explorer reads only `library/dist`, so render a fitted copy (from `tmp`/scratchpad, never a shipped manifest) into `library/dist` under a scratch device name for the check, and rebuild `library/dist` clean afterwards (it is gitignored). Then: a populated SFP port with `generic/sfp-lc@1` + `generic/lc-plug@1` + `common/lc-boot@1` and an RJ45 port with plug + boot, from three-quarter and side, composited screenshots (not buffer readbacks); a `latch-color` override visibly recolours the bail in 3D; beside product photographs from the staged set (open the photographs first — memory). One compare page for Jason's sign-off.
