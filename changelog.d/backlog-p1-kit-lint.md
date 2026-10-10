### Fixed
- The kit's `loadDevice` and `loadStage` (`kit/shell.js`) take a generation each
  call, and one that a newer load overtook stops after its await: it writes no
  device, configuration or view, mounts no drawing and emits no `load`, and its
  promise rejects with an error `isSuperseded(err)` (exported) recognises. The
  stage holds exactly one drawing after any overlap. A host that awaited a load
  sees the rejection instead of carrying on with a stale target (#929).
- A `fields=` entry for a part drawn only on a face other than the one the link
  opens (a supply's wattage on the rear, a link opening on the front) is kept on
  reload: the shell fetches the other faces before judging the entry, as
  `applySwaps` already does for a slot on another face, and paints it when that
  face is mounted. It used to be ignored and dropped from the location (#818).

### Changed
- `kit/rack` no longer speaks as portrayal.dev's page (#895). A rack file newer
  than the kit is refused with "this reader supports up to version N" (no
  "Reload to get the newer page"); a system command sent without origin
  `system` is refused as "a system command, sent only by the caller"; the
  `COMMANDS` descriptions say "set by the caller" and "sent by the caller".
  `kitReadme` and `titleLines` name their maker as `source` (default
  `Portrayal`), `kitReadme` points a blank site or role at `settingsAt`
  (default: the rack's `dcim.site` and `dcim.role`), and the Nautobot script's
  address is named only when the caller passes `scriptUrl`: there is no
  portrayal.dev default. A host that wants its own sentences passes them; the
  Rack Builder passes `source: 'the Portrayal Rack Builder'`, its own
  `settingsAt` and its script URL to keep its README as it was.
- The rule and fix text of L18, L31, L45, L50 and L132 (`--list-rules`,
  `docs/lint-rules.md`, `lint-rules.json`) now say what each rule checks (#959).
  L18 asks a port on a family cage to state its media; L31 checks a distance a
  side or top region label states; L45 is cleared by drawing the face or by a
  gap whose `scope` names it, not by an `empty:` sentence (whose 40-character
  floor the schema holds); L50 is about printing off the part or covered by
  something drawn after it, not font size; L132 names both of its branches.
  What the rules raise is unchanged.
