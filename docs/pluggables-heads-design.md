# Pluggables: the head outside the cage

Status: implemented, 2026-09-25. First of two pieces of work that add cable ends (DAC, ACC, AEC,
AOC) and the copper SFP as pluggable choices. This one gives a pluggable a HEAD, the part
that stands outside the cage, and ships the first two things that need one: a copper SFP
and a real QSFP pull tab. The cable ends follow in a second design note and reuse
everything here.

Related: [pluggables-design.md](pluggables-design.md) (the umbrella, decisions 1-10),
[pluggables-generics-design.md](pluggables-generics-design.md) (spec A, where
`generic/sfp-rj45` was gated), [pluggables-3d-design.md](pluggables-3d-design.md) (spec D).

## 1. Why

Three things are wrong or missing today, and all three have the same cause: the library
has no way to say how big a module is OUTSIDE its cage.

1. **The copper SFP is gated for the wrong reason.** Spec A refused `generic/sfp-rj45`
   because every RJ45 jack in the library (11.0 and taller) is taller than the 8.55 SFP
   envelope. But 8.55 is the envelope INSIDE the cage. The jack sits in the head, outside
   it, and the head is allowed to be larger.
2. **The QSFP pull tab is a brick.** `generic/qsfp-lc@1` and `generic/qsfp-dd-lc@1` draw
   the tab as one solid 19.0 x 3.4 rectangle from 20.0 to 34.8 mm. In 3D that is a block,
   and in 2D it is a grey band painted ACROSS the face, over the LC bores. They stopped
   composing `common/qsfp-pull-tab@1` (which has the real loop) only because a composed
   part could not take the generic's `latch-color` field at build time.
3. **The protrusion is a bare number.** Each generic carries its protrusion as
   `relief.features[body].out` with prose provenance, and nothing checks it against the
   standard that governs it.

## 2. What the sources say

All three MSAs define a maximum envelope for the section outside the cage, separate from
the module envelope inside it:

| form | width | above the module top | below the module bottom | length | source |
|---|---|---|---|---|---|
| SFP | 14.00 MAX (D) | 2.10 MAX (L) | 1.40 MAX (AK) | 10.00 RECOMMENDED MAX (A): "other lengths are application specific" | SFF-8432 Rev 5.2a, Table 4-3, Note 4 ("maximum envelope outside of cage") |
| QSFP | 19 MAX | 3.4 MAX (Note 6: includes bail travel) | 1.6 MAX | 20 MAX | SFF-8661 Rev 2.5, Figure 5-1, Note 1 ("enlarged section of transceiver that extends outside of cage to accommodate mating plug and actuator mechanism") |
| QSFP-DD | 19 MAX | 3.4 MAX | 1.6 MAX | 20 MAX Type 1, 35 MAX Type 2 | QSFP-DD HW Rev 6.3, Figure 52, Note 4; section 7.1 |

QSFP-DD HW 6.3 Appendix B also dimensions the pull handle (about 50 long on a Type 1,
118 REF overall from datum D, at the 13.5 REF latch height).

**Real copper SFPs exceed SFF-8432's outside envelope.** Four independent drawings agree:

| source | head height | head width | outside the cage | overall |
|---|---|---|---|---|
| Finisar FCLF852xP2BTL product spec Rev E, Fig 2 (toleranced table) | C 13.20 +/-0.2 | A 13.55 +/-0.25 | X 22.70 +/-0.3 | K 70.20 REF |
| Optcore SFPP-T-TCA5 datasheet (10GBASE-T) | 13.7 +/-0.10 | 13.4 +/-0.10 | 20.4 (67.90 - 47.5) | 67.90 +/-0.10 |
| FS SFP-GE-T datasheet (1000BASE-T) | 14 (2.70 above, 2.70 below an 8.60 body, untoleranced) | 13.40 +/-0.1 | 21 | 68 MAX |
| Cambium SFP-10G-Copper Rev .02, Fig 6 | 2.70 +/-0.10 above, 2.60 below an 8.50 body | 13.70 +/-0.10 | - | - |

SFF-8432 lets the length run long ("application specific"), but it states the height as a
MAXIMUM, and every copper SFP is 1.2 to 2 mm over it. A contract therefore has to be able to
say "this part exceeds the standard's outside envelope" and cite why. That is not an error
to suppress, it is a fact about the part class.

**The real QSFP pull tab** (the maintainer's photographs of a QSFP28-SR4 module, top, side
and end views; QSFP-DD HW Rev 6.3 Appendix B, Type 1, for the reach) is:

