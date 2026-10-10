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
