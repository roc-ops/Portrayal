# Rack mounting: ear positions and rail kits

Status: agreed 2026-10-08, with the five follow-up decisions in section 11.
Tracked in #904. The device keys (`chassis.ears` as an object, `chassis.kits`)
and `kind: kit` are in the schemas and lint (#905, #906). The exports (#907),
the default setback in `rack.json` (#908), the generic ear (#909), the move off
`common/rack-ear@1` (#910) and the worked examples (#912 to #915) follow.
Follows #865, which added `chassis.ears: behind` and `chassis.overhang`.

The site's Rack Builder is the first reader. It places every device with its
faceplate 30 mm behind the rails, and most gear mounts flush.

Scope: how a rack device attaches to a rack. That is where its ears put the
faceplate, which rail kits it takes and what those kits allow, recorded at
intake so the Rack Builder, the 3D viewer and the DCIM exports can use it. The
work on the site itself (a setback control, sliding a server out, depth and
door checks) belongs to the site, and section 9 lists what it can read.

## 1. What the sources say

The product lines of four vendors were read before this was drawn up. Each one
broke a simpler model.

| line | what it ships | what it showed |
|---|---|---|
| Dell PowerEdge R740 / R740xd | three rails: B6 ReadyRails sliding (drop-in), B13 stab-in/drop-in sliding, B4 ReadyRails static; optional CMA and strain-relief bar | ranges differ by hole type (square / round / threaded); rail depth differs with and without the CMA; only the static rail does 2-post, flush or centre; one rail serves a dozen chassis, and the same rail has a different minimum on another chassis group |
| UfiSpace deep boxes (S9710-76D, S9321-64E, S9600-30DX, S9601-102XC, S9311-64D, S9301-32D) | one three-member ball-bearing slide (inner on chassis pins, middle, outer clipping to the posts) | about twelve models share a 771 mm rail; ranges are printed in inches only (22-33 in); travel is "fully extended", with no figure |
| UfiSpace 1RU (S6301, S9110, S7801, S8901) | front ears plus an adjustable mounting rail screwed to the back of the switch, fitted only on a 4-post rack | a kit can be ears AND a rear support, the support optional by rack type |
| Edgecore (COR550, DCS520, DCS240, AMX3200, AIS800-64D, AGR560) | fixed bracket kits in the box, slide kits sold separately | COR550: chassis ear plus a separate post-to-post rail with a factory preset at 630 mm; DCS520 / DCS240: a long side bracket with a rear piece that telescopes over it; AMX3200: one kit, two depth ranges (555-670 and 760-875); AIS800-64D: normal and reversed slide kits under different SKUs |
| Smartoptics DCP (DCP-2, DCP-M, DCP-R, DCP-M-DE, DCP-SC-28P) | one seven-part kit: front brackets 600 and 700, extensions 270 and 470, rear brackets 42 and 142, a 225 mm mid-mount part | the parts combine into seven rack-depth bands from 600 to 1200 mm (the bands overlap as printed); 2-post mid-mount is a different part; the protective-earth stud is on the bracket; four named ear positions (chassis flush, transponder flush, recessed, mid-mount) with no millimetres |

Three things were true everywhere:

- **Kits are shared.** One UfiSpace rail, one Smartoptics kit, one Dell rail and
  one Edgecore slide (RKIT-100G-SLIDE, for the AMX3200 and the DCS240) each
  serve several devices.
- **Positions are named, rarely measured.** No source gave an ear setback in
  millimetres except the Dell chassis drawings, whose `Za` is the reach of the
  front ahead of the ear (R660: 22 mm bare, 35.84 with the bezel).
- **Sources disagree with themselves.** The R740/R740xd Technical Guide (July
  2019) gives B6 square holes as 631-868 in its prose and 676-868 in its Table
  19. The Dell Rail Sizing and Rack Compatibility Matrix (v4.7, December 2023)
  gives 631-868, and B13 as 559-931 where the guide says 603-915. The S6301 HIG
  gives its rail as 21-38 in in the text and 22-33 in in a table.

## 2. What existed before

- `chassis.ears: behind` (#865): the flanges fold back behind a body as wide as
  the rack, so a 482.6 face is the part and L43 stands down. It is a width
  statement and says nothing about depth.
- `chassis.overhang: {left, right}` (#865): parts reaching past the rack face.
- `chassis.full-depth`: the DCIM `is_full_depth` flag, stated by hand.
- `common/rack-ear@1`: a decorative 14 x 43.5 ear, placed outside the chassis
  under `optional: ears`, sized from EIA-310 proportions and not from any
  device. 36 devices place it, 188 placements in all.
- Provenance prose on a handful of devices names a rail kit. Nothing
  structured.

## 3. Ear positions on the device

The number is measured on the device, not in the rack, because the same device
goes into a 2-post frame, a 4-post rack and a cabinet, and the rack is for the
site to know.

`at` is the distance in millimetres from the front of the faceplate back to the
plane the ears bolt to, positive when the ears are behind the faceplate.

| position | `at` | the faceplate in the rack |
|---|---|---|
| recessed, bracket reaching forward | -25.4 | 25.4 behind the rails |
| flush | 0 | flush with the rails |
| proud | 40 | 40 in front of the rails |
| mid-mount | 228 | 228 in front of a 2-post frame |
| rear ears | about `chassis.depth` | the site bolts it to the rear rails |

```yaml
chassis:
  ears:
    behind: true            # the #865 statement, now a key (the bare string stays valid)
    h: 43.5                 # ear height
    y: 0.15                 # bottom of the ear above the bottom of the chassis
    positions:
      - {name: flush, at: 0, default: true}
      - {name: recessed, at: -25.4}
      - {name: mid, at: 228, racks: [2-post], part: {kit: smartoptics/dcp-rack-kit@1, part: mid}}
  kits:
    - {ref: smartoptics/dcp-rack-kit@1, supply: in-box}
```

- **`name` is required, `at` is not.** Manuals name positions; a figure that is
  not stated is not written. `name` is one of `flush`, `recessed`, `mid`,
  `rear` or `proud`, and `label` carries the words the vendor uses
  ("transponder flush"). The site may fall back on the name when `at` is
  absent.
- **`default`** is the position as shipped. At most one position says it.
- **`racks`**: any of `4-post`, `2-post` and `2-post-centre`, when the source
  restricts the position.
- **`part`**: the kit part a position needs when it is not the ears that ship
  (the Smartoptics mid-mount part). It is written `{kit, part}`: `kit` is the
  ref of a kit the device lists under `chassis.kits`, and `part` is the `id` of
  one of that kit's parts. Lint refuses a pair that does not resolve.
- **`h` and `y`** say what the ears span when they are not the chassis height
  (a 13U box with 10U ears). The device still occupies its `ru`.
- **`behind`** keeps the meaning #865 gave it. A device file may still say
  `ears: behind` as a bare string, so `fs/uscmh-sfdabsb2u` does not move, and
  L43 stands down for `{behind: true}` as it does for the string.
- `ears` and `kits` are for a `rack` device only (L125).

The faceplate drawing does not include the ears (Stage 1 of
[modelling-a-device.md](modelling-a-device.md)). The renderer draws a generic
L-bracket ear beside it in 2D and builds it in 3D, sized from `ears.h` and
`ears.y`, or from the chassis height when they are absent (#909). It skips a
device whose face already includes its ears and a device that still places
`common/rack-ear@1`, so no device gets two pairs.

## 4. Rail kits are library objects

A kit is its own item with its own SKU, documents and devices, so it is
modelled once, namespaced by vendor, and referenced. It is a third `kind` of
component contract beside `component` and `module`, so it takes the component
versioning, namespaces and devicelock as they are. Its parts are ordinary
components (rails, brackets, ears), so a part can carry placements (the
Smartoptics earth stud) and the site can draw it.

```
library/components/<vendor>/<kit>/v1/contract.yaml
```

```yaml
format: 1
kind: kit
name: b6-readyrails-ii
version: 1.0.0
description: ReadyRails II sliding rails (B6)
motion: sliding                  # fixed | telescoping | sliding | shelf
travel: full                     # mm, or `full` when the source says only that
install: drop-in                 # drop-in | stab-in | both
parts:
  - {ref: dell/readyrails-ii-inner@1, id: inner, count: 2}
  - {ref: dell/readyrails-ii-outer@1, id: outer, count: 2}
configurations:
  - id: four-post
    racks: [4-post]
    parts: [inner, outer]
    depth:                       # front flange to rear flange, mm
      square: [631, 868]
      round: [617, 861]
      threaded: [631, 883]
    rail-depth: 714              # from the front face of the front flange, no CMA
accessories:
  - {kind: cma, ref: dell/cma-2u@1, rail-depth: 845, sides: [left, right]}
  - {kind: srb, ref: dell/srb-2u@1}
provenance:
  depth: Dell Rail Sizing and Rack Compatibility Matrix v4.7 (Dec 2023), Table 2;
    the R740/R740xd Technical Guide (July 2019) gives 676-868 in Table 19 and lost
```

- **A kit has no `class` and no `size`.** It is a set of parts, and the parts
  carry both. It admits only the kit keys below.
- **`motion`**: `fixed` (static rails, ears, a rear support); `telescoping`
  (depth set at install, nothing moves after: Smartoptics, the two-piece
  Edgecore kits); `sliding` (moves out for service); `shelf` (the device
  stands on it). `travel` is allowed only with `sliding`.
- **`parts`**: `{ref, id, count}`. Each `ref` is an ordinary component, never
  another kit.
- **`configurations`**: each has an `id` and names its parts (ids from the
  kit's own `parts`), its rack types and its depth range. A slide kit has one;
  Smartoptics has seven, one per depth band, and the AMX3200 two. `depth` is
  one `[min, max]` or one range per hole type, and every range has
  `min < max`. `preset` records a factory setting (the 630 of the COR550),
  `tolerance` a stated `±`, and `rail-depth` the depth of the rail itself.
- **`accessories`**: `{kind, ref}` with `kind` one of `cma` (cable management
  arm) and `srb` (strain-relief bar), plus the `rail-depth` with that
  accessory fitted and the `sides` it fits. Each `ref` resolves.
- Inches are converted to millimetres, and the figures of the source stay in
  provenance.
- What a kit says about rack brands (Dell Titan racks, the third-party
  compatibility table of the matrix) stays in provenance. It is a statement
  about racks, and the library models none.
- Kits are published in their own `kits.json`, beside `components.json` and not
  in it.

## 5. The device names its kits

```yaml
chassis:
  kits:
    - {ref: dell/b6-readyrails-ii@1, supply: optional}
    - {ref: dell/b13-stab-in-drop-in@1, supply: optional}
    - {ref: dell/b4-readyrails-static@1, supply: optional,
       depth: {config: four-post, range: [685, 868]}}
```

- **`ref`** resolves to a `kind: kit`.
- **`supply`**: `in-box` or `optional`. A box can ship brackets in the box and
  sell a slide (DCS240), or ship a slide and sell a reversed one (AIS800-64D).
  The site defaults to the in-box kit, then to the first listed.
- **`variant: reversed`** marks a kit for reverse mounting (ports to the hot
  aisle).
- **`depth` overrides one configuration of the kit for this device.** `config`
  names a configuration `id` of that kit, and `range` replaces its depth: the
  matrix gives B6 a 685 mm minimum on one chassis group and 631 on another.
  Lint refuses a `config` the kit does not have.
- `chassis.full-depth` stays stated. A later lint can check it against the
  kits.

## 6. What stays in provenance

Screw sizes and torque, tool-less or tooled per hole type, install order,
service warnings (do not service with the rail extended), load ratings, and
which racks a vendor has tested. These are true and worth keeping, and nothing
draws or exports them.

## 7. Exports, lock and lint

- `<device>.configs.json` always publishes `chassis.ears` as an object: a
  device file that says `ears: behind` publishes `{behind: true}`. It carries
  `chassis.kits` with each kit resolved inline (motion, travel, install,
  configurations, accessories and the geometry of its parts), so the site
  reads one file (#907).
- `kits.json` publishes every kit, beside `components.json` (#905).
- `rack.json` carries the default position and the motion and depth range of
  the default kit, so the Rack Builder places a device without fetching its
  `configs.json` (#908).
- The DCIM exports gain a comment line for each, as `overhang` does: neither
  NetBox nor Nautobot has a field. A kit as an inventory item or a module is
  left for later; the trial of optics as modules is the precedent.
- devicelock files `ears` and `kits` as chassis surface, so stating either on
  a device is a patch: the faceplate drawing does not move. A kit takes its
  own version by the component rules (#906).
- Lint, as built in #905 and #906 (the codes are in
  [lint-rules.md](lint-rules.md)):
  - `ears` and `kits` only on a `rack` device (L125).
  - At most one `default` position, and `racks` from the enum.
  - A position `{kit, part}` resolves into a kit the device lists.
  - A kit `ref` on a device resolves to a `kind: kit`, and a `depth.config`
    names a configuration of that kit.
  - In a kit: each part `ref` resolves to a component that is not a kit; a
    configuration lists only the ids of the kit parts; every range has
    `min < max`; `travel` only with `motion: sliding`; accessory refs resolve.
  - L89 counts a kit reached through `chassis.kits` as placed, and its parts
    as reached.

## 8. Intake and modelling

- **Vendor intake** stages, for each product line: the rail or mounting-kit
  installation guide, any rail sizing matrix, the accessory table (kit SKUs,
  in-box or optional, normal or reversed), and the rack-mounting figures of
  the hardware installation guide. A rail document is a document, so it is
  converted with the rest.
- **Modelling a device** gains a step after the panel: read the rack-mounting
  section, write `chassis.ears` (the named positions, `at` only when a figure
  or drawing gives it) and `chassis.kits`, and model a kit that is not yet in
  the library. A kit that already exists is referenced, not copied.
- **Review** checks the default position against the mounting figure of the
  installation guide, and the ranges of a kit against the newest of its
  sources, with provenance naming the source that lost.

## 9. What the site reads

From `configs.json`: the positions (name, `at`, `racks`, `default`), the
`h` and `y` of the ears, and for each kit its motion, travel,
configurations, depth ranges, rail depth with and without each accessory, and
the geometry of its parts. From `rack.json`: the default position and the
default kit, enough to place a device in a rack. With that the Rack Builder can
default the setback to the shipped position, offer only the positions a device
has, slide a `sliding` kit out by its travel, warn when a rack is outside the
range of a kit or a device plus its CMA is deeper than the rack, and draw the
rails. A device with no `ears` keeps the site default.

## 10. Worked examples

These are the first four to model, one per kit shape.

1. **Dell R740xd** with B6, B13 and B4 and the CMA and SRB (#912): hole-type
   ranges, accessories, a static kit with `2-post` and `2-post-centre`.
   Sources: the PowerEdge R740/R740xd Technical Guide (July 2019), chapter 9,
   and the Rail Sizing and Rack Compatibility Matrix v4.7. The two disagree on
   the B6 and B13 ranges; the matrix is newer, and provenance says the guide
   lost.
2. **Smartoptics DCP-2** with its seven-part kit (#913): seven configurations,
   a mid-mount position that needs a part, the earth stud on the bracket.
   Source: DCP-Series User Manual 14.0 A, section 3.2.
3. **UfiSpace S9710-76D** with its three-member slide (#914): inch ranges
   converted, `travel: full`, one kit referenced by its siblings. Source:
   S9710-76D HIG, Rack Mounting.
4. **Edgecore COR550** with ear plus rail (#915): a `telescoping` kit with a
   preset. Source: COR550 Quick Start Guide.

## 11. Decisions

Taken 2026-10-08, when the design was agreed:

1. **A kit is a component `kind`**, `kind: kit` beside `component` and
   `module`, under `library/components/<vendor>/`, not a new `library/kits/`
   tree. It reuses the versioning, namespace and devicelock rules unchanged.
2. **Generic ears replace the decorative stopgap.** `common/rack-ear@1` was a
   placeholder until ears were modelled. A generic L-bracket ear, sized from
   `ears.h` and `ears.y` (the chassis height when those are absent), is drawn
   wherever a device does not name its own ears or kit, so every rack device
   has drawable ears in the Rack Builder and in 3D.
3. **Fit belongs to the site.** Whether a device and its kit fit a given rack
   (range, rail depth plus accessories, door clearance) is computed in the Rack
   Builder, from the data here. The library computes nothing about racks.

Settled when the work was split into issues:

4. **The renderer draws the generic ears** from `chassis.ears` (#909). The 36
   devices that place `common/rack-ear@1` move over when each next takes a
   major, not in one sweep that would cost 36 majors at once (#910). When the
   last reference is gone the part is marked `superseded-by` the generic ear,
   not deleted.
5. **`configs.json` always publishes `ears` as an object.** A device file may
   still say `ears: behind`; a consumer reads one shape.
6. **Kits are published in their own `kits.json`**, not in `components.json`.
   A kit is not a part a device places, and the component catalogue would
   count it as one.
7. **A device-level `depth` override names a kit configuration id**, since a
   kit with seven depth bands has no single range to override.
8. **A position's `part` is written `{kit, part}`**, so a part id that two
   listed kits share is not ambiguous.