- a flat U-loop in plan, with two thin arms along the module's side edges and a wider grip
  pad at the far end; the middle is open, so the fibre connector passes through it;
- a reach of 49.8 measured from the NOSE FRONT (118 REF - 48.2 MIN - 20 nose, per Appendix
  B's Type 1 drawing), corroborated by the photographs (mean 49.9, within 8%). The ProLabs
  PAN-QSFP28-100GBASE-CWDM4-C drawing's 34.80 does not describe this tab;
- a thin strap in side view: it leaves the nose near the top, dips about 1.8 mm mid-span,
  and rises 0.5 mm at the grip;
- seen end on, a grip pad that straddles the face's top edge rather than sitting wholly
  above it: it is 1.07 above the body top, so the receptacle stays partly visible. This is
  what SFF-8661's "3.4 MAX above, including bail travel" allows for.

## 3. Decisions

1. **A pluggable declares a `head:`**, the box it occupies outside the cage. It is a
   contract key, not relief: relief still builds the solid, `head:` is the envelope that
   relief, lint and a downstream tool read.
2. **The standards' outside envelopes go in the registry** as `head:` on `sfp-module`,
   `qsfp-module` and `qsfp-dd-module` in `spec/schemas/standards.yaml`. Maximums are
   maximums; SFF-8432's length is marked `recommended`.
3. **A head may exceed its registry envelope only with `exceeds:`**, which names the
   dimension or dimensions and carries a source. The copper SFP is the first user.
4. **A composed part inherits a field value from its host** when both declare the same
   field key. That is already true at runtime (`kit/fields.js` repaints every matching
   node in the part's group, composed children included); this makes the build agree.
5. **The QSFP generics compose the pull tab again**, a revised `common/qsfp-pull-tab`
   measured against the photographs: arms at the side edges, grip straddling the body top,
   colour from `latch-color`. The speed lettering on the grip (`100G`) is dropped from the
   default, because a generic carries no rate (L99).
6. **`generic/sfp-rj45@1` composes `std/rj45-ganged@2` in its head** (11.91 x 10.5
   opening, 18.6 deep, `interface: rj45`), which fits inside a 13.55 x 13.20 head and a 22.70
   protrusion. The single `std/rj45@2` (15.8 wide) does not fit and is not used.
7. **The copper SFP is modelled on the Finisar table**, the only one toleranced on every
   dimension; Optcore, FS and Cambium corroborate it and their spread is recorded.
8. **Every module-conforming occupant declares a head**, so the check applies to the four
   existing optical generics too, not just the new part.

## 4. The pieces

### 4.1 Registry: `head:` on the three module envelopes

```yaml
sfp-module:
  head:
    w-max: 14.00
    above-max: 2.10
    below-max: 1.40
    length-max: 10.00
    length-kind: recommended     # SFF-8432 A: "other lengths are application specific"
    source: 'SFF-8432 Rev 5.2a Table 4-3 designators D, L, AK, A; Note 4'
qsfp-module:
  head: {w-max: 19.0, above-max: 3.4, below-max: 1.6, length-max: 20.0,
         source: 'SFF-8661 Rev 2.5 Figure 5-1, Notes 1 and 6'}
qsfp-dd-module:
  head: {w-max: 19.0, above-max: 3.4, below-max: 1.6,
         length-max: {type-1: 20.0, type-2: 35.0},
         source: 'QSFP-DD HW Rev 6.3 Figure 52, Note 4; section 7.1'}
```

### 4.2 Contract: `head:`

On any occupant that `conforms:` to a module envelope:

```yaml
head:
  at: [0.0, -2.70]           # top-left of the head's front outline, in face coordinates (illustrative)
  size: {w: 13.55, h: 13.20, d: 22.70}   # d is the length outside the cage
  size-confidence: {w: drawing, h: drawing, d: drawing}
  type: 1                    # qsfp-dd only; selects the registry's length-max
  exceeds:                   # only when the head is larger than the registry envelope
    - {dimension: above, source: '...'}
```

The prose for it lives in `provenance.head`, as for every other key. `at` may be
negative and `size` may exceed the contract's `size`: the head overhangs the face the
cage accepts. The skin draws the head's front outline over that box. Art outside
the viewBox already renders (the QSFP tab straddles the face by 0.325 each side today); a
gate confirms it for a head that overhangs in y.

**Standalone preview framing.** A part that declares `head:` gets a standalone component
preview (`library/dist/components`, the explorer's module view) framed to the union of its
size box, its head box, and its composed parts' boxes, keeping its own origin. A part
without a head is untouched. The 3D module face is unaffected: it keeps its size box, since
the kit's `relief.js` consumer assumes a face's viewBox equals its size (a `sizeBox: true`
flag on the viewer3D component face preserves this).

### 4.3 Lint: L121, the head

For every component with `behaviour: occupies` and a `conforms:` naming a registry entry
that has `head:`:

1. It declares `head:`.
2. `head.size` is within the registry's head envelope, measured against the module's own
   `size` (`above` = `-head.at[1]`, `below` = `head.at[1] + head.size.h - size.h`, width
   and length direct), or every dimension over it is listed in `exceeds:` with a source.
   A `recommended` length that is exceeded is a note, not an error.
3. `exceeds:` names only dimensions that actually exceed (a stale waiver is an error).
4. Every relief feature's `out` is at most `head.size.d`. This checks only the host's OWN
   relief features: a composed part (such as the pull tab) has its own contract, on its
   own mounting plane, and its relief is never compared to the host's head. There is no
   `reach:` key.
5. The face's front outline node carries the head's bbox to within 0.25, not 0.05: a skin
   insets its outline by half a stroke, and 0.05 would fail every real part. The head's own
   figures (in the registry and the contract) stay at 0.05.

The rule is L121, the next free rule number on main when it was written.

### 4.4 Build: fields reach composed parts

`render.py`'s `instance_group` passes the host's merged field values to a composed part
(its `inherited_fields=` argument), keeping only the keys the part's contract declares, and
they feed that part's `fill_from_attrs`. A part's own `parts:` entry `attrs` still win,
so a host that pins a colour on a composed part keeps doing so. Test:
`spec/tests/test_fields_reach_composed_parts.py`, built against the defect first.

### 4.5 `common/qsfp-pull-tab@2`

- Arms `arm-l`, `arm-r`: thin, at the module's side edges, from the nose front forward.
- Grip `grip`: at the far end, spanning the 19.0 MAX width, positioned where it was
  measured: it straddles the body's top edge (y -1.07 to 1.83 in the face), its top 1.07
  above the body top, inside the 3.4 above allowance.
- A two-step approximation of the S-bend: arms low, grip high. Relief builds boxes; no new
  primitive. The round `uhandle` primitive is wrong for a flat strap and is not used.
- Reach 49.8 from the nose front (QSFP-DD HW 6.3 Appendix B, Type 1; drawing), corroborated
  by the photographs; arm width, grip length and grip height are MEASURED off the top and
  side photographs against the known 18.35 module width, and say so.
- A `default` skin whose fill follows `latch-color` (`data-fill-from`, `data-stroke-derive`),
  default the neutral grey `#6f6f6f` (decision taken in #473).
- No speed lettering. `@1` keeps its `white` and `blue` skins and its `100G` cut, and is
  marked `superseded-by: common/qsfp-pull-tab@2`.

### 4.6 `generic/qsfp-lc` and `generic/qsfp-dd-lc`

- Drop the painted `tab` rectangle; compose `common/qsfp-pull-tab@2` with `id: tab`, so
  the `tab` address still resolves (now to a group).
- Declare `head:` (18.35 x 8.5 face, protrusion 20.0; within the envelope, no `exceeds:`).
  The head node is the face's body (a rect, 0.1 inset for the skin's stroke — within the
  0.25 tolerance of L121 point 5).
- The bump is a major: `generic/qsfp-lc` and `generic/qsfp-dd-lc` go to `@2` (the CONTRIBUTING
  versioning rule — the tab geometry moved, not just the address). `@1` stays, marked
  `superseded-by: @2`, so the mechanism tests that use `@1` as a fixture keep working.
- Parked finding, not built this piece of work: the maintainer's photographs also measure
  the QSFP nose itself about 11.5 tall (1.6 above, 1.4 below the body top and bottom; within
  SFF-8661's 3.4/1.6 allowance) and a riser block about 7.5 long at the arm roots. The head
  stays the 18.35 x 8.5 face this PR; the nose and riser are not modelled. See section 5.

### 4.7 `generic/sfp-rj45@1`

- `class: transceiver`, `behaviour: occupies`, `mates: sfp`, `conforms: sfp-module`,
  `size: {w: 13.55, h: 8.55, d: 47.50}` (registry, L9).
- `head:` from the Finisar table: 13.55 x 13.20, 22.70 outside the cage; `exceeds:
  [above, below, length]` with the four sources in section 2.
- Composes `std/rj45-ganged@2` in the head face, so it PRESENTS `rj45` and a configuration
  can seat `generic/rj45-plug@1` + `common/rj45-boot@1` in it (the iterative `mate-to` chain
  from spec B).
- The jack is composed at rotate 180, keyway up (the Finisar and FS front views agree; see
  Decisions taken). No latch is drawn: the bail's pivot is vendor-specific (next item).
- No `latch-color` field: no bail is drawn (the pivot is vendor-specific — Finisar draws a
  top-front bail, Cambium and Optcore pivot at the bottom-front), so there is no colour for
  a field to paint (L73 is right to not require one).
- L76 does not ask this jack for lamps: copper SFPs carry no link LEDs (the host port's
  LEDs report the link), and L76 skips any contract whose class is `transceiver`. The
  Finisar and Cambium front-view drawings were checked and show no LED window.
- No rate, no reach, no power: it stands for 1000BASE-T, 10GBASE-T and NBASE-T alike
  (L99). The 10GBASE-T parts are a little shorter (Optcore 67.90 vs Finisar 70.20) and
  that spread goes in provenance, not in a second part.

### 4.8 The existing SFP generics

`generic/sfp-lc@1` and `generic/sfp-lc-simplex@2` declare `head:` (13.55 x 8.55, protrusion
10.0, within the envelope). Additive, so a minor bump each.

## 5. What does not change

- Portrayal still ships devices bare (umbrella decision 2). A copper SFP appears in a cage's
  accept list because it `mates: sfp`; nothing seats it by default.
- The explorer's swap menu offers `generic/sfp-rj45` automatically. It does NOT yet offer a
  plug INTO the copper SFP's jack: RJ45 connector slots are not in the swap menu (B3 left
  `rj45` out until its covers land). A configuration can seat one; that is tested.
- Head collisions between neighbouring cages (a copper SFP beside another in a tight 2xN)
  are real and vendors warn about them, but checking them needs seated occupants, which the
  library does not ship. Noted, not built.

Parked follow-ups, not built this piece of work:

- The QSFP nose height (about 11.5 tall per the photographs) and its riser block (about
  7.5 long) are not modelled; the head stays the 18.35 x 8.5 face (section 4.6).
- The pull tab's S-bend and its riser are approximated as a two-step (arms low, grip high),
  not modelled as a curve.
- RJ45 connector slots are not in the explorer's swap menu (section 5); a configuration can
  still seat one directly.
- A kit-vs-build coordinate check for the full copper-SFP-to-boot chain needs kit support
  the explorer does not have yet (the kit seats one occupant per cage); the copper chain's
  JS coverage stops one link short of that.

## 6. Testing and gates

1. Unit: L121 each clause, with a passing and failing fixture per clause; the stale-waiver
   case; the `recommended` note.
2. Build: a composed part takes its host's field (runs RED against today's render first).
3. Seating: SFP cage -> `generic/sfp-rj45` -> `generic/rj45-plug` -> `common/rj45-boot`,
   tested in the build (`test_copper_sfp_chain.py`). The kit's coverage is the `bodyRole`
   case in `test_body_role_js.py` (the boot is its own removable part, three deep); a kit
   coordinate check of the chain is a parked follow-up (section 5).
4. 3D: checks that read the compiled SVG's relief attributes (`data-z-out`, `data-z-lift`,
   the cavities) for the copper SFP head (its top at the settled `above`, section 8) and for the
   pull tab (two arms, one grip, no solid between the arms), per
   [pluggables-3d-design.md](pluggables-3d-design.md). The composed tab's `out` must not be
   double-lifted (the `out`-absolute, `lift`-summed rule).
5. 2D: head art that overhangs the viewBox in y is present in the compiled SVG and on
   screen.
6. Census tests: the new part joins every count and exemption table it should; nothing is
   waived.
7. A human review page before the full rebuild: the photographs and drawings beside the
   2D and 3D renders of `generic/sfp-rj45`, `generic/qsfp-lc` and `generic/qsfp-dd-lc`,
   seated in a real device, with close-ups. Sign-off, then gates.
8. Gates: lock, lint (no change against the baseline except L121's new passes), build,
   publish, catalogue, the full suite with `-n auto`, and CI time compared with main's last
   green run.

## 7. Out of scope (the second design note)

The cable ends: `generic/sfp-cable`, `generic/qsfp-cable`, `generic/qsfp-dd-cable`, one
per form, closed face, pull strap and ring, strain relief, a cable stub with OD and colour
as fields, and DAC/ACC/AEC/AOC on the vendor wrapper. Their heads are already sourced
(SFP+ DAC: Molex 747520001, Amphenol C-NJDDGN-0099; QSFP28 DAC and ACC: FCI 10121178,
Amphenol C-NDAAFR-0099, C-NDAAXF-0099, C-NJAAF3-0099; QSFP-DD DAC: Volex; QSFP28 AOC: FS),
except the AEC head, which is known only as a QSFP-DD Type 2 extension.

## 8. Open questions, all settled

- ~~The exact `above` and `below` split of the copper SFP head.~~ Resolved: 2.50 above,
  2.15 below (see Decisions taken).
- ~~Whether the QSFP generics' bump is a minor or a major (section 4.6).~~ Resolved: major
  (see Decisions taken).
- ~~Whether `head:` belongs in the component JSON schema as a new top-level key or under
  `relief:`.~~ Resolved: top level, because a downstream tool that never builds 3D still
  needs it; `components.json` publishes it.

## Decisions taken

- 2026-09-25: the pull tab fix belongs in this piece of work, not a separate one, because
  its height allowance is the same outside envelope the copper SFP needs.
- 2026-09-25: DAC, ACC, AEC and AOC are one generic cable end per form; the kind, cable OD
  and colour live on the vendor wrapper and in fields.
- 2026-09-25: the copper SFP jack's rotate is 180 (Finisar Rev E and FS SFP-GE-T front
  views agree: keyway up, contacts down, label-side up; `std/rj45-ganged@2` at rotate 0
  has its slot down).
- 2026-09-25: the copper SFP head splits 2.50 above / 2.15 below (Finisar Y 2.50 +/-0.2,
  head top to body top, same on both revisions, against the registry's 8.55 body; 13.20 -
  8.55 - 2.50 = 2.15). Finisar's own 2.25 against its 8.45 body is within tolerance.
- 2026-09-25: the head node (L121 point 5) is compared to its bbox at 0.25, not 0.05: a
  skin insets its outline by half a stroke, so 0.05 would fail every real part. The head's
  own figures, in the registry and the contract, stay at 0.05.
- 2026-09-25: the pull tab's reach is measured from the nose front, 49.8 (QSFP-DD HW 6.3
  Appendix B, Type 1), corroborated by the photographs (mean 49.9); the ProLabs 34.80 does
  not describe this tab and is dropped as a source for it.
