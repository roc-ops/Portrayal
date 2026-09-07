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

## Per-device intake checklist

1. **Identity**: photo of the label plate (model, PN — mask serials/MACs/asset
   tags per repo policy), plus the datasheet/QSG PDFs located and hashed.
2. **Six faces, square-on**: camera as far back as space allows, zoomed in
   (kills perspective distortion), face centered, scale markers visible in
   frame, no cables attached. Front, rear, top, bottom, both sides.
3. **Detail shots**: each connector cluster and LED cluster close-up; silkscreen
   legible. These resolve the "what does that little triangle mean" questions.
4. **Caliper dims** (write on the intake sheet): chassis W×H×D, port-block
   pitch (measure across 10 ports, divide), one connector's face W×H, FRU W×H.
5. **FRUs**: pull each PSU/fan/module. Square-on photo of its face with scale
   marker + a photogrammetry scan on the turntable (all sides). Photo of the
   empty bay too — bays are components.
6. **Chassis shell scan**: one LiDAR/photogrammetry pass around the whole unit
   (lid closed) for the 3D reference shell. Export glTF/OBJ/USDZ.
7. **If powerable**: sanitized entity dump (`show components`-equivalent, SNMP
   entPhysicalTable walk) via the repo sanitizer, plus per-NOS interface naming.

## What each capture feeds

| Capture | Feeds |
|---|---|
| Square-on photos + markers | compare-tool overlay → contract/manifest geometry (primary) |
| Caliper dims | provenance `measured` — anchors the photo calibration |
| Detail shots | skin art, LED semantics, silkscreen text |
| FRU scans (glTF) | future extruded/replaceable 3D modules; reference for skins |
| Shell scan | 3D-tab reference geometry beyond the flat box |
| Entity dump | overlay entity-map, live-state demos |

File everything under `devices/<vendor>/<model>/capture/` locally (photos and
scans stay out of the public repo unless contributor-licensed; dumps go in
sanitized).
