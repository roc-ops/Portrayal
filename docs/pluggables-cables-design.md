# Pluggables: cable ends

Status: implemented, 2026-09-26. The second of two pieces of work that add cable ends and the copper
SFP. It builds on [pluggables-heads-design.md](pluggables-heads-design.md), which gave every
module-shaped pluggable a declared `head:`, checked by L121, and let a composed part take its
host's field.

Related: [pluggables-design.md](pluggables-design.md) (decisions 1-10, the vendor-wrapper
idiom), [pluggables-connectors-design.md](pluggables-connectors-design.md) (the `cable` point,
and the "DAC/AOC ends" it deferred to here).

## 1. What a cable end is

A direct-attach or active cable is a MODULE in the cage and a CABLE outside it. SFF-8661 and
SFF-8663 both define "module" to include direct attach copper; QSFP-DD HW 6.3 section 7.1 says
module and cable plugs "must mate to the connectors and cages defined in this specification".
Inside the cage a cable end is the same envelope as an optic. What differs is outside it:

- a closed head (the backshell) with no optical or electrical face; the cable leaves from
  the middle of its front;
- a flat pull strap that lies along the cable and ends in a ring or loop;
- a moulded strain relief behind the head;
- the cable.

The four kinds are the same thing to the eye. They differ in the cable (thickness and jacket
colour) and in the electronics in the head, which nothing draws:

| kind | in the head | cable OD seen in the corpus |
|---|---|---|
| DAC (passive) | nothing but the ID EEPROM | 6.1-11.6 (Panduit, NVIDIA, Volex: heavier gauge, thicker) |
| ACC (active copper) | a redriver per lane | 6.9 (NVIDIA MCA1J00, 30AWG) |
| AEC (active electrical) | a retimer per lane | 5.3 (Credo HiWire SHIFT, 4P 30AWG) |
| AOC (active optical) | lasers and receivers | 3.0 +/-0.15 (Siemon) |

So there is ONE generic per form, and the kind lives on the vendor wrapper (decided 2026-09-25).

## 2. Decisions

1. **One generic per form**, and a second for the longer QSFP-DD head: `generic/sfp-cable`,
   `generic/qsfp-cable`, `generic/qsfp-dd-cable` (Type 1) and `generic/qsfp-dd-cable-type2`.
   Type 1 and Type 2 are the MSA's own form distinction (QSFP-DD HW 6.3 section 7.3, Figure 52
   Note 4: 20 MAX and 35 MAX outside the cage), so the name follows the form.
2. **Draw a short stub of cable.** It runs straight past the strain relief for the bend
   clearance the drawings specify, and the `cable` connection point moves to its end, so a
   downstream tool continues the run from there. Portrayal still ships no cable ASSEMBLY:
   which two ends belong together, and the run between them, are downstream data (umbrella
   decision 2).
3. **The stub's diameter and colour are FIELDS**: `cable-od` (mm) and `jacket-color`, with
   the strap's colour on `latch-color` as it is on the optics. A wrapper sets them; a
   placement will override them once occupants take attrs (section 4).
4. **A field may set a size, not only a colour.** A new skin binding, `data-r-from`, sets a
   circle's radius to half a field's value at build time. The kit applies it at runtime in 2D;
   3D takes the new size at the next load.
5. **The kind is an attr on the wrapper**: `cable-kind: dac | acc | aec | aoc`. L99 forbids it
   on a generic, alongside rate and reach.
6. **The Type 1 QSFP-DD generic ships at the MSA maximum.** No held drawing dimensions a Type 1
   cable head: the one QSFP-DD cable drawing held (Volex) is a Type 2. The part says so, and
   its head length carries the confidence `registry` (the library's term for a figure taken
   from spec/schemas/standards.yaml, where the MSA maximum lives), not `drawing` (decided
   2026-09-25).
7. **The pull strap is drawn in each generic**, not as a shared part. It is not the optic's
   U-loop: a cable's strap lies on top of the cable and ends in a ring, where an optic's loop
   straddles the face. Its length and width follow the form (about 43 for SFP, 61.5 for QSFP,
   40 for QSFP-DD Type 2 and 50 for Type 1 past the head, each to the far end of its ring or
   grip; section 3), and one shared part could not carry three lengths without a second
   geometry-from-field mechanism. It takes `latch-color` as the optics' latch does (decided
   2026-09-25; the draft planned a `common/cable-pull-strap` part).
8. **Breakout cables are ends.** A QSFP-DD to 8 x SFP56 breakout is one `qsfp-dd-cable` end and
   eight `sfp-cable` ends. Nothing here relates them.

## 3. The four generics

