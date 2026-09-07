# Field capture guide — bringing a physical device into the library

Goal: one intake session per device on a warehouse table yields everything needed
to build its Portrayal definition — calibrated photos (the primary source), a 3D shell,
per-FRU captures, and key verified dimensions.

## Kit (~$60–130 total, phone apps free)

- **Phone**: iPhone Pro / iPad Pro (LiDAR) preferred; any modern phone works for
  photogrammetry.
- **Apps** (all free tiers sufficient):
  - *Scaniverse* (free, LiDAR + splats) or *Polycam* (free tier) — quick shells.
  - *RealityScan* (Epic, free) or Apple *Reality Composer* Object Capture —
    higher-quality photogrammetry for FRUs and small parts.
- **Digital calipers** (~$25) — ground truth for the dimensions that matter.
- **Printed scale markers** — a sheet of ArUco markers / checkerboard + two
  adhesive paper rulers. Tape to the table and to the chassis edge. This is what
  turns photos into measurable, mm-calibrated sources.
- **Even lighting**: two cheap LED panels or a bright diffuse area (~$40).
  Avoid glare on faceplates — it destroys both photos and scans.
- Optional: motorized turntable (~$35) for FRU photogrammetry.

## Accuracy reality check

- Phone **LiDAR**: ±5–10mm — good for overall shell/proportions, *not* for port
  geometry.
- Phone **photogrammetry** (RealityScan/Object Capture, with scale reference):
  ~1mm on well-textured small objects — good for FRUs.
- **Square-on photos + scale markers + caliper spot checks**: sub-mm effective,
  and this is what actually drives the SVG pipeline (the compare-tool overlay
  workflow is already mm-calibrated).
- Dedicated structured-light scanners (Revopoint POP 3 ~$400+, exceeds the
  budget line) reach 0.1–0.3mm if scan-first ever becomes the bottleneck.

These are typical figures for a careful capture under the conditions above,
not guarantees. A capture is fit for geometry only once its caliper spot checks
have been taken and the error they show has been written down; the calipers
are the measurement, the photo is the map between them.

## Per-device intake checklist

1. **Identity**: photo of the label plate (model, PN — mask serials/MACs/asset
   tags per repo policy), plus the datasheet/QSG PDFs located and hashed.
2. **Six faces, square-on**: camera as far back as space allows and zoomed
   in, which flattens perspective but does not remove it; the sensor must be
   parallel to the face, because a tilted sensor keystones the face and no
   amount of zoom undoes that. Face centered, scale markers visible in frame,
   no cables attached. Front, rear, top, bottom, both sides.
3. **Detail shots**: each connector cluster and LED cluster close-up; silkscreen
   legible. These resolve the "what does that little triangle mean" questions.
4. **Caliper dims** (write on the intake sheet): chassis W×H×D, port-block
   pitch (measure across 10 ports, divide), one connector's face W×H, FRU W×H.
5. **FRUs**: pull each PSU/fan/module, wearing an ESD strap, and with the
   unit powered down and disconnected unless the vendor's guide says that
   module is hot-swappable. Square-on photo of its face with scale marker + a
   photogrammetry scan on the turntable (all sides). Photo of the empty bay
   too — bays are components.
6. **Chassis shell scan**: one LiDAR/photogrammetry pass around the whole unit
   (lid closed) for the 3D reference shell. Export glTF/OBJ/USDZ.
7. **If powerable**: an entity dump (`show components`-equivalent, SNMP
   entPhysicalTable walk) plus per-NOS interface naming. There is no sanitiser
   tool; strip serials, MACs, IPs, hostnames and communities by hand, to the
   rule in `library/README.md`, and read the result through before it goes
   under `dumps/` — the Edgecore dumps there show the expected shape, with
   those fields emptied.

## What each capture feeds

| Capture | Feeds |
|---|---|
| Square-on photos + markers | compare-tool overlay → contract/manifest geometry (primary) |
| Caliper dims | provenance `measured` — anchors the photo calibration |
| Detail shots | skin art, LED semantics, silkscreen text |
| FRU scans (glTF) | future extruded/replaceable 3D modules; reference for skins |
| Shell scan | 3D-tab reference geometry beyond the flat box |
| Entity dump | overlay entity-map, live-state demos |

File everything under `working/intake/<vendor>/<line>/` — the gitignored
staging tree the intake process uses — and record each file in that
directory's `SOURCES.md`. `working/images/<stem>/` is reserved for what
`spec/tools/intake/extract.py` writes. Photos and scans never enter the
repository, identity photos included: what crosses into `library/` is the
transcribed fact, carried in the device's provenance block as `measured` with
the maturity it earns, and the sanitised dump. There is nothing to redact for
publication because the originals are never published.