- 2026-09-25: `generic/sfp-rj45` carries no `latch-color` field, because it draws no bail
  (the pivot is vendor-specific); L73 correctly does not require a field with nothing to
  paint.
- 2026-09-25: L76 skips a contract whose class is `transceiver` when checking for lamps:
  copper SFPs carry no link LEDs, so asking their jack for one is a false positive.
- 2026-09-25: a composed part's own relief (such as the pull tab's) is never compared to
  its host's `head.size.d` (L121 point 4) — it lives on the composed part's own contract
  and its own mounting plane, not the host's.
- 2026-09-25: the standalone component preview of a part with `head:` frames to the union
  of its size, head and composed-parts boxes; the 3D module face keeps its size box.
- 2026-09-25: `generic/qsfp-lc` and `generic/qsfp-dd-lc` bump to `@2` (major, per
  CONTRIBUTING's versioning rule) because the tab's geometry moved, not just its address;
  `@1` is kept, marked `superseded-by`, so fixtures pinned to it keep working.
- 2026-09-25: the pull tab is placed where it was MEASURED, straddling the body's top edge
  (its grip at y -1.07 to 1.83, its top 1.07 above the body top), not wholly above the face
  as first specified. In 2D it therefore hides about 0.9 mm of the bore housing's top.
- 2026-09-25: the pull tab's grip length is the orthographic top view's 11.2 alone; the
  other top view failed the orthography check and is a cross-check only. The arms run out
  49.8 - 11.2 = 38.6, and the grip from 38.6 to 49.8.
- 2026-09-25: the S8901-54XC management jack's finish correction (the black plastic finish
  now reaches the composed `std/rj45@2` housing, matching what the kit already painted at
  runtime) is an intended fix, not a regression, and its changed front-view render is
  expected.
