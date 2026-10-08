# Rack kit: commands and questions an agent can use without reading the code

Status: 2026-10-08, design approved in conversation; spec awaiting review. Builds on
the rack core in `kit/rack/` (kit 0.3.0, #896), which must be merged first. A companion
spec in roc-ops/portrayal-site
(`docs/superpowers/specs/2026-10-08-rack-agent-tools-2-design.md`) covers the site's
side: the WebMCP tools that call what this spec adds. Named cable and optic types
(#897) come later and build on `fit`.

## 1. Why

portrayal.dev hands the Rack Builder's editor to AI agents as WebMCP tools over
`kit/rack/commands.js` and `queries.js`. Two real sessions (2026-10-08) got a 42U rack
built, cabled and exported. Every time the agent had to say "let me open the Explorer"
or "let me look at the code", the kit gave it no way to do what it needed:

| what the agent needed | what the kit has |
|---|---|
| what a device holds, and what each bay or cage can take | nothing; `describe` gives id, label, U and face only |
| seat one optic, or swap one cassette | `patch {swaps}`, which **replaces** the whole map and accepts any string: `{"port-48": "x"}` passes a dry run and is stored |
| set a latch colour or an optic's label | `patch {fields}`: the keys are undocumented and the map is replaced |
| a cable's routed length, to choose 0.5 m or 1 m | measured (`routedLength`, `stockLength`) but never returned |
| re-point a cable after a cassette swap renamed its port | none; the agent deleted and rebuilt 16 cables |
| delete "the cables on this device", or "every loose cable" | `cable.remove {id}`, one at a time, with ids from a listing that is cut short on a big rack |
| hear that a swap orphaned cables, or that OS2 meets an OM4 optic | the page shows these; `apply` returns nothing |
| find "a patch panel" | `catalog` matches manufacturer, model and ref only |

## 2. Decisions

| # | question | decision |
|---|---|---|
| D1 | merge or replace | **New commands merge; `patch` keeps replacing.** The Explorer pop-up hands back a whole map and the site sends it with `patch`; that stays. Agents get `fit` and `field`, which change one slot or one key. |
| D2 | where checking lives | **In the commands, when the catalogue is given.** Commands stay pure and synchronous. A caller that has loaded the slots (section 4) passes them in a per-call context, and the commands check against them. A caller that has not loaded them gets today's behaviour. |
| D3 | who loads the slots | **`loadSlots(dist, refs)` in `catalog.js`**, async, returning a synchronous lookup. The kit fetches nothing anywhere else. |
| D4 | what a change underneath returns | **Findings.** `apply` already returns `findings: [{kind, text}]`. Commands add notes for cables a swap orphans, ends it leaves loose, and media that no longer matches. Each note names the ids. |
| D5 | selectors | **A query, not a command argument.** `selectCables(rack, selector)` returns ids. Callers expand selectors into plain `cable.remove` / `cable.update` commands, so the command table stays id-based and a batch stays inspectable. |
| D6 | wording | Every new sentence is plain and names no site page or menu. #895's portrayal.dev-only sentences are fixed in the same PR where a command this spec touches carries one. |

## 3. Queries (`kit/rack/queries.js`)

### 3.1 `inspect(rack, id, ctx)`

`id` is an item id (`i3`) or a cable id (`c7`). It returns a plain object for the
caller to format, or `{error}` (GONE or CABLE_GONE).

**An item:**

```js
{kind: 'item', id, ref, model, manufacturer, label, cfg, configs: [{name, description, airflow}],
 ru, u, face, turned, on, unit, managers: [ids],
 bays:  [{path, view, group, holds, default, accepts: [{ref, name, kind}]}],
 cages: [{path, view, interface, media, holds, default, accepts: [{ref, name, kind}]}],
 fields: [{path, key, type, value, default, choices?}],
 cables: [{id, end: 'a'|'b', path, view, other: 'i4/port-2'}]}
```

- `bays`, `cages` and `holds` come from `ctx.slotsOf(ref)` (section 4) with
  `slotOptions` and `builtOccupants`. `holds` is what is seated after the item's own
  swaps: the swap if there is one, else what the configuration builds, else the default.
- `fields` lists the editable keys of every seated part that declares `fields` in
  `components.json`, with its current value from `item.fields`.
- Without `ctx.slotsOf`, `bays`, `cages` and `fields` are omitted and `slots: 'not
  loaded'` is set, so a caller can tell missing data from an empty device.

**A cable:**

```js
{kind: 'cable', id, a: {item, path, view, name}, b: {...}, media, purpose, label,
 length: {value, unit, source} | null, routed: {metres, stock} | null,
 route: {edited: bool, waypoints: [...], text}, lanes: [...], passes: {[itemId]: [ids]},
 loose: [{end, reason}], mismatch: [text]}
```

- `routed` comes from `routedLength(rack, cable, ctx)` and `stockLength`, when
  `ctx.route` is given. `route.text` comes from `routeText`.
- `lanes` comes from `lanesOf(frame)`. `passes` holds the ring, duct and pass-through
  ids on the cable's two devices, from `rack.json`'s `guides` and `passes`.
- `loose` and `mismatch` come from `ctx.cableFacts` facts when given, through
  `looseReason` and `mismatch`.

### 3.2 `selectCables(rack, selector, ctx)`

`selector` is one of these:

- `{item}`: every cable with an end on the item.
- `{item, path}` or `{item, path, view}`: the cable on that port, through `sameEnd` and `portPathOf`.
- `{loose: true}`: needs `ctx.cableFacts`; it is async for that reason.
- `{purpose}` or `{media}`.

It returns `{ids: [...]}` or `{error}`. An empty result is `{ids: []}`, not an error.

### 3.3 `describe` and `catalog`

- `describe(rack, ctx, {section, offset, limit})`:
  - `section` is `'items'`, `'cables'` or both.
  - The first line always gives the totals and the window shown: `Rack 1 (r1): 6 items,
    40 cables. Cables 21-40 shown.`
  - Item lines add `ref` and `cfg`. Cable lines add purpose and length.
  - With no window given, today's output and its 1,500-character bound stand.
- `catalog(devices, {text, ru, family, mount, kind})`:
  - `text` also matches the device's kind and capability words, for example "patch
    panel", "switch" or "cable manager".
  - `kind` filters on the same values.
  - This needs `kind` in `rack.json` (section 6).

## 4. The catalogue context

```js
// catalog.js
export async function loadSlots(dist, refs) -> {slotsOf(ref), compByRef(ref)}
```

- For each ref it fetches `<ref>.configs.json` through `jdist`, once per ref and
  memoised, and `components.json` once.
- `slotsOf(ref)` returns `{bays: {view: [...]}, cages: {view: [...]}, configs: [...],
  default}`, or `null` for an unknown ref. `compByRef(ref)` returns the component or
  `null`.
- A failed fetch for one ref leaves that ref `null`, and its commands are refused with
  "The parts list for <ref> could not be loaded." It never throws to the caller.

The editor gains a per-call context:

```js
ed.apply(cmds, {origin, ctx})   // ctx is merged over {chassisOf} for this call only
ed.preview(cmds, {ctx})
```

The site's agent layer loads the slots for every ref in the rack and the batch, then
passes `{slotsOf, compByRef}`. The page's own UI calls stay as they are.

## 5. Commands (`kit/rack/commands.js`)

### 5.1 `fit {id, path, ref}` (new)

- Seats `ref` in the bay or cage at `path` on item `id`. `ref: null` empties the slot,
  and `ref: 'default'` restores what the configuration builds by removing the key.
- It merges into `item.swaps`.
- **With `ctx.slotsOf`**, it checks through `acceptSwaps` against the merged map,
  nested bays included:
  - an unknown path is refused with "<path> is not a bay or cage on <label>. It has:
    <grouped list>";
  - a part the slot does not take is refused with "<path> does not take <ref>. It takes:
    <refs>". The list is cut at 8, then "and n more".
- Fields of the part it removes are dropped (`<path>-occupant`, or `<path>/module/...`).
- Findings:
  - "Removed the cables on <paths>: these ports are not on <new part>." This applies when
    a bay swap removes ports that cables end on. The cables are kept as loose ends,
    which is what `remove` does with `cables: 'keep'`.
  - "c3 now runs <media> into <part>." when `mismatch` applies, given facts.
- Summary: "Fitted <part name> in <path> on <label>." or "Emptied <path> on <label>."

### 5.2 `field {id, path, key, value}` (new)

- Sets one field on the part seated at `path`, merging into `item.fields[path]`.
- `value: null` resets it to the default.
- **With `ctx.compByRef`**, it checks that the seated part declares `key`, and checks the
  value with `fieldAccepts`. A refusal lists the part's keys and, for a choice field,
  its choices.

### 5.3 `cable.update` gains `a` and `b`

`a` or `b` (`{item, path, view}`) re-points that end. It runs `canCable` against the
other end with the cable itself ignored (`portFree`'s `ignoreId`), and refuses with its
sentence. The cable keeps its id, media, purpose, label and length. A hand-made route is
kept and noted as possibly stale: "c3's route was drawn for its old end."

### 5.4 `place` and `patch` check what they can

- **With `ctx.slotsOf`:**
  - `place` and `patch` refuse a `cfg` the device does not list, naming the ones it
    does.
  - `patch {swaps}` runs `acceptSwaps` on the map it is given. It still replaces the map,
    but no longer stores a ref the slot refuses.
- **`patch {cfg}` without `swaps`** now clears `swaps` and `fields` and returns the
  existing CLEARED note, as the site's inspector already does. Sending `swaps` or
  `fields` alongside `cfg` keeps what is sent.

### 5.5 Descriptions

- Every new and changed command has a description of 500 characters or less. Every
  argument has a description of 150 characters or less, and states its default when it
  has one.
- No description names a function (`freePorts()`, `catalog()`) or a site page.

## 6. `rack.json`

`rack_index.py` adds `kind` to each device, taken from `devices.json`:
`capability`, or the portfolio's category where the device has one. Values are plain
words: `switch`, `router`, `patch panel`, `cable manager`, `server`, `pdu`. It is an
additive field, so `format` stays 1, and `docs/format-stability.md` gets one line.

## 7. Tests (`spec/tests/js/rack-*.mjs`)

**queries:**
- `inspect` of an item, with and without slots loaded.
- `inspect` of a cable, with `routed` from a fixture route context.
- `selectCables` for every selector form, with an empty result.
- `describe` windows; the totals line is always present.
- `catalog` by `kind` and by text "patch panel".

**commands:**
- `fit`:
  - seat, empty and default;
  - a nested bay;
  - an unknown path, and a refused ref, each listing what the slot takes;
  - the orphaned-cable finding;
  - merge keeps the other swaps.
- `field`: set, reset, unknown key, refused value.
- `cable.update {a}`: re-point; refuse a taken port.
- `patch {cfg}` clears; `place` and `patch` refuse an unknown cfg when the slots are
  loaded.

**editor:** the per-call `ctx` reaches the commands for `apply` and `preview`, and is
not kept after the call.

**data:**
- `loadSlots` with a failing fetch for one ref (the others still load).
- `rack.json` carries `kind` (`test_rack_index.py`).

**house rules:** British comments (`comment_spelling.py`), and the kit's `npm test`.

## 8. Out of scope

- The WebMCP tools, `new_rack`, paging the site's port listing, and the site's
  description pass. These are in the companion site spec.
- Named cable and optic types (#897).
- Explorer controls for connector and boot colour (#897).
- An optics control in the Rack Builder's own device panel.
- Bulk `fit` over many ports. Callers batch one `fit` per port; a batch is one undo step.
