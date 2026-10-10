### Fixed
- The kit's `loadDevice` and `loadStage` (`kit/shell.js`) take a generation each
  call, and one that a newer load overtook stops after its await: it writes no
  device, configuration or view, mounts no drawing and emits no `load`, and its
  promise rejects with an error `isSuperseded(err)` (exported) recognises. The
  stage holds exactly one drawing after any overlap. A host that awaited a load
  sees the rejection instead of carrying on with a stale target (#929).