Every head figure is checked by L121 against the registry envelope for its form.

| part | head outside the cage (w x h x d) | source | stub | default `cable-od` |
|---|---|---|---|---|
| `generic/sfp-cable` | 13.55 x 11.50 x 10.8 | Molex customer drawing 747520001 rev V1: 13.55 +/-0.25 wide, backshell 11.50 REF tall, 58.30 REF from the front less the 47.50 in-cage body; 10Gtek SFP+ passive DAC V1.3 corroborates (58.4 +/-0.2, 11.65 +/-0.1) | 30 past the boot | 4.8 (Amphenol C-NJDDGN-0099: 25AWG dual-drain with braid) |
| `generic/qsfp-cable` | 18.35 x 13.10 x 19.8 | FCI 10121178 rev J: 72.20 head, 18.35 wide, 12.76 at the backshell, 13.10 at the tab; Amphenol C-NDAAFR-0099 and C-NDAAXF-0099: diecast 72.2 REF; 72.2 less the 52.4 in-cage body | 30 past the boot | 6.9 (NVIDIA MCP1600 and MCA1J00, 30AWG) |
| `generic/qsfp-dd-cable` (Type 1) | 18.35 x 13.5 x 20 | QSFP-DD HW 6.3 Figure 52: 20 MAX for Type 1 - the MSA maximum, confidence `registry`; no drawing | 30 past the boot (estimated) | 9.0 (Volex, 30AWG) |
| `generic/qsfp-dd-cable-type2` | 18.35 x 13.5 x 28.3 | Volex 400G QSFP-DD passive DAC data sheet: head 86.56 +/-0.15 less the 58.26 in-cage body; within Type 2's 35 MAX | 30 past the boot (estimated) | 9.0 (Volex, 30AWG) |

The head's HEIGHT above and below the body comes from each drawing's side view at modelling
time, measured against the body height the drawing itself gives, as the copper SFP's did.

