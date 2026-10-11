# Portrayal Design Decisions (format 1)

"Portrayal" is the name; the repository is `roc-ops/Portrayal`.

Mission: declarative, Git-versioned definitions of hardware devices paired with SVG
renderings in which every component is individually addressable — for monitoring
callouts, technical documentation, DCIM, and diagram-tool exports. Domain-neutral
core; networking is profile #1. See ../PRIOR-ART.md for the research this rests on.

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
   - *Listing*: a NOS vendor's entry for hardware on its compatibility list,
     under that vendor's namespace and pointing at one device. It carries the
     vendor's own names and part numbers, per-NOS naming (`terms`), logical
     interfaces (incl. breakout), and `entity-map` pattern rules joining that
     NOS's ENTITY-MIB / ietf-hardware / OpenConfig component names onto physical
     IDs or regions. NOS trees are never
     drawn — only joined. Unmapped NOS nodes are legal (linter warns on unmapped
     port/psu/fan classes only).
3. **Compiled SVG** — build artifact. Flat (components inline-expanded), stable
   hierarchical IDs, `data-*` semantics, `.state-*` stylesheet, and a digest of the
   full source definition in `<metadata>`; the source itself is published once
   per device beside the drawings. `<use>` only for decoration.

## The ten resolved decisions (Aug 2026)

1. **IDs**: kebab-case segments `[a-z0-9-]` (no `--` inside a segment); hierarchy
   in `data-path="port-1/led-link"`; element `id` = path joined with `--`
   (`port-1--led-link`, CSS-safe). Physical IDs are position-based, NOS-neutral,
   and follow the silkscreen (zero-based device → `port-0`). `index-origin`
   declared per component group. Logical names live in listings.
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
   NOS listings. Skins set their text in a system sans-serif (Arial or
   Helvetica, falling back to `sans-serif`). *Planned, not built:* one open
   project font, and a build flag that converts text to outlines.
6. **Regions**: addressable areas (sensor context via Redfish PhysicalContext
   vocabulary, grouping, doc callouts); may declare member components; NOS
   entity-map rules may target regions (e.g. a per-NOS "port bank" container).
7. **Licensing**: Apache-2.0 for everything — tooling, schemas, manifests,
   contracts and skins — so a rendered SVG never raises the question of whether
   it is a derivative of the library data. (It was CC-BY-SA 4.0 with an outputs
   exception for content until unified before publication.) Contributions under
   the Developer Certificate of Origin; see `README.md`, Licence. No vendor
   logos in community skins — contracts reserve a `logo-zone` region. No datasheet copies/conversions
   in-repo: transcribed facts with per-field provenance (`datasheet` | `drawing` |
   `measured` | `photo-measured` | `registry` | `borrowed` | `estimated` | `known-wrong`) + datasheet
   registered by title/URL/SHA-256/archive link. Device dumps stored sanitized
   (serials, MACs, IPs, hostnames, communities stripped/hashed).
