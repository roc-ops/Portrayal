# Handoff — QSFP transceiver, and what's open around it

Written at the end of a long session, for whoever picks this up next (probably me,
after a context compaction). Everything here is committed and deployed.

Demo host: `http://10.22.32.248:9003` — `./deploy.sh rocnet@10.22.32.248` from the
repo root builds and ships it. Lint: `python3 ndv-spec/tools/ndv/lint.py --schemas
ndv-spec/schemas --library ndv-library` (clean across 89 files as of writing).

---

## The pull tab tip — done

Solved as the loft this doc proposed. Kept here because the two dead ends are
still worth not repeating.

**What was wrong:** the tab tip was square in plan; the photographs and
`skins/top.svg` both show it rounded. The drawing radius is **3.2**, not the 3.4
this doc previously guessed — and `top.svg` also carries a **2.4** radius on the
finger slot, which had likewise never reached the 3D.

**Two approaches that do not work:**

1. *Extrude the plan outline, then bend the vertices onto the profile.*
   `THREE.ExtrudeGeometry` puts no vertices along the cap face, so the bend can
   only approximate the wave while the rails follow it exactly. Creases.
2. *Wider bevel on the extrusion.* Rounds the section, not the plan.

**What was built:** `sweep(stations)` in `part.html`. Each station is one
rounded-rectangle section at one z; consecutive stations stitch into quads. The
plan corners come out of `outerHalf(z)` and `slotHalf(z)`, both read off
`top.svg`. Because every station carries a complete section, the top and bottom
faces have as many vertices as there are stations and follow the wave exactly.

Three things that were not obvious and cost a pass each:

- **The nose needs rolling in section too, not just plan.** The leading stations
  inset by `bev - sqrt(bev^2 - u^2)` — the profile a ball of that radius leaves.
  Without it the tip was rounded in plan and razor-edged in section.
- **One bevel for the whole tab.** The pad at 0.30 and the rails at 0.22 met at
  the same y with different radii, and the shading broke along the seam.
- **Caps need their own vertices.** Fanning a cap off the shared side ring lets
  `computeVertexNormals` average the cap normal into the side surface, smearing
  the hard end edge into a shaded band about a millimetre wide. That band read
  as a crease exactly where the pad met the rails, and survived the first two
  fixes because it was never a geometry problem.

Verified in a headless browser, not by reading the code: the plan silhouette was
sampled off the vertex buffer at seven stations and matches `top.svg` to 0.02,
the nose rolls 6.00 -> 7.653 half-width and 2.80 -> 3.40 thickness across the
0.30 roll, and the six drawing-vs-model rows on the page still read.

**Known discrepancy left:** `top.svg` closes the slot 1.8 before the body; the 3D
runs it open to the body. It reads the same only because the body sits directly
behind it. Closing it means a fourth piece, or one sweep whose section splits.

---

## Where the part stands

| | |
|---|---|
| envelope | **19.00 × 8.50 × 118.00** — matches the drawing's reference |
| 2D | five views, measured against drawing *and* photographs |
| body | stepped geometry: front section, mid body, three rear tongues |
| tab | one loft: rounded sections swept along the plan outline, 3.2 tip / 2.4 slot radii |
| badge | 100G, 9.9 × 5.1, follows the contour, reads correctly |

The 118 is a genuine cross-check, not an input: an 83.2 body and a 34.8 tab reach
were derived separately and their sum lands on the drawing's reference length.

### Files

- `ndv-library/components/common/qsfp-drawing/v1/` — the five 2D views (`top`,
  `side`, `bottom`, `front`, `back`) on a common 118 × 19 sheet, plus provenance
- `ndv-library/components/common/qsfp-transceiver/v1/` — the placeable part
- `ndv-library/demo/drawing.html` — 2D study page, 10mm grid, callout table
- `ndv-library/demo/part.html` — 3D study page, drawing-vs-model check table
- `working/intake/optic/` — photographs (gitignored)

### Source photographs

