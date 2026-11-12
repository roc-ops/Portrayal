# Portrayal

## Goal
Grow the Portrayal toolkit from one rack to rooms, buildings and campuses, so network engineers can document what exists and plan what's next from the same files.

## About
Portrayal is a toolkit for describing network hardware as data and building on it. A device is a YAML manifest, compiled into SVG and JSON where every port, supply, fan, lamp and bay has a stable id. A rack file places devices and cables them. The direction is to help network engineers document what exists and plan what's next, from files kept in Git, at the scale of rooms, buildings and campuses.

The toolkit is the product. The Explorer, Rack Builder, Annotate and the export pages on portrayal.dev (repo `portrayal-site`) are examples of using it. A new capability belongs in the formats, the compiler or `@portrayal/kit`, where any page, script or agent can use it.

**What exists today**

- **Library and compiler** (`spec/`, `library/`): schemas, lint, lock files, more than 500 devices from 37 makers, and rack frames. Every figure records its source and confidence, and where a source is silent the manifest says so in `gaps:`. An overlay library adds an organisation's own devices without a fork.
- **Kit** (`kit/`, 0.51 in the repo): plain ES modules with no build step that read compiled files and never YAML. They draw a face in 2D and 3D, seat parts, mark and colour parts, and export draw.io, OmniGraffle, GLB and USDZ.
- **Racks** (`kit/rack/`): the rack file, every edit as a named command with undo, routing, fill and bend checks inside one rack, bundles, zero-U parts, and BOM and cable schedule rows. The same rules run in a browser, in node and in an agent. `mountRack2d` draws one face of one rack in any page.
- **DCIM export**: NetBox and Nautobot device and module types, and CSV import files for a rack's devices, modules and cables. It only goes out. Nothing reads racks, devices or cables back from a DCIM.

**In progress**