8. **Builds**: byte-deterministic (no timestamps; toolchain version in
   `<metadata>`); source-only repos. CI = schema validation, the
   contract↔skin linter and the test suite, including a check that the
   committed DCIM exports match a fresh build. *Planned, not built:* compiled
   SVGs published as release artifacts (#64), and a pixel-diff regression step
   in CI.
   **A configuration says what OCCUPIES a bay AND what is TRUE of a part, and
   still not what is true of the DEVICE.** That sentence is the decision #193
   asked for, and the shape it names came from two vendors at once
   (docs/what-a-configuration-cannot-say.md): a Casa C40G whose AC build bolts
   one inlet panel across the band its DC build fills with two PEMs, and a Cisco
   ASR 9001-S which is the same metal as the 9001 with two of four SFP+ ports
   disabled until a licence is applied.

   The design note costed two schema changes for it. Neither was needed.
   **Presence** was already sayable: `only-in:` scopes a placement or a bay to
   named configurations, which is where the C40G's panel and its two PEM
   openings live now - an AC chassis has the panel and no PEM openings, a DC one
   the openings and no panel, and because they are never both present there is no
   overlap for L13 to reject. Geometry belongs in the view, and which
   configurations a piece of metal exists in is geometry. **Property** needed one
   lookup: `component-attrs` was keyed by component name, which says a true thing
   about every copy of a part and nothing about one of them, and now takes a
   placement id too; `bay-attrs` already took a bay path and had never been used.

   What is still not sayable is a device attr that changes with the
   configuration - the 9001-S's 60 Gbps against the 9001's 120. That is the
   remaining third, filed on the device rather than solved here, because the
   fix is the same widening one level up and it has one instance.

9. **Versioning**: semver per component — art=patch, additive=minor,
   geometry/IDs=major. Manifests pin major only (`name@2`); majors coexist
   in-tree (`v1/`, `v2/`); linter hashes contract geometry to catch unbumped
   breaks; every file carries `format: 1`.

   **The `v<major>` level stays, decided 2026-09-16 (#172), and here is what it
   cost and what it buys.** Measured on the day: 587 version directories across
   582 names, 17 of them non-v1, and only four names holding more than one
   major. Three of those four were an old major behind a live one and nothing
   referenced them; they are deleted. The fourth, `common/usb-a@2` against `@3`,
   is not a version pair at all — one is a 17×7 receptacle, the other a 17×9.3
   bezel plate sized so it can abut its neighbours — which is a variant wearing
   a version number (#264). So on the evidence, coexistence had never once been
   used for the thing it exists for, and the argument to drop the level was a
   good one.

   It stays because of WHEN the question is being asked. Every reference to a
   component today is inside this repository, which is why "does anything use
   this" has an exact answer (L89) — and it is exactly that property that ends
   the day the library goes public. An outside manifest pinning `name@2` is the
   consumer coexistence is for, and there have been none to serve. Dropping the
   level would move 587 directories and change resolution in sixteen tools to
   retire a mechanism the week before it acquires its first users.

   **What pays for keeping it: a dead major goes, and says where it went.**
   While the package is at 0.x, a superseded major may be removed, and every
   removal is listed in `CHANGELOG.md` with the ref that replaces it, so a
   manifest outside this repository that pins the old major is told what to pin
   instead. From 1.0 a retired major is deprecated for at least one release
   before it is removed: that release is the coexistence above, spent on the
   consumers it exists for. The deprecation is the `superseded-by:` key the
   schema already has, on the retired major's contract, naming the ref that
   replaces it: one key for the fact, not a second marker beside it. L89
   telling a superseded major that still ships from a dead one is pending
   (roc-ops/Portrayal#448). The 0.x rule was chosen on 2026-10-10 over
   building the deprecation first. The whole mechanism is required before 1.0:
   the marker, a stated support window, and the L89 distinction. 1.0 is not cut
   without the three. Inside the repository, L89 still fails on a
   superseded major that nothing references — it will not accept
   an `unplaced:` sentence from a major that a newer live major supersedes.
   There is one exception, and it is the reason the check asks whether anything
   NAMES a major rather than only whether something seats it: a retired major
   can still be one side of an open question. `common/psu-550w@1` is retired and
   seated by nothing, and the PBC-2000's `psu-module-width` gap argues from its
   84.0 mm against the 73.5 mm of the `@2` that device places. Deleting it would
   have left that gap arguing from a figure no longer in the tree.

   **Devices take the same bump rules and not the coexistence.** A device is a
   root rather than a dependency — nothing pins `mx10016@1` — so majors do not
   need to live side by side; what a device needs is that the version tells the
   truth. Each device carries a `device.lock.json` beside its manifest recording a
   fingerprint, split so
   the check can say which bump a change requires rather than only that one
   happened: `shape` (chassis dimensions, view sizes, and the position, size and
   wiring of everything placed), `names` (ids, groups, configurations), `surface`
   (silkscreen, decor, description, attrs, provenance), `placement-attrs` (the
   `attrs` each placed port states for itself - `speed`, `media`, `usb` - hashed
   beside `surface` rather than inside it so that learning the field rehashed no
   device) and `gaps`. Surface alone, placement attrs included, is a patch; ids added with nothing moved or removed is a minor; anything else
   about shape or names is a major, because a moved slot invalidates a cached
   coordinate exactly as a renamed id invalidates a held reference. A sixth,
   `composed`, covers what the device draws and does not contain: every
   component it seats, followed through their `parts:`, the `default:` each
   part ships holding, their faces (`faces.rear`, `faces.plan` or the legacy
   `plan:` - a cassette's back is drawn under the device that seats the
   cassette, so redrawing it is redrawing that device) and the `default` and
   `accepts` of their own bays at any depth, each recorded as its version plus
   a digest of its contract and skins. A component redrawn in place
   therefore moves every device that shows it, and that alone is a patch.

   Every other key a placement can state, and every key a bay states, is
   fingerprinted the same way,
   under three keys of its own that each read only when the old lock has them:
   `placement-geometry` (`inset`, `lift`, `in`, `under`, `only-in`, `optional`,
   `interfaces` - where the part sits in depth, whether it is drawn at all, and
   which interfaces the export names in its place - and a bay's `opening`,
   `floor`, `plan` and `rear`: the hole that is punched, the shelf its occupant
   stands on, and where that occupant is projected on another face) is a major;
   `placement-addressing` (`for`, `rel-pos`, and a bay's `interface`) is a major
   when a value changes or goes, a minor when a `for` or an `interface` is
   stated where there was none - a slot opened to an interface admits more, as
   `accepts` growing does - and nothing when a `rel-pos` is; and
   `placement-surface` (`states`, `description`, `provenance`,
   `physical-context`, `frames`) is a patch. Together with the keys already
   hashed these sets cover the schema's placement and bay properties exactly,
   and a test holds that for each, so a new key on either has to be sorted when
   it is added.

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
10. **Layout**: one repository. `spec/` holds schemas, tooling and tests;
    `library/` holds `components/{std,common,<vendor>}/<name>/v<major>/` and
    `devices/<vendor>/<model>/`; `kit/` is the JS consumer of what `build.sh`
    publishes. Profiles live in `spec/schemas/profiles.yaml`. Photographs and
    vendor documents are never committed (no LFS; they stay in the gitignored
    `working/` staging tree and are cited, not copied); dumps are committed
    sanitised. Vendor slugs reused from netbox devicetype-library. Refs =
    `namespace/name@major`. Toolchain takes a library search path; reserved
    `local/` namespace for private listings and devices.

## Why some schema fields are shaped as they are

The descriptions in `spec/schemas/*.schema.json` say what a field is, what it
takes and what it does; they are published, and a reader of the schema page
cannot follow a reference into this repository. The reasons below are how some
of those fields came to be shaped as they are. They are kept here rather than
in the descriptions because they are history, not definition.

- **`maturity` is required.** Absent used to mean `draft`, and twelve finished
  devices were reading as drafts on that default: the Edgecore AS7726-32X, all
  five Smartoptics DCPs and the FS enclosure among them. A default that
  silently mislabels the work is worse than a field somebody has to fill in.
- **`profile` is required.** While it was optional, 67 of 89 devices had none,
  so `capability._specified` returned `cannot evaluate` for them while the
  flag read as a fact about the other 22.
- **The datasheet's `archive` field was removed (#274).** It was in the schema
  from the start, no entry used it, no tool read it and no document said what
  it was for: a field nobody knew the rule for. At the time `url` was absent on
  43 of 96 document entries, which is not a defect: documents read behind a
  login or received directly have none. Every one of the 37 hashes resolved to
  a held file - the rule `sha256` now states.
- **Provenance entries are objects.** L15 (`verified` means no dimension may be
  estimated) was implemented as `str(value).startswith("estimated")` against a
  corpus where 42 entries opened with the word and 80 more said it somewhere in
  a long paragraph. The prose moved into `note` and the word into `confidence`.
  744 of 1688 entries were migrated with no `confidence`, because reading 744
  paragraphs and deciding measured-or-estimated by eye is how an estimate
  becomes a measurement; L93 counts them so the number falls. A `source` key is
  still wanted, and waits on ids for the `datasheet` and `references` entries
  (#274).
- **A component's provenance keys are field names.** The library reached 579
  distinct keys across 584 contracts, 495 of them used fewer than five times
  and some of them whole sentences. L52 had to be loosened to accept any
  power-named key after convicting eighteen contracts that had done the work,
  and nothing could ask about `size` at all. Hence the core keys and the rule
  that a more specific key starts with one.
- **Airflow lives on the chassis.** It varies by build in 7 of the 48 devices
  that stated it when this was decided; in the rest, repeating it per
  configuration gave one fact two homes. The renderer had always read the
  configuration first and fallen back to the chassis, so the division matched
  what it already did.
- **Configurations say what kind they are.** The field carried four meanings at
  once, and a consumer could not tell an orderable SKU from an illustration: the
  C40G exported a DCIM device type called `C40G bdm-3plus1`, named after
  whichever redundancy drawing happened to be listed second. A `base` is the
  default because four devices opened on an illustration, which made `default`
  mean whatever the drawing happened to be populated with.
- **Group roles name the control plane.** `management` is its own bucket
  because on five devices the management block is written first in the
  manifest, so leaving it with the traffic ports still opened the tree with a
  console socket. Control-plane cards are named under `service` because the
  convention drifted both ways while they were unnamed: nine devices had routing
  engines in `service` and two in `management`, and the ASR 9912 and 9922 had
  their route processors in `traffic`, so the first base configuration built
  for a 9922 emptied both of them.
- **A device's lamp state has the component's shape.** When `rate` and
  `sequence` were added they went into the component schema only, and a device
  that stated a blink frequency on a placement was rejected by a rule nobody had
  thought about: two definitions of one concept, drifting. An omitted `rate`
  means once a second because that is what every state written before `rate`
  existed meant by `blinking`; an omitted `power-draw-scope` means `module` for
  the same reason, so no earlier figure changed meaning.
- **Component classes are not an enum in the schema.** The vocabulary lives in
  `spec/schemas/power-roles.yaml` alone, because the same list in two files
  drifts and only one would be the one lint reads. Synonyms were merged in
  #173: `cooling` became `fan`, `fastener` became `screw`, `panel` became
  `display` and `connector` became `inlet`, because each pair was one kind of
  part split by who happened to model it.
- **A component's `bays` are typed.** The key was `additionalProperties: true`
  and described as unused while 51 bays across 25 components relied on it, so a
  malformed bay validated and was found, if at all, by a tree that read wrong.
  `accepts` is required on them because the four SPA bays of
  `a9k-sip-700-8g` sat empty for want of one while its 4 GB twin listed 22
  cards in each.
- **`optical.front-order` is stated, not guessed, on a multi-row face.**
  Guessing a numbering rule from the one multi-row sample the library held is
  how the 12.90-versus-13.2 pitch confusion started.
- **A combine is declared, with `combine` on the path.** Two strands in one
  bore stay an error everywhere else, and a destination that is a list
  already means a split, so the opposite shape gets its own keyword. A path
  records the way the light travels; the fibre map is a binding and does not
  (#246).
- **`lift` on decor and on a placement** exists because `relief.features` had
  carried `lift` all along and composed `parts:` gained it; the others not
  having it was an asymmetry in the vocabulary rather than a decision, and it
  forced second copies of parts with fattened numbers.
- **The device `lint:` block** was written for the Casa C40G, which keeps a rear
  vent field that L44 reports as 100% buried: the PEMs or the AC panel cover it
  in 2D, and it is what punches the rear panel in 3D when a PEM is pulled. Its
  provenance said so at length, in prose no tool reads.
- **`chassis.edge` is hashed as surface.** Its schema entry carried no
  description, and for as long as that lasted it read as geometry (#271).

## First device (historical)

The scope the project started with, kept as the record of where it began; the
library has grown well past it.

Guinea pig: Edgecore AS7726-32X (a live lab unit, ArcOS S8.5.1A).
Components: qsfp28-cage, sfp-plus-cage, rj45-port, psu-ac-650 (+ bay), fan-module
(+ bay). Views: front + rear. Overlay: ArcOS. Deliverable: compiled SVG with a
consumer page proving query-highlight ("all 100G ports"), state toggling, and a
sensor callout.
