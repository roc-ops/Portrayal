# Portrayal Design Decisions (v0)

"Portrayal" is the name; the repository is `roc-ops/Portrayal`.

Mission: declarative, Git-versioned definitions of hardware devices paired with SVG
renderings in which every component is individually addressable — for monitoring
callouts, technical documentation, DCIM, and diagram-tool exports. Domain-neutral
core; networking is profile #1. See PRIOR-ART.md for the research this rests on.

## Architecture

Three layers:

1. **Skins** — plain SVG files (real mm units), one per component face. Artist
   territory. Only obligation: expose the contracted element IDs at the contracted
   geometry.
2. **Contracts + manifests** — YAML, validated by JSON Schema.
   - *Component contract*: dimensions, sub-element boxes/IDs, connection points,
     states, semantic attributes, skins list.
   - *Device manifest*: chassis, views, placements of component instances, bays,
     regions, label text.
   - *NOS overlay*: per-NOS naming (`terms`), logical interfaces (incl. breakout),
     and `entity-map` pattern rules joining that NOS's ENTITY-MIB / ietf-hardware /
     OpenConfig component names onto physical IDs or regions. NOS trees are never
     drawn — only joined. Unmapped NOS nodes are legal (linter warns on unmapped
     port/psu/fan classes only).
3. **Compiled SVG** — build artifact. Flat (components inline-expanded), stable
   hierarchical IDs, `data-*` semantics, `.state-*` stylesheet, full source
   definition embedded in `<metadata>`. `<use>` only for decoration.

## The ten resolved decisions (Aug 2026)

1. **IDs**: kebab-case segments `[a-z0-9-]` (no `--` inside a segment); hierarchy
   in `data-path="port-1/led-link"`; element `id` = path joined with `--`
   (`port-1--led-link`, CSS-safe). Physical IDs are position-based, NOS-neutral,
   and follow the silkscreen (zero-based device → `port-0`). `index-origin`
   declared per component group. Logical names live in overlays.
2. **Views**: free-form IDs, conventional names (`front`, `rear`, `top`,
   `interior`, `lid-open`); per-view mm frame, origin top-left, **y-down**;
   a component identity may appear in multiple views; only `front` required.
3. **Modularity**: kinds = component / module / device. Bays are ENTITY-MIB
   `container` class; canonical schema word `bay` + per-vendor display `term`
   ("Slot", "Bay", ...). Blanks are real modules (FRUs with part numbers). Bay
   states: populated / blanked / open. A *configuration* populates bays; one
   compiled SVG per configuration.
4. **State model**: contracts declare states per stateful element from a small
   core vocabulary (profiles extend); compiled SVG ships `.state-*` CSS rules;
   consumers toggle classes; skins expose CSS custom-property color hooks.
5. **Labels as data**: contracts define anchors; text comes from manifests and
   NOS overlays. One open project font; optional outline-to-paths build flag.
6. **Regions**: addressable areas (sensor context via Redfish PhysicalContext
   vocabulary, grouping, doc callouts); may declare member components; NOS
   entity-map rules may target regions (e.g. a per-NOS "port bank" container).
7. **Licensing**: Apache-2.0 for everything — tooling, schemas, manifests,
   contracts and skins — so a rendered SVG never raises the question of whether
   it is a derivative of the library data. (It was CC-BY-SA 4.0 with an outputs
   exception for content until unified before publication.) Contributions under
   the Developer Certificate of Origin; see `README.md`, Licence. No vendor
   logos in community skins — contracts reserve a `logo-zone` region. No datasheet copies/conversions
   in-repo: transcribed facts with per-field provenance (`datasheet §x` |
   `measured` | `photo-inferred` | `vendor-cad` | `estimated`) + datasheet
   registered by title/URL/SHA-256/archive link. Device dumps stored sanitized
   (serials, MACs, IPs, hostnames, communities stripped/hashed).
8. **Builds**: byte-deterministic (no timestamps; toolchain version in
   `<metadata>`); source-only repos, compiled SVGs as release artifacts/gallery;
   CI = schema validation + contract↔skin linter + pixel-diff regression.
9. **Versioning**: semver per component — art=patch, additive=minor,
   geometry/IDs=major. Manifests pin major only (`name@2`); majors coexist
   in-tree (`v1/`, `v2/`); linter hashes contract geometry to catch unbumped
   breaks; every file carries `format: 1`.

   **Devices take the same bump rules and not the coexistence.** A device is a
   root rather than a dependency — nothing pins `mx10016@1` — so majors do not
   need to live side by side; what a device needs is that the version tells the
   truth. `library/devices.lock.json` records a fingerprint per device, split so
   the check can say which bump a change requires rather than only that one
   happened: `shape` (chassis dimensions, view sizes, and the position, size and
   wiring of everything placed), `names` (ids, groups, configurations), `surface`
   (silkscreen, decor, description, attrs, provenance) and `gaps`. Surface alone
   is a patch; ids added with nothing moved or removed is a minor; anything else
   about shape or names is a major, because a moved slot invalidates a cached
   coordinate exactly as a renamed id invalidates a held reference.

   The workflow is: edit, bump `version:`, then `devicelock.py --update`. Lint
   (L53) fails the loop until the bump covers the change, and re-locking is what
   records that it was reviewed.

   **A shape change re-opens the device's `gaps`.** Gaps state what no rule can
   find — facts about documents, not about the file — so nothing can verify one
   is still true. But a change to the drawing can close a gap, open one, or leave
   one annotating a slot that no longer exists, and only a reader of the sources
   can say which. So when `shape` or `names` move and `gaps` do not, L53 asks for
   them to be re-read: a gap still standing is a fine outcome, as long as it is
   that on purpose rather than by omission. L54 catches the mechanical half — a
   gap whose `scope` names no group, view, configuration, id or attribute the
   device has.
10. **Repos**: `spec` (schema+tooling, Apache-2.0) and `library`
    (content). Photos/dumps via Git LFS. Layout:
    `components/{common,<vendor>}/`, `devices/<vendor>/<model>/`, `profiles/`.
    Vendor slugs reused from netbox devicetype-library. Refs =
    `namespace/name@major`. Toolchain takes a library search path; reserved
    `local/` namespace for private overlays.

## Walking-skeleton scope (current)

Guinea pig: Edgecore AS7726-32X (live as roc-spine1, ArcOS S8.5.1A).
Components: qsfp28-cage, sfp-plus-cage, rj45-port, psu-ac-650 (+ bay), fan-module
(+ bay). Views: front + rear. Overlay: ArcOS. Deliverable: compiled SVG with a
consumer page proving query-highlight ("all 100G ports"), state toggling, and a
sensor callout.
