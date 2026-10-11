# Rack mounting: ear positions and rail kits

Status: decided 2026-10-08, with the five follow-up decisions in section 11.
Tracked in #904. Follows #865, which added `chassis.ears: behind` and
`chassis.overhang`.

| piece | state |
|---|---|
| `kind: kit` in the component schema, `kits.json`, lint L155 to L159 (#905) | built |
| `chassis.ears` as an object, `chassis.kits`, lint L160 to L163 (#906) | built |
| ears and kits in `configs.json` and the DCIM exports (#907) | built |
| the generic L-bracket ear, drawn only when asked for (#909) | built |
| the default position in `rack.json` (#908) | not built |
| the move off `common/rack-ear@1` (#910) | open: 36 devices still place it |
| the worked examples (#912 to #915) | not built |

**No kit is in the library yet,** and no device lists one. Every kit and every
kit ref in this note is an example. The examples use the made-up namespace
`acme`, as [format-stability.md](format-stability.md) does. Four devices state
`chassis.ears`.

The Rack Builder of the site is the first reader. When this was drawn up it
placed every device with its faceplate 30 mm behind the rails, and most gear
mounts flush.

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

An example. Every key under `ears` is optional, and an object states at least
one:

```yaml
chassis:
  ears:
    behind: true            # the #865 statement, now a key (the bare string stays valid)
    h: 43.5                 # mm the ears span, when it is not the chassis height
    y: 0.15                 # mm, bottom of the ears above the bottom of the chassis
    color: "#1b1e21"        # the colour of the ears, when they are not silver
    positions:
      - {name: flush, at: 0, default: true}
      - {name: recessed, at: -25.4}
      - {name: mid, at: 228, racks: [2-post], part: {kit: acme/rack-kit@1, part: mid}}
  kits:
    - {ref: acme/rack-kit@1, supply: in-box}     # an example ref: no such kit exists
```

(The example shows every key at once. A real device that says `behind: true`
gets no generic ear, so it would have no use for `h`, `y` or `color`.)

- **`name` is required, `at` is not.** Manuals name positions; a figure that is
  not stated is not written. `name` is one of `flush`, `recessed`, `mid`,
  `rear` or `proud`, and `label` carries the words the vendor uses
  ("transponder flush"). The site may fall back on the name when `at` is
  absent. Two positions with one name are told apart by their labels; L165
  warns when two share both.
- **`default`** is the position as shipped. At most one position says it
  (L160).
- **`racks`**: any of `4-post`, `2-post` and `2-post-centre`, when the source
  restricts the position. Absent, any rack.
- **`part`**: the kit part a position needs when it is not the ears that ship
  (the Smartoptics mid-mount part). It is written `{kit, part}`: `kit` is the
  ref of a kit the device lists under `chassis.kits`, written as
  `chassis.kits[].ref` writes it, and `part` is the `id` of a part of that
  kit. L162 refuses a pair that does not resolve.
- **`h` and `y`** say what the ears span when they are not the chassis height
  (a 13U box with 10U ears). The device still occupies its `ru`. With no `h`
  the ears run from `y` to the top of the chassis, and with no `y` they start
  at its bottom. L164 warns when `y + h` is above the chassis.
- **`color`** is the colour of the ears, a fill written as `chassis.color` is.
  Absent, the generic ear is silver (`#c8cacc`): most network gear has bare or
  plated steel ears even when its faceplate is black.
- **`behind`** keeps the meaning #865 gave it. A device file may still say
  `ears: behind` as a bare string, so `fs/uscmh-sfdabsb2u` does not move, and
  L43 stands down for `{behind: true}` as it does for the string.
- `ears` and `kits` are for a `rack` device only (L125).

The [rack products note](rack-products-design.md) (section 7.1) proposes one
more key, `ears.holes`, for a part that clips into rail holes. It is not in
the schema.

### The generic ear

The faceplate drawing does not include the ears (Stage 1 of
[modelling-a-device.md](modelling-a-device.md)), and the default build draws
none. A generic L-bracket ear is drawn **only when asked for** (#909):

- `render.py --with ears` draws it on a face in 2D;
- the 3D viewer of the kit builds it when a host asks
  (`createViewer(el, {ears: true})`, `viewer.setEars(true)`);
- a page draws it over a published face with `ears2d.js` of the kit. The
  Explorer has a "Rack ears" toggle, off by default.

So no published face, export or device lock holds a generic ear.

The ear is a flange each side, from the body out to the 482.6 mm rack face,
with a slot over each rail hole and a leg back along the body. It is `ears.h`
tall and `ears.y` up, or the chassis height from the bottom when they are
absent. The back of its flange is on the plane the `at` of the default
position names, or flush when there is none. The sheet thickness (2 mm) and
the leg (30 mm) are estimates, the same in 2D and 3D.

A device gets no generic ear when:

- it is not a `rack` device (a `rack-face` part is its ears), or it is a
  sheet body (`chassis.shell`);
- it says `ears: behind` in either spelling;
- its front is 480 mm wide or more, so its ears are already in the drawing;
- it still places `common/rack-ear@1`, or anything under `optional: ears`.
  This last check is 2D only. Those ears are never in a published face, so
  the 3D scene cannot see them and gives such a device the generic pair.

[format-stability.md](format-stability.md) records the shapes and ids.

## 4. Rail kits are library objects

A kit is its own item with its own SKU, documents and devices, so it is
modelled once, namespaced by vendor, and referenced. It is a third `kind` of
component contract beside `component` and `module`, so it takes the component
versioning, namespaces and devicelock as they are. Its parts are ordinary
components (rails, brackets, ears), so a part can carry placements (the
Smartoptics earth stud) and the site can draw it.

A kit is named from `chassis.kits` and from nowhere else. It is never placed
in a view, seated in a bay or composed into a part (L5, L10).

```
library/components/<vendor>/<kit>/v1/contract.yaml
```

An example of the shape. The kit, its parts and its sources are made up; the
ranges are the kind a sliding rail prints.

```yaml
format: 1
kind: kit
name: slide
version: 1.0.0
description: Example sliding rails
motion: sliding                  # fixed | telescoping | sliding | shelf
travel: full                     # mm, or `full` when the source says only that
install: drop-in                 # drop-in | stab-in | both
parts:
  - {ref: acme/slide-inner@1, id: inner, count: 2}
  - {ref: acme/slide-outer@1, id: outer, count: 2}
configurations:
  - id: four-post
    racks: [4-post]
    parts: [inner, outer]
    depth:                       # front flange to rear flange, mm
      square: [631, 868]
      round: [617, 861]
      threaded: [631, 883]
    rail-depth: 714              # from the front face of the front flange, no accessory
accessories:
  - {kind: cma, ref: acme/cma@1, rail-depth: 845, sides: [left, right]}
  - {kind: srb, ref: acme/srb@1}
provenance:
  depth: the rail sizing matrix, v4.7 (2023), Table 2; the technical guide
    (2019) gives 676-868 in its Table 19 and lost
```

- **A kit has no `class`, no `size` and no skin.** It is a set of parts, and
  the parts carry all three. It admits only `format`, `kind`, `name`,
  `version`, `description`, `provenance`, `unplaced`, `superseded-by` and the
  kit keys below. There is no `title`; the words go in `description`.
- **Required**: `format`, `kind`, `name`, `version`, `motion`, `parts` and
  `configurations`. `travel`, `install` and `accessories` are optional.
- **`motion`**: `fixed` (static rails, ears, a rear support); `telescoping`
  (depth set at install, nothing moves after: Smartoptics, the two-piece
  Edgecore kits); `sliding` (moves out for service); `shelf` (the device
  stands on it). `travel` is allowed only with `sliding` (L158).
- **`parts`**: at least one, each `{ref, id, count}` and nothing else, so no
  `at`. All three are required, and `count` is an integer of at least 1. Each
  `ref` is an ordinary component, never another kit, and no two parts share an
  `id` (L155).
- **`configurations`**: at least one. Each needs `id`, `racks`, `parts` and
  `depth`, and may add `preset`, `tolerance` and `rail-depth`. The ids are
  distinct, and `parts` names only ids from the `parts` of the kit (L156). A
  slide kit has one configuration; Smartoptics has seven, one per depth band,
  and the AMX3200 two. `depth` is the rack depth, front flange to rear flange:
  one `[min, max]`, or one range for each of `square`, `round` and `threaded`
  that the source gives. Every range has min below max (L157). `preset`
  records a factory setting in mm of rack depth (the 630 of the COR550),
  `tolerance` the `x` of a stated `±x`, and `rail-depth` the depth of the rail
  itself, from the front face of the front flange, with no accessory fitted.
- **`accessories`**: `{kind, ref}` with `kind` one of `cma` (cable management
  arm) and `srb` (strain-relief bar). Each may add the `rail-depth` with that
  accessory fitted and the `sides` it fits. Each `ref` resolves to a component
  that is not a kit (L159).
- **`unplaced` and `superseded-by`** work as on any contract. A kit no device
  lists says why in `unplaced` (L89); a kit a device lists is reached, and so
  are its parts and accessories. The successor of a kit is a kit (L101).
- Inches are converted to millimetres, and the figures of the source stay in
  provenance.
- What a kit says about rack brands (Dell Titan racks, the third-party
  compatibility table of the matrix) stays in provenance. It is a statement
  about racks, and the library models none.
- Kits are published in their own `kits.json`, beside `components.json` and not
  in it. The component catalogue lists them in a table of their own, "Rail
  kits", once the library has one.

## 5. The device names its kits

An example, with the made-up kit of section 4 and a second one:

```yaml
chassis:
  kits:
    - {ref: acme/brackets@1, supply: in-box}
    - {ref: acme/slide@1, supply: optional,
       depth: {config: four-post,
               range: {square: [685, 868], round: [685, 861], threaded: [685, 883]}}}
```

- **`ref`** resolves to a `kind: kit`, and a kit is listed once (L161). `ref`
  and `supply` are required.
- **`supply`**: `in-box` or `optional`. A box can ship brackets in the box and
  sell a slide (DCS240), or ship a slide and sell a reversed one (AIS800-64D).
  The site defaults to the in-box kit, then to the first listed.
- **`variant: reversed`** marks a kit for reverse mounting (ports to the hot
  aisle).
- **`depth` overrides one configuration of the kit for this device.** `config`
  names a configuration `id` of that kit, and `range` replaces the `depth` of
  that configuration whole. So `range` has the shape that `depth` has: one
  `[min, max]`, or a range for each hole type the configuration gives. The
  Dell matrix gives B6 a 685 mm minimum on one chassis group and 631 on
  another. L163 refuses a `config` the kit does not have, a `range` of another
  shape, and a range whose min is not below its max.
- `chassis.full-depth` stays stated. A later lint can check it against the
  kits.

## 6. What stays in provenance

Screw sizes and torque, tool-less or tooled per hole type, install order,
service warnings (do not service with the rail extended), load ratings, and
which racks a vendor has tested. These are true and worth keeping, and nothing
draws or exports them.

## 7. Exports, lock and lint

[format-stability.md](format-stability.md) records each shape below, key by
key.

- `<device>.configs.json` carries `chassis.ears` and `chassis.kits`, each
  absent where the device does not state it (#907).
  - `ears` is always an object: a device file that says `ears: behind`
    publishes `{behind: true}`. An object publishes the keys it states
    (`behind`, `h`, `y`, `color`, `positions`) and no others.
  - `kits` has one row for each listed kit, in the order listed, with the kit
    resolved inline. A row is the entry of the device (`ref`, `supply`,
    `variant`, `depth`) and then `version`, `description`, `motion`, `travel`,
    `install`, `configurations`, `parts` and `accessories`. Each part and each
    accessory carries the `version`, `class`, `size` and `body` of its
    contract, so the site reads one file. Provenance is not in the row.
  - A `depth` override is applied: `configurations` in the row are what this
    device can do. The figures of the kit itself are in `kits.json`.
- `kits.json` publishes every kit as its contract states it, with its
  provenance, beside `components.json` (#905). Its parts are refs, not
  geometry. With no kit in the library the file is `{"kits": []}`.
- `rack.json` does not carry ears or kits. #908 is to add the default
  position and the motion and depth range of the default kit, so the Rack
  Builder can place a device without fetching its `configs.json`.
- The DCIM exports say both in `comments`, one paragraph for the ears and one
  sentence for the kits, as `overhang` does: neither NetBox nor Nautobot has a
  field. A kit as an inventory item or a module is left for later; the trial
  of optics as modules is the precedent.
- devicelock files `ears` and `kits` as chassis surface, so stating either on
  a device is a patch: the faceplate drawing does not move. That holds for
  `h`, `y` and `color` too, because the generic ear is never in a published
  face. A kit takes its own version by the component rules. A listed kit, its
  parts and its accessories are hashed with what the device composes, so a
  kit edited in place asks each device that lists it for a patch (#906).
- Lint (each rule is in [lint-rules.md](lint-rules.md)):
  - L125: `ears` and `kits` only on a `rack` device.
  - L43: stands down for `behind` in either spelling.
  - L160: at most one `default` position. The schema holds the words of
    `name` and `racks`.
  - L161: a kit `ref` on a device resolves to a `kind: kit`, listed once.
  - L162: a position `{kit, part}` names a listed kit and a part id of it.
  - L163: a `depth` override names a configuration of the kit, in the shape
    of that configuration, with min below max.
  - L164 (warning): `y + h` is not above the chassis.
  - L165 (warning): no two positions share a `name` and a `label`.
  - L155 to L159, in a kit: part refs resolve to components that are not
    kits, with distinct ids; configuration ids are distinct and list only
    part ids of the kit; every range has min below max; `travel` only with
    `motion: sliding`; accessory refs resolve to components that are not
    kits.
  - L5 and L10: a kit is never placed, seated in a bay or composed.
  - L101: the successor of a kit is a kit.
  - L89: a kit a device lists is reached, and so are its parts and
    accessories. A kit nothing lists says why in `unplaced`.

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
`h`, `y` and `color` of the ears, and for each kit its motion, travel,
configurations, depth ranges, rail depth with and without each accessory, and
the geometry of its parts. With that the Rack Builder can default the setback
to the shipped position, offer only the positions a device has, slide a
`sliding` kit out by its travel, warn when a rack is outside the range of a
kit or a device plus its CMA is deeper than the rack, and draw the rails.

`rack.json` will carry the default position and the default kit once #908 is
built, enough to place a device in a rack from one file.

The setback of an item in a rack is the mm its faceplate stands behind the
rail plane, so the setback of a position is `-at`. The
[rack products note](rack-products-design.md) (section 8) settles the order in
which a setback is found, and what a device with no `ears` gets.
[adjustable-positions-design.md](adjustable-positions-design.md) (section 8.4)
says how an adjustment inside a device adds to it.

## 10. Worked examples

These are the first four to model, one per kit shape. None is modelled yet.

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
   has drawable ears in the Rack Builder and in 3D. Section 3 lists the
   devices that get none.
3. **Fit belongs to the site.** Whether a device and its kit fit a given rack
   (range, rail depth plus accessories, door clearance) is computed in the Rack
   Builder, from the data here. The library computes nothing about racks.

Settled when the work was split into issues:

4. **The renderer draws the generic ears** from `chassis.ears`, and only when
   asked for, so no published face moves (#909). The 36 devices that place
   `common/rack-ear@1` move over when each next takes a major, not in one
   sweep that would cost 36 majors at once (#910). When the last reference is
   gone the part is kept and marked retired, not deleted. How it is marked is
   for #910: `superseded-by` names a component, and the generic ear is not
   one.
5. **`configs.json` always publishes `ears` as an object.** A device file may
   still say `ears: behind`; a consumer reads one shape.
6. **Kits are published in their own `kits.json`**, not in `components.json`.
   A kit is not a part a device places, and the component catalogue would
   count it as one.
7. **A device-level `depth` override names a kit configuration id**, since a
   kit with seven depth bands has no single range to override.
8. **The `part` of a position is written `{kit, part}`**, so a part id that two
   listed kits share is not ambiguous.