- **Site file, version 0** (#1297): a design note, schema and checker are proposed and not yet decided. They add site, building, floor and space, racks placed by reference to their rack files, walls and backboards, non-rack devices, a pathway graph, and cables between racks. The kit does not read it yet, so there is no floor plan, multi-rack editing or routing along pathways.
- **Rack exits** (#1299): designed, not built. A cable that leaves a rack has nowhere to end in the rack file.
- **Rack views** (#1298): the 2D elevation is in the kit. The 3D rack scene is still only in `portrayal-site`.
- **Rack products** (#935, #1104): open frames and generic shapes are in `library/racks/`. No maker's cabinet is yet.
- **Named types** (#897): cable types are published. Optic types are a proposal with nothing built, so a generic optic does not know SR from LR.
- **Power** (#1045, #934): cords, DC feeds and ground wires can land in a rack. Outlet states are not drawn yet, and nothing totals a rack's power.
- **More exports** (#1111, #11): Device42 and Infrahub writers exist and are unpublished. dcTrack and Nlyte do not exist. The kit writes Visio (`kit/visio.js`), and no page offers it yet.

**Limits an idea has to respect**

- **Drawing cost:** in one headless measurement a 275-cable rack took 39 s to draw and its 3D view did not settle in 15 minutes (portrayal-site #192). An idea for a room has to say what it does not draw.
- **One-way doors:** a new or changed published format is decided in a design note before code that depends on it merges (`docs/format-stability.md`). The format is still 0.x.

**Out of scope**

- Real-time telemetry, polling, monitoring and alerting. A host page can colour a drawing from its own data, and the toolkit stops there.
- Vendor material in any form. Facts are transcribed and cited, and the documents stay out of the repo.
- Serial numbers, MAC addresses, IP addresses, hostnames or SNMP communities in committed data.
- Becoming a hosted service or a live system of record. Portrayal stays files and a kit, and a DCIM stays the DCIM.

## Judging
Favour an idea that:

- adds to the formats, compiler or kit, so every page, script and agent gets it;
- helps document what exists or plan what's next at room, building or campus scale;
- builds on the stable ids, the rack file, the site file or the Git history;
- reports what it does not know: a missing figure is named as unknown, never counted as zero, dropped or guessed (`docs/failure-by-omission.md`);
- can ship a useful first piece, and says which step is a one-way format change.

Mark down an idea that:

- needs live data, polling or a monitoring system;
- is only a feature of one page, such as the Rack Builder;
- fits one vendor, one DCIM or one organisation's catalogue where a neutral seam would do;
- already exists, or repeats an open issue without adding anything;
- needs vendor drawings or documents redistributed.

## How to submit
Open a blank issue from https://github.com/roc-ops/Portrayal/issues/new/choose, one per idea. The forms there are for a device request, a modelling defect and a tooling bug, and anything else is a blank issue. Search the open issues first; a question about the format may already be under milestone "2 · Format reconciliation". A rough idea or a question can start in https://github.com/roc-ops/Portrayal/discussions instead. A page's layout, controls or copy belongs in `portrayal-site`; most other things belong here.

Write it the way this repo's design issues are written:

```markdown
One paragraph: what someone cannot do today, and who that is.

## What the library and the kit lack
- A fact, and the file or issue it was read in.

## What a contribution would add
1. A design note first, if a published format or schema changes.
2. The kit or library work, in steps a reviewer can take one at a time.

## Merge danger
One-way or two-way door, and why (see CONTRIBUTING.md).

## Done when
- A check someone can run.
```

## Ideas
### One model from campus down to a single port, under one address
Give every object one readable path, from campus through building, floor, room, rack and device to a single port, with every level generated from the same site file, rack files and compiled drawings. An engineer can put that path in a ticket or a cable record, and any view, export or search resolves it to the same port. No level has its own drawing to keep up to date. It is a small step because `data-path` already names the parts inside a device and the proposed site file gives each object an id; nothing yet joins the two.

### A top-down room view that opens one rack at a time
Draw a room from the site file as a floor plan, with racks as footprints and walls and pathways around them. Clicking a rack or row opens only its elevations and cables, and rotating turns the plan into 3D. An engineer finds equipment by where it stands rather than by file name, and can show a room to someone who has never opened a rack file. It holds up at room scale because only what is opened gets drawn: a single 275-cable rack took 39 s in one headless measurement (portrayal-site #192), so a room cannot draw every rack up front.

### Cable pathways as a routable graph that finds shared risk
Route each cable between racks along the trays, conduit and risers in the pathway graph, so it gets a real length and a list of the segments it runs through. Then query those lists: which redundant pairs share a segment, which segment is over its fill, and which cables a closed riser would strand. A planner sees a single point of failure on paper, before anything is pulled. These questions add one thing to the routing #1297 names: a way to mark two cables as a diverse pair.

### A parts list each deployment passes to the kit
Let whoever hosts the kit pass in their own list of optics and jumpers, keyed by the neutral types of #897. With no list, one BOM tool shows generic SR, LR and ER types, as on portrayal.dev; with a list, the same rack file shows that organisation's own part numbers. A type the list lacks is named as unmatched, not dropped or guessed. Engineers get a BOM their purchasing can use, rack files stay portable, and no private list enters the public library. An overlay is the wrong tool for this: it adds drawn parts, and this is only a lookup.

### A read-only rack embed in one tag
Wrap the kit's rack view in one custom element, `<portrayal-rack src="r1.rack.json" dist="/portrayal/dist">`, that loads the catalogue itself. Someone writing a web page, map popup or proposal gets a live elevation without writing loader code, and the host page supplies only its parts list and branding. Clicks come back as the view's existing pick event. Because the page reads the rack file, a change to the rack shows everywhere it is embedded, and nobody pastes a stale screenshot. `mountRack2d` already draws; what is missing is the part that needs no script.

### Start from what NetBox or Nautobot already holds
Portrayal writes to a DCIM and never reads from one. Add the other direction as a one-time read, on request: a site's racks, devices and cables become rack files and a site file. An engineer with a populated DCIM sees drawings of what exists on the first day instead of retyping it. Types are matched by the model and port names Portrayal's own exports write; anything it cannot match is listed by name with its rack units marked, and never guessed. Nothing is written back and nothing polls, so this stays documentation and not monitoring.

### A work list from two revisions of a plan
Compare two Git revisions of a rack or site file and write out what has to happen in the room: devices to rack or remove, optics to seat, cables to pull with their routes and lengths, and ports left free, each marked on before and after elevations. The engineer planning a change hands one generated sheet to the installer, and a reviewer reads the change as a list and not as JSON. It can be exact because objects keep stable ids and the files are already in Git. The kit has no way to compare two racks today.

### Room-scale checks that report like the linter
Run lint over a whole plan, not only a device: power per feed against its PDU, weight against a rack's load rating, airflow against a row's hot aisle, routed length against an optic's reach. Each finding names the object and its file, and a missing figure is reported as unknown, never counted as zero. A planner sees what fails before ordering anything, in a browser, in node or on a pull request. The figures already carry their provenance, so each answer can say how far to trust it, which a spreadsheet of nameplate numbers cannot.