`IMG_2190` side elevation · `IMG_2193` plan with the label · rest are detail. The
part is a **ROCNET QSFP28-SR4-UFI-RS, 100G 850nm 100m MMF**, tab beige (the drawing
says WHITE — different reach).

### Figures still soft

Recorded in the component's provenance, so they aren't mistaken for measured:
heatsink rib pitch · the 52 mm body-step position · the rear widths (18.35 / 14.60 /
12.40). All read off photographs at scale. Also: **the 100G is a texture, not moulded
geometry.**

---

## Hard-won lessons from this part

Written down because each cost several rounds.

- **A drawing bounds a part; photographs tell you its shape.** Every dimension I took
  from the mechanical drawing was right first time. The *shapes* were all wrong —
  round bail vs flat loop, closed loop vs open U, single crest vs flattened M. No
  amount of re-reading the drawing would have caught any of it.
- **Texture is not geometry.** Steps painted onto a cuboid's side read as steps from
  exactly one angle. If a shape matters obliquely, model it.
- **Two views constrain a part; I repeatedly used one.** Built the tab's plan from
  `top.svg` and left it flat, having *just* corrected `side.svg` to get the profile
  right.
- **Verify the outcome, not the property.** "I set `opacity = 0.05`" proved nothing —
  the material needed `needsUpdate` for it to take effect. Same shape of error as
  checking `data-z-uhandle` while the geometry it applied to was still the old node.
- **Check the artifact, not the local file.** Several string replaces silently didn't
  match. `node --check` passes happily on a mangled sentence. Rewrite whole blocks
  rather than patching prose with regex.
- **Bevels grow the result.** Inset the section by the bevel or the envelope
  overshoots — caught twice by the dimension check.
- **Build in the object's own frame when orientation matters.** The badge was wrong
  three times as a rotated plane, guessing at Euler order. Built vertex by vertex it
  was right immediately, and turning it 180° became a UV flip.

---

## Wider backlog, unrelated to the QSFP

- **`relief.js`** — extraction is done and both viewers use it. `3d.html` 908 → 510
  lines. No outstanding work, but it's the seam to be careful around.
- **DCP-R family** — three devices built from Visio stencil connection points.
  `dcp-r-9d-cs`, `dcp-r-34d-cs`, `dcp-sc-28p`. Their `top`/`bottom`/`left`/`right`
  views carry finish only (silver body, black front panel); no vents, screws or lid
  labels, because nothing photographed shows them.
- **`rj45-port@4`** — two independent sources now disagree with its 14.9 mm height:
  the AS7726 photo reads 13.3, the Smartoptics stencil 12.7. Worth a caliper.
- **`usb-a@2`** — its own provenance records a 13.1 × 5.7 nominal shell while
  declaring a 17.0 × 7.0 footprint. A photo measurement agreed with the nominal.
- **AS5912-54X / AS7326-56X** — front faces only. `top`/`left`/`right` are finish
  without vents, screws or lid labels. Needs photographs of a lid and a flank.
- **Visio intake, unfinished** — DCP-M, DCP-F and the H-series stencils are sitting
  in `working/intake` (gitignored) and were never modelled. Scope call, not a task.

### Closed since this doc was first written — do not redo

- ~~**`build.sh` does not run lint.**~~ It does now, before rendering. A manifest
  that would not parse used to yield an empty or partial `dist` that still printed
  a success line and deployed. That is how `dist` got emptied without my noticing.
- ~~**YAML colon-in-plain-scalar.**~~ Lint rule **L0** now reports the offending
  line and, when it carries a second `": "`, names the cause. Note the trap I fell
  into writing it: my first condition skipped any line whose key was a valid
  identifier, which is *every* line this can happen on. It only surfaced because I
  tested by injecting the fault into a scratch copy of the library instead of
  reasoning about the predicate. Do that.
- ~~**AS7726-32X `mgmt-sfp-1`/`usb` overlap.**~~ False positive — L13 was not
  honouring `rotate`. The faceplate is fine. Lint is clean at 89 files.