The pull strap's reach past the head, per form: SFP 43.1, scaled off the Molex drawing
(estimated); QSFP 61.5 to the ring's far edge (Amphenol lanyards, 61.5-75 REF); QSFP-DD Type 2
40, the Volex loop (estimated; QSFP-DD HW 6.3 Appendix B's 41.5 corroborates); Type 1 50
(Appendix B, informative). Three figures read in the draft as strap lengths are not: Molex's
103 +/-10 and Volex's 150 +/-10 locate the cable LABEL, and FCI's 50 +/-15 (Note 5) is the
label position too. Amphenol's 50 APPROX runs to the braid end, not to the loop.

The stub is 30 long and starts at the boot's end, one rule for every form. For QSFP that ends
exactly at Amphenol C-NDAAFR's 45 MIN bend clearance from the diecast. For SFP it is
estimated: Amphenol C-NJDDGN's 30 is measured from the diecast edge and would leave a 2 mm stub
past the 27.9 boot. No QSFP-DD drawing shows a strain relief, so both QSFP-DD generics carry
the QSFP boot figures with confidence `estimated` (the source names the QSFP part); the FS
QSFP-DD bend figures show the resulting 45 is conservative.

## 4. The new mechanism: a radius from a field

- **Skin:** the stub's end-on circle carries `data-r-from="cable-od"`. The circle's drawn `r` is
  half the generic's default, so the skin stays a valid standalone drawing.
- **Build:** `render.py`'s field pass (beside `data-fill-from`) sets `r` to half the value when
  the instance's merged attrs carry a numeric `cable-od`. Empty or absent leaves the drawn
  default, which is the same rule colour follows.
- **Kit:** `kit/fields.js` applies the same binding at runtime, so the 2D stub resizes when a
  placement's field changes. 3D builds its cylinder from the node's box when it loads.
- **Relief:** the stub is a `cyl` feature. It stands off the strain relief's end (`lift`) for
  the stub length (`cyl`), and its radius comes from the node's box, which the binding has
  already sized.
- **Lint:** a `cable-od` value, on a field's default or in a component's `parts` attrs (a
  wrapper), is a number from 2 to 15 (L122), written as plain ASCII digits and a point: the
  one pattern the build, the kit and L122 all ask, so lint passes nothing the drawing would
  leave undrawn. A device placement cannot set it yet: a configuration's occupants carry refs,
  not attrs, so the rule is component-scoped until occupants take attrs. A
  `data-r-from` names a declared field, which the existing field-wiring rule L73 is extended to
  check.

## 5. The vendor wrappers

Each wrapper follows the umbrella idiom: `kind: module`, it composes its generic with `attrs`,
restates the mate point, and carries the product's facts. Every value is sourced from that
product's own document or labelled otherwise. If a document gives no jacket colour, the
wrapper leaves the default and says so.

| wrapper | wraps | kind | values from its own document |
|---|---|---|---|
| Molex 74752 SFP+ passive | `sfp-cable` | dac | de-latch pull BLACK; 10G; OD not stated (default kept, said) |
| Amphenol NDAAFR QSFP28 passive | `qsfp-cable` | dac | 32AWG; lanyard Pantone 347C green; 100G |
| Amphenol NJAAF3 QSFP56 linear active | `qsfp-cable` | acc | 30AWG, PVC black; lanyard Pantone 2718 blue; 200G |
| FS 100G QSFP28 AOC | `qsfp-cable` | aoc | the generic's head; FS's smaller head, slim boot and ringless tab recorded in provenance; OD and jacket from the data sheet where stated |
| Volex 400G QSFP-DD passive | `qsfp-dd-cable-type2` | dac | 30AWG OD 9.0 (26AWG 11.6 noted); 400G |
| Credo HiWire SHIFT (QSFP-DD end) | `qsfp-dd-cable-type2` | aec | purple PVC jacket; 4P 30AWG 5.3 typical; "QSFP-DD type 2" |
| Siemon QSFP28 100G AOC | `qsfp-cable` | aoc | OD 3.0 +/-0.15; 1.78 W per end; 850 nm; aqua jacket read off its photograph (photo-measured) |

The FS AOC's data sheet states no cable diameter, so it keeps the 6.9 default; the Siemon
wrapper is the thin AOC, added at review for that reason. The FS drawing shows a smaller head
than the generic and a paddle tab with no ring; its provenance records the difference.

New vendor namespaces (molex, amphenol, volex, credo, siemon) join `spec/schemas/vendors.yaml` the way
existing vendors do.

## 6. A correction carried from the heads work

`common/qsfp-pull-tab@2` labels its photograph readings `measured`. The confidence vocabulary
reserves `measured` for readings off the part's own hardware and has `photo-measured` for a
photograph. This work relabels them (a patch bump). The heads PR is not touched while it is in
the merge queue.

## 7. What does not change

- Devices ship bare. A cable end is in a cage's accept list because it mates the cage's
  interface; nothing seats it by default.
- No 3D cable run, no cable routing and no bend geometry. The stub is straight and stops at
  the `cable` point.
- OSFP is out of scope, as it was for the optics.

## 8. Testing and gates

1. L121 holds each generic's head to its form's envelope. The Type 1 part's `registry`-confidence length is
   accepted, and a Type 2 head on the Type 1 generic fails.
2. The binding: at build time a wrapper's `cable-od` sizes the stub, empty leaves the default,
   and a non-number is a lint error. The kit's runtime binding matches the build (the
   stroke-derive pattern: Python and JS give the same numbers).
3. Seating: each generic seats in a cage of its family, and the accept lists offer all four.
4. 3D: the head, strap, strain relief and stub build as solids, with no inside-out boxes.
   The stub's cylinder diameter equals `cable-od`.
5. L99: `cable-kind` on a generic is an error; on a wrapper it is fine.
6. Census tests: the new parts join every count and exemption table. Nothing is waived.
7. A review page before the final rebuild shows each generic and wrapper beside its drawing,
   in 2D and 3D, with DAC, ACC, AEC and AOC side by side in one device. Sign-off, then gates.
8. Gates: lock, lint (no change against the baseline except new passes), build, publish,
   catalogue, the full suite, kit tests, and CI time against main's last green run.

## Decisions taken

- 2026-09-25: draw a short stub whose diameter and colour are fields (section 2, decision 2-4).
- 2026-09-25: a second generic for the QSFP-DD Type 2 head.
- 2026-09-25: ship the generics plus the sourced vendor wrappers in section 5.
- 2026-09-25: ship the Type 1 QSFP-DD generic at the MSA maximum, labelled as such.
- 2026-09-25: draw the pull strap in each generic rather than as a shared part (decision 7).
- 2026-09-25: one stub rule, 30 past the boot's end, for every form (section 3).
- 2026-09-25: L121 exempts features that start at or behind the head's back (strap, ring);
  a `cable` point may sit on a `cyl` feature and leaves from its far end.
- 2026-09-26: add the Siemon QSFP28 AOC wrapper so a thin AOC cable is shown (section 5).
- 2026-09-26: the wrappers state their rung as `rate`, not `media`, so the build's rate
  ceiling applies: a 10G DAC is no longer offered in a 1G SFP cage, nor a 200G cable in a
  100G QSFP28 cage. L102 refuses a rung written as `media`, and L12 refuses a configuration
  that seats a part above its cage's rung.
