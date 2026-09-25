# Pluggables: the head outside the cage

Status: draft, 2026-09-25. First of two pieces of work that add cable ends (DAC, ACC, AEC,
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
| FS SFP-GE-T datasheet (1000BASE-T) | 14 (2.70 above, 2.26 below an 8.60 body) | 13.40 +/-0.1 | 21 | 68 MAX |
| Cambium SFP-10G-Copper Rev .02, Fig 6 | 2.70 +/-0.10 above, 2.60 below an 8.50 body | 13.70 +/-0.10 | - | - |

SFF-8432 lets the length run long ("application specific"), but it states the height as a
MAXIMUM, and every copper SFP is 1.2 to 2 mm over it. A contract therefore has to be able to
say "this part exceeds the standard's outside envelope" and cite why. That is not an error
to suppress, it is a fact about the part class.

**The real QSFP pull tab** (the maintainer's photographs of a QSFP28-SR4 module, top, side
and end views; the existing ProLabs PAN-QSFP28-100GBASE-CWDM4-C drawing for the reach) is:

- a flat U-loop in plan, with two thin arms along the module's side edges and a wider grip
  pad at the far end; the middle is open, so the fibre connector passes through it;
- a thin strap in side view, leaving the nose low, running forward, and kicking UP at the
  grip in an S-bend;
- seen end on, a grip pad that sits ABOVE the top edge of the face, so the receptacle stays
  visible. This is what SFF-8661's "3.4 MAX above, including bail travel" allows for.

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
   measured against the photographs: arms at the side edges, grip above the body top,
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

### 4.3 Lint: L121, the head

For every component with `behaviour: occupies` and a `conforms:` naming a registry entry
that has `head:`:

1. It declares `head:`.
2. `head.size` is within the registry's head envelope, measured against the module's own
   `size` (`above` = `-head.at[1]`, `below` = `head.at[1] + head.size.h - size.h`, width
   and length direct), or every dimension over it is listed in `exceeds:` with a source.
   A `recommended` length that is exceeded is a note, not an error.
3. `exceeds:` names only dimensions that actually exceed (a stale waiver is an error).
4. Every relief feature's `out` is at most `head.size.d` plus the pull tab's reach, which is
   declared on the tab itself as `reach:` (so a tab is never mistaken for an oversize head).
5. The face's front outline node carries the head's bbox to within 0.05.

Next free rule number on main at the time of writing is L121; the plan confirms it.

### 4.4 Build: fields reach composed parts

`render.py`'s `fill_from_attrs` gets the host's merged field values for a composed part
whose contract declares the same field key. A part's own `parts:` entry `attrs` still win,
so a host that pins a colour on a composed part keeps doing so. Tests: the existing
`test_colour_is_a_field.py` and `test_stroke_derive.py` gain a composed case, built
against the defect first.

### 4.5 `common/qsfp-pull-tab@2`

- Arms `arm-l`, `arm-r`: thin, at the module's side edges, from the nose front forward.
- Grip `grip`: at the far end, spanning the 19.0 MAX width, positioned so it rises ABOVE
  the body top, inside the 3.4 above allowance.
- A two-step approximation of the S-bend: arms low, grip high. Relief builds boxes; no new
  primitive. The round `uhandle` primitive is wrong for a flat strap and is not used.
- `reach: 34.80` (ProLabs, drawing); arm width, grip length and grip height are MEASURED
  off the top and side photographs against the known 18.35 module width, and say so.
- A `default` skin whose fill follows `latch-color` (`data-fill-from`, `data-stroke-derive`),
  default the neutral grey `#6f6f6f` (decision taken in #473).
- No speed lettering. `@1` keeps its `white` and `blue` skins and its `100G` cut, and is
  marked `superseded-by: common/qsfp-pull-tab@2`.

### 4.6 `generic/qsfp-lc` and `generic/qsfp-dd-lc`

- Drop the painted `tab` rectangle; compose `common/qsfp-pull-tab@2` with `id: tab`, so
  the `tab` address still resolves (now to a group).
- Declare `head:` (18.35 x 8.5 face, protrusion 20.0; within the envelope, no `exceeds:`).
- The bump follows the README's versioning rule, recorded as a ruling in the plan. If
  keeping `id: tab` preserves every address, it is a minor; otherwise a major, with `@1`
  marked `superseded-by`, and the test fixtures that name `@1` stay on it or move with a
  reason.

### 4.7 `generic/sfp-rj45@1`

- `class: transceiver`, `behaviour: occupies`, `mates: sfp`, `conforms: sfp-module`,
  `size: {w: 13.55, h: 8.55, d: 47.50}` (registry, L9).
- `head:` from the Finisar table: 13.55 x 13.20, 22.70 outside the cage; `exceeds:
  [above, below, length]` with the four sources in section 2.
- Composes `std/rj45-ganged@2` in the head face, so it PRESENTS `rj45` and a configuration
  can seat `generic/rj45-plug@1` + `common/rj45-boot@1` in it (the iterative `mate-to` chain
  from spec B).
- The latch (bail or delatch tab) and the jack's orientation (latch slot up or down) are
  read off photographs at modelling time; the stacked-cage 180 turn already exists.
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

## 6. Testing and gates

1. Unit: L121 each clause, with a passing and failing fixture per clause; the stale-waiver
   case; the `recommended` note.
2. Build: a composed part takes its host's field (runs RED against today's render first).
3. Seating: SFP cage -> `generic/sfp-rj45` -> `generic/rj45-plug` -> `common/rj45-boot`, in
   2D and in the kit (`test_cage_seat_js` family), and the plug's `cable` point lands at the
   boot's rear.
4. 3D: GLB mesh bboxes for the copper SFP head (its top at the settled `above`, section 8) and for the
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

## 8. Open questions for the plan

- The exact `above` and `below` split of the copper SFP head. Finisar gives the total (C
  13.20) and the body (B 8.45); FS and Cambium give 2.70 above. The plan reads Finisar's
  L, N and P against its side view to settle it before building.
- Whether the QSFP generics' bump is a minor or a major (section 4.6).
- Whether `head:` belongs in the component JSON schema as a new top-level key or under
  `relief:`. This note assumes top level, because a downstream tool that never builds 3D
  still needs it.

## Decisions taken

- 2026-09-25: the pull tab fix belongs in this piece of work, not a separate one, because
  its height allowance is the same outside envelope the copper SFP needs.
- 2026-09-25: DAC, ACC, AEC and AOC are one generic cable end per form; the kind, cable OD
  and colour live on the vendor wrapper and in fields.
